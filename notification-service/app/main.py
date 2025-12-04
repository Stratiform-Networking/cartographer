"""
Notification Service - Main Application

Handles notifications for network events and anomalies across
multiple channels (email, Discord).
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.notifications import router as notifications_router
from .services.discord_service import discord_service, is_discord_configured

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events"""
    # Startup
    logger.info("Starting Notification Service...")
    
    # Start Discord bot if configured
    if is_discord_configured():
        logger.info("Starting Discord bot...")
        try:
            success = await discord_service.start()
            if success:
                logger.info("Discord bot started successfully")
            else:
                logger.warning("Discord bot failed to start")
        except Exception as e:
            logger.error(f"Error starting Discord bot: {e}")
    else:
        logger.info("Discord bot not configured (DISCORD_BOT_TOKEN not set)")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Notification Service...")
    
    # Stop Discord bot
    if discord_service._running:
        await discord_service.stop()
        logger.info("Discord bot stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    app = FastAPI(
        title="Cartographer Notification Service",
        description="Notification service for network events and anomalies. "
                    "Supports email (via Resend) and Discord notifications with "
                    "ML-based anomaly detection.",
        version="0.1.0",
        lifespan=lifespan,
    )
    
    # CORS configuration
    allowed_origins = os.environ.get("CORS_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(notifications_router, prefix="/api/notifications")
    
    @app.get("/")
    def root():
        """Root endpoint"""
        return {
            "service": "Cartographer Notification Service",
            "status": "running",
            "version": "0.1.0",
        }
    
    @app.get("/healthz")
    def healthz():
        """Health check endpoint for container orchestration"""
        return {"status": "healthy"}
    
    return app


app = create_app()

