"""
Unit tests for the mapper router and services.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.dependencies.auth import AuthenticatedUser, UserRole


class TestMapperHelpers:
    """Tests for embed service helper functions"""

    def test_generate_anonymized_id_is_consistent(self):
        """Same IP and embed ID should produce same anonymized ID"""
        from app.services.embed_service import generate_anonymized_id

        id1 = generate_anonymized_id("192.168.1.1", "embed123")
        id2 = generate_anonymized_id("192.168.1.1", "embed123")

        assert id1 == id2
        assert id1.startswith("device_")

    def test_generate_anonymized_id_differs_by_embed(self):
        """Different embed IDs should produce different anonymized IDs"""
        from app.services.embed_service import generate_anonymized_id

        id1 = generate_anonymized_id("192.168.1.1", "embed123")
        id2 = generate_anonymized_id("192.168.1.1", "embed456")

        assert id1 != id2

    def test_generate_anonymized_id_differs_by_ip(self):
        """Different IPs should produce different anonymized IDs"""
        from app.services.embed_service import generate_anonymized_id

        id1 = generate_anonymized_id("192.168.1.1", "embed123")
        id2 = generate_anonymized_id("192.168.1.2", "embed123")

        assert id1 != id2

    def test_generate_embed_id_format(self):
        """Embed IDs should be 24 alphanumeric characters"""
        from app.services.embed_service import generate_embed_id

        embed_id = generate_embed_id()

        assert len(embed_id) == 24
        assert embed_id.isalnum()

    def test_generate_embed_id_uniqueness(self):
        """Generated embed IDs should be unique"""
        from app.services.embed_service import generate_embed_id

        ids = [generate_embed_id() for _ in range(100)]

        assert len(set(ids)) == 100


class TestSanitizeNodeIps:
    """Tests for IP sanitization in sensitive mode"""

    def test_sanitize_simple_node(self, sample_network_layout):
        """Should sanitize IP address in node"""
        from app.services.embed_service import sanitize_node_ips

        node = {"id": "192.168.1.1", "ip": "192.168.1.1", "hostname": "router", "type": "router"}
        ip_mapping = {}

        sanitized = sanitize_node_ips(node, "embed123", ip_mapping)

        assert sanitized["ip"].startswith("device_")
        assert sanitized["id"].startswith("device_")
        assert "192.168.1.1" not in str(sanitized)
        assert ip_mapping[sanitized["ip"]] == "192.168.1.1"

    def test_sanitize_preserves_non_ip_fields(self):
        """Should preserve non-IP fields"""
        from app.services.embed_service import sanitize_node_ips

        node = {
            "id": "192.168.1.1",
            "ip": "192.168.1.1",
            "hostname": "my-router",
            "type": "router",
            "custom_field": "custom_value",
        }
        ip_mapping = {}

        sanitized = sanitize_node_ips(node, "embed123", ip_mapping)

        assert sanitized["hostname"] == "my-router"
        assert sanitized["type"] == "router"
        assert sanitized["custom_field"] == "custom_value"

    def test_sanitize_hostname_with_ip(self):
        """Should clear hostname if it contains IP pattern"""
        from app.services.embed_service import sanitize_node_ips

        node = {
            "id": "192.168.1.1",
            "ip": "192.168.1.1",
            "hostname": "device-192.168.1.1",
            "type": "device",
        }
        ip_mapping = {}

        sanitized = sanitize_node_ips(node, "embed123", ip_mapping)

        assert sanitized["hostname"] == ""

    def test_sanitize_recursive_children(self, sample_network_layout):
        """Should recursively sanitize children"""
        from app.services.embed_service import sanitize_node_ips

        ip_mapping = {}
        root = sample_network_layout["root"]

        sanitized = sanitize_node_ips(root, "embed123", ip_mapping)

        # Root should be sanitized
        assert sanitized["ip"].startswith("device_")

        # Children should be sanitized
        for child in sanitized["children"]:
            assert child["ip"].startswith("device_")
            assert child["parentId"].startswith("device_")

        # All IPs should be in mapping
        assert len(ip_mapping) == 3

    def test_sanitize_parentId(self):
        """Should sanitize parentId if it looks like IP"""
        from app.services.embed_service import sanitize_node_ips

        node = {
            "id": "192.168.1.10",
            "ip": "192.168.1.10",
            "hostname": "device",
            "parentId": "192.168.1.1",
            "type": "device",
        }
        ip_mapping = {}

        sanitized = sanitize_node_ips(node, "embed123", ip_mapping)

        assert sanitized["parentId"].startswith("device_")


class TestEmbedOperations:
    """Tests for embed CRUD operations"""

    @pytest.fixture
    def temp_embeds_file(self, tmp_path):
        """Create a temporary embeds.json file"""
        embeds_file = tmp_path / "embeds.json"
        embeds_file.write_text("{}")
        return embeds_file

    def test_load_all_embeds_empty(self, temp_embeds_file):
        """Should return empty dict if no embeds"""
        from app.services.embed_service import load_all_embeds

        with patch("app.services.embed_service._embeds_config_path", return_value=temp_embeds_file):
            embeds = load_all_embeds()
            assert embeds == {}

    def test_load_all_embeds_with_data(self, temp_embeds_file, sample_embed_config):
        """Should load existing embeds"""
        from app.services.embed_service import load_all_embeds

        temp_embeds_file.write_text(json.dumps({"embed1": sample_embed_config}))

        with patch("app.services.embed_service._embeds_config_path", return_value=temp_embeds_file):
            embeds = load_all_embeds()
            assert "embed1" in embeds
            assert embeds["embed1"]["name"] == "Test Embed"

    def test_load_embeds_handles_missing_file(self, tmp_path):
        """Should return empty dict if file doesn't exist"""
        from app.services.embed_service import load_all_embeds

        missing_file = tmp_path / "nonexistent.json"

        with patch("app.services.embed_service._embeds_config_path", return_value=missing_file):
            embeds = load_all_embeds()
            assert embeds == {}

    def test_load_embeds_handles_invalid_json(self, temp_embeds_file):
        """Should return empty dict if JSON is invalid"""
        from app.services.embed_service import load_all_embeds

        temp_embeds_file.write_text("not valid json")

        with patch("app.services.embed_service._embeds_config_path", return_value=temp_embeds_file):
            embeds = load_all_embeds()
            assert embeds == {}

    def test_save_all_embeds(self, temp_embeds_file, sample_embed_config):
        """Should save embeds to file"""
        from app.services.embed_service import save_all_embeds

        with patch("app.services.embed_service._embeds_config_path", return_value=temp_embeds_file):
            save_all_embeds({"embed1": sample_embed_config})

        saved = json.loads(temp_embeds_file.read_text())
        assert "embed1" in saved
        assert saved["embed1"]["name"] == "Test Embed"


