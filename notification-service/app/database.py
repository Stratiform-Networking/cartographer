"""
Database configuration and session management for notification service.
Uses the same PostgreSQL instance as the main application.
"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings

logger = logging.getLogger(__name__)


# Create async engine with optimized connection pool for high traffic
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,  # Test connections before using
    pool_size=30,  # Increased from 5 - highest traffic service
    max_overflow=40,  # Increased from 10 for peak load handling
    pool_timeout=30,  # Seconds to wait for connection from pool
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all database models in notification service."""

    pass


async def get_db() -> AsyncSession:
    """Dependency to get database session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def _migrate_network_id_to_uuid(conn):
    """Migrate network_id and context_id columns from INTEGER to UUID if needed."""

    # Check if discord_user_links.context_id is INTEGER and convert to UUID
    result = await conn.execute(
        text(
            """
        SELECT data_type
        FROM information_schema.columns
        WHERE table_name = 'discord_user_links'
        AND column_name = 'context_id'
    """
        )
    )
    row = result.fetchone()

    if row and row[0] in ("integer", "bigint"):
        logger.info("Migrating discord_user_links.context_id from INTEGER to UUID...")

        # Add new UUID column
        await conn.execute(
            text(
                """
            ALTER TABLE discord_user_links
            ADD COLUMN IF NOT EXISTS context_id_new UUID
        """
            )
        )

        # We can't reliably map old integer IDs to UUIDs, so we'll clear existing network links
        # Global links (context_id IS NULL) are preserved
        await conn.execute(
            text(
                """
            UPDATE discord_user_links
            SET context_id_new = NULL
            WHERE context_type = 'network'
        """
            )
        )

        # Drop old column and rename new one
        await conn.execute(text("ALTER TABLE discord_user_links DROP COLUMN context_id"))
        await conn.execute(
            text("ALTER TABLE discord_user_links RENAME COLUMN context_id_new TO context_id")
        )

        logger.info("discord_user_links.context_id migration complete")

    # Check if user_network_notification_prefs.network_id is INTEGER and convert to UUID
    result = await conn.execute(
        text(
            """
        SELECT data_type
        FROM information_schema.columns
        WHERE table_name = 'user_network_notification_prefs'
        AND column_name = 'network_id'
    """
        )
    )
    row = result.fetchone()

    if row and row[0] in ("integer", "bigint"):
        logger.info("Migrating user_network_notification_prefs.network_id from INTEGER to UUID...")

        # For this table, we need to drop existing rows since we can't map old IDs
        # Users will need to reconfigure their notification preferences
        await conn.execute(text("DELETE FROM user_network_notification_prefs"))

        # Drop old column and recreate as UUID
        await conn.execute(
            text("ALTER TABLE user_network_notification_prefs DROP COLUMN network_id")
        )
        await conn.execute(
            text(
                """
            ALTER TABLE user_network_notification_prefs
            ADD COLUMN network_id UUID NOT NULL
        """
            )
        )

        # Recreate index
        await conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS ix_user_network_notification_prefs_network_id
            ON user_network_notification_prefs(network_id)
        """
            )
        )

        logger.info("user_network_notification_prefs.network_id migration complete")


async def init_db():
    """Initialize database tables and run migrations."""
    async with engine.begin() as conn:
        # Create tables firs
        await conn.run_sync(Base.metadata.create_all)

        # Run schema migrations for existing tables
        await _migrate_network_id_to_uuid(conn)
