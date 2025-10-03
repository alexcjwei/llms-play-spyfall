"""Service for determining available tools for each bot based on game state"""
import logging
from typing import List, Dict, Any
from models import Game, GameStatus
from tools.game_actions import ask_tool, answer_tool, accuse_tool, guess_location_tool, vote_tool

logger = logging.getLogger(__name__)


class ToolSelector:
    """Determines which tools are available to each bot based on game state and bot status"""

    @staticmethod
    def get_available_tools(game: Game, bot_id: str) -> List[Dict[str, Any]]:
        """
        Get the list of available tools for a specific bot based on current game state.

        Tool availability rules:
        1. Bot's turn to ask: [ask_tool, accuse_tool] + guess_location_tool (if spy)
        2. Bot's turn to answer: [answer_tool, accuse_tool] + guess_location_tool (if spy)
        3. Not bot's turn: [] + guess_location_tool (if spy) + accuse_tool (if haven't accused this round)

        Args:
            game: The current game instance
            bot_id: ID of the bot to get tools for

        Returns:
            List of tool dictionaries available to this bot
        """
        available_tools = []

        # Get bot player
        bot_player = next((p for p in game.players if p.id == bot_id), None)
        if not bot_player or not bot_player.is_bot:
            logger.warning(f"Player {bot_id} is not a bot or doesn't exist")
            return []

        # Only provide tools during active gameplay or voting
        if game.status not in [GameStatus.IN_PROGRESS, GameStatus.VOTING, GameStatus.END_OF_ROUND_VOTING]:
            return []

        # Handle voting phases
        if game.status in [GameStatus.VOTING, GameStatus.END_OF_ROUND_VOTING]:
            # During voting, only provide vote tool to bots who can vote
            if game.current_accusation and bot_id != game.current_accusation.accused_id:
                # Check if bot hasn't voted yet
                if bot_id not in game.current_accusation.votes:
                    available_tools.append(vote_tool)
                    logger.debug(f"Bot {bot_id} can vote on current accusation")
                else:
                    logger.debug(f"Bot {bot_id} has already voted")
            else:
                logger.debug(f"Bot {bot_id} cannot vote (is accused or no accusation)")
            return available_tools

        # Handle regular gameplay (IN_PROGRESS)
        is_bot_turn = game.current_turn == bot_id
        is_spy = game.spy_id == bot_id

        # If it's the bot's turn, determine if they need to ask or answer
        if is_bot_turn:
            last_message = game.messages[-1] if game.messages else None
            if (last_message and
                last_message.type == "question" and
                last_message.to_id == bot_id):
                # Bot needs to answer a question
                logger.debug(f"Bot {bot_id} turn - needs to answer")
                available_tools.append(answer_tool)
                available_tools.append(accuse_tool)
            else:
                # Bot needs to ask a question
                logger.debug(f"Bot {bot_id} turn - needs to ask")
                available_tools.append(ask_tool)
                available_tools.append(accuse_tool)
        else:
            # Not the bot's turn - only spy can guess location, non-accused can accuse
            logger.debug(f"Not bot {bot_id} turn")

            # Add accuse tool if bot hasn't accused this round
            if not bot_player.has_accused_this_round:
                available_tools.append(accuse_tool)

        # Spy can always guess location (if game is in progress)
        if is_spy:
            available_tools.append(guess_location_tool)

        logger.debug(f"Bot {bot_id} available tools: {[tool['name'] for tool in available_tools]}")
        return available_tools

    @staticmethod
    def should_query_bot(game: Game, bot_id: str) -> bool:
        """
        Determine if a bot should be queried (has any available tools).

        Args:
            game: The current game instance
            bot_id: ID of the bot to check

        Returns:
            True if bot should be queried, False otherwise
        """
        available_tools = ToolSelector.get_available_tools(game, bot_id)
        should_query = len(available_tools) > 0

        logger.debug(f"Should query bot {bot_id}: {should_query}")
        return should_query

    @staticmethod
    def get_bots_to_query(game: Game) -> List[str]:
        """
        Get list of bot IDs that should be queried in the current game state.

        Args:
            game: The current game instance

        Returns:
            List of bot IDs that have available tools
        """
        bots_to_query = []

        for player in game.players:
            if player.is_bot and ToolSelector.should_query_bot(game, player.id):
                bots_to_query.append(player.id)

        logger.info(f"Bots to query: {bots_to_query}")
        return bots_to_query


# Global instance
tool_selector = ToolSelector()