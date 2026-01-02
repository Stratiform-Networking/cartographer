"""
Shared test fixtures for assistant service unit tests.
"""

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Set test environment before imports
os.environ["OPENAI_API_KEY"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""
os.environ["METRICS_SERVICE_URL"] = "http://test-metrics:8003"
os.environ["REDIS_URL"] = "redis://localhost:6379"


@pytest.fixture
def mock_authenticated_user():
    """Create a mock authenticated user for testing"""
    from app.dependencies.auth import AuthenticatedUser, UserRole

    return AuthenticatedUser(user_id="test-user-123", username="testuser", role=UserRole.MEMBER)


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user for testing"""
    from app.dependencies.auth import AuthenticatedUser, UserRole

    return AuthenticatedUser(user_id="admin-user-123", username="adminuser", role=UserRole.ADMIN)


@pytest.fixture
def override_auth_dependency(mock_authenticated_user):
    """
    Override the require_auth dependency to return a mock user.
    Use this fixture when testing authenticated endpoints.
    """
    from app.dependencies.auth import require_auth

    async def mock_require_auth():
        return mock_authenticated_user

    return mock_require_auth


@pytest.fixture
def override_rate_limit_dependency(mock_authenticated_user):
    """
    Override the require_auth_with_rate_limit dependency.
    Use this fixture when testing rate-limited endpoints.
    """

    def create_mock_rate_limit(limit: int, endpoint: str):
        async def mock_dependency():
            return mock_authenticated_user

        return mock_dependency

    return create_mock_rate_limit


@pytest.fixture
def sample_snapshot():
    """Sample network snapshot from metrics service"""
    return {
        "success": True,
        "snapshot": {
            "snapshot_id": "test-snapshot-123",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": 1,
            "total_nodes": 3,
            "healthy_nodes": 2,
            "degraded_nodes": 1,
            "unhealthy_nodes": 0,
            "unknown_nodes": 0,
            "nodes": {
                "gateway-1": {
                    "id": "gateway-1",
                    "name": "Main Router",
                    "ip": "192.168.1.1",
                    "role": "gateway/router",
                    "status": "healthy",
                    "hostname": "router.local",
                    "connection_speed": "1GbE",
                    "ping": {"success": True, "latency_ms": 5.0, "avg_latency_ms": 5.0},
                    "uptime": {"uptime_percent_24h": 99.9},
                    "open_ports": [
                        {"port": 80, "service": "HTTP"},
                        {"port": 443, "service": "HTTPS"},
                    ],
                    "notes": "Primary gateway device",
                },
                "switch-1": {
                    "id": "switch-1",
                    "name": "Core Switch",
                    "ip": "192.168.1.2",
                    "role": "switch/ap",
                    "status": "healthy",
                    "lan_ports": {
                        "rows": 2,
                        "cols": 4,
                        "ports": [
                            {
                                "row": 1,
                                "col": 1,
                                "status": "active",
                                "type": "rj45",
                                "port_number": 1,
                                "connected_device_name": "Server",
                                "speed": "1G",
                            },
                            {"row": 1, "col": 2, "status": "unused", "type": "sfp+", "poe": "poe+"},
                            {"row": 1, "col": 3, "status": "blocked", "type": "rj45"},
                        ],
                        "start_number": 1,
                    },
                },
                "server-1": {
                    "id": "server-1",
                    "name": "File Server",
                    "ip": "192.168.1.10",
                    "role": "server",
                    "status": "degraded",
                    "notes": "Needs maintenance",
                },
                "group-1": {
                    "id": "group-1",
                    "name": "Network Group",
                    "role": "group",
                    "status": "unknown",
                },
            },
            "connections": [
                {"source_id": "gateway-1", "target_id": "switch-1", "connection_speed": "10GbE"},
                {"source_id": "switch-1", "target_id": "server-1", "connection_speed": "1GbE"},
            ],
            "gateways": [
                {
                    "gateway_ip": "192.168.1.1",
                    "test_ips": [
                        {"ip": "8.8.8.8", "label": "Google DNS", "status": "healthy"},
                        {"ip": "1.1.1.1", "label": "Cloudflare", "status": "healthy"},
                    ],
                    "last_speed_test": {
                        "success": True,
                        "download_mbps": 100.5,
                        "upload_mbps": 50.2,
                        "ping_ms": 15.0,
                        "client_isp": "Test ISP",
                        "server_sponsor": "SpeedTest.net",
                        "server_location": "New York",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                }
            ],
            "root_node_id": "root-1",
        },
    }


@pytest.fixture
def sample_summary():
    """Sample network summary"""
    return {
        "available": True,
        "total_nodes": 3,
        "health_summary": {"healthy": 2, "degraded": 1, "unhealthy": 0, "unknown": 0},
    }


@pytest.fixture
def provider_config():
    """Sample provider config"""
    from app.providers.base import ProviderConfig

    return ProviderConfig(
        api_key="test-api-key", model="test-model", temperature=0.7, max_tokens=2048
    )


@pytest.fixture
def chat_messages():
    """Sample chat messages"""
    from app.providers.base import ChatMessage

    return [
        ChatMessage(role="user", content="Hello"),
        ChatMessage(role="assistant", content="Hi there!"),
        ChatMessage(role="user", content="How is my network?"),
    ]


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client"""
    mock = AsyncMock()

    # Mock chat completions
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test response"
    mock.chat.completions.create = AsyncMock(return_value=mock_response)

    # Mock models list
    mock_model = MagicMock()
    mock_model.id = "gpt-4o"
    mock_models = MagicMock()
    mock_models.data = [mock_model]
    mock.models.list = AsyncMock(return_value=mock_models)

    return mock


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client"""
    mock = AsyncMock()

    # Mock message creation
    mock_block = MagicMock()
    mock_block.text = "Test response"
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock.messages.create = AsyncMock(return_value=mock_response)

    return mock


@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client"""
    mock = AsyncMock()

    # Mock list
    mock.list = AsyncMock(return_value={"models": [{"name": "llama3.2"}]})

    # Mock chat
    mock.chat = AsyncMock(return_value={"message": {"content": "Test response"}})

    return mock


@pytest.fixture
def metrics_context_instance():
    """Fresh MetricsContextService instance for testing"""
    from app.services.metrics_context import MetricsContextService

    service = MetricsContextService()
    yield service
    # Reset state after test
    service.reset_state()
