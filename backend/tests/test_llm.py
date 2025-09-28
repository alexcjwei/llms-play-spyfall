"""
Tests for LLM integration module
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from llm import ClaudeClient


class TestClaudeClient:
    """Test cases for ClaudeClient"""

    def test_init_with_api_key(self, monkeypatch):
        """Test initialization with API key"""
        monkeypatch.setenv("CLAUDE_API_KEY", "test-key")
        client = ClaudeClient()
        assert client.api_key == "test-key"
        assert client.model == "claude-3-5-haiku-20241022"

    def test_init_without_api_key(self, monkeypatch):
        """Test initialization fails without API key"""
        monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
        with pytest.raises(ValueError, match="CLAUDE_API_KEY environment variable is required"):
            ClaudeClient()

    @pytest.mark.asyncio
    async def test_get_completion_success(self, monkeypatch):
        """Test successful completion"""
        monkeypatch.setenv("CLAUDE_API_KEY", "test-key")

        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": "Test response"}]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            client = ClaudeClient()
            result = await client.get_completion("Test prompt")

            assert result == "Test response"

    @pytest.mark.asyncio
    async def test_get_completion_api_error(self, monkeypatch):
        """Test API error handling"""
        monkeypatch.setenv("CLAUDE_API_KEY", "test-key")

        # Mock httpx response with error
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            client = ClaudeClient()
            result = await client.get_completion("Test prompt")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_json_completion_success(self, monkeypatch):
        """Test successful JSON completion"""
        monkeypatch.setenv("CLAUDE_API_KEY", "test-key")

        json_response = '{"test": "success", "value": 42}'
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": json_response}]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            client = ClaudeClient()
            result = await client.get_json_completion("Test prompt")

            assert result == {"test": "success", "value": 42}

    @pytest.mark.asyncio
    async def test_get_json_completion_with_markdown(self, monkeypatch):
        """Test JSON completion with markdown wrapping"""
        monkeypatch.setenv("CLAUDE_API_KEY", "test-key")

        json_response = '```json\n{"test": "success"}\n```'
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": json_response}]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            client = ClaudeClient()
            result = await client.get_json_completion("Test prompt")

            assert result == {"test": "success"}

    @pytest.mark.asyncio
    async def test_generate_question_success(self, monkeypatch, mock_game_state):
        """Test successful question generation"""
        monkeypatch.setenv("CLAUDE_API_KEY", "test-key")

        # Mock successful JSON response
        json_response = '{"target_id": "human1", "question": "What do you think about the safety procedures here?"}'
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": json_response}]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            client = ClaudeClient()
            result = await client.generate_question(mock_game_state, "bot1", ["human1", "bot2"])

            assert result is not None
            target_id, question = result
            assert target_id == "human1"
            assert "safety procedures" in question

    @pytest.mark.asyncio
    async def test_generate_question_invalid_target(self, monkeypatch, mock_game_state):
        """Test question generation with invalid target"""
        monkeypatch.setenv("CLAUDE_API_KEY", "test-key")

        # Mock response with invalid target
        json_response = '{"target_id": "invalid_player", "question": "Test question"}'
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": json_response}]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            client = ClaudeClient()
            result = await client.generate_question(mock_game_state, "bot1", ["human1", "bot2"])

            assert result is None

    @pytest.mark.asyncio
    async def test_generate_answer_success(self, monkeypatch, mock_game_state):
        """Test successful answer generation"""
        monkeypatch.setenv("CLAUDE_API_KEY", "test-key")

        # Mock successful JSON response
        json_response = '{"answer": "I really enjoy ensuring all the equipment is functioning properly."}'
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": json_response}]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            client = ClaudeClient()
            result = await client.generate_answer(
                mock_game_state, "bot1", "What's your favorite part of the job?", "human1"
            )

            assert result is not None
            assert "equipment" in result
            assert "functioning properly" in result