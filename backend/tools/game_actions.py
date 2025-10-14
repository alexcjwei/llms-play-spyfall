"""Tools for game actions taken by bots"""
import logging
from models import GameStatus
from models.commands import (
    AskQuestionCommand, AnswerCommand, AccuseCommand, VoteCommand,
    GuessLocationCommand, EndOfRoundAccuseCommand, EndOfRoundVoteCommand
)

logger = logging.getLogger(__name__)

ask_tool = {
        "name": "ask",
        "description": "Ask another player a question. Non-spies: The spy is listening -- DO NOT ask questions that reveal the location to the spy",
        "input_schema": {
            "type": "object",
            "properties": {
                "thought": {"type": "string", "description": "Your private thoughts, reasoning, and strategy"},
                "question": {"type": "string", "description": "Brief (1 sentence) question to the target"},
                "target": {"type": "string", "description": "ID of the player to ask (CANNOT be the last player that questioned you)"}
            },
            "required": ["thought", "question", "target"]
        }
    }

def ask(game, bot_id: str, thought: str, question: str, target: str) -> bool:
    """Ask a question to another player"""
    # Create command
    command = AskQuestionCommand(
        player_id=bot_id,
        target_player_id=target,
        question=question
    )

    # Process through state machine
    result = game.process_event(command)

    if result.success:
        logger.info(f"Bot {bot_id} asked {target}: {question}")
    else:
        logger.warning(f"Bot {bot_id} failed to ask question: {result.error}")

    return result.success

answer_tool = {
        "name": "answer",
        "description": "Answer the question just asked to you. Non-spies: the SPY is listening -- DO NOT answer with phrases that reveal the location",
        "input_schema": {
            "type": "object",
            "properties": {
                "thought": {"type": "string", "description": "Your private thoughts, reasoning, and strategy"},
                "answer": {"type": "string", "description": "Brief (1-2 sentence) answer. DO NOT ask a counter-question"}
            },
            "required": ["thought", "answer"]
        }
    }

def answer(game, bot_id: str, thought: str, answer: str) -> bool:
    """Answer the question just asked to this bot"""
    # Create command
    command = AnswerCommand(
        player_id=bot_id,
        answer=answer
    )

    # Process through state machine
    result = game.process_event(command)

    if result.success:
        logger.info(f"Bot {bot_id} answered: {answer}")
    else:
        logger.warning(f"Bot {bot_id} failed to answer: {result.error}")

    return result.success

accuse_tool = {
        "name": "accuse",
        "description": "Accuse another player of being a spy. Stops the game timer and forces a vote. May only be used once",
        "input_schema": {
            "type": "object",
            "properties": {
                "thought": {"type": "string", "description": "Your private thoughts, reasoning, and strategy"},
                "target": {"type": "string", "description": "ID of the player to accuse and vote guilty. If left empty, accusation will not be made"}
            },
            "required": ["thought"]
        }
    }

def accuse(game, bot_id: str, thought: str, target: str = "") -> bool:
    """Accuse another player of being a spy"""
    # If no target specified, bot chooses not to accuse
    if not target or target.strip() == "":
        logger.info(f"Bot {bot_id} chose not to accuse anyone")
        return False

    # Create appropriate command based on game state
    if game.status == GameStatus.END_OF_ROUND_VOTING:
        command = EndOfRoundAccuseCommand(
            player_id=bot_id,
            accused_id=target
        )
    else:
        command = AccuseCommand(
            player_id=bot_id,
            accused_id=target
        )

    # Process through state machine
    result = game.process_event(command)

    if result.success:
        if game.status == GameStatus.END_OF_ROUND_VOTING:
            logger.info(f"Bot {bot_id} made end-of-round accusation against {target}")
        else:
            logger.info(f"Bot {bot_id} accused {target} of being the spy")
    else:
        logger.warning(f"Bot {bot_id} failed to accuse: {result.error}")

    return result.success

vote_tool = {
        "name": "vote",
        "description": "Vote on whether the accused player is guilty of being the spy. The accused player does not have a vote. The spy wins if any non-spy is voted guilty. The non-spies win only if the spy is voted guilty. Non-spies should be 80% sure when voting guilty. If there is a majority vote for guilty, the game ends immediately and the winner is revealed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "thought": {"type": "string", "description": "Your private thoughts, reasoning, and strategy"},
                "guilty": {"type": "boolean", "description": "True to vote this player as the spy, false otherwise"},
            },
            "required": ["thought", "guilty"]
        }
    }

def vote(game, bot_id: str, thought: str, guilty: bool) -> bool:
    """Vote on the current accusation"""
    # Create appropriate command based on game state
    if game.status == GameStatus.END_OF_ROUND_VOTING:
        command = EndOfRoundVoteCommand(
            player_id=bot_id,
            vote=guilty
        )
    else:
        command = VoteCommand(
            player_id=bot_id,
            vote=guilty
        )

    # Process through state machine
    result = game.process_event(command)

    if result.success:
        logger.info(f"Bot {bot_id} voted {'guilty' if guilty else 'innocent'} on accusation")
    else:
        logger.warning(f"Bot {bot_id} failed to vote: {result.error}")

    return result.success

guess_location_tool = {
        "name": "guess_location",
        "description": "Guess the location. Reveals yourself as the spy and ends the game. You win if correct and lose if not. Do not guess if you are not 80 percent sure or higher",
        "input_schema": {
            "type": "object",
            "properties": {
                "thought": {"type": "string", "description": "Your private thoughts, reasoning, and strategy"},
                "location": {"type": "string", "description": "The game location, matching the case. If empty, guess will not be made"}
            },
            "required": ["thought"]
        }
    }

def guess_location(game, bot_id: str, thought: str, location: str = "") -> bool:
    """Guess the location as the spy, ending the game"""
    # If no location specified, bot chooses not to guess
    if not location or location.strip() == "":
        logger.info(f"Bot {bot_id} chose not to guess the location")
        return False

    # Create command
    command = GuessLocationCommand(
        player_id=bot_id,
        location=location
    )

    # Process through state machine
    result = game.process_event(command)

    if result.success:
        logger.info(f"Spy bot {bot_id} guessed location: {location}")
    else:
        logger.warning(f"Bot {bot_id} failed to guess location: {result.error}")

    return result.success


# List of all available tools for easy reference
ALL_TOOLS = [ask_tool, answer_tool, accuse_tool, guess_location_tool, vote_tool]

# Tool name to function mapping for easy dispatch
TOOL_FUNCTIONS = {
    "ask": ask,
    "answer": answer,
    "accuse": accuse,
    "guess_location": guess_location,
    "vote": vote
}