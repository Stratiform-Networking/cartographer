"""
Shared test fixtures for metrics service unit tests.
"""

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Set test environment before imports
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["REDIS_DB"] = "0"
os.environ["HEALTH_SERVICE_URL"] = "http://test-health:8001"
os.environ["BACKEND_SERVICE_URL"] = "http://test-backend:8000"
os.environ["JWT_SECRET"] = "test-secret-key"


@pytest.fixture
def sample_layout():
    """Sample network layout from backend"""
    return {
        "root": {
            "id": "root-1",
            "name": "Network",
            "role": "group",
            "children": [
                {
                    "id": "gateway-1",
                    "name": "Main Router",
                    "ip": "192.168.1.1",
                    "role": "gateway/router",
                    "connectionSpeed": "1GbE",
                    "notes": "Primary gateway",
                    "children": [
                        {
                            "id": "switch-1",
                            "name": "Core Switch",
                            "ip": "192.168.1.2",
                            "role": "switch/ap",
                            "connectionSpeed": "10GbE",
                            "lanPorts": {
                                "rows": 2,
                                "cols": 4,
                                "ports": [
                                    {"row": 1, "col": 1, "status": "active", "type": "rj45"},
                                    {"row": 1, "col": 2, "status": "unused", "poe": "poe+"},
                                ],
                            },
                            "children": [],
                        },
                        {
                            "id": "server-1",
                            "name": "File Server",
                            "ip": "192.168.1.10",
                            "role": "server",
                            "connectionSpeed": "1GbE",
                            "children": [],
                        },
                    ],
                }
            ],
        }
    }


@pytest.fixture
def sample_health_metrics():
    """Sample health metrics from health service"""
    return {
        "192.168.1.1": {
            "ip": "192.168.1.1",
            "status": "healthy",
            "last_check": datetime.now(timezone.utc).isoformat(),
            "ping": {
                "success": True,
                "latency_ms": 5.2,
                "packet_loss_percent": 0.0,
                "avg_latency_ms": 5.0,
                "min_latency_ms": 4.0,
                "max_latency_ms": 6.0,
                "jitter_ms": 0.5,
            },
            "dns": {
                "success": True,
                "resolved_hostname": "router.local",
                "reverse_dns": "router.local",
                "resolution_time_ms": 2.0,
            },
            "open_ports": [
                {"port": 80, "open": True, "service": "HTTP"},
                {"port": 443, "open": True, "service": "HTTPS"},
            ],
            "uptime_percent_24h": 99.9,
            "avg_latency_24h_ms": 5.0,
            "checks_passed_24h": 100,
            "checks_failed_24h": 1,
            "consecutive_failures": 0,
            "check_history": [
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "success": True,
                    "latency_ms": 5.0,
                }
            ],
        },
        "192.168.1.2": {
            "ip": "192.168.1.2",
            "status": "healthy",
            "last_check": datetime.now(timezone.utc).isoformat(),
            "ping": {"success": True, "latency_ms": 2.0, "packet_loss_percent": 0.0},
        },
        "192.168.1.10": {
            "ip": "192.168.1.10",
            "status": "degraded",
            "last_check": datetime.now(timezone.utc).isoformat(),
            "ping": {"success": True, "latency_ms": 250.0, "packet_loss_percent": 10.0},
        },
    }


@pytest.fixture
def sample_gateway_test_ips():
    """Sample gateway test IP metrics"""
    return {
        "192.168.1.1": {
            "gateway_ip": "192.168.1.1",
            "test_ips": [
                {
                    "ip": "8.8.8.8",
                    "label": "Google DNS",
                    "status": "healthy",
                    "last_check": datetime.now(timezone.utc).isoformat(),
                    "ping": {"success": True, "latency_ms": 15.0, "packet_loss_percent": 0.0},
                },
                {
                    "ip": "1.1.1.1",
                    "label": "Cloudflare",
                    "status": "healthy",
                    "last_check": datetime.now(timezone.utc).isoformat(),
                    "ping": {"success": True, "latency_ms": 12.0, "packet_loss_percent": 0.0},
                },
            ],
            "last_check": datetime.now(timezone.utc).isoformat(),
        }
    }


@pytest.fixture
def sample_speed_test_results():
    """Sample speed test results"""
    return {
        "192.168.1.1": {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "download_mbps": 100.5,
            "upload_mbps": 50.2,
            "ping_ms": 15.0,
            "server_name": "TestServer",
            "server_location": "New York, US",
            "client_isp": "TestISP",
        }
    }


@pytest.fixture
def sample_snapshot():
    """Sample network topology snapshot"""
    from app.models import (
        DeviceRole,
        HealthStatus,
        NetworkTopologySnapshot,
        NodeConnection,
        NodeMetrics,
    )

    now = datetime.now(timezone.utc)
    return NetworkTopologySnapshot(
        snapshot_id="test-snapshot-123",
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
                name="Main Router",
                ip="192.168.1.1",
                role=DeviceRole.GATEWAY_ROUTER,
                status=HealthStatus.HEALTHY,
            ),
            "switch-1": NodeMetrics(
                id="switch-1",
                name="Core Switch",
                ip="192.168.1.2",
                role=DeviceRole.SWITCH_AP,
                status=HealthStatus.HEALTHY,
            ),
            "server-1": NodeMetrics(
                id="server-1",
                name="File Server",
                ip="192.168.1.10",
                role=DeviceRole.SERVER,
                status=HealthStatus.DEGRADED,
            ),
        },
        connections=[
            NodeConnection(source_id="gateway-1", target_id="switch-1", connection_speed="10GbE"),
            NodeConnection(source_id="gateway-1", target_id="server-1", connection_speed="1GbE"),
        ],
        gateways=[],
        root_node_id="root-1",
    )


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    mock = AsyncMock()
    mock.ping = AsyncMock(return_value=True)
    mock.publish = AsyncMock(return_value=1)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.close = AsyncMock()
    mock.pubsub = MagicMock(return_value=AsyncMock())
    return mock


@pytest.fixture
def metrics_aggregator_instance():
    """Create a fresh MetricsAggregator instance for testing"""
    from app.services.metrics_aggregator import MetricsAggregator

    aggregator = MetricsAggregator()
    yield aggregator
    # Cleanup
    if aggregator._publish_task:
        aggregator._publish_task.cancel()


@pytest.fixture
def redis_publisher_instance():
    """Create a fresh RedisPublisher instance for testing"""
    from app.services.redis_publisher import RedisPublisher

    publisher = RedisPublisher()
    yield publisher
