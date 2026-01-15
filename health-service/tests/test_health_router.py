"""
Unit tests for health router endpoints.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models import (
    DeviceMetrics,
    DnsResult,
    GatewayTestIP,
    GatewayTestIPConfig,
    GatewayTestIPMetrics,
    GatewayTestIPsResponse,
    HealthStatus,
    MonitoringConfig,
    MonitoringStatus,
    PingResult,
    PortCheckResult,
    SpeedTestResult,
)
from app.routers.health import router


@pytest.fixture
def app():
    """Create test app with health router"""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api")
    return test_app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def sample_metrics():
    """Sample device metrics"""
    return DeviceMetrics(
        ip="192.168.1.1",
        status=HealthStatus.HEALTHY,
        last_check=datetime.utcnow(),
        ping=PingResult(success=True, latency_ms=25.0, packet_loss_percent=0.0),
    )


@pytest.fixture
def sample_ping():
    """Sample ping result"""
    return PingResult(
        success=True,
        latency_ms=25.0,
        packet_loss_percent=0.0,
        min_latency_ms=20.0,
        max_latency_ms=30.0,
        avg_latency_ms=25.0,
        jitter_ms=2.0,
    )


class TestCheckSingleDevice:
    """Tests for GET /api/health/check/{ip}"""

    def test_check_device_success(self, client, sample_metrics):
        """Should return device metrics"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.check_device_health = AsyncMock(return_value=sample_metrics)

            response = client.get("/api/health/check/192.168.1.1")

            assert response.status_code == 200
            data = response.json()
            assert data["ip"] == "192.168.1.1"
            assert data["status"] == "healthy"

    def test_check_device_with_ports(self, client, sample_metrics):
        """Should pass include_ports parameter"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.check_device_health = AsyncMock(return_value=sample_metrics)

            response = client.get("/api/health/check/192.168.1.1?include_ports=true")

            assert response.status_code == 200
            mock_checker.check_device_health.assert_called_once_with(
                ip="192.168.1.1", include_ports=True, include_dns=True
            )

    def test_check_device_error(self, client):
        """Should return 500 on error"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.check_device_health = AsyncMock(side_effect=Exception("Check failed"))

            response = client.get("/api/health/check/192.168.1.1")

            assert response.status_code == 500


class TestCheckMultipleDevices:
    """Tests for POST /api/health/check/batch"""

    def test_batch_check_success(self, client, sample_metrics):
        """Should check multiple devices"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.check_multiple_devices = AsyncMock(
                return_value={"192.168.1.1": sample_metrics, "192.168.1.2": sample_metrics}
            )

            response = client.post(
                "/api/health/check/batch", json={"ips": ["192.168.1.1", "192.168.1.2"]}
            )

            assert response.status_code == 200
            data = response.json()
            assert "devices" in data
            assert len(data["devices"]) == 2

    def test_batch_check_empty_ips(self, client):
        """Should return 400 for empty IPs"""
        response = client.post("/api/health/check/batch", json={"ips": []})

        assert response.status_code == 400

    def test_batch_check_too_many_ips(self, client):
        """Should return 400 for >100 IPs"""
        ips = [f"192.168.1.{i}" for i in range(101)]

        response = client.post("/api/health/check/batch", json={"ips": ips})

        assert response.status_code == 400

    def test_batch_check_error(self, client):
        """Should return 500 on error"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.check_multiple_devices = AsyncMock(side_effect=Exception("Batch failed"))

            response = client.post("/api/health/check/batch", json={"ips": ["192.168.1.1"]})

            assert response.status_code == 500


