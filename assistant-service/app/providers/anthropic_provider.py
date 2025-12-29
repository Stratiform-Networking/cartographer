"""
Anthropic (Claude) provider implementation.
"""

import asyncio
import logging
from collections.abc import AsyncIterator

from anthropic import Anthropic
from anthropic import AsyncAnthropic

from ..config import settings
from .base import BaseProvider, ProviderConfig, ChatMessage

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    """Anthropic Claude API provider"""
    
    @property
    def name(self) -> str:
        return "anthropic"
    
    @property
    def default_model(self) -> str:
        return "claude-sonnet-4-20250514"
    
    def _get_client(self):
        """Get Anthropic client"""
        api_key = self.config.api_key or settings.anthropic_api_key
        base_url = self.config.base_url or settings.anthropic_base_url
        
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
            
        return AsyncAnthropic(**kwargs)
    
    def _get_sync_client(self):
        """Get sync Anthropic client for operations that work better synchronously"""
        api_key = self.config.api_key or settings.anthropic_api_key
        base_url = self.config.base_url or settings.anthropic_base_url
        
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
            
        return Anthropic(**kwargs)
    
    async def is_available(self) -> bool:
        """Check if Anthropic is configured"""
        api_key = self.config.api_key or settings.anthropic_api_key
        return bool(api_key)
    
    async def stream_chat(
        self,
        messages: list[ChatMessage],
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream chat completion from Anthropic"""
        client = self._get_client()
        model = self.config.model or self.default_model
        
        # Build messages list (Anthropic uses separate system parameter)
        api_messages = []
        for msg in messages:
            api_messages.append({"role": msg.role, "content": msg.content})
        
        try:
            async with client.messages.stream(
                model=model,
                messages=api_messages,
                system=system_prompt or "",
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            logger.error(f"Anthropic stream error: {e}")
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
        for msg in messages:
            api_messages.append({"role": msg.role, "content": msg.content})
        
        response = await client.messages.create(
            model=model,
            messages=api_messages,
            system=system_prompt or "",
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )
        
        # Extract text from content blocks
        return "".join(
            block.text for block in response.content 
            if hasattr(block, 'text')
        )
    
    async def list_models(self) -> list[str]:
        """List available Anthropic models using the Models API"""
        # Use sync client in a thread pool to avoid async issues with the models API
        def fetch_models_sync():
            client = self._get_sync_client()
            all_models = []
            after_id = None
            
            while True:
                # Call models.list with pagination
                if after_id:
                    page = client.models.list(limit=100, after_id=after_id)
                else:
                    page = client.models.list(limit=100)
                
                # Collect model IDs
                for model in page.data:
                    model_id = model.id
                    logger.debug(f"Found Anthropic model: {model_id}")
                    all_models.append(model_id)
                
                # Check for more pages
                if not page.has_more:
                    break
                
                after_id = page.last_id
            
            return all_models
        
        # Run sync function in thread pool
        loop = asyncio.get_event_loop()
        all_models = await loop.run_in_executor(None, fetch_models_sync)
        
        logger.info(f"Retrieved {len(all_models)} models from Anthropic API")
        
        if not all_models:
            raise RuntimeError("Anthropic API returned no models")
        
        # Sort with newest/best models first
        def sort_key(model_name: str):
            # Priority by model family (newest first)
            version_priority = 10
            if 'sonnet-4' in model_name or 'claude-4' in model_name:
                version_priority = 0
            elif '3-7' in model_name or '3.7' in model_name:
                version_priority = 1
            elif '3-5' in model_name or '3.5' in model_name:
                version_priority = 2
            elif 'opus' in model_name:
                version_priority = 3
            elif '3' in model_name:
                version_priority = 4
            
            # Model type priority
            type_priority = 5
            if 'sonnet' in model_name:
                type_priority = 0
            elif 'haiku' in model_name:
                type_priority = 1
            elif 'opus' in model_name:
                type_priority = 2
            
            # Get date suffix if present (newer dates first)
            date_suffix = 0
            parts = model_name.split('-')
            for part in reversed(parts):
                if part.isdigit() and len(part) == 8:
                    date_suffix = int(part)
                    break
            
            return (version_priority, type_priority, -date_suffix, model_name)
        
        all_models.sort(key=sort_key)
        return all_models
