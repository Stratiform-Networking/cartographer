"""
Unit tests for MetricsAggregator service.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.models import DeviceRole, HealthStatus, PoeStatus, PortStatus, PortType, SpeedTestMetrics
from app.services.metrics_aggregator import (
    SERVICE_TOKEN,
    MetricsAggregator,
    _generate_service_token,
)


class TestServiceToken:
    """Tests for service token generation"""

    def test_generate_service_token(self):
        """Should generate a valid JWT token"""
        token = _generate_service_token()
        assert token is not None
        assert len(token) > 0

    def test_service_token_exists(self):
        """Should have a module-level service token"""
        assert SERVICE_TOKEN is not None


class TestMetricsAggregatorInit:
    """Tests for MetricsAggregator initialization"""

    def test_init_defaults(self, metrics_aggregator_instance):
        """Should initialize with default values"""
        assert metrics_aggregator_instance._publish_interval == 30
        assert metrics_aggregator_instance._publishing_enabled is True
        assert metrics_aggregator_instance._publish_task is None
        assert metrics_aggregator_instance._last_snapshot is None


class TestDataFetching:
    """Tests for data fetching methods"""

    async def test_fetch_network_layout_success(
        self, metrics_aggregator_instance, sample_layout, mock_http_client
    ):
        """Should fetch network layout successfully"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"exists": True, "layout": sample_layout}
        mock_http_client.get.return_value = mock_response

        layout = await metrics_aggregator_instance._fetch_network_layout()

        assert layout is not None
        assert "root" in layout

    async def test_fetch_network_layout_not_exists(
        self, metrics_aggregator_instance, mock_http_client
    ):
        """Should return None when layout doesn't exist"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"exists": False}
        mock_http_client.get.return_value = mock_response

        layout = await metrics_aggregator_instance._fetch_network_layout()

        assert layout is None

    async def test_fetch_network_layout_auth_error(
        self, metrics_aggregator_instance, mock_http_client
    ):
        """Should handle auth error"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_http_client.get.return_value = mock_response

        layout = await metrics_aggregator_instance._fetch_network_layout()

        assert layout is None

    async def test_fetch_network_layout_connect_error(
        self, metrics_aggregator_instance, mock_http_client
    ):
        """Should handle connection error"""
        mock_http_client.get.side_effect = httpx.ConnectError("Connection refused")

        layout = await metrics_aggregator_instance._fetch_network_layout()

        assert layout is None

    async def test_fetch_network_layout_exception(
        self, metrics_aggregator_instance, mock_http_client
    ):
        """Should handle generic exception"""
        mock_http_client.get.side_effect = Exception("Unexpected error")

        layout = await metrics_aggregator_instance._fetch_network_layout()

        assert layout is None

    async def test_fetch_health_metrics_success(
        self, metrics_aggregator_instance, sample_health_metrics, mock_http_client
    ):
        """Should fetch health metrics successfully"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_health_metrics
        mock_http_client.get.return_value = mock_response

        metrics = await metrics_aggregator_instance._fetch_health_metrics()

        assert metrics is not None
        assert "192.168.1.1" in metrics

    async def test_fetch_health_metrics_error(self, metrics_aggregator_instance, mock_http_client):
        """Should return empty dict on error"""
        mock_http_client.get.side_effect = httpx.ConnectError("Connection refused")

        metrics = await metrics_aggregator_instance._fetch_health_metrics()

        assert metrics == {}

    async def test_fetch_gateway_test_ips_success(
        self, metrics_aggregator_instance, sample_gateway_test_ips, mock_http_client
    ):
        """Should fetch gateway test IPs"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_gateway_test_ips
        mock_http_client.get.return_value = mock_response

        test_ips = await metrics_aggregator_instance._fetch_gateway_test_ips()

        assert "192.168.1.1" in test_ips

    async def test_fetch_gateway_test_ips_fallback(
        self, metrics_aggregator_instance, sample_gateway_test_ips, mock_http_client
    ):
        """Should fallback to old endpoint"""
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 404

        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = sample_gateway_test_ips

        mock_http_client.get.side_effect = [mock_response_fail, mock_response_success]

        test_ips = await metrics_aggregator_instance._fetch_gateway_test_ips()

        assert "192.168.1.1" in test_ips

    async def test_fetch_speed_test_results_success(
        self, metrics_aggregator_instance, sample_speed_test_results, mock_http_client
    ):
        """Should fetch speed test results"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_speed_test_results
        mock_http_client.get.return_value = mock_response

        results = await metrics_aggregator_instance._fetch_speed_test_results()

        assert "192.168.1.1" in results

    async def test_fetch_monitoring_status_success(
        self, metrics_aggregator_instance, mock_http_client
    ):
        """Should fetch monitoring status"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"is_monitoring": True}
        mock_http_client.get.return_value = mock_response

        status = await metrics_aggregator_instance._fetch_monitoring_status()

        assert status is not None

    async def test_fetch_monitoring_status_not_found(
        self, metrics_aggregator_instance, mock_http_client
    ):
        """Should return None when not found"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_http_client.get.return_value = mock_response

        status = await metrics_aggregator_instance._fetch_monitoring_status()

        assert status is None


class TestDataTransformation:
    """Tests for data transformation methods"""

    def test_parse_device_role_valid(self, metrics_aggregator_instance):
        """Should parse valid device roles"""
        assert (
            metrics_aggregator_instance._parse_device_role("gateway/router")
            == DeviceRole.GATEWAY_ROUTER
        )
        assert metrics_aggregator_instance._parse_device_role("switch/ap") == DeviceRole.SWITCH_AP
        assert metrics_aggregator_instance._parse_device_role("server") == DeviceRole.SERVER
        assert (
            metrics_aggregator_instance._parse_device_role("GROUP") == DeviceRole.GROUP
        )  # Case insensitive

    def test_parse_device_role_none(self, metrics_aggregator_instance):
        """Should return None for None input"""
        assert metrics_aggregator_instance._parse_device_role(None) is None

    def test_parse_device_role_unknown(self, metrics_aggregator_instance):
        """Should return UNKNOWN for unknown roles"""
        assert metrics_aggregator_instance._parse_device_role("invalid") == DeviceRole.UNKNOWN

    def test_parse_health_status_valid(self, metrics_aggregator_instance):
        """Should parse valid health statuses"""
        assert metrics_aggregator_instance._parse_health_status("healthy") == HealthStatus.HEALTHY
        assert metrics_aggregator_instance._parse_health_status("DEGRADED") == HealthStatus.DEGRADED
        assert (
            metrics_aggregator_instance._parse_health_status("unhealthy") == HealthStatus.UNHEALTHY
        )

    def test_parse_health_status_none(self, metrics_aggregator_instance):
        """Should return UNKNOWN for None"""
        assert metrics_aggregator_instance._parse_health_status(None) == HealthStatus.UNKNOWN

    def test_parse_health_status_invalid(self, metrics_aggregator_instance):
        """Should return UNKNOWN for invalid status"""
        assert metrics_aggregator_instance._parse_health_status("invalid") == HealthStatus.UNKNOWN

    def test_transform_ping_metrics_success(self, metrics_aggregator_instance):
        """Should transform ping metrics"""
        ping_data = {
            "success": True,
            "latency_ms": 5.5,
            "packet_loss_percent": 0.0,
            "avg_latency_ms": 5.0,
        }

        result = metrics_aggregator_instance._transform_ping_metrics(ping_data)

        assert result is not None
        assert result.success is True
        assert result.latency_ms == 5.5

    def test_transform_ping_metrics_none(self, metrics_aggregator_instance):
        """Should return None for None input"""
        assert metrics_aggregator_instance._transform_ping_metrics(None) is None

    def test_transform_dns_metrics_success(self, metrics_aggregator_instance):
        """Should transform DNS metrics"""
        dns_data = {"success": True, "resolved_hostname": "router.local", "resolution_time_ms": 2.0}

        result = metrics_aggregator_instance._transform_dns_metrics(dns_data)

        assert result is not None
        assert result.resolved_hostname == "router.local"

    def test_transform_dns_metrics_none(self, metrics_aggregator_instance):
        """Should return None for None input"""
        assert metrics_aggregator_instance._transform_dns_metrics(None) is None

    def test_transform_check_history(self, metrics_aggregator_instance):
        """Should transform check history"""
        history = [
            {"timestamp": "2024-01-01T00:00:00Z", "success": True, "latency_ms": 5.0},
            {"timestamp": "2024-01-01T00:01:00Z", "success": False},
        ]

        result = metrics_aggregator_instance._transform_check_history(history)

        assert len(result) == 2
        assert result[0].success is True

    def test_transform_check_history_empty(self, metrics_aggregator_instance):
        """Should handle empty history"""
        result = metrics_aggregator_instance._transform_check_history([])
        assert result == []

    def test_transform_check_history_invalid(self, metrics_aggregator_instance):
        """Should handle invalid entries"""
        history = [{"timestamp": "invalid", "success": True}]  # Invalid timestamp

        result = metrics_aggregator_instance._transform_check_history(history)
        # Should skip invalid entries
        assert len(result) == 0

    def test_transform_uptime_metrics(self, metrics_aggregator_instance):
        """Should transform uptime metrics"""
        health_data = {
            "uptime_percent_24h": 99.5,
            "avg_latency_24h_ms": 5.0,
            "checks_passed_24h": 100,
            "checks_failed_24h": 1,
            "consecutive_failures": 0,
            "last_seen_online": "2024-01-01T00:00:00Z",
        }

        result = metrics_aggregator_instance._transform_uptime_metrics(health_data)

        assert result.uptime_percent_24h == 99.5
        assert result.checks_passed_24h == 100

    def test_transform_test_ip_metrics(self, metrics_aggregator_instance):
        """Should transform test IP metrics"""
        test_ip_data = {
            "ip": "8.8.8.8",
            "label": "Google DNS",
            "status": "healthy",
            "last_check": "2024-01-01T00:00:00Z",
            "ping": {"success": True, "latency_ms": 15.0},
        }

        result = metrics_aggregator_instance._transform_test_ip_metrics(test_ip_data)

        assert result.ip == "8.8.8.8"
        assert result.label == "Google DNS"
        assert result.status == HealthStatus.HEALTHY

    def test_transform_lan_ports_none(self, metrics_aggregator_instance):
        """Should return None for None input"""
        assert metrics_aggregator_instance._transform_lan_ports(None) is None

    def test_transform_lan_ports_success(self, metrics_aggregator_instance):
        """Should transform LAN ports"""
        lan_ports_data = {
            "rows": 2,
            "cols": 4,
            "labelFormat": "numeric",
            "startNumber": 1,
            "ports": [
                {"row": 1, "col": 1, "type": "rj45", "status": "active"},
                {"row": 1, "col": 2, "type": "sfp+", "status": "unused", "poe": "poe+"},
                {"row": 1, "col": 3, "type": "sfp", "status": "blocked", "poe": "poe++"},
            ],
        }

        result = metrics_aggregator_instance._transform_lan_ports(lan_ports_data)

        assert result is not None
        assert result.rows == 2
        assert result.cols == 4
        assert len(result.ports) == 3
        assert result.ports[0].type == PortType.RJ45
        assert result.ports[1].type == PortType.SFP_PLUS
        assert result.ports[1].poe == PoeStatus.POE_PLUS
        assert result.ports[2].poe == PoeStatus.POE_PLUS_PLUS

    def test_transform_lan_ports_invalid_values(self, metrics_aggregator_instance):
        """Should handle invalid port values"""
        lan_ports_data = {
            "rows": 1,
            "cols": 1,
            "ports": [
                {
                    "row": 1,
                    "col": 1,
                    "type": "invalid_type",
                    "status": "invalid_status",
                    "poe": "invalid_poe",
                }
            ],
        }

        result = metrics_aggregator_instance._transform_lan_ports(lan_ports_data)

        # Should use defaults for invalid values
        assert result.ports[0].type == PortType.RJ45
        assert result.ports[0].status == PortStatus.UNUSED


class TestSnapshotGeneration:
    """Tests for snapshot generation"""

    async def test_generate_snapshot_success(
        self,
        metrics_aggregator_instance,
        sample_layout,
        sample_health_metrics,
        sample_gateway_test_ips,
        sample_speed_test_results,
    ):
        """Should generate a complete snapshot"""
        with patch.object(
            metrics_aggregator_instance,
            "_fetch_network_layout",
            AsyncMock(return_value=sample_layout),
        ):
            with patch.object(
                metrics_aggregator_instance,
                "_fetch_health_metrics",
                AsyncMock(return_value=sample_health_metrics),
            ):
                with patch.object(
                    metrics_aggregator_instance,
                    "_fetch_gateway_test_ips",
                    AsyncMock(return_value=sample_gateway_test_ips),
                ):
                    with patch.object(
                        metrics_aggregator_instance,
                        "_fetch_speed_test_results",
                        AsyncMock(return_value=sample_speed_test_results),
                    ):
                        snapshot = await metrics_aggregator_instance.generate_snapshot()

        assert snapshot is not None
        assert snapshot.total_nodes >= 0
        assert len(snapshot.nodes) > 0
        assert snapshot.root_node_id is not None

    async def test_generate_snapshot_no_layout(self, metrics_aggregator_instance):
        """Should return None when no layout available"""
        with patch.object(
            metrics_aggregator_instance, "_fetch_network_layout", AsyncMock(return_value=None)
        ):
            with patch.object(
                metrics_aggregator_instance, "_fetch_health_metrics", AsyncMock(return_value={})
            ):
                with patch.object(
                    metrics_aggregator_instance,
                    "_fetch_gateway_test_ips",
                    AsyncMock(return_value={}),
                ):
                    with patch.object(
                        metrics_aggregator_instance,
                        "_fetch_speed_test_results",
                        AsyncMock(return_value={}),
                    ):
                        snapshot = await metrics_aggregator_instance.generate_snapshot()

        assert snapshot is None

    async def test_generate_snapshot_empty_root(self, metrics_aggregator_instance):
        """Should return None when layout has no root"""
        with patch.object(
            metrics_aggregator_instance, "_fetch_network_layout", AsyncMock(return_value={})
        ):
            with patch.object(
                metrics_aggregator_instance, "_fetch_health_metrics", AsyncMock(return_value={})
            ):
                with patch.object(
                    metrics_aggregator_instance,
                    "_fetch_gateway_test_ips",
                    AsyncMock(return_value={}),
                ):
                    with patch.object(
                        metrics_aggregator_instance,
                        "_fetch_speed_test_results",
                        AsyncMock(return_value={}),
                    ):
                        snapshot = await metrics_aggregator_instance.generate_snapshot()

        assert snapshot is None


class TestPublishing:
    """Tests for publishing methods"""

    async def test_publish_snapshot_success(self, metrics_aggregator_instance, sample_snapshot):
        """Should publish snapshot successfully"""
        metrics_aggregator_instance._last_snapshot = sample_snapshot

        with patch.object(
            metrics_aggregator_instance,
            "generate_snapshot",
            AsyncMock(return_value=sample_snapshot),
        ):
            with patch("app.services.metrics_aggregator.redis_publisher") as mock_publisher:
                mock_publisher.publish_topology_snapshot = AsyncMock(return_value=True)
                mock_publisher.store_last_snapshot = AsyncMock(return_value=True)

                result = await metrics_aggregator_instance.publish_snapshot()

        assert result is True

    async def test_publish_snapshot_no_snapshot(self, metrics_aggregator_instance):
        """Should return False when no snapshot generated"""
        with patch.object(
            metrics_aggregator_instance, "generate_snapshot", AsyncMock(return_value=None)
        ):
            result = await metrics_aggregator_instance.publish_snapshot()

        assert result is False

    def test_start_publishing(self, metrics_aggregator_instance):
        """Should start publishing task"""
        with patch("asyncio.create_task") as mock_create_task:
            mock_task = MagicMock()
            mock_task.done.return_value = False
            mock_create_task.return_value = mock_task

            metrics_aggregator_instance.start_publishing()

            mock_create_task.assert_called_once()

    def test_start_publishing_already_running(self, metrics_aggregator_instance):
        """Should not start if already running"""
        mock_task = MagicMock()
        mock_task.done.return_value = False
        metrics_aggregator_instance._publish_task = mock_task

        with patch("asyncio.create_task") as mock_create_task:
            metrics_aggregator_instance.start_publishing()

            mock_create_task.assert_not_called()

    def test_stop_publishing(self, metrics_aggregator_instance):
        """Should stop publishing task"""
        mock_task = MagicMock()
        metrics_aggregator_instance._publish_task = mock_task

        metrics_aggregator_instance.stop_publishing()

        mock_task.cancel.assert_called_once()
        assert metrics_aggregator_instance._publish_task is None


class TestSpeedTest:
    """Tests for speed test triggering"""

    async def test_trigger_speed_test_success(self, metrics_aggregator_instance, mock_http_client):
        """Should trigger speed test successfully"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "download_mbps": 100.0,
            "upload_mbps": 50.0,
            "ping_ms": 15.0,
        }
        mock_http_client.post.return_value = mock_response

        with patch("app.services.metrics_aggregator.redis_publisher") as mock_publisher:
            mock_publisher.publish_speed_test_result = AsyncMock(return_value=True)

            result = await metrics_aggregator_instance.trigger_speed_test("192.168.1.1")

        assert result is not None
        assert result.download_mbps == 100.0

    async def test_trigger_speed_test_connect_error(
        self, metrics_aggregator_instance, mock_http_client
    ):
        """Should return None on connection error"""
        mock_http_client.post.side_effect = httpx.ConnectError("Connection refused")

        result = await metrics_aggregator_instance.trigger_speed_test("192.168.1.1")

        assert result is None