class TestCachedMetrics:
    """Tests for cached metrics endpoints"""

    def test_get_cached_metrics_found(self, client, sample_metrics):
        """Should return cached metrics"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.get_cached_metrics = MagicMock(return_value=sample_metrics)

            response = client.get("/api/health/cached/192.168.1.1")

            assert response.status_code == 200

    def test_get_cached_metrics_not_found(self, client):
        """Should return 404 when not cached"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.get_cached_metrics = MagicMock(return_value=None)

            response = client.get("/api/health/cached/192.168.1.1")

            assert response.status_code == 404

    def test_get_all_cached_metrics(self, client, sample_metrics):
        """Should return all cached metrics"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.get_all_cached_metrics = MagicMock(
                return_value={"192.168.1.1": sample_metrics}
            )

            response = client.get("/api/health/cached")

            assert response.status_code == 200

    def test_clear_cache(self, client):
        """Should clear the cache"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.clear_cache = MagicMock()

            response = client.delete("/api/health/cache")

            assert response.status_code == 200
            mock_checker.clear_cache.assert_called_once()


class TestQuickPing:
    """Tests for GET /api/health/ping/{ip}"""

    def test_quick_ping_success(self, client, sample_ping):
        """Should return ping result"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.ping_host = AsyncMock(return_value=sample_ping)

            response = client.get("/api/health/ping/192.168.1.1")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_quick_ping_custom_count(self, client, sample_ping):
        """Should use custom ping count"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.ping_host = AsyncMock(return_value=sample_ping)

            response = client.get("/api/health/ping/192.168.1.1?count=5")

            assert response.status_code == 200
            mock_checker.ping_host.assert_called_once_with("192.168.1.1", count=5)

    def test_quick_ping_error(self, client):
        """Should return 500 on error"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.ping_host = AsyncMock(side_effect=Exception("Ping failed"))

            response = client.get("/api/health/ping/192.168.1.1")

            assert response.status_code == 500


class TestPortScan:
    """Tests for GET /api/health/ports/{ip}"""

    def test_scan_ports_success(self, client):
        """Should return open ports"""
        open_ports = [
            PortCheckResult(port=80, open=True, service="HTTP"),
            PortCheckResult(port=443, open=True, service="HTTPS"),
        ]

        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.scan_common_ports = AsyncMock(return_value=open_ports)

            response = client.get("/api/health/ports/192.168.1.1")

            assert response.status_code == 200
            data = response.json()
            assert data["ip"] == "192.168.1.1"
            assert len(data["open_ports"]) == 2

    def test_scan_ports_error(self, client):
        """Should return 500 on error"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.scan_common_ports = AsyncMock(side_effect=Exception("Scan failed"))

            response = client.get("/api/health/ports/192.168.1.1")

            assert response.status_code == 500


class TestDnsCheck:
    """Tests for GET /api/health/dns/{ip}"""

    def test_dns_check_success(self, client):
        """Should return DNS result"""
        dns_result = DnsResult(
            success=True,
            resolved_hostname="router.local",
            reverse_dns="router.local",
            resolution_time_ms=5.0,
        )

        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.check_dns = AsyncMock(return_value=dns_result)

            response = client.get("/api/health/dns/192.168.1.1")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_dns_check_error(self, client):
        """Should return 500 on error"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.check_dns = AsyncMock(side_effect=Exception("DNS failed"))

            response = client.get("/api/health/dns/192.168.1.1")

            assert response.status_code == 500


class TestMonitoringDevices:
    """Tests for monitoring device endpoints"""

    def test_register_devices(self, client):
        """Should register devices for monitoring"""
        with (
            patch("app.routers.health.health_checker") as mock_checker,
            patch(
                "app.routers.health.sync_devices_with_notification_service", new_callable=AsyncMock
            ) as mock_sync,
        ):
            mock_checker.set_monitored_devices = MagicMock()
            mock_sync.return_value = True

            response = client.post(
                "/api/health/monitoring/devices",
                json={"ips": ["192.168.1.1", "192.168.1.2"], "network_id": "network-uuid-42"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Registered 2 devices for monitoring"
            assert data["network_id"] == "network-uuid-42"
            mock_sync.assert_called_once_with(
                ["192.168.1.1", "192.168.1.2"], network_id="network-uuid-42"
            )

    def test_get_monitored_devices(self, client):
        """Should return monitored devices"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.get_monitored_devices = MagicMock(return_value=["192.168.1.1"])

            response = client.get("/api/health/monitoring/devices")

            assert response.status_code == 200
            assert response.json()["devices"] == ["192.168.1.1"]

    def test_clear_monitored_devices(self, client):
        """Should clear monitored devices"""
        with (
            patch("app.routers.health.health_checker") as mock_checker,
            patch(
                "app.routers.health.sync_devices_with_notification_service", new_callable=AsyncMock
            ) as mock_sync,
        ):
            mock_checker.set_monitored_devices = MagicMock()
            mock_sync.return_value = False  # No network_id means it returns False

            response = client.delete("/api/health/monitoring/devices")

            assert response.status_code == 200
            mock_checker.set_monitored_devices.assert_called_once_with({})
            mock_sync.assert_called_once_with([])


