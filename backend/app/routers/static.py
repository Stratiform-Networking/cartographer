"""
Static file serving router for SPA frontend.

Serves the built frontend assets in production when the dist directory exists.
"""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..config import get_settings

settings = get_settings()


def create_static_router(dist_path: Path) -> APIRouter | None:
    """
    Create a router for serving static frontend files.

    Returns None if the dist directory doesn't exist or has no index.html.

    Args:
        dist_path: Path to the frontend dist directory.

    Returns:
        APIRouter configured for SPA serving, or None if not applicable.
    """
    if not dist_path.exists():
        return None

    index_file = dist_path / "index.html"
    if not index_file.exists():
        return None

    router = APIRouter(tags=["static"])

    @router.api_route("/favicon.png", methods=["GET", "HEAD"], include_in_schema=False)
    async def serve_favicon():
        """Serve favicon with caching headers."""
        favicon_path = dist_path / "favicon.png"
        if favicon_path.exists():
            return FileResponse(
                str(favicon_path),
                media_type="image/png",
                headers={"Cache-Control": "public, max-age=86400"},
            )
        return FileResponse(str(index_file))

    @router.get("/", include_in_schema=False)
    async def serve_index():
        """Serve index.html for root path."""
        return FileResponse(str(index_file))

    @router.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """
        SPA catch-all route.

        Serves static files if they exist, otherwise returns index.html
        to allow client-side routing.
        """
        # Don't catch /api routes (shouldn't happen due to order, but be safe)
        if full_path.startswith("api/"):
            return {"detail": "Not Found"}

        # Check if it's a static file in dist root
        file_path = dist_path / full_path
        if file_path.exists() and file_path.is_file():
            # Security: ensure path is within dist directory
            try:
                file_path.resolve().relative_to(dist_path.resolve())
                return FileResponse(str(file_path))
            except ValueError:
                pass  # Path traversal attempt, serve index.html

        # Default: serve index.html for SPA routing
        return FileResponse(str(index_file))

    return router


def mount_assets(app, dist_path: Path) -> bool:
    """
    Mount the Vite assets directory if it exists.

    Args:
        app: FastAPI application instance.
        dist_path: Path to the frontend dist directory.

    Returns:
        True if assets were mounted, False otherwise.
    """
    assets_dir = dist_path / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
        return True
    return False
