"""
OpenAI provider implementation.
"""

import logging
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from ..config import settings
from .base import BaseProvider, ProviderConfig, ChatMessage

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """OpenAI API provider"""
    
    @property
    def name(self) -> str:
        return "openai"
    
    @property
    def default_model(self) -> str:
        return "gpt-4o-mini"
    
    def _get_client(self):
        """Get OpenAI client"""
        api_key = self.config.api_key or settings.openai_api_key
        base_url = self.config.base_url or settings.openai_base_url
        
        return AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )
    
    async def is_available(self) -> bool:
        """Check if OpenAI is configured"""
        api_key = self.config.api_key or settings.openai_api_key
        return bool(api_key)
    
    async def stream_chat(
        self,
        messages: list[ChatMessage],
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream chat completion from OpenAI"""
        client = self._get_client()
        model = self.config.model or self.default_model
        
        # Build messages list
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        
        for msg in messages:
            api_messages.append({"role": msg.role, "content": msg.content})
        
        try:
            stream = await client.chat.completions.create(
                model=model,
                messages=api_messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stream=True,
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"OpenAI stream error: {e}")
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
        
        response = await client.chat.completions.create(
            model=model,
            messages=api_messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        
        return response.choices[0].message.content or ""
    
    async def list_models(self) -> list[str]:
        """List available OpenAI models from the API"""
        client = self._get_client()
        models_response = await client.models.list()
        
        # Filter to chat models (gpt-* and o* models that support chat)
        chat_models = []
        for model in models_response.data:
            model_id = model.id
            # Include GPT and O-series models that are chat-capable
            if model_id.startswith(('gpt-4', 'gpt-3.5-turbo', 'o1', 'o3')):
                # Exclude non-chat variants
                if not any(x in model_id for x in ['embedding', 'instruct', 'vision', 'audio', 'realtime', 'transcribe', 'tts']):
                    chat_models.append(model_id)
                    logger.debug(f"Found OpenAI model: {model_id}")
        
        logger.info(f"Retrieved {len(chat_models)} chat models from OpenAI API")
        
        if not chat_models:
            raise RuntimeError("OpenAI API returned no chat models")
        
        # Sort with newest/best models first
        priority_prefixes = ['o3', 'o1', 'gpt-4o', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo']
        
        def sort_key(model_name):
            for i, prefix in enumerate(priority_prefixes):
                if model_name.startswith(prefix):
                    return (i, model_name)
            return (len(priority_prefixes), model_name)
        
        chat_models.sort(key=sort_key)
        return chat_models
