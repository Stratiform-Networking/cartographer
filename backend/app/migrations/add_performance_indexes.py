"""
Performance Index Migration

Adds database indexes to improve query performance for high-concurrency scenarios.

Target: Support 200+ concurrent users
Impact: +20-30 concurrent users expected

Indexes added:
- networks.owner_id (WHERE deleted_at IS NULL)
- network_permissions(network_id, user_id)
- embeds.network_id (WHERE deleted_at IS NULL)
- network_layouts.network_id

Run: python -m app.migrations add-performance-indexes
"""

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from ..config import get_settings

logger = logging.getLogger(__name__)


async def add_performance_indexes():
    """Add performance indexes using CONCURRENTLY to avoid table locks."""
    
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    
    indexes = [
        {
            "name": "idx_networks_owner_id_active",
            "sql": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_networks_owner_id_active
                ON networks(user_id) WHERE is_active = true
            """,
            "description": "Speed up network list queries by owner (active networks only)"
        },
        {
            "name": "idx_network_permissions_network_user",
            "sql": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_network_permissions_network_user
                ON network_permissions(network_id, user_id)
            """,
            "description": "Speed up permission lookup queries"
        },
        {
            "name": "idx_network_notification_settings_network",
            "sql": """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_network_notification_settings_network
                ON network_notification_settings(network_id)
            """,
            "description": "Speed up notification settings lookup by network"
        },
    ]
    
    logger.info("=" * 70)
    logger.info("Adding Performance Indexes (CONCURRENTLY - no table locks)")
    logger.info("=" * 70)
    
    try:
        # Need to use autocommit for CREATE INDEX CONCURRENTLY
        async with engine.connect() as conn:
            # Enable autocommit mode
            await conn.execution_options(isolation_level="AUTOCOMMIT")
            
            for index in indexes:
                logger.info(f"\n📊 Creating index: {index['name']}")
                logger.info(f"   Purpose: {index['description']}")
                
                try:
                    await conn.execute(text(index['sql']))
                    logger.info(f"   ✅ Index {index['name']} created successfully")
                except Exception as e:
                    # Index might already exist or error occurred
                    if "already exists" in str(e).lower():
                        logger.info(f"   ⚠️  Index {index['name']} already exists, skipping")
                    else:
                        logger.error(f"   ❌ Failed to create index {index['name']}: {e}")
                        raise
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ Performance indexes added successfully")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"\n❌ Migration failed: {e}")
        raise
    finally:
        await engine.dispose()


def main():
    """Run the migration."""
    asyncio.run(add_performance_indexes())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

