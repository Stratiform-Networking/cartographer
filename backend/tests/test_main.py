"""
Unit tests for the main application module.
"""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestAppCreation:
    """Tests for application creation and configuration"""

    def test_create_app_returns_fastapi_instance(self):
        """create_app should return a FastAPI instance"""
        from app.main import create_app

        with patch("app.main.settings") as mock_settings:
            mock_settings.disable_docs = False
            mock_settings.resolved_frontend_dist = Path("/nonexistent/path")
            app = create_app()

            assert isinstance(app, FastAPI)

    def test_app_has_correct_title(self):
        """App should have the correct title"""
        from app.main import create_app

        with patch("app.main.settings") as mock_settings:
            mock_settings.disable_docs = False
            mock_settings.resolved_frontend_dist = Path("/nonexistent/path")
            app = create_app()

            assert app.title == "Cartographer Backend"

    def test_app_has_cors_middleware(self):
        """App should have CORS middleware configured"""
        from app.main import create_app

        with patch("app.main.settings") as mock_settings:
            mock_settings.disable_docs = False
            mock_settings.resolved_frontend_dist = Path("/nonexistent/path")
            app = create_app()

            # Check that CORS middleware is in the middleware stack
            middleware_classes = [m.cls.__name__ for m in app.user_middleware]
            assert "CORSMiddleware" in middleware_classes

    def test_api_routers_included(self):
        """App should include all API routers"""
        from app.main import create_app

        with patch("app.main.settings") as mock_settings:
            mock_settings.disable_docs = False
            mock_settings.resolved_frontend_dist = Path("/nonexistent/path")
            app = create_app()

            # Get all route paths
            routes = [route.path for route in app.routes]

            # Verify key API routes are registered
            assert "/healthz" in routes
            # API routes have /api prefix
            api_prefixed_routes = [r for r in routes if r.startswith("/api")]
            assert len(api_prefixed_routes) > 0


class TestHealthzEndpoint:
    """Tests for the /healthz endpoint"""

    @pytest.fixture
    def client(self):
        """Create a test client with mocked http_pool"""
        from app.main import create_app

        with patch("app.main.settings") as mock_settings:
            mock_settings.disable_docs = False
            mock_settings.resolved_frontend_dist = Path("/nonexistent/path")

            # Mock the http_pool for healthz endpoint
            with patch("app.routers.health.http_pool") as mock_pool:
                mock_pool._services = {
                    "health": MagicMock(
                        circuit_breaker=MagicMock(state=MagicMock(value="closed"), failure_count=0)
                    ),
                    "auth": MagicMock(
                        circuit_breaker=MagicMock(state=MagicMock(value="closed"), failure_count=0)
                    ),
                }

                app = create_app()
                yield TestClient(app, raise_server_exceptions=False)

    def test_healthz_returns_200(self, client):
        """Healthz endpoint should return 200"""
        response = client.get("/healthz")

        assert response.status_code == 200

    def test_healthz_returns_status(self, client):
        """Healthz should return status healthy"""
        response = client.get("/healthz")
        data = response.json()

        assert data["status"] == "healthy"

    def test_healthz_returns_services_status(self, client):
        """Healthz should return services circuit breaker status"""
        response = client.get("/healthz")
        data = response.json()

        assert "services" in data
        assert "health" in data["services"]
        assert "auth" in data["services"]

        # Check circuit breaker info is included
        assert "circuit_state" in data["services"]["health"]
        assert "failure_count" in data["services"]["health"]


