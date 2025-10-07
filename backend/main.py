"""
Spyfall Online API - Refactored
Clean, modular FastAPI application
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import json
import logging
import asyncio

# Import models
from models import Game, Player, GameStatus

# Import services
from services import game_service, llm_service
from services.parallel_bot_service import ParallelBotService
# Legacy prompts import removed - using tool-based system

# Import websocket components
from websocket import connection_manager, handlers

# Import utils
from utils import bot_orchestrator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Spyfall Online API", version="1.0.0")

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize bot services with dependencies
parallel_bot_service_instance = ParallelBotService(llm_service)

# Inject game_service into connection_manager
connection_manager.set_game_service(game_service)

# Inject dependencies into bot orchestrator to avoid circular imports
bot_orchestrator.parallel_bot_service = parallel_bot_service_instance
bot_orchestrator.game_service = game_service
bot_orchestrator.connection_manager = connection_manager

# Inject bot orchestrator into handlers
handlers.set_bot_orchestrator(bot_orchestrator)


# Background task for timer checking
async def check_game_timers():
    """Periodically check for expired game timers"""
    while True:
        try:
            expired_games = game_service.check_timers()
            for game_id in expired_games:
                # Cancel any pending bot actions
                bot_orchestrator.cancel_pending_tasks(game_id)
                # Send updated game state to all players
                await connection_manager.send_game_state(game_id)
            await asyncio.sleep(1)  # Check every second
        except Exception as e:
            logger.error(f"Error in timer checking: {e}")
            await asyncio.sleep(1)


# Global variable to store the timer task
timer_task = None


@app.get("/")
async def root():
    return {"message": "Spyfall Online API", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time game communication"""
    await connection_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle different message types
            message_type = message.get("type")

            try:
                if message_type == "join_game":
                    await handlers.handle_join_game(client_id, message)
                elif message_type == "start_game":
                    await handlers.handle_start_game(client_id, message)
                elif message_type == "ask_question":
                    await handlers.handle_ask_question(client_id, message)
                elif message_type == "give_answer":
                    await handlers.handle_give_answer(client_id, message)
                elif message_type == "vote":
                    await handlers.handle_vote(client_id, message)
                elif message_type == "accuse_player":
                    await handlers.handle_accuse_player(client_id, message)
                elif message_type == "spy_guess_location":
                    await handlers.handle_spy_guess_location(client_id, message)
                else:
                    logger.warning(f"Unknown message type: {message_type}")
            except Exception as e:
                logger.error(
                    f"Error handling message type {message_type}: {e}", exc_info=True
                )
                # Don't break the connection, just log and continue

    except WebSocketDisconnect:
        connection_manager.disconnect(client_id, websocket)
        await handlers.handle_client_disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}", exc_info=True)
        connection_manager.disconnect(client_id, websocket)
        await handlers.handle_client_disconnect(client_id)


# Serve React build files in production
if not os.getenv("DEBUG", "False").lower() == "true":
    app.mount("/", StaticFiles(directory="../frontend/build", html=True), name="static")


@app.on_event("startup")
async def startup_event():
    """Start background tasks when the server starts"""
    global timer_task
    timer_task = asyncio.create_task(check_game_timers())
    logger.info("Started timer checking task")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up background tasks when the server shuts down"""
    global timer_task
    if timer_task:
        timer_task.cancel()
        try:
            await timer_task
        except asyncio.CancelledError:
            pass
    logger.info("Stopped timer checking task")


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "False").lower() == "true"

    uvicorn.run(app, host=host, port=port, reload=debug)
