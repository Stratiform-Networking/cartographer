"""
Integration tests for mapper router endpoints using TestClient.
"""

import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

# Skip bash script tests on Windows
skip_on_windows = pytest.mark.skipif(
    sys.platform == "win32", reason="Bash scripts cannot run on Windows"
)

from app.dependencies.auth import AuthenticatedUser, UserRole
from app.routers.mapper import router

# ==================== Fixtures ====================


@pytest.fixture
def owner_user():
    return AuthenticatedUser(user_id="owner-123", username="owner", role=UserRole.OWNER)


@pytest.fixture
def readwrite_user():
    return AuthenticatedUser(user_id="rw-123", username="admin", role=UserRole.ADMIN)


@pytest.fixture
def readonly_user():
    return AuthenticatedUser(user_id="ro-123", username="member", role=UserRole.MEMBER)


@pytest.fixture
def temp_project_root(tmp_path):
    """Create temporary project structure"""
    # Create script
    script = tmp_path / "lan_mapper.sh"
    script.write_text("#!/bin/bash\necho 'Router: 192.168.1.1' > network_map.txt\necho 'Done'")
    script.chmod(0o755)

    # Create network map
    (tmp_path / "network_map.txt").write_text("Router: 192.168.1.1\nDevice: 192.168.1.10")

    return tmp_path


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def sample_layout():
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
                    "hostname": "desktop",
                    "type": "device",
                    "parentId": "192.168.1.1",
                    "children": [],
                }
            ],
        }
    }


# ==================== Run Mapper Endpoint Tests ====================


class TestRunMapperEndpoint:
    """Tests for /run-mapper endpoint"""

    def test_run_mapper_script_not_found(self, readwrite_user):
        """Should return 404 if script doesn't exist"""
        from app.routers.mapper import run_mapper
        from app.services import mapper_runner_service

        with patch.object(mapper_runner_service, "script_path") as mock_path:
            mock_path.return_value = Path("/nonexistent/lan_mapper.sh")

            with pytest.raises(Exception) as exc_info:
                run_mapper(user=readwrite_user)

            assert (
                "404" in str(exc_info.value.status_code)
                or "not found" in str(exc_info.value.detail).lower()
            )

    @skip_on_windows
    def test_run_mapper_executes_script(self, temp_project_root, readwrite_user):
        """Should execute script and return results"""
        from app.routers.mapper import run_mapper
        from app.services import mapper_runner_service

        with patch.object(mapper_runner_service, "project_root", return_value=temp_project_root):
            with patch.object(
                mapper_runner_service,
                "script_path",
                return_value=temp_project_root / "lan_mapper.sh",
            ):
                with patch.object(
                    mapper_runner_service,
                    "network_map_candidates",
                    return_value=[temp_project_root / "network_map.txt"],
                ):
                    response = run_mapper(user=readwrite_user)

                    assert response.content is not None
                    assert response.script_exit_code == 0

    def test_run_mapper_timeout(self, temp_project_root, readwrite_user):
        """Should handle script timeout"""
        import subprocess

        from app.routers.mapper import run_mapper
        from app.services import mapper_runner_service

        with patch.object(mapper_runner_service, "project_root", return_value=temp_project_root):
            with patch.object(
                mapper_runner_service,
                "script_path",
                return_value=temp_project_root / "lan_mapper.sh",
            ):
                with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("script", 300)):
                    with pytest.raises(Exception) as exc_info:
                        run_mapper(user=readwrite_user)

                    assert (
                        "504" in str(exc_info.value.status_code)
                        or "timeout" in str(exc_info.value.detail).lower()
                    )


class TestRunMapperStreamEndpoint:
    """Tests for /run-mapper/stream endpoint"""

    def test_run_mapper_stream_script_not_found(self, readwrite_user):
        """Should return 404 if script doesn't exist"""
        from app.routers.mapper import run_mapper_stream
        from app.services import mapper_runner_service

        with patch.object(mapper_runner_service, "script_path") as mock_path:
            mock_path.return_value = Path("/nonexistent/lan_mapper.sh")

            with pytest.raises(Exception) as exc_info:
                run_mapper_stream(user=readwrite_user)

            assert (
                "404" in str(exc_info.value.status_code)
                or "not found" in str(exc_info.value.detail).lower()
            )


