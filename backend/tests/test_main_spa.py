"""
Tests for main.py SPA routes and static file serving.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestSPARoutes:
    """Tests for SPA routing and static file serving"""

    @pytest.fixture
    def dist_with_assets(self, tmp_path):
        """Create a mock dist directory with assets"""
        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()

        # Create index.html
        (dist_dir / "index.html").write_text(
            """
        <!DOCTYPE html>
        <html>
        <head><title>Cartographer</title></head>
        <body><div id="app"></div></body>
        </html>
        """
        )

        # Create favicon
        (dist_dir / "favicon.png").write_bytes(b"\x89PNG\r\n\x1a\n")

        # Create assets directory
        assets_dir = dist_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "app.js").write_text("console.log('app');")
        (assets_dir / "style.css").write_text("body { margin: 0; }")

        return dist_dir

    def test_index_route(self, dist_with_assets):
        """Root route should serve index.html"""
        from app.main import create_app

        with patch("app.main.settings") as mock_settings:
            mock_settings.disable_docs = False
            mock_settings.resolved_frontend_dist = dist_with_assets

            app = create_app()
            client = TestClient(app)

            response = client.get("/")

            assert response.status_code == 200
            assert "Cartographer" in response.text

    def test_favicon_route_get(self, dist_with_assets):
        """GET /favicon.png should serve favicon"""
        from app.main import create_app

        with patch("app.main.settings") as mock_settings:
            mock_settings.disable_docs = False
            mock_settings.resolved_frontend_dist = dist_with_assets

            app = create_app()
            client = TestClient(app)

            response = client.get("/favicon.png")

            assert response.status_code == 200
            assert response.headers["content-type"] == "image/png"

    def test_favicon_route_head(self, dist_with_assets):
        """HEAD /favicon.png should work"""
        from app.main import create_app

        with patch("app.main.settings") as mock_settings:
            mock_settings.disable_docs = False
            mock_settings.resolved_frontend_dist = dist_with_assets

            app = create_app()
            client = TestClient(app)

            response = client.head("/favicon.png")

            assert response.status_code == 200

    def test_spa_catch_all_serves_index(self, dist_with_assets):
        """Unknown routes should serve index.html for SPA"""
        from app.main import create_app

        with patch("app.main.settings") as mock_settings:
            mock_settings.disable_docs = False
            mock_settings.resolved_frontend_dist = dist_with_assets

            app = create_app()
            client = TestClient(app)

            response = client.get("/dashboard")

            assert response.status_code == 200
            assert "Cartographer" in response.text

    def test_spa_nested_route_serves_index(self, dist_with_assets):
        """Nested SPA routes should serve index.html"""
        from app.main import create_app

        with patch("app.main.settings") as mock_settings:
            mock_settings.disable_docs = False
            mock_settings.resolved_frontend_dist = dist_with_assets

            app = create_app()
            client = TestClient(app)

            response = client.get("/settings/users")

            assert response.status_code == 200
            assert "Cartographer" in response.text

    def test_static_file_in_dist_root(self, dist_with_assets):
        """Files in dist root should be served directly"""
        from app.main import create_app

        # Create a static file in dist root
        (dist_with_assets / "robots.txt").write_text("User-agent: *\nDisallow: /api/")

        with patch("app.main.settings") as mock_settings:
            mock_settings.disable_docs = False
            mock_settings.resolved_frontend_dist = dist_with_assets

            app = create_app()
            client = TestClient(app)

            response = client.get("/robots.txt")

            assert response.status_code == 200
            assert "User-agent" in response.text

    def test_api_routes_not_caught_by_spa(self, dist_with_assets):
        """API routes should not be caught by SPA catch-all"""
        from app.main import create_app

        with patch("app.main.settings") as mock_settings:
            mock_settings.disable_docs = False
            mock_settings.resolved_frontend_dist = dist_with_assets

            with patch("app.routers.health.http_pool") as mock_pool:
                mock_pool._services = {}

            app = create_app()
            client = TestClient(app)

            # The serve_spa function checks for api/ prefix and returns 404
            # But since routers are registered first, actual API routes work
            # Test that healthz works (which is a real endpoint)
            response = client.get("/healthz")

            # Should be JSON, not HTML
            assert response.status_code == 200
            data = response.json()
            assert "status" in data

    def test_path_traversal_prevented(self, dist_with_assets):
        """Path traversal should be prevented"""
        from app.main import create_app

        # Create a file outside dist
        sensitive_file = dist_with_assets.parent / "sensitive.txt"
        sensitive_file.write_text("SECRET DATA")

        with patch("app.main.settings") as mock_settings:
            mock_settings.disable_docs = False
            mock_settings.resolved_frontend_dist = dist_with_assets

            app = create_app()
            client = TestClient(app)

            # Attempt path traversal
            response = client.get("/../sensitive.txt")

            # Should get index.html (caught by SPA) or 404, not the file contents
            assert "SECRET DATA" not in response.text

    def test_favicon_fallback_to_index(self, dist_with_assets):
        """Missing favicon should fallback to index"""
        from app.main import create_app

        # Remove favicon
        (dist_with_assets / "favicon.png").unlink()

        with patch("app.main.settings") as mock_settings:
            mock_settings.disable_docs = False
            mock_settings.resolved_frontend_dist = dist_with_assets

            app = create_app()
            client = TestClient(app)

            response = client.get("/favicon.png")

            # Should serve index.html as fallback
            assert response.status_code == 200


class TestNoDistDirectory:
    """Tests when dist directory doesn't exist"""

    def test_app_works_without_dist(self):
        """App should work even without dist directory"""
        from app.main import create_app

        with patch("app.main.settings") as mock_settings:
            mock_settings.disable_docs = False
            mock_settings.resolved_frontend_dist = Path("/nonexistent/path")

            with patch("app.routers.health.http_pool") as mock_pool:
                mock_pool._services = {}

            app = create_app()
            client = TestClient(app)

            # API endpoint should work
            response = client.get("/healthz")
            assert response.status_code == 200

    def test_healthz_always_available(self):
        """Healthz should be available regardless of dist"""
        from app.main import create_app

        with patch("app.main.settings") as mock_settings:
            mock_settings.disable_docs = False
            mock_settings.resolved_frontend_dist = Path("/nonexistent/path")

            with patch("app.routers.health.http_pool") as mock_pool:
                mock_pool._services = {}

                app = create_app()
                client = TestClient(app)

                response = client.get("/healthz")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"


