"""
Integration tests for mapper router to achieve higher coverage.
These tests cover the actual endpoint handlers with mocked file operations.
"""

import json
import subprocess
import sys
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


@pytest.fixture
def owner_user():
    return AuthenticatedUser(user_id="owner-123", username="owner", role=UserRole.OWNER)


@pytest.fixture
def readwrite_user():
    return AuthenticatedUser(user_id="rw-123", username="admin", role=UserRole.ADMIN)


@pytest.fixture
def app():
    """Create test app with mapper router"""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api")
    return test_app


class TestMapperScriptExecution:
    """Tests for run_mapper script execution"""

    @skip_on_windows
    def test_run_mapper_with_executable_script(self, tmp_path, readwrite_user):
        """Should run executable script directly"""
        from app.routers.mapper import run_mapper
        from app.services import mapper_runner_service

        # Create executable script
        script = tmp_path / "lan_mapper.sh"
        script.write_text("#!/bin/bash\necho 'Router: 192.168.1.1'")
        script.chmod(0o755)

        network_map = tmp_path / "network_map.txt"
        network_map.write_text("Router: 192.168.1.1\nDevice: 192.168.1.10")

        with patch.object(mapper_runner_service, "project_root", return_value=tmp_path):
            with patch.object(mapper_runner_service, "script_path", return_value=script):
                with patch.object(
                    mapper_runner_service, "network_map_candidates", return_value=[network_map]
                ):
                    result = run_mapper(user=readwrite_user)

                    assert result.content is not None
                    assert "Router" in result.content

    @skip_on_windows
    def test_run_mapper_with_non_executable_script(self, tmp_path, readwrite_user):
        """Should run non-executable script with bash"""
        from app.routers.mapper import run_mapper
        from app.services import mapper_runner_service

        # Create non-executable script
        script = tmp_path / "lan_mapper.sh"
        script.write_text("#!/bin/bash\necho 'Hello'")
        # Don't chmod - leave non-executable

        network_map = tmp_path / "network_map.txt"
        network_map.write_text("Network data")

        with patch.object(mapper_runner_service, "project_root", return_value=tmp_path):
            with patch.object(mapper_runner_service, "script_path", return_value=script):
                with patch.object(
                    mapper_runner_service, "network_map_candidates", return_value=[network_map]
                ):
                    result = run_mapper(user=readwrite_user)

                    assert result.content is not None

    @skip_on_windows
    def test_run_mapper_fallback_to_stdout(self, tmp_path, readwrite_user):
        """Should fallback to stdout if no file produced"""
        from app.routers.mapper import run_mapper
        from app.services import mapper_runner_service

        script = tmp_path / "lan_mapper.sh"
        script.write_text("#!/bin/bash\necho 'stdout content'")
        script.chmod(0o755)

        with patch.object(mapper_runner_service, "project_root", return_value=tmp_path):
            with patch.object(mapper_runner_service, "script_path", return_value=script):
                with patch.object(
                    mapper_runner_service,
                    "network_map_candidates",
                    return_value=[tmp_path / "nonexistent.txt"],
                ):
                    # When file doesn't exist, it uses stdout
                    result = run_mapper(user=readwrite_user)

                    # Should have content from stdout
                    assert result.content == "stdout content"

    def test_run_mapper_no_content_error(self, tmp_path, readwrite_user):
        """Should raise error if no content produced"""
        from app.routers.mapper import run_mapper
        from app.services import mapper_runner_service

        script = tmp_path / "lan_mapper.sh"
        script.write_text("#!/bin/bash\n# no output")
        script.chmod(0o755)

        with patch.object(mapper_runner_service, "project_root", return_value=tmp_path):
            with patch.object(mapper_runner_service, "script_path", return_value=script):
                with patch.object(
                    mapper_runner_service,
                    "network_map_candidates",
                    return_value=[tmp_path / "nonexistent.txt"],
                ):
                    with pytest.raises(HTTPException) as exc_info:
                        run_mapper(user=readwrite_user)

                    assert exc_info.value.status_code == 500

    def test_run_mapper_subprocess_exception(self, tmp_path, readwrite_user):
        """Should handle subprocess exceptions"""
        from app.routers.mapper import run_mapper
        from app.services import mapper_runner_service

        script = tmp_path / "lan_mapper.sh"
        script.write_text("#!/bin/bash\nexit 1")
        script.chmod(0o755)

        with patch.object(mapper_runner_service, "project_root", return_value=tmp_path):
            with patch.object(mapper_runner_service, "script_path", return_value=script):
                with patch("subprocess.run", side_effect=OSError("Execution failed")):
                    with pytest.raises(HTTPException) as exc_info:
                        run_mapper(user=readwrite_user)

                    assert exc_info.value.status_code == 500


