"""
Tests for LLM tool-based integration
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from services.llm_service import LLMService
from services.tool_prompt_builder import build_bot_tool_prompt, get_action_context
from services.tool_selector import ToolSelector
from tools.game_actions import ask_tool, answer_tool, accuse_tool, guess_location_tool
from models import Game, Player, GameStatus
from models.location import LOCATIONS


@pytest.fixture
def llm_service(monkeypatch):
    """Create LLM service instance for testing"""
    monkeypatch.setenv("CLAUDE_API_KEY", "test-key")
    return LLMService()


@pytest.fixture
def sample_game():
    """Create a sample game for testing"""
    game = Game(id="test-game")

    # Add players
    human_player = Player(id="human1", name="Alice", is_bot=False)
    bot_player_1 = Player(id="bot1", name="Bot Alice", is_bot=True)
    bot_player_2 = Player(id="bot2", name="Bot Bob", is_bot=True)

    game.players = [human_player, bot_player_1, bot_player_2]
    game.status = GameStatus.IN_PROGRESS
    game.current_turn = "bot1"
    game.location = LOCATIONS[0]  # Airplane
    game.spy_id = "human1"

    # Assign roles
    human_player.role = "Spy"
    bot_player_1.role = "Pilot"
    bot_player_2.role = "Flight Attendant"

    return game


class TestToolPromptBuilder:
    """Test the tool-based prompt builder"""

    def test_build_bot_tool_prompt_non_spy(self, sample_game):
        """Test prompt building for non-spy bot"""
        prompt = build_bot_tool_prompt(sample_game, "bot1", "ask a question")

        assert "Bot Alice" in prompt
        assert "ask a question" in prompt
        assert "Location: Airplane" in prompt
        assert "Role: Pilot" in prompt
        assert "Alice (ID: human1)" in prompt
        assert "Bot Alice (ID: bot1)" in prompt
        assert "Bot Bob (ID: bot2)" in prompt
        assert "Use the relevant tools" in prompt

    def test_build_bot_tool_prompt_spy(self, sample_game):
        """Test prompt building for spy bot"""
        # Make bot1 the spy instead
        sample_game.spy_id = "bot1"

        prompt = build_bot_tool_prompt(sample_game, "bot1", "take your next action")

        assert "Bot Alice" in prompt
        assert "Location: Unknown (You are the spy!)" in prompt
        assert "Role: Spy" in prompt

    def test_get_action_context_bot_turn_ask(self, sample_game):
        """Test action context when bot needs to ask"""
        context = get_action_context(sample_game, "bot1")
        assert context == "ask a question to another player"

    def test_get_action_context_bot_turn_answer(self, sample_game):
        """Test action context when bot needs to answer"""
        # Add a question message to the bot
        from models.message import Message
        question_msg = Message(
            from_id="human1",
            to_id="bot1",
            content="What do you do here?",
            type="question"
        )
        sample_game.messages = [question_msg]

        context = get_action_context(sample_game, "bot1")
        assert context == "answer the question asked to you"

    def test_get_action_context_not_bot_turn(self, sample_game):
        """Test action context when it's not the bot's turn"""
        context = get_action_context(sample_game, "bot2")
        assert context == "take your next action"


class TestToolSelector:
    """Test the tool selector logic"""

    def test_get_available_tools_bot_turn_ask(self, sample_game):
        """Test tools available when bot needs to ask"""
        tools = ToolSelector.get_available_tools(sample_game, "bot1")

        tool_names = [tool['name'] for tool in tools]
        assert 'ask' in tool_names
        assert 'accuse' in tool_names
        assert 'guess_location' not in tool_names  # bot1 is not spy

    def test_get_available_tools_bot_turn_answer(self, sample_game):
        """Test tools available when bot needs to answer"""
        # Add a question message to the bot
        from models.message import Message
        question_msg = Message(
            from_id="human1",
            to_id="bot1",
            content="What do you do here?",
            type="question"
        )
        sample_game.messages = [question_msg]

        tools = ToolSelector.get_available_tools(sample_game, "bot1")

        tool_names = [tool['name'] for tool in tools]
        assert 'answer' in tool_names
        assert 'accuse' in tool_names
        assert 'ask' not in tool_names

    def test_get_available_tools_spy_bot(self, sample_game):
        """Test tools available for spy bot"""
        sample_game.spy_id = "bot1"

        tools = ToolSelector.get_available_tools(sample_game, "bot1")

        tool_names = [tool['name'] for tool in tools]
        assert 'guess_location' in tool_names

    def test_get_available_tools_not_bot_turn(self, sample_game):
        """Test tools available when it's not the bot's turn"""
        tools = ToolSelector.get_available_tools(sample_game, "bot2")

        tool_names = [tool['name'] for tool in tools]
        assert 'accuse' in tool_names  # Can still accuse if haven't accused this round
        assert 'ask' not in tool_names
        assert 'answer' not in tool_names

    def test_get_available_tools_already_accused(self, sample_game):
        """Test tools when bot has already accused this round"""
        bot_player = next(p for p in sample_game.players if p.id == "bot2")
        bot_player.has_accused_this_round = True

        tools = ToolSelector.get_available_tools(sample_game, "bot2")

        tool_names = [tool['name'] for tool in tools]
        assert 'accuse' not in tool_names

    def test_should_query_bot_with_tools(self, sample_game):
        """Test whether bot should be queried when tools are available"""
        should_query = ToolSelector.should_query_bot(sample_game, "bot1")
        assert should_query is True

    def test_should_query_bot_no_tools(self, sample_game):
        """Test whether bot should be queried when no tools available"""
        # Make it not the bot's turn and already accused
        sample_game.current_turn = "human1"
        bot_player = next(p for p in sample_game.players if p.id == "bot1")
        bot_player.has_accused_this_round = True

        should_query = ToolSelector.should_query_bot(sample_game, "bot1")
        assert should_query is False


class TestLLMToolIntegration:
    """Test LLM service with tool-based requests"""

    @pytest.mark.asyncio
    async def test_query_bot_with_tools_success(self, llm_service):
        """Test successful tool-based query"""
        # Mock successful Claude API response with tool use
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [
                {
                    "type": "tool_use",
                    "name": "ask",
                    "input": {
                        "thought": "I need to ask a strategic question",
                        "question": "What safety procedures do you follow here?",
                        "target": "human1"
                    }
                }
            ]
        }

        available_tools = [ask_tool, accuse_tool]

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await llm_service.query_bot_with_tools(
                prompt="Test prompt",
                bot_id="bot1",
                available_tools=available_tools
            )

            assert result is not None
            assert "tool_calls" in result
            assert len(result["tool_calls"]) == 1

            tool_call = result["tool_calls"][0]
            assert tool_call["name"] == "ask"
            assert tool_call["parameters"]["question"] == "What safety procedures do you follow here?"
            assert tool_call["parameters"]["target"] == "human1"

    @pytest.mark.asyncio
    async def test_query_bot_with_tools_multiple_calls(self, llm_service):
        """Test bot making multiple tool calls"""
        # Mock response with multiple tool uses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [
                {
                    "type": "tool_use",
                    "name": "ask",
                    "input": {
                        "thought": "I'll ask a question",
                        "question": "How long have you worked here?",
                        "target": "human1"
                    }
                },
                {
                    "type": "tool_use",
                    "name": "accuse",
                    "input": {
                        "thought": "I'm suspicious of this player",
                        "target": "human1"
                    }
                }
            ]
        }

        available_tools = [ask_tool, accuse_tool]

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await llm_service.query_bot_with_tools(
                prompt="Test prompt",
                bot_id="bot1",
                available_tools=available_tools
            )

            assert result is not None
            assert len(result["tool_calls"]) == 2
            assert result["tool_calls"][0]["name"] == "ask"
            assert result["tool_calls"][1]["name"] == "accuse"

    @pytest.mark.asyncio
    async def test_query_bot_with_tools_api_error(self, llm_service):
        """Test handling of API errors with fallback"""
        # Mock API error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_response.headers = {}
        mock_response.url = "https://api.anthropic.com/v1/messages"

        available_tools = [answer_tool]

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await llm_service.query_bot_with_tools(
                prompt="Test prompt",
                bot_id="bot1",
                available_tools=available_tools
            )

            # Should return fallback response
            assert result is not None
            assert "tool_calls" in result
            assert len(result["tool_calls"]) == 1
            assert result["tool_calls"][0]["name"] == "answer"
            assert "interesting question" in result["tool_calls"][0]["parameters"]["answer"]

    @pytest.mark.asyncio
    async def test_query_bot_with_tools_no_tool_calls(self, llm_service):
        """Test when model doesn't make tool calls despite tool_choice"""
        # Mock response without tool use
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [
                {
                    "type": "text",
                    "text": "I need to think about this..."
                }
            ]
        }

        available_tools = [answer_tool]

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await llm_service.query_bot_with_tools(
                prompt="Test prompt",
                bot_id="bot1",
                available_tools=available_tools
            )

            # Should return fallback response
            assert result is not None
            assert "tool_calls" in result
            assert len(result["tool_calls"]) == 1
            assert result["tool_calls"][0]["name"] == "answer"

    @pytest.mark.asyncio
    async def test_fallback_response_creation(self, llm_service):
        """Test creation of fallback responses for different tools"""
        # Test answer tool fallback
        result = llm_service._create_fallback_tool_response([answer_tool], "bot1")
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["name"] == "answer"
        assert "thought" in result["tool_calls"][0]["parameters"]
        assert "answer" in result["tool_calls"][0]["parameters"]

        # Test accuse tool fallback (should not accuse)
        result = llm_service._create_fallback_tool_response([accuse_tool], "bot1")
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["name"] == "accuse"
        assert result["tool_calls"][0]["parameters"]["target"] == ""  # Empty = no accusation

        # Test ask tool fallback (should not ask - too risky)
        result = llm_service._create_fallback_tool_response([ask_tool], "bot1")
        assert len(result["tool_calls"]) == 0

        # Test guess_location fallback (should not guess - too risky)
        result = llm_service._create_fallback_tool_response([guess_location_tool], "bot1")
        assert len(result["tool_calls"]) == 0


