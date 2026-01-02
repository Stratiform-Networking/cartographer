"""
CLI entrypoint for database migrations.

Usage:
    python -m app.migrations [command]

Commands:
    layout      - Migrate JSON layout file to database
    uuid        - Convert network IDs from integer to UUID
    indexes     - Add performance indexes (CONCURRENTLY)
    all         - Run all migrations in order
    
Examples:
    python -m app.migrations layout
    python -m app.migrations uuid
    python -m app.migrations indexes
    python -m app.migrations all
"""

import asyncio
import logging
import sys

from .add_performance_indexes import add_performance_indexes
from .migrate_layout import run_migration as run_layout_migration
from .migrate_network_id_to_uuid import run_migration as run_uuid_migration

# Configure logging for CLI
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_all_migrations() -> bool:
    """
    Run all migrations in the correct order.
    
    Order:
    1. UUID migration (schema change)
    2. Layout migration (data migration)
    3. Performance indexes (optimization)
    
    Returns:
        True if any migration was performed
    """
    results = []
    
    logger.info("=" * 50)
    logger.info("Running UUID migration...")
    logger.info("=" * 50)
    results.append(await run_uuid_migration())
    
    logger.info("")
    logger.info("=" * 50)
    logger.info("Running layout migration...")
    logger.info("=" * 50)
    results.append(await run_layout_migration())
    
    logger.info("")
    logger.info("=" * 50)
    logger.info("Adding performance indexes...")
    logger.info("=" * 50)
    try:
        await add_performance_indexes()
        results.append(True)
    except Exception as e:
        logger.warning(f"Performance indexes skipped: {e}")
        results.append(False)
    
    return any(results)


def print_usage() -> None:
    """Print CLI usage information."""
    print(__doc__)


def main() -> int:
    """
    Main CLI entrypoint.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    if len(sys.argv) < 2:
        print_usage()
        return 1
    
    command = sys.argv[1].lower()
    
    try:
        if command == "layout":
            result = asyncio.run(run_layout_migration())
            if result:
                print("\n✅ Layout migration completed successfully!")
            else:
                print("\n⏭️  Layout migration skipped (no file found or networks already exist)")
                
        elif command == "uuid":
            result = asyncio.run(run_uuid_migration())
            if result:
                print("\n✅ UUID migration completed successfully!")
            else:
                print("\n⏭️  UUID migration skipped (already using UUID or no table found)")
        
        elif command == "indexes":
            asyncio.run(add_performance_indexes())
            print("\n✅ Performance indexes added successfully!")
                
        elif command == "all":
            result = asyncio.run(run_all_migrations())
            if result:
                print("\n✅ All migrations completed!")
            else:
                print("\n⏭️  All migrations skipped (nothing to migrate)")
                
        elif command in ("-h", "--help", "help"):
            print_usage()
            
        else:
            print(f"Unknown command: {command}")
            print_usage()
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration cancelled by user")
        return 130
    except Exception as e:
        logger.exception(f"Migration failed: {e}")
        print(f"\n❌ Migration failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

