"""
Network management API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import get_db
from ..dependencies.auth import AuthenticatedUser, require_auth
from ..models.network import Network, NetworkNotificationSettings, NetworkPermission, PermissionRole
from ..schemas import (
    NetworkCreate,
    NetworkLayoutResponse,
    NetworkLayoutSave,
    NetworkNotificationSettingsCreate,
    NetworkNotificationSettingsResponse,
    NetworkResponse,
    NetworkUpdate,
    PermissionCreate,
    PermissionResponse,
)
from ..services.cache_service import CacheService, get_cache
from ..services.network_service import generate_agent_key, get_network_with_access, is_service_token

router = APIRouter(prefix="/networks", tags=["Networks"])
settings = get_settings()


# ============================================================================
# Network CRUD
# ============================================================================


@router.post("", response_model=NetworkResponse, status_code=status.HTTP_201_CREATED)
async def create_network(
    network_data: NetworkCreate,
    current_user: AuthenticatedUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache),
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

    # Invalidate network list cache for this user
    cache_key = cache.make_key("networks", "user", current_user.user_id)
    await cache.delete(cache_key)

    # Build response with ownership info
    response = NetworkResponse.model_validate(network)
    response.owner_id = network.user_id
    response.is_owner = True
    response.permission = None

    return response


def _build_network_response(
    network: Network,
    is_owner: bool,
    permission: PermissionRole | None = None,
) -> NetworkResponse:
    """Build a NetworkResponse from a Network model.

    Args:
        network: The Network model instance
        is_owner: Whether the current user owns this network
        permission: The permission role if shared (None for owners)

    Returns:
        NetworkResponse with ownership info populated
    """
    response = NetworkResponse.model_validate(network)
    response.owner_id = network.user_id
    response.is_owner = is_owner
    response.permission = permission
    return response


@router.get("", response_model=list[NetworkResponse])
async def list_networks(
    current_user: AuthenticatedUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache),
):
    """List all networks accessible to the current user.

    For service tokens (internal service-to-service calls), returns ALL active networks
    in the system to support metrics generation across all networks.
    
    Implements caching with 60s TTL for regular users.
    """
    is_service = is_service_token(current_user.user_id)

    # Service tokens: no caching (always get fresh data for metrics)
    if is_service:
        result = await db.execute(
            select(Network).where(Network.is_active.is_(True)).order_by(Network.created_at.desc())
        )
        all_networks = result.scalars().all()
        return [
            _build_network_response(network, is_owner=False, permission=PermissionRole.EDITOR)
            for network in all_networks
        ]

    # Regular users: cache network list
    cache_key = cache.make_key("networks", "user", current_user.user_id)

    async def fetch_user_networks():
        # Get networks owned by user
        owned_result = await db.execute(
            select(Network)
            .where(Network.user_id == current_user.user_id, Network.is_active.is_(True))
            .order_by(Network.created_at.desc())
        )
        owned_networks = owned_result.scalars().all()

        # Get networks shared with user
        shared_result = await db.execute(
            select(Network, NetworkPermission.role)
            .join(NetworkPermission, Network.id == NetworkPermission.network_id)
            .where(
                NetworkPermission.user_id == current_user.user_id,
                Network.is_active.is_(True),
            )
            .order_by(Network.created_at.desc())
        )
        shared_networks = shared_result.all()

        # Build consolidated response list
        networks = [_build_network_response(network, is_owner=True) for network in owned_networks]
        networks.extend([
            _build_network_response(network, is_owner=False, permission=role)
            for network, role in shared_networks
        ])
        
        # Convert to dict for JSON serialization
        return [net.model_dump() for net in networks]

    # Get from cache or compute
    cached_networks = await cache.get_or_compute(
        cache_key,
        fetch_user_networks,
        ttl=settings.cache_ttl_network_list
    )
    
    # Convert back to Pydantic models
    return [NetworkResponse(**net) for net in cached_networks]


@router.get("/{network_id}", response_model=NetworkResponse)
async def get_network(
    network_id: str,
    current_user: AuthenticatedUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific network by ID."""
    network, is_owner, permission = await get_network_with_access(
        network_id,
        current_user.user_id,
        db,
        is_service=is_service_token(current_user.user_id),
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
    cache: CacheService = Depends(get_cache),
):
    """Update a network's metadata."""
    network, is_owner, permission = await get_network_with_access(
        network_id,
        current_user.user_id,
        db,
        require_write=True,
        is_service=is_service_token(current_user.user_id),
    )

    # Update fields if provided
    if update_data.name is not None:
        network.name = update_data.name
    if update_data.description is not None:
        network.description = update_data.description

    await db.commit()
    await db.refresh(network)

    # Invalidate network list cache for owner
    cache_key = cache.make_key("networks", "user", network.user_id)
    await cache.delete(cache_key)

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
    cache: CacheService = Depends(get_cache),
):
    """Delete a network. Only the owner can delete."""
    network, is_owner, _ = await get_network_with_access(
        network_id,
        current_user.user_id,
        db,
        is_service=is_service_token(current_user.user_id),
    )

    # Only owner can delete
    if not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the network owner can delete the network",
        )

    # Soft delete: mark as inactive
    network.is_active = False
    await db.commit()

    # Invalidate network list cache for owner and all members
    cache_key_owner = cache.make_key("networks", "user", network.user_id)
    await cache.delete(cache_key_owner)
    
    # Also invalidate cache for users with permissions
    perm_result = await db.execute(
        select(NetworkPermission.user_id).where(NetworkPermission.network_id == network_id)
    )
    member_ids = perm_result.scalars().all()
    for member_id in member_ids:
        cache_key_member = cache.make_key("networks", "user", member_id)
        await cache.delete(cache_key_member)
    network, is_owner, _ = await get_network_with_access(
        network_id,
        current_user.user_id,
        db,
        is_service=is_service_token(current_user.user_id),
    )

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
    network, _, _ = await get_network_with_access(
        network_id,
        current_user.user_id,
        db,
        is_service=is_service_token(current_user.user_id),
    )

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
        network_id,
        current_user.user_id,
        db,
        require_write=True,
        is_service=is_service_token(current_user.user_id),
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


