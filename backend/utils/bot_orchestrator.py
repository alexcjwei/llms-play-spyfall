"""Bot orchestration for managing bot actions and scheduling"""
import logging
import asyncio
from typing import Dict, Optional, List

from models import GameStatus

logger = logging.getLogger(__name__)


class BotOrchestrator:
    """Orchestrates bot actions and schedules async tasks"""

    def __init__(self):
        self.pending_tasks: Dict[str, asyncio.Task] = {}  # game_id -> pending async task
        # Will be injected from main.py to avoid circular imports
        self.bot_service = None  # Legacy bot service (will be deprecated)
        self.parallel_bot_service = None  # New parallel bot service
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

    def cancel_pending_tasks(self, game_id: str):
        """Alias for cancel_pending_task to match main.py usage."""
        self.cancel_pending_task(game_id)

    def schedule_task(self, game_id: str, task: asyncio.Task):
        """Schedule a new task for the given game, cancelling any existing task."""
        self.cancel_pending_task(game_id)  # Cancel existing task first
        self.pending_tasks[game_id] = task
        logger.info(f"Scheduled new task for game {game_id}")

    def schedule_next_bot_action(self, game_id: str, delay: int = 2):
        """Schedule the next bot action with a delay."""
        task = asyncio.create_task(self._delayed_bot_turn(game_id, delay))
        self.schedule_task(game_id, task)

    def schedule_parallel_bot_action(self, game_id: str, delay: int = 2):
        """Schedule parallel bot querying after a turn completion."""
        task = asyncio.create_task(self._delayed_parallel_bot_action(game_id, delay))
        self.schedule_task(game_id, task)

    async def _delayed_parallel_bot_action(self, game_id: str, delay: int = 2):
        """Delayed parallel bot action handling with state checking."""
        if delay > 0:
            await asyncio.sleep(delay)

        # Check if game still exists
        game = self.game_service.get_game(game_id)
        if not game:
            logger.info(f"Parallel bot action: Game {game_id} not found after delay")
            return

        # Only proceed if game allows bot actions
        if game.status not in [GameStatus.IN_PROGRESS, GameStatus.VOTING, GameStatus.END_OF_ROUND_VOTING]:
            logger.info(f"Parallel bot action: Game {game_id} not in valid state (status: {game.status})")
            return

        # Use new parallel bot service
        if self.parallel_bot_service:
            await self._handle_parallel_bot_actions(game)
        else:
            logger.warning("Parallel bot service not available, falling back to legacy behavior")
            await self._legacy_bot_turn(game_id, delay=0)

    async def _handle_parallel_bot_actions(self, game):
        """Handle parallel bot actions using the new system."""
        try:
            # Query all bots in parallel
            logger.info(f"Starting parallel bot query for game {game.id}")
            bot_responses = await self.parallel_bot_service.query_all_bots(game)

            if not bot_responses:
                logger.info(f"No bot responses for game {game.id}")
                return

            # Process responses and update game state
            result = await self.parallel_bot_service.process_bot_responses(game, bot_responses)

            # Log actions taken
            if result.actions_taken:
                logger.info(f"Game {game.id} - Bot actions taken: {[action['action'] for action in result.actions_taken]}")
            if result.errors:
                logger.warning(f"Game {game.id} - Bot action errors: {result.errors}")

            # Send updated game state to clients
            if result.actions_taken:
                await self.connection_manager.send_game_state(game.id)

            # Check if voting occurred and handle continuation
            if any(action['action'] == 'vote' for action in result.actions_taken):
                logger.info(f"Game {game.id} - Votes cast, checking if more voting needed")
                # After votes, check if still in voting mode and if more bots need to vote
                if game.status in [GameStatus.VOTING, GameStatus.END_OF_ROUND_VOTING]:
                    # Still in voting, schedule another round if bots can still vote
                    self.schedule_parallel_bot_action(game.id, delay=1)
                else:
                    # Voting resolved, game state changed
                    logger.info(f"Game {game.id} - Voting resolved, game state: {game.status}")
                    if game.status == GameStatus.IN_PROGRESS:
                        # Game resumed normal play
                        self._schedule_next_turn_if_needed(game)
                return

            # Handle game state transitions
            if result.game_ended:
                logger.info(f"Game {game.id} ended due to bot action")
                # Send final game state before ending
                await self.connection_manager.send_game_state(game.id)
                return

            if result.accusation_made:
                logger.info(f"Game {game.id} - Accusation made, scheduling voting with parallel system")
                # Accusation was made, game is now in voting state
                # Schedule parallel bot actions for voting
                self.schedule_parallel_bot_action(game.id, delay=1)
                return

            # Check if we need to move to next turn or handle any pending actions
            self._schedule_next_turn_if_needed(game)

        except Exception as e:
            logger.error(f"Error in parallel bot actions for game {game.id}: {e}")
            # Fallback to legacy system on error
            await self._legacy_bot_turn(game.id, delay=0)

    def _schedule_next_turn_if_needed(self, game):
        """Schedule next turn or bot actions if needed."""
        # If it's still a bot's turn after parallel actions, schedule another round
        current_player = next((p for p in game.players if p.id == game.current_turn), None)
        if current_player and current_player.is_bot:
            # Still a bot's turn, schedule another parallel bot action
            self.schedule_parallel_bot_action(game.id, delay=1)
        elif game.status in [GameStatus.VOTING, GameStatus.END_OF_ROUND_VOTING]:
            # In voting state, use parallel bot system for voting
            logger.info(f"Game {game.id} in voting state - using parallel voting system")
            self.schedule_parallel_bot_action(game.id, delay=1)
        # If it's a human's turn, wait for human action

    async def _legacy_bot_turn(self, game_id: str, delay: int = 2):
        """Legacy bot turn handling (fallback for old system)."""
        if delay > 0:
            await asyncio.sleep(delay)

        # Check if game still exists
        game = self.game_service.get_game(game_id)
        if not game:
            logger.info(f"Legacy bot turn: Game {game_id} not found after delay")
            return

        # Only proceed if game allows bot actions
        if game.status not in [
            GameStatus.IN_PROGRESS,
            GameStatus.VOTING,
            GameStatus.END_OF_ROUND_VOTING,
        ]:
            logger.info(
                f"Legacy bot turn: Game {game_id} not in valid state for bot actions (status: {game.status})"
            )
            return

        # For IN_PROGRESS games, don't act if clock is stopped (voting states expect clock to be stopped)
        if game.status == GameStatus.IN_PROGRESS and game.clock_stopped:
            logger.info(
                f"Legacy bot turn: Game {game_id} clock stopped during IN_PROGRESS"
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

    async def _delayed_bot_turn(self, game_id: str, delay: int = 2):
        """Wrapper for legacy bot turn handling."""
        await self._legacy_bot_turn(game_id, delay)


# Global orchestrator instance
bot_orchestrator = BotOrchestrator()
