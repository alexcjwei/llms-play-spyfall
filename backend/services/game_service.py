"""Game orchestration service"""
import logging
import uuid
from typing import Optional, Dict

from models import Game, Player, GameStatus

logger = logging.getLogger(__name__)


class GameService:
    """Service for managing game lifecycle and operations"""

    def __init__(self):
        self.active_games: Dict[str, Game] = {}

    def create_game(self, game_id: str) -> Game:
        """Create a new game"""
        game = Game(id=game_id)
        self.active_games[game_id] = game
        logger.info(f"Created new game: {game_id}")
        return game

    def get_game(self, game_id: str) -> Optional[Game]:
        """Get a game by ID"""
        return self.active_games.get(game_id)

    def remove_game(self, game_id: str) -> bool:
        """Remove a game"""
        if game_id in self.active_games:
            del self.active_games[game_id]
            logger.info(f"Removed game: {game_id}")
            return True
        return False

    def add_player_to_game(self, game_id: str, player: Player) -> tuple[bool, Optional[str]]:
        """
        Add a player to a game

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        game = self.get_game(game_id)
        if not game:
            return False, "Game not found"

        if game.add_player(player):
            logger.info(f"Player {player.name} ({player.id}) joined game {game_id}")
            return True, None
        else:
            return False, "Cannot join game (full or in progress)"

    def reconnect_player(self, game_id: str, player_id: str) -> tuple[bool, Optional[str]]:
        """
        Reconnect a player to a game

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        game = self.get_game(game_id)
        if not game:
            return False, "Game not found"

        # Check if player exists in game
        existing_player = next((p for p in game.players if p.id == player_id), None)
        if existing_player:
            existing_player.is_connected = True
            logger.info(f"Player {existing_player.name} ({player_id}) reconnected to game {game_id}")
            return True, None
        else:
            return False, "Player not found in game"

    def disconnect_player(self, game_id: str, player_id: str) -> tuple[bool, Optional[str]]:
        """
        Mark a player as disconnected

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        game = self.get_game(game_id)
        if not game:
            return False, "Game not found"

        player = next((p for p in game.players if p.id == player_id), None)
        if player:
            player.is_connected = False
            logger.info(f"Player {player.name} ({player_id}) disconnected from game {game_id}")
            return True, None
        else:
            return False, "Player not found in game"

    def start_game(self, game_id: str, player_id: str, player_count: int) -> tuple[bool, Optional[str]]:
        """
        Start a game

        Args:
            game_id: The game ID
            player_id: The player requesting to start the game
            player_count: Desired number of players (will add bots if needed)

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        game = self.get_game(game_id)
        if not game:
            return False, "Game not found"

        # Check if the requesting player is in the game
        player = next((p for p in game.players if p.id == player_id), None)
        if not player:
            return False, "You are not in this game"

        # Validate player count
        if player_count < 3 or player_count > 8:
            return False, "Player count must be between 3 and 8"

        # Add bots if needed to reach the requested player count
        bot_names = ["Alice", "Bob", "Carol", "Dan", "Eve", "Frank", "Grace"]
        while len(game.players) < player_count:
            bot_id = str(uuid.uuid4())
            bot_name = bot_names[
                len([p for p in game.players if p.is_bot]) % len(bot_names)
            ]

            bot_player = Player(id=bot_id, name=bot_name, is_bot=True, is_connected=True)
            if not game.add_player(bot_player):
                # Max players reached
                break
            logger.info(f"Added bot {bot_name} to game {game_id}")

        # Try to start the game
        if game.start_game():
            logger.info(f"Game {game_id} started with {len(game.players)} players")
            return True, None
        else:
            return False, "Cannot start game (insufficient players or wrong status)"

    def check_timers(self) -> list[str]:
        """
        Check all game timers and return list of games with expired timers

        Returns:
            List of game IDs with expired timers
        """
        expired_games = []
        for game_id, game in list(self.active_games.items()):
            if game.check_time_expired():
                logger.info(f"Timer expired for game {game_id}")
                expired_games.append(game_id)
        return expired_games


# Global service instance
game_service = GameService()