@router.get("/{network_id}/permissions", response_model=list[PermissionResponse])
async def list_network_permissions(
    network_id: str,
    current_user: AuthenticatedUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """List all permissions for a network. Only the owner can view."""
    network, is_owner, _ = await get_network_with_access(
        network_id,
        current_user.user_id,
        db,
        is_service=is_service_token(current_user.user_id),
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
    cache: CacheService = Depends(get_cache),
):
    """Share a network with another user. Only the owner can share."""
    network, is_owner, _ = await get_network_with_access(
        network_id,
        current_user.user_id,
        db,
        is_service=is_service_token(current_user.user_id),
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

    # Invalidate cache for the new member
    cache_key = cache.make_key("networks", "user", perm_data.user_id)
    await cache.delete(cache_key)

    return PermissionResponse.model_validate(new_perm)


@router.delete("/{network_id}/permissions/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(
    network_id: str,
    user_id: str,
    current_user: AuthenticatedUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache),
):
    """Remove a user's access to a network. Only the owner can remove access."""
    network, is_owner, _ = await get_network_with_access(
        network_id,
        current_user.user_id,
        db,
        is_service=is_service_token(current_user.user_id),
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

    # Invalidate cache for the removed member
    cache_key = cache.make_key("networks", "user", user_id)
    await cache.delete(cache_key)


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
        network_id,
        current_user.user_id,
        db,
        is_service=is_service_token(current_user.user_id),
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
        network_id,
        current_user.user_id,
        db,
        is_service=is_service_token(current_user.user_id),
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