# ==================== Download Map Endpoint Tests ====================


class TestDownloadMapEndpoint:
    """Tests for /download-map endpoint"""

    def test_download_map_file_found(self, temp_project_root, owner_user):
        """Should return file when exists"""
        from fastapi.responses import FileResponse

        from app.routers.mapper import download_map
        from app.services import mapper_runner_service

        with patch.object(
            mapper_runner_service,
            "find_network_map",
            return_value=temp_project_root / "network_map.txt",
        ):
            response = download_map(user=owner_user)

            assert isinstance(response, FileResponse)

    def test_download_map_file_not_found(self, owner_user):
        """Should return 404 when file doesn't exist"""
        from app.routers.mapper import download_map
        from app.services import mapper_runner_service

        with patch.object(mapper_runner_service, "find_network_map", return_value=None):
            with pytest.raises(Exception) as exc_info:
                download_map(user=owner_user)

            assert "404" in str(exc_info.value.status_code)


# ==================== Layout Save/Load Tests ====================


class TestLayoutEndpoints:
    """Tests for save-layout and load-layout endpoints"""

    def test_save_layout_success(self, temp_data_dir, readwrite_user, sample_layout):
        """Should save layout to file"""
        from app.routers.mapper import save_layout
        from app.services import mapper_runner_service

        layout_file = temp_data_dir / "saved_network_layout.json"

        with patch.object(mapper_runner_service, "save_layout", return_value=str(layout_file)):
            response = save_layout(layout=sample_layout, user=readwrite_user)

            data = json.loads(response.body.decode())
            assert data["success"] is True

    def test_load_layout_not_exists(self, temp_data_dir, owner_user):
        """Should return exists=False when no layout saved"""
        from app.routers.mapper import load_layout
        from app.services import mapper_runner_service

        with patch.object(mapper_runner_service, "load_layout", return_value=None):
            response = load_layout(user=owner_user)

            data = json.loads(response.body.decode())
            assert data["exists"] is False
            assert data["layout"] is None

    def test_load_layout_success(self, temp_data_dir, owner_user, sample_layout):
        """Should load layout from file"""
        from app.routers.mapper import load_layout
        from app.services import mapper_runner_service

        with patch.object(mapper_runner_service, "load_layout", return_value=sample_layout):
            response = load_layout(user=owner_user)

            data = json.loads(response.body.decode())
            assert data["exists"] is True
            assert data["layout"]["root"]["ip"] == "192.168.1.1"


# ==================== Embed CRUD Tests ====================


