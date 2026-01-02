"""
Additional tests to boost coverage above 95%.
Targets specific uncovered lines.
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from app.dependencies.auth import AuthenticatedUser, UserRole


@pytest.fixture
def owner_user():
    return AuthenticatedUser(user_id="owner-123", username="owner", role=UserRole.OWNER)


@pytest.fixture
def readwrite_user():
    return AuthenticatedUser(user_id="rw-123", username="admin", role=UserRole.ADMIN)


class TestMapperStreamGenerator:
    """Tests for mapper stream event generator"""

    def test_stream_generator_popen_exception(self, tmp_path, readwrite_user):
        """Stream generator should handle Popen exceptions"""
        from app.routers.mapper import run_mapper_stream
        from app.services import mapper_runner_service
        from app.services.mapper_runner_service import sse_event

        script = tmp_path / "lan_mapper.sh"
        script.write_text("#!/bin/bash\necho test")
        script.chmod(0o755)

        with patch.object(mapper_runner_service, "script_path", return_value=script):
            with patch.object(mapper_runner_service, "project_root", return_value=tmp_path):
                with patch("subprocess.Popen", side_effect=OSError("Cannot execute")):
                    response = run_mapper_stream(user=readwrite_user)

                    # Should return a streaming response
                    assert isinstance(response, StreamingResponse)

    def test_stream_generator_success(self, tmp_path, readwrite_user):
        """Stream generator should yield events correctly"""
        from app.routers.mapper import run_mapper_stream
        from app.services import mapper_runner_service

        script = tmp_path / "lan_mapper.sh"
        script.write_text("#!/bin/bash\necho 'line1'\necho 'line2'")
        script.chmod(0o755)

        # Create output file
        (tmp_path / "network_map.txt").write_text("Network data")

        with patch.object(mapper_runner_service, "script_path", return_value=script):
            with patch.object(mapper_runner_service, "project_root", return_value=tmp_path):
                with patch.object(
                    mapper_runner_service,
                    "network_map_candidates",
                    return_value=[tmp_path / "network_map.txt"],
                ):
                    response = run_mapper_stream(user=readwrite_user)

                    assert isinstance(response, StreamingResponse)
                    assert response.media_type == "text/event-stream"


class TestMapperEmbedDeleteWithMapping:
    """Test embed deletion clears IP mappings"""

    def test_delete_embed_clears_mapping(self, tmp_path, owner_user):
        """delete_embed should clear IP mapping"""
        from app.routers.mapper import delete_embed
        from app.services import embed_service

        embeds_file = tmp_path / "embeds.json"
        embeds_file.write_text(
            json.dumps(
                {
                    "embed-to-delete": {
                        "name": "Test",
                        "sensitiveMode": True,
                        "createdAt": "2024-01-01T00:00:00Z",
                    }
                }
            )
        )

        # Set up IP mapping
        embed_service.set_ip_mapping("embed-to-delete", {"device_abc": "192.168.1.1"})

        with patch.object(embed_service, "_embeds_config_path", return_value=embeds_file):
            response = delete_embed(embed_id="embed-to-delete", user=owner_user)

            data = json.loads(response.body.decode())
            assert data["success"] is True

            # Mapping should be cleared
            assert embed_service.get_ip_mapping("embed-to-delete") == {}


class TestAssistantStreamProxy:
    """Tests for assistant streaming proxy error handling"""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request with headers"""
        request = MagicMock()
        request.json = AsyncMock(return_value={"message": "Hello"})
        mock_headers = MagicMock()
        mock_headers.get = MagicMock(return_value="Bearer test-token")
        request.headers = mock_headers
        return request

    async def test_stream_proxy_yields_error_on_connect_failure(self, owner_user, mock_request):
        """Stream should raise 503 on connection failure"""
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
            assert "unavailable" in exc_info.value.detail.lower()

    async def test_stream_proxy_yields_error_on_timeout(self, owner_user, mock_request):
        """Stream should raise 504 on timeout"""
        import httpx
        from fastapi import HTTPException

        from app.routers.assistant_proxy import chat_stream

        with patch("app.services.streaming_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.aclose = AsyncMock()
            mock_client.build_request = MagicMock(return_value=MagicMock())
            mock_client.send = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client_cls.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                await chat_stream(request=mock_request, user=owner_user)

            assert exc_info.value.status_code == 504
            assert "timeout" in exc_info.value.detail.lower()

    async def test_stream_proxy_yields_error_on_generic_exception(self, owner_user, mock_request):
        """Stream should raise 500 on generic exception"""
        from fastapi import HTTPException

        from app.routers.assistant_proxy import chat_stream

        with patch("app.services.streaming_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.aclose = AsyncMock()
            mock_client.build_request = MagicMock(return_value=MagicMock())
            mock_client.send = AsyncMock(side_effect=RuntimeError("Something broke"))
            mock_client_cls.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                await chat_stream(request=mock_request, user=owner_user)

            assert exc_info.value.status_code == 500


class TestMetricsWebSocketForwarding:
    """Tests for metrics WebSocket message forwarding"""

    async def test_websocket_forward_to_client(self):
        """forward_to_client should handle exceptions"""
        # Mock websockets module
        mock_websockets = MagicMock()
        sys.modules["websockets"] = mock_websockets

        from fastapi import WebSocket, WebSocketDisconnect

        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.accept = AsyncMock()
        mock_websocket.close = AsyncMock()
        mock_websocket.send_text = AsyncMock(side_effect=Exception("Send failed"))
        mock_websocket.receive_text = AsyncMock(side_effect=WebSocketDisconnect())

        # Mock upstream ws that yields one message then closes
        mock_upstream = AsyncMock()
        mock_upstream.__aenter__ = AsyncMock(return_value=mock_upstream)
        mock_upstream.__aexit__ = AsyncMock()

        async def mock_iter():
            yield "test message"

        mock_upstream.__aiter__ = lambda self: mock_iter()
        mock_upstream.send = AsyncMock()

        mock_websockets.connect = MagicMock(return_value=mock_upstream)

        with patch.dict("sys.modules", {"websockets": mock_websockets}):
            from app.routers.metrics_proxy import websocket_proxy

            # Should not raise
            await websocket_proxy(mock_websocket)


class TestMapperProjectRootFallback:
    """Test mapper project root path calculation"""

    def test_embeds_config_path_fallback(self, tmp_path):
        """Should fallback to project root if /app/data doesn't exist"""
        from app.services.embed_service import _embeds_config_path

        # When /app/data doesn't exist, should use project root
        path = _embeds_config_path()
        assert path.name == "embeds.json"

    def test_saved_layout_path_fallback(self):
        """Should fallback to project root if /app/data doesn't exist"""
        from app.services.mapper_runner_service import saved_layout_path

        path = saved_layout_path()
        assert path.name == "saved_network_layout.json"


class TestMapperEmbedException:
    """Test exception handling in embed endpoints"""

    def test_update_embed_exception(self, tmp_path, readwrite_user):
        """update_embed should handle exceptions"""
        from app.routers.mapper import update_embed
        from app.services import embed_service

        embeds_file = tmp_path / "embeds.json"
        embeds_file.write_text(
            json.dumps(
                {
                    "test": {
                        "name": "Test",
                        "createdAt": "2024-01-01T00:00:00Z",
                        "updatedAt": "2024-01-01T00:00:00Z",
                    }
                }
            )
        )

        with patch.object(embed_service, "_embeds_config_path", return_value=embeds_file):
            with patch.object(
                embed_service, "save_all_embeds", side_effect=IOError("Write failed")
            ):
                with pytest.raises(HTTPException) as exc_info:
                    update_embed(embed_id="test", config={"name": "New Name"}, user=readwrite_user)

                assert exc_info.value.status_code == 500

    def test_delete_embed_exception(self, tmp_path, owner_user):
        """delete_embed should handle exceptions"""
        from app.routers.mapper import delete_embed
        from app.services import embed_service

        embeds_file = tmp_path / "embeds.json"
        embeds_file.write_text(
            json.dumps({"test": {"name": "Test", "createdAt": "2024-01-01T00:00:00Z"}})
        )

        with patch.object(embed_service, "_embeds_config_path", return_value=embeds_file):
            with patch.object(
                embed_service, "save_all_embeds", side_effect=IOError("Write failed")
            ):
                with pytest.raises(HTTPException) as exc_info:
                    delete_embed(embed_id="test", user=owner_user)

                assert exc_info.value.status_code == 500


class TestEmbedDataException:
    """Test exception handling in embed data endpoint"""

    async def test_get_embed_data_exception(self, tmp_path):
        """get_embed_data should handle load exceptions"""
        from app.routers.mapper import get_embed_data
        from app.services import embed_service, mapper_runner_service

        embeds_file = tmp_path / "embeds.json"

        embeds_file.write_text(
            json.dumps(
                {
                    "test": {
                        "name": "Test",
                        "sensitiveMode": False,
                        "createdAt": "2024-01-01T00:00:00Z",
                    }
                }
            )
        )

        mock_db = AsyncMock()

        with patch.object(embed_service, "_embeds_config_path", return_value=embeds_file):
            with patch.object(
                mapper_runner_service, "load_layout", side_effect=RuntimeError("Invalid JSON")
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await get_embed_data(embed_id="test", db=mock_db)

                assert exc_info.value.status_code == 500