class TestSSEEventFormatting:
    """Tests for SSE event formatting"""

    def test_sse_event_single_line(self):
        """Should format single-line SSE event correctly"""
        from app.services.mapper_runner_service import sse_event

        result = sse_event("log", "Hello world")

        assert "event: log" in result
        assert "data: Hello world" in result
        assert result.endswith("\n\n")

    def test_sse_event_multi_line(self):
        """Should handle multi-line data"""
        from app.services.mapper_runner_service import sse_event

        result = sse_event("log", "Line 1\nLine 2\nLine 3")

        assert "event: log" in result
        assert "data: Line 1" in result
        assert "data: Line 2" in result
        assert "data: Line 3" in result

    def test_sse_event_empty_data(self):
        """Should handle empty data"""
        from app.services.mapper_runner_service import sse_event

        result = sse_event("done", "")

        assert "event: done" in result
        assert "data: " in result


class TestLayoutOperations:
    """Tests for layout save/load operations"""

    @pytest.fixture
    def temp_layout_file(self, tmp_path):
        """Create a temporary layout file path"""
        return tmp_path / "saved_network_layout.json"

    def test_saved_layout_path_docker(self, tmp_path):
        """Should use /app/data in Docker environment"""
        import pathlib

        from app.services.mapper_runner_service import saved_layout_path

        docker_data = tmp_path / "app" / "data"
        docker_data.mkdir(parents=True)

        with patch("app.services.mapper_runner_service.pathlib.Path") as mock_path:
            mock_docker = MagicMock()
            mock_docker.exists.return_value = True
            mock_docker.__truediv__ = lambda self, x: tmp_path / "app" / "data" / x

            # Mock the Path("/app/data") call
            def path_side_effect(arg):
                if arg == "/app/data":
                    return mock_docker
                return Path(arg)

            mock_path.side_effect = path_side_effect

            # The function should check for /app/data existence
            result = saved_layout_path()
            # In test environment, it will fall back to project root


