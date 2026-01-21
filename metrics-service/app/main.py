"""
Cartographer Metrics Service

A microservice for publishing consistent network topology metrics
to Redis pub/sub for consumption by other services.

This service:
- Aggregates data from the health service and backend
- Generates comprehensive network topology snapshots
- Publishes metrics to Redis channels
- Provides WebSocket endpoint for real-time updates
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers.metrics import router as metrics_router
from .services.http_client import http_client
from .services.metrics_aggregator import metrics_aggregator
from .services.redis_publisher import redis_publisher
from .services.usage_middleware import UsageTrackingMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown events.

    On startup:
    - Connect to Redis
    - Generate initial snapshot immediately
    - Start the background metrics publishing loop

    On shutdown:
    - Stop publishing
    - Disconnect from Redis
    """
    import asyncio

    # Startup
    logger.info("Starting Cartographer Metrics Service...")

    # Initialize shared HTTP client for service-to-service communication
    await http_client.initialize()
    logger.info("HTTP client initialized with connection pooling")

    # Connect to Redis first
    redis_connected = await redis_publisher.connect()
    if redis_connected:
        logger.info("Connected to Redis successfully")
    else:
        logger.warning("Failed to connect to Redis - will retry on publish")

    # Generate initial snapshots for ALL networks IMMEDIATELY (before starting background loop)
    # This ensures snapshots are available as soon as the service starts accepting requests
    logger.info("Generating initial snapshots for all networks...")
    try:
        # Generate snapshots for all networks in the system
        initial_snapshots = await metrics_aggregator.generate_all_snapshots()
        if initial_snapshots:
            total_nodes = sum(s.total_nodes for s in initial_snapshots.values())
            logger.info(
                f"Initial snapshots ready for {len(initial_snapshots)} networks with {total_nodes} total nodes"
            )
            if redis_connected:
                for network_id, snapshot in initial_snapshots.items():
                    await redis_publisher.store_last_snapshot(snapshot)
                    await redis_publisher.publish_topology_snapshot(snapshot)
                    logger.debug(f"Published initial snapshot for network {network_id}")
        else:
            logger.warning(
                "No initial snapshots generated - networks may not exist yet or have no layouts"
            )
    except Exception as e:
        logger.warning(f"Failed to generate initial snapshots: {e}")

    # Start background publishing loop (will wait for interval before first publish)
    metrics_aggregator.start_publishing(skip_initial=True)
    logger.info("Background metrics publishing started")

    yield

    # Shutdown
    logger.info("Shutting down Cartographer Metrics Service...")

    # Stop publishing
    metrics_aggregator.stop_publishing()
    logger.info("Background publishing stopped")

    # Disconnect from Redis
    await redis_publisher.disconnect()
    logger.info("Disconnected from Redis")

    # Close HTTP client
    await http_client.close()
    logger.info("HTTP client closed")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Cartographer Metrics Service",
        description="""
Network topology metrics publishing service for Cartographer.

This service aggregates network topology and health data from multiple sources
and publishes comprehensive metrics to Redis pub/sub channels for consumption
by other services and real-time dashboards.

## Features

- **Topology Snapshots**: Complete network topology with node metrics
- **Health Status**: Device health, uptime, and connectivity information
- **ISP Metrics**: Gateway test IPs and speed test results
- **Real-time Updates**: WebSocket and Redis pub/sub for live data
- **Node Connections**: Connection graph with speed information

## Redis Channels

- `metrics:topology` - Full topology snapshots and node updates
- `metrics:health` - Health status changes
- `metrics:speedtest` - Speed test results
        """,
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

    # Usage tracking middleware - tracks own endpoint usage
    app.add_middleware(UsageTrackingMiddleware, service_name="metrics-service")

    # Include routers
    app.include_router(metrics_router, prefix="/api")

    # Root endpoint
    @app.get("/")
    def root():
        """Service information endpoint."""
        return {
            "service": "Cartographer Metrics Service",
            "description": "Network topology metrics publishing service",
            "status": "running",
            "version": "0.1.0",
            "endpoints": {
                "metrics": "/api/metrics",
                "docs": "/docs",
                "health": "/healthz",
            },
        }

    # Health check endpoint
    @app.get("/healthz")
    async def healthz():
        """
        Health check endpoint for container orchestration.
        Returns service health status including Redis connectivity.
        """
        redis_info = await redis_publisher.get_connection_info()
        config = metrics_aggregator.get_config()

        return {
            "status": "healthy",
            "redis_connected": redis_info["connected"],
            "publishing_enabled": config["publishing_enabled"],
            "is_publishing": config["is_running"],
        }

    # Readiness check endpoint
    @app.get("/ready")
    async def readyz():
        """
        Readiness check endpoint.
        Returns ready only when the service can fulfill requests.
        """
        redis_info = await redis_publisher.get_connection_info()

        # Service is ready if Redis is connected
        is_ready = redis_info["connected"]

        return {
            "ready": is_ready,
            "redis_connected": redis_info["connected"],
        }

    return app


# Create the application instance
app = create_app()
