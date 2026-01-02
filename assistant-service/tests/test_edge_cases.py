"""
Edge case tests for additional coverage.
"""

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.dependencies.auth import AuthenticatedUser, UserRole, require_auth
from app.providers.base import ChatMessage, ProviderConfig
from app.services.metrics_context import MetricsContextService

# Mock user for auth
_mock_user = AuthenticatedUser(user_id="test-user-123", username="testuser", role=UserRole.MEMBER)


async def mock_require_auth():
    """Mock auth dependency"""
    return _mock_user


def create_test_app_with_auth():
    """Create a test app with mocked auth"""
    from fastapi import FastAPI

    from app.routers.assistant import require_chat_auth, router

    app = FastAPI()
    app.include_router(router, prefix="/api")

    # Override auth dependencies
    app.dependency_overrides[require_auth] = mock_require_auth
    app.dependency_overrides[require_chat_auth] = mock_require_auth

    return app


class TestProviderEdgeCases:
    """Edge case tests for providers"""

    async def test_openai_get_client_with_base_url(self):
        """Should use custom base URL"""
        from app.providers.openai_provider import OpenAIProvider

        config = ProviderConfig(api_key="test-key", base_url="https://custom.api.com")
        provider = OpenAIProvider(config)

        with patch("app.providers.openai_provider.AsyncOpenAI") as mock_class:
            provider._get_client()
            mock_class.assert_called_once_with(
                api_key="test-key", base_url="https://custom.api.com"
            )

    async def test_openai_list_models_filters(self):
        """Should filter non-chat models"""
        from app.providers.openai_provider import OpenAIProvider

        config = ProviderConfig(api_key="test-key")
        provider = OpenAIProvider(config)

        # Create various model types
        models = []
        for model_id in ["gpt-4o", "gpt-3.5-turbo", "text-embedding-ada", "gpt-4-vision", "tts-1"]:
            mock_model = MagicMock()
            mock_model.id = model_id
            models.append(mock_model)

        mock_models = MagicMock()
        mock_models.data = models

        mock_client = AsyncMock()
        mock_client.models.list = AsyncMock(return_value=mock_models)

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.list_models()

        assert "gpt-4o" in result
        assert "gpt-3.5-turbo" in result
        assert "text-embedding-ada" not in result

    async def test_anthropic_get_client_with_base_url(self):
        """Should use custom base URL for Anthropic"""
        from app.providers.anthropic_provider import AnthropicProvider

        config = ProviderConfig(api_key="test-key", base_url="https://custom.anthropic.com")
        provider = AnthropicProvider(config)

        with patch("app.providers.anthropic_provider.AsyncAnthropic") as mock_class:
            provider._get_client()
            mock_class.assert_called_once()

    async def test_anthropic_list_models_pagination(self):
        """Should handle pagination in list_models"""
        from app.providers.anthropic_provider import AnthropicProvider

        config = ProviderConfig(api_key="test-key")
        provider = AnthropicProvider(config)

        # Mock paginated response
        mock_model = MagicMock()
        mock_model.id = "claude-3-sonnet"

        mock_page = MagicMock()
        mock_page.data = [mock_model]
        mock_page.has_more = False

        mock_sync_client = MagicMock()
        mock_sync_client.models.list = MagicMock(return_value=mock_page)

        with patch.object(provider, "_get_sync_client", return_value=mock_sync_client):
            result = await provider.list_models()

        assert len(result) >= 1

    async def test_anthropic_list_models_empty(self):
        """Should raise on empty models"""
        from app.providers.anthropic_provider import AnthropicProvider

        config = ProviderConfig(api_key="test-key")
        provider = AnthropicProvider(config)

        mock_page = MagicMock()
        mock_page.data = []
        mock_page.has_more = False

        mock_sync_client = MagicMock()
        mock_sync_client.models.list = MagicMock(return_value=mock_page)

        with patch.object(provider, "_get_sync_client", return_value=mock_sync_client):
            with pytest.raises(RuntimeError):
                await provider.list_models()

    async def test_gemini_list_models_filters(self):
        """Should filter non-chat Gemini models"""
        from app.providers.gemini_provider import GeminiProvider

        config = ProviderConfig(api_key="test-key")
        provider = GeminiProvider(config)

        # Mock models with different capabilities
        mock_chat_model = MagicMock()
        mock_chat_model.name = "models/gemini-2.5-flash"
        mock_chat_model.supported_generation_methods = ["generateContent"]

        mock_embed_model = MagicMock()
        mock_embed_model.name = "models/embedding-001"
        mock_embed_model.supported_generation_methods = ["embedContent"]

        with patch.object(provider, "_configure_genai") as mock_genai:
            mock_genai.return_value.list_models = MagicMock(
                return_value=[mock_chat_model, mock_embed_model]
            )

            result = await provider.list_models()

        assert "gemini-2.5-flash" in result
        assert "embedding-001" not in result

    async def test_gemini_list_models_empty(self):
        """Should raise on empty models"""
        from app.providers.gemini_provider import GeminiProvider

        config = ProviderConfig(api_key="test-key")
        provider = GeminiProvider(config)

        with patch.object(provider, "_configure_genai") as mock_genai:
            mock_genai.return_value.list_models = MagicMock(return_value=[])

            with pytest.raises(RuntimeError):
                await provider.list_models()

    async def test_ollama_get_client_default_url(self):
        """Should use default URL for Ollama"""
        from app.providers.ollama_provider import OllamaProvider

        config = ProviderConfig()
        provider = OllamaProvider(config)

        with patch.dict(os.environ, {"OLLAMA_BASE_URL": "", "OLLAMA_HOST": ""}, clear=True):
            with patch("app.providers.ollama_provider.AsyncClient") as mock_class:
                provider._get_client()
                mock_class.assert_called_once_with(host="http://localhost:11434")

    async def test_ollama_stream_chat_error(self):
        """Should handle stream error"""
        from app.providers.ollama_provider import OllamaProvider

        config = ProviderConfig(api_key="test-key")
        provider = OllamaProvider(config)
        messages = [ChatMessage(role="user", content="Hello")]

        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(side_effect=Exception("Stream error"))

        with patch.object(provider, "_get_client", return_value=mock_client):
            with pytest.raises(Exception):
                async for _ in provider.stream_chat(messages):
                    pass


