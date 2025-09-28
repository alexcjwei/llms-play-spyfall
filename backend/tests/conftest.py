"""
Pytest configuration and fixtures
"""
import pytest
import asyncio
import os
from unittest.mock import Mock, AsyncMock
from dotenv import load_dotenv

# Load environment variables (dotenv will find the right .env file)
load_dotenv()


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


@pytest.fixture
def mock_voting_game_state():
    """Mock game state during voting phase"""
    return {
        "id": "TEST123",
        "status": "voting",
        "players": [
            {"id": "bot1", "name": "Alice", "isBot": True, "isConnected": True},
            {"id": "human1", "name": "Player", "isBot": False, "isConnected": True},
            {"id": "bot2", "name": "Bob", "isBot": True, "isConnected": True},
            {"id": "bot3", "name": "Carol", "isBot": True, "isConnected": True}
        ],
        "currentTurn": "bot1",
        "location": "Airport",
        "role": "Pilot",
        "isSpy": False,
        "messages": [
            {
                "id": "1",
                "type": "question",
                "from": "bot2",
                "to": "bot3",
                "content": "What's the busiest time of day here?",
                "timestamp": 1234567890
            },
            {
                "id": "2",
                "type": "answer",
                "from": "bot3",
                "content": "I... well, you know, when people are traveling.",
                "timestamp": 1234567891
            },
            {
                "id": "3",
                "type": "question",
                "from": "human1",
                "to": "bot3",
                "content": "What equipment do you use most often?",
                "timestamp": 1234567892
            },
            {
                "id": "4",
                "type": "answer",
                "from": "bot3",
                "content": "The usual... things that everyone uses here.",
                "timestamp": 1234567893
            }
        ],
        "currentAccusation": {
            "accuserId": "bot1",
            "accusedId": "bot3",
            "accusedName": "Carol",
            "votes": {"bot1": True}  # Accuser already voted guilty
        },
        "clockStopped": False
    }


@pytest.fixture
def mock_spy_voting_game_state():
    """Mock game state during voting phase where bot making decision is the spy"""
    return {
        "id": "TEST123",
        "status": "voting",
        "players": [
            {"id": "bot1", "name": "Alice", "isBot": True, "isConnected": True},
            {"id": "human1", "name": "Player", "isBot": False, "isConnected": True},
            {"id": "bot2", "name": "Bob", "isBot": True, "isConnected": True}
        ],
        "currentTurn": "bot1",
        "isSpy": True,  # This bot is the spy
        "messages": [
            {
                "id": "1",
                "type": "question",
                "from": "human1",
                "to": "bot2",
                "content": "What's your main responsibility here?",
                "timestamp": 1234567890
            },
            {
                "id": "2",
                "type": "answer",
                "from": "bot2",
                "content": "I help passengers with their luggage and boarding passes.",
                "timestamp": 1234567891
            }
        ],
        "currentAccusation": {
            "accuserId": "human1",
            "accusedId": "bot2",
            "accusedName": "Bob",
            "votes": {"human1": True}
        },
        "clockStopped": False
    }