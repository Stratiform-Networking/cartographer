"""
Network management API routes.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from ..config import get_settings
from ..database import get_db
from ..dependencies.auth import AuthenticatedUser, require_auth
from ..models.network import Network, NetworkNotificationSettings, NetworkPermission, PermissionRole
from ..schemas import (
    AgentHealthCheckRequest,
    AgentHealthCheckResponse,
    AgentSyncRequest,
    AgentSyncResponse,
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
from ..services import health_proxy_service
from ..services.cache_service import CacheService, get_cache
from ..services.network_service import generate_agent_key, get_network_with_access, is_service_token

router = APIRouter(prefix="/networks", tags=["Networks"])
settings = get_settings()


# ============================================================================
# Network CRUD
# ============================================================================


async def check_network_limit(user_id: str, user_role: str, auth_header: str | None) -> None:
    """
    Check if user can create another network by calling auth-service.
    Raises HTTPException with 403 if limit exceeded.
    """
    import json
    import logging

    from ..services.http_client import http_pool

    logger = logging.getLogger(__name__)

    headers = {"Content-Type": "application/json"}
    if auth_header:
        headers["Authorization"] = auth_header

    try:
        response = await http_pool.request(
            service_name="auth",
            method="GET",
            path="/api/auth/network-limit",
            headers=headers,
            timeout=10.0,
        )

        # http_pool returns JSONResponse, extract content
        if response.status_code != 200:
            logger.warning(f"Network limit check failed with status {response.status_code}")
            # Fail closed - don't allow network creation if we can't verify limit
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to verify network limit. Please try again.",
            )

        # Parse response body
        status_data = json.loads(response.body)

        # Check if limit is exceeded
        if status_data.get("is_exempt"):
            return  # Exempt users can always create networks

        remaining = status_data.get("remaining", 0)
        limit = status_data.get("limit", 1)

        if remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Network limit reached. You can have a maximum of {limit} network(s).",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check network limit: {e}")
        # Fail closed - don't allow network creation if we can't verify limit
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify network limit. Please try again.",
        )


@router.post("", response_model=NetworkResponse, status_code=status.HTTP_201_CREATED)
async def create_network(
    request: Request,
    network_data: NetworkCreate,
    current_user: AuthenticatedUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache),
):
    """Create a new network for the current user."""
    # Check network limit before creating
    auth_header = request.headers.get("Authorization")
    await check_network_limit(current_user.user_id, current_user.role, auth_header)

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
        networks.extend(
            [
                _build_network_response(network, is_owner=False, permission=role)
                for network, role in shared_networks
            ]
        )

        # Convert to dict for JSON serialization
        return [net.model_dump() for net in networks]

    # Get from cache or compute
    cached_networks = await cache.get_or_compute(
        cache_key, fetch_user_networks, ttl=settings.cache_ttl_network_list
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


# ============================================================================
# Agent Sync
# ============================================================================


# Device role classification patterns (similar to lan_mapper.sh)
_ROLE_PATTERNS: dict[str, list[str]] = {
    "gateway/router": ["routerboard", "mikrotik", "router", "gateway"],
    "switch/ap": [
        "tl-sg",
        "tp-link",
        "tplink",
        "unifi",
        "cisco",
        "netgear",
        "switch",
        "ubiquiti",
        "aruba",
        "meraki",
    ],
    "firewall": ["firewalla", "pfsense", "opnsense", "fortinet", "sophos", "watchguard"],
    "nas": ["nas", "synology", "qnap", "ugreen", "drobo", "netgear-readynas"],
    "server": [
        "server",
        "debian",
        "ubuntu",
        "centos",
        "redhat",
        "fedora",
        "proxmox",
        "esxi",
        "vmware",
    ],
    "service": [
        "jellyfin",
        "plex",
        "grafana",
        "prometheus",
        "postgres",
        "mysql",
        "redis",
        "docker",
        "portainer",
        "home-assistant",
        "homeassistant",
        "pihole",
        "adguard",
    ],
}

# Group assignments for each role
_ROLE_TO_GROUP: dict[str, str] = {
    "gateway/router": "Infrastructure",  # Non-primary routers go to Infrastructure
    "switch/ap": "Infrastructure",
    "firewall": "Infrastructure",
    "nas": "Servers",
    "server": "Servers",
    "service": "Servers",
    "client": "Clients",
    "unknown": "Clients",
}


def _classify_device_role(device, is_gateway_ip: bool = False) -> str:
    """Classify a device's role based on hostname patterns, device_type, and gateway flag.

    Args:
        device: Device object with hostname, device_type, and is_gateway fields
        is_gateway_ip: Whether this device's IP matches the network gateway

    Returns:
        Role string (e.g., "gateway/router", "switch/ap", "client")
    """
    # Explicit gateway flag takes precedence
    if device.is_gateway or is_gateway_ip:
        return "gateway/router"

    # Check device_type from OUI/vendor inference (set by agent)
    if device.device_type:
        role = _map_device_type_to_role(device.device_type)
        if role != "client":
            return role

    hostname = (device.hostname or "").lower()

    # Check hostname against role patterns
    for role, patterns in _ROLE_PATTERNS.items():
        if any(pattern in hostname for pattern in patterns):
            return role

    return "client"


def _get_group_for_role(role: str) -> str:
    """Get the group name for a device role.

    Args:
        role: Device role string

    Returns:
        Group name (Infrastructure, Servers, Clients) or "root" for gateways
    """
    return _ROLE_TO_GROUP.get(role, "Clients")


def _ensure_groups_exist(root: dict) -> dict[str, dict]:
    """Ensure group nodes exist under the root node.

    Args:
        root: Root node of the layout tree

    Returns:
        Dictionary mapping group names to group nodes
    """
    groups: dict[str, dict] = {}
    existing_children = root.get("children", [])

    # Find existing group nodes
    for child in existing_children:
        if child.get("role") == "group":
            group_name = child.get("name", "")
            groups[group_name] = child

    # Create missing groups
    for group_name in ["Infrastructure", "Servers", "Clients"]:
        if group_name not in groups:
            group_node = {
                "id": f"group:{group_name.lower()}",
                "name": group_name,
                "role": "group",
                "children": [],
            }
            groups[group_name] = group_node
            existing_children.append(group_node)

    root["children"] = existing_children
    return groups


def _find_device_in_groups(groups: dict[str, dict], ip: str) -> dict | None:
    """Find a device node by IP within all groups.

    Args:
        groups: Dictionary of group nodes
        ip: IP address to search for

    Returns:
        Device node if found, None otherwise
    """
    for group in groups.values():
        for child in group.get("children", []):
            if child.get("ip") == ip:
                return child
    return None


def _update_root_with_gateway(root: dict, gateway_device, now: str) -> bool:
    """Update the root node with gateway device information.

    Args:
        root: Root node to update
        gateway_device: Gateway device from sync data
        now: Current timestamp

    Returns:
        True if root was updated, False otherwise
    """
    # Check if root is a placeholder (has no real device info)
    root_has_device_info = root.get("ip") and root.get("mac")

    # Only skip update if root already has real device info AND it's a different device
    if root_has_device_info and root.get("ip") != gateway_device.ip:
        return False

    root["ip"] = gateway_device.ip
    root["hostname"] = gateway_device.hostname
    root["mac"] = gateway_device.mac
    root["vendor"] = gateway_device.vendor
    root["deviceType"] = gateway_device.device_type

    # Use hostname, then vendor, then IP for display name
    display_name = gateway_device.hostname or gateway_device.vendor or gateway_device.ip
    root["name"] = (
        f"{gateway_device.ip} ({display_name})"
        if display_name != gateway_device.ip
        else gateway_device.ip
    )
    root["role"] = "gateway/router"
    root["updatedAt"] = now
    root["lastSeenAt"] = now
    if gateway_device.response_time_ms is not None:
        root["lastResponseMs"] = gateway_device.response_time_ms
    return True


def _build_nodes_by_ip_with_groups(root: dict, groups: dict[str, dict]) -> dict[str, dict]:
    """Build a map of all nodes indexed by IP, including grouped devices.

    Args:
        root: Root node of the layout
        groups: Dictionary of group nodes

    Returns:
        Dictionary mapping IP addresses to device nodes
    """
    nodes_by_ip: dict[str, dict] = {}

    # Include root if it has an IP
    if root.get("ip"):
        nodes_by_ip[root["ip"]] = root

    # Include devices in groups
    for group in groups.values():
        for child in group.get("children", []):
            if child.get("ip"):
                nodes_by_ip[child["ip"]] = child

    # Include legacy flat devices directly under root
    for child in root.get("children", []):
        if child.get("role") != "group" and child.get("ip"):
            nodes_by_ip[child["ip"]] = child

    return nodes_by_ip


def _migrate_legacy_devices(root: dict, groups: dict[str, dict]) -> None:
    """Migrate devices from legacy flat structure into proper groups.

    Args:
        root: Root node containing children to migrate
        groups: Dictionary of group nodes to migrate devices into
    """
    new_root_children = []
    root_ip = root.get("ip")

    for child in root.get("children", []):
        if child.get("role") == "group":
            new_root_children.append(child)
        elif child.get("ip") and child.get("ip") != root_ip:
            # Migrate device to appropriate group
            device_role = child.get("role", "client")
            target_group_name = _get_group_for_role(device_role)
            target_group = groups.get(target_group_name, groups["Clients"])
            if child not in target_group.get("children", []):
                child["parentId"] = target_group["id"]
                target_group["children"].append(child)

    root["children"] = new_root_children


def _initialize_layout_data(network_name: str, existing_data: dict | None) -> dict:
    """Initialize or retrieve layout data structure."""
    if existing_data:
        return existing_data

    return {
        "version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "positions": {},
        "root": {
            "id": "root",
            "name": network_name,
            "role": "gateway/router",
            "children": [],
        },
    }


def _ensure_root_node(layout_data: dict, network_name: str) -> dict:
    """Ensure layout has a valid root node with children list."""
    root = layout_data.get("root")
    if not root:
        root = {
            "id": "root",
            "name": network_name,
            "role": "gateway/router",
            "children": [],
        }
        layout_data["root"] = root

    if "children" not in root:
        root["children"] = []

    return root


def _build_nodes_by_ip(root: dict) -> dict[str, dict]:
    """Build a map of all nodes indexed by IP address."""

    def find_all_nodes(node: dict, by_ip: dict):
        """Recursively find all nodes and index by IP."""
        if node.get("ip"):
            by_ip[node["ip"]] = node
        for child in node.get("children", []):
            find_all_nodes(child, by_ip)

    nodes_by_ip: dict[str, dict] = {}
    find_all_nodes(root, nodes_by_ip)
    return nodes_by_ip


def _update_existing_device(existing_node: dict, device, now: str) -> None:
    """Update an existing device node with new scan data."""
    if device.hostname and not existing_node.get("hostname"):
        existing_node["hostname"] = device.hostname
    if device.mac and not existing_node.get("mac"):
        existing_node["mac"] = device.mac
    # Update vendor info if not already set
    if device.vendor and not existing_node.get("vendor"):
        existing_node["vendor"] = device.vendor
    if device.device_type and not existing_node.get("deviceType"):
        existing_node["deviceType"] = device.device_type
    # Update display name if it was just the IP and we now have vendor
    if (
        existing_node.get("name") == existing_node.get("ip")
        and not existing_node.get("hostname")
        and device.vendor
    ):
        existing_node["name"] = device.vendor
    existing_node["updatedAt"] = now
    existing_node["lastSeenAt"] = now
    if device.response_time_ms is not None:
        existing_node["lastResponseMs"] = device.response_time_ms


def _create_new_device_node(device, parent_id: str, now: str, role: str | None = None) -> dict:
    """Create a new device node from scan data.

    Args:
        device: Device object from scan data
        parent_id: ID of the parent node (root or group)
        now: Current timestamp
        role: Pre-classified device role (if None, uses is_gateway flag)

    Returns:
        New device node dictionary
    """
    if role is None:
        # Use device_type from agent if available, otherwise infer from is_gateway
        if device.device_type:
            role = _map_device_type_to_role(device.device_type)
        else:
            role = "gateway/router" if device.is_gateway else "client"

    # Use hostname, then vendor (manufacturer), then IP as display name
    display_name = device.hostname or device.vendor or device.ip

    new_node = {
        "id": str(uuid.uuid4()),
        "name": display_name,
        "ip": device.ip,
        "hostname": device.hostname,
        "mac": device.mac,
        "vendor": device.vendor,
        "deviceType": device.device_type,
        "role": role,
        "parentId": parent_id,
        "createdAt": now,
        "updatedAt": now,
        "lastSeenAt": now,
        "monitoringEnabled": True,
        "children": [],
    }
    if device.response_time_ms is not None:
        new_node["lastResponseMs"] = device.response_time_ms
    return new_node


def _map_device_type_to_role(device_type: str) -> str:
    """Map device type from OUI inference to network role.

    Note: "router" type is only assigned when a device is detected as the network gateway.
    Network equipment vendors (Cisco, TP-Link, etc.) are classified as "network_device"
    since they make switches, APs, and other devices - not just routers.
    """
    mapping = {
        "router": "gateway/router",
        "network_device": "switch/ap",  # Generic network equipment (switch, AP, etc.)
        "firewall": "firewall",
        "server": "server",
        "service": "service",
        "nas": "nas",
        "apple": "client",
        "computer": "client",
        "mobile": "client",
        "gaming": "client",
        "iot": "client",
        "printer": "client",
    }
    return mapping.get(device_type, "client")


def _process_device_sync(
    device, gateway_ip: str | None, groups: dict, nodes_by_ip: dict, now: str
) -> tuple[int, int]:
    """Process a single device during sync.

    Args:
        device: Device from sync data
        gateway_ip: IP of the gateway device (to skip)
        groups: Dictionary of group nodes
        nodes_by_ip: Map of existing devices by IP
        now: Current timestamp

    Returns:
        Tuple of (devices_added, devices_updated) counts
    """
    # Skip gateway device (already handled as root)
    if gateway_ip and device.ip == gateway_ip:
        return 0, 0

    role = _classify_device_role(device)
    target_group_name = _get_group_for_role(role)
    existing = nodes_by_ip.get(device.ip)

    if existing:
        _update_existing_device(existing, device, now)
        if existing.get("role") == "client" and role != "client":
            existing["role"] = role
        return 0, 1

    target_group = groups.get(target_group_name, groups["Clients"])
    new_node = _create_new_device_node(device, target_group["id"], now, role)
    target_group["children"].append(new_node)
    nodes_by_ip[device.ip] = new_node
    return 1, 0


def _flag_layout_modified_if_needed(network: Network) -> None:
    """
    Mark layout_data as dirty for SQLAlchemy JSON persistence.

    During unit tests we sometimes pass a MagicMock(spec=Network) that isn't
    SQLAlchemy-instrumented (no ``_sa_instance_state``). In that case the manual
    flagging is unnecessary, so we safely no-op.
    """
    try:
        flag_modified(network, "layout_data")
    except (AttributeError, InvalidRequestError):
        return


@router.post("/{network_id}/scan", response_model=AgentSyncResponse)
async def sync_agent_scan(
    network_id: str,
    sync_data: AgentSyncRequest,
    current_user: AuthenticatedUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Sync device scan data from Cartographer Agent.

    Merges discovered devices into the network's layout_data:
    - Gateway device becomes the root node
    - Devices are classified by role (switch, server, client, etc.)
    - Devices are organized into groups (Infrastructure, Servers, Clients)
    - Existing devices (matched by IP) are updated with latest data
    - Device positions are preserved if they were previously set

    This endpoint is called by the cloud backend when proxying agent sync requests.
    """
    network, is_owner, permission = await get_network_with_access(
        network_id,
        current_user.user_id,
        db,
        require_write=True,
        is_service=is_service_token(current_user.user_id),
    )

    layout_data = _initialize_layout_data(network.name, network.layout_data)
    root = _ensure_root_node(layout_data, network.name)
    now = datetime.now(timezone.utc).isoformat()

    devices_added = 0
    devices_updated = 0

    # Handle gateway device - first try explicit is_gateway flag
    gateway_device = next((d for d in sync_data.devices if d.is_gateway), None)

    # Fallback: if no explicit gateway, look for a router by device_type (from OUI)
    # Use fallback if:
    # - Root has no IP yet (placeholder)
    # - OR root's name equals the network name (still a placeholder with just the name)
    root_is_placeholder = (
        not root.get("ip")
        or root.get("name") == network.name
        or root.get("name") == layout_data.get("root", {}).get("name", network.name)
    )
    if not gateway_device and root_is_placeholder:
        gateway_device = next(
            (d for d in sync_data.devices if d.device_type == "router"),
            None,
        )

    gateway_ip = None
    if gateway_device and _update_root_with_gateway(root, gateway_device, now):
        devices_updated += 1
        gateway_ip = gateway_device.ip

    # Setup groups and device index
    groups = _ensure_groups_exist(root)
    nodes_by_ip = _build_nodes_by_ip_with_groups(root, groups)

    # Process each device
    for device in sync_data.devices:
        added, updated = _process_device_sync(device, gateway_ip, groups, nodes_by_ip, now)
        devices_added += added
        devices_updated += updated

    # Migrate legacy flat structure and update metadata
    _migrate_legacy_devices(root, groups)
    layout_data["version"] = layout_data.get("version", 0) + 1
    layout_data["timestamp"] = now

    # Save updated layout - must use flag_modified for SQLAlchemy to detect JSON changes
    network.layout_data = layout_data
    _flag_layout_modified_if_needed(network)
    network.last_sync_at = datetime.now(timezone.utc)
    await db.commit()

    return AgentSyncResponse(
        success=True,
        devices_received=len(sync_data.devices),
        devices_added=devices_added,
        devices_updated=devices_updated,
        message=f"Synced {devices_added} new and {devices_updated} existing devices",
    )


