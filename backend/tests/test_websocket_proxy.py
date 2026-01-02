"""
Tests for WebSocket proxy functionality in metrics_proxy.py
and streaming proxy in assistant_proxy.py
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.testclient import TestClient

from app.dependencies.auth import AuthenticatedUser, UserRole


class TestAssistantStreamProxy:
    """Tests for the streaming proxy in assistant router"""

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

    async def test_stream_proxy_connect_error(self, owner_user, mock_request):
        """Stream proxy should handle connection errors"""
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

    async def test_stream_proxy_returns_correct_headers(self, owner_user, mock_request):
        """Stream proxy should set correct headers"""
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

            assert response.media_type == "text/event-stream"
            assert "no-cache" in response.headers.get("Cache-Control", "")
            assert response.headers.get("X-Accel-Buffering") == "no"


class TestNotificationServiceStatus:
    """Tests for notification service status endpoints with optional body"""

    @pytest.fixture
    def owner_user(self):
        return AuthenticatedUser(user_id="owner-1", username="owner", role=UserRole.OWNER)

    @pytest.fixture(autouse=True)
    def mock_http_pool(self):
        """Mock http_pool for notification proxy tests"""
        from fastapi.responses import JSONResponse

        with patch("app.services.proxy_service.http_pool") as mock:
            mock.request = AsyncMock(return_value=JSONResponse(content={"ok": True}))
            yield mock

    async def test_notify_service_up_without_body(self, mock_http_pool, owner_user):
        """notify_service_up should work without JSON body"""
        from app.routers.notification_proxy import notify_service_up

        mock_request = MagicMock()
        mock_request.headers = MagicMock()
        mock_request.headers.get = MagicMock(return_value=None)  # No content-type

        response = await notify_service_up(request=mock_request, user=owner_user)

        # Should work even without body
        mock_http_pool.request.assert_called_once()

    async def test_notify_service_down_without_body(self, mock_http_pool, owner_user):
        """notify_service_down should work without JSON body"""
        from app.routers.notification_proxy import notify_service_down

        mock_request = MagicMock()
        mock_request.headers = MagicMock()
        mock_request.headers.get = MagicMock(return_value=None)  # No content-type

        response = await notify_service_down(request=mock_request, user=owner_user)

        mock_http_pool.request.assert_called_once()

    async def test_notify_service_up_with_body(self, mock_http_pool, owner_user):
        """notify_service_up should forward body when present"""
        from app.routers.notification_proxy import notify_service_up

        mock_request = MagicMock()
        mock_request.headers = MagicMock()
        mock_request.headers.get = MagicMock(return_value="application/json")
        mock_request.json = AsyncMock(return_value={"message": "Online", "downtime_minutes": 5})

        response = await notify_service_up(request=mock_request, user=owner_user)

        mock_http_pool.request.assert_called_once()
        call_kwargs = mock_http_pool.request.call_args[1]
        assert call_kwargs["params"]["message"] == "Online"
        assert call_kwargs["params"]["downtime_minutes"] == 5

    async def test_notify_service_down_with_body(self, mock_http_pool, owner_user):
        """notify_service_down should forward body when present"""
        from app.routers.notification_proxy import notify_service_down

        mock_request = MagicMock()
        mock_request.headers = MagicMock()
        mock_request.headers.get = MagicMock(return_value="application/json")
        mock_request.json = AsyncMock(
            return_value={"message": "Maintenance", "affected_services": ["api", "web"]}
        )

        response = await notify_service_down(request=mock_request, user=owner_user)

        mock_http_pool.request.assert_called_once()
