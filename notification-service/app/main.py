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
from .routers.cartographer_status import router as cartographer_status_router
from .routers.user_notifications import router as user_notifications_router
from .routers.user_notifications_send import router as user_notifications_send_router
from .routers.discord_oauth import router as discord_oauth_router
from .services.discord_service import discord_service, is_discord_configured
from .services.notification_manager import notification_manager
from .services.cartographer_status import cartographer_status_service
from .services.anomaly_detector import anomaly_detector
from .services.network_anomaly_detector import network_anomaly_detector_manager
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


async def _send_cartographer_status_notification(event_type: str, downtime_minutes: int = None, message: str = None):
    """
    Send Cartographer status notification directly (without HTTP).
    
    This is called during startup/shutdown when the HTTP server isn't available.
    """
    import uuid
    from .services.email_service import send_notification_email, is_email_configured
    from .services.discord_service import discord_service, is_discord_configured, send_discord_notification
    from .models import DiscordConfig, DiscordDeliveryMethod, DiscordChannelConfig, get_default_priority_for_type
    
    try:
        # Map event type to NotificationType
        if event_type == "up":
            notification_type = NotificationType.CARTOGRAPHER_UP
            downtime_str = ""
            if downtime_minutes:
                downtime_str = f"Service was down for approximately {downtime_minutes} minutes. "
            title = "Cartographer is Back Online"
            default_message = f"{downtime_str}The Cartographer monitoring service is now operational."
        else:
            notification_type = NotificationType.CARTOGRAPHER_DOWN
            title = "Cartographer Service Alert"
            default_message = "The Cartographer monitoring service may be unavailable."
        
        event = NetworkEvent(
            event_type=notification_type,
            priority=get_default_priority_for_type(notification_type),
            title=title,
            message=message or default_message,
            network_id=None,
            details={
                "service": "cartographer",
                "downtime_minutes": downtime_minutes,
                "reported_at": datetime.utcnow().isoformat(),
            },
        )
        
        # Get subscribers
        subscribers = cartographer_status_service.get_subscribers_for_event(notification_type)
        
        if not subscribers:
            logger.info(f"No subscribers found for {event_type} notification")
            return 0
        
        # Check available services
        email_available = is_email_configured()
        discord_available = is_discord_configured()
        
        if not email_available and not discord_available:
            logger.warning("Cannot send Cartographer status notifications: Neither email nor Discord is configured")
            return 0
        
        # Send to each subscriber
        notification_id = str(uuid.uuid4())
        successful = 0
        
        for subscriber in subscribers:
            subscriber_notified = False
            
            # Send via email if enabled
            if subscriber.email_enabled and subscriber.email_address and email_available:
                try:
                    record = await send_notification_email(
                        to_email=subscriber.email_address,
                        event=event,
                        notification_id=notification_id,
                    )
                    if record.success:
                        logger.info(f"✓ Cartographer {event_type} email sent to {subscriber.email_address}")
                        subscriber_notified = True
                    else:
                        logger.error(f"✗ Failed to send email to {subscriber.email_address}: {record.error_message}")
                except Exception as e:
                    logger.error(f"✗ Exception sending email to {subscriber.email_address}: {e}")
            
            # Send via Discord if enabled
            if subscriber.discord_enabled and discord_available:
                try:
                    discord_config = None
                    if subscriber.discord_delivery_method == "channel" and subscriber.discord_channel_id:
                        discord_config = DiscordConfig(
                            enabled=True,
                            delivery_method=DiscordDeliveryMethod.CHANNEL,
                            channel_config=DiscordChannelConfig(
                                guild_id=subscriber.discord_guild_id or "",
                                channel_id=subscriber.discord_channel_id,
                            ),
                        )
                    elif subscriber.discord_delivery_method == "dm" and subscriber.discord_user_id:
                        discord_config = DiscordConfig(
                            enabled=True,
                            delivery_method=DiscordDeliveryMethod.DM,
                            discord_user_id=subscriber.discord_user_id,
                        )
                    
                    if discord_config:
                        record = await send_discord_notification(discord_config, event, notification_id)
                        if record.success:
                            logger.info(f"✓ Cartographer {event_type} Discord sent to user {subscriber.user_id}")
                            subscriber_notified = True
                        else:
                            logger.error(f"✗ Failed to send Discord to user {subscriber.user_id}: {record.error_message}")
                except Exception as e:
                    logger.error(f"✗ Exception sending Discord to user {subscriber.user_id}: {e}")
            
            if subscriber_notified:
                successful += 1
        
        logger.info(f"Cartographer {event_type} notification complete: {successful}/{len(subscribers)} subscribers notified")
        return successful
        
    except Exception as e:
        logger.error(f"Failed to send cartographer_{event_type} notification: {e}", exc_info=True)
        return 0


