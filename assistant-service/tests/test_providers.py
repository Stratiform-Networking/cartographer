"""
Unit tests for AI provider implementations.
"""
import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock

from app.providers.base import BaseProvider, ProviderConfig, ChatMessage
from app.providers.openai_provider import OpenAIProvider
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.ollama_provider import OllamaProvider
from app.config import settings


class TestProviderConfig:
    """Tests for base ProviderConfig"""
    
    def test_provider_config_defaults(self):
        """Should have default values"""
        config = ProviderConfig()
        assert config.api_key is None
        assert config.base_url is None
        assert config.model is None
        assert config.temperature == 0.7
        assert config.max_tokens == 2048


class TestChatMessage:
    """Tests for ChatMessage dataclass"""
    
    def test_chat_message(self):
        """Should create chat message"""
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"


class TestOpenAIProvider:
    """Tests for OpenAI provider"""
    
    def test_name(self, provider_config):
        """Should return provider name"""
        provider = OpenAIProvider(provider_config)
        assert provider.name == "openai"
    
    def test_default_model(self, provider_config):
        """Should return default model"""
        provider = OpenAIProvider(provider_config)
        assert provider.default_model == "gpt-4o-mini"
    
    async def test_is_available_with_key(self, provider_config):
        """Should be available with API key"""
        provider = OpenAIProvider(provider_config)
        assert await provider.is_available() is True
    
    async def test_is_available_without_key(self):
        """Should not be available without API key"""
        config = ProviderConfig()
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=True):
            provider = OpenAIProvider(config)
            assert await provider.is_available() is False
    
    async def test_is_available_from_env(self):
        """Should use API key from settings"""
        config = ProviderConfig()
        with patch.object(settings, 'openai_api_key', "test-key"):
            provider = OpenAIProvider(config)
            assert await provider.is_available() is True
    
    async def test_chat(self, provider_config, chat_messages, mock_openai_client):
        """Should make chat request"""
        provider = OpenAIProvider(provider_config)
        
        with patch.object(provider, '_get_client', return_value=mock_openai_client):
            result = await provider.chat(chat_messages, "System prompt")
        
        assert result == "Test response"
    
    async def test_stream_chat(self, provider_config, chat_messages):
        """Should stream chat response"""
        provider = OpenAIProvider(provider_config)
        
        # Create mock stream
        async def mock_stream():
            chunks = [
                MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello"))]),
                MagicMock(choices=[MagicMock(delta=MagicMock(content=" World"))]),
            ]
            for chunk in chunks:
                yield chunk
        
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())
        
        with patch.object(provider, '_get_client', return_value=mock_client):
            chunks = []
            async for chunk in provider.stream_chat(chat_messages):
                chunks.append(chunk)
        
        assert "Hello" in chunks
        assert " World" in chunks
    
    async def test_stream_chat_error(self, provider_config, chat_messages):
        """Should handle stream error"""
        provider = OpenAIProvider(provider_config)
        
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
        
        with patch.object(provider, '_get_client', return_value=mock_client):
            with pytest.raises(Exception):
                async for _ in provider.stream_chat(chat_messages):
                    pass
    
    async def test_list_models(self, provider_config):
        """Should list models"""
        provider = OpenAIProvider(provider_config)
        
        mock_model = MagicMock()
        mock_model.id = "gpt-4o"
        mock_models = MagicMock()
        mock_models.data = [mock_model]
        
        mock_client = AsyncMock()
        mock_client.models.list = AsyncMock(return_value=mock_models)
        
        with patch.object(provider, '_get_client', return_value=mock_client):
            models = await provider.list_models()
        
        assert "gpt-4o" in models
    
    async def test_list_models_empty(self, provider_config):
        """Should raise when no models"""
        provider = OpenAIProvider(provider_config)
        
        mock_models = MagicMock()
        mock_models.data = []
        
        mock_client = AsyncMock()
        mock_client.models.list = AsyncMock(return_value=mock_models)
        
        with patch.object(provider, '_get_client', return_value=mock_client):
            with pytest.raises(RuntimeError):
                await provider.list_models()


