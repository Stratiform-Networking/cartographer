"""
Unit tests for metrics router endpoints.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models import (
    DeviceRole,
    EndpointUsage,
    EndpointUsageRecord,
    GatewayISPInfo,
    HealthStatus,
    NetworkTopologySnapshot,
    NodeConnection,
    NodeMetrics,
    PublishConfig,
    ServiceUsageSummary,
    SpeedTestMetrics,
    TestIPMetrics,
    UsageRecordBatch,
    UsageStatsResponse,
)
from app.routers.metrics import ConnectionManager, connection_manager, router


@pytest.fixture
def app():
    """Create test app with metrics router"""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api")
    return test_app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_snapshot():
    """Create mock snapshot"""
    now = datetime.now(timezone.utc)
    return NetworkTopologySnapshot(
        snapshot_id="test-123",
        timestamp=now,
        version=1,
        total_nodes=3,
        healthy_nodes=2,
        degraded_nodes=1,
        unhealthy_nodes=0,
        unknown_nodes=0,
        nodes={
            "gateway-1": NodeMetrics(
                id="gateway-1",
                name="Router",
                ip="192.168.1.1",
                role=DeviceRole.GATEWAY_ROUTER,
                status=HealthStatus.HEALTHY,
            ),
            "server-1": NodeMetrics(
                id="server-1",
                name="Server",
                ip="192.168.1.10",
                role=DeviceRole.SERVER,
                status=HealthStatus.DEGRADED,
            ),
        },
        connections=[
            NodeConnection(source_id="gateway-1", target_id="server-1", connection_speed="1GbE")
        ],
        gateways=[
            GatewayISPInfo(
                gateway_ip="192.168.1.1",
                test_ips=[
                    TestIPMetrics(ip="8.8.8.8", label="Google DNS", status=HealthStatus.HEALTHY)
                ],
                last_speed_test=SpeedTestMetrics(success=True, timestamp=now, download_mbps=100.0),
                last_speed_test_timestamp=now,
            )
        ],
        root_node_id="root-1",
    )


class TestSnapshotEndpoints:
    """Tests for snapshot endpoints"""

    def test_get_current_snapshot_success(self, client, mock_snapshot):
        """Should return current snapshot"""
        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator.get_last_snapshot.return_value = mock_snapshot

            response = client.get("/api/metrics/snapshot")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["snapshot"]["snapshot_id"] == "test-123"

    def test_get_current_snapshot_not_available(self, client):
        """Should return error when no snapshot"""
        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator.get_last_snapshot.return_value = None

            response = client.get("/api/metrics/snapshot")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "message" in data

    def test_generate_snapshot_success(self, client, mock_snapshot):
        """Should generate new snapshot"""
        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator.generate_snapshot = AsyncMock(return_value=mock_snapshot)

            response = client.post("/api/metrics/snapshot/generate")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_generate_snapshot_no_layout(self, client):
        """Should return error when no layout"""
        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator.generate_snapshot = AsyncMock(return_value=None)

            response = client.post("/api/metrics/snapshot/generate")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False

    def test_generate_snapshot_error(self, client):
        """Should handle errors"""
        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator.generate_snapshot = AsyncMock(side_effect=Exception("Error"))

            response = client.post("/api/metrics/snapshot/generate")

            assert response.status_code == 500

    def test_publish_snapshot_success(self, client):
        """Should publish snapshot"""
        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator.publish_snapshot = AsyncMock(return_value=True)

            response = client.post("/api/metrics/snapshot/publish")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_publish_snapshot_failure(self, client):
        """Should return error on publish failure"""
        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator.publish_snapshot = AsyncMock(return_value=False)

            response = client.post("/api/metrics/snapshot/publish")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False

    def test_get_cached_snapshot_success(self, client, mock_snapshot):
        """Should get cached snapshot from Redis"""
        with patch("app.routers.metrics.redis_publisher") as mock_redis:
            mock_redis.get_last_snapshot = AsyncMock(return_value=mock_snapshot)

            response = client.get("/api/metrics/snapshot/cached")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_get_cached_snapshot_not_found(self, client):
        """Should return error when no cached snapshot"""
        with patch("app.routers.metrics.redis_publisher") as mock_redis:
            mock_redis.get_last_snapshot = AsyncMock(return_value=None)

            response = client.get("/api/metrics/snapshot/cached")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False


class TestConfigEndpoints:
    """Tests for configuration endpoints"""

    def test_get_config(self, client):
        """Should return config"""
        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator.get_config.return_value = {
                "publishing_enabled": True,
                "publish_interval_seconds": 30,
                "is_running": True,
                "last_snapshot_id": "test-123",
                "last_snapshot_timestamp": "2024-01-01T00:00:00",
            }

            with patch("app.routers.metrics.redis_publisher") as mock_redis:
                mock_redis.get_connection_info = AsyncMock(return_value={"connected": True})

                response = client.get("/api/metrics/config")

        assert response.status_code == 200
        data = response.json()
        assert data["redis_connected"] is True
        assert data["publishing_enabled"] is True

    def test_update_config(self, client):
        """Should update config"""
        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator.set_publishing_enabled = MagicMock()
            mock_aggregator.set_publish_interval = MagicMock()

            response = client.post(
                "/api/metrics/config", json={"enabled": False, "publish_interval_seconds": 60}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_update_config_error(self, client):
        """Should handle config update error"""
        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator.set_publishing_enabled.side_effect = Exception("Error")

            response = client.post(
                "/api/metrics/config", json={"enabled": False, "publish_interval_seconds": 60}
            )

        assert response.status_code == 500


class TestSpeedTestEndpoint:
    """Tests for speed test endpoint"""

    def test_trigger_speed_test_success(self, client):
        """Should trigger speed test"""
        result = SpeedTestMetrics(
            success=True, timestamp=datetime.now(timezone.utc), download_mbps=100.0
        )

        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator.trigger_speed_test = AsyncMock(return_value=result)

            response = client.post("/api/metrics/speed-test", json={"gateway_ip": "192.168.1.1"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_trigger_speed_test_failure(self, client):
        """Should handle speed test failure"""
        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator.trigger_speed_test = AsyncMock(return_value=None)

            response = client.post("/api/metrics/speed-test", json={"gateway_ip": "192.168.1.1"})

        assert response.status_code == 500


class TestRedisEndpoints:
    """Tests for Redis endpoints"""

    def test_get_redis_status(self, client):
        """Should get Redis status"""
        with patch("app.routers.metrics.redis_publisher") as mock_redis:
            mock_redis.get_connection_info = AsyncMock(
                return_value={"connected": True, "url": "redis://localhost:6379"}
            )

            response = client.get("/api/metrics/redis/status")

        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is True

    def test_reconnect_redis_success(self, client):
        """Should reconnect to Redis"""
        with patch("app.routers.metrics.redis_publisher") as mock_redis:
            mock_redis.disconnect = AsyncMock()
            mock_redis.connect = AsyncMock(return_value=True)

            response = client.post("/api/metrics/redis/reconnect")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_reconnect_redis_failure(self, client):
        """Should handle reconnection failure"""
        with patch("app.routers.metrics.redis_publisher") as mock_redis:
            mock_redis.disconnect = AsyncMock()
            mock_redis.connect = AsyncMock(return_value=False)

            response = client.post("/api/metrics/redis/reconnect")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False


class TestSummaryEndpoints:
    """Tests for summary endpoints"""

    def test_get_summary_success(self, client, mock_snapshot):
        """Should get summary"""
        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator.get_last_snapshot.return_value = mock_snapshot

            response = client.get("/api/metrics/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert "health_summary" in data
        assert "role_counts" in data

    def test_get_summary_no_snapshot(self, client):
        """Should handle no snapshot"""
        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator.get_last_snapshot.return_value = None

            response = client.get("/api/metrics/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False

    def test_get_node_metrics(self, client, mock_snapshot):
        """Should get node metrics"""
        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator.get_last_snapshot.return_value = mock_snapshot

            response = client.get("/api/metrics/nodes/gateway-1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "gateway-1"

    def test_get_node_metrics_not_found(self, client, mock_snapshot):
        """Should return 404 for unknown node"""
        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator.get_last_snapshot.return_value = mock_snapshot

            response = client.get("/api/metrics/nodes/nonexistent")

        assert response.status_code == 404

    def test_get_node_metrics_no_snapshot(self, client):
        """Should return 404 when no snapshot"""
        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator.get_last_snapshot.return_value = None

            response = client.get("/api/metrics/nodes/gateway-1")

        assert response.status_code == 404

    def test_get_connections(self, client, mock_snapshot):
        """Should get connections"""
        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator.get_last_snapshot.return_value = mock_snapshot

            response = client.get("/api/metrics/connections")

        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert len(data["connections"]) == 1

    def test_get_connections_no_snapshot(self, client):
        """Should handle no snapshot"""
        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator.get_last_snapshot.return_value = None

            response = client.get("/api/metrics/connections")

        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False

    def test_get_gateways(self, client, mock_snapshot):
        """Should get gateways"""
        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator.get_last_snapshot.return_value = mock_snapshot

            response = client.get("/api/metrics/gateways")

        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert len(data["gateways"]) == 1

    def test_get_gateways_no_snapshot(self, client):
        """Should handle no snapshot"""
        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator.get_last_snapshot.return_value = None

            response = client.get("/api/metrics/gateways")

        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False


class TestDebugEndpoints:
    """Tests for debug endpoints"""

    def test_debug_layout_success(self, client):
        """Should return debug layout info"""
        layout = {
            "root": {"id": "root-1", "name": "Network", "notes": "Test notes", "children": []}
        }

        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator._fetch_network_layout = AsyncMock(return_value=layout)

            response = client.get("/api/metrics/debug/layout")

        assert response.status_code == 200
        data = response.json()
        assert data["layout_exists"] is True
        assert data["has_root"] is True

    def test_debug_layout_not_found(self, client):
        """Should handle no layout"""
        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator._fetch_network_layout = AsyncMock(return_value=None)

            response = client.get("/api/metrics/debug/layout")

        assert response.status_code == 200
        data = response.json()
        assert data["error"] == "Failed to fetch layout for network_id=None"


class TestConnectionManager:
    """Tests for WebSocket ConnectionManager"""

    async def test_connect(self):
        """Should accept and add connection"""
        manager = ConnectionManager()
        mock_websocket = AsyncMock()

        await manager.connect(mock_websocket)

        mock_websocket.accept.assert_called_once()
        assert mock_websocket in manager.active_connections

    def test_disconnect(self):
        """Should remove connection"""
        manager = ConnectionManager()
        mock_websocket = MagicMock()
        manager.active_connections.append(mock_websocket)

        manager.disconnect(mock_websocket)

        assert mock_websocket not in manager.active_connections

    def test_disconnect_not_in_list(self):
        """Should handle disconnecting non-existent connection"""
        manager = ConnectionManager()
        mock_websocket = MagicMock()

        # Should not raise
        manager.disconnect(mock_websocket)

    async def test_broadcast(self):
        """Should broadcast to all connections"""
        manager = ConnectionManager()
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        manager.active_connections = [mock_ws1, mock_ws2]

        await manager.broadcast({"message": "test"})

        mock_ws1.send_json.assert_called_once()
        mock_ws2.send_json.assert_called_once()

    async def test_broadcast_handles_disconnected(self):
        """Should handle disconnected clients during broadcast"""
        manager = ConnectionManager()
        mock_ws1 = AsyncMock()
        mock_ws1.send_json = AsyncMock(side_effect=Exception("Disconnected"))
        mock_ws2 = AsyncMock()
        manager.active_connections = [mock_ws1, mock_ws2]

        await manager.broadcast({"message": "test"})

        # Disconnected client should be removed
        assert mock_ws1 not in manager.active_connections
        assert mock_ws2 in manager.active_connections


class TestWebSocketEndpoint:
    """Tests for WebSocket endpoint"""

    def test_websocket_connection(self, app, mock_snapshot):
        """Should accept WebSocket connection"""
        from starlette.testclient import TestClient

        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator.get_last_snapshot.return_value = mock_snapshot

            with patch("app.routers.metrics.redis_publisher") as mock_redis:
                mock_redis.add_handler = MagicMock()
                mock_redis.remove_handler = MagicMock()
                mock_redis.subscribe = AsyncMock(return_value=True)

                client = TestClient(app)

                with client.websocket_connect("/api/metrics/ws") as websocket:
                    # Should receive initial snapshot
                    data = websocket.receive_json()
                    assert data["type"] == "initial_snapshot"

    def test_websocket_no_initial_snapshot(self, app):
        """Should handle no initial snapshot"""
        from starlette.testclient import TestClient

        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            mock_aggregator.get_last_snapshot.return_value = None

            with patch("app.routers.metrics.redis_publisher") as mock_redis:
                mock_redis.add_handler = MagicMock()
                mock_redis.remove_handler = MagicMock()
                mock_redis.subscribe = AsyncMock(return_value=True)

                client = TestClient(app)

                with client.websocket_connect("/api/metrics/ws") as websocket:
                    # Should still connect even without snapshot
                    websocket.send_json({"action": "request_snapshot"})
                    # No response since no snapshot

    def test_websocket_request_snapshot(self, app, mock_snapshot):
        """Should handle snapshot request"""
        from starlette.testclient import TestClient

        with patch("app.routers.metrics.metrics_aggregator") as mock_aggregator:
            # First call returns snapshot for initial, second for request
            mock_aggregator.get_last_snapshot.return_value = mock_snapshot

            with patch("app.routers.metrics.redis_publisher") as mock_redis:
                mock_redis.add_handler = MagicMock()
                mock_redis.remove_handler = MagicMock()
                mock_redis.subscribe = AsyncMock(return_value=True)

                client = TestClient(app)

                with client.websocket_connect("/api/metrics/ws") as websocket:
                    # Receive initial snapshot first
                    data = websocket.receive_json()
                    assert data["type"] == "initial_snapshot"

                    # Request another snapshot
                    websocket.send_json({"action": "request_snapshot"})
                    data = websocket.receive_json()
                    assert data["type"] == "snapshot"


class TestUsageEndpoints:
    """Tests for usage statistics endpoints"""

    @pytest.fixture
    def sample_usage_record(self):
        """Create sample usage record"""
        return {
            "endpoint": "/api/health/status",
            "method": "GET",
            "service": "health-service",
            "status_code": 200,
            "response_time_ms": 45.5,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @pytest.fixture
    def sample_usage_stats(self):
        """Create sample usage stats response"""
        return UsageStatsResponse(
            services={
                "health-service": ServiceUsageSummary(
                    service="health-service",
                    total_requests=100,
                    total_successes=95,
                    total_errors=5,
                    avg_response_time_ms=45.0,
                    endpoints=[
                        EndpointUsage(
                            endpoint="/api/health/status",
                            method="GET",
                            service="health-service",
                            request_count=80,
                            success_count=78,
                            error_count=2,
                            avg_response_time_ms=40.0,
                        )
                    ],
                )
            },
            total_requests=100,
            total_services=1,
            collection_started=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc),
        )

    def test_record_usage_success(self, client, sample_usage_record):
        """Should record single usage event"""
        with patch("app.routers.metrics.usage_tracker") as mock_tracker:
            mock_tracker.record_usage = AsyncMock(return_value=True)

            response = client.post("/api/metrics/usage/record", json=sample_usage_record)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "Usage recorded" in data["message"]

    def test_record_usage_fallback(self, client, sample_usage_record):
        """Should indicate fallback to local when Redis unavailable"""
        with patch("app.routers.metrics.usage_tracker") as mock_tracker:
            mock_tracker.record_usage = AsyncMock(return_value=False)

            response = client.post("/api/metrics/usage/record", json=sample_usage_record)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "locally" in data["message"]

    def test_record_usage_error(self, client, sample_usage_record):
        """Should handle errors gracefully"""
        with patch("app.routers.metrics.usage_tracker") as mock_tracker:
            mock_tracker.record_usage = AsyncMock(side_effect=Exception("Test error"))

            response = client.post("/api/metrics/usage/record", json=sample_usage_record)

            assert response.status_code == 500

    def test_record_usage_batch_success(self, client, sample_usage_record):
        """Should record batch of usage events"""
        batch = {"records": [sample_usage_record, sample_usage_record, sample_usage_record]}

        with patch("app.routers.metrics.usage_tracker") as mock_tracker:
            mock_tracker.record_batch = AsyncMock(return_value=3)

            response = client.post("/api/metrics/usage/record/batch", json=batch)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["recorded"] == 3
            assert data["total"] == 3

    def test_record_usage_batch_partial(self, client, sample_usage_record):
        """Should handle partial batch success"""
        batch = {"records": [sample_usage_record, sample_usage_record, sample_usage_record]}

        with patch("app.routers.metrics.usage_tracker") as mock_tracker:
            mock_tracker.record_batch = AsyncMock(return_value=2)

            response = client.post("/api/metrics/usage/record/batch", json=batch)

            assert response.status_code == 200
            data = response.json()
            assert data["recorded"] == 2
            assert data["total"] == 3

    def test_record_usage_batch_error(self, client, sample_usage_record):
        """Should handle batch errors"""
        batch = {"records": [sample_usage_record]}

        with patch("app.routers.metrics.usage_tracker") as mock_tracker:
            mock_tracker.record_batch = AsyncMock(side_effect=Exception("Test error"))

            response = client.post("/api/metrics/usage/record/batch", json=batch)

            assert response.status_code == 500

    def test_get_usage_stats_all(self, client, sample_usage_stats):
        """Should get all usage stats"""
        with patch("app.routers.metrics.usage_tracker") as mock_tracker:
            mock_tracker.get_usage_stats = AsyncMock(return_value=sample_usage_stats)

            response = client.get("/api/metrics/usage/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["total_services"] == 1
            assert data["total_requests"] == 100
            assert "health-service" in data["services"]

    def test_get_usage_stats_filtered(self, client, sample_usage_stats):
        """Should filter by service"""
        with patch("app.routers.metrics.usage_tracker") as mock_tracker:
            mock_tracker.get_usage_stats = AsyncMock(return_value=sample_usage_stats)

            response = client.get("/api/metrics/usage/stats?service=health-service")

            assert response.status_code == 200
            mock_tracker.get_usage_stats.assert_called_once_with("health-service")

    def test_get_usage_stats_error(self, client):
        """Should handle stats retrieval error"""
        with patch("app.routers.metrics.usage_tracker") as mock_tracker:
            mock_tracker.get_usage_stats = AsyncMock(side_effect=Exception("Test error"))

            response = client.get("/api/metrics/usage/stats")

            assert response.status_code == 500

    def test_reset_usage_stats_all(self, client):
        """Should reset all usage stats"""
        with patch("app.routers.metrics.usage_tracker") as mock_tracker:
            mock_tracker.reset_stats = AsyncMock(return_value=True)

            response = client.delete("/api/metrics/usage/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "all services" in data["message"]
            mock_tracker.reset_stats.assert_called_once_with(None)

    def test_reset_usage_stats_single_service(self, client):
        """Should reset single service stats"""
        with patch("app.routers.metrics.usage_tracker") as mock_tracker:
            mock_tracker.reset_stats = AsyncMock(return_value=True)

            response = client.delete("/api/metrics/usage/stats?service=health-service")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "health-service" in data["message"]
            mock_tracker.reset_stats.assert_called_once_with("health-service")

    def test_reset_usage_stats_failure(self, client):
        """Should handle reset failure"""
        with patch("app.routers.metrics.usage_tracker") as mock_tracker:
            mock_tracker.reset_stats = AsyncMock(return_value=False)

            response = client.delete("/api/metrics/usage/stats")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False

    def test_reset_usage_stats_error(self, client):
        """Should handle reset error"""
        with patch("app.routers.metrics.usage_tracker") as mock_tracker:
            mock_tracker.reset_stats = AsyncMock(side_effect=Exception("Test error"))

            response = client.delete("/api/metrics/usage/stats")

            assert response.status_code == 500
