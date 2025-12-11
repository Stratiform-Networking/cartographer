"""
Notification Service - Main Application

Handles notifications for network events and anomalies across
multiple channels (email, Discord).
"""

import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.notifications import router as notifications_router
from .services.discord_service import discord_service, is_discord_configured
from .services.notification_manager import notification_manager
from .services.anomaly_detector import anomaly_detector
from .services.version_checker import version_checker
from .services.usage_middleware import UsageTrackingMiddleware
from .models import NetworkEvent, NotificationType, NotificationPriority, get_default_priority_for_type

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Data directory for service state
DATA_DIR = Path(os.environ.get("NOTIFICATION_DATA_DIR", "/app/data"))
SERVICE_STATE_FILE = DATA_DIR / "service_state.json"


def _get_service_state() -> dict:
    """Read service state from file"""
    import json
    try:
        if SERVICE_STATE_FILE.exists():
            with open(SERVICE_STATE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read service state: {e}")
    return {"clean_shutdown": False, "last_shutdown": None, "last_startup": None}


def _save_service_state(clean_shutdown: bool):
    """Save service state to file"""
    import json
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        state = {
            "clean_shutdown": clean_shutdown,
            "last_shutdown": datetime.utcnow().isoformat() if clean_shutdown else None,
            "last_startup": datetime.utcnow().isoformat(),
        }
        with open(SERVICE_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save service state: {e}")


async def _send_cartographer_up_notification(previous_state: dict):
    """Send notification that Cartographer is back online"""
    try:
        # Determine downtime message
        last_shutdown = previous_state.get("last_shutdown")
        clean_shutdown = previous_state.get("clean_shutdown", False)
        
        if clean_shutdown and last_shutdown:
            try:
                shutdown_time = datetime.fromisoformat(last_shutdown)
                downtime = datetime.utcnow() - shutdown_time
                downtime_str = f"Service was down for approximately {int(downtime.total_seconds() / 60)} minutes"
            except:
                downtime_str = "Service was restarted"
        elif not clean_shutdown:
            downtime_str = "Service recovered from unexpected shutdown"
        else:
            downtime_str = "Service is now online"
        
        event = NetworkEvent(
            event_type=NotificationType.CARTOGRAPHER_UP,
            priority=get_default_priority_for_type(NotificationType.CARTOGRAPHER_UP),
            title="Cartographer is Back Online",
            message=f"The Cartographer monitoring service has started successfully. {downtime_str}",
            details={
                "service": "cartographer",
                "previous_clean_shutdown": clean_shutdown,
                "startup_time": datetime.utcnow().isoformat(),
            },
        )
        
        # Broadcast to all users who have global Cartographer Up notifications enabled
        results = await notification_manager.broadcast_global_notification(event)
        logger.info(f"Sent cartographer_up notification to {len(results)} users")
        
    except Exception as e:
        logger.error(f"Failed to send cartographer_up notification: {e}")


async def _send_cartographer_down_notification():
    """Send notification that Cartographer is shutting down"""
    try:
        event = NetworkEvent(
            event_type=NotificationType.CARTOGRAPHER_DOWN,
            priority=get_default_priority_for_type(NotificationType.CARTOGRAPHER_DOWN),
            title="Cartographer is Shutting Down",
            message="The Cartographer monitoring service is shutting down for maintenance or restart. You will receive a notification when it comes back online.",
            details={
                "service": "cartographer",
                "shutdown_type": "clean",
                "shutdown_time": datetime.utcnow().isoformat(),
            },
        )
        
        # Broadcast to all users who have global Cartographer Down notifications enabled
        results = await notification_manager.broadcast_global_notification(event)
        logger.info(f"Sent cartographer_down notification to {len(results)} users")
        
    except Exception as e:
        logger.error(f"Failed to send cartographer_down notification: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events"""
    # Startup
    logger.info("Starting Notification Service...")
    
    # Check previous service state
    previous_state = _get_service_state()
    was_clean_shutdown = previous_state.get("clean_shutdown", False)
    
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
    
    # Start scheduled broadcast scheduler
    logger.info("Starting scheduled broadcast scheduler...")
    await notification_manager.start_scheduler()
    
    # Start version checker
    logger.info("Starting version checker...")
    await version_checker.start()
    
    # Mark service as running (not clean shutdown yet)
    _save_service_state(clean_shutdown=False)
    
    # Send cartographer_up notification if this is a recovery from shutdown
    # (Skip on very first startup when there's no previous state file)
    if SERVICE_STATE_FILE.exists() or not was_clean_shutdown:
        # Small delay to ensure all services are ready
        await asyncio.sleep(2)
        await _send_cartographer_up_notification(previous_state)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Notification Service...")
    
    # Send shutdown notification FIRST (before stopping services)
    logger.info("Sending shutdown notification...")
    await _send_cartographer_down_notification()
    
    # Small delay to ensure notification is sent
    await asyncio.sleep(1)
    
    # Save ML model state
    logger.info("Saving ML anomaly detection model state...")
    anomaly_detector.save()
    logger.info("ML model state saved")
    
    # Stop scheduled broadcast scheduler
    await notification_manager.stop_scheduler()
    logger.info("Scheduled broadcast scheduler stopped")
    
    # Stop version checker
    await version_checker.stop()
    logger.info("Version checker stopped")
    
    # Stop Discord bot
    if discord_service._running:
        await discord_service.stop()
        logger.info("Discord bot stopped")
    
    # Mark clean shutdown
    _save_service_state(clean_shutdown=True)


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
    
    # Usage tracking middleware - reports endpoint usage to metrics service
    app.add_middleware(UsageTrackingMiddleware, service_name="notification-service")
    
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