class TestMonitoringConfig:
    """Tests for monitoring config endpoints"""

    def test_get_monitoring_config(self, client):
        """Should return monitoring config"""
        config = MonitoringConfig(enabled=True, check_interval_seconds=30)

        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.get_monitoring_config = MagicMock(return_value=config)

            response = client.get("/api/health/monitoring/config")

            assert response.status_code == 200

    def test_set_monitoring_config(self, client):
        """Should update monitoring config"""
        config = MonitoringConfig(enabled=False, check_interval_seconds=60)

        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.set_monitoring_config = MagicMock()
            mock_checker.get_monitoring_config = MagicMock(return_value=config)

            response = client.post(
                "/api/health/monitoring/config",
                json={"enabled": False, "check_interval_seconds": 60},
            )

            assert response.status_code == 200


class TestMonitoringStatus:
    """Tests for monitoring status endpoint"""

    def test_get_monitoring_status(self, client):
        """Should return monitoring status"""
        status = MonitoringStatus(
            enabled=True,
            check_interval_seconds=30,
            include_dns=True,
            monitored_devices=["192.168.1.1"],
            last_check=datetime.utcnow(),
            next_check=datetime.utcnow(),
        )

        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.get_monitoring_status = MagicMock(return_value=status)

            response = client.get("/api/health/monitoring/status")

            assert response.status_code == 200


class TestMonitoringControls:
    """Tests for monitoring start/stop endpoints"""

    def test_start_monitoring(self, client):
        """Should start monitoring"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.start_monitoring = MagicMock()

            response = client.post("/api/health/monitoring/start")

            assert response.status_code == 200
            mock_checker.start_monitoring.assert_called_once()

    def test_stop_monitoring(self, client):
        """Should stop monitoring"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.stop_monitoring = MagicMock()

            response = client.post("/api/health/monitoring/stop")

            assert response.status_code == 200
            mock_checker.stop_monitoring.assert_called_once()

    def test_trigger_immediate_check(self, client):
        """Should trigger immediate check"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.get_monitored_devices = MagicMock(return_value=["192.168.1.1"])
            mock_checker._perform_monitoring_check = AsyncMock()

            response = client.post("/api/health/monitoring/check-now")

            assert response.status_code == 200

    def test_trigger_immediate_check_no_devices(self, client):
        """Should return 400 when no devices registered"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.get_monitored_devices = MagicMock(return_value=[])

            response = client.post("/api/health/monitoring/check-now")

            assert response.status_code == 400


