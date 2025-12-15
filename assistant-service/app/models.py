"""
Pydantic models for the Assistant Service.

Defines chat messages, provider configurations, and response structures.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum


class ModelProvider(str, Enum):
    """Supported AI model providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"


class ChatRole(str, Enum):
    """Chat message roles"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """A single chat message"""
    role: ChatRole
    content: str
    timestamp: Optional[datetime] = None


class ProviderConfig(BaseModel):
    """Configuration for a specific provider"""
    provider: ModelProvider
    model: str = Field(description="Model name/ID to use")
    api_key: Optional[str] = Field(default=None, description="API key (if not using env var)")
    base_url: Optional[str] = Field(default=None, description="Custom base URL (for Ollama or custom endpoints)")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=32000)


class ChatRequest(BaseModel):
    """Request to chat with the assistant"""
    message: str = Field(description="User's message")
    provider: ModelProvider = Field(default=ModelProvider.OPENAI)
    model: Optional[str] = Field(default=None, description="Model to use (uses default if not specified)")
    conversation_history: List[ChatMessage] = Field(default_factory=list)
    include_network_context: bool = Field(default=True, description="Include network topology as context")
    network_id: Optional[str] = Field(default=None, description="Network ID (UUID) for multi-tenant mode")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=32000)


class ChatResponse(BaseModel):
    """Non-streaming chat response"""
    message: str
    provider: ModelProvider
    model: str
    tokens_used: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StreamChunk(BaseModel):
    """A chunk of streamed response"""
    type: Literal["content", "error", "done"]
    content: Optional[str] = None
    error: Optional[str] = None


class ProviderStatus(BaseModel):
    """Status of a provider"""
    provider: ModelProvider
    available: bool
    configured: bool
    default_model: str
    available_models: List[str] = []
    error: Optional[str] = None


class AssistantConfig(BaseModel):
    """Overall assistant configuration"""
    providers: List[ProviderStatus]
    default_provider: ModelProvider
    network_context_enabled: bool


class NetworkContextSummary(BaseModel):
    """Summary of network context provided to the assistant"""
    total_nodes: int
    healthy_nodes: int
    unhealthy_nodes: int
    gateway_count: int
    snapshot_timestamp: Optional[datetime] = None
    context_tokens_estimate: int = Field(description="Estimated token count of context")
