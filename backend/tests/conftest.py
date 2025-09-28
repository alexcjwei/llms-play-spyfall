"""
Pytest configuration and fixtures
"""
import pytest
import asyncio
import os
from unittest.mock import Mock, AsyncMock
from dotenv import load_dotenv

# Load environment variables from .env.local
load_dotenv('.env.local')


@pytest.fixture
def mock_claude_response():
    """Mock successful Claude API response"""
    return {
        "content": [
            {
                "text": '{"target_id": "player1", "question": "What do you think about this place?"}'
            }
        ]
    }


@pytest.fixture
def mock_game_state():
    """Mock game state for testing"""
    return {
        "id": "TEST123",
        "status": "in_progress",
        "players": [
            {"id": "bot1", "name": "Alice", "isBot": True, "isConnected": True},
            {"id": "human1", "name": "Player", "isBot": False, "isConnected": True},
            {"id": "bot2", "name": "Bob", "isBot": True, "isConnected": True}
        ],
        "currentTurn": "bot1",
        "location": "Airport",
        "role": "Pilot",
        "isSpy": False,
        "messages": [
            {
                "id": "1",
                "type": "question",
                "from": "human1",
                "to": "bot2",
                "content": "What's your favorite thing about working here?",
                "timestamp": 1234567890
            },
            {
                "id": "2",
                "type": "answer",
                "from": "bot2",
                "content": "I love helping passengers get to their destinations safely.",
                "timestamp": 1234567891
            }
        ],
        "clockStopped": False
    }


@pytest.fixture
def mock_spy_game_state():
    """Mock game state where bot is the spy"""
    return {
        "id": "TEST123",
        "status": "in_progress",
        "players": [
            {"id": "bot1", "name": "Alice", "isBot": True, "isConnected": True},
            {"id": "human1", "name": "Player", "isBot": False, "isConnected": True}
        ],
        "currentTurn": "bot1",
        "isSpy": True,
        "messages": [],
        "clockStopped": False
    }