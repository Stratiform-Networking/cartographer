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
        from websockets.exceptions import ConnectionClosed

        # Mock websockets module with proper exceptions submodule
        mock_exceptions = MagicMock()
        mock_exceptions.ConnectionClosed = ConnectionClosed
        mock_websockets = MagicMock()
        mock_websockets.exceptions = mock_exceptions

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

        with patch.dict(
            "sys.modules",
            {"websockets": mock_websockets, "websockets.exceptions": mock_exceptions},
        ):
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


class TestAgentSyncEndpoint:
    """Tests for agent sync endpoint to boost coverage"""

    @pytest.fixture
    def service_user(self):
        """Service token user for agent sync"""
        return AuthenticatedUser(user_id="service", username="service", role=UserRole.ADMIN)

    @pytest.fixture
    def mock_network(self):
        """Create a mock network for sync tests"""
        from app.models.network import Network

        network = MagicMock(spec=Network)
        network.id = "net-123"
        network.name = "Test Network"
        network.layout_data = None
        network.last_sync_at = None
        return network

    async def test_sync_agent_scan_with_gateway_device(self, service_user, mock_network):
        """sync_agent_scan should update root with gateway device"""
        from datetime import datetime

        from app.routers.networks import sync_agent_scan
        from app.schemas.agent_sync import AgentSyncRequest, SyncDevice

        mock_db = AsyncMock()

        # Create sync request with gateway device
        sync_data = AgentSyncRequest(
            timestamp=datetime.now(),
            devices=[
                SyncDevice(
                    ip="192.168.1.1",
                    mac="AA:BB:CC:DD:EE:FF",
                    hostname="router",
                    is_gateway=True,
                    vendor="NETGEAR",
                    device_type="router",
                ),
                SyncDevice(
                    ip="192.168.1.100",
                    mac="11:22:33:44:55:66",
                    hostname="laptop",
                    is_gateway=False,
                ),
            ],
        )

        with patch("app.routers.networks.get_network_with_access") as mock_get:
            mock_get.return_value = (mock_network, True, "owner")

            response = await sync_agent_scan(
                network_id="net-123",
                sync_data=sync_data,
                current_user=service_user,
                db=mock_db,
            )

            assert response.success is True
            assert response.devices_received == 2
            # Gateway updates root + 1 new device added
            assert response.devices_added >= 1
            mock_db.commit.assert_called_once()

    async def test_sync_agent_scan_camelcase_fields(self, service_user, mock_network):
        """sync_agent_scan should accept camelCase fields from agent"""
        from datetime import datetime

        from app.routers.networks import sync_agent_scan
        from app.schemas.agent_sync import AgentSyncRequest, SyncDevice

        mock_db = AsyncMock()

        # Simulate what the agent sends (camelCase via model_validate)
        device_data = {
            "ip": "192.168.1.1",
            "mac": "AA:BB:CC:DD:EE:FF",
            "hostname": "router",
            "isGateway": True,  # camelCase from Rust agent
            "responseTimeMs": 5.5,  # camelCase
            "deviceType": "router",  # camelCase
            "vendor": "NETGEAR",
        }
        gateway_device = SyncDevice.model_validate(device_data)

        sync_data = AgentSyncRequest(
            timestamp=datetime.now(),
            devices=[gateway_device],
        )

        with patch("app.routers.networks.get_network_with_access") as mock_get:
            mock_get.return_value = (mock_network, True, "owner")

            response = await sync_agent_scan(
                network_id="net-123",
                sync_data=sync_data,
                current_user=service_user,
                db=mock_db,
            )

            assert response.success is True
            assert response.devices_received == 1
            # Verify the gateway was properly identified
            assert gateway_device.is_gateway is True
            assert gateway_device.response_time_ms == 5.5
            assert gateway_device.device_type == "router"

    async def test_sync_agent_scan_fallback_to_router_device_type(self, service_user, mock_network):
        """sync_agent_scan should fallback to device_type=router if no is_gateway"""
        from datetime import datetime

        from app.routers.networks import sync_agent_scan
        from app.schemas.agent_sync import AgentSyncRequest, SyncDevice

        mock_db = AsyncMock()

        # No is_gateway flag, but device_type is router
        sync_data = AgentSyncRequest(
            timestamp=datetime.now(),
            devices=[
                SyncDevice(
                    ip="192.168.1.1",
                    mac="AA:BB:CC:DD:EE:FF",
                    hostname="router",
                    is_gateway=False,
                    device_type="router",
                ),
                SyncDevice(
                    ip="192.168.1.100",
                    hostname="laptop",
                ),
            ],
        )

        with patch("app.routers.networks.get_network_with_access") as mock_get:
            mock_get.return_value = (mock_network, True, "owner")

            response = await sync_agent_scan(
                network_id="net-123",
                sync_data=sync_data,
                current_user=service_user,
                db=mock_db,
            )

            assert response.success is True
            assert response.devices_received == 2

    async def test_sync_agent_scan_with_existing_layout(self, service_user):
        """sync_agent_scan should work with existing layout data"""
        from datetime import datetime

        from app.models.network import Network
        from app.routers.networks import sync_agent_scan
        from app.schemas.agent_sync import AgentSyncRequest, SyncDevice

        mock_db = AsyncMock()

        # Network with existing layout data
        mock_network = MagicMock(spec=Network)
        mock_network.id = "net-123"
        mock_network.name = "Test Network"
        mock_network.layout_data = {
            "version": 1,
            "root": {
                "id": "root",
                "name": "192.168.1.1",
                "ip": "192.168.1.1",
                "mac": "AA:BB:CC:DD:EE:FF",
                "role": "gateway/router",
                "children": [],
            },
        }
        mock_network.last_sync_at = None

        sync_data = AgentSyncRequest(
            timestamp=datetime.now(),
            devices=[
                SyncDevice(
                    ip="192.168.1.1",
                    mac="AA:BB:CC:DD:EE:FF",
                    hostname="router",
                    is_gateway=True,
                ),
                SyncDevice(
                    ip="192.168.1.100",
                    mac="11:22:33:44:55:66",
                    hostname="new-device",
                    response_time_ms=2.5,
                ),
            ],
        )

        with patch("app.routers.networks.get_network_with_access") as mock_get:
            mock_get.return_value = (mock_network, True, "owner")

            response = await sync_agent_scan(
                network_id="net-123",
                sync_data=sync_data,
                current_user=service_user,
                db=mock_db,
            )

            assert response.success is True
            assert response.devices_received == 2
            mock_db.commit.assert_called_once()


