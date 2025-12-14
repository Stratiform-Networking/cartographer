"""
Auth Service - Main Application

Handles user authentication and authorization for Cartographer.
Uses PostgreSQL database for user and invitation storage.
"""

import os
import logging
import subprocess
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.auth import router as auth_router
from .services.usage_middleware import UsageTrackingMiddleware

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
    logger.info("Starting Auth Service...")
    
    # Run database migrations
    logger.info("Running database migrations...")
    try:
        # Get the app directory (parent of app/)
        app_dir = Path(__file__).parent.parent
        
        # Check if alembic.ini exists
        alembic_ini = app_dir / "alembic.ini"
        if not alembic_ini.exists():
            logger.warning(f"alembic.ini not found at {alembic_ini}, skipping migrations")
        else:
            # First, check if we need to stamp the database (for migration from old version table)
            from .database import async_session_maker
            from sqlalchemy import text
            
            async def check_and_stamp_version():
                """Check if tables exist but version table is empty, and stamp if needed."""
                async with async_session_maker() as session:
                    try:
                        # Check if our version table exists and has entries
                        result = await session.execute(text(
                            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'alembic_version_auth')"
                        ))
                        version_table_exists = result.scalar()
                        
                        if version_table_exists:
                            result = await session.execute(text("SELECT COUNT(*) FROM alembic_version_auth"))
                            version_count = result.scalar()
                        else:
                            version_count = 0
                        
                        # Check if users table exists (indicates migrations were run before)
                        result = await session.execute(text(
                            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users')"
                        ))
                        tables_exist = result.scalar()
                        
                        return version_count == 0 and tables_exist
                    except Exception as e:
                        logger.warning(f"Could not check version table state: {e}")
                        return False
            
            needs_stamp = await check_and_stamp_version()
            
            if needs_stamp:
                # Tables exist but version table is empty - stamp to current head
                logger.info("Tables exist but version table empty. Stamping database at 001_create_users_and_invites...")
                
                stamp_result = subprocess.run(
                    [sys.executable, "-m", "alembic", "stamp", "001_create_users_and_invites"],
                    cwd=str(app_dir),
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=os.environ.copy()
                )
                
                if stamp_result.returncode == 0:
                    logger.info("Database stamped at 001_create_users_and_invites")
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
                # Don't raise an exception - allow service to start
                logger.warning("Migration may have failed, but service will continue. Check database connection.")
                    
    except FileNotFoundError:
        logger.warning("Alembic not found, skipping migrations. Install alembic to enable automatic migrations.")
    except subprocess.TimeoutExpired:
        logger.error("Migration timed out after 60 seconds")
    except Exception as e:
        logger.error(f"Failed to run database migrations: {e}", exc_info=True)
        logger.warning("Service will continue, but some features may not work. Please check database connection and migration files.")
    
    logger.info("Auth Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Auth Service...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    app = FastAPI(
        title="Cartographer Auth Service",
        description="User authentication and authorization microservice for Cartographer. "
                    "Uses PostgreSQL database for user storage, compatible with cartographer-cloud format.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Allow CORS for development and integration with main app
    allowed_origins = os.environ.get("CORS_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Usage tracking middleware - reports endpoint usage to metrics service
    app.add_middleware(UsageTrackingMiddleware, service_name="auth-service")

    # Include routers
    app.include_router(auth_router, prefix="/api/auth")

    @app.get("/")
    def root():
        return {
            "service": "Cartographer Auth Service",
            "status": "running",
            "version": "0.1.0"
        }

    @app.get("/healthz")
    def healthz():
        """Health check endpoint for container orchestration"""
        return {"status": "healthy"}

    return app


app = create_app()