class TestToolIntegrationEndToEnd:
    """End-to-end integration tests for tool system"""

    @pytest.mark.asyncio
    async def test_complete_tool_flow_ask(self, llm_service, sample_game):
        """Test complete flow for asking a question"""
        # Mock LLM response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [
                {
                    "type": "tool_use",
                    "name": "ask",
                    "input": {
                        "thought": "I should ask about their job to see if they know the location",
                        "question": "What's the most challenging part of your work here?",
                        "target": "human1"
                    }
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            # Get available tools
            available_tools = ToolSelector.get_available_tools(sample_game, "bot1")

            # Build prompt
            prompt = build_bot_tool_prompt(sample_game, "bot1", "ask a question")

            # Query LLM
            result = await llm_service.query_bot_with_tools(
                prompt=prompt,
                bot_id="bot1",
                available_tools=available_tools
            )

            # Verify result
            assert result is not None
            assert len(result["tool_calls"]) == 1
            tool_call = result["tool_calls"][0]
            assert tool_call["name"] == "ask"
            assert "challenging part" in tool_call["parameters"]["question"]
            assert tool_call["parameters"]["target"] == "human1"

    def test_tool_schemas_are_valid(self):
        """Test that all tool schemas are properly formatted"""
        tools = [ask_tool, answer_tool, accuse_tool, guess_location_tool]

        for tool in tools:
            # Check required fields
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            assert "required" in tool

            # Check schema structure
            schema = tool["input_schema"]
            required_fields = tool["required"]

            for field in required_fields:
                assert field in schema, f"Required field {field} not in schema for {tool['name']}"

            # Check thought field is always present and required
            assert "thought" in schema
            assert "thought" in required_fields

    def test_location_enum_completeness(self):
        """Test that guess_location tool has complete location enum"""
        location_enum = guess_location_tool["input_schema"]["location"]["enum"]
        location_names = [loc.name for loc in LOCATIONS]

        assert len(location_enum) == len(location_names)
        for location_name in location_names:
            assert location_name in location_enum