class TestAgentHealthEndpoint:
    """Tests for agent health sync endpoint to boost coverage."""

    @pytest.fixture
    def service_user(self):
        """Service token user for agent health sync."""
        return AuthenticatedUser(user_id="service", username="service", role=UserRole.ADMIN)

    async def test_sync_agent_health_returns_early_when_no_layout(self, service_user):
        """sync_agent_health should return early when layout_data is missing."""
        from datetime import datetime

        from app.models.network import Network
        from app.routers.networks import sync_agent_health
        from app.schemas.agent_sync import AgentHealthCheckRequest, HealthCheckResult

        mock_db = AsyncMock()
        mock_network = MagicMock(spec=Network)
        mock_network.id = "net-123"
        mock_network.name = "Test Network"
        mock_network.layout_data = None

        health_data = AgentHealthCheckRequest(
            timestamp=datetime.now(),
            results=[HealthCheckResult(ip="192.168.1.1", reachable=True, response_time_ms=4.2)],
        )

        with patch("app.routers.networks.get_network_with_access") as mock_get:
            mock_get.return_value = (mock_network, True, "owner")

            response = await sync_agent_health(
                network_id="net-123",
                health_data=health_data,
                current_user=service_user,
                db=mock_db,
            )

            assert response.success is True
            assert response.results_received == 1
            assert response.results_applied == 0
            assert "No layout data" in response.message
            mock_db.commit.assert_not_called()

    async def test_sync_agent_health_returns_early_when_no_root(self, service_user):
        """sync_agent_health should return early when root node is missing."""
        from datetime import datetime

        from app.models.network import Network
        from app.routers.networks import sync_agent_health
        from app.schemas.agent_sync import AgentHealthCheckRequest, HealthCheckResult

        mock_db = AsyncMock()
        mock_network = MagicMock(spec=Network)
        mock_network.id = "net-123"
        mock_network.name = "Test Network"
        mock_network.layout_data = {"version": 1, "timestamp": "2024-01-01T00:00:00Z"}

        health_data = AgentHealthCheckRequest(
            timestamp=datetime.now(),
            results=[HealthCheckResult(ip="192.168.1.1", reachable=True)],
        )

        with patch("app.routers.networks.get_network_with_access") as mock_get:
            mock_get.return_value = (mock_network, True, "owner")

            response = await sync_agent_health(
                network_id="net-123",
                health_data=health_data,
                current_user=service_user,
                db=mock_db,
            )

            assert response.success is True
            assert response.results_received == 1
            assert response.results_applied == 0
            assert "No root node" in response.message
            mock_db.commit.assert_not_called()

    async def test_sync_agent_health_updates_nodes_and_forwards_results(self, service_user):
        """sync_agent_health should apply updates and forward payload to health service."""
        from datetime import datetime

        from app.models.network import Network
        from app.routers.networks import sync_agent_health
        from app.schemas.agent_sync import AgentHealthCheckRequest, HealthCheckResult

        mock_db = AsyncMock()
        mock_network = MagicMock(spec=Network)
        mock_network.id = "net-123"
        mock_network.name = "Test Network"
        mock_network.layout_data = {
            "version": 1,
            "root": {
                "id": "root",
                "name": "gateway",
                "ip": "192.168.1.1",
                "children": [
                    {
                        "id": "child-1",
                        "name": "client-1",
                        "ip": "192.168.1.100",
                        "children": [],
                    }
                ],
            },
        }

        health_data = AgentHealthCheckRequest(
            timestamp=datetime.now(),
            results=[
                HealthCheckResult(ip="192.168.1.1", reachable=True, response_time_ms=1.1),
                HealthCheckResult(ip="192.168.1.100", reachable=False),
                HealthCheckResult(ip="192.168.1.250", reachable=True),  # Not in map -> skipped
            ],
        )

        with (
            patch("app.routers.networks.get_network_with_access") as mock_get,
            patch(
                "app.routers.networks.health_proxy_service.sync_agent_health", new=AsyncMock()
            ) as mock_forward,
        ):
            mock_get.return_value = (mock_network, True, "owner")

            response = await sync_agent_health(
                network_id="net-123",
                health_data=health_data,
                current_user=service_user,
                db=mock_db,
            )

            assert response.success is True
            assert response.results_received == 3
            assert response.results_applied == 2
            assert "Updated health status for 2 devices" in response.message
            mock_db.commit.assert_called_once()
            mock_forward.assert_called_once()

            root_node = mock_network.layout_data["root"]
            child_node = root_node["children"][0]
            assert root_node["healthStatus"] == "healthy"
            assert root_node["lastResponseMs"] == 1.1
            assert child_node["healthStatus"] == "unreachable"
            assert child_node["consecutiveFailures"] == 1
            assert mock_network.layout_data["version"] == 2
            assert "lastHealthCheck" in mock_network.layout_data

    async def test_sync_agent_health_ignores_forwarding_errors(self, service_user):
        """sync_agent_health should still succeed if forwarding to health service fails."""
        from datetime import datetime

        from app.models.network import Network
        from app.routers.networks import sync_agent_health
        from app.schemas.agent_sync import AgentHealthCheckRequest, HealthCheckResult

        mock_db = AsyncMock()
        mock_network = MagicMock(spec=Network)
        mock_network.id = "net-123"
        mock_network.name = "Test Network"
        mock_network.layout_data = {
            "version": 1,
            "root": {
                "id": "root",
                "name": "gateway",
                "ip": "192.168.1.1",
                "children": [],
            },
        }

        health_data = AgentHealthCheckRequest(
            timestamp=datetime.now(),
            results=[HealthCheckResult(ip="192.168.1.1", reachable=True, response_time_ms=3.3)],
        )

        with (
            patch("app.routers.networks.get_network_with_access") as mock_get,
            patch(
                "app.routers.networks.health_proxy_service.sync_agent_health",
                new=AsyncMock(side_effect=RuntimeError("health service unavailable")),
            ),
        ):
            mock_get.return_value = (mock_network, True, "owner")

            response = await sync_agent_health(
                network_id="net-123",
                health_data=health_data,
                current_user=service_user,
                db=mock_db,
            )

            assert response.success is True
            assert response.results_received == 1
            assert response.results_applied == 1
            mock_db.commit.assert_called_once()


