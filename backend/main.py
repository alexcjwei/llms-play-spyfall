from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import json
import logging

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
active_games = {}
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
            for client_id in active_games[game_id].get("players", []):
                await self.send_personal_message(message, client_id)

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
            elif message_type == "send_message":
                await handle_game_message(client_id, message)
            elif message_type == "vote":
                await handle_vote(client_id, message)
            else:
                logger.warning(f"Unknown message type: {message_type}")

    except WebSocketDisconnect:
        manager.disconnect(client_id)
        await handle_client_disconnect(client_id)

async def handle_join_game(client_id: str, message: dict):
    # Placeholder for game joining logic
    game_id = message.get("game_id", "default")

    if game_id not in active_games:
        active_games[game_id] = {
            "id": game_id,
            "players": [],
            "status": "waiting",
            "created_at": None
        }

    if client_id not in active_games[game_id]["players"]:
        active_games[game_id]["players"].append(client_id)

    response = {
        "type": "game_joined",
        "game_id": game_id,
        "players": active_games[game_id]["players"]
    }

    await manager.broadcast_to_game(json.dumps(response), game_id)

async def handle_start_game(client_id: str, message: dict):
    # Placeholder for game start logic
    game_id = message.get("game_id")
    if game_id and game_id in active_games:
        active_games[game_id]["status"] = "in_progress"

        response = {
            "type": "game_started",
            "game_id": game_id
        }

        await manager.broadcast_to_game(json.dumps(response), game_id)

async def handle_game_message(client_id: str, message: dict):
    # Placeholder for game message handling
    game_id = message.get("game_id")
    content = message.get("content")

    if game_id and game_id in active_games:
        response = {
            "type": "message",
            "from": client_id,
            "content": content,
            "timestamp": None  # Add timestamp logic
        }

        await manager.broadcast_to_game(json.dumps(response), game_id)

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
    # Remove client from all games
    for game_id, game in active_games.items():
        if client_id in game["players"]:
            game["players"].remove(client_id)

            response = {
                "type": "player_left",
                "player": client_id,
                "players": game["players"]
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