async def _send_cartographer_up_notification(previous_state: dict):
    """Send notification that Cartographer is back online"""
    # Determine downtime
    last_shutdown = previous_state.get("last_shutdown")
    clean_shutdown = previous_state.get("clean_shutdown", False)
    
    downtime_minutes = None
    if clean_shutdown and last_shutdown:
        try:
            shutdown_time = datetime.fromisoformat(last_shutdown)
            downtime = datetime.utcnow() - shutdown_time
            downtime_minutes = int(downtime.total_seconds() / 60)
        except:
            pass
    
    await _send_cartographer_status_notification("up", downtime_minutes=downtime_minutes)


async def _send_cartographer_down_notification():
    """Send notification that Cartographer is shutting down"""
    await _send_cartographer_status_notification(
        "down",
        message="The Cartographer monitoring service is shutting down for maintenance or restart. You will receive a notification when it comes back online."
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events"""
    # Startup
    logger.info("Starting Notification Service...")
    
    # Run database migrations
    logger.info("Running database migrations...")
    try:
        import subprocess
        import sys
        from pathlib import Path
        
        # Get the app directory (parent of app/)
        app_dir = Path(__file__).parent.parent
        
        # Check if alembic.ini exists
        alembic_ini = app_dir / "alembic.ini"
        if not alembic_ini.exists():
            logger.warning(f"alembic.ini not found at {alembic_ini}, skipping migrations")
        else:
            # First, check if we need to stamp the database (for migration from old version table)
            # This handles the case where tables exist but the new version table doesn't track them
            from .database import async_session_maker, engine
            from sqlalchemy import text
            
            async def check_and_stamp_version():
                """Check if tables exist but version table is empty, and stamp if needed."""
                async with async_session_maker() as session:
                    try:
                        # Check if our version table exists and has entries
                        result = await session.execute(text(
                            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'alembic_version_notification')"
                        ))
                        version_table_exists = result.scalar()
                        
                        if version_table_exists:
                            result = await session.execute(text("SELECT COUNT(*) FROM alembic_version_notification"))
                            version_count = result.scalar()
                        else:
                            version_count = 0
                        
                        # Check if discord_user_links table exists (indicates migrations were run before)
                        result = await session.execute(text(
                            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'discord_user_links')"
                        ))
                        tables_exist = result.scalar()
                        
                        # Check if context_type column exists (indicates 002 migration was applied)
                        has_context_column = False
                        if tables_exist:
                            result = await session.execute(text(
                                "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'discord_user_links' AND column_name = 'context_type')"
                            ))
                            has_context_column = result.scalar()
                        
                        return version_count == 0 and tables_exist, has_context_column
                    except Exception as e:
                        logger.warning(f"Could not check version table state: {e}")
                        return False, False
            
            needs_stamp, has_context = await check_and_stamp_version()
            
            if needs_stamp:
                # Tables exist but version table is empty - stamp to current head
                # Determine which revision to stamp based on schema state
                stamp_revision = "002_discord_link_context" if has_context else "001_create_notification_tables"
                logger.info(f"Tables exist but version table empty. Stamping database at {stamp_revision}...")
                
                stamp_result = subprocess.run(
                    [sys.executable, "-m", "alembic", "stamp", stamp_revision],
                    cwd=str(app_dir),
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=os.environ.copy()
                )
                
                if stamp_result.returncode == 0:
                    logger.info(f"Database stamped at {stamp_revision}")
                else:
                    logger.warning(f"Failed to stamp database: {stamp_result.stderr}")
            
            # Now run migrations normally
            logger.info("Running Alembic migrations...")
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=str(app_dir),
                capture_output=True,
                text=True,
                timeout=60,
                env=os.environ.copy()  # Pass environment variables (including DATABASE_URL)
            )
            
            if result.returncode == 0:
                logger.info("Database migrations completed successfully")
                if result.stdout:
                    logger.debug(f"Migration output: {result.stdout}")
            else:
                logger.error(f"Migration failed with return code {result.returncode}")
                logger.error(f"Migration stderr: {result.stderr}")
                logger.error(f"Migration stdout: {result.stdout}")
                # Don't raise - let service continue if tables already exist
                logger.warning("Migration may have failed, but service will continue. Check database connection.")
                
    except FileNotFoundError:
        logger.warning("Alembic not found, skipping migrations. Install alembic to enable automatic migrations.")
    except subprocess.TimeoutExpired:
        logger.error("Migration timed out after 60 seconds")
    except Exception as e:
        logger.error(f"Failed to run database migrations: {e}", exc_info=True)
        logger.warning("Service will continue, but some features may not work. Please check database connection and migration files.")
    
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
    network_anomaly_detector_manager.save_all()
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
    app.include_router(cartographer_status_router, prefix="/api/cartographer-status")
    app.include_router(user_notifications_router, prefix="/api")
    app.include_router(user_notifications_send_router, prefix="/api")
    app.include_router(discord_oauth_router, prefix="/api")
    
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