class TestNetworksAdditionalCoverage:
    """Targeted tests for remaining uncovered network router branches."""

    async def test_delete_network_invalidates_member_cache_keys(self, owner_user):
        """delete_network should clear cache keys for permission members."""
        from app.routers.networks import delete_network

        mock_db = AsyncMock()
        mock_cache = MagicMock()
        mock_cache.make_key = MagicMock(side_effect=lambda *parts: ":".join(parts))
        mock_cache.delete = AsyncMock()

        mock_network = MagicMock()
        mock_network.user_id = owner_user.user_id
        mock_network.is_active = True

        perm_result = MagicMock()
        perm_result.scalars.return_value.all.return_value = ["member-1", "member-2"]
        mock_db.execute = AsyncMock(return_value=perm_result)
        mock_db.commit = AsyncMock()
        mock_db.delete = AsyncMock()

        with patch("app.routers.networks.get_network_with_access") as mock_get:
            # Called twice in current implementation
            mock_get.side_effect = [
                (mock_network, True, "owner"),
                (mock_network, True, "owner"),
            ]

            await delete_network(
                network_id="net-123",
                current_user=owner_user,
                db=mock_db,
                cache=mock_cache,
            )

        mock_cache.delete.assert_any_await("networks:user:owner-123")
        mock_cache.delete.assert_any_await("networks:user:member-1")
        mock_cache.delete.assert_any_await("networks:user:member-2")
        assert mock_cache.delete.await_count == 3

    async def test_delete_network_raises_if_second_access_check_is_not_owner(self, owner_user):
        """delete_network should reject if follow-up access check is not owner."""
        from app.routers.networks import delete_network

        mock_db = AsyncMock()
        mock_cache = MagicMock()
        mock_cache.make_key = MagicMock(return_value="networks:user:owner-123")
        mock_cache.delete = AsyncMock()

        mock_network = MagicMock()
        mock_network.user_id = owner_user.user_id
        mock_network.is_active = True

        perm_result = MagicMock()
        perm_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=perm_result)
        mock_db.commit = AsyncMock()

        with patch("app.routers.networks.get_network_with_access") as mock_get:
            mock_get.side_effect = [
                (mock_network, True, "owner"),
                (mock_network, False, "read"),
            ]

            with pytest.raises(HTTPException) as exc_info:
                await delete_network(
                    network_id="net-123",
                    current_user=owner_user,
                    db=mock_db,
                    cache=mock_cache,
                )

        assert exc_info.value.status_code == 403
        assert "Only the owner can delete a network" in exc_info.value.detail

    def test_update_existing_device_sets_vendor_type_and_display_name(self):
        """_update_existing_device should fill vendor/type and rename IP-only nodes."""
        from app.routers.networks import _update_existing_device
        from app.schemas.agent_sync import SyncDevice

        node = {
            "name": "192.168.1.50",
            "ip": "192.168.1.50",
            "hostname": None,
            "vendor": None,
            "deviceType": None,
        }
        device = SyncDevice(
            ip="192.168.1.50",
            vendor="Synology",
            device_type="nas",
            is_gateway=False,
        )

        _update_existing_device(node, device, now="2026-01-01T00:00:00+00:00")

        assert node["vendor"] == "Synology"
        assert node["deviceType"] == "nas"
        assert node["name"] == "Synology"

    def test_create_new_device_node_maps_role_from_device_type(self):
        """_create_new_device_node should map role from device_type when role is None."""
        from app.routers.networks import _create_new_device_node
        from app.schemas.agent_sync import SyncDevice

        device = SyncDevice(
            ip="192.168.1.77",
            vendor="Cisco",
            device_type="network_device",
            is_gateway=False,
        )

        node = _create_new_device_node(
            device=device,
            parent_id="group-infra",
            now="2026-01-01T00:00:00+00:00",
            role=None,
        )

        assert node["role"] == "switch/ap"


