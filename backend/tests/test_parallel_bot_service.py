"""
Tests for the parallel bot service
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from services.parallel_bot_service import ParallelBotService, BotResponse, GameUpdateResult
from services.llm_service import LLMService
from models import Game, Player, GameStatus
from models.location import LOCATIONS


@pytest.fixture
def parallel_bot_service(monkeypatch):
    """Create parallel bot service instance for testing"""
    monkeypatch.setenv("CLAUDE_API_KEY", "test-key")
    llm_service = LLMService()
    return ParallelBotService(llm_service)


@pytest.fixture
def sample_game():
    """Create a sample game for testing"""
    game = Game(id="test-game")

    # Add players
    human_player = Player(id="human1", name="Alice", is_bot=False)
    bot_player_1 = Player(id="bot1", name="Bot Alice", is_bot=True)
    bot_player_2 = Player(id="bot2", name="Bot Bob", is_bot=True)
    bot_player_3 = Player(id="bot3", name="Bot Carol", is_bot=True)

    game.players = [human_player, bot_player_1, bot_player_2, bot_player_3]
    game.status = GameStatus.IN_PROGRESS
    game.current_turn = "human1"  # Human turn, so bots can only accuse
    game.location = LOCATIONS[0]  # Airplane
    game.spy_id = "bot1"  # Make bot1 the spy

    # Assign roles
    human_player.role = "Pilot"
    bot_player_1.role = "Spy"
    bot_player_2.role = "Flight Attendant"
    bot_player_3.role = "Passenger"

    return game


class TestParallelBotService:
    """Test the parallel bot service"""

    @pytest.mark.asyncio
    async def test_query_all_bots_success(self, parallel_bot_service, sample_game):
        """Test successful parallel querying of all bots"""
        # Mock LLM responses for different bots
        def mock_llm_response(prompt, bot_id, available_tools):
            if bot_id == "bot1":  # Spy bot - can guess location
                return {
                    "tool_calls": [{
                        "name": "guess_location",
                        "parameters": {
                            "thought": "I think this is an airplane",
                            "location": "Airplane"
                        }
                    }]
                }
            elif bot_id == "bot2":  # Regular bot - can accuse
                return {
                    "tool_calls": [{
                        "name": "accuse",
                        "parameters": {
                            "thought": "I'm suspicious of the human",
                            "target": "human1"
                        }
                    }]
                }
            else:  # bot3 - chooses not to act
                return {
                    "tool_calls": [{
                        "name": "accuse",
                        "parameters": {
                            "thought": "I'm not ready to accuse yet",
                            "target": ""  # No accusation
                        }
                    }]
                }

        parallel_bot_service.llm_service.query_bot_with_tools = AsyncMock(side_effect=mock_llm_response)

        responses = await parallel_bot_service.query_all_bots(sample_game)

        # Should have responses from all 3 bots
        assert len(responses) == 3

        # Check each response
        bot_ids = [resp.bot_id for resp in responses]
        assert "bot1" in bot_ids
        assert "bot2" in bot_ids
        assert "bot3" in bot_ids

        # All should be successful
        for response in responses:
            assert response.success is True
            assert response.error is None

    @pytest.mark.asyncio
    async def test_query_all_bots_with_errors(self, parallel_bot_service, sample_game):
        """Test parallel querying with some bot errors"""
        def mock_llm_response(prompt, bot_id, available_tools):
            if bot_id == "bot1":
                return {
                    "tool_calls": [{
                        "name": "guess_location",
                        "parameters": {
                            "thought": "I'll guess the location",
                            "location": "Bank"
                        }
                    }]
                }
            elif bot_id == "bot2":
                # Simulate LLM error
                raise Exception("API timeout")
            else:
                return {"tool_calls": []}

        parallel_bot_service.llm_service.query_bot_with_tools = AsyncMock(side_effect=mock_llm_response)

        responses = await parallel_bot_service.query_all_bots(sample_game)

        assert len(responses) == 3

        # Find responses by bot_id
        responses_by_id = {resp.bot_id: resp for resp in responses}

        # bot1 should be successful
        assert responses_by_id["bot1"].success is True

        # bot2 should have error
        assert responses_by_id["bot2"].success is False
        assert "API timeout" in responses_by_id["bot2"].error

        # bot3 should be successful (empty tool calls)
        assert responses_by_id["bot3"].success is True

    @pytest.mark.asyncio
    async def test_query_all_bots_no_bots_to_query(self, parallel_bot_service, sample_game):
        """Test when no bots need to be queried"""
        # Make all bots have no available tools (already accused this round)
        for player in sample_game.players:
            if player.is_bot:
                player.has_accused_this_round = True

        responses = await parallel_bot_service.query_all_bots(sample_game)
        assert len(responses) == 0

    @pytest.mark.asyncio
    async def test_process_bot_responses_priority_order(self, parallel_bot_service, sample_game):
        """Test that tool calls are processed in priority order"""
        # Create mock responses with different tool types
        responses = [
            BotResponse(
                bot_id="bot1",
                tool_calls=[
                    {
                        "name": "accuse",
                        "parameters": {"thought": "I'll accuse", "target": "human1"}
                    },
                    {
                        "name": "guess_location",
                        "parameters": {"thought": "I'll guess", "location": "Airplane"}
                    }
                ],
                success=True
            ),
            BotResponse(
                bot_id="bot2",
                tool_calls=[
                    {
                        "name": "ask",
                        "parameters": {"thought": "I'll ask", "question": "How are you?", "target": "human1"}
                    }
                ],
                success=True
            )
        ]

        # Mock the tool functions
        with patch('tools.game_actions.TOOL_FUNCTIONS') as mock_functions:
            mock_functions.__getitem__ = Mock(return_value=Mock(return_value=True))
            mock_functions.__contains__ = Mock(return_value=True)

            result = await parallel_bot_service.process_bot_responses(sample_game, responses)

            # guess_location should be processed first (priority 1), then ask (priority 2), then accuse (priority 4)
            assert len(result.actions_taken) == 3
            assert result.actions_taken[0]['action'] == 'guess_location'
            assert result.actions_taken[1]['action'] == 'ask'
            assert result.actions_taken[2]['action'] == 'accuse'

    @pytest.mark.asyncio
    async def test_process_bot_responses_game_ends(self, parallel_bot_service, sample_game):
        """Test when spy guesses location correctly and game ends"""
        responses = [
            BotResponse(
                bot_id="bot1",  # Spy
                tool_calls=[
                    {
                        "name": "guess_location",
                        "parameters": {"thought": "I know it's an airplane", "location": "Airplane"}
                    }
                ],
                success=True
            ),
            BotResponse(
                bot_id="bot2",
                tool_calls=[
                    {
                        "name": "accuse",
                        "parameters": {"thought": "I'll accuse", "target": "human1"}
                    }
                ],
                success=True
            )
        ]

        # Mock guess_location to end the game
        def mock_guess_location(game, bot_id, **kwargs):
            game.status = GameStatus.FINISHED
            game.winner = "spy"
            return True

        with patch('tools.game_actions.TOOL_FUNCTIONS') as mock_functions:
            mock_functions.__getitem__ = Mock(side_effect=lambda name: {
                'guess_location': mock_guess_location,
                'accuse': Mock(return_value=True)
            }[name])
            mock_functions.__contains__ = Mock(return_value=True)

            result = await parallel_bot_service.process_bot_responses(sample_game, responses)

            # Should process guess_location and end game
            assert result.game_ended is True
            assert len(result.actions_taken) == 1  # Only guess_location processed
            assert result.actions_taken[0]['action'] == 'guess_location'

    @pytest.mark.asyncio
    async def test_process_bot_responses_multiple_accusations(self, parallel_bot_service, sample_game):
        """Test when multiple bots make accusations simultaneously"""
        responses = [
            BotResponse(
                bot_id="bot1",
                tool_calls=[
                    {
                        "name": "accuse",
                        "parameters": {"thought": "I accuse human1", "target": "human1"}
                    }
                ],
                success=True
            ),
            BotResponse(
                bot_id="bot2",
                tool_calls=[
                    {
                        "name": "accuse",
                        "parameters": {"thought": "I accuse bot3", "target": "bot3"}
                    }
                ],
                success=True
            ),
            BotResponse(
                bot_id="bot3",
                tool_calls=[
                    {
                        "name": "accuse",
                        "parameters": {"thought": "I accuse bot1", "target": "bot1"}
                    }
                ],
                success=True
            )
        ]

        with patch('tools.game_actions.TOOL_FUNCTIONS') as mock_functions:
            mock_functions.__getitem__ = Mock(return_value=Mock(return_value=True))
            mock_functions.__contains__ = Mock(return_value=True)

            result = await parallel_bot_service.process_bot_responses(sample_game, responses)

            # Only first accusation should be processed
            assert len(result.actions_taken) == 1
            assert result.actions_taken[0]['action'] == 'accuse'
            assert result.accusation_made is True

    @pytest.mark.asyncio
    async def test_process_bot_responses_empty_accusations(self, parallel_bot_service, sample_game):
        """Test when bots make empty accusations (choose not to accuse)"""
        responses = [
            BotResponse(
                bot_id="bot1",
                tool_calls=[
                    {
                        "name": "accuse",
                        "parameters": {"thought": "I'm not ready to accuse", "target": ""}
                    }
                ],
                success=True
            ),
            BotResponse(
                bot_id="bot2",
                tool_calls=[
                    {
                        "name": "accuse",
                        "parameters": {"thought": "No accusation yet", "target": "   "}  # Whitespace
                    }
                ],
                success=True
            )
        ]

        with patch('tools.game_actions.TOOL_FUNCTIONS') as mock_functions:
            mock_functions.__getitem__ = Mock(return_value=Mock(return_value=True))
            mock_functions.__contains__ = Mock(return_value=True)

            result = await parallel_bot_service.process_bot_responses(sample_game, responses)

            # No accusations should be processed
            assert len(result.actions_taken) == 0
            assert result.accusation_made is False

    @pytest.mark.asyncio
    async def test_process_bot_responses_tool_execution_error(self, parallel_bot_service, sample_game):
        """Test handling of tool execution errors"""
        responses = [
            BotResponse(
                bot_id="bot1",
                tool_calls=[
                    {
                        "name": "ask",
                        "parameters": {"thought": "I'll ask", "question": "How are you?", "target": "invalid_player"}
                    }
                ],
                success=True
            )
        ]

        # Mock tool function to raise an error
        def mock_ask_function(game, bot_id, **kwargs):
            raise ValueError("Invalid target player")

        with patch('tools.game_actions.TOOL_FUNCTIONS') as mock_functions:
            mock_functions.__getitem__ = Mock(return_value=mock_ask_function)
            mock_functions.__contains__ = Mock(return_value=True)

            result = await parallel_bot_service.process_bot_responses(sample_game, responses)

            # Should have error but no actions taken
            assert len(result.actions_taken) == 0
            assert len(result.errors) == 1
            assert "Invalid target player" in result.errors[0]

    @pytest.mark.asyncio
    async def test_process_bot_responses_unknown_tool(self, parallel_bot_service, sample_game):
        """Test handling of unknown tool calls"""
        responses = [
            BotResponse(
                bot_id="bot1",
                tool_calls=[
                    {
                        "name": "unknown_tool",
                        "parameters": {"some": "param"}
                    }
                ],
                success=True
            )
        ]

        with patch('tools.game_actions.TOOL_FUNCTIONS') as mock_functions:
            mock_functions.__contains__ = Mock(return_value=False)

            result = await parallel_bot_service.process_bot_responses(sample_game, responses)

            # Should have error for unknown tool
            assert len(result.actions_taken) == 0
            assert len(result.errors) == 1
            assert "Unknown tool: unknown_tool" in result.errors[0]

    @pytest.mark.asyncio
    async def test_execute_tool_call_success(self, parallel_bot_service, sample_game):
        """Test successful tool call execution"""
        tool_call = {
            "name": "ask",
            "parameters": {
                "thought": "I need to ask a question",
                "question": "What do you do here?",
                "target": "human1"
            }
        }

        with patch('tools.game_actions.TOOL_FUNCTIONS') as mock_functions:
            mock_ask = Mock(return_value=True)
            mock_functions.__getitem__ = Mock(return_value=mock_ask)
            mock_functions.__contains__ = Mock(return_value=True)

            success, error = await parallel_bot_service._execute_tool_call(sample_game, "bot1", tool_call)

            assert success is True
            assert error is None
            mock_ask.assert_called_once_with(
                sample_game,
                "bot1",
                thought="I need to ask a question",
                question="What do you do here?",
                target="human1"
            )