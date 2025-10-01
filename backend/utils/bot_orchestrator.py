"""Bot orchestration for managing bot actions and scheduling"""
import logging
import asyncio
from typing import Dict, Optional

from models import GameStatus

logger = logging.getLogger(__name__)


class BotOrchestrator:
    """Orchestrates bot actions and schedules async tasks"""

    def __init__(self):
        self.pending_tasks: Dict[str, asyncio.Task] = {}  # game_id -> pending async task
        # Will be injected from main.py to avoid circular imports
        self.bot_service = None
        self.game_service = None
        self.connection_manager = None

    def cancel_pending_task(self, game_id: str):
        """Cancel any pending task for the given game."""
        if game_id in self.pending_tasks:
            task = self.pending_tasks[game_id]
            if not task.done():
                task.cancel()
            del self.pending_tasks[game_id]
            logger.info(f"Cancelled pending task for game {game_id}")

    def schedule_task(self, game_id: str, task: asyncio.Task):
        """Schedule a new task for the given game, cancelling any existing task."""
        self.cancel_pending_task(game_id)  # Cancel existing task first
        self.pending_tasks[game_id] = task
        logger.info(f"Scheduled new task for game {game_id}")

    def schedule_next_bot_action(self, game_id: str, delay: int = 2):
        """Schedule the next bot action with a delay."""
        task = asyncio.create_task(self._delayed_bot_turn(game_id, delay))
        self.schedule_task(game_id, task)

    async def _delayed_bot_turn(self, game_id: str, delay: int = 2):
        """Delayed bot turn handling with state checking."""
        if delay > 0:
            await asyncio.sleep(delay)

        # Check if game still exists
        game = self.game_service.get_game(game_id)
        if not game:
            logger.info(f"delayed_bot_turn: Game {game_id} not found after delay")
            return

        # Only proceed if game allows bot actions
        if game.status not in [
            GameStatus.IN_PROGRESS,
            GameStatus.VOTING,
            GameStatus.END_OF_ROUND_VOTING,
        ]:
            logger.info(
                f"delayed_bot_turn: Game {game_id} not in valid state for bot actions (status: {game.status})"
            )
            return

        # For IN_PROGRESS games, don't act if clock is stopped (voting states expect clock to be stopped)
        if game.status == GameStatus.IN_PROGRESS and game.clock_stopped:
            logger.info(
                f"delayed_bot_turn: Game {game_id} clock stopped during IN_PROGRESS"
            )
            return

        # Route to appropriate handler
        if game.status == GameStatus.VOTING or game.status == GameStatus.END_OF_ROUND_VOTING:
            # First check if a bot needs to make an accusation (end of round)
            if game.status == GameStatus.END_OF_ROUND_VOTING and not game.current_accusation:
                success, error = await self.bot_service.handle_bot_end_of_round_accusation(game)
                if success:
                    await self.connection_manager.send_game_state(game_id)
                    # Schedule voting for this accusation
                    self.schedule_next_bot_action(game_id, delay=0)
                elif error and "should vote" not in error.lower():
                    logger.info(f"Bot end-of-round accusation: {error}")
                return

            # Handle voting
            votes_cast, errors = await self.bot_service.handle_bot_voting(game)
            if votes_cast > 0:
                await self.connection_manager.send_game_state(game_id)

                # If we're in end-of-round voting and vote resolution moved to next accuser, schedule bot logic
                if (
                    game.status == GameStatus.END_OF_ROUND_VOTING
                    and not game.current_accusation
                ):
                    logger.info(f"Vote resolution complete, scheduling bot logic for next accuser")
                    self.schedule_next_bot_action(game_id, delay=0)

        elif game.status == GameStatus.IN_PROGRESS:
            # Handle Q&A turn
            success, error = await self.bot_service.handle_bot_turn(game)
            if success:
                await self.connection_manager.send_game_state(game_id)
                # Schedule next bot action
                self.schedule_next_bot_action(game_id)
            elif error and "not a bot's turn" not in error.lower():
                logger.info(f"Bot turn handling: {error}")


# Global orchestrator instance
bot_orchestrator = BotOrchestrator()
