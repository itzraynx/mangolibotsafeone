
"""
GroqCloud AI Integration Module
Provides AI-powered responses using GroqCloud API
"""

import asyncio
import aiohttp
import logging
from typing import Optional

logger = logging.getLogger('GroqAI')

class GroqAI:
    """GroqCloud AI client for generating responses."""

    def __init__(self, api_key: str):
        """
        Initialize the GroqAI client.

        Args:
            api_key: Your GroqCloud API key
        """
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1"
        self.session = None

        # Available free models on GroqCloud
        self.models = {
            "llama3-70b-8192": "llama3-70b-8192",
            "llama3-8b-8192": "llama3-8b-8192",
            "mixtral-8x7b-32768": "mixtral-8x7b-32768",
            "gemma-7b-it": "gemma-7b-it"
        }

        # Default model (fast and free)
        self.default_model = self.models["llama3-70b-8192"]

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def generate_response(
        self,
        message: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> Optional[str]:
        """
        Generate an AI response to the given message.

        Args:
            message: The user's message to respond to
            model: The model to use (defaults to llama2-70b-chat)
            temperature: Response randomness (0.0-1.0)
            max_tokens: Maximum tokens in response

        Returns:
            AI response text or None if error
        """
        if not self.session:
            logger.error("Session not initialized. Use async context manager.")
            return None

        try:
            # Use specified model or default
            model_to_use = model or self.default_model

            payload = {
                "model": model_to_use,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful, friendly, and knowledgeable AI assistant. Provide clear, accurate, and concise responses."
                    },
                    {
                        "role": "user",
                        "content": message
                    }
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            }

            async with self.session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    error_text = await response.text()
                    logger.error(f"Groq API error: {response.status} - {error_text}")
                    return None

        except asyncio.TimeoutError:
            logger.error("Groq API request timed out")
            return None
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return None
