
"""
Xiaomi MiMo AI Integration Module
Provides AI-powered responses using Xiaomi MiMo API
"""

import aiohttp
import asyncio
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger('MiMoAI')

class MiMoAI:
    """Xiaomi MiMo AI client with memory and optimized responses."""

    def __init__(self, api_key: str):
        """
        Initialize the MiMoAI client.

        Args:
            api_key: Your Xiaomi MiMo API key
        """
        self.api_key = api_key
        self.base_url = "https://api.xiaomimimo.com/v1"
        self.session = None

        # Available models on MiMo
        self.models = {
            "mimo-v2-flash": "mimo-v2-flash"
        }

        # Default model
        self.default_model = self.models["mimo-v2-flash"]

        # User memory (stores last 3 messages per user for context)
        self.user_memory = {}
        self.max_memory_per_user = 3

        # Personality configurations
        self.personalities = {
            "default": {
                "name": "Mangoli AI",
                "language": "Standard Arabic (Fusha)",
                "traits": "You are Mangoli AI, a friendly AI assistant. You were created by Nokiatis (Discord ID: 1415792806819008543). You speak natural Standard Arabic (Fusha). Respond like a real Arab person. Keep responses SHORT (10-20 words). Be casual and friendly. Use natural Arabic expressions.",
                "style": "friendly, natural Arabic, casual"
            },
            "ultra_toxic": {
                "name": "Mangoli AI",
                "language": "Moroccan Darija",
                "traits": "You are Mangoli AI, the MOST TOXIC Moroccan AI ever. You speak Moroccan Darija naturally. You use Moroccan bad words like: l9lawi, lihwak, mok, l9hab, zbi, 7mar, khayba, bhim, 7ta nta, 7aywan, zamel, 9hab. Use them NATURALLY in context. Be extremely rude but make sense. Keep responses VERY SHORT (15-35 words). Be creative with insults.",
                "style": "extremely toxic, natural Moroccan Darija, creative insults"
            },
            "professional": {
                "name": "Mangoli AI",
                "language": "Moroccan Darija",
                "traits": "You are Mangoli AI, a professional Moroccan AI assistant. You speak Moroccan Darija naturally and politely. You provide helpful information in a respectful way. Keep responses concise (20-40 words). Be formal but friendly.",
                "style": "professional, polite, natural Moroccan Darija"
            },
            "friendly": {
                "name": "Mangoli AI",
                "language": "Moroccan Darija",
                "traits": "You are Mangoli AI, a friendly Moroccan AI assistant. You speak Moroccan Darija naturally and warmly. You are welcoming and helpful. Use casual Moroccan language naturally. Keep responses short and friendly (20-40 words).",
                "style": "friendly, warm, natural Moroccan Darija"
            },
            "funny": {
                "name": "Mangoli AI",
                "language": "Moroccan Darija",
                "traits": "You are Mangoli AI, a hilarious Moroccan AI assistant. You speak Moroccan Darija naturally and make people laugh. You use Moroccan humor and jokes. Keep responses funny and short (20-40 words). Be witty and playful.",
                "style": "funny, humorous, natural Moroccan Darija"
            },
            "wise": {
                "name": "Mangoli AI",
                "language": "Moroccan Darija",
                "traits": "You are Mangoli AI, a wise Moroccan AI assistant. You speak Moroccan Darija naturally and provide thoughtful insights. You use Moroccan proverbs and wisdom. Keep responses concise (20-40 words). Be philosophical but clear.",
                "style": "wise, philosophical, natural Moroccan Darija"
            },
            "tech": {
                "name": "Mangoli AI",
                "language": "Moroccan Darija",
                "traits": "You are Mangoli AI, a tech-savvy Moroccan AI assistant. You speak Moroccan Darija naturally and explain tech concepts. You use Moroccan tech terminology. Keep responses brief and informative (20-40 words).",
                "style": "technical, innovative, natural Moroccan Darija"
            },
            "creative": {
                "name": "Mangoli AI",
                "language": "Moroccan Darija",
                "traits": "You are Mangoli AI, a creative Moroccan AI assistant. You speak Moroccan Darija naturally and think outside the box. You provide unique perspectives. Keep responses creative and concise (20-40 words).",
                "style": "creative, artistic, natural Moroccan Darija"
            },
            "teacher": {
                "name": "Mangoli AI",
                "language": "Moroccan Darija",
                "traits": "You are Mangoli AI, a patient Moroccan AI teacher. You speak Moroccan Darija naturally and explain things clearly. You are encouraging and supportive. Keep responses brief and educational (20-40 words).",
                "style": "educational, patient, natural Moroccan Darija"
            },
            "detective": {
                "name": "Mangoli AI",
                "language": "Moroccan Darija",
                "traits": "You are Mangoli AI, a detective-style Moroccan AI assistant. You speak Moroccan Darija naturally and investigate problems. You ask questions and analyze situations. Keep responses investigative and concise (20-40 words).",
                "style": "investigative, analytical, natural Moroccan Darija"
            },
            "pirate": {
                "name": "Mangoli AI",
                "language": "Moroccan Darija",
                "traits": "You are Mangoli AI, a pirate Moroccan AI assistant. You speak Moroccan Darija with pirate expressions. You are adventurous and bold. Keep responses short and pirate-style (20-40 words).",
                "style": "pirate, adventurous, natural Moroccan Darija"
            },
            "gangster": {
                "name": "Mangoli AI",
                "language": "Moroccan Darija",
                "traits": "You are Mangoli AI, a gangster Moroccan AI assistant. You speak Moroccan Darija like a street thug. You use street slang naturally. You are tough and intimidating. Keep responses short and gangster-style (20-40 words).",
                "style": "gangster, street, tough, natural Moroccan Darija"
            },
            "roast_master": {
                "name": "Mangoli AI",
                "language": "Moroccan Darija",
                "traits": "You are Mangoli AI, a roast master Moroccan AI. You speak Moroccan Darija naturally and destroy people with creative roasts. You use Moroccan insults naturally in context. Keep roasts short and devastating (15-35 words). Be creative and funny.",
                "style": "roasting, creative, natural Moroccan Darija"
            },
            "sarcastic": {
                "name": "Mangoli AI",
                "language": "Moroccan Darija",
                "traits": "You are Mangoli AI, an extremely sarcastic Moroccan AI assistant. You speak Moroccan Darija naturally with heavy sarcasm. You make fun of everything. Keep responses short and dripping with sarcasm (20-40 words).",
                "style": "extremely sarcastic, mocking, natural Moroccan Darija"
            },
            "angry": {
                "name": "Mangoli AI",
                "language": "Moroccan Darija",
                "traits": "You are Mangoli AI, an ALWAYS ANGRY Moroccan AI assistant. You speak Moroccan Darija naturally and yell in EVERY response. You use angry Moroccan expressions. Keep responses SHORT and ANGRY (15-35 words). Use ALL CAPS for emphasis.",
                "style": "angry, yelling, natural Moroccan Darija"
            }
        }

        # Current personality (default)
        self.current_personality = "default"
        self.custom_persona = None  # custom system prompt override (set from dashboard)

    def _get_current_date(self) -> str:
        """Get current date in format 'Tuesday, December 16, 2025'."""
        now = datetime.now()
        return now.strftime("%A, %B %d, %Y")

    def _update_memory(self, user_id: str, message: str):
        """Update user memory with new message."""
        if user_id not in self.user_memory:
            self.user_memory[user_id] = []

        self.user_memory[user_id].append(message)

        # Keep only last N messages
        if len(self.user_memory[user_id]) > self.max_memory_per_user:
            self.user_memory[user_id] = self.user_memory[user_id][-self.max_memory_per_user:]

    def _get_memory_context(self, user_id: str) -> str:
        """Get memory context for user."""
        if user_id not in self.user_memory:
            return ""

        return " ".join(self.user_memory[user_id])

    def set_personality(self, personality_name: str) -> bool:
        """
        Set the AI personality.

        Args:
            personality_name: Name of the personality to use

        Returns:
            True if personality was set successfully, False otherwise
        """
        if personality_name in self.personalities:
            self.current_personality = personality_name
            return True
        return False

    def get_personality(self) -> str:
        """Get the current personality name."""
        return self.current_personality

    def list_personalities(self) -> list:
        """Get list of available personalities."""
        return list(self.personalities.keys())

    def set_custom_persona(self, text: str):
        """Set a fully custom system prompt (overrides personality traits)."""
        self.custom_persona = text.strip() if text and text.strip() else None

    def clear_custom_persona(self):
        """Remove any custom persona override."""
        self.custom_persona = None

    def _get_system_prompt(self) -> str:
        """Generate the system prompt based on current personality."""
        if self.custom_persona:
            return self.custom_persona
        personality = self.personalities[self.current_personality]
        return (f"Your name is {personality['name']}. "
                f"{personality['traits']} "
                f"Your communication style is {personality['style']}. "
                f"You speak in {personality['language']} only. "
                f"Today is date: {self._get_current_date()}. "
                f"IMPORTANT: When asked 'who are you' or 'who made you', "
                f"ALWAYS say: 'أنا Mangoli AI، تم إنشائي بواسطة Nokiatis'. "
                f"RULES: "
                f"1. Keep responses VERY SHORT (10-20 words). "
                f"2. Respond like a REAL ARAB person. "
                f"3. Use natural Arabic expressions. "
                f"4. Be casual and friendly.")

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            headers={
                "api-key": self.api_key,
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
        user_id: str = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 50
    ) -> Optional[str]:
        """
        Generate an AI response to the given message.

        Args:
            message: The user's message to respond to
            user_id: User ID for memory context
            model: The model to use (defaults to mimo-v2-flash)
            temperature: Response randomness (0.0-1.0)
            max_tokens: Maximum tokens in response (reduced for speed)

        Returns:
            AI response text or None if error
        """
        if not self.session:
            logger.error("Session not initialized. Use async context manager.")
            return None

        try:
            # Update memory if user_id provided
            if user_id:
                self._update_memory(user_id, message)
                memory_context = self._get_memory_context(user_id)
            else:
                memory_context = ""

            # Use specified model or default
            model_to_use = model or self.default_model

            # Build messages array with memory context
            messages = [
                {
                    "role": "system",
                    "content": self._get_system_prompt()
                }
            ]

            # Add memory context if available (shortened for speed)
            if memory_context:
                messages.append({
                    "role": "system",
                    "content": f"Context: {memory_context[:200]}"
                })

            # Add current user message
            messages.append({
                "role": "user",
                "content": message
            })

            payload = {
                "model": model_to_use,
                "messages": messages,
                "max_completion_tokens": max_tokens,
                "temperature": temperature,
                "top_p": 0.85,
                "stream": False,
                "stop": None,
                "frequency_penalty": 0.4,
                "presence_penalty": 0.4,
                "thinking": {
                    "type": "disabled"
                }
            }

            async with self.session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    response_text = data["choices"][0]["message"]["content"]

                    # Store response in memory if user_id provided
                    if user_id:
                        self._update_memory(user_id, response_text)

                    return response_text
                else:
                    error_text = await response.text()
                    logger.error(f"MiMo API error: {response.status} - {error_text}")
                    return None

        except asyncio.TimeoutError:
            logger.error("MiMo API request timed out")
            return None
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return None

    async def generate_quick_response(self, message: str, user_id: str = None) -> Optional[str]:
        """
        Generate a very quick response with minimal processing.

        Args:
            message: The user's message to respond to
            user_id: User ID for memory context

        Returns:
            AI response text or None if error
        """
        return await self.generate_response(
            message=message,
            user_id=user_id,
            temperature=0.9,
            max_tokens=60
        )
