"""
Ollama (local models) provider implementation.
"""

import logging
from collections.abc import AsyncIterator

from ollama import AsyncClient

from ..config import settings
from .base import BaseProvider, ChatMessage, ProviderConfig

logger = logging.getLogger(__name__)


class OllamaProvider(BaseProvider):
    """Ollama local model provider"""

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def default_model(self) -> str:
        return "llama3.2"

    def _get_client(self):
        """Get Ollama client"""
        base_url = self.config.base_url or settings.effective_ollama_url
        return AsyncClient(host=base_url)

    async def is_available(self) -> bool:
        """Check if Ollama is available by trying to connect"""
        try:
            client = self._get_client()
            # Try to list models to check connection
            await client.list()
            return True
        except Exception as e:
            logger.debug(f"Ollama not available: {e}")
            return False

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream chat completion from Ollama"""
        client = self._get_client()
        model = self.config.model or self.default_model

        # Build messages list
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            api_messages.append({"role": msg.role, "content": msg.content})

        try:
            stream = await client.chat(
                model=model,
                messages=api_messages,
                stream=True,
                options={
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens,
                },
            )

            async for chunk in stream:
                if chunk.get("message", {}).get("content"):
                    yield chunk["message"]["content"]

        except Exception as e:
            logger.error(f"Ollama stream error: {e}")
            raise

    async def chat(
        self,
        messages: list[ChatMessage],
        system_prompt: str | None = None,
    ) -> str:
        """Non-streaming chat completion"""
        client = self._get_client()
        model = self.config.model or self.default_model

        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            api_messages.append({"role": msg.role, "content": msg.content})

        response = await client.chat(
            model=model,
            messages=api_messages,
            stream=False,
            options={
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        )

        return response.get("message", {}).get("content", "")

    async def list_models(self) -> list[str]:
        """List available Ollama models"""
        client = self._get_client()
        response = await client.list()
        models = response.get("models", [])

        model_names = [m.get("name", "") for m in models if m.get("name")]
        logger.info(f"Retrieved {len(model_names)} models from Ollama")

        if not model_names:
            raise RuntimeError(
                "Ollama returned no models - make sure you have pulled at least one model"
            )

        return model_names