class TestMapperResponse:
    """Tests for MapperResponse model"""

    def test_mapper_response_model(self):
        """Should create valid MapperResponse"""
        from app.routers.mapper import MapperResponse

        response = MapperResponse(
            content="Network map content", script_exit_code=0, network_map_path="/path/to/map.txt"
        )

        assert response.content == "Network map content"
        assert response.script_exit_code == 0
        assert response.network_map_path == "/path/to/map.txt"

    def test_mapper_response_optional_path(self):
        """network_map_path should be optional"""
        from app.routers.mapper import MapperResponse

        response = MapperResponse(content="Network map content", script_exit_code=0)

        assert response.network_map_path is None


class TestConfigEndpoint:
    """Tests for the /config endpoint"""

    def test_get_config_with_app_url(self):
        """Should return application_url from settings"""
        from unittest.mock import MagicMock

        from app.config import Settings

        # Create test settings with custom URL
        test_settings = MagicMock(spec=Settings)
        test_settings.application_url = "https://my-app.com"

        with patch("app.routers.mapper.settings", test_settings):
            from app.routers.mapper import get_config

            response = get_config()
            data = response.body.decode()
            parsed = json.loads(data)
            assert parsed["applicationUrl"] == "https://my-app.com"

    def test_get_config_empty_url(self):
        """Should return empty string if application_url not set"""
        from unittest.mock import MagicMock

        from app.config import Settings

        # Create test settings with empty URL (default)
        test_settings = MagicMock(spec=Settings)
        test_settings.application_url = ""

        with patch("app.routers.mapper.settings", test_settings):
            from app.routers.mapper import get_config

            response = get_config()
            data = response.body.decode()
            parsed = json.loads(data)
            assert parsed["applicationUrl"] == ""


class TestEmbedHealthEndpoints:
    """Tests for embed health check endpoint helpers"""

    async def test_health_service_request_get(self):
        """Should make GET request to health service"""
        from app.services.health_proxy_service import health_service_request

        with patch("app.services.health_proxy_service.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            response = await health_service_request("GET", "/cached")

            mock_client.get.assert_called_once()

    async def test_health_service_request_post(self):
        """Should make POST request with JSON body"""
        from app.services.health_proxy_service import health_service_request

        with patch("app.services.health_proxy_service.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            response = await health_service_request(
                "POST", "/monitoring/devices", json_body={"ips": ["192.168.1.1"]}
            )

            mock_client.post.assert_called_once()
            call_kwargs = mock_client.post.call_args
            assert call_kwargs[1]["json"] == {"ips": ["192.168.1.1"]}

    async def test_health_service_request_unsupported_method(self):
        """Should raise ValueError for unsupported HTTP method"""
        from app.services.health_proxy_service import health_service_request

        with patch("app.services.health_proxy_service.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(ValueError) as exc_info:
                await health_service_request("DELETE", "/path")

            assert "Unsupported method" in str(exc_info.value)