class TestConfiguration:
    """Tests for configuration methods"""

    def test_set_publish_interval(self, metrics_aggregator_instance):
        """Should set publish interval"""
        metrics_aggregator_instance.set_publish_interval(60)
        assert metrics_aggregator_instance._publish_interval == 60

    def test_set_publish_interval_minimum(self, metrics_aggregator_instance):
        """Should enforce minimum interval"""
        metrics_aggregator_instance.set_publish_interval(1)
        assert metrics_aggregator_instance._publish_interval == 5  # Minimum is 5

    def test_set_publishing_enabled(self, metrics_aggregator_instance):
        """Should enable/disable publishing"""
        metrics_aggregator_instance.set_publishing_enabled(False)
        assert metrics_aggregator_instance._publishing_enabled is False

        metrics_aggregator_instance.set_publishing_enabled(True)
        assert metrics_aggregator_instance._publishing_enabled is True

    def test_get_config(self, metrics_aggregator_instance):
        """Should return current config"""
        config = metrics_aggregator_instance.get_config()

        assert "publish_interval_seconds" in config
        assert "publishing_enabled" in config
        assert "is_running" in config
        assert "last_snapshot_id" in config

    def test_get_last_snapshot(self, metrics_aggregator_instance, sample_snapshot):
        """Should return last snapshot"""
        metrics_aggregator_instance._last_snapshot = sample_snapshot

        result = metrics_aggregator_instance.get_last_snapshot()

        assert result == sample_snapshot

    def test_get_last_snapshot_none(self, metrics_aggregator_instance):
        """Should return None when no snapshot"""
        assert metrics_aggregator_instance.get_last_snapshot() is None

    def test_get_last_snapshot_with_network_id(self, metrics_aggregator_instance, sample_snapshot):
        """Should return snapshot for specific network_id"""
        metrics_aggregator_instance._snapshots["network-123"] = sample_snapshot

        result = metrics_aggregator_instance.get_last_snapshot("network-123")

        assert result == sample_snapshot

    def test_get_last_snapshot_network_id_not_found(
        self, metrics_aggregator_instance, sample_snapshot
    ):
        """Should return None for non-existent network_id"""
        metrics_aggregator_instance._snapshots["network-456"] = sample_snapshot

        result = metrics_aggregator_instance.get_last_snapshot("network-123")

        assert result is None

    def test_last_snapshot_backwards_compat_first_value(
        self, metrics_aggregator_instance, sample_snapshot
    ):
        """Should return first snapshot when None key not present"""
        metrics_aggregator_instance._snapshots["network-123"] = sample_snapshot

        # Access via backwards compatibility property
        result = metrics_aggregator_instance._last_snapshot

        assert result == sample_snapshot


