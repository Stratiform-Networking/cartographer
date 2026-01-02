"""
Unit tests for MetricsContextService.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.metrics_context import MetricsContextService


class TestMetricsContextServiceInit:
    """Tests for MetricsContextService initialization"""

    def test_init_defaults(self, metrics_context_instance):
        """Should initialize with default values"""
        assert metrics_context_instance.timeout == 10.0
        assert metrics_context_instance._cached_context is None
        # Multi-tenant: _snapshot_available is now a dict, empty by default
        assert metrics_context_instance.is_snapshot_available() is False


class TestFetchNetworkSnapshot:
    """Tests for fetch_network_snapshot"""

    async def test_fetch_snapshot_success(self, metrics_context_instance, sample_snapshot):
        """Should fetch snapshot successfully"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_snapshot

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await metrics_context_instance.fetch_network_snapshot()

        assert result is not None
        assert result["snapshot_id"] == "test-snapshot-123"
        # Multi-tenant: check is_snapshot_available() for the default network
        assert metrics_context_instance.is_snapshot_available() is True

    async def test_fetch_snapshot_force_refresh(self, metrics_context_instance, sample_snapshot):
        """Should use POST when force_refresh is True"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_snapshot

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await metrics_context_instance.fetch_network_snapshot(force_refresh=True)

        assert result is not None

    async def test_fetch_snapshot_not_available(self, metrics_context_instance):
        """Should return None when snapshot not available"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": False}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await metrics_context_instance.fetch_network_snapshot()

        assert result is None
        # Multi-tenant: check is_snapshot_available() for the default network
        assert metrics_context_instance.is_snapshot_available() is False

    async def test_fetch_snapshot_connect_error(self, metrics_context_instance):
        """Should handle connection error"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )

            result = await metrics_context_instance.fetch_network_snapshot()

        assert result is None

    async def test_fetch_snapshot_generic_error(self, metrics_context_instance):
        """Should handle generic error"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Error")
            )

            result = await metrics_context_instance.fetch_network_snapshot()

        assert result is None


