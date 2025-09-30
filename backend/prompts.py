"""
Prompt templates for LLM-powered bot behaviors in Spyfall
"""
from typing import List, Dict, Any, Optional
from models import LOCATIONS, Location


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
        spy = "- You are the SPY\n" if is_spy else ""
        return f"{spy}- Location: {location}\n- Role: {role}"

    @staticmethod
    def build_player_mapping(game_state: Dict[str, Any], target_ids: List[str]) -> str:
        """Build formatted list of available target players"""
        mappings = ""
        for player in game_state["players"]:
            if player["id"] in target_ids:
                mappings += f"- {player['name']}: {player['id']}\n"
        return mappings

    @staticmethod
    def format_qa_history(game_state: Dict[str, Any], limit: Optional[int] = None) -> str:
        """Format Q&A message history with optional limit"""
        messages = game_state.get("messages", [])
        if limit:
            messages = messages[-limit:]

        if not messages:
            return ""

        qa_history = ""
        for msg in messages:
            from_name = next((p["name"] for p in game_state["players"] if p["id"] == msg["from"]), msg["from"])
            to_name = next((p["name"] for p in game_state["players"] if p["id"] == msg.get("to", "")), msg.get("to", "all"))
            qa_history += f"- From {from_name} to {to_name}: \"{msg['content']}\"\n"

        return qa_history

    @staticmethod
    def build_xml_instruction(xml_format_example: str) -> str:
        """Build consistent XML response instruction with thinking"""
        return f"""

{xml_format_example}"""
    
    @staticmethod
    def get_game_description() -> str:
        return """Spyfall is a social deduction game. Each round, players are assigned a location and role. One player is the spy who doesn't know the location.
- **The spy’s objective** is to avoid exposure until the end of a given round or identify the current location.
- **The non-spies’ objective** is to establish consensus on the identity of the spy and expose him or her.

Strategies:
- The objectives of the non-spy players are to identify the spy and avoid revealing their location. Therefore, the non-spies should refrain from being too explicit in their questions: (for example, “How much cash did the robbers steal yesterday?” The spy will instantly identify the location as the bank). However, when a player’s questions and answers are too vague, other players might start suspecting them of being the spy, enabling the real spy to win.
- The spy’s objective is to listen as carefully as possible to what the other players say and do their best to avoid blowing their cover while also trying to identify the location before eight minutes have passed. A spy who doesn’t attempt to guess the location is taking a risk — it is entirely possible that the other players will identify them after discussion and voting."""

    @staticmethod
    def format_game_locations(locations: List[Location]) -> str:
        def format_location(location: Location):
            return f"- {location.name}"
        return "\n".join(map(format_location, locations))


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
    qa_history = PromptFormatter.format_qa_history(game_state, limit=6)

    role_context = PromptFormatter.build_role_context(is_spy, location, role)
    game_description = PromptFormatter.get_game_description()
    game_locations = PromptFormatter.format_game_locations(LOCATIONS)
    xml_instruction = PromptFormatter.build_xml_instruction("""<scratchpad>
[Your reasoning process here - consider the game state, your role, and strategic implications]
</scratchpad>
<target_id>player_id</target_id>
<question>your question</question>""")

    prompt = f"""You are {bot_name} playing a game of Spyfall. It is your turn to ask another player a question. 

GAME DESCRIPTION:
{game_description}

LIST OF ALL GAME LOCATIONS:
{game_locations}

YOUR CARD:
{role_context}

PREVIOUS Q&A:
{qa_history}

WHO YOU CAN ASK:
You must choose the id of ONE of these players
{player_mapping}

YOUR TASK:
Think through your decision in the scratchpad, then provide your target player and brief question in the following format:
{xml_instruction}"""

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
    role_context = PromptFormatter.build_role_context(is_spy, location, role)
    game_description = PromptFormatter.get_game_description()
    game_locations = PromptFormatter.format_game_locations(LOCATIONS)
    xml_instruction = PromptFormatter.build_xml_instruction("""<scratchpad>
[Your reasoning process here - consider the game state, your role, and strategic implications]
</scratchpad><answer>your answer</answer>""")

    prompt = f"""You are {bot_name} playing Spyfall. It is your turn to answer another player's question.

GAME DESCRIPTION:
{game_description}

LIST OF ALL GAME LOCATIONS:
{game_locations}

YOUR CARD:
{role_context}

PREVIOUS Q&A:
{qa_history}

QUESTION:
{questioner_name} asked you: "{question}"

YOUR TASK:
Think through your response in the scratchpad, then provide your brief answer in the following format:
{xml_instruction}"""

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
    return "Not implemented."


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
    role_context = PromptFormatter.build_role_context(is_spy, location, role)
    game_description = PromptFormatter.get_game_description()
    game_locations = PromptFormatter.format_game_locations(LOCATIONS)

    xml_instruction = PromptFormatter.build_xml_instruction("""<scratchpad>
[Your reasoning process here - consider the game state, your role, and strategic implications]
</scratchpad><vote_guilty>true</vote_guilty> <!-- or false -->""")

    prompt = f"""You are {bot_name} playing Spyfall and need to vote on an accusation that has been made.
    
GAME DESCRIPTION:
{game_description}

LIST OF ALL GAME LOCATIONS:
{game_locations}

YOUR CARD:
{role_context}

PREVIOUS Q&A:
{qa_history}

ACCUSATION:
{accuser_name} has accused {accused_name} of being the spy.

YOUR TASK:
Think through whether to vote {accused_name} guilty of being the spy, then provide your vote in the following format:
{xml_instruction}"""

    return prompt
