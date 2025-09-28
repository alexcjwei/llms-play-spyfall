from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import json
import logging
import uuid
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
    else:
        # Send error to the requesting player
        error_response = {
            "type": "answer_error",
            "message": "Cannot give answer (not your turn)"
        }
        await manager.send_personal_message(json.dumps(error_response), client_id)

async def handle_vote(client_id: str, message: dict):
    # Placeholder for voting logic
    game_id = message.get("game_id")
    target = message.get("target")

    response = {
        "type": "vote_cast",
        "voter": client_id,
        "target": target
    }

    if game_id:
        await manager.broadcast_to_game(json.dumps(response), game_id)

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