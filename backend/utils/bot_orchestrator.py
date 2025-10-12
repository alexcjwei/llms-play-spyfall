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
        self.parallel_bot_service = None
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
            logger.error("Parallel bot service not available - bot actions cannot be processed")

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
            # Log error but don't fallback - let the game continue with human players

    def _schedule_next_turn_if_needed(self, game):
        """Schedule next turn or bot actions if needed."""
        # If it's still a bot's turn after parallel actions, schedule another round
        current_player = next((p for p in game.players if p.id == game.current_turn), None)
        if current_player and current_player.is_bot:
            # Check if the bot has available tools or new events to process
            from services.bot_message_history import get_bot_history
            from services.tool_selector import tool_selector

            bot_history = get_bot_history(current_player.id)
            available_tools = tool_selector.get_available_tools(game, current_player.id)

            if bot_history:
                # Bot has been initialized, check if there are new events or available tools
                last_seen_index = bot_history.get("last_seen_event_index", 0)
                has_new_events = len(game.events) > last_seen_index
                has_tools = len(available_tools) > 0

                if has_new_events or has_tools:
                    # Bot has new events to process or tools to use, schedule another round
                    reason = []
                    if has_new_events:
                        reason.append(f"{len(game.events) - last_seen_index} new events")
                    if has_tools:
                        reason.append(f"{len(available_tools)} available tools")
                    logger.info(f"Bot {current_player.id} has {', '.join(reason)}, scheduling action")
                    self.schedule_parallel_bot_action(game.id, delay=1)
                else:
                    logger.info(f"Bot {current_player.id} has no new events or tools, waiting for game state change")
            else:
                # Bot not yet initialized, schedule first query
                logger.info(f"Bot {current_player.id} not initialized, scheduling first query")
                self.schedule_parallel_bot_action(game.id, delay=1)
        elif game.status in [GameStatus.VOTING, GameStatus.END_OF_ROUND_VOTING]:
            # In voting state, use parallel bot system for voting
            logger.info(f"Game {game.id} in voting state - using parallel voting system")
            self.schedule_parallel_bot_action(game.id, delay=1)
        # If it's a human's turn, wait for human action



# Global orchestrator instance
bot_orchestrator = BotOrchestrator()
