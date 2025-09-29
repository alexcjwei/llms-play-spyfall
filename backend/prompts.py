"""
Prompt templates for LLM-powered bot behaviors in Spyfall
"""
import json
from typing import List, Dict, Any, Optional


class PromptFormatter:
    """Modular components for shared prompt formatting functionality"""

    @staticmethod
    def get_player_by_id(game_state: Dict[str, Any], player_id: str) -> Dict[str, Any]:
        """Get player data by ID with validation"""
        player = next((p for p in game_state["players"] if p["id"] == player_id), None)
        if not player:
            raise ValueError(f"Player {player_id} not found in game state")
        return player

    @staticmethod
    def build_role_context(is_spy: bool, location: str = "", role: str = "") -> str:
        """Build role-specific context for spy vs non-spy players"""
        if is_spy:
            return "You are the SPY. You don't know the location and must figure it out without being detected."
        else:
            return f"You know the location is '{location}' and your role is '{role}'. Try to identify the spy."

    @staticmethod
    def build_player_mapping(game_state: Dict[str, Any], target_ids: List[str]) -> str:
        """Build formatted list of available target players"""
        mapping = ""
        for player in game_state["players"]:
            if player["id"] in target_ids:
                mapping += f"- {player['id']}: {player['name']}\n"
        return mapping

    @staticmethod
    def format_qa_history(game_state: Dict[str, Any], limit: Optional[int] = None, include_header: bool = True) -> str:
        """Format Q&A message history with optional limit"""
        messages = game_state.get("messages", [])
        if limit:
            messages = messages[-limit:]

        if not messages:
            return ""

        qa_history = "Q&A History:\n" if include_header else ""
        for msg in messages:
            from_name = next((p["name"] for p in game_state["players"] if p["id"] == msg["from"]), msg["from"])
            to_name = next((p["name"] for p in game_state["players"] if p["id"] == msg.get("to", "")), msg.get("to", "all"))
            qa_history += f"- From {from_name} to {to_name}: {msg['content']}\n"

        return qa_history

    @staticmethod
    def build_json_instruction(format_example: str) -> str:
        """Build consistent JSON response instruction"""
        return f"IMPORTANT: Respond with ONLY valid JSON, no additional text or explanation:\n\n{format_example}"


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
    bot_player = PromptFormatter.get_player_by_id(game_state, bot_player_id)
    bot_name = bot_player["name"]

    is_spy = game_state.get("isSpy", False)
    location = game_state.get("location", "Unknown")
    role = game_state.get("role", "Unknown")

    player_mapping = PromptFormatter.build_player_mapping(game_state, available_target_ids)
    qa_history = PromptFormatter.format_qa_history(game_state, limit=6, include_header=True)

    role_context = PromptFormatter.build_role_context(is_spy, location, role)
    json_instruction = PromptFormatter.build_json_instruction('{"target_id": "player_id", "question": "your question", "reasoning": "brief explanation (private, will not be shared)" }')

    prompt = f"""You are {bot_name} playing Spyfall. {role_context}

{qa_history}

Available players to question:
{player_mapping}

Strategy:
- Spy: Ask questions to learn the location without revealing ignorance
- Non-spy: Ask questions that would be easy for location-knowers but hard for spies

Choose a target player ID and generate an appropriate question.

{json_instruction}"""

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
    bot_player = PromptFormatter.get_player_by_id(game_state, bot_player_id)
    questioner = PromptFormatter.get_player_by_id(game_state, questioner_id)

    bot_name = bot_player["name"]
    questioner_name = questioner["name"]
    is_spy = game_state.get("isSpy", False)
    location = game_state.get("location", "Unknown")
    role = game_state.get("role", "Unknown")

    qa_history = PromptFormatter.format_qa_history(game_state)
    if qa_history:
        qa_history += "\n"

    if is_spy:
        role_context = "You are the SPY. You don't know the location. Answer carefully to avoid detection while trying to learn clues."
    else:
        role_context = f"You know the location is '{location}' and your role is '{role}'. Answer naturally but watch for spy behavior."

    json_instruction = PromptFormatter.build_json_instruction('{"answer": "your answer", "reasoning": "brief explanation (private, will not be shared)"}')

    prompt = f"""You are {bot_name} playing Spyfall. {role_context}

{qa_history}{questioner_name} asked you: "{question}"

If you're the spy, be careful not to reveal your ignorance. If you know the location, answer in a way that makes sense for your role without revealing it to the spy.

{json_instruction}"""

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
    bot_player = PromptFormatter.get_player_by_id(game_state, bot_player_id)
    bot_name = bot_player["name"]

    is_spy = game_state.get("isSpy", False)
    location = game_state.get("location", "Unknown")
    role = game_state.get("role", "Unknown")

    player_mapping = PromptFormatter.build_player_mapping(game_state, potential_target_ids)
    qa_analysis = PromptFormatter.format_qa_history(game_state, include_header=True)
    if qa_analysis:
        qa_analysis = qa_analysis.replace("Q&A History:", "Q&A Analysis:")

    if is_spy:
        role_context = "You are the SPY. Consider accusing someone to deflect suspicion or if you think you've been found out."
    else:
        role_context = f"You know the location is '{location}'. Look for players who gave vague, evasive, or inconsistent answers."

    json_instruction = PromptFormatter.build_json_instruction('{"should_accuse": true/false, "target_id": "player_id or null", "reasoning": "brief explanation"}')

    prompt = f"""You are {bot_name} playing Spyfall. {role_context}

{qa_analysis}

Players you can accuse:
{player_mapping}

Analyze the Q&A history. Should you make an accusation? If yes, who seems most suspicious?

{json_instruction}"""

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
    bot_player = PromptFormatter.get_player_by_id(game_state, bot_player_id)
    bot_name = bot_player["name"]

    is_spy = game_state.get("isSpy", False)
    location = game_state.get("location", "Unknown")
    role = game_state.get("role", "Unknown")

    # Get accusation details
    accusation = game_state.get("currentAccusation", {})
    accuser_id = accusation.get("accuser", "")
    accuser = PromptFormatter.get_player_by_id(game_state, accuser_id) if accuser_id else None
    accuser_name = accuser["name"] if accuser else "Unknown"

    qa_history = PromptFormatter.format_qa_history(game_state)

    if is_spy:
        role_context = "You are the SPY. You don't know the location. Vote strategically to deflect suspicion or eliminate threats."
    else:
        role_context = f"You know the location is '{location}' and your role is '{role}'. Vote based on who seems most likely to be the spy."

    json_instruction = PromptFormatter.build_json_instruction('{"vote_guilty": true/false, "reasoning": "brief explanation of your decision"}')

    prompt = f"""You are {bot_name} playing Spyfall. {role_context}

{qa_history}

{accuser_name} has accused {accused_name} of being the spy. You must vote GUILTY ({accused_name} is the spy) or INNOCENT ({accused_name} is not the spy).

{json_instruction}"""

    return prompt
