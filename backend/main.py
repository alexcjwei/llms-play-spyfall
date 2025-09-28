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

        # Check if it's now a bot's turn
        await handle_bot_turn(game_id)

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

        # Check if it's now a bot's turn
        await handle_bot_turn(game_id)
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

        # Check if it's now a bot's turn
        await handle_bot_turn(game_id)
    else:
        # Send error to the requesting player
        error_response = {
            "type": "answer_error",
            "message": "Cannot give answer (not your turn)"
        }
        await manager.send_personal_message(json.dumps(error_response), client_id)

async def handle_bot_turn(game_id: str):
    """Handle bot's turn - make them ask questions, give answers, or vote automatically"""
    if game_id not in active_games:
        logger.info(f"handle_bot_turn: Game {game_id} not found")
        return

    game = active_games[game_id]

    # Handle bot voting during accusation phase
    if game.status == GameStatus.VOTING and game.current_accusation:
        await handle_bot_voting(game_id)
        return

    current_player = next((p for p in game.players if p.id == game.current_turn), None)

    logger.info(f"handle_bot_turn: Game {game_id}, current turn: {game.current_turn}, current player: {current_player.name if current_player else 'None'}, is_bot: {current_player.is_bot if current_player else 'N/A'}")

    # Only proceed if it's a bot's turn for Q&A
    if not current_player or not current_player.is_bot:
        logger.info(f"handle_bot_turn: Not a bot's turn, exiting")
        return

    # Add delay to simulate thinking
    await asyncio.sleep(2)

    # Check if bot needs to answer a question
    last_message = game.messages[-1] if game.messages else None
    logger.info(f"handle_bot_turn: Last message: {last_message.type if last_message else 'None'}, to_player: {last_message.to_player if last_message else 'None'}")

    if last_message and last_message.type == "question" and last_message.to_player == current_player.id:
        # Bot needs to answer
        logger.info(f"handle_bot_turn: Bot {current_player.name} needs to answer")
        if game.give_answer(current_player.id, "Answer"):
            logger.info(f"Bot {current_player.name} gave an answer")
            await manager.send_game_state(game_id)
            # Check if bot can ask next question
            await handle_bot_turn(game_id)
    else:
        # Bot needs to ask a question
        logger.info(f"handle_bot_turn: Bot {current_player.name} needs to ask a question")
        # Get available players (exclude self and the person who just asked this bot)
        available_players = [p for p in game.players if p.id != current_player.id and p.id != game.last_questioned_by]
        if available_players:
            target = random.choice(available_players)  # Randomly choose from available players
            logger.info(f"handle_bot_turn: Bot {current_player.name} asking {target.name}")
            if game.ask_question(current_player.id, target.id, "Question"):
                logger.info(f"Bot {current_player.name} asked a question to {target.name}")
                await manager.send_game_state(game_id)
                # Check if target is also a bot and needs to answer
                await handle_bot_turn(game_id)
            else:
                logger.info(f"handle_bot_turn: Failed to ask question")
        else:
            logger.info(f"handle_bot_turn: No available players to ask (last_questioned_by={game.last_questioned_by})")

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

    # Make the accusation
    if game.stop_clock_for_accusation(client_id, accused_id):
        logger.info(f"Player {client_id} accused {accused_id} in game {game_id}")

        # Send updated game state to all players (now in voting mode)
        await manager.send_game_state(game_id)

        # Notify all players about the accusation
        accuser_name = next((p.name for p in game.players if p.id == client_id), "Unknown")
        accused_name = next((p.name for p in game.players if p.id == accused_id), "Unknown")

        response = {
            "type": "accusation_made",
            "accuser": accuser_name,
            "accused": accused_name,
            "game_id": game_id
        }
        await manager.broadcast_to_game(json.dumps(response), game_id)
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

    if game.vote_on_accusation(client_id, vote):
        logger.info(f"Player {client_id} voted {vote} in game {game_id}")

        # Send updated game state to all players
        await manager.send_game_state(game_id)

        # Check if voting is complete and handle game end if needed
        await handle_bot_turn(game_id)  # Bots should vote too

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