class TestFetchAllNetworkIds:
    """Tests for _fetch_all_network_ids method"""

    async def test_fetch_all_network_ids_success(
        self, metrics_aggregator_instance, mock_http_client
    ):
        """Should fetch network IDs successfully"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "network-1", "name": "Network 1"},
            {"id": "network-2", "name": "Network 2"},
            {"id": None, "name": "Invalid"},  # Should be filtered out
        ]
        mock_http_client.get.return_value = mock_response

        result = await metrics_aggregator_instance._fetch_all_network_ids()

        assert result == ["network-1", "network-2"]

    async def test_fetch_all_network_ids_auth_error(
        self, metrics_aggregator_instance, mock_http_client
    ):
        """Should return empty list on auth error"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_http_client.get.return_value = mock_response

        result = await metrics_aggregator_instance._fetch_all_network_ids()

        assert result == []

    async def test_fetch_all_network_ids_other_error(
        self, metrics_aggregator_instance, mock_http_client
    ):
        """Should return empty list on other HTTP errors"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_http_client.get.return_value = mock_response

        result = await metrics_aggregator_instance._fetch_all_network_ids()

        assert result == []

    async def test_fetch_all_network_ids_connect_error(
        self, metrics_aggregator_instance, mock_http_client
    ):
        """Should return empty list on connection error"""
        mock_http_client.get.side_effect = httpx.ConnectError("Connection refused")

        result = await metrics_aggregator_instance._fetch_all_network_ids()

        assert result == []

    async def test_fetch_all_network_ids_generic_error(
        self, metrics_aggregator_instance, mock_http_client
    ):
        """Should return empty list on generic error"""
        mock_http_client.get.side_effect = Exception("Error")

        result = await metrics_aggregator_instance._fetch_all_network_ids()

        assert result == []


class TestMultiTenantLayout:
    """Tests for multi-tenant network layout fetching"""

    async def test_fetch_network_layout_with_network_id_success(
        self, metrics_aggregator_instance, sample_layout, mock_http_client
    ):
        """Should fetch layout for specific network ID"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"layout_data": sample_layout}
        mock_http_client.get.return_value = mock_response

        result = await metrics_aggregator_instance._fetch_network_layout("network-123")

        assert result == sample_layout

    async def test_fetch_network_layout_with_network_id_no_data(
        self, metrics_aggregator_instance, mock_http_client
    ):
        """Should return None when network has no layout data"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"layout_data": None}
        mock_http_client.get.return_value = mock_response

        result = await metrics_aggregator_instance._fetch_network_layout("network-123")

        assert result is None

    async def test_fetch_network_layout_with_network_id_404(
        self, metrics_aggregator_instance, mock_http_client
    ):
        """Should return None when network not found"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_http_client.get.return_value = mock_response

        result = await metrics_aggregator_instance._fetch_network_layout("network-123")

        assert result is None

    async def test_fetch_network_layout_with_network_id_500(
        self, metrics_aggregator_instance, mock_http_client
    ):
        """Should return None on server error"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_http_client.get.return_value = mock_response

        result = await metrics_aggregator_instance._fetch_network_layout("network-123")

        assert result is None


class TestGenerateAllSnapshots:
    """Tests for generate_all_snapshots method"""

    async def test_generate_all_snapshots_success(
        self, metrics_aggregator_instance, sample_snapshot
    ):
        """Should generate snapshots for all networks"""
        with patch.object(
            metrics_aggregator_instance,
            "_fetch_all_network_ids",
            AsyncMock(return_value=["network-1", "network-2"]),
        ):
            with patch.object(
                metrics_aggregator_instance,
                "generate_snapshot",
                AsyncMock(return_value=sample_snapshot),
            ):

                result = await metrics_aggregator_instance.generate_all_snapshots()

        assert len(result) == 2
        assert "network-1" in result
        assert "network-2" in result

    async def test_generate_all_snapshots_no_networks(
        self, metrics_aggregator_instance, sample_snapshot
    ):
        """Should fall back to legacy mode when no networks found"""
        with patch.object(
            metrics_aggregator_instance, "_fetch_all_network_ids", AsyncMock(return_value=[])
        ):
            with patch.object(
                metrics_aggregator_instance,
                "generate_snapshot",
                AsyncMock(return_value=sample_snapshot),
            ):

                result = await metrics_aggregator_instance.generate_all_snapshots()

        # Should return empty dict (legacy snapshot handled separately)
        assert result == {}

    async def test_generate_all_snapshots_partial_failure(
        self, metrics_aggregator_instance, sample_snapshot
    ):
        """Should continue generating even if some networks fail"""

        async def generate_snapshot_with_error(network_id):
            if network_id == "network-fail":
                raise Exception("Failed")
            return sample_snapshot

        with patch.object(
            metrics_aggregator_instance,
            "_fetch_all_network_ids",
            AsyncMock(return_value=["network-1", "network-fail", "network-2"]),
        ):
            with patch.object(
                metrics_aggregator_instance,
                "generate_snapshot",
                AsyncMock(side_effect=generate_snapshot_with_error),
            ):

                result = await metrics_aggregator_instance.generate_all_snapshots()

        # Should have 2 successful, 1 failed
        assert len(result) == 2

    async def test_generate_all_snapshots_returns_none(self, metrics_aggregator_instance):
        """Should handle when generate_snapshot returns None"""
        with patch.object(
            metrics_aggregator_instance,
            "_fetch_all_network_ids",
            AsyncMock(return_value=["network-1"]),
        ):
            with patch.object(
                metrics_aggregator_instance, "generate_snapshot", AsyncMock(return_value=None)
            ):

                result = await metrics_aggregator_instance.generate_all_snapshots()

        assert result == {}


class TestPublishAllSnapshots:
    """Tests for publish_all_snapshots method"""

    async def test_publish_all_snapshots_success(
        self, metrics_aggregator_instance, sample_snapshot
    ):
        """Should publish snapshots for all networks"""
        snapshots = {"network-1": sample_snapshot, "network-2": sample_snapshot}

        with patch.object(
            metrics_aggregator_instance, "generate_all_snapshots", AsyncMock(return_value=snapshots)
        ):
            with patch("app.services.metrics_aggregator.redis_publisher") as mock_publisher:
                mock_publisher.publish_topology_snapshot = AsyncMock(return_value=True)
                mock_publisher.store_last_snapshot = AsyncMock(return_value=True)

                result = await metrics_aggregator_instance.publish_all_snapshots()

        assert result == 2

    async def test_publish_all_snapshots_partial_failure(
        self, metrics_aggregator_instance, sample_snapshot
    ):
        """Should count only successful publishes"""
        snapshots = {"network-1": sample_snapshot, "network-2": sample_snapshot}

        call_count = 0

        async def publish_with_failure(snapshot):
            nonlocal call_count
            call_count += 1
            return call_count == 1  # First succeeds, second fails

        with patch.object(
            metrics_aggregator_instance, "generate_all_snapshots", AsyncMock(return_value=snapshots)
        ):
            with patch("app.services.metrics_aggregator.redis_publisher") as mock_publisher:
                mock_publisher.publish_topology_snapshot = AsyncMock(
                    side_effect=publish_with_failure
                )
                mock_publisher.store_last_snapshot = AsyncMock(return_value=True)

                result = await metrics_aggregator_instance.publish_all_snapshots()

        assert result == 1

    async def test_publish_all_snapshots_exception(
        self, metrics_aggregator_instance, sample_snapshot
    ):
        """Should handle exceptions during publish"""
        snapshots = {"network-1": sample_snapshot}

        with patch.object(
            metrics_aggregator_instance, "generate_all_snapshots", AsyncMock(return_value=snapshots)
        ):
            with patch("app.services.metrics_aggregator.redis_publisher") as mock_publisher:
                mock_publisher.publish_topology_snapshot = AsyncMock(side_effect=Exception("Error"))

                result = await metrics_aggregator_instance.publish_all_snapshots()

        assert result == 0