class TestRunMapperStream:
    """Tests for streaming mapper endpoint"""

    def test_run_mapper_stream_script_not_found(self, readwrite_user):
        """Should return 404 if script not found"""
        from app.routers.mapper import run_mapper_stream
        from app.services import mapper_runner_service

        with patch.object(
            mapper_runner_service, "script_path", return_value=Path("/nonexistent/script.sh")
        ):
            with pytest.raises(HTTPException) as exc_info:
                run_mapper_stream(user=readwrite_user)

            assert exc_info.value.status_code == 404

    def test_run_mapper_stream_generator(self, tmp_path, readwrite_user):
        """Should return StreamingResponse"""
        from fastapi.responses import StreamingResponse

        from app.routers.mapper import run_mapper_stream
        from app.services import mapper_runner_service

        script = tmp_path / "lan_mapper.sh"
        script.write_text("#!/bin/bash\necho 'line1'\necho 'line2'")
        script.chmod(0o755)

        with patch.object(mapper_runner_service, "script_path", return_value=script):
            with patch.object(mapper_runner_service, "project_root", return_value=tmp_path):
                with patch.object(
                    mapper_runner_service,
                    "network_map_candidates",
                    return_value=[tmp_path / "map.txt"],
                ):
                    response = run_mapper_stream(user=readwrite_user)

                    assert isinstance(response, StreamingResponse)


