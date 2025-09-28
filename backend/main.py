from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import json
import logging
import uuid
import asyncio
import random
from models import Game, Player, GameStatus

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Spyfall Online API", version="1.0.0")

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for game state
active_games: dict[str, Game] = {}
connected_clients = {}
pending_tasks: dict[str, asyncio.Task] = {}  # game_id -> pending async task

def cancel_pending_task(game_id: str):
    """Cancel any pending task for the given game."""
    if game_id in pending_tasks:
        task = pending_tasks[game_id]
        if not task.done():
            task.cancel()
        del pending_tasks[game_id]
        logger.info(f"Cancelled pending task for game {game_id}")

def schedule_task(game_id: str, task: asyncio.Task):
    """Schedule a new task for the given game, cancelling any existing task."""
    cancel_pending_task(game_id)  # Cancel existing task first
    pending_tasks[game_id] = task
    logger.info(f"Scheduled new task for game {game_id}")

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected")

    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_text(message)

    async def broadcast_to_game(self, message: str, game_id: str):
        if game_id in active_games:
            game = active_games[game_id]
            for player in game.players:
                await self.send_personal_message(message, player.id)

    async def send_game_state(self, game_id: str, player_id: str = None):
        """Send current game state to player(s)"""
        if game_id not in active_games:
            return

        game = active_games[game_id]

        if player_id:
            # Send player-specific state
            state = game.to_player_dict(player_id)
            message = json.dumps({"type": "game_state", "data": state})
            await self.send_personal_message(message, player_id)
        else:
            # Broadcast general state to all players
            for player in game.players:
                state = game.to_player_dict(player.id)
                message = json.dumps({"type": "game_state", "data": state})
                await self.send_personal_message(message, player.id)

manager = ConnectionManager()