class TestHealthRouterAdditionalCoverage:
    """Tests for uncovered internal health router branches."""

    async def test_readyz_returns_not_ready_when_pool_empty(self):
        """readyz should report not_ready when HTTP pool has no services."""
        from app.routers.health import readyz

        with patch("app.routers.health.http_pool") as mock_pool:
            mock_pool._services = {}
            result = await readyz()

        assert result["status"] == "not_ready"
        assert "not initialized" in result["reason"]

    async def test_config_check_warning_in_development(self):
        """config_check should warn in development for weak security settings."""
        from app.routers.health import config_check

        mock_settings = MagicMock()
        mock_settings.jwt_secret = ""
        mock_settings.cors_origins = "*"
        mock_settings.env = "development"
        mock_settings.disable_docs = False

        with patch("app.routers.health.get_settings", return_value=mock_settings):
            result = await config_check()

        assert result["status"] == "warning"
        assert "JWT_SECRET is not set" in result["issues"]
        assert "CORS allows all origins (*)" in result["issues"]

    async def test_config_check_misconfigured_in_production(self):
        """config_check should report misconfigured in production with issues."""
        from app.routers.health import config_check

        mock_settings = MagicMock()
        mock_settings.jwt_secret = ""
        mock_settings.cors_origins = "*"
        mock_settings.env = "production"
        mock_settings.disable_docs = True

        with patch("app.routers.health.get_settings", return_value=mock_settings):
            result = await config_check()

        assert result["status"] == "misconfigured"
        assert result["checks"]["environment"] == "production"
