"""
Unit tests for assistant service models.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models import (
    AssistantConfig,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatRole,
    ModelProvider,
    NetworkContextSummary,
    ProviderConfig,
    ProviderStatus,
    StreamChunk,
)


class TestModelProvider:
    """Tests for ModelProvider enum"""

    def test_provider_values(self):
        """Should have expected values"""
        assert ModelProvider.OPENAI.value == "openai"
        assert ModelProvider.ANTHROPIC.value == "anthropic"
        assert ModelProvider.GEMINI.value == "gemini"
        assert ModelProvider.OLLAMA.value == "ollama"


class TestChatRole:
    """Tests for ChatRole enum"""

    def test_role_values(self):
        """Should have expected values"""
        assert ChatRole.USER.value == "user"
        assert ChatRole.ASSISTANT.value == "assistant"
        assert ChatRole.SYSTEM.value == "system"


class TestChatMessage:
    """Tests for ChatMessage model"""

    def test_chat_message(self):
        """Should create chat message"""
        msg = ChatMessage(role=ChatRole.USER, content="Hello", timestamp=datetime.utcnow())
        assert msg.role == ChatRole.USER
        assert msg.content == "Hello"

    def test_chat_message_optional_timestamp(self):
        """Should allow optional timestamp"""
        msg = ChatMessage(role=ChatRole.ASSISTANT, content="Hi")
        assert msg.timestamp is None


class TestProviderConfig:
    """Tests for ProviderConfig model"""

    def test_provider_config(self):
        """Should create provider config"""
        config = ProviderConfig(
            provider=ModelProvider.OPENAI,
            model="gpt-4o",
            api_key="test-key",
            temperature=0.5,
            max_tokens=1024,
        )
        assert config.provider == ModelProvider.OPENAI
        assert config.model == "gpt-4o"

    def test_provider_config_defaults(self):
        """Should use defaults"""
        config = ProviderConfig(provider=ModelProvider.ANTHROPIC, model="claude-3")
        assert config.temperature == 0.7
        assert config.max_tokens == 2048

    def test_provider_config_temperature_validation(self):
        """Should validate temperature range"""
        with pytest.raises(ValidationError):
            ProviderConfig(
                provider=ModelProvider.OPENAI, model="gpt-4o", temperature=3.0  # Invalid: > 2.0
            )


class TestChatRequest:
    """Tests for ChatRequest model"""

    def test_chat_request(self):
        """Should create chat request"""
        req = ChatRequest(
            message="Hello",
            provider=ModelProvider.OPENAI,
            model="gpt-4o",
            include_network_context=True,
        )
        assert req.message == "Hello"
        assert req.provider == ModelProvider.OPENAI

    def test_chat_request_defaults(self):
        """Should use defaults"""
        req = ChatRequest(message="Hi")
        assert req.provider == ModelProvider.OPENAI
        assert req.include_network_context is True
        assert req.conversation_history == []

    def test_chat_request_with_history(self):
        """Should accept conversation history"""
        history = [ChatMessage(role=ChatRole.USER, content="Hello")]
        req = ChatRequest(message="How are you?", conversation_history=history)
        assert len(req.conversation_history) == 1


class TestChatResponse:
    """Tests for ChatResponse model"""

    def test_chat_response(self):
        """Should create chat response"""
        resp = ChatResponse(
            message="Hello!", provider=ModelProvider.ANTHROPIC, model="claude-3", tokens_used=100
        )
        assert resp.message == "Hello!"
        assert resp.tokens_used == 100

    def test_chat_response_timestamp_default(self):
        """Should have default timestamp"""
        resp = ChatResponse(message="Hi", provider=ModelProvider.GEMINI, model="gemini-2.5")
        assert resp.timestamp is not None


class TestStreamChunk:
    """Tests for StreamChunk model"""

    def test_stream_chunk_content(self):
        """Should create content chunk"""
        chunk = StreamChunk(type="content", content="Hello")
        assert chunk.type == "content"
        assert chunk.content == "Hello"

    def test_stream_chunk_error(self):
        """Should create error chunk"""
        chunk = StreamChunk(type="error", error="Something went wrong")
        assert chunk.type == "error"
        assert chunk.error == "Something went wrong"

    def test_stream_chunk_done(self):
        """Should create done chunk"""
        chunk = StreamChunk(type="done")
        assert chunk.type == "done"


class TestProviderStatus:
    """Tests for ProviderStatus model"""

    def test_provider_status(self):
        """Should create provider status"""
        status = ProviderStatus(
            provider=ModelProvider.OPENAI,
            available=True,
            configured=True,
            default_model="gpt-4o",
            available_models=["gpt-4o", "gpt-3.5-turbo"],
        )
        assert status.available is True
        assert len(status.available_models) == 2

    def test_provider_status_with_error(self):
        """Should accept error message"""
        status = ProviderStatus(
            provider=ModelProvider.OLLAMA,
            available=False,
            configured=False,
            default_model="llama3.2",
            error="Not configured",
        )
        assert status.error == "Not configured"


class TestAssistantConfig:
    """Tests for AssistantConfig model"""

    def test_assistant_config(self):
        """Should create assistant config"""
        providers = [
            ProviderStatus(
                provider=ModelProvider.OPENAI,
                available=True,
                configured=True,
                default_model="gpt-4o",
            )
        ]
        config = AssistantConfig(
            providers=providers, default_provider=ModelProvider.OPENAI, network_context_enabled=True
        )
        assert len(config.providers) == 1
        assert config.network_context_enabled is True


class TestNetworkContextSummary:
    """Tests for NetworkContextSummary model"""

    def test_network_context_summary(self):
        """Should create network context summary"""
        summary = NetworkContextSummary(
            total_nodes=10,
            healthy_nodes=8,
            unhealthy_nodes=2,
            gateway_count=1,
            snapshot_timestamp=datetime.utcnow(),
            context_tokens_estimate=500,
        )
        assert summary.total_nodes == 10
        assert summary.context_tokens_estimate == 500

    def test_network_context_summary_optional_timestamp(self):
        """Should allow optional timestamp"""
        summary = NetworkContextSummary(
            total_nodes=5,
            healthy_nodes=5,
            unhealthy_nodes=0,
            gateway_count=1,
            context_tokens_estimate=100,
        )
        assert summary.snapshot_timestamp is None
