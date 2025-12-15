"""
Network management API routes.
"""

import secrets
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.network import Network, NetworkPermission, PermissionRole, NetworkNotificationSettings
from ..schemas import (
    NetworkCreate,
    NetworkUpdate,
    NetworkResponse,
    NetworkLayoutResponse,
    NetworkLayoutSave,
    PermissionCreate,
    PermissionResponse,
    NetworkNotificationSettingsCreate,
    NetworkNotificationSettingsResponse,
)
from ..dependencies.auth import AuthenticatedUser, require_auth, require_write_access

router = APIRouter(prefix="/networks", tags=["Networks"])


def generate_agent_key() -> str:
    """Generate a secure agent key for future cloud sync."""
    return secrets.token_hex(32)


async def get_network_with_access(
    network_id: str,
    user: AuthenticatedUser,
    db: AsyncSession,
    require_write: bool = False,
) -> tuple[Network, bool, Optional[PermissionRole]]:
    """
    Get a network and verify user has access.
    Returns (network, is_owner, permission_role).
    Raises 404 if not found or user has no access.
    
    Service tokens (user_id in ["service", "metrics-service"]) have full access
    to all networks for internal service-to-service operations.
    """
    # Check if this is a service token - services have access to all networks
    is_service = user.user_id in ("service", "metrics-service")
    
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
    is_owner = network.user_id == user.user_id

    if is_owner:
        return network, True, None

    # Check for permission grant
    perm_result = await db.execute(
        select(NetworkPermission).where(
            NetworkPermission.network_id == network_id,
            NetworkPermission.user_id == user.user_id,
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
) -> List[str]:
    """
    Get all user IDs who have access to a network.
    Returns a list of user IDs including:
    - The network owner
    - All users with viewer/editor permissions
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
        select(NetworkPermission.user_id).where(
            NetworkPermission.network_id == network_id
        )
    )
    permission_user_ids = perm_result.scalars().all()
    user_ids.extend(permission_user_ids)

    # Remove duplicates (in case owner somehow has a permission entry)
    return list(set(user_ids))


# ============================================================================
# Network CRUD
# ============================================================================


@router.post("", response_model=NetworkResponse, status_code=status.HTTP_201_CREATED)
async def create_network(
    network_data: NetworkCreate,
    current_user: AuthenticatedUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Create a new network for the current user."""
    # Generate unique agent key for future cloud sync
    agent_key = generate_agent_key()

    network = Network(
        user_id=current_user.user_id,
        name=network_data.name,
        description=network_data.description,
        agent_key=agent_key,
    )
    db.add(network)
    await db.commit()
    await db.refresh(network)

    # Build response with ownership info
    response = NetworkResponse.model_validate(network)
    response.owner_id = network.user_id
    response.is_owner = True
    response.permission = None

    return response


@router.get("", response_model=List[NetworkResponse])
async def list_networks(
    current_user: AuthenticatedUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """List all networks accessible to the current user.
    
    For service tokens (internal service-to-service calls), returns ALL active networks
    in the system to support metrics generation across all networks.
    """
    # Check if this is a service token (user_id will be 'service' or 'metrics-service')
    is_service = current_user.user_id in ("service", "metrics-service")
    
    if is_service:
        # Service tokens get access to ALL networks for metrics generation
        result = await db.execute(
            select(Network)
            .where(Network.is_active == True)
            .order_by(Network.created_at.desc())
        )
        all_networks = result.scalars().all()
        
        response_list = []
        for network in all_networks:
            response = NetworkResponse.model_validate(network)
            response.owner_id = network.user_id
            response.is_owner = False  # Service is not the owner
            response.permission = PermissionRole.EDITOR  # Service has editor access
            response_list.append(response)
        
        return response_list
    
    # Regular user: Get networks owned by user
    owned_result = await db.execute(
        select(Network)
        .where(Network.user_id == current_user.user_id, Network.is_active == True)
        .order_by(Network.created_at.desc())
    )
    owned_networks = owned_result.scalars().all()

    # Get networks shared with user
    shared_result = await db.execute(
        select(Network, NetworkPermission.role)
        .join(NetworkPermission, Network.id == NetworkPermission.network_id)
        .where(
            NetworkPermission.user_id == current_user.user_id,
            Network.is_active == True,
        )
        .order_by(Network.created_at.desc())
    )
    shared_networks = shared_result.all()

    # Build response list
    response_list = []

    for network in owned_networks:
        response = NetworkResponse.model_validate(network)
        response.owner_id = network.user_id
        response.is_owner = True
        response.permission = None
        response_list.append(response)

    for network, role in shared_networks:
        response = NetworkResponse.model_validate(network)
        response.owner_id = network.user_id
        response.is_owner = False
        response.permission = role
        response_list.append(response)

    return response_list


@router.get("/{network_id}", response_model=NetworkResponse)
async def get_network(
    network_id: str,
    current_user: AuthenticatedUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific network by ID."""
    network, is_owner, permission = await get_network_with_access(
        network_id, current_user, db
    )

    response = NetworkResponse.model_validate(network)
    response.owner_id = network.user_id
    response.is_owner = is_owner
    response.permission = permission

    return response


@router.patch("/{network_id}", response_model=NetworkResponse)
async def update_network(
    network_id: str,
    update_data: NetworkUpdate,
    current_user: AuthenticatedUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Update a network's metadata."""
    network, is_owner, permission = await get_network_with_access(
        network_id, current_user, db, require_write=True
    )

    # Update fields if provided
    if update_data.name is not None:
        network.name = update_data.name
    if update_data.description is not None:
        network.description = update_data.description

    await db.commit()
    await db.refresh(network)

    response = NetworkResponse.model_validate(network)
    response.owner_id = network.user_id
    response.is_owner = is_owner
    response.permission = permission

    return response


@router.delete("/{network_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_network(
    network_id: str,
    current_user: AuthenticatedUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Delete a network. Only the owner can delete."""
    network, is_owner, _ = await get_network_with_access(network_id, current_user, db)

    if not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can delete a network",
        )

    await db.delete(network)
    await db.commit()


# ============================================================================
# Network Layout
# ============================================================================


@router.get("/{network_id}/layout", response_model=NetworkLayoutResponse)
async def get_network_layout(
    network_id: str,
    current_user: AuthenticatedUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get the network layout data."""
    network, _, _ = await get_network_with_access(network_id, current_user, db)

    return NetworkLayoutResponse(
        id=network.id,
        name=network.name,
        layout_data=network.layout_data,
        updated_at=network.updated_at,
    )


@router.post("/{network_id}/layout", response_model=NetworkLayoutResponse)
async def save_network_layout(
    network_id: str,
    layout_data: NetworkLayoutSave,
    current_user: AuthenticatedUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Save the network layout data."""
    network, _, _ = await get_network_with_access(
        network_id, current_user, db, require_write=True
    )

    network.layout_data = layout_data.layout_data
    await db.commit()
    await db.refresh(network)

    return NetworkLayoutResponse(
        id=network.id,
        name=network.name,
        layout_data=network.layout_data,
        updated_at=network.updated_at,
    )


# ============================================================================
# Network Permissions
# ============================================================================


@router.get("/{network_id}/permissions", response_model=List[PermissionResponse])
async def list_network_permissions(
    network_id: str,
    current_user: AuthenticatedUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """List all permissions for a network. Only the owner can view."""
    network, is_owner, _ = await get_network_with_access(
        network_id, current_user, db
    )

    # Only owner can view permissions
    if not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the network owner can view sharing settings",
        )

    result = await db.execute(
        select(NetworkPermission)
        .where(NetworkPermission.network_id == network_id)
        .order_by(NetworkPermission.created_at.desc())
    )
    permissions = result.scalars().all()

    return [PermissionResponse.model_validate(p) for p in permissions]


@router.post(
    "/{network_id}/permissions",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_permission(
    network_id: str,
    perm_data: PermissionCreate,
    current_user: AuthenticatedUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Share a network with another user. Only the owner can share."""
    network, is_owner, _ = await get_network_with_access(
        network_id, current_user, db
    )

    # Only owner can share
    if not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the network owner can share the network",
        )

    # Can't share with yourself
    if perm_data.user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot share a network with yourself",
        )

    # Check if permission already exists
    existing = await db.execute(
        select(NetworkPermission).where(
            NetworkPermission.network_id == network_id,
            NetworkPermission.user_id == perm_data.user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already has access to this network",
        )

    # Create permission
    new_perm = NetworkPermission(
        network_id=network_id,
        user_id=perm_data.user_id,
        role=perm_data.role,
    )
    db.add(new_perm)
    await db.commit()
    await db.refresh(new_perm)

    return PermissionResponse.model_validate(new_perm)


@router.delete(
    "/{network_id}/permissions/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_permission(
    network_id: str,
    user_id: str,
    current_user: AuthenticatedUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Remove a user's access to a network. Only the owner can remove access."""
    network, is_owner, _ = await get_network_with_access(
        network_id, current_user, db
    )

    # Only owner can remove access
    if not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the network owner can remove access",
        )

    # Find the permission to delete
    result = await db.execute(
        select(NetworkPermission).where(
            NetworkPermission.network_id == network_id,
            NetworkPermission.user_id == user_id,
        )
    )
    perm_to_delete = result.scalar_one_or_none()

    if not perm_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found",
        )

    await db.delete(perm_to_delete)
    await db.commit()


# ============================================================================
# Network Notification Settings
# ============================================================================


@router.get("/{network_id}/notifications", response_model=NetworkNotificationSettingsResponse)
async def get_network_notification_settings(
    network_id: str,
    current_user: AuthenticatedUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get notification settings for a network. Only owner and editors can view."""
    network, is_owner, permission = await get_network_with_access(
        network_id, current_user, db
    )

    # Owner and editors can view notification settings
    if not is_owner and permission == PermissionRole.VIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot access notification settings",
        )

    # Get or create notification settings
    result = await db.execute(
        select(NetworkNotificationSettings).where(
            NetworkNotificationSettings.network_id == network_id
        )
    )
    settings = result.scalar_one_or_none()

    if not settings:
        # Create default settings
        settings = NetworkNotificationSettings(
            network_id=network_id,
            enabled=True,
            email_enabled=False,
            discord_enabled=False,
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return NetworkNotificationSettingsResponse.model_validate(settings)


@router.put("/{network_id}/notifications", response_model=NetworkNotificationSettingsResponse)
async def update_network_notification_settings(
    network_id: str,
    settings_data: NetworkNotificationSettingsCreate,
    current_user: AuthenticatedUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Update notification settings for a network. Only owner and editors can update."""
    network, is_owner, permission = await get_network_with_access(
        network_id, current_user, db
    )

    # Owner and editors can update notification settings
    if not is_owner and permission == PermissionRole.VIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot modify notification settings",
        )

    # Get or create notification settings
    result = await db.execute(
        select(NetworkNotificationSettings).where(
            NetworkNotificationSettings.network_id == network_id
        )
    )
    settings = result.scalar_one_or_none()

    if not settings:
        settings = NetworkNotificationSettings(network_id=network_id)
        db.add(settings)

    # Update fields
    settings.enabled = settings_data.enabled

    if settings_data.email:
        settings.email_enabled = settings_data.email.enabled
        settings.email_address = settings_data.email.email_address

    if settings_data.discord:
        settings.discord_enabled = settings_data.discord.enabled
        settings.discord_config = {
            "delivery_method": settings_data.discord.delivery_method,
            "discord_user_id": settings_data.discord.discord_user_id,
            "guild_id": settings_data.discord.guild_id,
            "channel_id": settings_data.discord.channel_id,
        }

    if settings_data.preferences:
        settings.preferences = settings_data.preferences.model_dump()

    await db.commit()
    await db.refresh(settings)

    return NetworkNotificationSettingsResponse.model_validate(settings)

