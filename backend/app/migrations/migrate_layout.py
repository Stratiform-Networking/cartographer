"""
Migration script to move existing JSON layout to the database.

This script:
1. Checks for existing saved_network_layout.json
2. If found and no networks exist in DB, creates a "Default Network"
3. Assigns ownership to the first owner user found in auth-service

Run during application startup or manually:
    python -m app.migrations.migrate_layout
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional
import httpx

from sqlalchemy import select, func

from ..database import async_session_maker, engine, Base
from ..models.network import Network
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_layout_path() -> Path:
    """Get the path to the saved network layout JSON file."""
    # Check Docker volume path first
    data_dir = Path("/app/data")
    if data_dir.exists():
        return data_dir / "saved_network_layout.json"
    # Fallback to project root for local development
    return Path(__file__).resolve().parents[4] / "saved_network_layout.json"


async def _get_owner_user_id() -> Optional[str]:
    """
    Get the user_id of the first owner user from auth-service.
    Returns None if no owner is found.
    """
    auth_service_url = settings.auth_service_url
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Use internal endpoint that doesn't require auth
            response = await client.get(f"{auth_service_url}/api/auth/internal/owner")
            if response.status_code == 200:
                data = response.json()
                owner_id = data.get("user_id")
                if owner_id:
                    logger.info(f"Found owner user: {data.get('username')} ({owner_id})")
                    return owner_id
            elif response.status_code == 404:
                logger.warning("No owner user found in auth service (setup may not be complete)")
            else:
                logger.warning(f"Failed to get owner from auth service: {response.status_code}")
    except Exception as e:
        logger.warning(f"Failed to connect to auth service: {e}")
    
    return None


PLACEHOLDER_USER_ID = "00000000-0000-0000-0000-000000000000"


async def _fix_placeholder_networks() -> bool:
    """
    Fix networks that were created with placeholder user IDs.
    This happens when migration runs before setup is complete.
    
    Returns True if any networks were fixed.
    """
    owner_user_id = await _get_owner_user_id()
    if not owner_user_id:
        return False
    
    async with async_session_maker() as session:
        # Find networks with placeholder user ID
        result = await session.execute(
            select(Network).where(Network.user_id == PLACEHOLDER_USER_ID)
        )
        placeholder_networks = result.scalars().all()
        
        if not placeholder_networks:
            return False
        
        logger.info(f"Found {len(placeholder_networks)} networks with placeholder owner, updating to {owner_user_id}")
        
        for network in placeholder_networks:
            network.user_id = owner_user_id
            logger.info(f"Updated network '{network.name}' (ID: {network.id}) owner to {owner_user_id}")
        
        await session.commit()
        return True


async def migrate_layout_to_database() -> bool:
    """
    Migrate existing JSON layout to the database.
    Also fixes any networks that were created with placeholder user IDs.
    
    Returns True if migration was performed, False if skipped.
    """
    # First, try to fix any networks with placeholder user IDs
    fixed = await _fix_placeholder_networks()
    if fixed:
        logger.info("Fixed placeholder networks")
    
    layout_path = _get_layout_path()
    
    # Check if layout file exists
    if not layout_path.exists():
        logger.info(f"No existing layout file found at {layout_path}, skipping migration")
        return fixed  # Return True if we fixed placeholder networks
    
    logger.info(f"Found existing layout file at {layout_path}")
    
    # Check if any networks already exist in database
    async with async_session_maker() as session:
        result = await session.execute(select(func.count(Network.id)))
        network_count = result.scalar()
        
        if network_count > 0:
            logger.info(f"Database already has {network_count} networks, skipping JSON migration")
            return fixed  # Return True if we fixed placeholder networks
        
        # Load the layout data
        try:
            with open(layout_path, "r") as f:
                layout_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load layout file: {e}")
            return fixed
        
        # Get owner user ID
        owner_user_id = await _get_owner_user_id()
        if not owner_user_id:
            logger.warning("No owner user found, using placeholder ID for migration")
            # Use a placeholder - the network can be claimed later
            owner_user_id = PLACEHOLDER_USER_ID
        
        logger.info(f"Migrating layout to database with owner: {owner_user_id}")
        
        # Create the default network
        network = Network(
            user_id=owner_user_id,
            name="Default Network",
            description="Migrated from previous Cartographer installation",
            layout_data=layout_data,
            is_active=True,
        )
        
        session.add(network)
        await session.commit()
        await session.refresh(network)
        
        logger.info(f"Successfully migrated layout to network ID: {network.id}")
        
        # Optionally rename the old file to indicate migration
        backup_path = layout_path.with_suffix(".json.migrated")
        try:
            layout_path.rename(backup_path)
            logger.info(f"Renamed old layout file to {backup_path}")
        except Exception as e:
            logger.warning(f"Failed to rename old layout file: {e}")
        
        return True


async def run_migration():
    """Run the migration (for command-line execution)."""
    logging.basicConfig(level=logging.INFO)
    
    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Run migration
    result = await migrate_layout_to_database()
    
    if result:
        print("Migration completed successfully!")
    else:
        print("Migration skipped (no file found or networks already exist)")


if __name__ == "__main__":
    asyncio.run(run_migration())

