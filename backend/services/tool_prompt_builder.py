"""Prompt builder for tool-based bot interactions"""
import logging
from typing import Dict, Any, List
from models import Game

logger = logging.getLogger(__name__)


def build_bot_tool_prompt(
    game: Game,
    bot_id: str,
    action_context: str = "take your next action"
) -> str:
    """
    Build the base prompt for bot tool-based interactions.

    Args:
        game: The current game instance
        bot_id: ID of the bot player
        action_context: Context for what the bot should do (e.g., "ask a question", "answer the question")

    Returns:
        Formatted prompt string
    """

    # Get bot player
    bot_player = next((p for p in game.players if p.id == bot_id), None)
    if not bot_player:
        raise ValueError(f"Bot {bot_id} not found in game")

    # Get bot's role and location info
    if game.spy_id == bot_id:
        location = "Unknown (You are the spy!)"
        role = "Spy"
    else:
        location = game.location.name if game.location else "Unknown"
        role = bot_player.role.name if bot_player.role else "Unknown"

    # Build player list with question targeting info
    player_list = []
    last_questioner_id = None

    # Find who last asked this bot a question (if any)
    if game.messages:
        for message in reversed(game.messages):
            if message.type == "question" and message.to_id == bot_id:
                last_questioner_id = message.from_id
                break

    for player in game.players:
        if player.id == bot_id:
            player_list.append(f"- {player.name} (ID: {player.id}) - **YOU**")
        elif player.id == last_questioner_id:
            last_questioner = next((p for p in game.players if p.id == last_questioner_id), None)
            last_questioner_name = last_questioner.name if last_questioner else "Unknown"
            player_list.append(f"- {player.name} (ID: {player.id}) - **CANNOT ASK** (just asked you)")
        else:
            player_list.append(f"- {player.name} (ID: {player.id}) - can ask")

    player_name_and_id = "\n".join(player_list)

    # Build Q&A history
    qa_history_lines = []
    if game.messages:
        for message in game.messages:
            from_player = next((p for p in game.players if p.id == message.from_id), None)
            to_player = next((p for p in game.players if p.id == message.to_id), None)

            from_name = from_player.name if from_player else "Unknown"
            to_name = to_player.name if to_player else "Unknown"

            if message.type == "question":
                qa_history_lines.append(f"**{from_name}** asked **{to_name}**: {message.content}")
            elif message.type == "answer":
                qa_history_lines.append(f"**{from_name}** answered: {message.content}")

    qa_history = "\n".join(qa_history_lines) if qa_history_lines else "No questions or answers yet."

    # Build accusation context if game is in voting mode
    accusation_context = ""
    if game.current_accusation:
        accuser = next((p for p in game.players if p.id == game.current_accusation.accuser_id), None)
        accused = next((p for p in game.players if p.id == game.current_accusation.accused_id), None)

        accuser_name = accuser.name if accuser else "Unknown"
        accused_name = accused.name if accused else "Unknown"

        accusation_context = f"""
**{accuser_name}** has accused **{accused_name}** of being the spy!
"""
    # Format the prompt
    prompt = f"""You are a cunning, observant, and socially aware AI playing the social deduction game Spyfall. You are playing as {bot_player.name} and it is your turn to {action_context}.

Spyfall background:
<background>
Spyfall is a social deduction game. Each round, players are assigned a location and role. One player is the spy who doesn't know the location.
- **The spy's objective** is to avoid exposure until the end of a given round or identify the current location. Their object is to listen as carefully as possible to what the other players say and do their best to avoid blowing their cover while also trying to identify the location. A spy who doesn't attempt to guess the location is taking a risk — it is entirely possible that the other players will identify them after discussion and voting.
- **The non-spies' objective** is to establish consensus on the identity of the spy and expose him or her while not revealing their location. Therefore, the non-spies should refrain from being too explicit in their questions: (for example, "How much cash did the robbers steal yesterday?" The spy will instantly identify the location as the bank).

<rules>
- Questions are asked once; no follow-up questions are allowed.
- The player who answers the question proceeds to ask any other player a question of their own, but cannot ask a question of the player who just asked them a question.
</rules>

The spy knows the location is one of the following:
<locations>
- Airplane
- Amusement Park
- Bank
- Beach
- Carnival
- Casino
- Circus Tent
- Corporate Party
- Crusader Army
- Day Spa
- Embassy
- Hospital
- Hotel
- Military Base
- Movie Studio
- Nightclub
- Ocean Liner
- Passenger Train
- Pirate Ship
- Police Station
- Polar Station
- Restaurant
- School
- Service Station
- Space Station
- Submarine
- Supermarket
- Theater
- University
- Zoo
</locations>
</background>

Use this game context to respond:
<context>
This is the role card you were dealt at the beginning of the game:
<role_card>
Location: {location}
Role: {role}
</role_card>

These are all the players and their player_id:
<players>
{player_name_and_id}
</players>

This is the game log up to this point, which may include your previous actions:
<game_events>
{qa_history}
{accusation_context}
</game_events>
</context>

<instructions>
Consider the game context to take the next game action.
Respond naturally and concisely.
Your action should help you get closer to your goal of winning the game.
</instructions>"""

    return prompt


def get_action_context(game: Game, bot_id: str) -> str:
    """
    Get the appropriate action context based on game state.

    Args:
        game: The current game instance
        bot_id: ID of the bot player

    Returns:
        Action context string
    """
    from models import GameStatus

    # Handle voting phases
    if game.status in [GameStatus.VOTING, GameStatus.END_OF_ROUND_VOTING]:
        if game.current_accusation and bot_id != game.current_accusation.accused_id:
            if bot_id not in game.current_accusation.votes:
                return "vote on the current accusation"
            else:
                return "wait for other players to vote"
        elif game.current_turn == bot_id:
            return "accuse another player of being the spy"
        else:
            return "wait for voting to complete"

    # Check if it's the bot's turn
    if game.current_turn == bot_id:
        # Check if bot needs to answer a question
        last_message = game.messages[-1] if game.messages else None
        if (last_message and
            last_message.type == "question" and
            last_message.to_id == bot_id):
            return "answer the question asked to you"
        else:
            return "ask a question to another player"
    else:
        return "take your next action"