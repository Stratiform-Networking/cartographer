"""
Database configuration and session management.
Matches cartographer-cloud's database setup for compatibility.
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Create async engine with connection retry settings
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,  # Check connection health before use
    pool_size=5,
    max_overflow=10,
    pool_recycle=300,  # Recycle connections after 5 minutes
    pool_timeout=30,  # Wait up to 30s for a connection from pool
    connect_args={
        "server_settings": {"application_name": "cartographer-backend"},
        "timeout": 10,  # Connection timeout in seconds
    },
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables with retry logic for startup."""
    max_retries = 10
    retry_delay = 2.0
    
    for attempt in range(max_retries):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables initialized successfully")
            return
        except Exception as e:
            error_msg = str(e).lower()
            is_transient = (
                "name resolution" in error_msg or
                "connection refused" in error_msg or
                "could not connect" in error_msg or
                "timeout" in error_msg
            )
            
            if is_transient and attempt < max_retries - 1:
                logger.warning(
                    f"Database connection failed (attempt {attempt + 1}/{max_retries}): {e}. "
                    f"Retrying in {retry_delay}s..."
                )
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 30)  # Cap at 30s
            else:
                logger.error(f"Database init failed after {attempt + 1} attempts: {e}")
                raise


async def wait_for_db(timeout: float = 60.0):
    """Wait for database to become available. Called during startup."""
    import time
    start = time.time()
    retry_delay = 1.0
    
    while time.time() - start < timeout:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Database connection established")
            return True
        except Exception as e:
            error_msg = str(e).lower()
            is_transient = (
                "name resolution" in error_msg or
                "connection refused" in error_msg or
                "could not connect" in error_msg or
                "timeout" in error_msg
            )
            
            if is_transient:
                logger.warning(f"Waiting for database... ({e})")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 5)
            else:
                raise
    
    raise TimeoutError(f"Database not available after {timeout}s")

