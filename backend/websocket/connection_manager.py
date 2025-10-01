"""WebSocket connection management"""
import logging
import json
from typing import Dict
from fastapi import WebSocket

from models import Game

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for players"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.game_service = None  # Will be injected from main.py

    def set_game_service(self, game_service):
        """Inject game service dependency"""
        self.game_service = game_service

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected. Total active connections: {len(self.active_connections)}")

    def disconnect(self, client_id: str):
        """Unregister a WebSocket connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected. Total active connections: {len(self.active_connections)}")
        else:
            logger.warning(f"Attempted to disconnect {client_id} but they were not in active connections")

    async def send_personal_message(self, message: str, client_id: str):
        """Send a message to a specific client"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_text(message)
                logger.debug(f"Successfully sent message to {client_id}")
            except Exception as e:
                logger.error(f"Failed to send message to {client_id}: {e}")
        else:
            logger.warning(f"Client {client_id} not in active connections")

    async def broadcast_to_game(self, message: str, game: Game):
        """Broadcast a message to all players in a game"""
        for player in game.players:
            await self.send_personal_message(message, player.id)

    async def send_game_state(self, game_id: str, player_id: str = None):
        """
        Send current game state to player(s)

        Args:
            game_id: The game ID to fetch and send state for
            player_id: Optional player ID to send to specific player, otherwise broadcasts to all
        """
        if not self.game_service:
            logger.error("game_service not injected into ConnectionManager")
            return

        game = self.game_service.get_game(game_id)
        if not game:
            logger.warning(f"Game {game_id} not found when trying to send game state")
            return

        logger.info(f"Sending game state for game {game_id} with {len(game.players)} players")

        if player_id:
            # Send player-specific state
            state = game.to_player_dict(player_id)
            message = json.dumps({"type": "game_state", "data": state})
            logger.info(f"Sending game state to player {player_id}")
            await self.send_personal_message(message, player_id)
        else:
            # Broadcast general state to all players
            for player in game.players:
                state = game.to_player_dict(player.id)
                message = json.dumps({"type": "game_state", "data": state})
                logger.info(f"Broadcasting game state to player {player.id} ({player.name})")
                await self.send_personal_message(message, player.id)


# Global connection manager instance
connection_manager = ConnectionManager()