class TestGatewayTestIPs:
    """Tests for gateway test IP endpoints"""

    def test_get_all_gateway_test_ips(self, client):
        """Should return all gateway configs"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.get_all_gateway_test_ips = MagicMock(return_value={})

            response = client.get("/api/health/gateway/test-ips/all")

            assert response.status_code == 200

    def test_get_all_gateway_test_ip_metrics(self, client):
        """Should return all gateway metrics"""
        metrics_response = GatewayTestIPsResponse(
            gateway_ip="192.168.1.1", test_ips=[], last_check=None
        )

        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.get_all_gateway_test_ips = MagicMock(return_value={"192.168.1.1": {}})
            mock_checker.get_cached_test_ip_metrics = MagicMock(return_value=metrics_response)

            response = client.get("/api/health/gateway/test-ips/all/metrics")

            assert response.status_code == 200

    def test_set_gateway_test_ips(self, client):
        """Should set test IPs for gateway"""
        config = GatewayTestIPConfig(
            gateway_ip="192.168.1.1",
            test_ips=[GatewayTestIP(ip="8.8.8.8", label="Google")],
            enabled=True,
        )

        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.set_gateway_test_ips = MagicMock(return_value=config)

            response = client.post(
                "/api/health/gateway/192.168.1.1/test-ips",
                json={
                    "gateway_ip": "192.168.1.1",
                    "test_ips": [{"ip": "8.8.8.8", "label": "Google"}],
                },
            )

            assert response.status_code == 200

    def test_set_gateway_test_ips_mismatch(self, client):
        """Should return 400 if gateway IP doesn't match"""
        response = client.post(
            "/api/health/gateway/192.168.1.1/test-ips",
            json={"gateway_ip": "192.168.1.2", "test_ips": [{"ip": "8.8.8.8"}]},
        )

        assert response.status_code == 400

    def test_get_gateway_test_ips(self, client):
        """Should get test IPs for gateway"""
        config = GatewayTestIPConfig(gateway_ip="192.168.1.1", test_ips=[], enabled=True)

        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.get_gateway_test_ips = MagicMock(return_value=config)

            response = client.get("/api/health/gateway/192.168.1.1/test-ips")

            assert response.status_code == 200

    def test_get_gateway_test_ips_not_found(self, client):
        """Should return 404 for unconfigured gateway"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.get_gateway_test_ips = MagicMock(return_value=None)

            response = client.get("/api/health/gateway/192.168.1.99/test-ips")

            assert response.status_code == 404

    def test_delete_gateway_test_ips(self, client):
        """Should delete test IPs for gateway"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.remove_gateway_test_ips = MagicMock(return_value=True)

            response = client.delete("/api/health/gateway/192.168.1.1/test-ips")

            assert response.status_code == 200

    def test_delete_gateway_test_ips_not_found(self, client):
        """Should return 404 for unconfigured gateway"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.remove_gateway_test_ips = MagicMock(return_value=False)

            response = client.delete("/api/health/gateway/192.168.1.99/test-ips")

            assert response.status_code == 404

    def test_check_gateway_test_ips(self, client):
        """Should check all test IPs for gateway"""
        config = GatewayTestIPConfig(
            gateway_ip="192.168.1.1", test_ips=[GatewayTestIP(ip="8.8.8.8")], enabled=True
        )
        response_data = GatewayTestIPsResponse(
            gateway_ip="192.168.1.1", test_ips=[], last_check=datetime.utcnow()
        )

        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.get_gateway_test_ips = MagicMock(return_value=config)
            mock_checker.check_gateway_test_ips = AsyncMock(return_value=response_data)

            response = client.get("/api/health/gateway/192.168.1.1/test-ips/check")

            assert response.status_code == 200

    def test_check_gateway_test_ips_not_configured(self, client):
        """Should return 404 for unconfigured gateway"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.get_gateway_test_ips = MagicMock(return_value=None)

            response = client.get("/api/health/gateway/192.168.1.99/test-ips/check")

            assert response.status_code == 404

    def test_get_cached_test_ip_metrics(self, client):
        """Should return cached test IP metrics"""
        response_data = GatewayTestIPsResponse(
            gateway_ip="192.168.1.1", test_ips=[], last_check=None
        )

        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.get_cached_test_ip_metrics = MagicMock(return_value=response_data)

            response = client.get("/api/health/gateway/192.168.1.1/test-ips/cached")

            assert response.status_code == 200


