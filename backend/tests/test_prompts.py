"""
Tests for prompts module
"""
import pytest
from prompts import build_question_prompt, build_answer_prompt


class TestPrompts:
    """Test cases for prompt building functions"""

    def test_build_question_prompt_non_spy(self, mock_game_state):
        """Test question prompt building for non-spy bot"""
        available_targets = ["human1", "bot2"]
        prompt = build_question_prompt(mock_game_state, "bot1", available_targets)

        assert "Alice" in prompt  # Bot name
        assert "Airport" in prompt  # Location
        assert "Pilot" in prompt  # Role
        assert "target_id" in prompt  # Expected XML format
        assert "scratchpad" in prompt  # Thinking format

    def test_build_question_prompt_spy(self, mock_spy_game_state):
        """Test question prompt building for spy bot"""
        available_targets = ["human1"]
        prompt = build_question_prompt(mock_spy_game_state, "bot1", available_targets)

        assert "Alice" in prompt  # Bot name
        assert "you are the spy" in prompt.lower()  # Spy context
        assert "target_id" in prompt  # Expected XML format
        assert "scratchpad" in prompt  # Thinking format

    def test_build_question_prompt_invalid_bot(self, mock_game_state):
        """Test question prompt with invalid bot ID"""
        with pytest.raises(ValueError, match="Player invalid_bot not found"):
            build_question_prompt(mock_game_state, "invalid_bot", ["human1"])

    def test_build_answer_prompt_non_spy(self, mock_game_state):
        """Test answer prompt building for non-spy bot"""
        prompt = build_answer_prompt(mock_game_state, "bot1", "What's your role here?", "human1")

        assert "Alice" in prompt  # Bot name
        assert "Airport" in prompt  # Location
        assert "Pilot" in prompt  # Role
        assert "What's your role here?" in prompt  # The question
        assert "<answer>" in prompt  # Expected XML format
        assert "scratchpad" in prompt  # Thinking format

    def test_build_answer_prompt_spy(self, mock_spy_game_state):
        """Test answer prompt building for spy bot"""
        prompt = build_answer_prompt(mock_spy_game_state, "bot1", "Where do you work?", "human1")

        assert "Alice" in prompt  # Bot name
        assert "you are the spy" in prompt.lower()  # Spy context
        assert "Where do you work?" in prompt  # The question
        assert "<answer>" in prompt  # Expected XML format
        assert "scratchpad" in prompt  # Thinking format

    def test_build_answer_prompt_invalid_bot(self, mock_game_state):
        """Test answer prompt with invalid bot ID"""
        with pytest.raises(ValueError, match="Player invalid_bot not found"):
            build_answer_prompt(mock_game_state, "invalid_bot", "Test question", "human1")

    def test_build_answer_prompt_invalid_questioner(self, mock_game_state):
        """Test answer prompt with invalid questioner ID"""
        with pytest.raises(ValueError, match="Player invalid_questioner not found"):
            build_answer_prompt(mock_game_state, "bot1", "Test question", "invalid_questioner")

    def test_prompt_includes_message_history(self, mock_game_state):
        """Test that prompts include message history correctly"""
        # Test question prompt
        question_prompt = build_question_prompt(mock_game_state, "bot1", ["human1"])
        assert "What's your favorite thing about working here?" in question_prompt
        assert "helping passengers" in question_prompt

        # Test answer prompt
        answer_prompt = build_answer_prompt(mock_game_state, "bot1", "Test question", "human1")
        assert "What's your favorite thing about working here?" in answer_prompt
        assert "helping passengers" in answer_prompt