class TestReadyzEndpoint:
    """Tests for the /ready endpoint"""

    @pytest.fixture
    def client_ready(self):
        """Create a test client with healthy http_pool"""
        from app.main import create_app

        with patch("app.main.settings") as mock_settings:
            mock_settings.disable_docs = False
            mock_settings.resolved_frontend_dist = Path("/nonexistent/path")

            with patch("app.routers.health.http_pool") as mock_pool:
                mock_pool._services = {
                    "health": MagicMock(
                        circuit_breaker=MagicMock(state=MagicMock(value="closed"), failure_count=0)
                    )
                }

                app = create_app()
                yield TestClient(app, raise_server_exceptions=False)

    @pytest.fixture
    def client_degraded(self):
        """Create a test client with open circuit"""
        from app.main import create_app

        with patch("app.main.settings") as mock_settings:
            mock_settings.disable_docs = False
            mock_settings.resolved_frontend_dist = Path("/nonexistent/path")

            with patch("app.routers.health.http_pool") as mock_pool:
                mock_pool._services = {
                    "health": MagicMock(
                        circuit_breaker=MagicMock(state=MagicMock(value="open"), failure_count=5)
                    )
                }

                app = create_app()
                yield TestClient(app, raise_server_exceptions=False)

    def test_ready_returns_200(self, client_ready):
        """Ready endpoint should return 200"""
        response = client_ready.get("/ready")
        assert response.status_code == 200

    def test_ready_returns_ready_status(self, client_ready):
        """Ready should return ready status when healthy"""
        response = client_ready.get("/ready")
        data = response.json()
        assert data["status"] == "ready"

    def test_ready_returns_degraded_with_open_circuit(self, client_degraded):
        """Ready should return degraded when circuit is open"""
        response = client_degraded.get("/ready")
        data = response.json()
        assert data["status"] == "degraded"
        assert "open_circuits" in data


class TestLifespan:
    """Tests for application lifespan management"""

    async def test_lifespan_initializes_http_pool(self):
        """Lifespan should initialize and warm up HTTP pool on startup"""
        from app.main import lifespan

        mock_app = MagicMock()

        with patch("app.main.init_db", new_callable=AsyncMock):
            with patch("app.main.run_migrations", new_callable=AsyncMock):
                with patch("app.main.http_pool") as mock_pool:
                    mock_pool.initialize_all = AsyncMock()
                    mock_pool.warm_up_all = AsyncMock(return_value={"service1": True})
                    mock_pool.close_all = AsyncMock()

                    async with lifespan(mock_app):
                        mock_pool.initialize_all.assert_called_once()
                        mock_pool.warm_up_all.assert_called_once()

                    # After exiting context, close should be called
                    mock_pool.close_all.assert_called_once()

    async def test_lifespan_handles_partial_warmup(self):
        """Lifespan should handle partial warm-up success"""
        from app.main import lifespan

        mock_app = MagicMock()

        with patch("app.main.init_db", new_callable=AsyncMock):
            with patch("app.main.run_migrations", new_callable=AsyncMock):
                with patch("app.main.http_pool") as mock_pool:
                    mock_pool.initialize_all = AsyncMock()
                    mock_pool.warm_up_all = AsyncMock(
                        return_value={"service1": True, "service2": False, "service3": True}
                    )
                    mock_pool.close_all = AsyncMock()

                    # Should not raise even if some services fail warm-up
                    async with lifespan(mock_app):
                        pass


class TestRunMigrations:
    """Tests for migration runner"""

    async def test_run_migrations_handles_uuid_migration(self):
        """run_migrations should handle UUID migration"""
        from app.main import run_migrations

        with patch(
            "app.main.migrate_network_ids_to_uuid", new_callable=AsyncMock, return_value=True
        ) as mock_uuid:
            with patch(
                "app.main.migrate_layout_to_database", new_callable=AsyncMock, return_value=False
            ):
                await run_migrations()
                mock_uuid.assert_called_once()

    async def test_run_migrations_handles_layout_migration(self):
        """run_migrations should handle layout migration"""
        from app.main import run_migrations

        with patch(
            "app.main.migrate_network_ids_to_uuid", new_callable=AsyncMock, return_value=False
        ):
            with patch(
                "app.main.migrate_layout_to_database", new_callable=AsyncMock, return_value=True
            ) as mock_layout:
                await run_migrations()
                mock_layout.assert_called_once()

    async def test_run_migrations_handles_errors(self):
        """run_migrations should handle errors gracefully"""
        from app.main import run_migrations

        with patch(
            "app.main.migrate_network_ids_to_uuid",
            new_callable=AsyncMock,
            side_effect=Exception("Test error"),
        ):
            with patch(
                "app.main.migrate_layout_to_database", new_callable=AsyncMock, return_value=False
            ):
                # Should not raise - errors are logged as warnings
                await run_migrations()


