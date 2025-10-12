"""
Pytest integration tests for LLM service and tool-based bot system
"""
import os
import pytest
import pytest_asyncio
from dotenv import load_dotenv

from services.llm_service import LLMService
from services.tool_prompt_builder import build_bot_tool_prompt, get_action_context
from services.tool_selector import ToolSelector
from tools.game_actions import ask_tool, answer_tool, accuse_tool, guess_location_tool
from models import Game, Player, GameStatus
from models.player import PlayerRole
from models.location import LOCATIONS

# Load environment variables
load_dotenv()

# Pytest setup
pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(not os.getenv('CLAUDE_API_KEY'), reason="CLAUDE_API_KEY not set")
async def test_basic_llm_connection():
    """Test basic LLM connection"""
    llm_service = LLMService()
    response = await llm_service.get_completion("Hello, can you respond with just 'Connection successful'?", max_tokens=50)

    assert response is not None, "LLM should return a response"
    assert len(response.strip()) > 0, "LLM response should not be empty"


@pytest.fixture
def sample_game():
    """Create a sample game for testing"""
    game = Game(id="test-game")

    # Add players
    human_player = Player(id="human1", name="Alice", is_bot=False)
    bot_player = Player(id="bot1", name="Detective Bot", is_bot=True)

    game.players = [human_player, bot_player]
    game.status = GameStatus.IN_PROGRESS
    game.current_turn = "bot1"
    game.location = LOCATIONS[2]  # Bank
    game.spy_id = "human1"

    # Assign roles
    human_player.role = PlayerRole.SPY
    bot_player.role = PlayerRole.INNOCENT
    bot_player.location_role = "Teller"

    return game

@pytest.mark.skipif(not os.getenv('CLAUDE_API_KEY'), reason="CLAUDE_API_KEY not set")
async def test_tool_based_query(sample_game):
    """Test tool-based LLM query"""
    game = sample_game

    # Get available tools
    available_tools = ToolSelector.get_available_tools(game, "bot1")
    assert len(available_tools) > 0, "Bot should have available tools"

    # Build prompt
    action_context = get_action_context(game, "bot1")
    prompt = build_bot_tool_prompt(game, "bot1", action_context)

    assert len(prompt) > 0, "Prompt should not be empty"
    assert "Detective Bot" in prompt, "Prompt should contain bot name"

    # Query LLM with tools
    llm_service = LLMService()
    result = await llm_service.query_bot_with_tools(
        messages=[{"role": "user", "content": prompt}],
        bot_id="bot1",
        available_tools=available_tools,
        system="You are a bot playing Spyfall.",
        max_tokens=500
    )

    assert result is not None, "LLM should return a result"
    assert result.get('tool_calls'), "Result should contain tool calls"
    assert len(result['tool_calls']) > 0, "Should have at least one tool call"

    # Verify tool call structure
    tool_call = result['tool_calls'][0]
    assert 'name' in tool_call, "Tool call should have a name"
    assert 'parameters' in tool_call, "Tool call should have parameters"


async def test_prompt_building():
    """Test prompt building components"""
    # Create test game
    game = Game(id="test-prompt")

    human_player = Player(id="human1", name="Alice", is_bot=False)
    bot_player = Player(id="bot1", name="Detective Bot", is_bot=True)

    game.players = [human_player, bot_player]
    game.status = GameStatus.IN_PROGRESS
    game.current_turn = "bot1"
    game.location = LOCATIONS[0]  # Airplane
    game.spy_id = "human1"

    human_player.role = PlayerRole.SPY
    bot_player.role = PlayerRole.INNOCENT
    bot_player.location_role = "Pilot"

    # Test basic prompt building
    prompt = build_bot_tool_prompt(game, "bot1", "ask a question")

    # Verify prompt contains expected elements
    required_elements = [
        "Detective Bot",
        "ask a question",
        "Location: Airplane",
        "Role: Pilot",
        "Alice (ID: human1)",
    ]

    for element in required_elements:
        assert element in prompt, f"Prompt should contain '{element}'"

    assert len(prompt) > 100, "Prompt should be substantial in length"


async def test_tool_selection():
    """Test tool selection logic"""
    # Create test scenarios
    game = Game(id="test-tools")

    human_player = Player(id="human1", name="Alice", is_bot=False)
    bot_player = Player(id="bot1", name="Detective Bot", is_bot=True)
    spy_bot = Player(id="bot2", name="Spy Bot", is_bot=True)

    game.players = [human_player, bot_player, spy_bot]
    game.status = GameStatus.IN_PROGRESS
    game.location = LOCATIONS[1]  # Amusement Park
    game.spy_id = "bot2"

    # Test 1: Bot's turn to ask
    game.current_turn = "bot1"
    tools = ToolSelector.get_available_tools(game, "bot1")
    tool_names = [tool['name'] for tool in tools]

    assert 'ask' in tool_names, "Bot on turn should have 'ask' tool available"
    assert 'accuse' in tool_names, "Bot should always have 'accuse' tool available"

    # Test 2: Spy bot tools
    tools = ToolSelector.get_available_tools(game, "bot2")
    tool_names = [tool['name'] for tool in tools]

    assert 'guess_location' in tool_names, "Spy bot should have 'guess_location' tool available"

    # Test 3: Bot not on turn
    game.current_turn = "human1"
    tools = ToolSelector.get_available_tools(game, "bot1")
    tool_names = [tool['name'] for tool in tools]

    assert 'accuse' in tool_names, "Bot not on turn should still have 'accuse' available"
    assert 'ask' not in tool_names, "Bot not on turn should not have 'ask' available"
