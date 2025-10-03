#!/usr/bin/env python3
"""
Simple test runner for LLM integration
Run this to verify the tool-based LLM system works end-to-end
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.llm_service import LLMService
from services.tool_prompt_builder import build_bot_tool_prompt, get_action_context
from services.tool_selector import ToolSelector
from tools.game_actions import ask_tool, answer_tool, accuse_tool, guess_location_tool
from models import Game, Player, GameStatus
from models.location import LOCATIONS

# Load environment variables
load_dotenv()


async def test_basic_llm_connection():
    """Test basic LLM connection"""
    print("🔍 Testing basic LLM connection...")

    try:
        llm_service = LLMService()
        response = await llm_service.get_completion("Hello, can you respond with just 'Connection successful'?", max_tokens=50)

        if response:
            print(f"✅ LLM Connection successful: {response.strip()}")
            return True
        else:
            print("❌ LLM Connection failed: No response")
            return False
    except Exception as e:
        print(f"❌ LLM Connection failed: {e}")
        return False


async def test_tool_based_query():
    """Test tool-based LLM query"""
    print("\n🛠️ Testing tool-based LLM query...")

    try:
        # Create a sample game
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
        human_player.role = "Spy"
        bot_player.role = "Teller"

        # Get available tools
        available_tools = ToolSelector.get_available_tools(game, "bot1")
        print(f"📋 Available tools for bot1: {[tool['name'] for tool in available_tools]}")

        # Build prompt
        action_context = get_action_context(game, "bot1")
        prompt = build_bot_tool_prompt(game, "bot1", action_context)

        print(f"📝 Action context: {action_context}")
        print(f"📄 Prompt length: {len(prompt)} characters")

        # Query LLM with tools
        llm_service = LLMService()
        result = await llm_service.query_bot_with_tools(
            prompt=prompt,
            bot_id="bot1",
            available_tools=available_tools,
            max_tokens=500
        )

        if result and result.get('tool_calls'):
            print(f"✅ Tool-based query successful!")
            print(f"🔧 Tool calls received: {len(result['tool_calls'])}")

            for i, tool_call in enumerate(result['tool_calls']):
                print(f"   {i+1}. Tool: {tool_call.get('name')}")
                print(f"      Parameters: {tool_call.get('parameters', {})}")

            return True
        else:
            print("❌ Tool-based query failed: No tool calls received")
            print(f"Raw result: {result}")
            return False

    except Exception as e:
        print(f"❌ Tool-based query failed: {e}")
        return False


async def test_prompt_building():
    """Test prompt building components"""
    print("\n📋 Testing prompt building components...")

    try:
        # Create test game
        game = Game(id="test-prompt")

        human_player = Player(id="human1", name="Alice", is_bot=False)
        bot_player = Player(id="bot1", name="Detective Bot", is_bot=True)

        game.players = [human_player, bot_player]
        game.status = GameStatus.IN_PROGRESS
        game.current_turn = "bot1"
        game.location = LOCATIONS[0]  # Airplane
        game.spy_id = "human1"

        human_player.role = "Spy"
        bot_player.role = "Pilot"

        # Test basic prompt building
        prompt = build_bot_tool_prompt(game, "bot1", "ask a question")

        # Verify prompt contains expected elements
        required_elements = [
            "Detective Bot",
            "ask a question",
            "Location: Airplane",
            "Role: Pilot",
            "Alice (ID: human1)",
            "Use the relevant tools"
        ]

        missing_elements = []
        for element in required_elements:
            if element not in prompt:
                missing_elements.append(element)

        if not missing_elements:
            print("✅ Prompt building successful - all required elements present")
            print(f"📏 Prompt length: {len(prompt)} characters")
            return True
        else:
            print(f"❌ Prompt building failed - missing elements: {missing_elements}")
            return False

    except Exception as e:
        print(f"❌ Prompt building failed: {e}")
        return False


async def test_tool_selection():
    """Test tool selection logic"""
    print("\n⚙️ Testing tool selection logic...")

    try:
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

        if 'ask' in tool_names and 'accuse' in tool_names:
            print("✅ Bot turn (ask) - correct tools available")
        else:
            print(f"❌ Bot turn (ask) - unexpected tools: {tool_names}")
            return False

        # Test 2: Spy bot tools
        tools = ToolSelector.get_available_tools(game, "bot2")
        tool_names = [tool['name'] for tool in tools]

        if 'guess_location' in tool_names:
            print("✅ Spy bot - guess_location tool available")
        else:
            print(f"❌ Spy bot - guess_location missing: {tool_names}")
            return False

        # Test 3: Bot not on turn
        game.current_turn = "human1"
        tools = ToolSelector.get_available_tools(game, "bot1")
        tool_names = [tool['name'] for tool in tools]

        if 'accuse' in tool_names and 'ask' not in tool_names:
            print("✅ Bot not on turn - only accuse available")
        else:
            print(f"❌ Bot not on turn - unexpected tools: {tool_names}")
            return False

        print("✅ Tool selection logic working correctly")
        return True

    except Exception as e:
        print(f"❌ Tool selection failed: {e}")
        return False


async def main():
    """Run all integration tests"""
    print("🚀 Starting LLM Integration Tests")
    print("=" * 50)

    # Check if API key is available
    api_key = os.getenv('CLAUDE_API_KEY')
    if not api_key:
        print("❌ CLAUDE_API_KEY environment variable not set")
        print("   Please set your Claude API key to run LLM tests")
        return

    print(f"🔑 API key found: {api_key[:10]}...")

    # Run tests
    tests = [
        test_prompt_building,
        test_tool_selection,
        test_basic_llm_connection,
        test_tool_based_query,
    ]

    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")

    passed = sum(results)
    total = len(results)

    print(f"✅ Passed: {passed}/{total}")

    if passed == total:
        print("🎉 All LLM integration tests passed!")
        print("   The tool-based bot system is ready for use.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

    return passed == total


if __name__ == "__main__":
    asyncio.run(main())