@app.get("/")
async def root():
    return {"message": "Spyfall Online API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle different message types
            message_type = message.get("type")

            if message_type == "join_game":
                await handle_join_game(client_id, message)
            elif message_type == "start_game":
                await handle_start_game(client_id, message)
            elif message_type == "ask_question":
                await handle_ask_question(client_id, message)
            elif message_type == "give_answer":
                await handle_give_answer(client_id, message)
            elif message_type == "vote":
                await handle_vote(client_id, message)
            elif message_type == "accuse_player":
                await handle_accuse_player(client_id, message)
            else:
                logger.warning(f"Unknown message type: {message_type}")

    except WebSocketDisconnect:
        manager.disconnect(client_id)
        await handle_client_disconnect(client_id)

async def handle_join_game(client_id: str, message: dict):
    """Handle player joining a game"""
    game_id = message.get("game_id", "default")
    player_name = message.get("player_name", f"Player_{client_id[:8]}")
    is_bot = message.get("is_bot", False)

    # Create game if it doesn't exist
    if game_id not in active_games:
        game = Game(id=game_id)
        active_games[game_id] = game
        logger.info(f"Created new game: {game_id}")

    game = active_games[game_id]

    # Check if player is reconnecting (already exists in game)
    existing_player = next((p for p in game.players if p.id == client_id), None)
    if existing_player:
        # Player is reconnecting
        existing_player.is_connected = True
        logger.info(f"Player {existing_player.name} ({client_id}) reconnected to game {game_id}")

        # Send game state to all players
        await manager.send_game_state(game_id)

        # Send reconnection confirmation
        response = {
            "type": "rejoin_success",
            "game_id": game_id,
            "player_id": client_id
        }
        await manager.send_personal_message(json.dumps(response), client_id)
        return

    # Create new player
    player = Player(
        id=client_id,
        name=player_name,
        is_bot=is_bot,
        is_connected=True
    )

    if game.add_player(player):
        logger.info(f"Player {player_name} ({client_id}) joined game {game_id}")

        # Send game state to all players
        await manager.send_game_state(game_id)

        # Send join confirmation to the joining player
        response = {
            "type": "join_success",
            "game_id": game_id,
            "player_id": client_id
        }
        await manager.send_personal_message(json.dumps(response), client_id)
    else:
        # Failed to join (game full or in progress)
        error_response = {
            "type": "join_error",
            "message": "Cannot join game (full or in progress)"
        }
        await manager.send_personal_message(json.dumps(error_response), client_id)

async def handle_start_game(client_id: str, message: dict):
    """Handle game start request"""
    game_id = message.get("game_id")

    if not game_id or game_id not in active_games:
        error_response = {
            "type": "start_error",
            "message": "Game not found"
        }
        await manager.send_personal_message(json.dumps(error_response), client_id)
        return

    game = active_games[game_id]

    # Check if the requesting player is in the game
    player = next((p for p in game.players if p.id == client_id), None)
    if not player:
        error_response = {
            "type": "start_error",
            "message": "You are not in this game"
        }
        await manager.send_personal_message(json.dumps(error_response), client_id)
        return

    # Add bots if needed to reach minimum players
    while len(game.players) < 3:
        bot_id = str(uuid.uuid4())
        bot_names = ["Alice", "Bob", "Carol", "Dan", "Eve", "Frank", "Grace"]
        bot_name = bot_names[len([p for p in game.players if p.is_bot]) % len(bot_names)]

        bot_player = Player(
            id=bot_id,
            name=bot_name,
            is_bot=True,
            is_connected=True
        )
        game.add_player(bot_player)
        logger.info(f"Added bot {bot_name} to game {game_id}")

    # Try to start the game
    if game.start_game():
        logger.info(f"Game {game_id} started with {len(game.players)} players")

        # Send updated game state to all players
        await manager.send_game_state(game_id)

        # Check if it's now a bot's turn - schedule with slight delay
        schedule_next_bot_action(game_id, delay=1)

        # Send start confirmation
        response = {
            "type": "game_started",
            "game_id": game_id
        }
        await manager.broadcast_to_game(json.dumps(response), game_id)
    else:
        error_response = {
            "type": "start_error",
            "message": "Cannot start game (insufficient players or wrong status)"
        }
        await manager.send_personal_message(json.dumps(error_response), client_id)

async def handle_ask_question(client_id: str, message: dict):
    """Handle player asking a question"""
    game_id = message.get("game_id")
    content = message.get("content")
    target_id = message.get("target")

    if not game_id or game_id not in active_games:
        return

    game = active_games[game_id]

    if game.ask_question(client_id, target_id, content):
        logger.info(f"Question asked: {client_id} -> {target_id}: {content}")
        # Send updated game state to all players
        await manager.send_game_state(game_id)

        # Check if it's now a bot's turn - schedule with slight delay
        schedule_next_bot_action(game_id, delay=1)
    else:
        # Send error to the requesting player
        error_response = {
            "type": "question_error",
            "message": "Cannot ask question (not your turn or invalid target)"
        }
        await manager.send_personal_message(json.dumps(error_response), client_id)

async def handle_give_answer(client_id: str, message: dict):
    """Handle player giving an answer"""
    game_id = message.get("game_id")
    content = message.get("content")

    if not game_id or game_id not in active_games:
        return

    game = active_games[game_id]

    if game.give_answer(client_id, content):
        logger.info(f"Answer given: {client_id}: {content}")
        # Send updated game state to all players
        await manager.send_game_state(game_id)

        # Check if it's now a bot's turn - schedule with slight delay
        schedule_next_bot_action(game_id, delay=1)
    else:
        # Send error to the requesting player
        error_response = {
            "type": "answer_error",
            "message": "Cannot give answer (not your turn)"
        }
        await manager.send_personal_message(json.dumps(error_response), client_id)

async def delayed_bot_action(game_id: str, action_type: str, delay: int = 0):
    """Generic delayed bot action handler with state checking."""
    if delay > 0:
        await asyncio.sleep(delay)

    # Check if game still exists
    if game_id not in active_games:
        logger.info(f"delayed_bot_action: Game {game_id} not found after delay")
        return

    game = active_games[game_id]

    # Route to appropriate handler based on action type
    if action_type == "turn":
        # Only proceed if game allows bot actions
        if game.status not in [GameStatus.IN_PROGRESS, GameStatus.VOTING, GameStatus.END_OF_ROUND_VOTING]:
            logger.info(f"delayed_bot_action: Game {game_id} not in valid state for bot actions (status: {game.status})")
            return

        # For IN_PROGRESS games, don't act if clock is stopped (voting states expect clock to be stopped)
        if game.status == GameStatus.IN_PROGRESS and game.clock_stopped:
            logger.info(f"delayed_bot_action: Game {game_id} clock stopped during IN_PROGRESS")
            return

        await handle_bot_turn_immediate(game_id)

    elif action_type == "voting":
        if not game.current_accusation:
            return

        # Handle both regular voting and end-of-round voting
        if game.status == GameStatus.VOTING:
            await handle_bot_voting(game_id)
        elif game.status == GameStatus.END_OF_ROUND_VOTING:
            await handle_end_of_round_bot_voting(game_id)

    elif action_type == "end_of_round_voting":
        if game.status != GameStatus.END_OF_ROUND_VOTING:
            return
        await handle_end_of_round_bot_voting(game_id)

    elif action_type == "end_of_round_accusation":
        if game.status != GameStatus.END_OF_ROUND_VOTING:
            return
        await handle_bot_end_of_round_accusation(game_id)

# Convenience wrappers for backward compatibility
async def delayed_bot_turn(game_id: str, delay: int = 2):
    """Delayed bot turn handling with state checking."""
    await delayed_bot_action(game_id, "turn", delay)

async def delayed_bot_voting(game_id: str, delay: int = 0):
    """Delayed bot voting action with state checking."""
    await delayed_bot_action(game_id, "voting", delay)

async def delayed_bot_end_of_round_voting(game_id: str, delay: int = 0):
    """Delayed bot end-of-round voting action with state checking."""
    await delayed_bot_action(game_id, "end_of_round_voting", delay)

async def delayed_bot_end_of_round_accusation(game_id: str, delay: int = 0):
    """Delayed bot end-of-round accusation action with state checking."""
    await delayed_bot_action(game_id, "end_of_round_accusation", delay)

async def handle_bot_turn_immediate(game_id: str):
    """Handle bot's turn immediately without delay - core bot logic."""
    if game_id not in active_games:
        logger.info(f"handle_bot_turn_immediate: Game {game_id} not found")
        return

    game = active_games[game_id]

    # Handle voting states
    if game.status == GameStatus.VOTING:
        task = asyncio.create_task(delayed_bot_voting(game_id))
        schedule_task(game_id, task)
        return
    elif game.status == GameStatus.END_OF_ROUND_VOTING:
        task = asyncio.create_task(delayed_bot_end_of_round_accusation(game_id))
        schedule_task(game_id, task)
        return

    # Don't handle bot actions if game is not in progress or clock is stopped
    if game.status != GameStatus.IN_PROGRESS or game.clock_stopped:
        logger.info(f"handle_bot_turn_immediate: Game {game_id} not in progress (status: {game.status}, clock_stopped: {game.clock_stopped})")
        return

    current_player = next((p for p in game.players if p.id == game.current_turn), None)

    logger.info(f"handle_bot_turn_immediate: Game {game_id}, current turn: {game.current_turn}, current player: {current_player.name if current_player else 'None'}, is_bot: {current_player.is_bot if current_player else 'N/A'}")

    # Only proceed if it's a bot's turn for Q&A
    if not current_player or not current_player.is_bot:
        logger.info(f"handle_bot_turn_immediate: Not a bot's turn, exiting")
        return

    # Check if bot needs to answer a question
    last_message = game.messages[-1] if game.messages else None
    logger.info(f"handle_bot_turn_immediate: Last message: {last_message.type if last_message else 'None'}, to_player: {last_message.to_player if last_message else 'None'}")

    if last_message and last_message.type == "question" and last_message.to_player == current_player.id:
        # Bot needs to answer
        logger.info(f"handle_bot_turn_immediate: Bot {current_player.name} needs to answer")
        if game.give_answer(current_player.id, "Answer"):
            logger.info(f"Bot {current_player.name} gave an answer")
            await manager.send_game_state(game_id)
            # Schedule next bot action instead of immediate recursion
            schedule_next_bot_action(game_id)
    else:
        # Bot needs to ask a question
        logger.info(f"handle_bot_turn_immediate: Bot {current_player.name} needs to ask a question")
        # Get available players (exclude self and the person who just asked this bot)
        available_players = [p for p in game.players if p.id != current_player.id and p.id != game.last_questioned_by]
        if available_players:
            target = random.choice(available_players)  # Randomly choose from available players
            logger.info(f"handle_bot_turn_immediate: Bot {current_player.name} asking {target.name}")
            if game.ask_question(current_player.id, target.id, "Question"):
                logger.info(f"Bot {current_player.name} asked a question to {target.name}")
                await manager.send_game_state(game_id)
                # Schedule next bot action instead of immediate recursion
                schedule_next_bot_action(game_id)
            else:
                logger.info(f"handle_bot_turn_immediate: Failed to ask question")
        else:
            logger.info(f"handle_bot_turn_immediate: No available players to ask (last_questioned_by={game.last_questioned_by})")

def schedule_next_bot_action(game_id: str, delay: int = 2):
    """Schedule the next bot action with a delay."""
    task = asyncio.create_task(delayed_bot_turn(game_id, delay))
    schedule_task(game_id, task)

async def handle_bot_turn(game_id: str):
    """Handle bot's turn - use immediate version for backwards compatibility."""
    await handle_bot_turn_immediate(game_id)

async def handle_bot_voting(game_id: str):
    """Handle bots voting on accusations with 50% chance each way"""
    if game_id not in active_games:
        return

    game = active_games[game_id]

    if not game.current_accusation or game.status != GameStatus.VOTING:
        return

    # Find bots who haven't voted yet
    bots_to_vote = []
    for player in game.players:
        if (player.is_bot and
            player.id != game.current_accusation.accused_id and  # Accused can't vote
            player.id not in game.current_accusation.votes):     # Haven't voted yet
            bots_to_vote.append(player)

    # Make each bot vote with 50% chance
    for bot in bots_to_vote:
        # Add small delay between bot votes to make it feel more natural
        await asyncio.sleep(1)

        # 50% chance to vote guilty
        vote = random.choice([True, False])

        if game.vote_on_accusation(bot.id, vote):
            logger.info(f"Bot {bot.name} voted {vote} on accusation in game {game_id}")

            # Send updated game state after each vote
            await manager.send_game_state(game_id)

            # Check if voting is complete (this triggers resolution if all votes are in)
            # The vote_on_accusation method handles resolution automatically

async def handle_accuse_player(client_id: str, message: dict):
    """Handle player making an accusation"""
    game_id = message.get("game_id")
    accused_id = message.get("target")

    if not game_id or game_id not in active_games:
        error_response = {
            "type": "accusation_error",
            "message": "Game not found"
        }
        await manager.send_personal_message(json.dumps(error_response), client_id)
        return

    game = active_games[game_id]

    # Use appropriate accusation method based on game status
    if game.status == GameStatus.END_OF_ROUND_VOTING:
        success = game.make_end_of_round_accusation(client_id, accused_id)
        accusation_type = "end-of-round"
        response_type = "end_of_round_accusation_made"
    else:
        success = game.stop_clock_for_accusation(client_id, accused_id)
        accusation_type = "mid-game"
        response_type = "accusation_made"

    if success:
        logger.info(f"Player {client_id} made {accusation_type} accusation against {accused_id} in game {game_id}")

        # Cancel any pending bot actions - accusation interrupts everything
        cancel_pending_task(game_id)

        # Send updated game state to all players
        await manager.send_game_state(game_id)

        # Notify all players about the accusation
        accuser_name = next((p.name for p in game.players if p.id == client_id), "Unknown")
        accused_name = next((p.name for p in game.players if p.id == accused_id), "Unknown")

        response = {
            "type": response_type,
            "accuser": accuser_name,
            "accused": accused_name,
            "game_id": game_id
        }
        await manager.broadcast_to_game(json.dumps(response), game_id)

        # Schedule bot actions based on game state
        task = asyncio.create_task(delayed_bot_turn(game_id, delay=0))
        schedule_task(game_id, task)
    else:
        error_response = {
            "type": "accusation_error",
            "message": "Cannot make accusation (game not in progress, already accused this round, or clock stopped)"
        }
        await manager.send_personal_message(json.dumps(error_response), client_id)

async def handle_vote(client_id: str, message: dict):
    """Handle voting on an accusation"""
    game_id = message.get("game_id")
    vote = message.get("vote")  # True for guilty, False for innocent

    if not game_id or game_id not in active_games:
        return

    game = active_games[game_id]

    # Use appropriate voting method based on game status
    if game.status == GameStatus.END_OF_ROUND_VOTING:
        success = game.vote_on_end_of_round_accusation(client_id, vote)
        vote_type = "end-of-round"
    else:
        success = game.vote_on_accusation(client_id, vote)
        vote_type = "mid-game"

    if success:
        logger.info(f"Player {client_id} voted {vote} in {vote_type} voting in game {game_id}")

        # Send updated game state to all players
        await manager.send_game_state(game_id)

        # Schedule bot actions (voting or accusations) based on game status
        task = asyncio.create_task(delayed_bot_turn(game_id, delay=0))
        schedule_task(game_id, task)

async def handle_bot_end_of_round_accusation(game_id: str):
    """Handle bot making end-of-round accusation when it's their turn"""
    if game_id not in active_games:
        logger.info(f"handle_bot_end_of_round_accusation: Game {game_id} not found")
        return

    game = active_games[game_id]

    if game.status != GameStatus.END_OF_ROUND_VOTING:
        logger.info(f"handle_bot_end_of_round_accusation: Game {game_id} not in END_OF_ROUND_VOTING status (current: {game.status})")
        return

    # If there's already an accusation, bots should vote (regardless of whose turn it is)
    if game.current_accusation:
        logger.info(f"handle_bot_end_of_round_accusation: Current accusation exists, handling voting instead")
        task = asyncio.create_task(delayed_bot_end_of_round_voting(game_id))
        schedule_task(game_id, task)
        return

    # No active accusation - check if it's a bot's turn to make an accusation
    current_player = next((p for p in game.players if p.id == game.current_turn), None)
    logger.info(f"handle_bot_end_of_round_accusation: Game {game_id}, current turn: {game.current_turn}, current player: {current_player.name if current_player else 'None'}, is_bot: {current_player.is_bot if current_player else 'N/A'}, has_accused: {current_player.has_accused_this_round if current_player else 'N/A'}")

    # Only proceed if it's a bot's turn
    if not current_player or not current_player.is_bot:
        logger.info(f"handle_bot_end_of_round_accusation: Not a bot's turn, exiting")
        return

    # Check if bot has already accused this round
    if current_player.has_accused_this_round:
        logger.info(f"handle_bot_end_of_round_accusation: Bot {current_player.name} has already accused this round")
        return

    # Add delay to simulate thinking
    await asyncio.sleep(2)

    # Bot makes a random accusation (excluding themselves)
    potential_targets = [p for p in game.players if p.id != current_player.id]
    if potential_targets:
        target = random.choice(potential_targets)

        logger.info(f"Bot {current_player.name} making end-of-round accusation against {target.name}")

        if game.make_end_of_round_accusation(current_player.id, target.id):
            # Send updated game state
            await manager.send_game_state(game_id)

            # Notify players
            response = {
                "type": "end_of_round_accusation_made",
                "accuser": current_player.name,
                "accused": target.name,
                "game_id": game_id
            }
            await manager.broadcast_to_game(json.dumps(response), game_id)

            # Schedule bot voting on this accusation
            task = asyncio.create_task(delayed_bot_turn(game_id, delay=0))
            schedule_task(game_id, task)
        else:
            logger.info(f"handle_bot_end_of_round_accusation: Failed to make accusation for bot {current_player.name}")
    else:
        logger.info(f"handle_bot_end_of_round_accusation: No potential targets for bot {current_player.name}")

async def handle_end_of_round_bot_voting(game_id: str):
    """Handle bots voting on end-of-round accusations"""
    if game_id not in active_games:
        return

    game = active_games[game_id]

    if not game.current_accusation or game.status != GameStatus.END_OF_ROUND_VOTING:
        return

    # Find bots who haven't voted yet
    bots_to_vote = []
    for player in game.players:
        if (player.is_bot and
            player.id != game.current_accusation.accused_id and  # Accused can't vote
            player.id not in game.current_accusation.votes):     # Haven't voted yet
            bots_to_vote.append(player)

    # Make each bot vote with 50% chance
    for bot in bots_to_vote:
        # Add small delay between bot votes
        await asyncio.sleep(1)

        # 50% chance to vote guilty
        vote = random.choice([True, False])

        if game.vote_on_end_of_round_accusation(bot.id, vote):
            logger.info(f"End-of-round bot vote: {bot.name} voted {vote} in game {game_id}")

            # Send updated game state after each vote
            await manager.send_game_state(game_id)

            # If vote resolution moved to next accuser, schedule bot logic
            if game.status == GameStatus.END_OF_ROUND_VOTING and not game.current_accusation:
                logger.info(f"Vote resolution complete, scheduling bot logic for next accuser")
                task = asyncio.create_task(delayed_bot_turn(game_id, delay=0))
                schedule_task(game_id, task)

async def handle_client_disconnect(client_id: str):
    """Handle client disconnection"""
    # Mark player as disconnected instead of removing them
    for game_id, game in active_games.items():
        player = next((p for p in game.players if p.id == client_id), None)
        if player:
            logger.info(f"Player {player.name} ({client_id}) disconnected from game {game_id}")
            player.is_connected = False

            # Send updated game state to remaining players
            await manager.send_game_state(game_id)

            response = {
                "type": "player_disconnected",
                "player_id": client_id,
                "player_name": player.name
            }
            await manager.broadcast_to_game(json.dumps(response), game_id)

# Serve React build files in production
if not os.getenv("DEBUG", "False").lower() == "true":
    app.mount("/", StaticFiles(directory="../frontend/build", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "False").lower() == "true"

    uvicorn.run(app, host=host, port=port, reload=debug)