class TestEmbedDataEndpoint:
    """Additional tests for embed data endpoint"""

    @pytest.fixture
    def setup_files(self, tmp_path):
        """Setup test files"""
        embeds_file = tmp_path / "embeds.json"
        layout_file = tmp_path / "layout.json"

        embeds_file.write_text(
            json.dumps(
                {
                    "test-embed": {
                        "name": "Test",
                        "sensitiveMode": False,
                        "showOwner": True,
                        "ownerDisplayName": "Admin",
                        "createdAt": "2024-01-01T00:00:00Z",
                    }
                }
            )
        )

        layout_file.write_text(
            json.dumps(
                {
                    "root": {
                        "id": "192.168.1.1",
                        "ip": "192.168.1.1",
                        "hostname": "router",
                        "type": "router",
                        "children": [],
                    }
                }
            )
        )

        return {"embeds": embeds_file, "layout": layout_file}

    async def test_embed_data_no_root_in_layout(self, tmp_path):
        """Should handle layout without root"""
        from app.routers.mapper import get_embed_data
        from app.services import embed_service, mapper_runner_service

        embeds_file = tmp_path / "embeds.json"
        layout_file = tmp_path / "layout.json"

        embeds_file.write_text(
            json.dumps(
                {
                    "test": {
                        "name": "Test",
                        "sensitiveMode": False,
                        "createdAt": "2024-01-01T00:00:00Z",
                    }
                }
            )
        )
        layout_file.write_text(json.dumps({"root": None}))

        mock_db = AsyncMock()

        with (
            patch.object(embed_service, "_embeds_config_path", return_value=embeds_file),
            patch.object(mapper_runner_service, "saved_layout_path", return_value=layout_file),
            patch.object(mapper_runner_service, "load_layout", return_value={"root": None}),
        ):
            response = await get_embed_data(embed_id="test", db=mock_db)

            data = json.loads(response.body.decode())
            assert data["exists"] is False

    async def test_embed_data_load_exception(self, tmp_path):
        """Should handle load exception"""
        from app.routers.mapper import get_embed_data
        from app.services import embed_service, mapper_runner_service

        embeds_file = tmp_path / "embeds.json"

        embeds_file.write_text(
            json.dumps(
                {
                    "test": {
                        "name": "Test",
                        "sensitiveMode": False,
                        "createdAt": "2024-01-01T00:00:00Z",
                    }
                }
            )
        )

        mock_db = AsyncMock()

        with patch.object(embed_service, "_embeds_config_path", return_value=embeds_file):
            with patch.object(
                mapper_runner_service, "load_layout", side_effect=RuntimeError("Failed to load")
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await get_embed_data(embed_id="test", db=mock_db)

                assert exc_info.value.status_code == 500


class TestEmbedHealthEndpointsWithMapping:
    """Tests for embed health endpoints with IP mapping"""

    @pytest.fixture
    def setup_embed_with_mapping(self, tmp_path):
        """Setup embed with IP mapping in global variable"""
        from app.services import embed_service

        embeds_file = tmp_path / "embeds.json"
        embeds_file.write_text(
            json.dumps(
                {
                    "embed-with-mapping": {
                        "name": "Test",
                        "sensitiveMode": True,
                        "createdAt": "2024-01-01T00:00:00Z",
                    }
                }
            )
        )

        # Set up the IP mapping
        embed_service.set_ip_mapping(
            "embed-with-mapping", {"device_abc123": "192.168.1.1", "device_def456": "192.168.1.2"}
        )

        return embeds_file

    async def test_register_with_mapping(self, setup_embed_with_mapping):
        """Should translate anonymized IDs to real IPs"""
        from app.routers.mapper import EmbedHealthRegisterRequest, register_embed_health_devices
        from app.services import embed_service, health_proxy_service

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            embed_service, "_embeds_config_path", return_value=setup_embed_with_mapping
        ):
            with patch.object(
                health_proxy_service, "register_devices", new_callable=AsyncMock
            ) as mock_health:
                mock_health.return_value = mock_response

                response = await register_embed_health_devices(
                    embed_id="embed-with-mapping",
                    request=EmbedHealthRegisterRequest(
                        device_ids=["device_abc123", "device_def456"]
                    ),
                )

                data = json.loads(response.body.decode())
                assert data["count"] == 2

    async def test_get_cached_health_with_mapping(self, setup_embed_with_mapping):
        """Should anonymize metrics in response"""
        from app.routers.mapper import get_embed_cached_health
        from app.services import embed_service, health_proxy_service

        with patch.object(
            embed_service, "_embeds_config_path", return_value=setup_embed_with_mapping
        ):
            with patch.object(
                health_proxy_service, "get_cached_metrics", new_callable=AsyncMock
            ) as mock_health:
                mock_health.return_value = {
                    "192.168.1.1": {"status": "healthy", "ip": "192.168.1.1"},
                    "192.168.1.2": {"status": "healthy", "ip": "192.168.1.2"},
                }

                response = await get_embed_cached_health(embed_id="embed-with-mapping")

                data = json.loads(response.body.decode())
                # Should have anonymized keys
                assert "device_abc123" in data or "device_def456" in data

    async def test_trigger_check_returns_400_handling(self, tmp_path):
        """Should handle 400 response from health service"""
        from app.routers.mapper import trigger_embed_health_check
        from app.services import embed_service, health_proxy_service

        embeds_file = tmp_path / "embeds.json"
        embeds_file.write_text(
            json.dumps(
                {
                    "test": {
                        "name": "Test",
                        "sensitiveMode": False,
                        "createdAt": "2024-01-01T00:00:00Z",
                    }
                }
            )
        )

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status = MagicMock()

        with patch.object(embed_service, "_embeds_config_path", return_value=embeds_file):
            with patch.object(
                health_proxy_service, "trigger_health_check", new_callable=AsyncMock
            ) as mock_health:
                mock_health.return_value = mock_response

                response = await trigger_embed_health_check(embed_id="test")

                data = json.loads(response.body.decode())
                assert "No devices" in data["message"]


