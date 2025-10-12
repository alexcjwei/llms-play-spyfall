"""
Integration tests for the complete tool-based bot system
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from services.parallel_bot_service import ParallelBotService
from services.llm_service import LLMService
from services.tool_prompt_builder import build_bot_tool_prompt, get_action_context
from services.tool_selector import ToolSelector
from tools.game_actions import ask, answer, accuse, guess_location
from models import Game, Player, GameStatus
from models.player import PlayerRole
from models.location import LOCATIONS
from models.message import GameEvent, create_question_event


@pytest.fixture
def full_game_setup():
    """Create a complete game setup for integration testing"""
    game = Game(id="integration-test")

    # Add players
    human_player = Player(id="human1", name="Alice", is_bot=False)
    bot_player_1 = Player(id="bot1", name="Detective Bot", is_bot=True)
    bot_player_2 = Player(id="bot2", name="Casual Bot", is_bot=True)
    bot_player_3 = Player(id="bot3", name="Analytical Bot", is_bot=True)

    game.players = [human_player, bot_player_1, bot_player_2, bot_player_3]
    game.status = GameStatus.IN_PROGRESS
    game.current_turn = "bot1"
    game.location = LOCATIONS[2]  # Bank
    game.spy_id = "human1"

    # Assign roles
    human_player.role = PlayerRole.SPY
    bot_player_1.role = PlayerRole.INNOCENT
    bot_player_1.location_role = "Teller"
    bot_player_2.role = PlayerRole.INNOCENT
    bot_player_2.location_role = "Security Guard"
    bot_player_3.role = PlayerRole.INNOCENT
    bot_player_3.location_role = "Manager"

    return game


class TestToolIntegration:
    """Integration tests for the complete tool system"""

    def test_ask_tool_integration(self, full_game_setup):
        """Test ask tool integration with game logic"""
        game = full_game_setup

        # Bot1 asks human1 a question
        success = ask(game, "bot1",
                     thought="I need to test if they know about banking procedures",
                     question="What security measures do you think are most important here?",
                     target="human1")

        assert success is True
        assert len(game.events) == 1

        event = game.events[0]
        assert event.player_id == "bot1"
        assert event.content.get("to_id") == "human1"
        assert event.type == "question"
        assert "security measures" in event.content.get("text", "")

        # Turn should advance to human1
        assert game.current_turn == "human1"

    def test_ask_tool_invalid_target(self, full_game_setup):
        """Test ask tool with invalid target"""
        game = full_game_setup

        # Try to ask non-existent player
        success = ask(game, "bot1",
                     thought="I'll try to ask someone who doesn't exist",
                     question="How are you?",
                     target="nonexistent")

        assert success is False
        assert len(game.events) == 0
        assert game.current_turn == "bot1"  # Turn shouldn't advance

    def test_ask_tool_self_target(self, full_game_setup):
        """Test ask tool with self as target"""
        game = full_game_setup

        # Try to ask themselves
        success = ask(game, "bot1",
                     thought="Can I ask myself?",
                     question="How am I doing?",
                     target="bot1")

        assert success is False
        assert len(game.events) == 0

    def test_answer_tool_integration(self, full_game_setup):
        """Test answer tool integration"""
        game = full_game_setup

        # First, add a question that needs answering
        question_event = create_question_event(
            from_player_id="human1",
            from_player_name="Alice",
            to_player_id="bot1",
            to_player_name="Detective Bot",
            question_text="What's your role here?"
        )
        game.events = [question_event]
        game.current_turn = "bot1"
        game.last_questioned_by = "human1"

        # Bot1 answers the question
        success = answer(game, "bot1",
                        thought="I should answer about my banking role",
                        answer="I help customers with their transactions and account inquiries.")

        assert success is True
        assert len(game.events) == 2

        answer_event = game.events[1]
        assert answer_event.player_id == "bot1"
        assert answer_event.type == "answer"
        assert "transactions" in answer_event.content.get("text", "")

    def test_answer_tool_no_question(self, full_game_setup):
        """Test answer tool when no question was asked"""
        game = full_game_setup

        # Try to answer without a question
        success = answer(game, "bot1",
                        thought="I'll try to answer without a question",
                        answer="I like working here.")

        assert success is False
        assert len(game.events) == 0

    def test_accuse_tool_integration(self, full_game_setup):
        """Test accuse tool integration"""
        game = full_game_setup

        # Bot1 accuses human1
        success = accuse(game, "bot1",
                        thought="I think the human is acting suspiciously",
                        target="human1")

        assert success is True
        assert game.current_accusation is not None
        assert game.current_accusation.accuser_id == "bot1"
        assert game.current_accusation.accused_id == "human1"
        assert game.status == GameStatus.VOTING

    def test_accuse_tool_empty_target(self, full_game_setup):
        """Test accuse tool with empty target (choose not to accuse)"""
        game = full_game_setup

        # Bot chooses not to accuse
        success = accuse(game, "bot1",
                        thought="I'm not ready to accuse anyone yet",
                        target="")

        assert success is False
        assert game.current_accusation is None
        assert game.status == GameStatus.IN_PROGRESS

    def test_accuse_tool_already_accused(self, full_game_setup):
        """Test accuse tool when bot has already accused this round"""
        game = full_game_setup

        # Mark bot as having already accused
        bot1 = next(p for p in game.players if p.id == "bot1")
        bot1.has_accused_this_round = True

        success = accuse(game, "bot1",
                        thought="I want to accuse again",
                        target="human1")

        assert success is False

    def test_guess_location_tool_spy(self, full_game_setup):
        """Test guess_location tool for spy"""
        game = full_game_setup

        # Make bot1 the spy
        game.spy_id = "bot1"

        success = guess_location(game, "bot1",
                               thought="I'm confident this is a bank",
                               location="Bank")

        assert success is True
        assert game.status == GameStatus.FINISHED
        assert game.winner == "spy"  # Correct guess

    def test_guess_location_tool_wrong_guess(self, full_game_setup):
        """Test guess_location tool with wrong guess"""
        game = full_game_setup

        # Make bot1 the spy
        game.spy_id = "bot1"

        success = guess_location(game, "bot1",
                               thought="I think this is an airplane",
                               location="Airplane")

        assert success is True
        assert game.status == GameStatus.FINISHED
        assert game.winner == "innocents"  # Wrong guess

    def test_guess_location_tool_non_spy(self, full_game_setup):
        """Test guess_location tool for non-spy"""
        game = full_game_setup

        # Bot1 is not the spy (human1 is)
        success = guess_location(game, "bot1",
                               thought="I'll try to guess",
                               location="Bank")

        assert success is False
        assert game.status == GameStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_full_parallel_bot_flow(self, full_game_setup, monkeypatch):
        """Test complete parallel bot query flow"""
        monkeypatch.setenv("CLAUDE_API_KEY", "test-key")
        game = full_game_setup

        # Set up scenario: human's turn, bots can accuse or spy can guess
        game.current_turn = "human1"

        # Add an event to trigger bot queries
        question_event = create_question_event(
            from_player_id="human1",
            from_player_name="Alice",
            to_player_id="bot1",
            to_player_name="Detective Bot",
            question_text="What do you think?"
        )
        game.events = [question_event]

        # Create LLM service and parallel bot service
        llm_service = LLMService()
        parallel_bot_service = ParallelBotService(llm_service)

        # Mock LLM responses
        def mock_llm_query(messages, bot_id, available_tools, system):
            if bot_id == "bot1":  # Detective Bot - makes accusation
                return {
                    "tool_calls": [{
                        "id": "call_1",
                        "name": "accuse",
                        "parameters": {
                            "thought": "The human seems suspicious based on their answers",
                            "target": "human1"
                        }
                    }],
                    "response_content": [{"type": "tool_use", "id": "call_1", "name": "accuse", "input": {"thought": "The human seems suspicious based on their answers", "target": "human1"}}]
                }
            elif bot_id == "bot2":  # Casual Bot - doesn't accuse
                return {
                    "tool_calls": [{
                        "id": "call_2",
                        "name": "accuse",
                        "parameters": {
                            "thought": "I'm not ready to accuse anyone yet",
                            "target": ""
                        }
                    }],
                    "response_content": [{"type": "tool_use", "id": "call_2", "name": "accuse", "input": {"thought": "I'm not ready to accuse anyone yet", "target": ""}}]
                }
            else:  # bot3 - Analytical Bot - also suspicious
                return {
                    "tool_calls": [{
                        "id": "call_3",
                        "name": "accuse",
                        "parameters": {
                            "thought": "I agree with the detective",
                            "target": "human1"
                        }
                    }],
                    "response_content": [{"type": "tool_use", "id": "call_3", "name": "accuse", "input": {"thought": "I agree with the detective", "target": "human1"}}]
                }

        llm_service.query_bot_with_tools = AsyncMock(side_effect=mock_llm_query)

        # Execute parallel bot queries
        bot_responses = await parallel_bot_service.query_all_bots(game)

        # Process responses
        result = await parallel_bot_service.process_bot_responses(game, bot_responses)

        # Verify results
        assert len(bot_responses) == 3  # All bots were queried
        assert len(result.actions_taken) == 1  # Only first accusation processed
        assert result.actions_taken[0]['action'] == 'accuse'
        assert result.actions_taken[0]['bot_id'] == 'bot1'  # First to accuse
        assert result.accusation_made is True

        # Game state should be updated
        assert game.current_accusation is not None
        assert game.current_accusation.accuser_id == "bot1"
        assert game.current_accusation.accused_id == "human1"

    @pytest.mark.asyncio
    async def test_tool_priority_ordering(self, full_game_setup, monkeypatch):
        """Test that tools are processed in correct priority order"""
        monkeypatch.setenv("CLAUDE_API_KEY", "test-key")
        game = full_game_setup

        # Make bot1 the spy and it's their turn
        game.spy_id = "bot1"
        game.current_turn = "bot1"

        # Add an event to trigger bot queries
        question_event = create_question_event(
            from_player_id="human1",
            from_player_name="Alice",
            to_player_id="bot1",
            to_player_name="Detective Bot",
            question_text="What do you think?"
        )
        game.events = [question_event]

        llm_service = LLMService()
        parallel_bot_service = ParallelBotService(llm_service)

        # Mock bot1 making multiple tool calls in wrong order
        def mock_llm_query(messages, bot_id, available_tools, system):
            if bot_id == "bot1":
                return {
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "name": "accuse",
                            "parameters": {
                                "thought": "I'll accuse someone",
                                "target": "bot2"
                            }
                        },
                        {
                            "id": "call_2",
                            "name": "ask",
                            "parameters": {
                                "thought": "I'll ask a question",
                                "question": "What do you do here?",
                                "target": "human1"
                            }
                        },
                        {
                            "id": "call_3",
                            "name": "guess_location",
                            "parameters": {
                                "thought": "I'll guess the location",
                                "location": "Bank"
                            }
                        }
                    ],
                    "response_content": [
                        {"type": "tool_use", "id": "call_1", "name": "accuse", "input": {"thought": "I'll accuse someone", "target": "bot2"}},
                        {"type": "tool_use", "id": "call_2", "name": "ask", "input": {"thought": "I'll ask a question", "question": "What do you do here?", "target": "human1"}},
                        {"type": "tool_use", "id": "call_3", "name": "guess_location", "input": {"thought": "I'll guess the location", "location": "Bank"}}
                    ]
                }
            else:
                return {"tool_calls": [], "response_content": []}

        llm_service.query_bot_with_tools = AsyncMock(side_effect=mock_llm_query)

        # Execute and process
        bot_responses = await parallel_bot_service.query_all_bots(game)
        result = await parallel_bot_service.process_bot_responses(game, bot_responses)

        # Verify guess_location is processed first and ends game
        assert len(result.actions_taken) == 1
        assert result.actions_taken[0]['action'] == 'guess_location'
        assert result.game_ended == True

    def test_tool_prompt_contextual_accuracy(self, full_game_setup):
        """Test that prompts are built with correct context"""
        game = full_game_setup

        # Test prompt for bot needing to ask
        prompt = build_bot_tool_prompt(game, "bot1", "ask a question")

        assert "Detective Bot" in prompt
        assert "ask a question" in prompt
        assert "Location: Bank" in prompt
        assert "Role: Teller" in prompt
        assert "spy's objective" in prompt.lower()
        assert "non-spies' objective" in prompt.lower()

        # Add a question and test answer context
        question_event = create_question_event(
            from_player_id="human1",
            from_player_name="Alice",
            to_player_id="bot1",
            to_player_name="Detective Bot",
            question_text="What's your favorite part of the job?"
        )
        game.events = [question_event]

        context = get_action_context(game, "bot1")
        assert context == "answer the question asked to you"

        answer_prompt = build_bot_tool_prompt(game, "bot1", context)
        assert "**Alice** asked **Detective Bot**: \"What's your favorite part of the job?\"" in answer_prompt

    def test_tool_selector_game_state_awareness(self, full_game_setup):
        """Test that tool selector correctly responds to game state"""
        game = full_game_setup

        # Test when it's bot's turn to ask
        tools = ToolSelector.get_available_tools(game, "bot1")
        tool_names = [t['name'] for t in tools]
        assert 'ask' in tool_names
        assert 'accuse' in tool_names
        assert 'guess_location' not in tool_names  # Not spy

        # Test when bot needs to answer
        question_event = create_question_event(
            from_player_id="human1",
            from_player_name="Alice",
            to_player_id="bot1",
            to_player_name="Detective Bot",
            question_text="Test?"
        )
        game.events = [question_event]

        tools = ToolSelector.get_available_tools(game, "bot1")
        tool_names = [t['name'] for t in tools]
        assert 'answer' in tool_names
        assert 'accuse' in tool_names
        assert 'ask' not in tool_names

        # Test spy tools
        game.spy_id = "bot1"
        tools = ToolSelector.get_available_tools(game, "bot1")
        tool_names = [t['name'] for t in tools]
        assert 'guess_location' in tool_names

        # Test after accusation
        bot1 = next(p for p in game.players if p.id == "bot1")
        bot1.has_accused_this_round = True
        game.current_turn = "human1"  # Not bot's turn

        tools = ToolSelector.get_available_tools(game, "bot1")
        tool_names = [t['name'] for t in tools]
        assert 'accuse' not in tool_names  # Already accused
        assert 'guess_location' in tool_names  # Still spy