"""
Prompt templates for LLM-powered bot behaviors in Spyfall
"""
import json
from typing import List, Dict, Any


def build_question_prompt(
    game_state: Dict[str, Any],
    bot_player_id: str,
    available_target_ids: List[str]
) -> str:
    """
    Build prompt for generating a question from a bot player

    Args:
        game_state: Current game state
        bot_player_id: ID of the bot player asking the question
        available_target_ids: List of player IDs that can be questioned

    Returns:
        Formatted prompt string
    """
    bot_player = next((p for p in game_state["players"] if p["id"] == bot_player_id), None)
    if not bot_player:
        raise ValueError(f"Bot player {bot_player_id} not found in game state")

    bot_name = bot_player["name"]
    is_spy = game_state.get("isSpy", False)
    location = game_state.get("location", "Unknown")
    role = game_state.get("role", "Unknown")

    # Build player mapping for available targets
    player_mapping = ""
    for player in game_state["players"]:
        if player["id"] in available_target_ids:
            player_mapping += f"- {player['id']}: {player['name']}\n"

    # Get recent Q&A context
    recent_messages = game_state.get("messages", [])[-6:]  # Last 6 messages for context
    qa_history = ""
    if recent_messages:
        qa_history = "Recent Q&A:\n"
        for msg in recent_messages:
            from_name = next((p["name"] for p in game_state["players"] if p["id"] == msg["from"]), msg["from"])
            to_name = next((p["name"] for p in game_state["players"] if p["id"] == msg.get("to", "")), msg.get("to", "all"))
            qa_history += f"- {from_name} → {to_name}: {msg['content']}\n"

    role_context = ""
    if is_spy:
        role_context = f"You are the SPY. You don't know the location and must figure it out without being detected."
    else:
        role_context = f"You know the location is '{location}' and your role is '{role}'. Try to identify the spy."

    prompt = f"""You are {bot_name} playing Spyfall. {role_context}

{qa_history}

Available players to question:
{player_mapping}

Strategy:
- Spy: Ask questions to learn the location without revealing ignorance
- Non-spy: Ask questions that would be easy for location-knowers but hard for spies

Choose a target player ID and generate an appropriate question.

IMPORTANT: Respond with ONLY valid JSON, no additional text or explanation:

{{"target_id": "player_id", "question": "your question"}}"""

    return prompt


def build_answer_prompt(
    game_state: Dict[str, Any],
    bot_player_id: str,
    question: str,
    questioner_id: str
) -> str:
    """
    Build prompt for generating an answer to a question

    Args:
        game_state: Current game state
        bot_player_id: ID of the bot player answering
        question: The question being asked
        questioner_id: ID of the player asking the question

    Returns:
        Formatted prompt string
    """
    bot_player = next((p for p in game_state["players"] if p["id"] == bot_player_id), None)
    questioner = next((p for p in game_state["players"] if p["id"] == questioner_id), None)

    if not bot_player:
        raise ValueError(f"Bot player {bot_player_id} not found in game state")
    if not questioner:
        raise ValueError(f"Questioner {questioner_id} not found in game state")

    bot_name = bot_player["name"]
    questioner_name = questioner["name"]
    is_spy = game_state.get("isSpy", False)
    location = game_state.get("location", "Unknown")
    role = game_state.get("role", "Unknown")

    # Get all Q&A history for context
    messages = game_state.get("messages", [])
    qa_history = ""
    if messages:
        qa_history = "Q&A History:\n"
        for msg in messages:
            from_name = next((p["name"] for p in game_state["players"] if p["id"] == msg["from"]), msg["from"])
            to_name = next((p["name"] for p in game_state["players"] if p["id"] == msg.get("to", "")), msg.get("to", "all"))
            qa_history += f"- {from_name} → {to_name}: {msg['content']}\n"
        qa_history += "\n"

    role_context = ""
    if is_spy:
        role_context = "You are the SPY. You don't know the location. Answer carefully to avoid detection while trying to learn clues."
    else:
        role_context = f"You know the location is '{location}' and your role is '{role}'. Answer naturally but watch for spy behavior."

    prompt = f"""You are {bot_name} playing Spyfall. {role_context}

{qa_history}{questioner_name} asked you: "{question}"

If you're the spy, be careful not to reveal your ignorance. If you know the location, answer in a way that makes sense for your role without revealing it to the spy.

IMPORTANT: Respond with ONLY valid JSON, no additional text or explanation:

{{"answer": "your answer"}}"""

    return prompt


