"""
Integration tests for Claude API (requires CLAUDE_API_KEY)
"""
import pytest
import os
from llm import claude_client


@pytest.mark.skipif(
    not os.getenv("CLAUDE_API_KEY"),
    reason="CLAUDE_API_KEY not set - skipping integration tests"
)
class TestClaudeIntegration:
    """Integration tests that actually call Claude API"""

    @pytest.mark.asyncio
    async def test_claude_basic_connection(self):
        """Test basic Claude API connection"""
        prompt = 'Respond with JSON: {"test": "success", "message": "API working"}'
        response = await claude_client.get_json_completion(prompt, max_tokens=100)

        assert response is not None
        assert response.get("test") == "success"
        assert "message" in response

    @pytest.mark.asyncio
    async def test_question_generation_integration(self, mock_game_state):
        """Test actual question generation with Claude"""
        available_targets = ["human1", "bot2"]
        result = await claude_client.generate_question(mock_game_state, "bot1", available_targets)

        assert result is not None
        target_id, question = result
        assert target_id in available_targets
        assert isinstance(question, str)
        assert len(question) > 0

    @pytest.mark.asyncio
    async def test_answer_generation_integration(self, mock_game_state):
        """Test actual answer generation with Claude"""
        answer = await claude_client.generate_answer(
            mock_game_state, "bot1", "What's your favorite part of working here?", "human1"
        )

        assert answer is not None
        assert isinstance(answer, str)
        assert len(answer) > 0

    @pytest.mark.asyncio
    async def test_spy_question_generation(self, mock_spy_game_state):
        """Test question generation when bot is the spy"""
        available_targets = ["human1"]
        result = await claude_client.generate_question(mock_spy_game_state, "bot1", available_targets)

        assert result is not None
        target_id, question = result
        assert target_id == "human1"
        assert isinstance(question, str)
        # Spy questions should be more general/fishing for information
        assert len(question) > 0

    @pytest.mark.asyncio
    async def test_voting_decision_integration(self, mock_voting_game_state):
        """Test actual voting decision generation with Claude"""
        result = await claude_client.should_vote_guilty(
            mock_voting_game_state, "bot2", "bot3", "Carol"
        )

        assert result is not None
        should_vote_guilty = result
        assert isinstance(should_vote_guilty, bool)

    @pytest.mark.asyncio
    async def test_spy_voting_decision_integration(self, mock_spy_voting_game_state):
        """Test voting decision when bot is the spy"""
        result = await claude_client.should_vote_guilty(
            mock_spy_voting_game_state, "bot1", "bot2", "Bob"
        )

        assert result is not None
        should_vote_guilty = result
        assert isinstance(should_vote_guilty, bool)