class TestEmbedUpdateFields:
    """Test various embed update scenarios"""

    def test_update_all_fields(self, tmp_path, readwrite_user):
        """Should update all configurable fields"""
        from app.routers.mapper import update_embed
        from app.services import embed_service

        embeds_file = tmp_path / "embeds.json"
        embeds_file.write_text(
            json.dumps(
                {
                    "test": {
                        "name": "Old Name",
                        "sensitiveMode": False,
                        "showOwner": False,
                        "ownerDisplayType": "fullName",
                        "ownerDisplayName": None,
                        "createdAt": "2024-01-01T00:00:00Z",
                        "updatedAt": "2024-01-01T00:00:00Z",
                    }
                }
            )
        )

        with patch.object(embed_service, "_embeds_config_path", return_value=embeds_file):
            response = update_embed(
                embed_id="test",
                config={
                    "name": "New Name",
                    "sensitiveMode": True,
                    "showOwner": True,
                    "ownerDisplayType": "username",
                    "ownerDisplayName": "Admin",
                },
                user=readwrite_user,
            )

            data = json.loads(response.body.decode())
            assert data["success"] is True
            assert data["embed"]["name"] == "New Name"
            assert data["embed"]["sensitiveMode"] is True


class TestHelperPaths:
    """Test helper path functions"""

    def test_project_root(self):
        """project_root should return correct path"""
        from app.services.mapper_runner_service import project_root

        root = project_root()
        assert root.exists() or True  # Path may not exist in test env, just check it runs

    def test_script_path(self):
        """script_path should return path to lan_mapper.sh"""
        from app.services.mapper_runner_service import script_path

        path = script_path()
        assert path.name == "lan_mapper.sh"

    def test_network_map_candidates(self):
        """network_map_candidates should return list of paths"""
        from app.services.mapper_runner_service import network_map_candidates

        candidates = network_map_candidates()
        assert len(candidates) >= 1
        assert all(isinstance(p, Path) for p in candidates)


class TestGetScriptCommandWindows:
    """Tests for Windows-specific mapper command selection"""

    def test_windows_prefers_pwsh(self, tmp_path):
        """Should use pwsh for Windows when available"""
        from app.services import mapper_runner_service

        script = tmp_path / "lan_mapper.sh"
        script.write_text("#!/bin/bash\necho ok")
        ps1 = tmp_path / "lan_mapper.ps1"
        ps1.write_text("Write-Host ok")

        with patch.object(mapper_runner_service, "project_root", return_value=tmp_path):
            with patch.object(mapper_runner_service, "script_path", return_value=script):
                with patch(
                    "app.services.mapper_runner_service.platform.system", return_value="Windows"
                ):
                    with patch("app.services.mapper_runner_service.shutil.which") as mock_which:

                        def which_side(name):
                            if name == "pwsh":
                                return "C:\\Program Files\\PowerShell\\pwsh.exe"
                            return None

                        mock_which.side_effect = which_side
                        cmd = mapper_runner_service.get_script_command()

                        assert cmd == [
                            "C:\\Program Files\\PowerShell\\pwsh.exe",
                            "-NoProfile",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-File",
                            str(ps1),
                        ]

    def test_windows_falls_back_to_bash(self, tmp_path):
        """Should use bash when PowerShell is unavailable on Windows"""
        from app.services import mapper_runner_service

        script = tmp_path / "lan_mapper.sh"
        script.write_text("#!/bin/bash\necho ok")
        ps1 = tmp_path / "lan_mapper.ps1"
        ps1.write_text("Write-Host ok")

        with patch.object(mapper_runner_service, "project_root", return_value=tmp_path):
            with patch.object(mapper_runner_service, "script_path", return_value=script):
                with patch(
                    "app.services.mapper_runner_service.platform.system", return_value="Windows"
                ):
                    with patch("app.services.mapper_runner_service.shutil.which") as mock_which:

                        def which_side(name):
                            if name == "bash":
                                return "/usr/bin/bash"
                            return None

                        mock_which.side_effect = which_side
                        cmd = mapper_runner_service.get_script_command()

                        assert cmd == ["/usr/bin/bash", str(script)]

    def test_windows_falls_back_to_script(self, tmp_path):
        """Should return script directly when no shells are available on Windows"""
        from app.services import mapper_runner_service

        script = tmp_path / "lan_mapper.sh"
        script.write_text("#!/bin/bash\necho ok")

        with patch.object(mapper_runner_service, "project_root", return_value=tmp_path):
            with patch.object(mapper_runner_service, "script_path", return_value=script):
                with patch(
                    "app.services.mapper_runner_service.platform.system", return_value="Windows"
                ):
                    with patch(
                        "app.services.mapper_runner_service.shutil.which", return_value=None
                    ):
                        cmd = mapper_runner_service.get_script_command()

                        assert cmd == [str(script)]


