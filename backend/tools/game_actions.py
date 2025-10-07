"""Tools for game actions taken by bots"""
ask_tool = {
        "name": "ask",
        "description": "Ask another player a question. Non-spies: DO NOT ask questions that might reveal the location to the spy",
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
    from models import Game
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"Bot {bot_id} thinking: {thought}")

    # Validate target is not the bot themselves
    if target == bot_id:
        logger.warning(f"Bot {bot_id} tried to ask themselves a question")
        return False

    # Validate target exists
    target_player = next((p for p in game.players if p.id == target), None)
    if not target_player:
        logger.warning(f"Bot {bot_id} tried to ask non-existent player {target}")
        return False

    # Validate bot can't ask the player who just asked them
    if target == game.last_questioned_by:
        logger.warning(f"Bot {bot_id} tried to ask back the player who just asked them")
        return False

    # Ask the question using existing game logic
    success = game.ask_question(bot_id, target, question)
    if success:
        logger.info(f"Bot {bot_id} asked {target}: {question}")

    return success

answer_tool = {
        "name": "answer",
        "description": "Answer the question just asked to you. Non-spies: DO NOT answer in a way that might reveal the location to the spy",
        "input_schema": {
            "type": "object",
            "properties": {
                "thought": {"type": "string", "description": "Your private thoughts, reasoning, and strategy"},
                "answer": {"type": "string", "description": "Brief (1-2 sentence) answer. Do not ask a counter-question."}
            },
            "required": ["thought", "answer"]
        }
    }

def answer(game, bot_id: str, thought: str, answer: str) -> bool:
    """Answer the question just asked to this bot"""
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"Bot {bot_id} thinking: {thought}")

    # Validate there's a question waiting for this bot to answer
    last_message = game.messages[-1] if game.messages else None
    if not last_message or last_message.type != "question" or last_message.to_id != bot_id:
        logger.warning(f"Bot {bot_id} tried to answer but no question was asked to them")
        return False

    # Answer using existing game logic
    success = game.give_answer(bot_id, answer)
    if success:
        logger.info(f"Bot {bot_id} answered: {answer}")

    return success

accuse_tool = {
        "name": "accuse",
        "description": "Accuse another player of being a spy. Stops the game timer and forces a vote. May only be used once",
        "input_schema": {
            "type": "object",
            "properties": {
                "thought": {"type": "string", "description": "Your private thoughts, reasoning, and strategy"},
                "target": {"type": "string", "description": "ID of the player to accuse and vote guilty. No accusation made if left empty"}
            },
            "required": ["thought"]
        }
    }

def accuse(game, bot_id: str, thought: str, target: str = "") -> bool:
    """Accuse another player of being a spy"""
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"Bot {bot_id} thinking: {thought}")

    # If no target specified, bot chooses not to accuse
    if not target or target.strip() == "":
        logger.info(f"Bot {bot_id} chose not to accuse anyone")
        return False

    # Validate target is not the bot themselves
    if target == bot_id:
        logger.warning(f"Bot {bot_id} tried to accuse themselves")
        return False

    # Validate target exists
    target_player = next((p for p in game.players if p.id == target), None)
    if not target_player:
        logger.warning(f"Bot {bot_id} tried to accuse non-existent player {target}")
        return False

    # Check if bot has already accused this round
    bot_player = next((p for p in game.players if p.id == bot_id), None)
    if bot_player and bot_player.has_accused_this_round:
        logger.warning(f"Bot {bot_id} has already accused this round")
        return False

    # Make accusation using existing game logic
    success = game.stop_clock_for_accusation(bot_id, target)
    if success:
        logger.info(f"Bot {bot_id} accused {target} of being the spy")

    return success

vote_tool = {
        "name": "vote",
        "description": "Vote on whether the accused player is guilty of being the spy.",
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
    from models import GameStatus
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"Bot {bot_id} thinking: {thought}")

    # Check if game is in voting state
    if game.status not in [GameStatus.VOTING, GameStatus.END_OF_ROUND_VOTING]:
        logger.warning(f"Bot {bot_id} tried to vote but game not in voting state")
        return False

    # Check if there's an active accusation
    if not game.current_accusation:
        logger.warning(f"Bot {bot_id} tried to vote but no active accusation")
        return False

    # Check if bot can vote (not the accused player)
    if bot_id == game.current_accusation.accused_id:
        logger.warning(f"Bot {bot_id} tried to vote but is the accused player")
        return False

    # Check if bot has already voted
    if bot_id in game.current_accusation.votes:
        logger.warning(f"Bot {bot_id} has already voted on this accusation")
        return False

    # Cast vote using appropriate game method
    if game.status == GameStatus.VOTING:
        success = game.vote_on_accusation(bot_id, guilty)
    else:  # END_OF_ROUND_VOTING
        success = game.vote_on_end_of_round_accusation(bot_id, guilty)

    if success:
        logger.info(f"Bot {bot_id} voted {'guilty' if guilty else 'innocent'} on accusation")

    return success

guess_location_tool = {
        "name": "guess_location",
        "description": "Guess the location. Reveals yourself as the spy and ends the game. You win if correct and lose if not.",
        "input_schema": {
            "type": "object",
            "properties": {
                "thought": {"type": "string", "description": "Your private thoughts, reasoning, and strategy"},
                "location": {"type": "string", "description": "The game location, matching the case"}
            },
            "required": ["thought", "location"]
        }
    }

def guess_location(game, bot_id: str, thought: str, location: str) -> bool:
    """Guess the location as the spy, ending the game"""
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"Bot {bot_id} thinking: {thought}")

    # Validate the bot is actually the spy
    if game.spy_id != bot_id:
        logger.warning(f"Bot {bot_id} tried to guess location but is not the spy")
        return False

    # Validate location is valid
    from models.location import LOCATIONS
    valid_locations = [loc.name for loc in LOCATIONS]
    if location not in valid_locations:
        logger.warning(f"Bot {bot_id} guessed invalid location: {location}")
        return False

    # Make the guess using existing game logic
    success = game.spy_guess_location(bot_id, location)
    if success:
        logger.info(f"Spy bot {bot_id} guessed location: {location}")

    return success


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