import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .routers.mapper import router as mapper_router
from .routers.health_proxy import router as health_proxy_router
from .routers.auth_proxy import router as auth_proxy_router
from .routers.metrics_proxy import router as metrics_proxy_router
from .routers.assistant_proxy import router as assistant_proxy_router
from .routers.notification_proxy import router as notification_proxy_router
from .routers.networks import router as networks_router
from .services.http_client import http_pool
from .services.usage_middleware import UsageTrackingMiddleware
from .database import init_db
from .migrations.migrate_layout import migrate_layout_to_database

logger = logging.getLogger(__name__)

# Resolve dist path at module level so it's available for route definitions
_default_dist = Path(__file__).resolve().parents[3] / "frontend" / "dist"
DIST_PATH = Path(os.environ.get("FRONTEND_DIST", str(_default_dist)))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown tasks including HTTP client pool warm-up.
    """
    # Startup: Initialize database
    logger.info("Starting application - initializing database...")
    await init_db()
    logger.info("Database initialized")
    
    # Run migration for existing layouts
    try:
        migrated = await migrate_layout_to_database()
        if migrated:
            logger.info("Layout migration completed")
    except Exception as e:
        logger.warning(f"Layout migration failed (non-fatal): {e}")
    
    # Initialize and warm up HTTP client pool
    logger.info("Initializing HTTP client pool...")
    await http_pool.initialize_all()
    
    # Warm up connections to reduce cold start latency
    warm_up_results = await http_pool.warm_up_all()
    ready_count = sum(1 for v in warm_up_results.values() if v)
    logger.info(f"Warm-up complete: {ready_count}/{len(warm_up_results)} services ready")
    
    yield
    
    # Shutdown: Close HTTP client pool gracefully
    logger.info("Shutting down - closing HTTP client pool...")
    await http_pool.close_all()


def create_app() -> FastAPI:
	app = FastAPI(
		title="Cartographer Backend",
		version="0.1.0",
		lifespan=lifespan
	)

	# Allow local dev UIs
	app.add_middleware(
		CORSMiddleware,
		allow_origins=["*"],
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)
	
	# Usage tracking middleware - reports endpoint usage to metrics service
	app.add_middleware(UsageTrackingMiddleware, service_name="backend")

	# API routes - these MUST be registered before static file handling
	app.include_router(mapper_router, prefix="/api")
	app.include_router(health_proxy_router, prefix="/api")
	app.include_router(auth_proxy_router, prefix="/api")
	app.include_router(metrics_proxy_router, prefix="/api")
	app.include_router(assistant_proxy_router, prefix="/api")
	app.include_router(notification_proxy_router, prefix="/api")
	app.include_router(networks_router, prefix="/api")

	# Internal health check endpoint for load balancers and warm-up
	@app.get("/healthz", tags=["internal"])
	async def healthz():
		"""
		Health check endpoint for load balancers.
		Returns service status and HTTP pool state.
		"""
		services_status = {}
		for name, service in http_pool._services.items():
			services_status[name] = {
				"circuit_state": service.circuit_breaker.state.value,
				"failure_count": service.circuit_breaker.failure_count,
			}
		
		return {
			"status": "healthy",
			"services": services_status
		}

	# Serve built frontend if present (for production)
	if DIST_PATH.exists():
		index_file = DIST_PATH / "index.html"
		assets_dir = DIST_PATH / "assets"

		# Mount Vite assets directory
		if assets_dir.exists():
			app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

		if index_file.exists():
			# Explicit favicon route - supports GET and HEAD
			@app.api_route("/favicon.png", methods=["GET", "HEAD"], include_in_schema=False)
			async def serve_favicon():
				favicon_path = DIST_PATH / "favicon.png"
				if favicon_path.exists():
					return FileResponse(
						str(favicon_path),
						media_type="image/png",
						headers={"Cache-Control": "public, max-age=86400"}
					)
				return FileResponse(str(index_file))

			# Serve index.html for root
			@app.get("/", include_in_schema=False)
			async def serve_index():
				return FileResponse(str(index_file))

			# SPA catch-all - must be LAST
			@app.get("/{full_path:path}", include_in_schema=False)
			async def serve_spa(full_path: str):
				# Don't catch /api routes (shouldn't happen due to order, but be safe)
				if full_path.startswith("api/"):
					return {"detail": "Not Found"}
				
				# Check if it's a static file in dist root
				file_path = DIST_PATH / full_path
				if file_path.exists() and file_path.is_file():
					# Security: ensure path is within dist directory
					try:
						file_path.resolve().relative_to(DIST_PATH.resolve())
						return FileResponse(str(file_path))
					except ValueError:
						pass  # Path traversal attempt, serve index.html
				
				# Default: serve index.html for SPA routing
				return FileResponse(str(index_file))

	return app


app = create_app()