class TestMetricsContextEdgeCases:
    """Edge case tests for MetricsContextService"""

    async def test_format_gateway_test_ips_dict_status(self):
        """Should handle status as dict"""
        service = MetricsContextService()

        gateway = {
            "gateway_ip": "192.168.1.1",
            "test_ips": [{"ip": "8.8.8.8", "label": "Google", "status": {"value": "healthy"}}],
            "last_speed_test": None,
        }

        result = service._format_gateway_info(gateway, {})

        assert "8.8.8.8" in result

    async def test_format_speed_test_partial_data(self):
        """Should handle partial speed test data"""
        service = MetricsContextService()

        gateway = {
            "gateway_ip": "192.168.1.1",
            "test_ips": [],
            "last_speed_test": {
                "success": True,
                "download_mbps": None,
                "upload_mbps": 50.0,
                "ping_ms": None,
            },
        }

        result = service._format_gateway_info(gateway, {})

        assert "50.0" in result

    async def test_format_speed_test_with_server_info(self):
        """Should include server info in speed test"""
        service = MetricsContextService()

        gateway = {
            "gateway_ip": "192.168.1.1",
            "test_ips": [],
            "last_speed_test": {
                "success": True,
                "download_mbps": 100.0,
                "upload_mbps": 50.0,
                "ping_ms": 15.0,
                "server_sponsor": "TestSponsor",
                "server_location": "NYC",
            },
        }

        result = service._format_gateway_info(gateway, {})

        assert "TestSponsor" in result

    async def test_format_node_with_all_features(self):
        """Should format node with all features"""
        service = MetricsContextService()

        node = {
            "name": "Test Node",
            "ip": "192.168.1.1",
            "role": "server",
            "status": "healthy",
            "hostname": "test.local",
            "connection_speed": "1GbE",
            "ping": {"success": True, "avg_latency_ms": 5.0},
            "uptime": {"uptime_percent_24h": 99.9},
            "open_ports": [
                {"port": 80, "service": "HTTP"},
                {"port": 443, "service": "HTTPS"},
                {"port": 22, "service": "SSH"},
                {"port": 3306, "service": "MySQL"},
                {"port": 5432, "service": "PostgreSQL"},
                {"port": 6379},  # No service name
            ],
            "notes": "Important server",
        }

        result = service._format_node_info(node)

        assert "test.local" in result
        assert "1GbE" in result
        assert "99.9%" in result
        assert "Important server" in result

    async def test_build_context_with_roles(self):
        """Should organize nodes by role"""
        service = MetricsContextService()

        snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_nodes": 4,
            "healthy_nodes": 4,
            "degraded_nodes": 0,
            "unhealthy_nodes": 0,
            "unknown_nodes": 0,
            "nodes": {
                "gw": {
                    "id": "gw",
                    "name": "Gateway",
                    "ip": "192.168.1.1",
                    "role": "gateway/router",
                    "status": "healthy",
                },
                "fw": {
                    "id": "fw",
                    "name": "Firewall",
                    "ip": "192.168.1.2",
                    "role": "firewall",
                    "status": "healthy",
                },
                "nas": {
                    "id": "nas",
                    "name": "NAS",
                    "ip": "192.168.1.3",
                    "role": "nas",
                    "status": "healthy",
                },
                "client": {
                    "id": "client",
                    "name": "Laptop",
                    "ip": "192.168.1.4",
                    "role": "client",
                    "status": "healthy",
                },
            },
            "connections": [],
            "gateways": [],
        }

        with patch.object(service, "fetch_network_snapshot", AsyncMock(return_value=snapshot)):
            context, summary = await service.build_context_string(wait_for_data=False)

        assert "GATEWAYS & ROUTERS" in context
        assert "FIREWALLS" in context
        assert "NAS DEVICES" in context
        assert "CLIENT DEVICES" in context

    async def test_build_context_with_unknown_role(self):
        """Should handle unknown roles - they go to 'unknown' category"""
        service = MetricsContextService()

        snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_nodes": 1,
            "healthy_nodes": 1,
            "degraded_nodes": 0,
            "unhealthy_nodes": 0,
            "unknown_nodes": 0,
            "nodes": {
                "unknown": {
                    "id": "unknown",
                    "name": "Unknown Device",
                    "ip": "192.168.1.1",
                    "role": "unknown",
                    "status": "healthy",
                },
            },
            "connections": [],
            "gateways": [],
        }

        with patch.object(service, "fetch_network_snapshot", AsyncMock(return_value=snapshot)):
            context, summary = await service.build_context_string(wait_for_data=False)

        # Should categorize properly and include node
        assert "UNKNOWN DEVICES" in context
        assert "Unknown Device" in context

    async def test_format_lan_ports_with_poe(self):
        """Should format LAN ports with PoE"""
        service = MetricsContextService()

        lan_ports = {
            "rows": 2,
            "cols": 4,
            "ports": [
                {
                    "row": 1,
                    "col": 1,
                    "status": "active",
                    "type": "rj45",
                    "poe": "poe+",
                    "connected_device_name": "Camera",
                    "speed": "1G",
                },
            ],
        }

        result = service._format_lan_ports(lan_ports)

        assert "PoE" in result


