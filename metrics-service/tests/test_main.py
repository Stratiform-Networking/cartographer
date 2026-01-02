"""
Unit tests for the main FastAPI application.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app, create_app


class TestCreateApp:
    """Tests for create_app factory"""

    def test_creates_fastapi_app(self):
        """Should create a FastAPI application"""
        with patch("app.main.lifespan"):
            test_app = create_app()

            assert test_app is not None
            assert test_app.title == "Cartographer Metrics Service"
            assert test_app.version == "0.1.0"

    def test_includes_metrics_router(self):
        """Should include metrics router at /api prefix"""
        with patch("app.main.lifespan"):
            test_app = create_app()

            routes = [r.path for r in test_app.routes]

            # Check that metrics endpoints are included
            assert any("/api/metrics" in str(r) for r in routes)


class TestRootEndpoint:
    """Tests for root endpoint"""

    def test_root_returns_service_info(self):
        """Should return service information"""
        with patch("app.main.lifespan"):
            test_app = create_app()
            client = TestClient(test_app)

            response = client.get("/")

            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "Cartographer Metrics Service"
            assert data["status"] == "running"
            assert data["version"] == "0.1.0"
            assert "endpoints" in data


class TestHealthzEndpoint:
    """Tests for healthz endpoint"""

    def test_healthz_returns_healthy(self):
        """Should return healthy status"""
        with patch("app.main.lifespan"):
            test_app = create_app()
            client = TestClient(test_app)

            with patch("app.main.redis_publisher") as mock_redis:
                mock_redis.get_connection_info = AsyncMock(return_value={"connected": True})

                with patch("app.main.metrics_aggregator") as mock_aggregator:
                    mock_aggregator.get_config.return_value = {
                        "publishing_enabled": True,
                        "is_running": True,
                    }

                    response = client.get("/healthz")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"


class TestReadyEndpoint:
    """Tests for ready endpoint"""

    def test_ready_when_redis_connected(self):
        """Should return ready when Redis connected"""
        with patch("app.main.lifespan"):
            test_app = create_app()
            client = TestClient(test_app)

            with patch("app.main.redis_publisher") as mock_redis:
                mock_redis.get_connection_info = AsyncMock(return_value={"connected": True})

                response = client.get("/ready")

            assert response.status_code == 200
            data = response.json()
            assert data["ready"] is True

    def test_not_ready_when_redis_disconnected(self):
        """Should return not ready when Redis disconnected"""
        with patch("app.main.lifespan"):
            test_app = create_app()
            client = TestClient(test_app)

            with patch("app.main.redis_publisher") as mock_redis:
                mock_redis.get_connection_info = AsyncMock(return_value={"connected": False})

                response = client.get("/ready")

            assert response.status_code == 200
            data = response.json()
            assert data["ready"] is False


class TestCORS:
    """Tests for CORS middleware"""

    def test_cors_middleware_present(self):
        """Should have CORS middleware"""
        with patch("app.main.lifespan"):
            with patch.dict("os.environ", {"CORS_ORIGINS": "http://localhost:3000"}):
                test_app = create_app()

                # CORS middleware should be present
                middlewares = [m.cls.__name__ for m in test_app.user_middleware]
                assert "CORSMiddleware" in middlewares


class TestGlobalAppInstance:
    """Tests for global app instance"""

    def test_global_app_exists(self):
        """Should have a global app instance"""
        # The global app is created with lifespan, so we need to mock it
        assert app is not None
        assert app.title == "Cartographer Metrics Service"
