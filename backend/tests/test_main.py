"""
Unit tests for the main application module.
"""
import os
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestAppCreation:
    """Tests for application creation and configuration"""
    
    def test_create_app_returns_fastapi_instance(self):
        """create_app should return a FastAPI instance"""
        from app.main import create_app
        
        with patch('app.main.DIST_PATH') as mock_dist:
            mock_dist.exists.return_value = False
            app = create_app()
            
            assert isinstance(app, FastAPI)
    
    def test_app_has_correct_title(self):
        """App should have the correct title"""
        from app.main import create_app
        
        with patch('app.main.DIST_PATH') as mock_dist:
            mock_dist.exists.return_value = False
            app = create_app()
            
            assert app.title == "Cartographer Backend"
    
    def test_app_has_cors_middleware(self):
        """App should have CORS middleware configured"""
        from app.main import create_app
        
        with patch('app.main.DIST_PATH') as mock_dist:
            mock_dist.exists.return_value = False
            app = create_app()
            
            # Check that CORS middleware is in the middleware stack
            middleware_classes = [m.cls.__name__ for m in app.user_middleware]
            assert "CORSMiddleware" in middleware_classes
    
    def test_api_routers_included(self):
        """App should include all API routers"""
        from app.main import create_app
        
        with patch('app.main.DIST_PATH') as mock_dist:
            mock_dist.exists.return_value = False
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
        
        with patch('app.main.DIST_PATH') as mock_dist:
            mock_dist.exists.return_value = False
            app = create_app()
            
            # Mock the http_pool for healthz endpoint
            with patch('app.main.http_pool') as mock_pool:
                mock_pool._services = {
                    "health": MagicMock(
                        circuit_breaker=MagicMock(
                            state=MagicMock(value="closed"),
                            failure_count=0
                        )
                    ),
                    "auth": MagicMock(
                        circuit_breaker=MagicMock(
                            state=MagicMock(value="closed"),
                            failure_count=0
                        )
                    )
                }
                
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


class TestLifespan:
    """Tests for application lifespan management"""
    
    async def test_lifespan_initializes_http_pool(self):
        """Lifespan should initialize and warm up HTTP pool on startup"""
        from app.main import lifespan
        
        mock_app = MagicMock()
        
        with patch('app.main.init_db', new_callable=AsyncMock):
            with patch('app.main.migrate_layout_to_database', new_callable=AsyncMock, return_value=False):
                with patch('app.main.http_pool') as mock_pool:
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
        
        with patch('app.main.init_db', new_callable=AsyncMock):
            with patch('app.main.migrate_layout_to_database', new_callable=AsyncMock, return_value=False):
                with patch('app.main.http_pool') as mock_pool:
                    mock_pool.initialize_all = AsyncMock()
                    mock_pool.warm_up_all = AsyncMock(return_value={
                        "service1": True,
                        "service2": False,
                        "service3": True
                    })
                    mock_pool.close_all = AsyncMock()
                    
                    # Should not raise even if some services fail warm-up
                    async with lifespan(mock_app):
                        pass


class TestDistPathConfiguration:
    """Tests for frontend dist path configuration"""
    
    def test_default_dist_path(self):
        """Default dist path should be relative to main.py"""
        # Clear environment variable to test default
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("FRONTEND_DIST", None)
            
            # Re-import to get fresh module with default path
            import importlib
            import app.main
            importlib.reload(app.main)
            
            # The default should be relative to the module
            # ../../../frontend/dist from backend/app/main.py
            expected_suffix = Path("frontend") / "dist"
            assert app.main.DIST_PATH.name == "dist"
    
    def test_custom_dist_path_from_env(self):
        """FRONTEND_DIST env var should override default path"""
        custom_path = "/custom/frontend/path"
        
        with patch.dict(os.environ, {"FRONTEND_DIST": custom_path}):
            import importlib
            import app.main
            importlib.reload(app.main)
            
            # Convert custom_path to platform-specific path for comparison
            expected_path = str(Path(custom_path))
            assert str(app.main.DIST_PATH) == expected_path


class TestStaticFileServing:
    """Tests for static file serving when dist exists"""
    
    def test_spa_routes_not_added_without_dist(self):
        """SPA routes should not be added if dist doesn't exist"""
        from app.main import create_app
        
        with patch('app.main.DIST_PATH') as mock_dist:
            mock_dist.exists.return_value = False
            app = create_app()
            
            routes = [route.path for route in app.routes]
            
            # Root and catch-all should not exist without dist
            spa_routes = [r for r in routes if r == "/" or r == "/{full_path:path}"]
            # These should not be in routes when dist doesn't exist
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
        
        with patch('app.main.DIST_PATH', dist_dir):
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
        from app.routers import mapper
        from app.routers import health_proxy
        from app.routers import auth_proxy
        from app.routers import metrics_proxy
        from app.routers import assistant_proxy
        from app.routers import notification_proxy
        
        # Verify each has a router
        assert hasattr(mapper, 'router')
        assert hasattr(health_proxy, 'router')
        assert hasattr(auth_proxy, 'router')
        assert hasattr(metrics_proxy, 'router')
        assert hasattr(assistant_proxy, 'router')
        assert hasattr(notification_proxy, 'router')
    
    def test_http_client_importable(self):
        """HTTP client module should be importable"""
        from app.services.http_client import http_pool, HTTPClientPool
        
        assert http_pool is not None
        assert HTTPClientPool is not None
    
    def test_auth_dependencies_importable(self):
        """Auth dependencies should be importable"""
        from app.dependencies.auth import (
            AuthenticatedUser,
            UserRole,
            require_auth,
            require_write_access,
            require_owner,
            get_current_user
        )
        
        assert AuthenticatedUser is not None
        assert UserRole is not None

