"""
Unit tests for main application module.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import reload_env_overrides, settings


class TestCreateApp:
    """Tests for create_app function"""

    def test_create_app(self):
        """Should create FastAPI app"""
        from app.main import create_app

        app = create_app()

        assert app is not None
        assert app.title == "Cartographer Auth Service"

    def test_create_app_with_docs_disabled(self):
        """Should disable docs when disable_docs is true"""
        with patch.object(settings, "disable_docs", True):
            from app.main import create_app

            app = create_app()

            assert app.docs_url is None
            assert app.redoc_url is None
            assert app.openapi_url is None

    def test_create_app_cors_origins(self):
        """Should configure CORS from settings"""
        with patch.object(settings, "cors_origins", "http://localhost:3000,http://localhost:5173"):
            from app.main import create_app

            app = create_app()

            assert app is not None


class TestEndpoints:
    """Tests for app endpoints"""

    def test_root_endpoint(self):
        """Should return service info"""
        from app.main import create_app

        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Cartographer Auth Service"
        assert data["status"] == "running"

    def test_healthz_endpoint(self):
        """Should return healthy status"""
        from app.main import create_app

        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/healthz")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_ready_endpoint(self):
        """Should return ready status"""
        from app.main import create_app

        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/ready")

        assert response.status_code == 200
        assert response.json()["status"] == "ready"


class TestLifespan:
    """Tests for application lifespan"""

    @pytest.mark.asyncio
    async def test_lifespan_without_alembic(self):
        """Should handle missing alembic.ini gracefully"""
        from fastapi import FastAPI

        from app.main import lifespan

        app = FastAPI()

        with patch("pathlib.Path.exists", return_value=False):
            async with lifespan(app):
                pass  # Should complete without error

    @pytest.mark.asyncio
    async def test_lifespan_with_alembic_success(self):
        """Should run migrations successfully"""

        from fastapi import FastAPI

        from app.main import lifespan

        app = FastAPI()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Migration successful"
        mock_result.stderr = ""

        mock_session = AsyncMock()
        mock_result_obj = MagicMock()
        mock_result_obj.scalar.return_value = False  # version_table_exists = False
        mock_session.execute.return_value = mock_result_obj

        mock_session_context = AsyncMock()
        mock_session_context.__aenter__.return_value = mock_session
        mock_session_context.__aexit__.return_value = None

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("subprocess.run", return_value=mock_result),
            patch("app.database.async_session_maker", return_value=mock_session_context),
        ):
            async with lifespan(app):
                pass  # Should complete without error

    @pytest.mark.asyncio
    async def test_lifespan_migration_failure(self):
        """Should handle migration failure gracefully"""
        from fastapi import FastAPI

        from app.main import lifespan

        app = FastAPI()

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Migration error"

        mock_session = AsyncMock()
        mock_result_obj = MagicMock()
        mock_result_obj.scalar.return_value = False
        mock_session.execute.return_value = mock_result_obj

        mock_session_context = AsyncMock()
        mock_session_context.__aenter__.return_value = mock_session
        mock_session_context.__aexit__.return_value = None

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("subprocess.run", return_value=mock_result),
            patch("app.database.async_session_maker", return_value=mock_session_context),
        ):
            async with lifespan(app):
                pass  # Should continue despite failure

    @pytest.mark.asyncio
    async def test_lifespan_migration_timeout(self):
        """Should handle migration timeout"""
        import subprocess

        from fastapi import FastAPI

        from app.main import lifespan

        app = FastAPI()

        mock_session = AsyncMock()
        mock_result_obj = MagicMock()
        mock_result_obj.scalar.return_value = False
        mock_session.execute.return_value = mock_result_obj

        mock_session_context = AsyncMock()
        mock_session_context.__aenter__.return_value = mock_session
        mock_session_context.__aexit__.return_value = None

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="test", timeout=60)),
            patch("app.database.async_session_maker", return_value=mock_session_context),
        ):
            async with lifespan(app):
                pass  # Should continue despite timeout

    @pytest.mark.asyncio
    async def test_lifespan_alembic_not_found(self):
        """Should handle alembic not installed"""
        from fastapi import FastAPI

        from app.main import lifespan

        app = FastAPI()

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("subprocess.run", side_effect=FileNotFoundError()),
        ):
            async with lifespan(app):
                pass  # Should continue without alembic

    @pytest.mark.asyncio
    async def test_lifespan_general_exception(self):
        """Should handle general exceptions during migration"""
        from fastapi import FastAPI

        from app.main import lifespan

        app = FastAPI()

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("subprocess.run", side_effect=Exception("Test error")),
        ):
            async with lifespan(app):
                pass  # Should continue despite error


class TestAppInstance:
    """Tests for the app instance"""

    def test_app_exists(self):
        """Should have app instance"""
        from app.main import app

        assert app is not None


class TestReloadEnv:
    """Tests for internal env hot-reload paths."""

    def test_reload_env_overrides_updates_known_fields(self):
        """Should update known config fields and ignore unknown keys."""
        with patch.object(settings, "application_url", "http://before"):
            updated = reload_env_overrides(
                {"application_url": "http://after", "unknown_field": "x"}
            )

            assert "application_url" in updated
            assert settings.application_url == "http://after"

    def test_reload_env_endpoint(self):
        """Should return updated fields for internal reload endpoint."""
        from app.main import create_app

        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)

        with patch("app.main.reload_env_overrides", return_value=["application_url"]) as m:
            response = client.post(
                "/_internal/reload-env",
                json={"application_url": "https://prod.example.com/app"},
            )

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "updated": ["application_url"]}
        m.assert_called_once_with({"application_url": "https://prod.example.com/app"})
