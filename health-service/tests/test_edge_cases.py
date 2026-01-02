"""
Edge case and integration tests for additional coverage.
"""

import asyncio
import json
from collections import deque
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import (
    CheckHistoryEntry,
    DeviceMetrics,
    GatewayTestIP,
    GatewayTestIPMetrics,
    HealthStatus,
    PingResult,
    SpeedTestResult,
)


class TestPingEdgeCases:
    """Edge cases for ping functionality"""

    async def test_ping_with_partial_packet_loss(self, health_checker_instance):
        """Should calculate stats for partial packet loss"""
        output = b"""PING 192.168.1.1 (192.168.1.1): 56 data bytes
64 bytes from 192.168.1.1: icmp_seq=0 ttl=64 time=20.5 ms
64 bytes from 192.168.1.1: icmp_seq=2 ttl=64 time=22.1 ms

--- 192.168.1.1 ping statistics ---
3 packets transmitted, 2 packets received, 33.3% packet loss
round-trip min/avg/max/stddev = 20.5/21.3/22.1/0.8 ms
"""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(output, b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await health_checker_instance.ping_host("192.168.1.1")

            assert result.success is True
            assert result.packet_loss_percent > 0

    async def test_ping_with_no_latencies_parsed(self, health_checker_instance):
        """Should handle when no latencies can be parsed"""
        output = b"""PING 192.168.1.1 (192.168.1.1): 56 data bytes

--- 192.168.1.1 ping statistics ---
3 packets transmitted, 0 packets received
"""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(output, b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await health_checker_instance.ping_host("192.168.1.1")

            assert result.success is False

    async def test_ping_calculates_jitter(
        self, health_checker_instance, mock_subprocess_ping_success
    ):
        """Should calculate jitter from latency variance"""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(mock_subprocess_ping_success, b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await health_checker_instance.ping_host("192.168.1.1")

            assert result.jitter_ms is not None


class TestDnsEdgeCases:
    """Edge cases for DNS functionality"""

    async def test_dns_reverse_only(self, health_checker_instance):
        """Should succeed with only reverse DNS"""
        with patch("dns.reversename.from_address") as mock_reverse:
            with patch("dns.resolver.resolve") as mock_resolve:
                mock_resolve.return_value = [MagicMock(__str__=lambda self: "ptr.local.")]
                with patch("socket.gethostbyaddr", side_effect=Exception("No host")):
                    result = await health_checker_instance.check_dns("192.168.1.1")

                    assert result.success is True
                    assert result.reverse_dns == "ptr.local"

    async def test_dns_socket_only(self, health_checker_instance):
        """Should succeed with only socket resolution"""
        with patch("dns.reversename.from_address", side_effect=Exception("DNS error")):
            with patch("socket.gethostbyaddr", return_value=("hostname.local", [], [])):
                result = await health_checker_instance.check_dns("192.168.1.1")

                assert result.success is True
                assert result.resolved_hostname == "hostname.local"


class TestHistoricalStatsEdgeCases:
    """Edge cases for historical statistics"""

    def test_old_history_excluded(self, health_checker_instance):
        """Should exclude history older than 24 hours"""
        old_time = datetime.utcnow() - timedelta(hours=25)
        recent_time = datetime.utcnow()

        health_checker_instance._history["192.168.1.1"] = deque(
            [
                (old_time, True, 20.0),
                (recent_time, True, 25.0),
                (recent_time, False, None),
            ]
        )

        uptime, avg_lat, passed, failed = health_checker_instance._calculate_historical_stats(
            "192.168.1.1"
        )

        # Only 2 recent entries counted
        assert passed == 1
        assert failed == 1
        assert avg_lat == 25.0

    def test_history_with_no_latencies(self, health_checker_instance):
        """Should handle history with no latency data"""
        now = datetime.utcnow()
        health_checker_instance._history["192.168.1.1"] = deque(
            [
                (now, False, None),
                (now, False, None),
            ]
        )

        uptime, avg_lat, passed, failed = health_checker_instance._calculate_historical_stats(
            "192.168.1.1"
        )

        assert avg_lat is None
        assert failed == 2


class TestCheckDeviceHealthEdgeCases:
    """Edge cases for device health checking"""

    async def test_consecutive_failures_incremented(
        self, health_checker_instance, mock_ping_failure
    ):
        """Should increment consecutive failures"""
        health_checker_instance.ping_host = AsyncMock(return_value=mock_ping_failure)

        with patch("app.services.health_checker.report_health_check", new_callable=AsyncMock):
            # First failure
            metrics1 = await health_checker_instance.check_device_health(
                "192.168.1.1", include_dns=False
            )
            assert metrics1.consecutive_failures == 1

            # Second failure
            metrics2 = await health_checker_instance.check_device_health(
                "192.168.1.1", include_dns=False
            )
            assert metrics2.consecutive_failures == 2

    async def test_consecutive_failures_reset_on_success(
        self, health_checker_instance, mock_ping_success, mock_ping_failure
    ):
        """Should reset consecutive failures on success"""
        with patch("app.services.health_checker.report_health_check", new_callable=AsyncMock):
            # First failure
            health_checker_instance.ping_host = AsyncMock(return_value=mock_ping_failure)
            await health_checker_instance.check_device_health("192.168.1.1", include_dns=False)

            # Then success
            health_checker_instance.ping_host = AsyncMock(return_value=mock_ping_success)
            metrics = await health_checker_instance.check_device_health(
                "192.168.1.1", include_dns=False
            )

            assert metrics.consecutive_failures == 0

    async def test_last_seen_online_updated(self, health_checker_instance, mock_ping_success):
        """Should update last seen online on success"""
        health_checker_instance.ping_host = AsyncMock(return_value=mock_ping_success)

        with patch("app.services.health_checker.report_health_check", new_callable=AsyncMock):
            metrics = await health_checker_instance.check_device_health(
                "192.168.1.1", include_dns=False
            )

            assert metrics.last_seen_online is not None


class TestTestIPEdgeCases:
    """Edge cases for gateway test IP functionality"""

    def test_record_test_ip_check_creates_history(self, health_checker_instance):
        """Should create history for new test IP"""
        health_checker_instance._record_test_ip_check("192.168.1.1", "8.8.8.8", True, 15.0)

        key = health_checker_instance._get_test_ip_history_key("192.168.1.1", "8.8.8.8")
        assert key in health_checker_instance._test_ip_history
        assert len(health_checker_instance._test_ip_history[key]) == 1

    def test_calculate_test_ip_stats_empty(self, health_checker_instance):
        """Should handle empty test IP history"""
        uptime, avg_lat, passed, failed = (
            health_checker_instance._calculate_test_ip_historical_stats("192.168.1.1", "8.8.8.8")
        )

        assert uptime is None
        assert passed == 0

    async def test_check_test_ip_increments_failures(
        self, health_checker_instance, mock_ping_failure
    ):
        """Should track consecutive failures for test IPs"""
        health_checker_instance.ping_host = AsyncMock(return_value=mock_ping_failure)

        metrics1 = await health_checker_instance.check_test_ip("192.168.1.1", "8.8.8.8", "Google")
        assert metrics1.consecutive_failures == 1

        metrics2 = await health_checker_instance.check_test_ip("192.168.1.1", "8.8.8.8", "Google")
        assert metrics2.consecutive_failures == 2

    async def test_check_gateway_test_ips_handles_exception(
        self, health_checker_instance, sample_gateway_test_ips
    ):
        """Should handle exception during test IP check"""
        health_checker_instance.set_gateway_test_ips("192.168.1.1", sample_gateway_test_ips)
        health_checker_instance.ping_host = AsyncMock(side_effect=Exception("Network error"))

        response = await health_checker_instance.check_gateway_test_ips("192.168.1.1")

        # Should have entries with UNKNOWN status
        assert len(response.test_ips) == 2
        assert all(tip.status == HealthStatus.UNKNOWN for tip in response.test_ips)


class TestSpeedTestEdgeCases:
    """Edge cases for speed test functionality"""

    async def test_speed_test_stores_result_for_gateway(self, health_checker_instance, tmp_path):
        """Should store result when gateway_ip provided"""
        mock_results = {
            "download": 100_000_000,
            "upload": 50_000_000,
            "ping": 15.0,
            "server": {},
            "client": {},
        }

        mock_speedtest = MagicMock()
        mock_speedtest.return_value.get_best_server.return_value = None
        mock_speedtest.return_value.download.return_value = None
        mock_speedtest.return_value.upload.return_value = None
        mock_speedtest.return_value.results.dict.return_value = mock_results

        with patch("speedtest.Speedtest", mock_speedtest):
            with patch("app.services.health_checker.DATA_DIR", tmp_path):
                with patch(
                    "app.services.health_checker.SPEED_TEST_RESULTS_FILE", tmp_path / "speed.json"
                ):
                    result = await health_checker_instance.run_speed_test("192.168.1.1")

                    assert result.success is True
                    assert "192.168.1.1" in health_checker_instance._speed_test_results


class TestMonitoringLoopEdgeCases:
    """Edge cases for monitoring loop"""

    async def test_perform_monitoring_check_empty_devices(self, health_checker_instance):
        """Should do nothing when no devices registered"""
        # Clear all devices
        health_checker_instance._monitored_devices = {}
        health_checker_instance._gateway_test_ips = {}

        await health_checker_instance._perform_monitoring_check()

        # Should complete without error
        assert True

    async def test_perform_monitoring_check_with_gateway_test_ips(
        self, health_checker_instance, sample_gateway_test_ips, mock_ping_success
    ):
        """Should check gateway test IPs during monitoring"""
        health_checker_instance.set_gateway_test_ips("192.168.1.1", sample_gateway_test_ips)
        health_checker_instance.ping_host = AsyncMock(return_value=mock_ping_success)

        with patch("app.services.health_checker.report_health_check", new_callable=AsyncMock):
            await health_checker_instance._perform_monitoring_check()

            # Should have cached metrics for test IPs
            cached = health_checker_instance.get_cached_test_ip_metrics("192.168.1.1")
            assert len(cached.test_ips) == 2

    async def test_set_monitoring_config_restarts_task(self, health_checker_instance):
        """Should restart monitoring when config changes"""
        # Start monitoring in async context
        health_checker_instance.start_monitoring()
        old_task = health_checker_instance._monitoring_task

        new_config = health_checker_instance._monitoring_config.model_copy(
            update={"check_interval_seconds": 60}
        )
        health_checker_instance.set_monitoring_config(new_config)

        # Give some time for task recreation
        await asyncio.sleep(0.01)

        # Task should have been recreated or old one cancelled
        new_task = health_checker_instance._monitoring_task
        assert old_task.cancelled() or old_task.done() or new_task != old_task

        health_checker_instance.stop_monitoring()


class TestDataPersistenceEdgeCases:
    """Edge cases for data persistence"""

    def test_load_gateway_test_ips_invalid_json(self, tmp_path):
        """Should handle invalid JSON file"""
        test_file = tmp_path / "gateway_test_ips.json"
        test_file.write_text("invalid json{}")

        with patch("app.services.health_checker.DATA_DIR", tmp_path):
            with patch("app.services.health_checker.GATEWAY_TEST_IPS_FILE", test_file):
                from app.services.health_checker import HealthChecker

                checker = HealthChecker()

                # Should not crash, just log error
                assert checker._gateway_test_ips == {}

    def test_load_speed_test_with_iso_timestamp(self, tmp_path):
        """Should handle ISO timestamp strings"""
        test_data = {
            "192.168.1.1": {
                "success": True,
                "timestamp": "2024-01-15T12:00:00Z",
                "download_mbps": 100.0,
                "upload_mbps": 50.0,
            }
        }

        test_file = tmp_path / "speed_test_results.json"
        test_file.write_text(json.dumps(test_data))

        with patch("app.services.health_checker.DATA_DIR", tmp_path):
            with patch("app.services.health_checker.SPEED_TEST_RESULTS_FILE", test_file):
                from app.services.health_checker import HealthChecker

                checker = HealthChecker()

                result = checker.get_last_speed_test("192.168.1.1")
                assert result is not None
                assert result.download_mbps == 100.0

    def test_save_gateway_test_ips_creates_directory(self, tmp_path):
        """Should create directory if it doesn't exist"""
        new_dir = tmp_path / "new_dir"

        with patch("app.services.health_checker.DATA_DIR", new_dir):
            with patch("app.services.health_checker.GATEWAY_TEST_IPS_FILE", new_dir / "test.json"):
                from app.services.health_checker import HealthChecker

                checker = HealthChecker()
                checker.set_gateway_test_ips("192.168.1.1", [GatewayTestIP(ip="8.8.8.8")])

                assert new_dir.exists()


class TestPortCheckEdgeCases:
    """Edge cases for port checking"""

    async def test_check_port_generic_exception(self, health_checker_instance):
        """Should handle generic exceptions"""
        with patch("asyncio.open_connection", side_effect=RuntimeError("Unknown")):
            result = await health_checker_instance.check_port("192.168.1.1", 80)

            assert result.open is False


class TestTestIPDegradedStatus:
    """Tests for test IP degraded status conditions"""

    async def test_test_ip_degraded_high_packet_loss(self, health_checker_instance):
        """Should report degraded for high packet loss on test IP"""
        ping = PingResult(
            success=True, latency_ms=25.0, packet_loss_percent=60.0, avg_latency_ms=25.0  # > 50%
        )
        health_checker_instance.ping_host = AsyncMock(return_value=ping)

        metrics = await health_checker_instance.check_test_ip("192.168.1.1", "8.8.8.8", "Test")

        assert metrics.status == HealthStatus.DEGRADED

    async def test_test_ip_degraded_high_latency(self, health_checker_instance):
        """Should report degraded for high latency on test IP"""
        ping = PingResult(
            success=True, latency_ms=250.0, packet_loss_percent=0.0, avg_latency_ms=250.0  # > 200ms
        )
        health_checker_instance.ping_host = AsyncMock(return_value=ping)

        metrics = await health_checker_instance.check_test_ip("192.168.1.1", "8.8.8.8", "Test")

        assert metrics.status == HealthStatus.DEGRADED


class TestPersistenceErrors:
    """Tests for persistence error handling"""

    def test_save_gateway_test_ips_error(self, health_checker_instance, tmp_path):
        """Should handle save errors gracefully"""
        # Make the directory read-only to cause write error
        readonly_file = tmp_path / "readonly.json"

        with patch("app.services.health_checker.GATEWAY_TEST_IPS_FILE", readonly_file):
            with patch("builtins.open", side_effect=PermissionError("Read only")):
                # Should not crash, just log error
                health_checker_instance._save_gateway_test_ips()

    def test_save_speed_test_results_error(self, health_checker_instance):
        """Should handle save errors gracefully"""
        with patch("builtins.open", side_effect=PermissionError("Read only")):
            # Should not crash, just log error
            health_checker_instance._save_speed_test_results()

    def test_load_speed_test_results_error(self, tmp_path):
        """Should handle load errors gracefully"""
        test_file = tmp_path / "bad_speed.json"
        test_file.write_text("not valid json {{{")

        with patch("app.services.health_checker.DATA_DIR", tmp_path):
            with patch("app.services.health_checker.SPEED_TEST_RESULTS_FILE", test_file):
                from app.services.health_checker import HealthChecker

                checker = HealthChecker()

                # Should not crash
                assert checker._speed_test_results == {}


class TestMonitoringLoopErrors:
    """Tests for monitoring loop error handling"""

    async def test_monitoring_check_exception(self, health_checker_instance):
        """Should handle exceptions during monitoring check"""
        health_checker_instance.register_devices({"192.168.1.1": "network-uuid-1"})

        # Make check_multiple_devices raise an exception
        async def failing_check(*args, **kwargs):
            raise RuntimeError("Network error")

        health_checker_instance.check_multiple_devices = failing_check

        # Should not crash
        await health_checker_instance._perform_monitoring_check()

        # Check time should still be updated
        assert health_checker_instance._last_check_time is not None


class TestSinglePingLatency:
    """Test for single ping latency jitter calculation"""

    async def test_ping_single_latency_zero_jitter(self, health_checker_instance):
        """Should have zero jitter with single latency"""
        output = b"""PING 192.168.1.1 (192.168.1.1): 56 data bytes
64 bytes from 192.168.1.1: icmp_seq=0 ttl=64 time=20.5 ms

--- 192.168.1.1 ping statistics ---
1 packets transmitted, 1 packets received, 0.0% packet loss
"""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(output, b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await health_checker_instance.ping_host("192.168.1.1", count=1)

            assert result.success is True
            assert result.jitter_ms == 0.0


class TestCheckHistoryEntry:
    """Tests for CheckHistoryEntry model"""

    def test_get_check_history_empty(self, health_checker_instance):
        """Should return empty list for no history"""
        history = health_checker_instance._get_check_history("192.168.1.99")
        assert history == []

    def test_get_test_ip_check_history_empty(self, health_checker_instance):
        """Should return empty list for no test IP history"""
        history = health_checker_instance._get_test_ip_check_history("192.168.1.1", "8.8.8.8")
        assert history == []

    def test_get_test_ip_check_history_with_hours(self, health_checker_instance):
        """Should respect hours parameter"""
        now = datetime.utcnow()
        old_time = now - timedelta(hours=12)

        key = health_checker_instance._get_test_ip_history_key("192.168.1.1", "8.8.8.8")
        health_checker_instance._test_ip_history[key] = deque(
            [
                (old_time, True, 20.0),
                (now, True, 25.0),
            ]
        )

        # 6 hour window should only get recent
        history = health_checker_instance._get_test_ip_check_history(
            "192.168.1.1", "8.8.8.8", hours=6
        )
        assert len(history) == 1

        # 24 hour window should get both
        history_24h = health_checker_instance._get_test_ip_check_history(
            "192.168.1.1", "8.8.8.8", hours=24
        )
        assert len(history_24h) == 2
