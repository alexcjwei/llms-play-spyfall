"""Bot message history management for persistent conversations with Claude API"""
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Global storage for bot message histories
# Structure: {bot_id: {"system": str, "messages": List[Dict], "last_seen_event_index": int}}
bot_message_histories: Dict[str, Dict[str, Any]] = {}

# System prompt for all bots
SYSTEM_PROMPT = "You are an AI agent playing the social deduction game Spyfall."


def initialize_bot_history(bot_id: str, initial_message: Dict[str, Any], initial_event_index: int = 0):
    """
    Initialize message history for a bot.

    Args:
        bot_id: ID of the bot
        initial_message: First user message dict with role and content
        initial_event_index: Starting event index (usually 0 or len(game.events))
    """
    bot_message_histories[bot_id] = {
        "system": SYSTEM_PROMPT,
        "messages": [initial_message],
        "last_seen_event_index": initial_event_index
    }
    logger.info(f"Initialized message history for bot {bot_id}")


def get_bot_history(bot_id: str) -> Optional[Dict[str, Any]]:
    """
    Get bot's message history.

    Args:
        bot_id: ID of the bot

    Returns:
        Bot's history dict or None if not found
    """
    return bot_message_histories.get(bot_id)


def append_assistant_message(bot_id: str, content: List[Dict]):
    """
    Append assistant's response to history.

    Args:
        bot_id: ID of the bot
        content: Response content array from Claude API
    """
    if bot_id not in bot_message_histories:
        logger.warning(f"Cannot append assistant message - bot {bot_id} has no history")
        return

    bot_message_histories[bot_id]["messages"].append({
        "role": "assistant",
        "content": content
    })
    logger.debug(f"Appended assistant message to bot {bot_id} history")


def append_user_message(bot_id: str, content):
    """
    Append user message to history.

    Args:
        bot_id: ID of the bot
        content: User message content (can be str or List[Dict])
    """
    if bot_id not in bot_message_histories:
        logger.warning(f"Cannot append user message - bot {bot_id} has no history")
        return

    bot_message_histories[bot_id]["messages"].append({
        "role": "user",
        "content": content
    })
    logger.debug(f"Appended user message to bot {bot_id} history")


def update_last_seen_event_index(bot_id: str, index: int):
    """
    Update the last seen event index for a bot.

    Args:
        bot_id: ID of the bot
        index: New event index
    """
    if bot_id not in bot_message_histories:
        logger.warning(f"Cannot update event index - bot {bot_id} has no history")
        return

    bot_message_histories[bot_id]["last_seen_event_index"] = index
    logger.debug(f"Updated bot {bot_id} last_seen_event_index to {index}")


def get_messages(bot_id: str) -> List[Dict[str, Any]]:
    """
    Get bot's message list.

    Args:
        bot_id: ID of the bot

    Returns:
        List of messages or empty list if not found
    """
    history = bot_message_histories.get(bot_id)
    return history["messages"] if history else []


def get_system_prompt(bot_id: str) -> str:
    """
    Get bot's system prompt.

    Args:
        bot_id: ID of the bot

    Returns:
        System prompt string
    """
    history = bot_message_histories.get(bot_id)
    return history["system"] if history else SYSTEM_PROMPT


def get_last_seen_event_index(bot_id: str) -> int:
    """
    Get bot's last seen event index.

    Args:
        bot_id: ID of the bot

    Returns:
        Last seen event index or 0 if not found
    """
    history = bot_message_histories.get(bot_id)
    return history["last_seen_event_index"] if history else 0


def clear_bot_history(bot_id: str):
    """
    Clear history for a specific bot.

    Args:
        bot_id: ID of the bot
    """
    if bot_id in bot_message_histories:
        del bot_message_histories[bot_id]
        logger.info(f"Cleared history for bot {bot_id}")


def clear_all_histories():
    """Clear all bot histories (useful for testing or game reset)"""
    bot_message_histories.clear()
    logger.info("Cleared all bot message histories")


def get_all_bot_ids() -> List[str]:
    """
    Get list of all bot IDs with history.

    Returns:
        List of bot IDs
    """
    return list(bot_message_histories.keys())
