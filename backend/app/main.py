"""
Cartographer Backend - FastAPI Application Entry Point.

This module creates and configures the FastAPI application,
including middleware, routers, and lifecycle management.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import init_db
from .migrations.add_performance_indexes import add_performance_indexes
from .migrations.migrate_layout import migrate_layout_to_database
from .migrations.migrate_network_id_to_uuid import migrate_network_ids_to_uuid
from .routers.assistant_proxy import router as assistant_proxy_router
from .routers.auth_proxy import router as auth_proxy_router
from .routers.health import router as health_router
from .routers.health_proxy import router as health_proxy_router
from .routers.mapper import router as mapper_router
from .routers.metrics_proxy import router as metrics_proxy_router
from .routers.networks import router as networks_router
from .routers.notification_proxy import router as notification_proxy_router
from .routers.static import create_static_router, mount_assets
from .services.cache_service import cache_service
from .services.http_client import http_pool, register_all_services
from .services.usage_middleware import UsageTrackingMiddleware

logger = logging.getLogger(__name__)
settings = get_settings()


async def run_migrations() -> None:
    """
    Run database migrations on startup.

    These migrations are non-fatal - the application will continue
    even if they fail, logging warnings for investigation.
    """
    # Migration: Network IDs (integer -> UUID)
    try:
        uuid_migrated = await migrate_network_ids_to_uuid()
        if uuid_migrated:
            logger.info("Network ID UUID migration completed")
    except Exception as e:
        logger.warning(f"Network ID UUID migration failed (non-fatal): {e}")

    # Migration: Existing layouts to database
    try:
        layout_migrated = await migrate_layout_to_database()
        if layout_migrated:
            logger.info("Layout migration completed")
    except Exception as e:
        logger.warning(f"Layout migration failed (non-fatal): {e}")

    # Migration: Performance indexes
    try:
        logger.info("Running performance index migration...")
        await add_performance_indexes()
        logger.info("Performance indexes ensured")
    except Exception as e:
        logger.warning(f"Performance index migration failed (non-fatal): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown tasks:
    - Database initialization
    - Data migrations
    - Cache service initialization
    - HTTP client pool warm-up
    - Graceful shutdown
    """
    # Startup: Initialize database
    logger.info("Starting application - initializing database...")
    await init_db()
    logger.info("Database initialized")

    # Run data migrations
    await run_migrations()

    # Initialize cache service
    logger.info("Initializing cache service...")
    await cache_service.initialize()

    # Register and initialize HTTP client pool
    logger.info("Registering services with HTTP client pool...")
    register_all_services()

    logger.info("Initializing HTTP client pool...")
    await http_pool.initialize_all()

    # Warm up connections to reduce cold start latency
    warm_up_results = await http_pool.warm_up_all()
    ready_count = sum(1 for v in warm_up_results.values() if v)
    logger.info(f"Warm-up complete: {ready_count}/{len(warm_up_results)} services ready")

    yield

    # Shutdown: Close connections gracefully
    logger.info("Shutting down - closing cache service...")
    await cache_service.close()

    logger.info("Shutting down - closing HTTP client pool...")
    await http_pool.close_all()


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="Cartographer Backend",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.disable_docs else "/docs",
        redoc_url=None if settings.disable_docs else "/redoc",
        openapi_url=None if settings.disable_docs else "/openapi.json",
    )

    # CORS middleware - read origins from settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Usage tracking middleware - reports endpoint usage to metrics service
    app.add_middleware(UsageTrackingMiddleware, service_name="backend")

    # Internal health endpoints (no /api prefix)
    app.include_router(health_router)

    # API routes - registered before static file handling
    app.include_router(mapper_router, prefix="/api")
    app.include_router(health_proxy_router, prefix="/api")
    app.include_router(auth_proxy_router, prefix="/api")
    app.include_router(metrics_proxy_router, prefix="/api")
    app.include_router(assistant_proxy_router, prefix="/api")
    app.include_router(notification_proxy_router, prefix="/api")
    app.include_router(networks_router, prefix="/api")

    # Static file serving for production frontend
    dist_path = settings.resolved_frontend_dist
    if dist_path.exists():
        # Mount Vite assets directory
        mount_assets(app, dist_path)

        # Add SPA routes (must be last to act as catch-all)
        static_router = create_static_router(dist_path)
        if static_router:
            app.include_router(static_router)

    return app


app = create_app()
