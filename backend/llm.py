"""
LLM integration module for Claude API
"""
import os
import json
import logging
import re
from typing import Optional, Dict, Any, List, Tuple
import httpx
from dotenv import load_dotenv
from prompts import build_question_prompt, build_answer_prompt, build_accusation_prompt, build_voting_prompt

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class ClaudeClient:
    """Client for interacting with Claude API"""

    def __init__(self):
        self.api_key = os.getenv('CLAUDE_API_KEY')
        if not self.api_key:
            raise ValueError("CLAUDE_API_KEY environment variable is required")

        self.base_url = "https://api.anthropic.com/v1/messages"
        self.model = "claude-3-7-sonnet-20250219"
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }

    async def get_completion(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> Optional[str]:
        """
        Get completion from Claude API

        Args:
            prompt: The prompt to send to Claude
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            The completion text or None if error
        """
        try:
            payload = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    logging.info(f"Prompt: {prompt}\nResult: {result['content'][0]['text']}")
                    return result["content"][0]["text"]
                else:
                    error_details = {
                        "status_code": response.status_code,
                        "response_text": response.text,
                        "headers": dict(response.headers),
                        "url": str(response.url)
                    }
                    logger.error(f"Claude API HTTP error: {error_details}")
                    return None

        except httpx.TimeoutException as e:
            logger.error(f"Claude API timeout after 30s: {e}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Claude API request error (network/connection): {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Claude API returned invalid JSON: {e}")
            return None
        except KeyError as e:
            logger.error(f"Claude API response missing expected field: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling Claude API: {type(e).__name__}: {e}")
            return None

    def extract_xml_tags(self, completion: str, tags: List[str]) -> Optional[Dict[str, str]]:
        """
        Extract XML tags from completion text

        Args:
            completion: The completion text containing XML tags
            tags: List of tag names to extract

        Returns:
            Dictionary mapping tag names to their values, or None if parsing fails
        """
        try:
            result = {}
            for tag in tags:
                pattern = f'<{tag}>(.*?)</{tag}>'
                match = re.search(pattern, completion, re.DOTALL)
                if match:
                    result[tag] = match.group(1).strip()
                else:
                    logger.warning(f"XML tag '{tag}' not found in completion")
                    return None
            return result
        except Exception as e:
            logger.error(f"Failed to parse XML tags from completion: {e}")
            return None

    async def get_xml_completion(self, prompt: str, tags: List[str], max_tokens: int = 1024, temperature: float = 0.7) -> Optional[Dict[str, str]]:
        """
        Get XML completion from Claude API

        Args:
            prompt: The prompt to send to Claude (should request XML response)
            tags: List of XML tag names to extract from response
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Dictionary mapping tag names to their values, or None if error
        """
        completion = await self.get_completion(prompt, max_tokens, temperature)
        if not completion:
            return None

        return self.extract_xml_tags(completion, tags)

    async def get_json_completion(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> Optional[Dict[str, Any]]:
        """
        Get JSON completion from Claude API

        Args:
            prompt: The prompt to send to Claude (should request JSON response)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Parsed JSON response or None if error
        """
        completion = await self.get_completion(prompt, max_tokens, temperature)
        if not completion:
            return None

        try:
            # Extract JSON from response if it's wrapped in other text
            completion = completion.strip()

            # Handle markdown code blocks
            if completion.startswith("```json"):
                completion = completion[7:]
            if completion.endswith("```"):
                completion = completion[:-3]
            completion = completion.strip()

            # Try to find JSON object boundaries
            start_idx = completion.find('{')
            if start_idx == -1:
                raise json.JSONDecodeError("No JSON object found", completion, 0)

            # Find the matching closing brace
            brace_count = 0
            end_idx = -1
            for i, char in enumerate(completion[start_idx:], start_idx):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break

            if end_idx == -1:
                raise json.JSONDecodeError("No matching closing brace", completion, start_idx)

            json_str = completion[start_idx:end_idx]
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Claude response: {e}")
            logger.error(f"Raw response (first 500 chars): {completion[:500]}")
            logger.error(f"Response length: {len(completion) if completion else 'None'}")
            return None

    async def generate_question(
        self,
        game_state: Dict[str, Any],
        bot_player_id: str,
        available_target_ids: List[str]
    ) -> Optional[Tuple[str, str]]:
        """
        Generate a question for a bot player

        Args:
            game_state: Current game state
            bot_player_id: ID of the bot player asking the question
            available_target_ids: List of player IDs that can be questioned

        Returns:
            Tuple of (target_player_id, question) or None if error
        """
        try:
            prompt = build_question_prompt(game_state, bot_player_id, available_target_ids)
            response = await self.get_xml_completion(prompt, ["target_id", "question"], max_tokens=512, temperature=0.8)

            if response and "target_id" in response and "question" in response:
                target_id = response["target_id"]
                question = response["question"]

                # Validate target_id is in available targets
                if target_id in available_target_ids:
                    return target_id, question
                else:
                    logger.warning(f"Bot question generation: Invalid target selected. Bot chose '{target_id}' but available targets are {available_target_ids}")
                    return None

            logger.warning(f"Bot question generation: Invalid response format. Expected target_id and question tags but got: {response}")
            return None

        except Exception as e:
            logger.error(f"Bot question generation: Unexpected error for bot {bot_player_id}: {type(e).__name__}: {e}")
            return None

    async def generate_answer(
        self,
        game_state: Dict[str, Any],
        bot_player_id: str,
        question: str,
        questioner_id: str
    ) -> Optional[str]:
        """
        Generate an answer to a question for a bot player

        Args:
            game_state: Current game state
            bot_player_id: ID of the bot player answering
            question: The question being asked
            questioner_id: ID of the player asking the question

        Returns:
            The answer string or None if error
        """
        try:
            prompt = build_answer_prompt(game_state, bot_player_id, question, questioner_id)
            response = await self.get_xml_completion(prompt, ["answer"], max_tokens=256, temperature=0.7)

            if response and "answer" in response:
                return response["answer"]

            logger.warning(f"Bot answer generation: Invalid response format. Expected answer tag but got: {response}")
            return None

        except Exception as e:
            logger.error(f"Bot answer generation: Unexpected error for bot {bot_player_id} answering '{question}': {type(e).__name__}: {e}")
            return None

    async def should_make_accusation(
        self,
        game_state: Dict[str, Any],
        bot_player_id: str,
        potential_target_ids: List[str]
    ) -> Optional[Tuple[bool, str, str]]:
        """
        Determine if bot should make an accusation and against whom

        Args:
            game_state: Current game state
            bot_player_id: ID of the bot player considering an accusation
            potential_target_ids: List of player IDs that can be accused

        Returns:
            Tuple of (should_accuse, target_id, reasoning) or None if error
        """
        try:
            prompt = build_accusation_prompt(game_state, bot_player_id, potential_target_ids)
            response = await self.get_xml_completion(prompt, ["should_accuse", "target_id"], max_tokens=512, temperature=0.6)

            if response and "should_accuse" in response:
                should_accuse_str = response["should_accuse"].lower()
                target_id = response.get("target_id", "")

                # Convert string to boolean
                if should_accuse_str in ["true", "false"]:
                    should_accuse = should_accuse_str == "true"
                else:
                    logger.warning(f"Bot accusation decision: Invalid should_accuse value. Expected 'true' or 'false' but got: {should_accuse_str}")
                    return False, "", "Invalid accusation decision"

                # Validate target_id if accusation is being made
                if should_accuse and target_id and target_id in potential_target_ids:
                    return True, target_id, ""
                elif not should_accuse:
                    return False, "", ""
                else:
                    logger.warning(f"Bot accusation decision: Invalid target selected. Bot chose '{target_id}' but available targets are {potential_target_ids}")
                    return False, "", "Invalid target selected"

            logger.warning(f"Bot accusation decision: Invalid response format. Expected should_accuse and target_id tags but got: {response}")
            return None

        except Exception as e:
            logger.error(f"Bot accusation decision: Unexpected error for bot {bot_player_id}: {type(e).__name__}: {e}")
            return None

    async def should_vote_guilty(
        self,
        game_state: Dict[str, Any],
        bot_player_id: str,
        accused_id: str,
        accused_name: str
    ) -> Optional[bool]:
        """
        Determine if bot should vote guilty on an accusation

        Args:
            game_state: Current game state
            bot_player_id: ID of the bot player voting
            accused_id: ID of the player being accused
            accused_name: Name of the player being accused

        Returns:
            Tuple of (vote_guilty, reasoning) or None if error
        """
        try:
            prompt = build_voting_prompt(game_state, bot_player_id, accused_id, accused_name)
            response = await self.get_xml_completion(prompt, ["vote_guilty"], max_tokens=512, temperature=0.6)

            if response and "vote_guilty" in response:
                vote_guilty_str = response["vote_guilty"].lower()

                if vote_guilty_str in ["true", "false"]:
                    vote_guilty = vote_guilty_str == "true"
                    return vote_guilty
                else:
                    logger.warning(f"Bot voting decision: Invalid vote_guilty value. Expected 'true' or 'false' but got: {vote_guilty_str}")
                    return None

            logger.warning(f"Bot voting decision: Invalid response format. Expected vote_guilty tag but got: {response}")
            return None

        except Exception as e:
            logger.error(f"Bot voting decision: Unexpected error for bot {bot_player_id} voting on {accused_name}: {type(e).__name__}: {e}")
            return None


# Global client instance
claude_client = ClaudeClient()
