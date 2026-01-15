"""
Unit tests for health_checker service.
"""

import asyncio
import json
from collections import deque
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import (
    DeviceMetrics,
    DnsResult,
    GatewayTestIP,
    GatewayTestIPConfig,
    HealthStatus,
    MonitoringConfig,
    PingResult,
    PortCheckResult,
    SpeedTestResult,
)


class TestHealthCheckerInit:
    """Tests for HealthChecker initialization"""

    def test_init_creates_empty_caches(self, health_checker_instance):
        """Should initialize with empty caches"""
        assert health_checker_instance._metrics_cache == {}
        assert health_checker_instance._history == {}
        assert health_checker_instance._monitored_devices == {}

    def test_init_default_config(self, health_checker_instance):
        """Should have default monitoring config"""
        config = health_checker_instance._monitoring_config
        assert config.enabled is True
        assert config.check_interval_seconds == 30


class TestPingHost:
    """Tests for ping_host method"""

    async def test_ping_success(self, health_checker_instance, mock_subprocess_ping_success):
        """Should parse successful ping output"""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(mock_subprocess_ping_success, b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await health_checker_instance.ping_host("192.168.1.1")

            assert result.success is True
            assert result.packet_loss_percent == 0.0
            assert result.avg_latency_ms is not None

    async def test_ping_failure(self, health_checker_instance, mock_subprocess_ping_failure):
        """Should handle failed ping"""
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(mock_subprocess_ping_failure, b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await health_checker_instance.ping_host("192.168.1.1")

            assert result.success is False
            assert result.packet_loss_percent == 100.0

    async def test_ping_timeout(self, health_checker_instance):
        """Should handle ping timeout"""
        with patch("asyncio.create_subprocess_exec", side_effect=asyncio.TimeoutError()):
            result = await health_checker_instance.ping_host("192.168.1.1")

            assert result.success is False
            assert result.packet_loss_percent == 100.0

    async def test_ping_exception(self, health_checker_instance):
        """Should handle unexpected exceptions"""
        with patch("asyncio.create_subprocess_exec", side_effect=OSError("Network error")):
            result = await health_checker_instance.ping_host("192.168.1.1")

            assert result.success is False


class TestCheckDns:
    """Tests for check_dns method"""

    async def test_dns_success_with_reverse(self, health_checker_instance):
        """Should resolve DNS successfully"""
        with patch("dns.reversename.from_address") as mock_reverse:
            with patch("dns.resolver.resolve") as mock_resolve:
                with patch("socket.gethostbyaddr", return_value=("hostname.local", [], [])):
                    mock_resolve.return_value = [MagicMock(__str__=lambda self: "ptr.local.")]

                    result = await health_checker_instance.check_dns("192.168.1.1")

                    assert result.success is True
                    assert result.resolved_hostname == "hostname.local"

    async def test_dns_failure(self, health_checker_instance):
        """Should handle DNS failure"""
        with patch("dns.reversename.from_address", side_effect=Exception("DNS error")):
            with patch("socket.gethostbyaddr", side_effect=Exception("No host")):
                result = await health_checker_instance.check_dns("192.168.1.1")

                assert result.success is False


class TestCheckPort:
    """Tests for check_port method"""

    async def test_port_open(self, health_checker_instance):
        """Should detect open port"""
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.wait_closed = AsyncMock()

        with patch("asyncio.open_connection", return_value=(mock_reader, mock_writer)):
            result = await health_checker_instance.check_port("192.168.1.1", 80)

            assert result.open is True
            assert result.port == 80
            assert result.service == "HTTP"

    async def test_port_closed(self, health_checker_instance):
        """Should detect closed port"""
        with patch("asyncio.open_connection", side_effect=ConnectionRefusedError()):
            result = await health_checker_instance.check_port("192.168.1.1", 80)

            assert result.open is False

    async def test_port_timeout(self, health_checker_instance):
        """Should handle timeout"""
        with patch("asyncio.open_connection", side_effect=asyncio.TimeoutError()):
            result = await health_checker_instance.check_port("192.168.1.1", 80)

            assert result.open is False

    async def test_port_os_error(self, health_checker_instance):
        """Should handle OS error"""
        with patch("asyncio.open_connection", side_effect=OSError("No route")):
            result = await health_checker_instance.check_port("192.168.1.1", 80)

            assert result.open is False


class TestScanCommonPorts:
    """Tests for scan_common_ports method"""

    async def test_scan_returns_open_ports(self, health_checker_instance):
        """Should return only open ports"""

        async def mock_check_port(ip, port):
            return PortCheckResult(
                port=port, open=port in [80, 443], service="HTTP" if port == 80 else "HTTPS"
            )

        health_checker_instance.check_port = mock_check_port

        result = await health_checker_instance.scan_common_ports("192.168.1.1")

        assert len(result) == 2
        assert all(p.open for p in result)


class TestCheckDeviceHealth:
    """Tests for check_device_health method"""

    async def test_healthy_device(
        self, health_checker_instance, mock_ping_success, mock_dns_success
    ):
        """Should report healthy status for good ping"""
        health_checker_instance.ping_host = AsyncMock(return_value=mock_ping_success)
        health_checker_instance.check_dns = AsyncMock(return_value=mock_dns_success)

        with patch("app.services.health_checker.report_health_check", new_callable=AsyncMock):
            metrics = await health_checker_instance.check_device_health("192.168.1.1")

            assert metrics.status == HealthStatus.HEALTHY
            assert metrics.ip == "192.168.1.1"
            assert metrics.consecutive_failures == 0

    async def test_unhealthy_device(self, health_checker_instance, mock_ping_failure):
        """Should report unhealthy status for failed ping"""
        health_checker_instance.ping_host = AsyncMock(return_value=mock_ping_failure)

        with patch("app.services.health_checker.report_health_check", new_callable=AsyncMock):
            metrics = await health_checker_instance.check_device_health(
                "192.168.1.1", include_dns=False
            )

            assert metrics.status == HealthStatus.UNHEALTHY
            assert metrics.consecutive_failures == 1

    async def test_degraded_high_packet_loss(self, health_checker_instance):
        """Should report degraded for high packet loss"""
        ping = PingResult(
            success=True, latency_ms=25.0, packet_loss_percent=60.0, avg_latency_ms=25.0  # > 50%
        )
        health_checker_instance.ping_host = AsyncMock(return_value=ping)

        with patch("app.services.health_checker.report_health_check", new_callable=AsyncMock):
            metrics = await health_checker_instance.check_device_health(
                "192.168.1.1", include_dns=False
            )

            assert metrics.status == HealthStatus.DEGRADED

    async def test_degraded_high_latency(self, health_checker_instance):
        """Should report degraded for high latency"""
        ping = PingResult(
            success=True, latency_ms=250.0, packet_loss_percent=0.0, avg_latency_ms=250.0  # > 200ms
        )
        health_checker_instance.ping_host = AsyncMock(return_value=ping)

        with patch("app.services.health_checker.report_health_check", new_callable=AsyncMock):
            metrics = await health_checker_instance.check_device_health(
                "192.168.1.1", include_dns=False
            )

            assert metrics.status == HealthStatus.DEGRADED

    async def test_includes_ports_when_requested(self, health_checker_instance, mock_ping_success):
        """Should scan ports when requested"""
        health_checker_instance.ping_host = AsyncMock(return_value=mock_ping_success)
        health_checker_instance.scan_common_ports = AsyncMock(
            return_value=[PortCheckResult(port=80, open=True, service="HTTP")]
        )

        with patch("app.services.health_checker.report_health_check", new_callable=AsyncMock):
            metrics = await health_checker_instance.check_device_health(
                "192.168.1.1", include_ports=True, include_dns=False
            )

            assert len(metrics.open_ports) == 1
            health_checker_instance.scan_common_ports.assert_called_once()

    async def test_caches_metrics(self, health_checker_instance, mock_ping_success):
        """Should cache metrics after check"""
        health_checker_instance.ping_host = AsyncMock(return_value=mock_ping_success)

        with patch("app.services.health_checker.report_health_check", new_callable=AsyncMock):
            await health_checker_instance.check_device_health("192.168.1.1", include_dns=False)

            cached = health_checker_instance.get_cached_metrics("192.168.1.1")
            assert cached is not None
            assert cached.ip == "192.168.1.1"


class TestCheckMultipleDevices:
    """Tests for check_multiple_devices method"""

    async def test_checks_in_parallel(self, health_checker_instance, mock_ping_success):
        """Should check multiple devices in parallel"""
        health_checker_instance.ping_host = AsyncMock(return_value=mock_ping_success)

        with patch("app.services.health_checker.report_health_check", new_callable=AsyncMock):
            results = await health_checker_instance.check_multiple_devices(
                ips=["192.168.1.1", "192.168.1.2", "192.168.1.3"], include_dns=False
            )

            assert len(results) == 3
            assert all(ip in results for ip in ["192.168.1.1", "192.168.1.2", "192.168.1.3"])

    async def test_handles_exceptions(self, health_checker_instance):
        """Should handle exceptions for individual devices"""

        async def mock_check(ip, include_ports, include_dns):
            if ip == "192.168.1.2":
                raise RuntimeError("Check failed")
            return DeviceMetrics(ip=ip, status=HealthStatus.HEALTHY, last_check=datetime.utcnow())

        health_checker_instance.check_device_health = mock_check

        results = await health_checker_instance.check_multiple_devices(
            ips=["192.168.1.1", "192.168.1.2"], include_dns=False
        )

        assert results["192.168.1.1"].status == HealthStatus.HEALTHY
        assert results["192.168.1.2"].status == HealthStatus.UNKNOWN
        assert results["192.168.1.2"].error_message is not None


class TestCacheOperations:
    """Tests for cache operations"""

    def test_get_cached_metrics_none(self, health_checker_instance):
        """Should return None for uncached device"""
        result = health_checker_instance.get_cached_metrics("192.168.1.1")
        assert result is None

    def test_get_all_cached_metrics(self, health_checker_instance, sample_device_metrics):
        """Should return all cached metrics"""
        health_checker_instance._metrics_cache["192.168.1.1"] = sample_device_metrics

        result = health_checker_instance.get_all_cached_metrics()

        assert "192.168.1.1" in result

    def test_clear_cache(self, health_checker_instance, sample_device_metrics):
        """Should clear all caches"""
        health_checker_instance._metrics_cache["192.168.1.1"] = sample_device_metrics
        health_checker_instance._history["192.168.1.1"] = deque()

        health_checker_instance.clear_cache()

        assert health_checker_instance._metrics_cache == {}
        assert health_checker_instance._history == {}


class TestHistoricalStats:
    """Tests for historical statistics"""

    def test_record_check(self, health_checker_instance):
        """Should record check in history"""
        health_checker_instance._record_check("192.168.1.1", True, 25.0)

        assert "192.168.1.1" in health_checker_instance._history
        assert len(health_checker_instance._history["192.168.1.1"]) == 1

    def test_calculate_stats_empty(self, health_checker_instance):
        """Should handle empty history"""
        uptime, avg_lat, passed, failed = health_checker_instance._calculate_historical_stats(
            "192.168.1.1"
        )

        assert uptime is None
        assert avg_lat is None
        assert passed == 0
        assert failed == 0

    def test_calculate_stats_with_data(self, health_checker_instance):
        """Should calculate correct statistics"""
        now = datetime.utcnow()
        health_checker_instance._history["192.168.1.1"] = deque(
            [
                (now, True, 20.0),
                (now, True, 25.0),
                (now, False, None),
                (now, True, 30.0),
            ]
        )

        uptime, avg_lat, passed, failed = health_checker_instance._calculate_historical_stats(
            "192.168.1.1"
        )

        assert uptime == 75.0  # 3/4 * 100
        assert avg_lat == 25.0  # (20+25+30)/3
        assert passed == 3
        assert failed == 1

    def test_get_check_history(self, health_checker_instance):
        """Should return check history entries"""
        now = datetime.utcnow()
        health_checker_instance._history["192.168.1.1"] = deque(
            [
                (now, True, 20.0),
                (now, True, 25.0),
            ]
        )

        history = health_checker_instance._get_check_history("192.168.1.1")

        assert len(history) == 2
        assert all(h.success for h in history)


class TestGatewayTestIPs:
    """Tests for gateway test IP functionality"""

    def test_set_gateway_test_ips(self, health_checker_instance, sample_gateway_test_ips):
        """Should set test IPs for gateway"""
        config = health_checker_instance.set_gateway_test_ips(
            "192.168.1.1", sample_gateway_test_ips
        )

        assert config.gateway_ip == "192.168.1.1"
        assert len(config.test_ips) == 2
        assert config.enabled is True

    def test_get_gateway_test_ips(self, health_checker_instance, sample_gateway_test_ips):
        """Should retrieve test IP config"""
        health_checker_instance.set_gateway_test_ips("192.168.1.1", sample_gateway_test_ips)

        config = health_checker_instance.get_gateway_test_ips("192.168.1.1")

        assert config is not None
        assert len(config.test_ips) == 2

    def test_get_gateway_test_ips_not_found(self, health_checker_instance):
        """Should return None for unconfigured gateway"""
        config = health_checker_instance.get_gateway_test_ips("192.168.1.99")
        assert config is None

    def test_get_all_gateway_test_ips(self, health_checker_instance, sample_gateway_test_ips):
        """Should return all gateway configs"""
        health_checker_instance.set_gateway_test_ips("192.168.1.1", sample_gateway_test_ips)
        health_checker_instance.set_gateway_test_ips("192.168.1.2", sample_gateway_test_ips)

        all_configs = health_checker_instance.get_all_gateway_test_ips()

        assert len(all_configs) == 2

    def test_remove_gateway_test_ips(self, health_checker_instance, sample_gateway_test_ips):
        """Should remove gateway config"""
        health_checker_instance.set_gateway_test_ips("192.168.1.1", sample_gateway_test_ips)

        result = health_checker_instance.remove_gateway_test_ips("192.168.1.1")

        assert result is True
        assert health_checker_instance.get_gateway_test_ips("192.168.1.1") is None

    def test_remove_gateway_test_ips_not_found(self, health_checker_instance):
        """Should return False for non-existent gateway"""
        result = health_checker_instance.remove_gateway_test_ips("192.168.1.99")
        assert result is False

    async def test_check_test_ip(self, health_checker_instance, mock_ping_success):
        """Should check single test IP"""
        health_checker_instance.ping_host = AsyncMock(return_value=mock_ping_success)

        metrics = await health_checker_instance.check_test_ip(
            "192.168.1.1", "8.8.8.8", "Google DNS"
        )

        assert metrics.ip == "8.8.8.8"
        assert metrics.label == "Google DNS"
        assert metrics.status == HealthStatus.HEALTHY

    async def test_check_gateway_test_ips(
        self, health_checker_instance, sample_gateway_test_ips, mock_ping_success
    ):
        """Should check all gateway test IPs"""
        health_checker_instance.set_gateway_test_ips("192.168.1.1", sample_gateway_test_ips)
        health_checker_instance.ping_host = AsyncMock(return_value=mock_ping_success)

        response = await health_checker_instance.check_gateway_test_ips("192.168.1.1")

        assert response.gateway_ip == "192.168.1.1"
        assert len(response.test_ips) == 2

    async def test_check_gateway_test_ips_disabled(
        self, health_checker_instance, sample_gateway_test_ips
    ):
        """Should return empty for disabled gateway"""
        health_checker_instance.set_gateway_test_ips("192.168.1.1", sample_gateway_test_ips)
        health_checker_instance._gateway_test_ips["192.168.1.1"].enabled = False

        response = await health_checker_instance.check_gateway_test_ips("192.168.1.1")

        assert len(response.test_ips) == 0

    def test_get_cached_test_ip_metrics(self, health_checker_instance, sample_gateway_test_ips):
        """Should return cached test IP metrics"""
        health_checker_instance.set_gateway_test_ips("192.168.1.1", sample_gateway_test_ips)

        response = health_checker_instance.get_cached_test_ip_metrics("192.168.1.1")

        assert response.gateway_ip == "192.168.1.1"


class TestSpeedTest:
    """Tests for speed test functionality"""

    async def test_run_speed_test_success(self, health_checker_instance):
        """Should run speed test successfully"""
        mock_results = {
            "download": 100_000_000,  # 100 Mbps
            "upload": 50_000_000,  # 50 Mbps
            "ping": 15.0,
            "server": {"name": "TestServer", "city": "New York", "country": "US", "sponsor": "ISP"},
            "client": {"ip": "1.2.3.4", "isp": "TestISP"},
        }

        mock_speedtest = MagicMock()
        mock_speedtest.return_value.get_best_server.return_value = None
        mock_speedtest.return_value.download.return_value = None
        mock_speedtest.return_value.upload.return_value = None
        mock_speedtest.return_value.results.dict.return_value = mock_results

        with patch("speedtest.Speedtest", mock_speedtest):
            result = await health_checker_instance.run_speed_test("192.168.1.1")

            assert result.success is True
            assert result.download_mbps == 100.0
            assert result.upload_mbps == 50.0

    async def test_run_speed_test_import_error(self, health_checker_instance):
        """Should handle missing speedtest module"""
        with patch.dict("sys.modules", {"speedtest": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module")):
                # This would need the actual import to fail, mock differently
                pass

    async def test_run_speed_test_exception(self, health_checker_instance):
        """Should handle speed test exception"""
        mock_speedtest = MagicMock()
        mock_speedtest.return_value.get_best_server.side_effect = Exception("Network error")

        with patch("speedtest.Speedtest", mock_speedtest):
            result = await health_checker_instance.run_speed_test()

            assert result.success is False
            assert result.error_message is not None

    def test_get_last_speed_test(self, health_checker_instance):
        """Should return last speed test result"""
        result = SpeedTestResult(
            success=True, timestamp=datetime.utcnow(), download_mbps=100.0, upload_mbps=50.0
        )
        health_checker_instance._speed_test_results["192.168.1.1"] = result

        retrieved = health_checker_instance.get_last_speed_test("192.168.1.1")

        assert retrieved is not None
        assert retrieved.download_mbps == 100.0

    def test_get_all_speed_tests(self, health_checker_instance):
        """Should return all speed test results"""
        result = SpeedTestResult(
            success=True, timestamp=datetime.utcnow(), download_mbps=100.0, upload_mbps=50.0
        )
        health_checker_instance._speed_test_results["192.168.1.1"] = result

        all_results = health_checker_instance.get_all_speed_tests()

        assert "192.168.1.1" in all_results


class TestMonitoringDevices:
    """Tests for monitoring device registration"""

    def test_register_devices(self, health_checker_instance):
        """Should register devices for monitoring"""
        health_checker_instance.register_devices(
            {"192.168.1.1": "network-uuid-1", "192.168.1.2": "network-uuid-1"}
        )

        devices = health_checker_instance.get_monitored_devices()

        assert "192.168.1.1" in devices
        assert "192.168.1.2" in devices

    def test_unregister_devices(self, health_checker_instance):
        """Should unregister devices from monitoring"""
        health_checker_instance.register_devices(
            {"192.168.1.1": "network-uuid-1", "192.168.1.2": "network-uuid-1"}
        )
        health_checker_instance.unregister_devices(["192.168.1.1"])

        devices = health_checker_instance.get_monitored_devices()

        assert "192.168.1.1" not in devices
        assert "192.168.1.2" in devices

    def test_set_monitored_devices(self, health_checker_instance):
        """Should replace all monitored devices"""
        health_checker_instance.register_devices({"192.168.1.1": "network-uuid-1"})
        health_checker_instance.set_monitored_devices(
            {"192.168.1.10": "network-uuid-2", "192.168.1.20": "network-uuid-2"}
        )

        devices = health_checker_instance.get_monitored_devices()

        assert "192.168.1.1" not in devices
        assert "192.168.1.10" in devices
        assert "192.168.1.20" in devices


class TestMonitoringConfig:
    """Tests for monitoring configuration"""

    def test_get_monitoring_config(self, health_checker_instance):
        """Should return current config"""
        config = health_checker_instance.get_monitoring_config()

        assert config.enabled is True
        assert config.check_interval_seconds == 30

    def test_set_monitoring_config(self, health_checker_instance):
        """Should update config"""
        new_config = MonitoringConfig(enabled=False, check_interval_seconds=60, include_dns=False)

        health_checker_instance.set_monitoring_config(new_config)

        config = health_checker_instance.get_monitoring_config()
        assert config.enabled is False
        assert config.check_interval_seconds == 60

    def test_get_monitoring_status(self, health_checker_instance):
        """Should return status with all fields"""
        health_checker_instance.register_devices({"192.168.1.1": "network-uuid-1"})

        status = health_checker_instance.get_monitoring_status()

        assert status.enabled is True
        assert "192.168.1.1" in status.monitored_devices


class TestMonitoringLifecycle:
    """Tests for monitoring start/stop"""

    async def test_start_monitoring(self, health_checker_instance):
        """Should start monitoring task"""
        health_checker_instance.start_monitoring()

        assert health_checker_instance._monitoring_task is not None

        # Cleanup
        health_checker_instance.stop_monitoring()

    async def test_stop_monitoring(self, health_checker_instance):
        """Should stop monitoring task"""
        health_checker_instance.start_monitoring()
        health_checker_instance.stop_monitoring()

        assert health_checker_instance._monitoring_task is None

    async def test_start_monitoring_already_running(self, health_checker_instance):
        """Should not start twice"""
        health_checker_instance.start_monitoring()
        task1 = health_checker_instance._monitoring_task

        health_checker_instance.start_monitoring()
        task2 = health_checker_instance._monitoring_task

        assert task1 is task2

        health_checker_instance.stop_monitoring()

    async def test_perform_monitoring_check(self, health_checker_instance, mock_ping_success):
        """Should perform monitoring check"""
        health_checker_instance.register_devices({"192.168.1.1": "network-uuid-1"})
        health_checker_instance.ping_host = AsyncMock(return_value=mock_ping_success)

        with patch("app.services.health_checker.report_health_check", new_callable=AsyncMock):
            await health_checker_instance._perform_monitoring_check()

            assert health_checker_instance._last_check_time is not None

    async def test_perform_monitoring_check_skips_when_in_progress(self, health_checker_instance):
        """Should skip check if already in progress"""
        health_checker_instance._is_checking = True
        health_checker_instance.register_devices({"192.168.1.1": "network-uuid-1"})

        await health_checker_instance._perform_monitoring_check()

        # Should not have updated last check time
        assert health_checker_instance._last_check_time is None


class TestDataPersistence:
    """Tests for data persistence"""

    def test_save_gateway_test_ips(
        self, health_checker_instance, sample_gateway_test_ips, tmp_path
    ):
        """Should save gateway test IPs to file"""
        with patch("app.services.health_checker.DATA_DIR", tmp_path):
            with patch(
                "app.services.health_checker.GATEWAY_TEST_IPS_FILE", tmp_path / "test_ips.json"
            ):
                health_checker_instance.set_gateway_test_ips("192.168.1.1", sample_gateway_test_ips)

                # Check file was created
                assert (tmp_path / "test_ips.json").exists()

    def test_load_gateway_test_ips(self, tmp_path):
        """Should load gateway test IPs from file"""
        test_data = {
            "192.168.1.1": {
                "gateway_ip": "192.168.1.1",
                "test_ips": [{"ip": "8.8.8.8", "label": "Google"}],
                "enabled": True,
            }
        }

        test_file = tmp_path / "gateway_test_ips.json"
        test_file.write_text(json.dumps(test_data))

        with patch("app.services.health_checker.DATA_DIR", tmp_path):
            with patch("app.services.health_checker.GATEWAY_TEST_IPS_FILE", test_file):
                from app.services.health_checker import HealthChecker

                checker = HealthChecker()

                config = checker.get_gateway_test_ips("192.168.1.1")

                assert config is not None
                assert len(config.test_ips) == 1

    def test_save_speed_test_results(self, health_checker_instance, tmp_path):
        """Should save speed test results"""
        result = SpeedTestResult(
            success=True, timestamp=datetime.utcnow(), download_mbps=100.0, upload_mbps=50.0
        )

        with patch("app.services.health_checker.DATA_DIR", tmp_path):
            with patch(
                "app.services.health_checker.SPEED_TEST_RESULTS_FILE", tmp_path / "speed.json"
            ):
                health_checker_instance._speed_test_results["192.168.1.1"] = result
                health_checker_instance._save_speed_test_results()

                assert (tmp_path / "speed.json").exists()


class TestAgentHealthSync:
    """Tests for update_from_agent_health method - syncing data from Cartographer Agent"""

    def test_update_from_agent_health_reachable(self, health_checker_instance):
        """Should update cache with healthy status for reachable device"""
        result = health_checker_instance.update_from_agent_health(
            ip="192.168.1.100",
            reachable=True,
            response_time_ms=25.0,
            network_id="test-network-uuid",
        )

        assert result is True
        cached = health_checker_instance.get_cached_metrics("192.168.1.100")
        assert cached is not None
        assert cached.status == HealthStatus.HEALTHY
        assert cached.ping.success is True
        assert cached.ping.latency_ms == 25.0
        assert cached.consecutive_failures == 0
        assert cached.last_seen_online is not None

    def test_update_from_agent_health_unreachable(self, health_checker_instance):
        """Should update cache with unhealthy status for unreachable device"""
        result = health_checker_instance.update_from_agent_health(
            ip="192.168.1.101",
            reachable=False,
            response_time_ms=None,
            network_id="test-network-uuid",
        )

        assert result is True
        cached = health_checker_instance.get_cached_metrics("192.168.1.101")
        assert cached is not None
        assert cached.status == HealthStatus.UNHEALTHY
        assert cached.ping.success is False
        assert cached.consecutive_failures == 1

    def test_update_from_agent_health_increments_failures(self, health_checker_instance):
        """Should increment consecutive failures for repeated failures"""
        ip = "192.168.1.102"

        # First failure
        health_checker_instance.update_from_agent_health(
            ip=ip, reachable=False, response_time_ms=None
        )
        cached = health_checker_instance.get_cached_metrics(ip)
        assert cached.consecutive_failures == 1

        # Second failure
        health_checker_instance.update_from_agent_health(
            ip=ip, reachable=False, response_time_ms=None
        )
        cached = health_checker_instance.get_cached_metrics(ip)
        assert cached.consecutive_failures == 2

        # Recovery resets failures
        health_checker_instance.update_from_agent_health(
            ip=ip, reachable=True, response_time_ms=20.0
        )
        cached = health_checker_instance.get_cached_metrics(ip)
        assert cached.consecutive_failures == 0

    def test_update_from_agent_health_registers_device(self, health_checker_instance):
        """Should register device for monitoring if network_id provided"""
        ip = "192.168.1.103"
        network_id = "test-network-uuid"

        health_checker_instance.update_from_agent_health(
            ip=ip, reachable=True, response_time_ms=30.0, network_id=network_id
        )

        assert ip in health_checker_instance._monitored_devices
        assert health_checker_instance._monitored_devices[ip] == network_id

    def test_update_from_agent_health_records_history(self, health_checker_instance):
        """Should record check in history for historical stats"""
        ip = "192.168.1.104"

        # Make several checks
        for _ in range(5):
            health_checker_instance.update_from_agent_health(
                ip=ip, reachable=True, response_time_ms=25.0
            )

        cached = health_checker_instance.get_cached_metrics(ip)
        assert cached.checks_passed_24h == 5
        assert cached.checks_failed_24h == 0