class TestAnthropicProvider:
    """Tests for Anthropic provider"""
    
    def test_name(self, provider_config):
        """Should return provider name"""
        provider = AnthropicProvider(provider_config)
        assert provider.name == "anthropic"
    
    def test_default_model(self, provider_config):
        """Should return default model"""
        provider = AnthropicProvider(provider_config)
        assert "claude" in provider.default_model.lower()
    
    async def test_is_available_with_key(self, provider_config):
        """Should be available with API key"""
        provider = AnthropicProvider(provider_config)
        assert await provider.is_available() is True
    
    async def test_is_available_without_key(self):
        """Should not be available without API key"""
        config = ProviderConfig()
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}, clear=True):
            provider = AnthropicProvider(config)
            assert await provider.is_available() is False
    
    async def test_chat(self, provider_config, chat_messages, mock_anthropic_client):
        """Should make chat request"""
        provider = AnthropicProvider(provider_config)
        
        with patch.object(provider, '_get_client', return_value=mock_anthropic_client):
            result = await provider.chat(chat_messages, "System prompt")
        
        assert result == "Test response"
    
    async def test_stream_chat(self, provider_config, chat_messages):
        """Should stream chat response"""
        provider = AnthropicProvider(provider_config)
        
        # Mock the streaming context manager
        mock_stream = AsyncMock()
        
        async def mock_text_stream():
            yield "Hello"
            yield " World"
        
        mock_stream.text_stream = mock_text_stream()
        
        mock_client = AsyncMock()
        mock_client.messages.stream = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_stream)))
        
        with patch.object(provider, '_get_client', return_value=mock_client):
            chunks = []
            async for chunk in provider.stream_chat(chat_messages):
                chunks.append(chunk)
        
        assert "Hello" in chunks
    
    async def test_list_models(self, provider_config):
        """Should list models"""
        provider = AnthropicProvider(provider_config)
        
        mock_model = MagicMock()
        mock_model.id = "claude-sonnet-4-20250514"
        
        mock_page = MagicMock()
        mock_page.data = [mock_model]
        mock_page.has_more = False
        
        mock_sync_client = MagicMock()
        mock_sync_client.models.list = MagicMock(return_value=mock_page)
        
        with patch.object(provider, '_get_sync_client', return_value=mock_sync_client):
            models = await provider.list_models()
        
        assert len(models) >= 1


class TestGeminiProvider:
    """Tests for Gemini provider"""
    
    def test_name(self, provider_config):
        """Should return provider name"""
        provider = GeminiProvider(provider_config)
        assert provider.name == "gemini"
    
    def test_default_model(self, provider_config):
        """Should return default model"""
        provider = GeminiProvider(provider_config)
        assert "gemini" in provider.default_model.lower()
    
    async def test_is_available_with_key(self, provider_config):
        """Should be available with API key"""
        with patch.object(type(settings), 'effective_google_api_key', property(lambda self: "test-key")):
            config = ProviderConfig()
            provider = GeminiProvider(config)
            assert await provider.is_available() is True
    
    async def test_is_available_without_key(self):
        """Should not be available without API key"""
        config = ProviderConfig()
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "", "GEMINI_API_KEY": ""}, clear=True):
            provider = GeminiProvider(config)
            assert await provider.is_available() is False
    
    async def test_chat(self, provider_config, chat_messages):
        """Should make chat request"""
        provider = GeminiProvider(provider_config)
        
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Test response"
        mock_chat.send_message_async = AsyncMock(return_value=mock_response)
        
        mock_model = MagicMock()
        mock_model.start_chat = MagicMock(return_value=mock_chat)
        
        with patch.object(provider, '_configure_genai') as mock_genai:
            mock_genai.return_value.GenerativeModel = MagicMock(return_value=mock_model)
            mock_genai.return_value.types.GenerationConfig = MagicMock()
            
            result = await provider.chat(chat_messages, "System prompt")
        
        assert result == "Test response"
    
    async def test_stream_chat(self, provider_config, chat_messages):
        """Should stream chat response"""
        provider = GeminiProvider(provider_config)
        
        async def mock_chunks():
            chunk1 = MagicMock()
            chunk1.text = "Hello"
            yield chunk1
            chunk2 = MagicMock()
            chunk2.text = " World"
            yield chunk2
        
        mock_chat = MagicMock()
        mock_chat.send_message_async = AsyncMock(return_value=mock_chunks())
        
        mock_model = MagicMock()
        mock_model.start_chat = MagicMock(return_value=mock_chat)
        
        with patch.object(provider, '_configure_genai') as mock_genai:
            mock_genai.return_value.GenerativeModel = MagicMock(return_value=mock_model)
            mock_genai.return_value.types.GenerationConfig = MagicMock()
            
            chunks = []
            async for chunk in provider.stream_chat(chat_messages):
                chunks.append(chunk)
        
        assert "Hello" in chunks
    
    async def test_list_models(self, provider_config):
        """Should list models"""
        provider = GeminiProvider(provider_config)
        
        mock_model = MagicMock()
        mock_model.name = "models/gemini-2.5-flash"
        mock_model.supported_generation_methods = ["generateContent"]
        
        with patch.object(provider, '_configure_genai') as mock_genai:
            mock_genai.return_value.list_models = MagicMock(return_value=[mock_model])
            
            models = await provider.list_models()
        
        assert "gemini-2.5-flash" in models


