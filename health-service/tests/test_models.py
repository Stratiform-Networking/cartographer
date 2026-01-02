"""
Unit tests for health service models.
"""

from datetime import datetime

import pytest

from app.models import (
    BatchHealthResponse,
    CheckHistoryEntry,
    DeviceMetrics,
    DeviceToMonitor,
    DnsResult,
    GatewayTestIP,
    GatewayTestIPConfig,
    GatewayTestIPMetrics,
    GatewayTestIPsResponse,
    HealthCheckRequest,
    HealthStatus,
    MonitoringConfig,
    MonitoringStatus,
    PingResult,
    PortCheckResult,
    RegisterDevicesRequest,
    SetGatewayTestIPsRequest,
    SpeedTestResult,
)


class TestHealthStatus:
    """Tests for HealthStatus enum"""

    def test_health_status_values(self):
        """Should have expected enum values"""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"


class TestPingResult:
    """Tests for PingResult model"""

    def test_ping_result_success(self):
        """Should create successful ping result"""
        result = PingResult(
            success=True,
            latency_ms=25.5,
            packet_loss_percent=0.0,
            min_latency_ms=20.0,
            max_latency_ms=30.0,
            avg_latency_ms=25.5,
            jitter_ms=2.0,
        )

        assert result.success is True
        assert result.latency_ms == 25.5
        assert result.packet_loss_percent == 0.0

    def test_ping_result_failure(self):
        """Should create failed ping result with defaults"""
        result = PingResult(success=False, packet_loss_percent=100.0)

        assert result.success is False
        assert result.latency_ms is None
        assert result.packet_loss_percent == 100.0


class TestDnsResult:
    """Tests for DnsResult model"""

    def test_dns_result_success(self):
        """Should create successful DNS result"""
        result = DnsResult(
            success=True,
            resolved_hostname="router.local",
            reverse_dns="router.local",
            resolution_time_ms=5.0,
        )

        assert result.success is True
        assert result.resolved_hostname == "router.local"

    def test_dns_result_failure(self):
        """Should create failed DNS result"""
        result = DnsResult(success=False)

        assert result.success is False
        assert result.resolved_hostname is None


class TestPortCheckResult:
    """Tests for PortCheckResult model"""

    def test_port_check_open(self):
        """Should create open port result"""
        result = PortCheckResult(port=80, open=True, service="HTTP", response_time_ms=5.0)

        assert result.port == 80
        assert result.open is True
        assert result.service == "HTTP"

    def test_port_check_closed(self):
        """Should create closed port result"""
        result = PortCheckResult(port=22, open=False, service="SSH")

        assert result.open is False


class TestDeviceMetrics:
    """Tests for DeviceMetrics model"""

    def test_device_metrics_healthy(self):
        """Should create healthy device metrics"""
        now = datetime.utcnow()
        metrics = DeviceMetrics(
            ip="192.168.1.1",
            status=HealthStatus.HEALTHY,
            last_check=now,
            ping=PingResult(success=True, latency_ms=25.0, packet_loss_percent=0.0),
        )

        assert metrics.ip == "192.168.1.1"
        assert metrics.status == HealthStatus.HEALTHY
        assert metrics.consecutive_failures == 0

    def test_device_metrics_with_history(self):
        """Should include check history"""
        now = datetime.utcnow()
        history = [
            CheckHistoryEntry(timestamp=now, success=True, latency_ms=25.0),
            CheckHistoryEntry(timestamp=now, success=True, latency_ms=30.0),
        ]

        metrics = DeviceMetrics(
            ip="192.168.1.1", status=HealthStatus.HEALTHY, last_check=now, check_history=history
        )

        assert len(metrics.check_history) == 2


class TestHealthCheckRequest:
    """Tests for HealthCheckRequest model"""

    def test_health_check_request(self):
        """Should create valid request"""
        request = HealthCheckRequest(
            ips=["192.168.1.1", "192.168.1.2"], include_ports=True, include_dns=True
        )

        assert len(request.ips) == 2
        assert request.include_ports is True

    def test_health_check_request_defaults(self):
        """Should use defaults"""
        request = HealthCheckRequest(ips=["192.168.1.1"])

        assert request.include_ports is False
        assert request.include_dns is True


class TestMonitoringConfig:
    """Tests for MonitoringConfig model"""

    def test_monitoring_config_defaults(self):
        """Should have sensible defaults"""
        config = MonitoringConfig()

        assert config.enabled is True
        assert config.check_interval_seconds == 30
        assert config.include_dns is True

    def test_monitoring_config_custom(self):
        """Should accept custom values"""
        config = MonitoringConfig(enabled=False, check_interval_seconds=60, include_dns=False)

        assert config.enabled is False
        assert config.check_interval_seconds == 60


class TestGatewayTestIPModels:
    """Tests for gateway test IP models"""

    def test_gateway_test_ip(self):
        """Should create test IP with label"""
        tip = GatewayTestIP(ip="8.8.8.8", label="Google DNS")

        assert tip.ip == "8.8.8.8"
        assert tip.label == "Google DNS"

    def test_gateway_test_ip_config(self):
        """Should create config with test IPs"""
        config = GatewayTestIPConfig(
            gateway_ip="192.168.1.1",
            test_ips=[
                GatewayTestIP(ip="8.8.8.8", label="Google"),
                GatewayTestIP(ip="1.1.1.1", label="Cloudflare"),
            ],
            enabled=True,
        )

        assert config.gateway_ip == "192.168.1.1"
        assert len(config.test_ips) == 2

    def test_gateway_test_ip_metrics(self):
        """Should create test IP metrics"""
        now = datetime.utcnow()
        metrics = GatewayTestIPMetrics(
            ip="8.8.8.8",
            label="Google DNS",
            status=HealthStatus.HEALTHY,
            last_check=now,
            ping=PingResult(success=True, latency_ms=15.0, packet_loss_percent=0.0),
        )

        assert metrics.status == HealthStatus.HEALTHY


class TestSpeedTestResult:
    """Tests for SpeedTestResult model"""

    def test_speed_test_success(self):
        """Should create successful speed test result"""
        result = SpeedTestResult(
            success=True,
            timestamp=datetime.utcnow(),
            download_mbps=100.5,
            upload_mbps=50.2,
            ping_ms=15.0,
            server_name="TestServer",
            server_location="New York, US",
            client_isp="TestISP",
        )

        assert result.success is True
        assert result.download_mbps == 100.5
        assert result.upload_mbps == 50.2

    def test_speed_test_failure(self):
        """Should create failed speed test result"""
        result = SpeedTestResult(
            success=False, timestamp=datetime.utcnow(), error_message="Connection timeout"
        )

        assert result.success is False
        assert result.error_message == "Connection timeout"
