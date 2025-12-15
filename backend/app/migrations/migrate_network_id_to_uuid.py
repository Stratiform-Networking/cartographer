"""
Migration script to convert network IDs from integer to UUID.

This script:
1. Creates new UUID columns for network_id in all tables
2. Generates UUIDs for existing networks
3. Updates foreign key references
4. Replaces the old integer columns with UUID columns

Run during application startup or manually:
    python -m app.migrations.migrate_network_id_to_uuid

IMPORTANT: This migration must run BEFORE the application uses the new UUID model.
Back up your database before running this migration.
"""

import asyncio
import uuid
import logging
from typing import Dict

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from ..database import async_session_maker, engine

logger = logging.getLogger(__name__)


async def check_column_type(session, table_name: str, column_name: str) -> str:
    """Check the data type of a column."""
    result = await session.execute(text(f"""
        SELECT data_type 
        FROM information_schema.columns 
        WHERE table_name = :table_name 
        AND column_name = :column_name
    """), {"table_name": table_name, "column_name": column_name})
    row = result.fetchone()
    return row[0] if row else None


async def migrate_network_ids_to_uuid() -> bool:
    """
    Migrate network IDs from integer to UUID.
    
    This migration:
    1. Checks if migration is needed (if id column is already UUID, skip)
    2. Creates a mapping of old integer IDs to new UUIDs
    3. Updates the networks table
    4. Updates all foreign key references
    
    Returns True if migration was performed, False if skipped.
    """
    async with async_session_maker() as session:
        # Check if migration is needed
        id_type = await check_column_type(session, "networks", "id")
        
        if id_type is None:
            logger.info("networks table not found, skipping migration")
            return False
        
        if id_type == "uuid":
            logger.info("networks.id is already UUID, skipping migration")
            return False
        
        if id_type not in ("integer", "bigint", "int4", "int8"):
            logger.warning(f"Unexpected column type for networks.id: {id_type}")
            return False
        
        logger.info(f"Starting migration from {id_type} to UUID for network IDs")
        
        try:
            # Step 1: Get all existing network IDs and create UUID mapping
            result = await session.execute(text("SELECT id FROM networks ORDER BY id"))
            existing_ids = [row[0] for row in result.fetchall()]
            
            if not existing_ids:
                logger.info("No existing networks found")
                # Still need to migrate the schema even if no data
            
            # Create mapping: old_id -> new_uuid
            id_mapping: Dict[int, str] = {}
            for old_id in existing_ids:
                id_mapping[old_id] = str(uuid.uuid4())
            
            logger.info(f"Created UUID mapping for {len(id_mapping)} networks")
            
            # Step 2: Add new UUID column to networks table
            await session.execute(text("""
                ALTER TABLE networks 
                ADD COLUMN IF NOT EXISTS new_id UUID
            """))
            await session.commit()
            
            # Step 3: Populate new_id with generated UUIDs
            for old_id, new_uuid in id_mapping.items():
                await session.execute(text("""
                    UPDATE networks SET new_id = :new_uuid WHERE id = :old_id
                """), {"new_uuid": new_uuid, "old_id": old_id})
            await session.commit()
            
            # Step 4: Add new UUID column to network_permissions table
            perm_exists = await check_column_type(session, "network_permissions", "network_id")
            if perm_exists:
                await session.execute(text("""
                    ALTER TABLE network_permissions 
                    ADD COLUMN IF NOT EXISTS new_network_id UUID
                """))
                await session.commit()
                
                # Update references
                for old_id, new_uuid in id_mapping.items():
                    await session.execute(text("""
                        UPDATE network_permissions 
                        SET new_network_id = :new_uuid 
                        WHERE network_id = :old_id
                    """), {"new_uuid": new_uuid, "old_id": old_id})
                await session.commit()
            
            # Step 5: Add new UUID column to network_notification_settings table
            notif_exists = await check_column_type(session, "network_notification_settings", "network_id")
            if notif_exists:
                await session.execute(text("""
                    ALTER TABLE network_notification_settings 
                    ADD COLUMN IF NOT EXISTS new_network_id UUID
                """))
                await session.commit()
                
                # Update references
                for old_id, new_uuid in id_mapping.items():
                    await session.execute(text("""
                        UPDATE network_notification_settings 
                        SET new_network_id = :new_uuid 
                        WHERE network_id = :old_id
                    """), {"new_uuid": new_uuid, "old_id": old_id})
                await session.commit()
            
            # Step 6: Drop old constraints and columns, rename new columns
            # This is done in a specific order to avoid constraint violations
            
            # Drop foreign keys first
            try:
                await session.execute(text("""
                    ALTER TABLE network_permissions 
                    DROP CONSTRAINT IF EXISTS network_permissions_network_id_fkey
                """))
                await session.commit()
            except Exception as e:
                logger.warning(f"Could not drop network_permissions FK: {e}")
                await session.rollback()
            
            try:
                await session.execute(text("""
                    ALTER TABLE network_notification_settings 
                    DROP CONSTRAINT IF EXISTS network_notification_settings_network_id_fkey
                """))
                await session.commit()
            except Exception as e:
                logger.warning(f"Could not drop network_notification_settings FK: {e}")
                await session.rollback()
            
            # Drop primary key constraint on networks
            try:
                await session.execute(text("""
                    ALTER TABLE networks DROP CONSTRAINT IF EXISTS networks_pkey
                """))
                await session.commit()
            except Exception as e:
                logger.warning(f"Could not drop networks primary key: {e}")
                await session.rollback()
            
            # Drop old columns and rename new ones
            # Networks table
            await session.execute(text("ALTER TABLE networks DROP COLUMN IF EXISTS id"))
            await session.execute(text("ALTER TABLE networks RENAME COLUMN new_id TO id"))
            await session.execute(text("ALTER TABLE networks ALTER COLUMN id SET NOT NULL"))
            await session.execute(text("ALTER TABLE networks ADD PRIMARY KEY (id)"))
            await session.commit()
            
            # Network permissions table
            if perm_exists:
                await session.execute(text("""
                    ALTER TABLE network_permissions DROP COLUMN IF EXISTS network_id
                """))
                await session.execute(text("""
                    ALTER TABLE network_permissions RENAME COLUMN new_network_id TO network_id
                """))
                await session.execute(text("""
                    ALTER TABLE network_permissions ALTER COLUMN network_id SET NOT NULL
                """))
                await session.execute(text("""
                    ALTER TABLE network_permissions 
                    ADD CONSTRAINT network_permissions_network_id_fkey 
                    FOREIGN KEY (network_id) REFERENCES networks(id) ON DELETE CASCADE
                """))
                await session.commit()
            
            # Network notification settings table
            if notif_exists:
                await session.execute(text("""
                    ALTER TABLE network_notification_settings DROP COLUMN IF EXISTS network_id
                """))
                await session.execute(text("""
                    ALTER TABLE network_notification_settings RENAME COLUMN new_network_id TO network_id
                """))
                await session.execute(text("""
                    ALTER TABLE network_notification_settings ALTER COLUMN network_id SET NOT NULL
                """))
                await session.execute(text("""
                    ALTER TABLE network_notification_settings 
                    ADD CONSTRAINT network_notification_settings_network_id_fkey 
                    FOREIGN KEY (network_id) REFERENCES networks(id) ON DELETE CASCADE
                """))
                await session.commit()
            
            logger.info("Successfully migrated network IDs from integer to UUID")
            
            # Log the mapping for reference
            if id_mapping:
                logger.info("ID Mapping (old -> new):")
                for old_id, new_uuid in id_mapping.items():
                    logger.info(f"  {old_id} -> {new_uuid}")
            
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            await session.rollback()
            raise


async def run_migration():
    """Run the migration (for command-line execution)."""
    logging.basicConfig(level=logging.INFO)
    
    result = await migrate_network_ids_to_uuid()
    
    if result:
        print("Migration completed successfully!")
    else:
        print("Migration skipped (already using UUID or no table found)")


if __name__ == "__main__":
    asyncio.run(run_migration())