@router.post("/{network_id}/health", response_model=AgentHealthCheckResponse)
async def sync_agent_health(
    network_id: str,
    health_data: AgentHealthCheckRequest,
    current_user: AuthenticatedUser = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """
    Sync device health check data from Cartographer Agent.

    Updates device health status in the network's layout_data:
    - Marks devices as reachable/unreachable
    - Records latest response time
    - Updates lastSeenAt timestamp for reachable devices

    This endpoint is called by the cloud backend when proxying agent health data.
    """
    network, is_owner, permission = await get_network_with_access(
        network_id,
        current_user.user_id,
        db,
        require_write=True,
        is_service=is_service_token(current_user.user_id),
    )

    if not network.layout_data:
        return AgentHealthCheckResponse(
            success=True,
            results_received=len(health_data.results),
            results_applied=0,
            message="No layout data to update",
        )

    layout_data = network.layout_data
    root = layout_data.get("root")
    if not root:
        return AgentHealthCheckResponse(
            success=True,
            results_received=len(health_data.results),
            results_applied=0,
            message="No root node in layout",
        )

    # Build a map of nodes by IP
    nodes_by_ip = _build_nodes_by_ip(root)

    now = datetime.now(timezone.utc).isoformat()
    results_applied = 0

    for result in health_data.results:
        node = nodes_by_ip.get(result.ip)
        if not node:
            continue

        # Update health status
        node["healthStatus"] = "healthy" if result.reachable else "unreachable"
        node["lastHealthCheck"] = now

        if result.reachable:
            node["lastSeenAt"] = now
            if result.response_time_ms is not None:
                node["lastResponseMs"] = result.response_time_ms
        else:
            # Increment consecutive failures
            node["consecutiveFailures"] = node.get("consecutiveFailures", 0) + 1

        results_applied += 1

    # Update layout metadata
    layout_data["version"] = layout_data.get("version", 0) + 1
    layout_data["timestamp"] = now
    layout_data["lastHealthCheck"] = now

    # Save updated layout - must use flag_modified for SQLAlchemy to detect JSON changes
    network.layout_data = layout_data
    _flag_layout_modified_if_needed(network)
    await db.commit()

    # Also forward health data to the health-service to update its cache
    # This ensures the frontend's real-time health metrics are updated
    try:
        await health_proxy_service.sync_agent_health(
            network_id=network_id,
            timestamp=health_data.timestamp.isoformat(),
            results=[
                {
                    "ip": r.ip,
                    "reachable": r.reachable,
                    "response_time_ms": r.response_time_ms,
                }
                for r in health_data.results
            ],
        )
    except Exception:
        # Don't fail the main request if health-service is unavailable
        pass

    return AgentHealthCheckResponse(
        success=True,
        results_received=len(health_data.results),
        results_applied=results_applied,
        message=f"Updated health status for {results_applied} devices",
    )
