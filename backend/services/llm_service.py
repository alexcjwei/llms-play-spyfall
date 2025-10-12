"""LLM integration service for Claude API"""
import os
import json
import logging
import re
from typing import Optional, Dict, Any, List, Tuple
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with Claude API for bot AI"""

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

    async def query_bot_with_tools(
        self,
        messages: List[Dict[str, Any]],
        bot_id: str,
        available_tools: List[Dict[str, Any]],
        system: str,
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> Optional[Dict[str, Any]]:
        """
        Query bot with available tools using full message history

        Args:
            messages: Full message history
            bot_id: ID of the bot being queried (for logging)
            available_tools: List of available tool definitions
            system: System prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Dictionary containing tool calls and response content, or None if error
        """
        try:
            payload = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system,
                "messages": messages,
                "tools": available_tools,
                "tool_choice": {"type": "any"}  # Force the model to use a tool
            }

            logger.info(f"Querying Claude API for bot {bot_id}")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()

                    # Extract tool calls from Claude's response
                    content = result.get("content", [])
                    tool_calls = []

                    for item in content:
                        if item.get("type") == "tool_use":
                            tool_calls.append({
                                "id": item.get("id"),  # Extract tool use ID
                                "name": item.get("name"),
                                "parameters": item.get("input", {})
                            })

                    # Handle fallback if no tool calls (shouldn't happen with tool_choice: any)
                    if not tool_calls:
                        logger.warning(f"Bot {bot_id} made no tool calls despite tool_choice: any")
                        # Create fallback response based on available tools
                        return self._create_fallback_tool_response(available_tools, bot_id)

                    return {
                        "tool_calls": tool_calls,
                        "response_content": content  # Return full content array
                    }

                else:
                    error_details = {
                        "status_code": response.status_code,
                        "response_text": response.text,
                        "headers": dict(response.headers),
                        "url": str(response.url)
                    }
                    logger.error(f"Claude API HTTP error for bot {bot_id}: {error_details}")
                    return self._create_fallback_tool_response(available_tools, bot_id)

        except httpx.TimeoutException as e:
            logger.error(f"Claude API timeout for bot {bot_id}: {e}")
            return self._create_fallback_tool_response(available_tools, bot_id)
        except httpx.RequestError as e:
            logger.error(f"Claude API request error for bot {bot_id}: {e}")
            return self._create_fallback_tool_response(available_tools, bot_id)
        except Exception as e:
            logger.error(f"Unexpected error querying bot {bot_id} with tools: {type(e).__name__}: {e}")
            return self._create_fallback_tool_response(available_tools, bot_id)

    def _create_fallback_tool_response(self, available_tools: List[Dict[str, Any]], bot_id: str) -> Dict[str, Any]:
        """
        Create a fallback tool response when LLM fails

        Args:
            available_tools: List of available tools
            bot_id: ID of the bot (for logging)

        Returns:
            Fallback tool response
        """
        logger.warning(f"Creating fallback response for bot {bot_id}")

        # Simple fallback logic: choose the first available tool with minimal parameters
        if not available_tools:
            return {"tool_calls": []}

        # Prefer non-accusation tools for fallback to avoid random accusations
        non_accuse_tools = [tool for tool in available_tools if tool.get('name') != 'accuse']

        if non_accuse_tools:
            fallback_tool = non_accuse_tools[0]
        else:
            fallback_tool = available_tools[0]

        tool_name = fallback_tool.get('name')

        # Create minimal parameters based on tool type
        if tool_name == 'ask':
            # Don't create fallback ask - too risky without proper target
            return {"tool_calls": []}
        elif tool_name == 'answer':
            return {
                "tool_calls": [{
                    "name": "answer",
                    "parameters": {
                        "thought": "I need to think about this question.",
                        "answer": "That's an interesting question."
                    }
                }]
            }
        elif tool_name == 'accuse':
            # Don't make fallback accusations - leave target empty
            return {
                "tool_calls": [{
                    "name": "accuse",
                    "parameters": {
                        "thought": "I'm not ready to make an accusation yet.",
                        "target": ""  # Empty target = no accusation
                    }
                }]
            }
        elif tool_name == 'guess_location':
            # Don't make fallback location guesses - too risky
            return {"tool_calls": []}

        return {"tool_calls": []}


# Global service instance
llm_service = LLMService()