class TestWaitForSnapshot:
    """Tests for wait_for_snapshot"""

    async def test_wait_for_snapshot_available(self, metrics_context_instance, sample_snapshot):
        """Should return snapshot when available"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_snapshot

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await metrics_context_instance.wait_for_snapshot(max_attempts=1)

        assert result is not None

    async def test_wait_for_snapshot_retry(self, metrics_context_instance, sample_snapshot):
        """Should retry until snapshot available"""
        metrics_context_instance._check_interval_seconds = 0.01  # Fast for testing

        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return MagicMock(status_code=200, json=MagicMock(return_value={"success": False}))
            return MagicMock(status_code=200, json=MagicMock(return_value=sample_snapshot))

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = mock_get

            result = await metrics_context_instance.wait_for_snapshot(max_attempts=3)

        assert result is not None
        assert call_count >= 2

    async def test_wait_for_snapshot_timeout(self, metrics_context_instance):
        """Should return None after max attempts"""
        metrics_context_instance._check_interval_seconds = 0.01

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": False}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await metrics_context_instance.wait_for_snapshot(max_attempts=2)

        assert result is None


class TestFetchNetworkSummary:
    """Tests for fetch_network_summary"""

    async def test_fetch_summary_success(self, metrics_context_instance, sample_summary):
        """Should fetch summary"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_summary

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await metrics_context_instance.fetch_network_summary()

        assert result is not None
        assert result["total_nodes"] == 3

    async def test_fetch_summary_error(self, metrics_context_instance):
        """Should return None on error"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Error")
            )

            result = await metrics_context_instance.fetch_network_summary()

        assert result is None


class TestBuildContextString:
    """Tests for build_context_string"""

    async def test_build_context_with_snapshot(self, metrics_context_instance, sample_snapshot):
        """Should build context from snapshot"""
        with patch.object(
            metrics_context_instance,
            "fetch_network_snapshot",
            AsyncMock(return_value=sample_snapshot["snapshot"]),
        ):
            context, summary = await metrics_context_instance.build_context_string(
                wait_for_data=False
            )

        assert "NETWORK TOPOLOGY INFORMATION" in context
        assert summary["total_nodes"] == 3

    async def test_build_context_cached(self, metrics_context_instance):
        """Should use cached context"""
        # Set up cache using new multi-tenant structure
        # _context_cache[network_id] = (context, summary, timestamp)
        metrics_context_instance._context_cache[None] = (
            "Cached context",
            {"total_nodes": 1},
            datetime.utcnow(),
        )

        context, summary = await metrics_context_instance.build_context_string()

        assert context == "Cached context"

    async def test_build_context_force_refresh(self, metrics_context_instance, sample_snapshot):
        """Should bypass cache when force_refresh is True"""
        # Set up cache using new multi-tenant structure
        metrics_context_instance._context_cache[None] = (
            "Cached context",
            {"total_nodes": 1},
            datetime.utcnow(),
        )

        with patch.object(
            metrics_context_instance,
            "fetch_network_snapshot",
            AsyncMock(return_value=sample_snapshot["snapshot"]),
        ):
            context, summary = await metrics_context_instance.build_context_string(
                force_refresh=True
            )

        assert context != "Cached context"

    async def test_build_context_loading(self, metrics_context_instance):
        """Should return loading context when waiting for data"""
        with patch.object(
            metrics_context_instance, "fetch_network_snapshot", AsyncMock(return_value=None)
        ):
            with patch.object(
                metrics_context_instance, "wait_for_snapshot", AsyncMock(return_value=None)
            ):
                context, summary = await metrics_context_instance.build_context_string()

        assert "loading" in context.lower() or "unavailable" in context.lower()

    async def test_build_context_fallback(self, metrics_context_instance):
        """Should return fallback context when unavailable"""
        # Multi-tenant: set snapshot was previously available for default network
        metrics_context_instance._snapshot_available[None] = True

        with patch.object(
            metrics_context_instance, "fetch_network_snapshot", AsyncMock(return_value=None)
        ):
            context, summary = await metrics_context_instance.build_context_string(
                wait_for_data=False
            )

        assert "unavailable" in context.lower()


class TestFormatMethods:
    """Tests for formatting methods"""

    def test_format_node_info(self, metrics_context_instance, sample_snapshot):
        """Should format node information"""
        node = sample_snapshot["snapshot"]["nodes"]["gateway-1"]

        result = metrics_context_instance._format_node_info(node)

        assert "Main Router" in result
        assert "192.168.1.1" in result
        assert "gateway/router" in result

    def test_format_node_info_with_ports(self, metrics_context_instance, sample_snapshot):
        """Should format node with open ports"""
        node = sample_snapshot["snapshot"]["nodes"]["gateway-1"]

        result = metrics_context_instance._format_node_info(node)

        assert "80" in result
        assert "HTTP" in result

    def test_format_node_info_with_lan_ports(self, metrics_context_instance, sample_snapshot):
        """Should format node with LAN ports"""
        node = sample_snapshot["snapshot"]["nodes"]["switch-1"]

        result = metrics_context_instance._format_node_info(node)

        assert "LAN Ports" in result

    def test_format_lan_ports(self, metrics_context_instance, sample_snapshot):
        """Should format LAN ports configuration"""
        lan_ports = sample_snapshot["snapshot"]["nodes"]["switch-1"]["lan_ports"]

        result = metrics_context_instance._format_lan_ports(lan_ports)

        assert "total" in result
        assert "active" in result

    def test_format_lan_ports_empty(self, metrics_context_instance):
        """Should handle empty ports"""
        result = metrics_context_instance._format_lan_ports({"rows": 0, "cols": 0, "ports": []})
        assert result == ""

    def test_get_port_label(self, metrics_context_instance):
        """Should get port label"""
        port = {"row": 1, "col": 2}
        lan_ports = {"rows": 2, "cols": 4, "start_number": 1, "ports": []}

        result = metrics_context_instance._get_port_label(port, lan_ports)

        assert result == "2"

    def test_get_port_label_with_number(self, metrics_context_instance):
        """Should use port_number if available"""
        port = {"row": 1, "col": 1, "port_number": 5}
        lan_ports = {"rows": 2, "cols": 4, "ports": []}

        result = metrics_context_instance._get_port_label(port, lan_ports)

        assert result == "5"

    def test_format_gateway_info(self, metrics_context_instance, sample_snapshot):
        """Should format gateway information"""
        gateway = sample_snapshot["snapshot"]["gateways"][0]
        nodes = sample_snapshot["snapshot"]["nodes"]

        result = metrics_context_instance._format_gateway_info(gateway, nodes)

        assert "192.168.1.1" in result
        assert "External Connectivity" in result
        assert "Speed Test" in result

    def test_format_gateway_info_failed_speed_test(self, metrics_context_instance):
        """Should handle failed speed test"""
        gateway = {
            "gateway_ip": "192.168.1.1",
            "test_ips": [],
            "last_speed_test": {"success": False, "error_message": "Test failed"},
        }

        result = metrics_context_instance._format_gateway_info(gateway, {})

        assert "Failed" in result


class TestCacheAndStatus:
    """Tests for cache and status methods"""

    def test_is_snapshot_available(self, metrics_context_instance):
        """Should return snapshot availability"""
        assert metrics_context_instance.is_snapshot_available() is False

        # Multi-tenant: set availability for default network
        metrics_context_instance._snapshot_available[None] = True
        assert metrics_context_instance.is_snapshot_available() is True

    def test_should_recheck_no_previous_check(self, metrics_context_instance):
        """Should recheck when no previous check"""
        assert metrics_context_instance.should_recheck() is True

    def test_should_recheck_snapshot_available(self, metrics_context_instance):
        """Should not recheck when snapshot available"""
        # Multi-tenant: set availability for default network
        metrics_context_instance._snapshot_available[None] = True
        assert metrics_context_instance.should_recheck() is False

    def test_should_recheck_interval(self, metrics_context_instance):
        """Should recheck after interval"""
        metrics_context_instance._last_check_time = datetime.utcnow() - timedelta(seconds=10)
        metrics_context_instance._check_interval_seconds = 5

        assert metrics_context_instance.should_recheck() is True

    def test_clear_cache(self, metrics_context_instance):
        """Should clear cache"""
        # Multi-tenant: set cache using new structure
        metrics_context_instance._context_cache[None] = ("test", {"test": True}, datetime.utcnow())

        metrics_context_instance.clear_cache()

        # Backwards-compatible properties should now return None
        assert metrics_context_instance._cached_context is None
        assert metrics_context_instance._cached_summary is None

    def test_reset_state(self, metrics_context_instance):
        """Should reset all state"""
        # Multi-tenant: set cache and availability using new structures
        metrics_context_instance._context_cache[None] = ("test", {"test": True}, datetime.utcnow())
        metrics_context_instance._snapshot_available[None] = True

        metrics_context_instance.reset_state()

        # Backwards-compatible properties should now return None/False
        assert metrics_context_instance._cached_context is None
        assert metrics_context_instance.is_snapshot_available() is False

    def test_get_status(self, metrics_context_instance):
        """Should return status dict"""
        status = metrics_context_instance.get_status()

        assert "snapshot_available" in status
        assert "cached" in status
        assert "last_check" in status


class TestBuildLoadingAndFallback:
    """Tests for loading and fallback context builders"""

    def test_build_loading_context(self, metrics_context_instance):
        """Should build loading context"""
        context, summary = metrics_context_instance._build_loading_context()

        assert "loading" in context.lower()
        assert summary["loading"] is True

    def test_build_fallback_context(self, metrics_context_instance):
        """Should build fallback context"""
        context, summary = metrics_context_instance._build_fallback_context()

        assert "unavailable" in context.lower()
        assert summary["unavailable"] is True
