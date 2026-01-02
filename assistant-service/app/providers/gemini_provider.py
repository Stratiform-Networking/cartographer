"""
Google Gemini provider implementation.
"""

import logging
from collections.abc import AsyncIterator

import google.generativeai as genai

from ..config import settings
from .base import BaseProvider, ChatMessage, ProviderConfig

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    """Google Gemini API provider"""

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return "gemini-2.5-flash"

    def _configure_genai(self):
        """Configure Google Generative AI"""
        api_key = self.config.api_key or settings.effective_google_api_key
        genai.configure(api_key=api_key)
        return genai

    async def is_available(self) -> bool:
        """Check if Gemini is configured"""
        api_key = self.config.api_key or settings.effective_google_api_key
        return bool(api_key)

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream chat completion from Gemini"""
        genai = self._configure_genai()
        model_name = self.config.model or self.default_model

        # Create model with system instruction
        generation_config = genai.types.GenerationConfig(
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_tokens,
        )

        model = genai.GenerativeModel(
            model_name,
            generation_config=generation_config,
            system_instruction=system_prompt,
        )

        # Convert messages to Gemini format
        # Gemini uses 'user' and 'model' roles
        history = []
        for msg in messages[:-1]:  # All but last message
            role = "model" if msg.role == "assistant" else "user"
            history.append({"role": role, "parts": [msg.content]})

        # Start chat with history
        chat = model.start_chat(history=history)

        # Get last user message
        last_message = messages[-1].content if messages else ""

        try:
            response = await chat.send_message_async(last_message, stream=True)

            async for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Gemini stream error: {e}")
            raise

    async def chat(
        self,
        messages: list[ChatMessage],
        system_prompt: str | None = None,
    ) -> str:
        """Non-streaming chat completion"""
        genai = self._configure_genai()
        model_name = self.config.model or self.default_model

        generation_config = genai.types.GenerationConfig(
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_tokens,
        )

        model = genai.GenerativeModel(
            model_name,
            generation_config=generation_config,
            system_instruction=system_prompt,
        )

        # Convert messages
        history = []
        for msg in messages[:-1]:
            role = "model" if msg.role == "assistant" else "user"
            history.append({"role": role, "parts": [msg.content]})

        chat = model.start_chat(history=history)
        last_message = messages[-1].content if messages else ""

        response = await chat.send_message_async(last_message)
        return response.text

    async def list_models(self) -> list[str]:
        """List available Gemini models from the API"""
        genai = self._configure_genai()

        # List models from the API
        chat_models = []
        for model in genai.list_models():
            model_name = model.name
            # Model names come as "models/gemini-1.5-flash" - extract just the model ID
            if model_name.startswith("models/"):
                model_id = model_name[7:]  # Remove "models/" prefix
            else:
                model_id = model_name

            # Filter to generative models that support chat/generateContent
            supported_methods = getattr(model, "supported_generation_methods", [])
            if (
                "generateContent" in supported_methods
                or "streamGenerateContent" in supported_methods
            ):
                # Include gemini models, exclude embedding/vision-only models
                if "gemini" in model_id.lower():
                    if not any(x in model_id.lower() for x in ["embedding", "aqa"]):
                        chat_models.append(model_id)
                        logger.debug(f"Found Gemini model: {model_id}")

        logger.info(f"Retrieved {len(chat_models)} models from Gemini API")

        if not chat_models:
            raise RuntimeError("Gemini API returned no models")

        # Sort with newest/best models first
        def sort_key(model_name):
            # Priority: 2.0 > 1.5 > 1.0, pro > flash
            version_priority = 0
            if "2.0" in model_name or "2-0" in model_name:
                version_priority = 0
            elif "1.5" in model_name or "1-5" in model_name:
                version_priority = 1
            else:
                version_priority = 2

            # flash-8b < flash < pro
            type_priority = 0
            if "pro" in model_name.lower():
                type_priority = 0
            elif "flash-8b" in model_name.lower():
                type_priority = 2
            elif "flash" in model_name.lower():
                type_priority = 1
            else:
                type_priority = 3

            return (version_priority, type_priority, model_name)

        chat_models.sort(key=sort_key)

        # Remove duplicates while preserving order
        seen = set()
        unique_models = []
        for m in chat_models:
            if m not in seen:
                seen.add(m)
                unique_models.append(m)

        return unique_models