class TestAssetsMount:
    """Tests for /assets static file mounting"""

    def test_assets_served(self, tmp_path):
        """Assets directory should be properly mounted"""
        from app.main import create_app

        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()
        (dist_dir / "index.html").write_text("<html></html>")

        assets_dir = dist_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "app.js").write_text("console.log('test');")

        with patch("app.main.settings") as mock_settings:
            mock_settings.disable_docs = False
            mock_settings.resolved_frontend_dist = dist_dir

            app = create_app()
            client = TestClient(app)

            response = client.get("/assets/app.js")

            assert response.status_code == 200
            assert "console.log" in response.text

    def test_missing_asset_returns_404(self, tmp_path):
        """Missing assets should return 404"""
        from app.main import create_app

        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()
        (dist_dir / "index.html").write_text("<html></html>")

        assets_dir = dist_dir / "assets"
        assets_dir.mkdir()

        with patch("app.main.settings") as mock_settings:
            mock_settings.disable_docs = False
            mock_settings.resolved_frontend_dist = dist_dir

            app = create_app()
            client = TestClient(app)

            response = client.get("/assets/nonexistent.js")

            assert response.status_code == 404


class TestStaticRouter:
    """Tests for the static router module"""

    def test_create_static_router_returns_none_for_missing_dist(self):
        """create_static_router should return None if dist doesn't exist"""
        from app.routers.static import create_static_router

        result = create_static_router(Path("/nonexistent/path"))
        assert result is None

    def test_create_static_router_returns_none_without_index(self, tmp_path):
        """create_static_router should return None if index.html missing"""
        from app.routers.static import create_static_router

        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()
        # No index.html

        result = create_static_router(dist_dir)
        assert result is None

    def test_create_static_router_returns_router_with_index(self, tmp_path):
        """create_static_router should return router if dist has index.html"""
        from fastapi import APIRouter

        from app.routers.static import create_static_router

        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()
        (dist_dir / "index.html").write_text("<html></html>")

        result = create_static_router(dist_dir)
        assert isinstance(result, APIRouter)

    def test_mount_assets_returns_false_without_assets(self, tmp_path):
        """mount_assets should return False if assets dir doesn't exist"""
        from fastapi import FastAPI

        from app.routers.static import mount_assets

        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()

        app = FastAPI()
        result = mount_assets(app, dist_dir)
        assert result is False

    def test_mount_assets_returns_true_with_assets(self, tmp_path):
        """mount_assets should return True if assets dir exists"""
        from fastapi import FastAPI

        from app.routers.static import mount_assets

        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()
        (dist_dir / "assets").mkdir()

        app = FastAPI()
        result = mount_assets(app, dist_dir)
        assert result is True