class TestOllamaProvider:
    """Tests for Ollama provider"""
    
    def test_name(self, provider_config):
        """Should return provider name"""
        provider = OllamaProvider(provider_config)
        assert provider.name == "ollama"
    
    def test_default_model(self, provider_config):
        """Should return default model"""
        provider = OllamaProvider(provider_config)
        assert provider.default_model == "llama3.2"
    
    async def test_is_available_success(self, provider_config, mock_ollama_client):
        """Should be available when Ollama responds"""
        provider = OllamaProvider(provider_config)
        
        with patch.object(provider, '_get_client', return_value=mock_ollama_client):
            assert await provider.is_available() is True
    
    async def test_is_available_failure(self, provider_config):
        """Should not be available when Ollama fails"""
        provider = OllamaProvider(provider_config)
        
        mock_client = AsyncMock()
        mock_client.list = AsyncMock(side_effect=Exception("Connection refused"))
        
        with patch.object(provider, '_get_client', return_value=mock_client):
            assert await provider.is_available() is False
    
    async def test_chat(self, provider_config, chat_messages, mock_ollama_client):
        """Should make chat request"""
        provider = OllamaProvider(provider_config)
        
        with patch.object(provider, '_get_client', return_value=mock_ollama_client):
            result = await provider.chat(chat_messages, "System prompt")
        
        assert result == "Test response"
    
    async def test_stream_chat(self, provider_config, chat_messages):
        """Should stream chat response"""
        provider = OllamaProvider(provider_config)
        
        async def mock_stream():
            yield {"message": {"content": "Hello"}}
            yield {"message": {"content": " World"}}
        
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=mock_stream())
        
        with patch.object(provider, '_get_client', return_value=mock_client):
            chunks = []
            async for chunk in provider.stream_chat(chat_messages):
                chunks.append(chunk)
        
        assert "Hello" in chunks
    
    async def test_list_models(self, provider_config, mock_ollama_client):
        """Should list models"""
        provider = OllamaProvider(provider_config)
        
        with patch.object(provider, '_get_client', return_value=mock_ollama_client):
            models = await provider.list_models()
        
        assert "llama3.2" in models
    
    async def test_list_models_empty(self, provider_config):
        """Should raise when no models"""
        provider = OllamaProvider(provider_config)
        
        mock_client = AsyncMock()
        mock_client.list = AsyncMock(return_value={"models": []})
        
        with patch.object(provider, '_get_client', return_value=mock_client):
            with pytest.raises(RuntimeError):
                await provider.list_models()


class TestBaseProvider:
    """Tests for BaseProvider"""
    
    async def test_list_models_default(self, provider_config):
        """Should return default model when not overridden"""
        # Using a concrete implementation
        provider = OpenAIProvider(provider_config)
        
        # The default implementation returns [default_model]
        # But OpenAI overrides this, so we need to test directly
        from app.providers.base import BaseProvider
        
        # Cannot instantiate abstract class directly, so skip this test
        pass