class TestSpeedTestEndpoints:
    """Tests for speed test endpoints"""

    def test_run_speed_test(self, client):
        """Should run speed test"""
        result = SpeedTestResult(
            success=True, timestamp=datetime.utcnow(), download_mbps=100.0, upload_mbps=50.0
        )

        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.run_speed_test = AsyncMock(return_value=result)

            response = client.post("/api/health/speedtest")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_run_gateway_speed_test(self, client):
        """Should run speed test for gateway"""
        result = SpeedTestResult(
            success=True, timestamp=datetime.utcnow(), download_mbps=100.0, upload_mbps=50.0
        )

        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.run_speed_test = AsyncMock(return_value=result)

            response = client.post("/api/health/gateway/192.168.1.1/speedtest")

            assert response.status_code == 200

    def test_get_gateway_speed_test(self, client):
        """Should return last speed test for gateway"""
        result = SpeedTestResult(
            success=True, timestamp=datetime.utcnow(), download_mbps=100.0, upload_mbps=50.0
        )

        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.get_last_speed_test = MagicMock(return_value=result)

            response = client.get("/api/health/gateway/192.168.1.1/speedtest")

            assert response.status_code == 200

    def test_get_gateway_speed_test_not_found(self, client):
        """Should return 404 if no speed test results"""
        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.get_last_speed_test = MagicMock(return_value=None)

            response = client.get("/api/health/gateway/192.168.1.99/speedtest")

            assert response.status_code == 404

    def test_get_all_speed_tests(self, client):
        """Should return all speed test results"""
        result = SpeedTestResult(
            success=True, timestamp=datetime.utcnow(), download_mbps=100.0, upload_mbps=50.0
        )

        with patch("app.routers.health.health_checker") as mock_checker:
            mock_checker.get_all_speed_tests = MagicMock(return_value={"192.168.1.1": result})

            response = client.get("/api/health/speedtest/all")

            assert response.status_code == 200


class TestAgentSync:
    """Tests for POST /api/health/agent-sync - agent health data sync endpoint"""

    def test_agent_sync_success(self, client):
        """Should update cache with agent health data"""
        with patch("app.routers.health.health_checker") as mock_checker:
            # Use AsyncMock since update_from_agent_health is now async
            mock_checker.update_from_agent_health = AsyncMock(return_value=True)

            response = client.post(
                "/api/health/agent-sync",
                json={
                    "timestamp": datetime.utcnow().isoformat(),
                    "network_id": "test-network-uuid",
                    "results": [
                        {"ip": "192.168.1.10", "reachable": True, "response_time_ms": 25.0},
                        {"ip": "192.168.1.20", "reachable": False, "response_time_ms": None},
                    ],
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["results_processed"] == 2
            assert data["cache_updated"] == 2

            # Verify update_from_agent_health was called for each result
            assert mock_checker.update_from_agent_health.call_count == 2

    def test_agent_sync_empty_results(self, client):
        """Should handle empty results list gracefully"""
        response = client.post(
            "/api/health/agent-sync",
            json={
                "timestamp": datetime.utcnow().isoformat(),
                "network_id": "test-network-uuid",
                "results": [],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["results_processed"] == 0
        assert data["cache_updated"] == 0
        assert "No results" in data["message"]

    def test_agent_sync_partial_update(self, client):
        """Should handle partial updates where some devices fail"""
        with patch("app.routers.health.health_checker") as mock_checker:
            # First call succeeds, second fails - use AsyncMock
            mock_checker.update_from_agent_health = AsyncMock(side_effect=[True, False])

            response = client.post(
                "/api/health/agent-sync",
                json={
                    "timestamp": datetime.utcnow().isoformat(),
                    "network_id": "test-network-uuid",
                    "results": [
                        {"ip": "192.168.1.10", "reachable": True, "response_time_ms": 25.0},
                        {"ip": "192.168.1.20", "reachable": True, "response_time_ms": 30.0},
                    ],
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["results_processed"] == 2
            assert data["cache_updated"] == 1  # Only first one updated
