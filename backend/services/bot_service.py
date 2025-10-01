"""Bot behavior orchestration service"""
import logging
import random
import asyncio
from typing import Optional

from models import Game, GameStatus

logger = logging.getLogger(__name__)


class BotService:
    """Service for orchestrating bot actions in games"""

    def __init__(self, llm_service, prompt_service):
        self.llm_service = llm_service
        self.prompt_service = prompt_service

    async def handle_bot_turn(self, game: Game) -> tuple[bool, Optional[str]]:
        """
        Handle a bot's turn for Q&A

        Args:
            game: The game instance

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        if game.status not in [GameStatus.IN_PROGRESS, GameStatus.VOTING, GameStatus.END_OF_ROUND_VOTING]:
            return False, f"Game not in valid state for bot actions (status: {game.status})"

        # Handle voting states
        if game.status == GameStatus.VOTING:
            return False, "Bot should be voting, not taking Q&A turn"
        elif game.status == GameStatus.END_OF_ROUND_VOTING:
            return False, "Bot should be making end-of-round accusation, not taking Q&A turn"

        # Don't handle bot actions if game is not in progress or clock is stopped
        if game.status != GameStatus.IN_PROGRESS or game.clock_stopped:
            return False, f"Game not in progress or clock stopped (status: {game.status}, clock_stopped: {game.clock_stopped})"

        current_player = next((p for p in game.players if p.id == game.current_turn), None)

        # Only proceed if it's a bot's turn for Q&A
        if not current_player or not current_player.is_bot:
            return False, "Not a bot's turn"

        # Check if bot needs to answer a question
        last_message = game.messages[-1] if game.messages else None

        if (
            last_message
            and last_message.type == "question"
            and last_message.to_id == current_player.id
        ):
            # Bot needs to answer
            return await self._handle_bot_answer(game, current_player, last_message)
        else:
            # Bot needs to ask a question
            return await self._handle_bot_question(game, current_player)

    async def _handle_bot_answer(self, game: Game, current_player, last_message) -> tuple[bool, Optional[str]]:
        """Handle bot answering a question"""
        game_state_dict = game.to_player_dict(current_player.id)
        question = last_message.content
        questioner_id = last_message.from_id

        try:
            answer = await self.llm_service.generate_answer(
                game_state_dict,
                current_player.id,
                question,
                questioner_id,
                self.prompt_service.build_answer_prompt
            )

            if answer:
                logger.info(f"Claude generated answer for {current_player.name}: {answer}")
                if game.give_answer(current_player.id, answer):
                    logger.info(f"Bot {current_player.name} gave Claude-generated answer")
                    return True, None
                else:
                    return False, "Failed to give Claude-generated answer"
            else:
                # Fallback to generic answer if Claude fails
                logger.warning(f"Claude failed to generate answer, using fallback")
                fallback_answer = "I think it's interesting here."
                if game.give_answer(current_player.id, fallback_answer):
                    logger.info(f"Bot {current_player.name} gave fallback answer")
                    return True, None
                else:
                    return False, "Failed to give fallback answer"
        except Exception as e:
            logger.error(f"Error generating answer with Claude: {e}")
            # Fallback to generic answer
            fallback_answer = "I think it's interesting here."
            if game.give_answer(current_player.id, fallback_answer):
                logger.info(f"Bot {current_player.name} gave fallback answer")
                return True, None
            else:
                return False, f"Error generating answer: {e}"

    async def _handle_bot_question(self, game: Game, current_player) -> tuple[bool, Optional[str]]:
        """Handle bot asking a question"""
        # Get available players (exclude self and the person who just asked this bot)
        available_players = [
            p
            for p in game.players
            if p.id != current_player.id and p.id != game.last_questioned_by
        ]

        if not available_players:
            return False, f"No available players to ask (last_questioned_by={game.last_questioned_by})"

        # Use Claude API to generate question
        available_target_ids = [p.id for p in available_players]
        game_state_dict = game.to_player_dict(current_player.id)

        try:
            result = await self.llm_service.generate_question(
                game_state_dict,
                current_player.id,
                available_target_ids,
                self.prompt_service.build_question_prompt
            )

            if result:
                target_id, question = result
                logger.info(f"Claude generated question for {current_player.name} -> {target_id}: {question}")
                if game.ask_question(current_player.id, target_id, question):
                    logger.info(f"Bot {current_player.name} asked Claude-generated question to {target_id}")
                    return True, None
                else:
                    return False, "Failed to ask Claude-generated question"
            else:
                # Fallback to random question if Claude fails
                logger.warning(f"Claude failed to generate question, using fallback")
                target = random.choice(available_players)
                fallback_question = "What do you think about this place?"
                if game.ask_question(current_player.id, target.id, fallback_question):
                    logger.info(f"Bot {current_player.name} asked fallback question to {target.name}")
                    return True, None
                else:
                    return False, "Failed to ask fallback question"
        except Exception as e:
            logger.error(f"Error generating question with Claude: {e}")
            # Fallback to random question
            target = random.choice(available_players)
            fallback_question = "What do you think about this place?"
            if game.ask_question(current_player.id, target.id, fallback_question):
                logger.info(f"Bot {current_player.name} asked fallback question to {target.name}")
                return True, None
            else:
                return False, f"Error generating question: {e}"

    async def handle_bot_voting(self, game: Game) -> tuple[int, list[str]]:
        """
        Handle bots voting on accusations

        Returns:
            Tuple of (number of votes cast, list of errors)
        """
        if not game.current_accusation or game.status not in [GameStatus.VOTING, GameStatus.END_OF_ROUND_VOTING]:
            return 0, ["No active accusation or invalid game state"]

        # Find bots who haven't voted yet
        bots_to_vote = []
        for player in game.players:
            if (
                player.is_bot
                and player.id != game.current_accusation.accused_id  # Accused can't vote
                and player.id not in game.current_accusation.votes
            ):  # Haven't voted yet
                bots_to_vote.append(player)

        errors = []
        votes_cast = 0

        # Make each bot vote using LLM decision
        for bot in bots_to_vote:
            # Add small delay between bot votes to make it feel more natural
            await asyncio.sleep(1)

            # Get LLM-based voting decision
            accused_player = next(
                (p for p in game.players if p.id == game.current_accusation.accused_id),
                None,
            )
            accused_name = accused_player.name if accused_player else "Unknown"

            vote = await self.llm_service.should_vote_guilty(
                game.to_player_dict(bot.id),
                bot.id,
                game.current_accusation.accused_id,
                accused_name,
                self.prompt_service.build_voting_prompt
            )

            if vote is not None:
                logger.info(f"Bot {bot.name} voting decision: {vote}")
            else:
                # Fallback to random if LLM fails
                vote = random.choice([True, False])
                logger.warning(f"Bot {bot.name} using fallback random vote: {vote}")

            # Use appropriate voting method based on game status
            if game.status == GameStatus.END_OF_ROUND_VOTING:
                success = game.vote_on_end_of_round_accusation(bot.id, vote)
                vote_type = "end-of-round"
            else:
                success = game.vote_on_accusation(bot.id, vote)
                vote_type = "mid-game"

            if success:
                logger.info(f"Bot {bot.name} voted {vote} in {vote_type} voting")
                votes_cast += 1
            else:
                errors.append(f"Failed to record vote for bot {bot.name}")

        return votes_cast, errors

    async def handle_bot_end_of_round_accusation(self, game: Game) -> tuple[bool, Optional[str]]:
        """
        Handle bot making end-of-round accusation when it's their turn

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        if game.status != GameStatus.END_OF_ROUND_VOTING:
            return False, f"Game not in END_OF_ROUND_VOTING status (current: {game.status})"

        # If there's already an accusation, bot should vote instead
        if game.current_accusation:
            return False, "Current accusation exists, bot should vote instead"

        # No active accusation - check if it's a bot's turn to make an accusation
        current_player = next((p for p in game.players if p.id == game.current_turn), None)

        # Only proceed if it's a bot's turn
        if not current_player or not current_player.is_bot:
            return False, "Not a bot's turn"

        # Check if bot has already accused this round
        if current_player.has_accused_this_round:
            return False, f"Bot {current_player.name} has already accused this round"

        # Add delay to simulate thinking
        await asyncio.sleep(2)

        # Bot makes a random accusation (excluding themselves)
        potential_targets = [p for p in game.players if p.id != current_player.id]
        if not potential_targets:
            return False, "No potential targets available"

        target = random.choice(potential_targets)

        logger.info(f"Bot {current_player.name} making end-of-round accusation against {target.name}")

        if game.make_end_of_round_accusation(current_player.id, target.id):
            return True, None
        else:
            return False, f"Failed to make accusation for bot {current_player.name}"


# Will be initialized with dependencies in main.py
bot_service: Optional[BotService] = None