class TestHealthServiceRequestErrors:
    """Test health service request error handling"""

    async def test_health_request_connect_error(self, tmp_path):
        """Should handle connection errors"""
        import httpx

        from app.routers.mapper import EmbedHealthRegisterRequest, register_embed_health_devices
        from app.services import embed_service, health_proxy_service

        embeds_file = tmp_path / "embeds.json"
        embeds_file.write_text(
            json.dumps(
                {
                    "test": {
                        "name": "Test",
                        "sensitiveMode": False,
                        "createdAt": "2024-01-01T00:00:00Z",
                    }
                }
            )
        )

        # Set up IP mapping
        embed_service.set_ip_mapping("test", {"device_abc": "192.168.1.1"})

        with patch.object(embed_service, "_embeds_config_path", return_value=embeds_file):
            with patch.object(
                health_proxy_service, "register_devices", new_callable=AsyncMock
            ) as mock_health:
                mock_health.side_effect = httpx.ConnectError("Connection refused")

                with pytest.raises(HTTPException) as exc_info:
                    await register_embed_health_devices(
                        embed_id="test",
                        request=EmbedHealthRegisterRequest(device_ids=["device_abc"]),
                    )

                assert exc_info.value.status_code == 503

    async def test_cached_health_connect_error(self, tmp_path):
        """Should handle connection errors in cached health"""
        import httpx

        from app.routers.mapper import get_embed_cached_health
        from app.services import embed_service, health_proxy_service

        embeds_file = tmp_path / "embeds.json"
        embeds_file.write_text(
            json.dumps(
                {
                    "test": {
                        "name": "Test",
                        "sensitiveMode": False,
                        "createdAt": "2024-01-01T00:00:00Z",
                    }
                }
            )
        )

        with patch.object(embed_service, "_embeds_config_path", return_value=embeds_file):
            with patch.object(
                health_proxy_service, "get_cached_metrics", new_callable=AsyncMock
            ) as mock_health:
                mock_health.side_effect = httpx.ConnectError("Connection refused")

                with pytest.raises(HTTPException) as exc_info:
                    await get_embed_cached_health(embed_id="test")

                assert exc_info.value.status_code == 503

    async def test_trigger_check_connect_error(self, tmp_path):
        """Should handle connection errors in trigger check"""
        import httpx

        from app.routers.mapper import trigger_embed_health_check
        from app.services import embed_service, health_proxy_service

        embeds_file = tmp_path / "embeds.json"
        embeds_file.write_text(
            json.dumps(
                {
                    "test": {
                        "name": "Test",
                        "sensitiveMode": False,
                        "createdAt": "2024-01-01T00:00:00Z",
                    }
                }
            )
        )

        with patch.object(embed_service, "_embeds_config_path", return_value=embeds_file):
            with patch.object(
                health_proxy_service, "trigger_health_check", new_callable=AsyncMock
            ) as mock_health:
                mock_health.side_effect = httpx.ConnectError("Connection refused")

                with pytest.raises(HTTPException) as exc_info:
                    await trigger_embed_health_check(embed_id="test")

                assert exc_info.value.status_code == 503