class TestDistPathConfiguration:
    """Tests for frontend dist path configuration"""

    def test_default_dist_path(self):
        """Default dist path should be relative to config.py"""
        from app.config import Settings

        # Create settings with default (empty) frontend_dist
        settings = Settings(frontend_dist="")

        # The default should resolve to frontend/dist relative to config.py
        assert settings.resolved_frontend_dist.name == "dist"
        assert "frontend" in str(settings.resolved_frontend_dist)

    def test_custom_dist_path_from_settings(self):
        """Settings.frontend_dist should override default path"""
        from app.config import Settings

        custom_path = "/custom/frontend/path"
        test_settings = Settings(frontend_dist=custom_path)

        # Verify the resolved path matches the custom path
        assert str(test_settings.resolved_frontend_dist) == custom_path


class TestStaticFileServing:
    """Tests for static file serving when dist exists"""

    def test_spa_routes_not_added_without_dist(self):
        """SPA routes should not be added if dist doesn't exist"""
        from app.main import create_app

        with patch("app.main.settings") as mock_settings:
            mock_settings.disable_docs = False
            mock_settings.resolved_frontend_dist = Path("/nonexistent/path")

            app = create_app()

            routes = [route.path for route in app.routes]

            # Root and catch-all should not exist without dist
            spa_routes = [r for r in routes if r == "/" or r == "/{full_path:path}"]
            assert len(spa_routes) == 0

    def test_spa_routes_added_with_dist(self, tmp_path):
        """SPA routes should be added if dist exists with index.html"""
        from app.main import create_app

        # Create mock dist directory
        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()
        (dist_dir / "index.html").write_text("<html></html>")
        assets_dir = dist_dir / "assets"
        assets_dir.mkdir()

        with patch("app.main.settings") as mock_settings:
            mock_settings.disable_docs = False
            mock_settings.resolved_frontend_dist = dist_dir

            app = create_app()

            routes = [route.path for route in app.routes]

            # Check for SPA routes
            assert "/" in routes
            assert "/{full_path:path}" in routes
            assert "/favicon.png" in routes


class TestAppModuleImports:
    """Tests to verify module imports are correct"""

    def test_all_routers_imported(self):
        """All router modules should be importable"""
        from app.routers import (
            assistant_proxy,
            auth_proxy,
            health,
            health_proxy,
            mapper,
            metrics_proxy,
            notification_proxy,
            static,
        )

        # Verify each has a router
        assert hasattr(mapper, "router")
        assert hasattr(health_proxy, "router")
        assert hasattr(auth_proxy, "router")
        assert hasattr(metrics_proxy, "router")
        assert hasattr(assistant_proxy, "router")
        assert hasattr(notification_proxy, "router")
        assert hasattr(health, "router")
        assert hasattr(static, "create_static_router")

    def test_services_imported(self):
        """Service modules should be importable"""
        from app.services import http_client, network_service, usage_middleware

        assert hasattr(http_client, "http_pool")
        assert hasattr(usage_middleware, "UsageTrackingMiddleware")
        assert hasattr(network_service, "get_network_with_access")


class TestDocsDisabling:
    """Tests for documentation URL disabling"""

    def test_docs_enabled_by_default(self):
        """Docs should be enabled when disable_docs is False"""
        from app.main import create_app

        with patch("app.main.settings") as mock_settings:
            mock_settings.disable_docs = False
            mock_settings.resolved_frontend_dist = Path("/nonexistent/path")

            app = create_app()

            assert app.docs_url == "/docs"
            assert app.redoc_url == "/redoc"
            assert app.openapi_url == "/openapi.json"

    def test_docs_disabled_when_configured(self):
        """Docs should be disabled when disable_docs is True"""
        from app.main import create_app

        with patch("app.main.settings") as mock_settings:
            mock_settings.disable_docs = True
            mock_settings.resolved_frontend_dist = Path("/nonexistent/path")

            app = create_app()

            assert app.docs_url is None
            assert app.redoc_url is None
            assert app.openapi_url is None
