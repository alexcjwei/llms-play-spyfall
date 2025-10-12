"""Parallel bot query system for tool-based bot interactions"""
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

from models import Game, GameStatus
from services.tool_selector import tool_selector
from services.tool_prompt_builder import build_bot_tool_prompt, get_action_context
from services.bot_message_history import (
    get_bot_history,
    initialize_bot_history,
    append_assistant_message,
    append_user_message,
    update_last_seen_event_index,
    get_system_prompt
)
from tools.game_actions import TOOL_FUNCTIONS

logger = logging.getLogger(__name__)


@dataclass
class BotResponse:
    """Represents a bot's response with tool calls"""
    bot_id: str
    tool_calls: List[Dict[str, Any]]  # Now includes 'id', 'name', 'parameters'
    response_content: List[Dict] = None  # Full content array from API
    events_at_query_time: int = 0  # Number of events when bot was queried
    success: bool = True
    error: Optional[str] = None


@dataclass
class GameUpdateResult:
    """Result of processing bot responses and updating game state"""
    actions_taken: List[Dict[str, Any]]
    errors: List[str]
    game_ended: bool = False
    accusation_made: bool = False


class ParallelBotService:
    """Service for querying all bots in parallel and processing their responses"""

    def __init__(self, llm_service):
        self.llm_service = llm_service

    async def query_all_bots(self, game: Game) -> List[BotResponse]:
        """
        Query all bots in parallel with their available tools.

        Args:
            game: The current game instance

        Returns:
            List of bot responses
        """
        # Get bots that should be queried
        bots_to_query = tool_selector.get_bots_to_query(game)

        if not bots_to_query:
            logger.info("No bots to query")
            return []

        # Create parallel queries
        query_tasks = []
        for bot_id in bots_to_query:
            task = self._query_single_bot(game, bot_id)
            query_tasks.append(task)

        # Execute all queries in parallel
        logger.info(f"Querying {len(query_tasks)} bots in parallel")
        responses = await asyncio.gather(*query_tasks, return_exceptions=True)

        # Process responses and handle exceptions
        bot_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                bot_id = bots_to_query[i]
                logger.error(f"Error querying bot {bot_id}: {response}")
                bot_responses.append(BotResponse(
                    bot_id=bot_id,
                    tool_calls=[],
                    events_at_query_time=0,  # Unknown due to exception
                    success=False,
                    error=str(response)
                ))
            else:
                bot_responses.append(response)

        return bot_responses

    async def _query_single_bot(self, game: Game, bot_id: str) -> BotResponse:
        """
        Query a single bot with their available tools using message history.

        Args:
            game: The current game instance
            bot_id: ID of the bot to query

        Returns:
            Bot response with tool calls and content
        """
        try:
            # Capture event count at query time for proper history tracking
            events_at_query_time = len(game.events)

            # Get available tools for this bot
            available_tools = tool_selector.get_available_tools(game, bot_id)

            if not available_tools:
                logger.debug(f"No tools available for bot {bot_id}")
                return BotResponse(
                    bot_id=bot_id,
                    tool_calls=[],
                    response_content=[],
                    events_at_query_time=events_at_query_time,
                    success=True
                )

            # Get or initialize bot history
            bot_history = get_bot_history(bot_id)

            if not bot_history:
                # First query - build initial message with background, role, players, and instruction
                action_context = get_action_context(game, bot_id)
                initial_content = build_bot_tool_prompt(game, bot_id, action_context)

                # Initialize history with first user message
                initialize_bot_history(
                    bot_id=bot_id,
                    initial_message={"role": "user", "content": initial_content},
                    initial_event_index=len(game.events)
                )
                bot_history = get_bot_history(bot_id)
                logger.info(f"Initialized message history for bot {bot_id}")
            else:
                # Subsequent query - append new events and instruction as user message
                last_index = bot_history["last_seen_event_index"]
                new_events = game.events[last_index:]

                if new_events:
                    # Format new events
                    events_text = self._format_events(new_events)
                    instruction = get_action_context(game, bot_id)

                    # Build user message content with events and instruction
                    user_content = f"{events_text}\n\n<instructions>\n{instruction}\n</instructions>"
                    append_user_message(bot_id, user_content)
                    logger.debug(f"Appended {len(new_events)} new events to bot {bot_id} history")

                    # Note: last_seen_event_index will be updated AFTER tool execution
                    # in _update_message_histories, to include events created by this bot
                else:
                    # No new events - but bot might still have actions to take (e.g., ask after answering)
                    if available_tools:
                        # Bot has tools available, send just the instruction
                        instruction = get_action_context(game, bot_id)
                        user_content = f"<instructions>\n{instruction}\n</instructions>"
                        append_user_message(bot_id, user_content)
                        logger.debug(f"No new events for bot {bot_id}, but has {len(available_tools)} tools - sending instruction")
                    else:
                        # No new events and no tools - don't query the bot
                        logger.debug(f"No new events or tools for bot {bot_id}, skipping query")
                        return BotResponse(
                            bot_id=bot_id,
                            tool_calls=[],
                            response_content=[],
                            events_at_query_time=events_at_query_time,
                            success=True
                        )

            # Query with full message history
            response = await self.llm_service.query_bot_with_tools(
                messages=bot_history["messages"],
                bot_id=bot_id,
                available_tools=available_tools,
                system=bot_history["system"]
            )

            if response and response.get('tool_calls'):
                tool_calls = response['tool_calls']
                response_content = response.get('response_content', [])
                logger.info(f"Bot {bot_id} made {len(tool_calls)} tool calls")
                return BotResponse(
                    bot_id=bot_id,
                    tool_calls=tool_calls,
                    response_content=response_content,
                    events_at_query_time=events_at_query_time,
                    success=True
                )
            else:
                logger.warning(f"Bot {bot_id} made no tool calls")
                return BotResponse(
                    bot_id=bot_id,
                    tool_calls=[],
                    response_content=[],
                    events_at_query_time=events_at_query_time,
                    success=True
                )

        except Exception as e:
            logger.error(f"Error querying bot {bot_id}: {e}")
            return BotResponse(
                bot_id=bot_id,
                tool_calls=[],
                response_content=[],
                events_at_query_time=len(game.events),
                success=False,
                error=str(e)
            )

    def _format_events(self, events: List) -> str:
        """Format game events for bot consumption"""
        if not events:
            return "No new game events."

        formatted = ["Recent game events:"]
        for event in events:
            formatted.append(f"- {event.formatted_text}")

        return "\n".join(formatted)

    async def process_bot_responses(self, game: Game, responses: List[BotResponse]) -> GameUpdateResult:
        """
        Process bot responses and apply valid actions to game state.

        Tool call priority order: [guess_location, ask, answer, accuse]

        Args:
            game: The current game instance
            responses: List of bot responses

        Returns:
            Game update result
        """
        actions_taken = []
        errors = []
        game_ended = False
        accusation_made = False

        # Track tool execution results by (bot_id, tool_use_id) -> (success, error_msg)
        tool_execution_results: Dict[Tuple[str, str], Tuple[bool, Optional[str]]] = {}

        # Collect all tool calls by priority
        guess_location_calls = []
        ask_calls = []
        answer_calls = []
        accuse_calls = []
        vote_calls = []

        for response in responses:
            if not response.success:
                errors.append(f"Bot {response.bot_id}: {response.error}")
                continue

            for tool_call in response.tool_calls:
                tool_name = tool_call.get('name')
                if tool_name == 'guess_location':
                    guess_location_calls.append((response.bot_id, tool_call))
                elif tool_name == 'ask':
                    ask_calls.append((response.bot_id, tool_call))
                elif tool_name == 'answer':
                    answer_calls.append((response.bot_id, tool_call))
                elif tool_name == 'accuse':
                    accuse_calls.append((response.bot_id, tool_call))
                elif tool_name == 'vote':
                    vote_calls.append((response.bot_id, tool_call))
                else:
                    # Unknown tool - check if it exists in TOOL_FUNCTIONS
                    if tool_name not in TOOL_FUNCTIONS:
                        errors.append(f"Unknown tool: {tool_name}")
                        # Track as failed execution
                        tool_use_id = tool_call.get('id', 'unknown')
                        tool_execution_results[(response.bot_id, tool_use_id)] = (False, f"Unknown tool: {tool_name}")
                    else:
                        # Known tool but not handled in categorization - add to ask_calls as fallback
                        ask_calls.append((response.bot_id, tool_call))

        # Process in priority order: [guess_location, accuse, ask, answer]

        # 1. Process guess_location (ends game immediately if successful)
        for bot_id, tool_call in guess_location_calls:
            tool_use_id = tool_call.get('id', 'unknown')
            success, error = await self._execute_tool_call(game, bot_id, tool_call)
            tool_execution_results[(bot_id, tool_use_id)] = (success, error)

            if success:
                actions_taken.append({
                    'bot_id': bot_id,
                    'action': 'guess_location',
                    'details': tool_call.get('parameters', {})
                })
                game_ended = True
                break  # Game ends, don't process other actions
            elif error:
                errors.append(error)

        if game_ended:
            # Update message histories before returning
            self._update_message_histories(responses, tool_execution_results, game)
            return GameUpdateResult(actions_taken, errors, game_ended, accusation_made)

        # 2. Process accuse (stops timer and forces voting)
        if accuse_calls:
            # Filter out empty accusations (bots choosing not to accuse)
            valid_accuse_calls = []
            for bot_id, tool_call in accuse_calls:
                params = tool_call.get('parameters', {})
                target = params.get('target', '').strip()
                if target:  # Only process if target is specified
                    valid_accuse_calls.append((bot_id, tool_call))
                else:
                    # Track filtered-out accusation as "not executed"
                    tool_use_id = tool_call.get('id', 'unknown')
                    tool_execution_results[(bot_id, tool_use_id)] = (False, "No accusation made (empty target)")

            if valid_accuse_calls:
                # Process only the first valid accusation
                bot_id, tool_call = valid_accuse_calls[0]
                tool_use_id = tool_call.get('id', 'unknown')
                success, error = await self._execute_tool_call(game, bot_id, tool_call)
                tool_execution_results[(bot_id, tool_use_id)] = (success, error)

                if success:
                    actions_taken.append({
                        'bot_id': bot_id,
                        'action': 'accuse',
                        'details': tool_call.get('parameters', {})
                    })
                    accusation_made = True
                elif error:
                    errors.append(error)

                # Log ignored accusations and mark them with priority error
                if len(valid_accuse_calls) > 1:
                    ignored_bots = [bot_id for bot_id, _ in valid_accuse_calls[1:]]
                    logger.info(f"Ignored simultaneous accusations from bots: {ignored_bots}")
                    # Track ignored accusations
                    for ignored_bot_id, ignored_tool_call in valid_accuse_calls[1:]:
                        ignored_tool_id = ignored_tool_call.get('id', 'unknown')
                        tool_execution_results[(ignored_bot_id, ignored_tool_id)] = (False, "Another player's action took priority")

        # 3. Process ask (advances game turn)
        for bot_id, tool_call in ask_calls:
            tool_use_id = tool_call.get('id', 'unknown')
            success, error = await self._execute_tool_call(game, bot_id, tool_call)
            tool_execution_results[(bot_id, tool_use_id)] = (success, error)

            if success:
                actions_taken.append({
                    'bot_id': bot_id,
                    'action': 'ask',
                    'details': tool_call.get('parameters', {})
                })
                break  # Only one ask action per turn
            elif error:
                errors.append(error)

        # 4. Process answer (completes Q&A exchange)
        for bot_id, tool_call in answer_calls:
            tool_use_id = tool_call.get('id', 'unknown')
            success, error = await self._execute_tool_call(game, bot_id, tool_call)
            tool_execution_results[(bot_id, tool_use_id)] = (success, error)

            if success:
                actions_taken.append({
                    'bot_id': bot_id,
                    'action': 'answer',
                    'details': tool_call.get('parameters', {})
                })
                break  # Only one answer per turn
            elif error:
                errors.append(error)

        # 5. Process vote calls (during voting phases)
        for bot_id, tool_call in vote_calls:
            tool_use_id = tool_call.get('id', 'unknown')
            success, error = await self._execute_tool_call(game, bot_id, tool_call)
            tool_execution_results[(bot_id, tool_use_id)] = (success, error)

            if success:
                actions_taken.append({
                    'bot_id': bot_id,
                    'action': 'vote',
                    'details': tool_call.get('parameters', {})
                })
                # Check if voting is complete (game state may have changed)
                if game.status not in [GameStatus.VOTING, GameStatus.END_OF_ROUND_VOTING]:
                    logger.info("Voting completed, game state changed")
                    break
            elif error:
                errors.append(error)

        # Update message histories for all bots that responded
        self._update_message_histories(responses, tool_execution_results, game)

        return GameUpdateResult(actions_taken, errors, game_ended, accusation_made)

    async def _execute_tool_call(self, game: Game, bot_id: str, tool_call: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Execute a single tool call.

        Args:
            game: The current game instance
            bot_id: ID of the bot making the call
            tool_call: Tool call dictionary

        Returns:
            Tuple of (success, error_message)
        """
        tool_name = tool_call.get('name')
        parameters = tool_call.get('parameters', {})

        if tool_name not in TOOL_FUNCTIONS:
            return False, f"Unknown tool: {tool_name}"

        tool_function = TOOL_FUNCTIONS[tool_name]

        try:
            # Execute tool function
            success = tool_function(game, bot_id, **parameters)
            if success:
                return True, None
            else:
                # Tool function returned False, indicating failure
                error_msg = f"Tool {tool_name} failed for bot {bot_id}"
                return False, error_msg
        except Exception as e:
            error_msg = f"Error executing {tool_name} for bot {bot_id}: {e}"
            logger.error(error_msg)
            return False, error_msg

    def _update_message_histories(
        self,
        responses: List[BotResponse],
        tool_execution_results: Dict[Tuple[str, str], Tuple[bool, Optional[str]]],
        game: Game
    ):
        """
        Update message histories for all bots that responded.

        Args:
            responses: List of bot responses
            tool_execution_results: Dict mapping (bot_id, tool_use_id) to (success, error_msg)
            game: Current game instance
        """
        for response in responses:
            if not response.success or not response.response_content:
                continue

            # Append assistant message (bot's response with tool use)
            append_assistant_message(response.bot_id, response.response_content)
            logger.debug(f"Appended assistant message for bot {response.bot_id}")

            # Build tool_results for each tool call
            tool_results = []
            bot_had_successful_tool = False
            for tool_call in response.tool_calls:
                tool_use_id = tool_call.get('id', 'unknown')
                success, error = tool_execution_results.get((response.bot_id, tool_use_id), (True, None))

                if success:
                    bot_had_successful_tool = True

                result_content = "success" if success else f"error: {error}"
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": result_content
                })

            # Append user message with tool results
            append_user_message(response.bot_id, tool_results)
            logger.debug(f"Appended tool results for bot {response.bot_id}")

            # Update last_seen_event_index based on what the bot saw at query time
            # If bot successfully executed a tool (likely creating an event), include current events
            # Otherwise, only include events up to query time (bot will see other bots' events next time)
            if bot_had_successful_tool:
                # Bot created an event, update to current state to avoid seeing own action
                new_last_seen = len(game.events)
            else:
                # Bot created no events, keep at query time so they see events from other bots
                new_last_seen = response.events_at_query_time

            update_last_seen_event_index(response.bot_id, new_last_seen)
            logger.debug(f"Updated bot {response.bot_id} last_seen_event_index to {new_last_seen} (queried at {response.events_at_query_time}, had_success={bot_had_successful_tool})")


# Will be initialized with dependencies in main.py
parallel_bot_service: Optional[ParallelBotService] = None