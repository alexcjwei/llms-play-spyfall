"""Parallel bot query system for tool-based bot interactions"""
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from models import Game, GameStatus
from services.tool_selector import tool_selector
from services.tool_prompt_builder import build_bot_tool_prompt, get_action_context
from tools.game_actions import TOOL_FUNCTIONS

logger = logging.getLogger(__name__)


@dataclass
class BotResponse:
    """Represents a bot's response with tool calls"""
    bot_id: str
    tool_calls: List[Dict[str, Any]]
    success: bool
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
                    success=False,
                    error=str(response)
                ))
            else:
                bot_responses.append(response)

        return bot_responses

    async def _query_single_bot(self, game: Game, bot_id: str) -> BotResponse:
        """
        Query a single bot with their available tools.

        Args:
            game: The current game instance
            bot_id: ID of the bot to query

        Returns:
            Bot response with tool calls
        """
        try:
            # Get available tools for this bot
            available_tools = tool_selector.get_available_tools(game, bot_id)

            if not available_tools:
                logger.debug(f"No tools available for bot {bot_id}")
                return BotResponse(bot_id=bot_id, tool_calls=[], success=True)

            # Build prompt
            action_context = get_action_context(game, bot_id)
            prompt = build_bot_tool_prompt(game, bot_id, action_context)

            # Query LLM with tools
            response = await self.llm_service.query_bot_with_tools(
                prompt=prompt,
                bot_id=bot_id,
                available_tools=available_tools
            )

            if response and response.get('tool_calls'):
                tool_calls = response['tool_calls']
                logger.info(f"Bot {bot_id} made {len(tool_calls)} tool calls")
                return BotResponse(bot_id=bot_id, tool_calls=tool_calls, success=True)
            else:
                logger.warning(f"Bot {bot_id} made no tool calls")
                return BotResponse(bot_id=bot_id, tool_calls=[], success=True)

        except Exception as e:
            logger.error(f"Error querying bot {bot_id}: {e}")
            return BotResponse(bot_id=bot_id, tool_calls=[], success=False, error=str(e))

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
                    else:
                        # Known tool but not handled in categorization - add to ask_calls as fallback
                        ask_calls.append((response.bot_id, tool_call))

        # Process in priority order: [guess_location, accuse, ask, answer]

        # 1. Process guess_location (ends game immediately if successful)
        for bot_id, tool_call in guess_location_calls:
            success, error = await self._execute_tool_call(game, bot_id, tool_call)
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

            if valid_accuse_calls:
                # Process only the first valid accusation
                bot_id, tool_call = valid_accuse_calls[0]
                success, error = await self._execute_tool_call(game, bot_id, tool_call)
                if success:
                    actions_taken.append({
                        'bot_id': bot_id,
                        'action': 'accuse',
                        'details': tool_call.get('parameters', {})
                    })
                    accusation_made = True
                elif error:
                    errors.append(error)

                # Log ignored accusations
                if len(valid_accuse_calls) > 1:
                    ignored_bots = [bot_id for bot_id, _ in valid_accuse_calls[1:]]
                    logger.info(f"Ignored simultaneous accusations from bots: {ignored_bots}")

        # 3. Process ask (advances game turn)
        for bot_id, tool_call in ask_calls:
            success, error = await self._execute_tool_call(game, bot_id, tool_call)
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
            success, error = await self._execute_tool_call(game, bot_id, tool_call)
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
            success, error = await self._execute_tool_call(game, bot_id, tool_call)
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


# Will be initialized with dependencies in main.py
parallel_bot_service: Optional[ParallelBotService] = None