class TestEmbedEndpoints:
    """Tests for embed CRUD endpoints"""

    @pytest.fixture
    def embeds_file(self, temp_data_dir):
        embeds_path = temp_data_dir / "embeds.json"
        embeds_path.write_text("{}")
        return embeds_path

    def test_list_embeds_empty(self, embeds_file, owner_user):
        """Should return empty list when no embeds"""
        from app.routers.mapper import list_embeds
        from app.services import embed_service

        with patch.object(embed_service, "_embeds_config_path", return_value=embeds_file):
            response = list_embeds(user=owner_user)

            data = json.loads(response.body.decode())
            assert data["embeds"] == []

    def test_create_embed(self, embeds_file, readwrite_user):
        """Should create new embed"""
        from app.routers.mapper import create_embed
        from app.services import embed_service

        with patch.object(embed_service, "_embeds_config_path", return_value=embeds_file):
            response = create_embed(
                config={"name": "Test Embed", "sensitiveMode": True}, user=readwrite_user
            )

            data = json.loads(response.body.decode())
            assert data["success"] is True
            assert "id" in data
            assert len(data["id"]) == 24

    def test_list_embeds_with_data(self, embeds_file, owner_user):
        """Should list existing embeds"""
        from app.routers.mapper import list_embeds
        from app.services import embed_service

        embeds_file.write_text(
            json.dumps(
                {
                    "embed123": {
                        "name": "Test",
                        "sensitiveMode": False,
                        "createdAt": "2024-01-01T00:00:00Z",
                        "updatedAt": "2024-01-01T00:00:00Z",
                    }
                }
            )
        )

        with patch.object(embed_service, "_embeds_config_path", return_value=embeds_file):
            response = list_embeds(user=owner_user, network_id=None)

            data = json.loads(response.body.decode())
            assert len(data["embeds"]) == 1
            assert data["embeds"][0]["id"] == "embed123"

    def test_update_embed(self, embeds_file, readwrite_user):
        """Should update existing embed"""
        from app.routers.mapper import update_embed
        from app.services import embed_service

        embeds_file.write_text(
            json.dumps(
                {
                    "embed123": {
                        "name": "Old Name",
                        "sensitiveMode": False,
                        "createdAt": "2024-01-01T00:00:00Z",
                        "updatedAt": "2024-01-01T00:00:00Z",
                    }
                }
            )
        )

        with patch.object(embed_service, "_embeds_config_path", return_value=embeds_file):
            response = update_embed(
                embed_id="embed123", config={"name": "New Name"}, user=readwrite_user
            )

            data = json.loads(response.body.decode())
            assert data["success"] is True
            assert data["embed"]["name"] == "New Name"

    def test_update_embed_not_found(self, embeds_file, readwrite_user):
        """Should return 404 for non-existent embed"""
        from app.routers.mapper import update_embed
        from app.services import embed_service

        with patch.object(embed_service, "_embeds_config_path", return_value=embeds_file):
            with pytest.raises(Exception) as exc_info:
                update_embed(embed_id="nonexistent", config={"name": "Test"}, user=readwrite_user)

            assert "404" in str(exc_info.value.status_code)

    def test_delete_embed(self, embeds_file, owner_user):
        """Should delete embed (owner only)"""
        from app.routers.mapper import delete_embed
        from app.services import embed_service

        embeds_file.write_text(
            json.dumps(
                {
                    "embed123": {
                        "name": "Test",
                        "sensitiveMode": False,
                        "createdAt": "2024-01-01T00:00:00Z",
                        "updatedAt": "2024-01-01T00:00:00Z",
                    }
                }
            )
        )

        with patch.object(embed_service, "_embeds_config_path", return_value=embeds_file):
            response = delete_embed(embed_id="embed123", user=owner_user)

            data = json.loads(response.body.decode())
            assert data["success"] is True

            # Verify deletion
            saved = json.loads(embeds_file.read_text())
            assert "embed123" not in saved

    def test_delete_embed_not_found(self, embeds_file, owner_user):
        """Should return 404 for non-existent embed"""
        from app.routers.mapper import delete_embed
        from app.services import embed_service

        with patch.object(embed_service, "_embeds_config_path", return_value=embeds_file):
            with pytest.raises(Exception) as exc_info:
                delete_embed(embed_id="nonexistent", user=owner_user)

            assert "404" in str(exc_info.value.status_code)


# ==================== Embed Data Endpoint Tests ====================


