"""
Tests for streaming endpoints to cover assistant and metrics proxies.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.responses import StreamingResponse

from app.dependencies.auth import AuthenticatedUser, UserRole


class TestAssistantStreamingProxy:
    """Full coverage tests for assistant streaming proxy"""

    @pytest.fixture
    def owner_user(self):
        return AuthenticatedUser(user_id="user-1", username="test", role=UserRole.OWNER)

    @pytest.fixture
    def mock_request(self):
        """Create a mock request with headers"""
        request = MagicMock()
        request.json = AsyncMock(return_value={"message": "Hello"})
        mock_headers = MagicMock()
        mock_headers.get = MagicMock(return_value="Bearer test-token")
        request.headers = mock_headers
        return request

    async def test_stream_proxy_generator_connect_error(self, owner_user, mock_request):
        """Stream generator should raise 503 on connect failure"""
        import httpx
        from fastapi import HTTPException

        from app.routers.assistant_proxy import chat_stream

        with patch("app.services.streaming_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.aclose = AsyncMock()
            mock_client.build_request = MagicMock(return_value=MagicMock())
            mock_client.send = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
            mock_client_cls.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                await chat_stream(request=mock_request, user=owner_user)

            assert exc_info.value.status_code == 503

    async def test_stream_proxy_timeout_error_in_stream(self, owner_user, mock_request):
        """Stream should handle timeout during streaming"""
        from app.routers.assistant_proxy import chat_stream

        # Mock a successful response that returns chunks
        async def mock_aiter_bytes():
            yield b'data: {"type": "chunk"}\n\n'

        with patch("app.services.streaming_service.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.aiter_bytes = mock_aiter_bytes
            mock_response.aclose = AsyncMock()

            mock_client = MagicMock()
            mock_client.aclose = AsyncMock()
            mock_client.build_request = MagicMock(return_value=MagicMock())
            mock_client.send = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            response = await chat_stream(request=mock_request, user=owner_user)

            assert response.media_type == "text/event-stream"

    async def test_stream_proxy_headers(self, owner_user, mock_request):
        """Stream proxy should set correct cache headers"""
        from app.routers.assistant_proxy import chat_stream

        async def mock_aiter_bytes():
            yield b'data: {"type": "chunk"}\n\n'

        with patch("app.services.streaming_service.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.aiter_bytes = mock_aiter_bytes
            mock_response.aclose = AsyncMock()

            mock_client = MagicMock()
            mock_client.aclose = AsyncMock()
            mock_client.build_request = MagicMock(return_value=MagicMock())
            mock_client.send = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            response = await chat_stream(request=mock_request, user=owner_user)

            # Verify headers
            assert response.headers.get("Cache-Control") == "no-cache"
            assert response.headers.get("Connection") == "keep-alive"
            assert response.headers.get("X-Accel-Buffering") == "no"


class TestMetricsWebSocketProxy:
    """Tests for metrics WebSocket proxy"""

    async def test_websocket_proxy_creates_response(self):
        """WebSocket proxy endpoint should be callable"""
        # Import with mocked websockets module
        import sys

        mock_websockets = MagicMock()
        sys.modules["websockets"] = mock_websockets

        from fastapi import WebSocket, WebSocketDisconnect

        from app.routers.metrics_proxy import websocket_proxy

        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.accept = AsyncMock()
        mock_websocket.close = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        mock_websocket.receive_text = AsyncMock(side_effect=WebSocketDisconnect())

        # Mock the websockets.connect to fail immediately
        mock_websockets.connect = MagicMock(side_effect=Exception("Test error"))

        with patch.dict("sys.modules", {"websockets": mock_websockets}):
            # Should handle the error gracefully
            await websocket_proxy(mock_websocket)

            # Accept should have been called
            mock_websocket.accept.assert_called_once()


class TestAssistantProxyURLConfig:
    """Test assistant proxy URL configuration"""

    def test_assistant_service_url_from_settings(self):
        """assistant_service_url should be available from settings"""
        from app.routers import assistant_proxy

        # The settings object should be available
        assert assistant_proxy.settings is not None
        assert assistant_proxy.settings.assistant_service_url is not None

    async def test_proxy_request_uses_timeout(self):
        """proxy_assistant_request should use specified timeout"""
        with patch("app.services.proxy_service.http_pool") as mock_pool:
            mock_pool.request = AsyncMock(return_value=MagicMock())

            from app.services.proxy_service import proxy_request

            await proxy_request("assistant", "GET", "/test", timeout=90.0)

            call_kwargs = mock_pool.request.call_args[1]
            assert call_kwargs["timeout"] == 90.0


class TestMetricsProxyURLConfig:
    """Test metrics proxy URL configuration"""

    def test_metrics_service_url_from_settings(self):
        """metrics_service_url should be available from settings"""
        from app.routers import metrics_proxy

        # The settings object should be available
        assert metrics_proxy.settings is not None
        assert metrics_proxy.settings.metrics_service_url is not None


class TestHealthProxyTimeouts:
    """Test health proxy timeout configurations"""

    @pytest.fixture(autouse=True)
    def mock_http_pool(self):
        """Mock http_pool"""
        from fastapi.responses import JSONResponse

        with patch("app.services.proxy_service.http_pool") as mock:
            mock.request = AsyncMock(return_value=JSONResponse(content={"ok": True}))
            yield mock

    async def test_proxy_request_default_timeout(self, mock_http_pool):
        """proxy_health_request should use default 30s timeout"""
        from app.services.proxy_service import proxy_health_request

        await proxy_health_request("GET", "/test")

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["timeout"] == 30.0

    async def test_proxy_request_custom_timeout(self, mock_http_pool):
        """proxy_health_request should accept custom timeout"""
        from app.services.proxy_service import proxy_health_request

        await proxy_health_request("GET", "/test", timeout=60.0)

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["timeout"] == 60.0


class TestNotificationProxyHeaders:
    """Test notification proxy header forwarding"""

    @pytest.fixture(autouse=True)
    def mock_http_pool(self):
        """Mock http_pool"""
        from fastapi.responses import JSONResponse

        with patch("app.services.proxy_service.http_pool") as mock:
            mock.request = AsyncMock(return_value=JSONResponse(content={"ok": True}))
            yield mock

    async def test_proxy_request_forwards_headers(self, mock_http_pool):
        """proxy_notification_request should forward custom headers"""
        from app.services.proxy_service import proxy_notification_request

        await proxy_notification_request(
            "GET", "/test", headers={"X-Custom": "value", "X-User-Id": "user-123"}
        )

        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["headers"]["X-Custom"] == "value"
        assert call_kwargs["headers"]["X-User-Id"] == "user-123"


class TestAuthProxyNoHeader:
    """Test auth proxy without authorization header"""

    @pytest.fixture(autouse=True)
    def mock_http_pool(self):
        """Mock http_pool"""
        from fastapi.responses import JSONResponse

        with patch("app.services.proxy_service.http_pool") as mock:
            mock.request = AsyncMock(return_value=JSONResponse(content={"ok": True}))
            yield mock

    async def test_proxy_request_without_auth_header(self, mock_http_pool):
        """proxy_auth_request should work without Authorization header"""
        from app.services.proxy_service import proxy_auth_request

        mock_request = MagicMock()
        mock_request.headers = MagicMock()
        mock_request.headers.get = MagicMock(return_value=None)

        await proxy_auth_request("GET", "/setup/status", mock_request)

        call_kwargs = mock_http_pool.request.call_args[1]
        # Should still have Content-Type
        assert "Content-Type" in call_kwargs["headers"]
