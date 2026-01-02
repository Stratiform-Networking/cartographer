"""
Unit tests for the main FastAPI application.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app, create_app


class TestCreateApp:
    """Tests for create_app factory"""

    def test_creates_fastapi_app(self):
        """Should create a FastAPI application"""
        test_app = create_app()

        assert test_app is not None
        assert test_app.title == "Cartographer Health Service"
        assert test_app.version == "0.1.0"

    def test_includes_health_router(self):
        """Should include health router at /api prefix"""
        test_app = create_app()

        routes = [r.path for r in test_app.routes]

        # Check that health endpoints are included
        assert any("/api/health" in str(r) for r in routes)


class TestRootEndpoint:
    """Tests for root endpoint"""

    def test_root_returns_service_info(self):
        """Should return service information"""
        with patch("app.main.health_checker") as mock_checker:
            mock_checker.start_monitoring = MagicMock()
            mock_checker.stop_monitoring = MagicMock()

            test_app = create_app()
            client = TestClient(test_app)

            response = client.get("/")

            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "Cartographer Health Service"
            assert data["status"] == "running"
            assert data["version"] == "0.1.0"


class TestHealthzEndpoint:
    """Tests for healthz endpoint"""

    def test_healthz_returns_healthy(self):
        """Should return healthy status"""
        with patch("app.main.health_checker") as mock_checker:
            mock_checker.start_monitoring = MagicMock()
            mock_checker.stop_monitoring = MagicMock()

            test_app = create_app()
            client = TestClient(test_app)

            response = client.get("/healthz")

            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}


class TestCORS:
    """Tests for CORS middleware"""

    def test_cors_allows_all_origins_by_default(self):
        """Should allow all origins by default"""
        with patch.dict("os.environ", {}, clear=True):
            test_app = create_app()

            # CORS middleware should be present
            middlewares = [m.cls.__name__ for m in test_app.user_middleware]
            assert "CORSMiddleware" in middlewares

    def test_cors_uses_env_origins(self):
        """Should use CORS_ORIGINS from environment"""
        with patch.dict("os.environ", {"CORS_ORIGINS": "http://localhost:3000,http://example.com"}):
            test_app = create_app()

            # App should be created without errors
            assert test_app is not None


class TestLifespan:
    """Tests for application lifespan events"""

    def test_lifespan_starts_monitoring(self):
        """Should start monitoring on startup"""
        with patch("app.main.health_checker") as mock_checker:
            mock_checker.start_monitoring = MagicMock()
            mock_checker.stop_monitoring = MagicMock()

            test_app = create_app()

            with TestClient(test_app):
                mock_checker.start_monitoring.assert_called_once()

    def test_lifespan_stops_monitoring(self):
        """Should stop monitoring on shutdown"""
        with patch("app.main.health_checker") as mock_checker:
            mock_checker.start_monitoring = MagicMock()
            mock_checker.stop_monitoring = MagicMock()

            test_app = create_app()

            with TestClient(test_app):
                pass

            mock_checker.stop_monitoring.assert_called_once()


class TestGlobalAppInstance:
    """Tests for global app instance"""

    def test_global_app_exists(self):
        """Should have a global app instance"""
        assert app is not None
        assert app.title == "Cartographer Health Service"
