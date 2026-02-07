"""
Shared test fixtures for health service unit tests.
"""

import os
from collections import deque
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Set test environment variables before imports
os.environ["NOTIFICATION_SERVICE_URL"] = "http://test-notification:8005"
os.environ["HEALTH_DATA_DIR"] = "/tmp/test-health-data"


@pytest.fixture
def mock_ping_success():
    """Mock successful ping result"""
    from app.models import PingResult

    return PingResult(
        success=True,
        latency_ms=25.5,
        packet_loss_percent=0.0,
        min_latency_ms=20.0,
        max_latency_ms=30.0,
        avg_latency_ms=25.5,
        jitter_ms=2.0,
    )


@pytest.fixture
def mock_ping_failure():
    """Mock failed ping result"""
    from app.models import PingResult

    return PingResult(success=False, packet_loss_percent=100.0)


@pytest.fixture
def mock_dns_success():
    """Mock successful DNS result"""
    from app.models import DnsResult

    return DnsResult(
        success=True,
        resolved_hostname="router.local",
        reverse_dns="router.local",
        resolution_time_ms=5.0,
    )


@pytest.fixture
def mock_dns_failure():
    """Mock failed DNS result"""
    from app.models import DnsResult

    return DnsResult(success=False)


@pytest.fixture
def sample_device_metrics():
    """Sample device metrics"""
    from app.models import DeviceMetrics, HealthStatus, PingResult

    return DeviceMetrics(
        ip="192.168.1.1",
        status=HealthStatus.HEALTHY,
        last_check=datetime.now(timezone.utc),
        ping=PingResult(success=True, latency_ms=25.0, packet_loss_percent=0.0),
    )


@pytest.fixture
def health_checker_instance(tmp_path):
    """Create a fresh HealthChecker instance for testing"""
    from app.services.health_checker import HealthChecker

    # Override data directory
    with patch("app.services.health_checker.DATA_DIR", tmp_path):
        with patch(
            "app.services.health_checker.GATEWAY_TEST_IPS_FILE", tmp_path / "gateway_test_ips.json"
        ):
            with patch(
                "app.services.health_checker.SPEED_TEST_RESULTS_FILE",
                tmp_path / "speed_test_results.json",
            ):
                checker = HealthChecker()
                yield checker
                # Cleanup
                if checker._monitoring_task:
                    checker._monitoring_task.cancel()


@pytest.fixture
def mock_subprocess_ping_success():
    """Mock successful subprocess ping output"""
    return b"""PING 192.168.1.1 (192.168.1.1): 56 data bytes
64 bytes from 192.168.1.1: icmp_seq=0 ttl=64 time=20.5 ms
64 bytes from 192.168.1.1: icmp_seq=1 ttl=64 time=25.3 ms
64 bytes from 192.168.1.1: icmp_seq=2 ttl=64 time=22.1 ms

--- 192.168.1.1 ping statistics ---
3 packets transmitted, 3 packets received, 0.0% packet loss
round-trip min/avg/max/stddev = 20.5/22.6/25.3/2.0 ms
"""


@pytest.fixture
def mock_subprocess_ping_failure():
    """Mock failed subprocess ping output"""
    return b"""PING 192.168.1.1 (192.168.1.1): 56 data bytes

--- 192.168.1.1 ping statistics ---
3 packets transmitted, 0 packets received, 100.0% packet loss
"""


@pytest.fixture
def mock_subprocess_ping_success_windows():
    """Mock successful Windows ping output"""
    return b"""Pinging 192.168.1.1 with 32 bytes of data:
Reply from 192.168.1.1: bytes=32 time=10ms TTL=64
Reply from 192.168.1.1: bytes=32 time=12ms TTL=64
Reply from 192.168.1.1: bytes=32 time=11ms TTL=64

Ping statistics for 192.168.1.1:
    Packets: Sent = 3, Received = 3, Lost = 0 (0% loss),
Approximate round trip times in milli-seconds:
    Minimum = 10ms, Maximum = 12ms, Average = 11ms
"""


@pytest.fixture
def mock_subprocess_ping_failure_windows():
    """Mock failed Windows ping output"""
    return b"""Pinging 192.168.1.1 with 32 bytes of data:
Request timed out.
Request timed out.
Request timed out.

Ping statistics for 192.168.1.1:
    Packets: Sent = 3, Received = 0, Lost = 3 (100% loss),
"""


@pytest.fixture
def sample_gateway_test_ips():
    """Sample gateway test IP configuration"""
    from app.models import GatewayTestIP

    return [
        GatewayTestIP(ip="8.8.8.8", label="Google DNS"),
        GatewayTestIP(ip="1.1.1.1", label="Cloudflare DNS"),
    ]
