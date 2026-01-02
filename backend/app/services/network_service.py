"""
Network service layer for business logic related to networks.

This module contains extracted business logic from routers/networks.py
to maintain proper layer separation (routers -> services -> repositories).
"""

import secrets

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.network import Network, NetworkPermission, PermissionRole


def generate_agent_key() -> str:
    """Generate a secure agent key for future cloud sync."""
    return secrets.token_hex(32)


async def get_network_with_access(
    network_id: str,
    user_id: str,
    db: AsyncSession,
    *,
    require_write: bool = False,
    is_service: bool = False,
) -> tuple[Network, bool, PermissionRole | None]:
    """
    Get a network and verify user has access.

    Args:
        network_id: The network UUID to look up.
        user_id: The user ID requesting access.
        db: Database session.
        require_write: Whether write access is required.
        is_service: Whether this is a service token (has full access).

    Returns:
        Tuple of (network, is_owner, permission_role).

    Raises:
        HTTPException(404) if not found or user has no access.
        HTTPException(403) if write access required but user only has viewer role.
    """
    # Fetch the network
    result = await db.execute(select(Network).where(Network.id == network_id))
    network = result.scalar_one_or_none()

    if not network:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Network not found",
        )

    # Service tokens have full access to all networks
    if is_service:
        return network, False, PermissionRole.EDITOR

    # Check if user is the owner
    is_owner = network.user_id == user_id

    if is_owner:
        return network, True, None

    # Check for permission grant
    perm_result = await db.execute(
        select(NetworkPermission).where(
            NetworkPermission.network_id == network_id,
            NetworkPermission.user_id == user_id,
        )
    )
    permission = perm_result.scalar_one_or_none()

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Network not found",
        )

    # Check write access if required
    if require_write and permission.role == PermissionRole.VIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access required",
        )

    return network, False, permission.role


async def get_network_member_user_ids(
    network_id: str,
    db: AsyncSession,
) -> list[str]:
    """
    Get all user IDs who have access to a network.

    Returns a list of user IDs including:
    - The network owner
    - All users with viewer/editor permissions

    Args:
        network_id: The network UUID.
        db: Database session.

    Returns:
        List of user IDs with access to the network.

    Raises:
        HTTPException(404) if network not found.
    """
    # Fetch the network
    result = await db.execute(select(Network).where(Network.id == network_id))
    network = result.scalar_one_or_none()

    if not network:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Network not found",
        )

    # Start with the owner
    user_ids = [network.user_id]

    # Add all users with permissions
    perm_result = await db.execute(
        select(NetworkPermission.user_id).where(NetworkPermission.network_id == network_id)
    )
    permission_user_ids = perm_result.scalars().all()
    user_ids.extend(permission_user_ids)

    # Remove duplicates (in case owner somehow has a permission entry)
    return list(set(user_ids))


def is_service_token(user_id: str) -> bool:
    """Check if a user_id represents a service token."""
    return user_id in ("service", "metrics-service")