class TestRouterEdgeCases:
    """Edge case tests for router"""

    def test_chat_error(self):
        """Should handle chat errors"""
        from fastapi.testclient import TestClient

        app = create_test_app_with_auth()
        client = TestClient(app)

        with patch("app.routers.assistant.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.is_available = AsyncMock(return_value=True)
            mock_provider.default_model = "test-model"
            mock_provider.chat = AsyncMock(side_effect=Exception("Chat error"))
            mock_get.return_value = mock_provider

            with patch("app.routers.assistant.metrics_context_service") as mock_service:
                mock_service.build_context_string = AsyncMock(return_value=("Context", {}))

                response = client.post(
                    "/api/assistant/chat", json={"message": "Hello", "provider": "openai"}
                )

        assert response.status_code == 500

    def test_stream_error_handling(self):
        """Should handle stream errors gracefully"""
        from fastapi.testclient import TestClient

        app = create_test_app_with_auth()
        client = TestClient(app)

        with patch("app.routers.assistant.get_provider") as mock_get:

            async def error_stream():
                yield "Hello"
                raise Exception("Stream error")

            mock_provider = MagicMock()
            mock_provider.is_available = AsyncMock(return_value=True)
            mock_provider.default_model = "test-model"
            mock_provider.stream_chat = MagicMock(return_value=error_stream())
            mock_get.return_value = mock_provider

            with patch("app.routers.assistant.metrics_context_service") as mock_service:
                mock_service.build_context_string = AsyncMock(
                    return_value=("Context", {"test": True})
                )

                response = client.post(
                    "/api/assistant/chat/stream", json={"message": "Hello", "provider": "openai"}
                )

        # Should still return 200 with error in stream
        assert response.status_code == 200

    def test_model_cache_double_check(self):
        """Should handle double-check after lock acquisition"""
        import asyncio

        from app.models import ModelProvider
        from app.routers.assistant import ModelCache

        cache = ModelCache(ttl_seconds=300)

        mock_provider = MagicMock()
        mock_provider.list_models = AsyncMock(return_value=["model1"])

        # Simulate cache being populated while waiting for lock
        async def populate_cache():
            # This simulates another coroutine populating the cache
            cache._cache["openai"] = (["cached-model"], datetime.utcnow())

        async def test():
            # Pre-populate cache
            await populate_cache()

            # Now get models - should use cached value
            models = await cache.get_models(ModelProvider.OPENAI, mock_provider)
            return models

        result = asyncio.get_event_loop().run_until_complete(test())
        assert result == ["cached-model"]


class TestMainEdgeCases:
    """Edge case tests for main app"""

    async def test_lifespan_provider_unavailable(self):
        """Should handle unavailable providers during startup"""
        from fastapi import FastAPI

        from app.main import lifespan

        test_app = FastAPI()

        # This tests the actual lifespan with no API keys
        async with lifespan(test_app):
            pass

        # Should complete without errors
        assert True

    async def test_lifespan_provider_exception(self):
        """Should handle provider exception during startup"""
        from fastapi import FastAPI

        from app.main import lifespan

        test_app = FastAPI()

        # Mock provider to raise exception - providers are imported inside lifespan
        with patch("app.providers.OpenAIProvider") as mock_openai:
            mock_provider = MagicMock()
            mock_provider.is_available = AsyncMock(side_effect=Exception("Provider error"))
            mock_openai.return_value = mock_provider

            # Should complete without errors even with exception
            async with lifespan(test_app):
                pass

    def test_healthz_provider_exception(self):
        """Should handle provider exception in healthz"""
        from fastapi.testclient import TestClient

        from app.main import create_app

        with patch("app.main.lifespan"):
            test_app = create_app()
            client = TestClient(test_app)

            # Mock providers - imported inside healthz endpoint
            with patch("app.providers.OpenAIProvider") as mock_openai:
                mock_provider = MagicMock()
                mock_provider.is_available = AsyncMock(side_effect=Exception("Provider error"))
                mock_openai.return_value = mock_provider

                response = client.get("/healthz")

            # Should return degraded status
            assert response.status_code == 200
            data = response.json()
            assert "status" in data

    def test_ready_provider_available(self):
        """Should return ready when provider is available"""
        from fastapi.testclient import TestClient

        from app.main import create_app

        with patch("app.main.lifespan"):
            test_app = create_app()
            client = TestClient(test_app)

            # Mock provider to be available - imported inside ready endpoint
            with patch("app.providers.OpenAIProvider") as mock_openai:
                mock_provider = MagicMock()
                mock_provider.is_available = AsyncMock(return_value=True)
                mock_openai.return_value = mock_provider

                response = client.get("/ready")

            # Should return ready
            assert response.status_code == 200
            data = response.json()
            assert data["ready"] is True

    def test_ready_provider_exception(self):
        """Should handle provider exception in ready endpoint"""
        from fastapi.testclient import TestClient

        from app.main import create_app

        with patch("app.main.lifespan"):
            test_app = create_app()
            client = TestClient(test_app)

            # Mock all providers to raise exception - imported inside ready endpoint
            with (
                patch("app.providers.OpenAIProvider") as mock_openai,
                patch("app.providers.AnthropicProvider") as mock_anthropic,
                patch("app.providers.GeminiProvider") as mock_gemini,
                patch("app.providers.OllamaProvider") as mock_ollama,
            ):

                for mock_cls in [mock_openai, mock_anthropic, mock_gemini, mock_ollama]:
                    mock_provider = MagicMock()
                    mock_provider.is_available = AsyncMock(side_effect=Exception("Provider error"))
                    mock_cls.return_value = mock_provider

                response = client.get("/ready")

            # Should return not ready
            assert response.status_code == 200
            data = response.json()
            assert data["ready"] is False


class TestAdditionalCoverage:
    """Additional tests to boost coverage"""

    async def test_anthropic_chat_extracts_text(self):
        """Should extract text from Anthropic content blocks"""
        from app.providers.anthropic_provider import AnthropicProvider
        from app.providers.base import ChatMessage, ProviderConfig

        config = ProviderConfig(api_key="test-key")
        provider = AnthropicProvider(config)
        messages = [ChatMessage(role="user", content="Hello")]

        # Mock response with multiple content blocks
        mock_block1 = MagicMock()
        mock_block1.text = "Hello "
        mock_block2 = MagicMock()
        mock_block2.text = "World"

        mock_response = MagicMock()
        mock_response.content = [mock_block1, mock_block2]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch.object(provider, "_get_client", return_value=mock_client):
            result = await provider.chat(messages, "System")

        assert result == "Hello World"

    async def test_anthropic_stream_error(self):
        """Should handle stream error in Anthropic"""
        from app.providers.anthropic_provider import AnthropicProvider
        from app.providers.base import ChatMessage, ProviderConfig

        config = ProviderConfig(api_key="test-key")
        provider = AnthropicProvider(config)
        messages = [ChatMessage(role="user", content="Hello")]

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(side_effect=Exception("Stream error"))

        mock_client = AsyncMock()
        mock_client.messages.stream = MagicMock(return_value=mock_stream)

        with patch.object(provider, "_get_client", return_value=mock_client):
            with pytest.raises(Exception):
                async for _ in provider.stream_chat(messages):
                    pass

    async def test_gemini_stream_error(self):
        """Should handle stream error in Gemini"""
        from app.providers.base import ChatMessage, ProviderConfig
        from app.providers.gemini_provider import GeminiProvider

        config = ProviderConfig(api_key="test-key")
        provider = GeminiProvider(config)
        messages = [ChatMessage(role="user", content="Hello")]

        mock_chat = MagicMock()
        mock_chat.send_message_async = AsyncMock(side_effect=Exception("Stream error"))

        mock_model = MagicMock()
        mock_model.start_chat = MagicMock(return_value=mock_chat)

        with patch.object(provider, "_configure_genai") as mock_genai:
            mock_genai.return_value.GenerativeModel = MagicMock(return_value=mock_model)
            mock_genai.return_value.types.GenerationConfig = MagicMock()

            with pytest.raises(Exception):
                async for _ in provider.stream_chat(messages):
                    pass

    async def test_metrics_context_non_200_response(self):
        """Should handle non-200 response from metrics service"""
        service = MetricsContextService()

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await service.fetch_network_summary()

        assert result is None

    def test_model_cache_invalidate_missing_key(self):
        """Should handle invalidating non-existent cache key"""
        from app.models import ModelProvider
        from app.routers.assistant import ModelCache

        cache = ModelCache()

        # Should not raise when invalidating non-existent key
        cache.invalidate(ModelProvider.OPENAI)

        assert "openai" not in cache._cache

    async def test_context_status_not_ready(self):
        """Should return not ready when snapshot not available"""
        from fastapi.testclient import TestClient

        app = create_test_app_with_auth()
        client = TestClient(app)

        with patch("app.routers.assistant.metrics_context_service") as mock_service:
            mock_service.get_status = MagicMock(
                return_value={"snapshot_available": False, "cached": False}
            )

            response = client.get("/api/assistant/context/status")

        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is False
        assert data["loading"] is True

    async def test_fetch_network_summary_non_200(self):
        """Should return None for non-200 summary response"""
        service = MetricsContextService()

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await service.fetch_network_summary()

        assert result is None

    async def test_openai_stream_no_content(self):
        """Should handle chunks with no content"""
        from app.providers.base import ChatMessage, ProviderConfig
        from app.providers.openai_provider import OpenAIProvider

        config = ProviderConfig(api_key="test-key")
        provider = OpenAIProvider(config)
        messages = [ChatMessage(role="user", content="Hello")]

        async def mock_stream():
            # Chunk with no content
            chunk1 = MagicMock()
            chunk1.choices = [MagicMock(delta=MagicMock(content=None))]
            yield chunk1
            # Chunk with empty choices
            chunk2 = MagicMock()
            chunk2.choices = []
            yield chunk2
            # Chunk with content
            chunk3 = MagicMock()
            chunk3.choices = [MagicMock(delta=MagicMock(content="Hello"))]
            yield chunk3

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())

        with patch.object(provider, "_get_client", return_value=mock_client):
            chunks = []
            async for chunk in provider.stream_chat(messages):
                chunks.append(chunk)

        assert "Hello" in chunks

    async def test_anthropic_sync_client_with_base_url(self):
        """Should create sync client with base URL"""
        from app.providers.anthropic_provider import AnthropicProvider
        from app.providers.base import ProviderConfig

        config = ProviderConfig(api_key="test-key", base_url="https://custom.anthropic.com")
        provider = AnthropicProvider(config)

        with patch("app.providers.anthropic_provider.Anthropic") as mock_class:
            provider._get_sync_client()
            mock_class.assert_called_once()

    async def test_gemini_using_env_key(self):
        """Should use GEMINI_API_KEY from settings"""
        from app.config import settings
        from app.providers.base import ProviderConfig
        from app.providers.gemini_provider import GeminiProvider

        config = ProviderConfig()

        with patch.object(
            type(settings), "effective_google_api_key", property(lambda self: "test-gemini-key")
        ):
            provider = GeminiProvider(config)
            assert await provider.is_available() is True

    async def test_ollama_stream_empty_content(self):
        """Should handle empty content in Ollama stream"""
        from app.providers.base import ChatMessage, ProviderConfig
        from app.providers.ollama_provider import OllamaProvider

        config = ProviderConfig()
        provider = OllamaProvider(config)
        messages = [ChatMessage(role="user", content="Hello")]

        async def mock_stream():
            yield {"message": {}}  # No content
            yield {"message": {"content": "Hello"}}

        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=mock_stream())

        with patch.object(provider, "_get_client", return_value=mock_client):
            chunks = []
            async for chunk in provider.stream_chat(messages):
                chunks.append(chunk)

        assert "Hello" in chunks

    async def test_metrics_context_timestamp_handling(self):
        """Should handle different timestamp formats in gateway"""
        service = MetricsContextService()

        gateway = {
            "gateway_ip": "192.168.1.1",
            "test_ips": [],
            "last_speed_test": {
                "success": True,
                "download_mbps": 100.0,
                "upload_mbps": 50.0,
                "timestamp": "2024-01-01T00:00:00Z",
            },
        }

        result = service._format_gateway_info(gateway, {})

        assert "2024-01-01" in result

    async def test_metrics_context_timestamp_datetime(self):
        """Should handle datetime timestamp in gateway"""
        service = MetricsContextService()

        gateway = {
            "gateway_ip": "192.168.1.1",
            "test_ips": [],
            "last_speed_test": {
                "success": True,
                "download_mbps": 100.0,
                "upload_mbps": 50.0,
                "timestamp": datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            },
        }

        result = service._format_gateway_info(gateway, {})

        assert "192.168.1.1" in result

    def test_config_list_models_error(self):
        """Should handle model list error gracefully"""
        from fastapi.testclient import TestClient

        app = create_test_app_with_auth()
        client = TestClient(app)

        with patch("app.routers.assistant.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.is_available = AsyncMock(return_value=True)
            mock_provider.default_model = "test-model"
            mock_get.return_value = mock_provider

            with patch("app.routers.assistant.model_cache") as mock_cache:
                mock_cache.get_models = AsyncMock(side_effect=Exception("API Error"))

                response = client.get("/api/assistant/config")

        assert response.status_code == 200
        data = response.json()
        # Should still return config, with error in provider
        assert "providers" in data