class TestEmbedDataEndpoint:
    """Tests for /embed-data/{embed_id} endpoint"""

    @pytest.fixture
    def setup_embed(self, temp_data_dir, sample_layout):
        """Setup embed config and layout files"""
        embeds_file = temp_data_dir / "embeds.json"
        layout_file = temp_data_dir / "saved_network_layout.json"

        embeds_file.write_text(
            json.dumps(
                {
                    "embed123": {
                        "name": "Test Embed",
                        "sensitiveMode": False,
                        "showOwner": True,
                        "ownerDisplayName": "Admin",
                        "createdAt": "2024-01-01T00:00:00Z",
                    },
                    "sensitive456": {
                        "name": "Sensitive Embed",
                        "sensitiveMode": True,
                        "showOwner": False,
                        "createdAt": "2024-01-01T00:00:00Z",
                    },
                }
            )
        )

        layout_file.write_text(json.dumps(sample_layout))

        return {"embeds_file": embeds_file, "layout_file": layout_file, "layout": sample_layout}

    async def test_get_embed_data_not_found(self, temp_data_dir):
        """Should return 404 for non-existent embed"""
        from app.routers.mapper import get_embed_data
        from app.services import embed_service

        embeds_file = temp_data_dir / "embeds.json"
        embeds_file.write_text("{}")

        mock_db = AsyncMock()

        with patch.object(embed_service, "_embeds_config_path", return_value=embeds_file):
            with pytest.raises(HTTPException) as exc_info:
                await get_embed_data(embed_id="nonexistent", db=mock_db)

            assert exc_info.value.status_code == 404

    async def test_get_embed_data_no_layout(self, setup_embed):
        """Should return exists=False if no layout saved"""
        from app.routers.mapper import get_embed_data
        from app.services import embed_service, mapper_runner_service

        # Remove layout file
        setup_embed["layout_file"].unlink()

        mock_db = AsyncMock()

        with patch.object(
            embed_service, "_embeds_config_path", return_value=setup_embed["embeds_file"]
        ):
            with patch.object(mapper_runner_service, "load_layout", return_value=None):
                response = await get_embed_data(embed_id="embed123", db=mock_db)

                data = json.loads(response.body.decode())
                assert data["exists"] is False

    async def test_get_embed_data_non_sensitive(self, setup_embed):
        """Should return raw IPs when not in sensitive mode"""
        from app.routers.mapper import get_embed_data
        from app.services import embed_service, mapper_runner_service

        mock_db = AsyncMock()

        with patch.object(
            embed_service, "_embeds_config_path", return_value=setup_embed["embeds_file"]
        ):
            with patch.object(
                mapper_runner_service, "load_layout", return_value=setup_embed["layout"]
            ):
                response = await get_embed_data(embed_id="embed123", db=mock_db)

                data = json.loads(response.body.decode())
                assert data["exists"] is True
                assert data["root"]["ip"] == "192.168.1.1"  # Raw IP preserved
                assert data["showOwner"] is True
                assert data["ownerDisplayName"] == "Admin"

    async def test_get_embed_data_sensitive(self, setup_embed):
        """Should anonymize IPs in sensitive mode"""
        from app.routers.mapper import get_embed_data
        from app.services import embed_service, mapper_runner_service

        mock_db = AsyncMock()

        with patch.object(
            embed_service, "_embeds_config_path", return_value=setup_embed["embeds_file"]
        ):
            with patch.object(
                mapper_runner_service, "load_layout", return_value=setup_embed["layout"]
            ):
                response = await get_embed_data(embed_id="sensitive456", db=mock_db)

                data = json.loads(response.body.decode())
                assert data["exists"] is True
                assert data["sensitiveMode"] is True
                # IPs should be anonymized
                assert data["root"]["ip"].startswith("device_")
                assert "192.168" not in str(data["root"])


# ==================== Embed Health Endpoints Tests ====================


