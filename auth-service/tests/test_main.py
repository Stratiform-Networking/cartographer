"""
Unit tests for the main FastAPI application.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import create_app, app


class TestCreateApp:
    """Tests for create_app factory"""
    
    def test_creates_fastapi_app(self):
        """Should create a FastAPI application"""
        test_app = create_app()
        
        assert test_app is not None
        assert test_app.title == "Cartographer Auth Service"
        assert test_app.version == "0.1.0"
    
    def test_includes_auth_router(self):
        """Should include auth router at /api/auth prefix"""
        test_app = create_app()
        
        routes = [r.path for r in test_app.routes]
        
        # Check that auth endpoints are included
        assert any("/api/auth" in str(r) for r in routes)


class TestRootEndpoint:
    """Tests for root endpoint"""
    
    def test_root_returns_service_info(self):
        """Should return service information"""
        test_app = create_app()
        client = TestClient(test_app)
        
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Cartographer Auth Service"
        assert data["status"] == "running"
        assert data["version"] == "0.1.0"


class TestHealthzEndpoint:
    """Tests for healthz endpoint"""
    
    def test_healthz_returns_healthy(self):
        """Should return healthy status"""
        test_app = create_app()
        client = TestClient(test_app)
        
        response = client.get("/healthz")
        
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestCORS:
    """Tests for CORS middleware"""
    
    def test_cors_allows_all_origins_by_default(self):
        """Should allow all origins by default"""
        with patch.dict('os.environ', {}, clear=False):
            test_app = create_app()
            
            # CORS middleware should be present
            middlewares = [m.cls.__name__ for m in test_app.user_middleware]
            assert "CORSMiddleware" in middlewares
    
    def test_cors_uses_env_origins(self):
        """Should use CORS_ORIGINS from environment"""
        with patch.dict('os.environ', {"CORS_ORIGINS": "http://localhost:3000,http://example.com"}):
            test_app = create_app()
            
            # App should be created without errors
            assert test_app is not None


class TestGlobalAppInstance:
    """Tests for global app instance"""
    
    def test_global_app_exists(self):
        """Should have a global app instance"""
        assert app is not None
        assert app.title == "Cartographer Auth Service"