def build_accusation_prompt(
    game_state: Dict[str, Any],
    bot_player_id: str,
    potential_target_ids: List[str]
) -> str:
    """
    Build prompt for deciding whether to make an accusation and against whom

    Args:
        game_state: Current game state
        bot_player_id: ID of the bot player considering an accusation
        potential_target_ids: List of player IDs that can be accused

    Returns:
        Formatted prompt string
    """
    bot_player = next((p for p in game_state["players"] if p["id"] == bot_player_id), None)
    if not bot_player:
        raise ValueError(f"Bot player {bot_player_id} not found in game state")

    bot_name = bot_player["name"]
    is_spy = game_state.get("isSpy", False)
    location = game_state.get("location", "Unknown")
    role = game_state.get("role", "Unknown")

    # Build player mapping for potential targets
    player_mapping = ""
    for player in game_state["players"]:
        if player["id"] in potential_target_ids:
            player_mapping += f"- {player['id']}: {player['name']}\n"

    # Analyze Q&A history for suspicious behavior
    messages = game_state.get("messages", [])
    qa_analysis = "Q&A Analysis:\n"
    for msg in messages:
        from_name = next((p["name"] for p in game_state["players"] if p["id"] == msg["from"]), msg["from"])
        to_name = next((p["name"] for p in game_state["players"] if p["id"] == msg.get("to", "")), msg.get("to", "all"))
        qa_analysis += f"- {from_name} → {to_name}: {msg['content']}\n"

    role_context = ""
    if is_spy:
        role_context = "You are the SPY. Consider accusing someone to deflect suspicion or if you think you've been found out."
    else:
        role_context = f"You know the location is '{location}'. Look for players who gave vague, evasive, or inconsistent answers."

    prompt = f"""You are {bot_name} playing Spyfall. {role_context}

{qa_analysis}

Players you can accuse:
{player_mapping}

Analyze the Q&A history. Should you make an accusation? If yes, who seems most suspicious?

Consider:
- Vague or evasive answers
- Answers that don't fit the location
- Players asking fishing questions
- Inconsistent behavior

Respond with JSON:

{{"should_accuse": true/false, "target_id": "player_id or null", "reasoning": "brief explanation"}}"""

    return prompt


def build_voting_prompt(
    game_state: Dict[str, Any],
    bot_player_id: str,
    accused_id: str,
    accused_name: str
) -> str:
    """
    Build prompt for deciding how to vote on an accusation

    Args:
        game_state: Current game state
        bot_player_id: ID of the bot player voting
        accused_id: ID of the player being accused
        accused_name: Name of the player being accused

    Returns:
        Formatted prompt string
    """
    bot_player = next((p for p in game_state["players"] if p["id"] == bot_player_id), None)
    if not bot_player:
        raise ValueError(f"Bot player {bot_player_id} not found in game state")

    bot_name = bot_player["name"]
    is_spy = game_state.get("isSpy", False)
    location = game_state.get("location", "Unknown")
    role = game_state.get("role", "Unknown")

    # Get accusation details
    accusation = game_state.get("currentAccusation", {})
    accuser_id = accusation.get("accuser", "")
    accuser = next((p for p in game_state["players"] if p["id"] == accuser_id), None)
    accuser_name = accuser["name"] if accuser else "Unknown"

    # Get all Q&A history for context
    messages = game_state.get("messages", [])
    qa_history = ""
    if messages:
        qa_history = "Q&A History:\n"
        for msg in messages:
            from_name = next((p["name"] for p in game_state["players"] if p["id"] == msg["from"]), msg["from"])
            to_name = next((p["name"] for p in game_state["players"] if p["id"] == msg.get("to", "")), msg.get("to", "all"))
            qa_history += f"- {from_name} → {to_name}: {msg['content']}\n"

    role_context = ""
    if is_spy:
        role_context = "You are the SPY. You don't know the location. Vote strategically to deflect suspicion or eliminate threats."
    else:
        role_context = f"You know the location is '{location}' and your role is '{role}'. Vote based on who seems most likely to be the spy."

    prompt = f"""You are {bot_name} playing Spyfall. {role_context}

{qa_history}

{accuser_name} has accused {accused_name} of being the spy. You must vote GUILTY (they are the spy) or INNOCENT (they are not the spy).

Consider all players' behavior in the Q&A history:
- Who gave vague or evasive answers?
- Who asked fishing questions to learn the location?
- Who seemed unfamiliar with the location?
- Who behaved most suspiciously overall?

IMPORTANT: Respond with ONLY valid JSON, no additional text or explanation:

{{"vote_guilty": true/false, "reasoning": "brief explanation of your decision"}}"""

    return prompt