class TestEmbedHealthEndpoints:
    """Tests for embed health endpoints"""

    @pytest.fixture
    def setup_embed_health(self, temp_data_dir, sample_layout):
        """Setup embed with IP mapping"""
        embeds_file = temp_data_dir / "embeds.json"
        layout_file = temp_data_dir / "saved_network_layout.json"

        embeds_file.write_text(
            json.dumps(
                {
                    "embed123": {
                        "name": "Test",
                        "sensitiveMode": True,
                        "createdAt": "2024-01-01T00:00:00Z",
                    }
                }
            )
        )
        layout_file.write_text(json.dumps(sample_layout))

        return {"embeds_file": embeds_file, "layout_file": layout_file}

    async def test_register_embed_health_devices_not_found(self, temp_data_dir):
        """Should return 404 for non-existent embed"""
        from app.routers.mapper import register_embed_health_devices
        from app.services import embed_service

        embeds_file = temp_data_dir / "embeds.json"
        embeds_file.write_text("{}")

        with patch.object(embed_service, "_embeds_config_path", return_value=embeds_file):
            with pytest.raises(Exception) as exc_info:
                await register_embed_health_devices(
                    embed_id="nonexistent", request={"device_ids": ["device_abc"]}
                )

            assert "404" in str(exc_info.value.status_code)

    async def test_trigger_embed_health_check_not_found(self, temp_data_dir):
        """Should return 404 for non-existent embed"""
        from app.routers.mapper import trigger_embed_health_check
        from app.services import embed_service

        embeds_file = temp_data_dir / "embeds.json"
        embeds_file.write_text("{}")

        with patch.object(embed_service, "_embeds_config_path", return_value=embeds_file):
            with pytest.raises(Exception) as exc_info:
                await trigger_embed_health_check(embed_id="nonexistent")

            assert "404" in str(exc_info.value.status_code)

    async def test_get_embed_cached_health_not_found(self, temp_data_dir):
        """Should return 404 for non-existent embed"""
        from app.routers.mapper import get_embed_cached_health
        from app.services import embed_service

        embeds_file = temp_data_dir / "embeds.json"
        embeds_file.write_text("{}")

        with patch.object(embed_service, "_embeds_config_path", return_value=embeds_file):
            with pytest.raises(Exception) as exc_info:
                await get_embed_cached_health(embed_id="nonexistent")

            assert "404" in str(exc_info.value.status_code)

    async def test_register_embed_health_devices_empty(self, setup_embed_health):
        """Should handle empty device IDs"""
        from app.routers.mapper import register_embed_health_devices
        from app.services import embed_service

        with patch.object(
            embed_service, "_embeds_config_path", return_value=setup_embed_health["embeds_file"]
        ):
            response = await register_embed_health_devices(
                embed_id="embed123", request={"device_ids": []}
            )

            data = json.loads(response.body.decode())
            assert data["count"] == 0

    async def test_trigger_embed_health_check_success(self, setup_embed_health):
        """Should trigger health check"""
        from app.routers.mapper import trigger_embed_health_check
        from app.services import embed_service, health_proxy_service

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            embed_service, "_embeds_config_path", return_value=setup_embed_health["embeds_file"]
        ):
            with patch.object(
                health_proxy_service, "trigger_health_check", new_callable=AsyncMock
            ) as mock_health:
                mock_health.return_value = mock_response

                response = await trigger_embed_health_check(embed_id="embed123")

                data = json.loads(response.body.decode())
                assert "message" in data

    async def test_get_embed_cached_health_non_sensitive(self, setup_embed_health):
        """Should return metrics as-is when not in sensitive mode"""
        from app.routers.mapper import get_embed_cached_health
        from app.services import embed_service, health_proxy_service

        # Change to non-sensitive
        embeds = json.loads(setup_embed_health["embeds_file"].read_text())
        embeds["embed123"]["sensitiveMode"] = False
        setup_embed_health["embeds_file"].write_text(json.dumps(embeds))

        with patch.object(
            embed_service, "_embeds_config_path", return_value=setup_embed_health["embeds_file"]
        ):
            with patch.object(
                health_proxy_service, "get_cached_metrics", new_callable=AsyncMock
            ) as mock_health:
                mock_health.return_value = {"192.168.1.1": {"status": "healthy"}}

                response = await get_embed_cached_health(embed_id="embed123")

                data = json.loads(response.body.decode())
                assert "192.168.1.1" in data


# ==================== Additional Edge Cases ====================


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_save_layout_exception(self, readwrite_user):
        """Should handle file write errors"""
        from app.routers.mapper import save_layout
        from app.services import mapper_runner_service

        with patch.object(
            mapper_runner_service, "save_layout", side_effect=RuntimeError("Access denied")
        ):
            with pytest.raises(Exception) as exc_info:
                save_layout(layout={"root": {}}, user=readwrite_user)

            assert "500" in str(exc_info.value.status_code)

    def test_load_layout_exception(self, temp_data_dir, owner_user):
        """Should handle file read errors"""
        from app.routers.mapper import load_layout
        from app.services import mapper_runner_service

        with patch.object(
            mapper_runner_service, "load_layout", side_effect=RuntimeError("Invalid JSON")
        ):
            with pytest.raises(Exception) as exc_info:
                load_layout(user=owner_user)

            assert "500" in str(exc_info.value.status_code)

    def test_create_embed_exception(self, temp_data_dir, readwrite_user):
        """Should handle embed creation errors"""
        from app.routers.mapper import create_embed
        from app.services import embed_service

        embeds_file = temp_data_dir / "embeds.json"
        embeds_file.write_text("{}")

        with patch.object(embed_service, "_embeds_config_path", return_value=embeds_file):
            with patch.object(
                embed_service, "save_all_embeds", side_effect=IOError("Write failed")
            ):
                with pytest.raises(Exception) as exc_info:
                    create_embed(config={"name": "Test"}, user=readwrite_user)

                assert "500" in str(exc_info.value.status_code)
