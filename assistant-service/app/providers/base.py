"""
Base provider interface for AI model providers.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class ProviderConfig:
    """Configuration passed to providers"""
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int = 2048


@dataclass
class ChatMessage:
    """Simple chat message for providers"""
    role: str  # "user", "assistant", "system"
    content: str


class BaseProvider(ABC):
    """Base class for AI model providers"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name"""
        pass
    
    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model for this provider"""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider is available/configured"""
        pass
    
    @abstractmethod
    async def stream_chat(
        self,
        messages: list[ChatMessage],
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream chat completion response"""
        pass
    
    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        system_prompt: str | None = None,
    ) -> str:
        """Non-streaming chat completion"""
        pass
    
    async def list_models(self) -> list[str]:
        """List available models (optional implementation)"""
        return [self.default_model]
