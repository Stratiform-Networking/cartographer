"""
Unit tests for assistant router endpoints.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.dependencies.auth import (
    AuthenticatedUser,
    UserRole,
    require_auth,
    require_auth_with_rate_limit,
)
from app.models import ChatMessage, ChatRole, ModelProvider
from app.routers.assistant import ModelCache, get_provider, model_cache, router

# Mock user for auth
_mock_user = AuthenticatedUser(user_id="test-user-123", username="testuser", role=UserRole.MEMBER)


async def mock_require_auth():
    """Mock auth dependency"""
    return _mock_user


@pytest.fixture
def app():
    """Create test app with assistant router and mocked auth"""
    from app.routers.assistant import require_chat_auth

    test_app = FastAPI()
    test_app.include_router(router, prefix="/api")

    # Override auth dependencies
    test_app.dependency_overrides[require_auth] = mock_require_auth
    test_app.dependency_overrides[require_chat_auth] = mock_require_auth

    return test_app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


class TestModelCache:
    """Tests for ModelCache"""

    async def test_get_models_fresh(self):
        """Should fetch models when not cached"""
        cache = ModelCache(ttl_seconds=300)

        mock_provider = MagicMock()
        mock_provider.list_models = AsyncMock(return_value=["model1", "model2"])

        models = await cache.get_models(ModelProvider.OPENAI, mock_provider)

        assert models == ["model1", "model2"]
        mock_provider.list_models.assert_called_once()

    async def test_get_models_cached(self):
        """Should use cached models"""
        cache = ModelCache(ttl_seconds=300)
        cache._cache["openai:default"] = (["cached-model"], datetime.utcnow())

        mock_provider = MagicMock()
        mock_provider.list_models = AsyncMock(return_value=["new-model"])

        models = await cache.get_models(ModelProvider.OPENAI, mock_provider)

        assert models == ["cached-model"]
        mock_provider.list_models.assert_not_called()

    async def test_get_models_expired(self):
        """Should refresh expired cache"""
        cache = ModelCache(ttl_seconds=1)
        cache._cache["openai"] = (["old-model"], datetime.utcnow() - timedelta(seconds=5))

        mock_provider = MagicMock()
        mock_provider.list_models = AsyncMock(return_value=["new-model"])

        models = await cache.get_models(ModelProvider.OPENAI, mock_provider)

        assert models == ["new-model"]

    def test_invalidate_specific(self):
        """Should invalidate specific provider"""
        cache = ModelCache()
        cache._cache["openai:default"] = (["model"], datetime.utcnow())
        cache._cache["anthropic:default"] = (["model"], datetime.utcnow())

        cache.invalidate(ModelProvider.OPENAI)

        assert "openai:default" not in cache._cache
        assert "anthropic:default" in cache._cache

    def test_invalidate_all(self):
        """Should invalidate all providers"""
        cache = ModelCache()
        cache._cache["openai"] = (["model"], datetime.utcnow())
        cache._cache["anthropic"] = (["model"], datetime.utcnow())

        cache.invalidate()

        assert cache._cache == {}


class TestGetProvider:
    """Tests for get_provider function"""

    def test_get_openai_provider(self):
        """Should return OpenAI provider"""
        provider = get_provider(ModelProvider.OPENAI)
        assert provider.name == "openai"

    def test_get_anthropic_provider(self):
        """Should return Anthropic provider"""
        provider = get_provider(ModelProvider.ANTHROPIC)
        assert provider.name == "anthropic"

    def test_get_gemini_provider(self):
        """Should return Gemini provider"""
        provider = get_provider(ModelProvider.GEMINI)
        assert provider.name == "gemini"

    def test_get_ollama_provider(self):
        """Should return Ollama provider"""
        provider = get_provider(ModelProvider.OLLAMA)
        assert provider.name == "ollama"


class TestConfigEndpoint:
    """Tests for /config endpoint"""

    def test_get_config(self, client):
        """Should return assistant config"""
        with patch("app.routers.assistant.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.is_available = AsyncMock(return_value=True)
            mock_provider.default_model = "test-model"
            mock_get.return_value = mock_provider

            with patch("app.routers.assistant.model_cache") as mock_cache:
                mock_cache.get_models = AsyncMock(return_value=["model1"])

                response = client.get("/api/assistant/config")

        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert "default_provider" in data

    def test_get_config_provider_error(self, client):
        """Should handle provider error"""
        with patch("app.routers.assistant.get_provider") as mock_get:
            mock_get.side_effect = Exception("Error")

            response = client.get("/api/assistant/config")

        assert response.status_code == 200


class TestProvidersEndpoint:
    """Tests for /providers endpoint"""

    def test_list_providers(self, client):
        """Should list all providers"""
        with patch("app.routers.assistant.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.is_available = AsyncMock(return_value=True)
            mock_provider.default_model = "test-model"
            mock_get.return_value = mock_provider

            response = client.get("/api/assistant/providers")

        assert response.status_code == 200
        data = response.json()
        assert "providers" in data

    def test_list_providers_with_error(self, client):
        """Should handle provider error"""
        with patch("app.routers.assistant.get_provider") as mock_get:
            mock_get.side_effect = Exception("Error")

            response = client.get("/api/assistant/providers")

        assert response.status_code == 200


class TestModelsEndpoint:
    """Tests for /models/{provider} endpoint"""

    def test_list_models(self, client):
        """Should list models for provider"""
        with patch("app.routers.assistant.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.is_available = AsyncMock(return_value=True)
            mock_provider.default_model = "test-model"
            mock_get.return_value = mock_provider

            with patch("app.routers.assistant.model_cache") as mock_cache:
                mock_cache.get_models = AsyncMock(return_value=["model1", "model2"])

                response = client.get("/api/assistant/models/openai")

        assert response.status_code == 200
        data = response.json()
        assert data["models"] == ["model1", "model2"]

    def test_list_models_provider_unavailable(self, client):
        """Should return 503 when provider unavailable"""
        with patch("app.routers.assistant.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.is_available = AsyncMock(return_value=False)
            mock_get.return_value = mock_provider

            response = client.get("/api/assistant/models/openai")

        assert response.status_code == 503

    def test_list_models_refresh(self, client):
        """Should refresh cache when requested"""
        with patch("app.routers.assistant.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.is_available = AsyncMock(return_value=True)
            mock_provider.default_model = "test-model"
            mock_get.return_value = mock_provider

            with patch("app.routers.assistant.model_cache") as mock_cache:
                mock_cache.get_models = AsyncMock(return_value=["model1"])
                mock_cache.invalidate = MagicMock()

                response = client.get("/api/assistant/models/openai?refresh=true")

        assert response.status_code == 200
        mock_cache.invalidate.assert_called_once()


class TestRefreshModelsEndpoint:
    """Tests for /models/refresh endpoint"""

    def test_refresh_all_models(self, client):
        """Should refresh all models"""
        with patch("app.routers.assistant.model_cache") as mock_cache:
            mock_cache.invalidate = MagicMock()
            mock_cache.get_models = AsyncMock(return_value=["model1"])

            with patch("app.routers.assistant.get_provider") as mock_get:
                mock_provider = MagicMock()
                mock_provider.is_available = AsyncMock(return_value=True)
                mock_get.return_value = mock_provider

                response = client.post("/api/assistant/models/refresh")

        assert response.status_code == 200
        data = response.json()
        assert data["refreshed"] is True


class TestContextEndpoints:
    """Tests for context endpoints"""

    def test_get_context(self, client):
        """Should return network context"""
        with patch("app.routers.assistant.metrics_context_service") as mock_service:
            mock_service.build_context_string = AsyncMock(
                return_value=(
                    "Context",
                    {
                        "total_nodes": 5,
                        "healthy_nodes": 4,
                        "unhealthy_nodes": 1,
                        "gateway_count": 1,
                        "context_tokens_estimate": 100,
                    },
                )
            )

            response = client.get("/api/assistant/context")

        assert response.status_code == 200
        data = response.json()
        assert data["total_nodes"] == 5

    def test_refresh_context(self, client):
        """Should refresh context"""
        with patch("app.routers.assistant.metrics_context_service") as mock_service:
            mock_service.clear_cache = MagicMock()
            mock_service.build_context_string = AsyncMock(
                return_value=("Context", {"total_nodes": 5})
            )

            response = client.post("/api/assistant/context/refresh")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_context_status(self, client):
        """Should return context status"""
        with patch("app.routers.assistant.metrics_context_service") as mock_service:
            mock_service.get_status = MagicMock(
                return_value={"snapshot_available": True, "cached": True}
            )

            response = client.get("/api/assistant/context/status")

        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True

    def test_get_context_debug(self, client):
        """Should return debug context"""
        with patch("app.routers.assistant.metrics_context_service") as mock_service:
            mock_service.clear_cache = MagicMock()
            mock_service.build_context_string = AsyncMock(
                return_value=("Test context string", {"total_nodes": 5})
            )

            response = client.get("/api/assistant/context/debug")

        assert response.status_code == 200
        data = response.json()
        assert "context_string" in data


class TestChatEndpoint:
    """Tests for /chat endpoint"""

    def test_chat_success(self, client):
        """Should process chat request"""
        with patch("app.routers.assistant.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.is_available = AsyncMock(return_value=True)
            mock_provider.default_model = "test-model"
            mock_provider.chat = AsyncMock(return_value="Test response")
            mock_get.return_value = mock_provider

            with patch("app.routers.assistant.metrics_context_service") as mock_service:
                mock_service.build_context_string = AsyncMock(return_value=("Context", {}))

                response = client.post(
                    "/api/assistant/chat", json={"message": "Hello", "provider": "openai"}
                )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Test response"

    def test_chat_without_context(self, client):
        """Should chat without network context"""
        with patch("app.routers.assistant.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.is_available = AsyncMock(return_value=True)
            mock_provider.default_model = "test-model"
            mock_provider.chat = AsyncMock(return_value="Test response")
            mock_get.return_value = mock_provider

            response = client.post(
                "/api/assistant/chat",
                json={"message": "Hello", "provider": "openai", "include_network_context": False},
            )

        assert response.status_code == 200

    def test_chat_provider_unavailable(self, client):
        """Should return 503 when provider unavailable"""
        with patch("app.routers.assistant.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.is_available = AsyncMock(return_value=False)
            mock_get.return_value = mock_provider

            response = client.post(
                "/api/assistant/chat", json={"message": "Hello", "provider": "openai"}
            )

        assert response.status_code == 503

    def test_chat_with_history(self, client):
        """Should include conversation history"""
        with patch("app.routers.assistant.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.is_available = AsyncMock(return_value=True)
            mock_provider.default_model = "test-model"
            mock_provider.chat = AsyncMock(return_value="Test response")
            mock_get.return_value = mock_provider

            with patch("app.routers.assistant.metrics_context_service") as mock_service:
                mock_service.build_context_string = AsyncMock(return_value=("Context", {}))

                response = client.post(
                    "/api/assistant/chat",
                    json={
                        "message": "How are you?",
                        "provider": "openai",
                        "conversation_history": [{"role": "user", "content": "Hello"}],
                    },
                )

        assert response.status_code == 200


class TestChatStreamEndpoint:
    """Tests for /chat/stream endpoint"""

    def test_chat_stream_success(self, client):
        """Should stream chat response"""
        with patch("app.routers.assistant.get_provider") as mock_get:

            async def mock_stream():
                yield "Hello"
                yield " World"

            mock_provider = MagicMock()
            mock_provider.is_available = AsyncMock(return_value=True)
            mock_provider.default_model = "test-model"
            mock_provider.stream_chat = MagicMock(return_value=mock_stream())
            mock_get.return_value = mock_provider

            with patch("app.routers.assistant.metrics_context_service") as mock_service:
                mock_service.build_context_string = AsyncMock(
                    return_value=("Context", {"test": True})
                )

                response = client.post(
                    "/api/assistant/chat/stream", json={"message": "Hello", "provider": "openai"}
                )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    def test_chat_stream_provider_unavailable(self, client):
        """Should return 503 when provider unavailable"""
        with patch("app.routers.assistant.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.is_available = AsyncMock(return_value=False)
            mock_get.return_value = mock_provider

            response = client.post(
                "/api/assistant/chat/stream", json={"message": "Hello", "provider": "openai"}
            )

        assert response.status_code == 503


class TestContextRawEndpoint:
    """Tests for /context/raw endpoint"""

    def test_get_context_raw_success(self, client):
        """Should return raw context data"""
        with patch("app.routers.assistant.metrics_context_service") as mock_service:
            mock_service.fetch_network_snapshot = AsyncMock(
                return_value={
                    "nodes": {
                        "node-1": {
                            "name": "Test",
                            "ip": "192.168.1.1",
                            "role": "server",
                            "notes": None,
                            "isp_info": None,
                        }
                    },
                    "gateways": [
                        {"gateway_ip": "192.168.1.1", "test_ips": [], "last_speed_test": None}
                    ],
                }
            )

            with patch("httpx.AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"layout_exists": True}
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    return_value=mock_response
                )

                response = client.get("/api/assistant/context/raw")

        assert response.status_code == 200
        data = response.json()
        assert data["snapshot_available"] is True

    def test_get_context_raw_no_snapshot(self, client):
        """Should handle no snapshot"""
        with patch("app.routers.assistant.metrics_context_service") as mock_service:
            mock_service.fetch_network_snapshot = AsyncMock(return_value=None)

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    side_effect=Exception("Error")
                )

                response = client.get("/api/assistant/context/raw")

        assert response.status_code == 200
        data = response.json()
        assert "error" in data


class TestChatLimitEndpoint:
    """Tests for /chat/limit endpoint."""

    def test_get_chat_limit_with_provider_byok_exempt(self, client):
        """Should return unlimited when provider has user BYOK key."""
        with (
            patch("app.routers.assistant.get_user_assistant_settings") as mock_settings,
            patch("app.routers.assistant.get_rate_limit_status") as mock_rate_status,
        ):
            mock_settings.return_value = {
                "openai": {"api_key": "sk-openai", "model": "gpt-4o-mini"},
                "anthropic": {"api_key": None, "model": None},
                "gemini": {"api_key": None, "model": None},
            }

            response = client.get("/api/assistant/chat/limit?provider=openai")

        assert response.status_code == 200
        data = response.json()
        assert data["is_exempt"] is True
        assert data["limit"] == -1
        mock_rate_status.assert_not_called()

    def test_get_chat_limit_without_provider_uses_rate_limit_status(self, client):
        """Should use rate-limit service when no provider is specified."""
        with patch("app.routers.assistant.get_rate_limit_status") as mock_rate_status:
            mock_rate_status.return_value = {
                "used": 2,
                "limit": 5,
                "remaining": 3,
                "resets_in_seconds": 100,
                "is_exempt": False,
            }

            response = client.get("/api/assistant/chat/limit")

        assert response.status_code == 200
        data = response.json()
        assert data["is_exempt"] is False
        assert data["remaining"] == 3
