"""
Shared test fixtures for backend unit tests.
"""

import asyncio
import json
import os
import tempfile
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, Response

# Set test environment variables before importing app modules
os.environ["HEALTH_SERVICE_URL"] = "http://test-health:8001"
os.environ["AUTH_SERVICE_URL"] = "http://test-auth:8002"
os.environ["METRICS_SERVICE_URL"] = "http://test-metrics:8003"
os.environ["ASSISTANT_SERVICE_URL"] = "http://test-assistant:8004"
os.environ["NOTIFICATION_SERVICE_URL"] = "http://test-notification:8005"


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient for testing HTTP calls"""
    with patch("httpx.AsyncClient") as mock:
        client_instance = AsyncMock()
        mock.return_value.__aenter__.return_value = client_instance
        mock.return_value.__aexit__.return_value = None
        yield client_instance


@pytest.fixture
def sample_user_data():
    """Sample authenticated user data"""
    return {"user_id": "user-123", "username": "testuser", "role": "owner"}


@pytest.fixture
def sample_readonly_user():
    """Sample member (read-only) user data"""
    return {"user_id": "user-456", "username": "member_user", "role": "member"}


@pytest.fixture
def sample_readwrite_user():
    """Sample admin (read-write) user data"""
    return {"user_id": "user-789", "username": "admin_user", "role": "admin"}


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary data directory for file-based tests"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def sample_network_layout():
    """Sample network layout data"""
    return {
        "root": {
            "id": "192.168.1.1",
            "ip": "192.168.1.1",
            "hostname": "router",
            "type": "router",
            "children": [
                {
                    "id": "192.168.1.10",
                    "ip": "192.168.1.10",
                    "hostname": "desktop-pc",
                    "type": "device",
                    "parentId": "192.168.1.1",
                    "children": [],
                },
                {
                    "id": "192.168.1.20",
                    "ip": "192.168.1.20",
                    "hostname": "laptop",
                    "type": "device",
                    "parentId": "192.168.1.1",
                    "children": [],
                },
            ],
        }
    }


@pytest.fixture
def sample_embed_config():
    """Sample embed configuration"""
    return {
        "name": "Test Embed",
        "sensitiveMode": True,
        "showOwner": False,
        "ownerDisplayName": None,
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def mock_auth_response():
    """Mock successful auth service response"""
    return {"valid": True, "user_id": "user-123", "username": "testuser", "role": "owner"}


def create_mock_response(
    status_code: int = 200, json_data: dict = None, text: str = ""
) -> MagicMock:
    """Helper to create mock httpx Response objects"""
    response = MagicMock(spec=Response)
    response.status_code = status_code
    response.text = text or json.dumps(json_data or {})
    response.json.return_value = json_data or {}
    return response
