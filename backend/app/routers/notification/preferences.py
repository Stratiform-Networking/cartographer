"""
Notification preferences router.

Handles all notification preference endpoints:
- Per-network preferences
- Global preferences
- User-specific preferences
- Legacy preferences (deprecated)

Performance optimizations:
- Redis caching for GET endpoints (30 second TTL per user/network)
- Cache invalidation on PUT/DELETE
"""

import json
from fastapi import APIRouter, Depends, Request

from ...dependencies import AuthenticatedUser, require_auth
from ...services.cache_service import CacheService, get_cache
from ...services.proxy_service import proxy_notification_request

router = APIRouter(tags=["notification-preferences"])


# ==================== Per-Network Preferences ====================


@router.get("/networks/{network_id}/preferences")
async def get_network_preferences(
    network_id: str,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Get notification preferences for a specific network."""
    return await proxy_notification_request(
        "GET",
        f"/networks/{network_id}/preferences",
        headers={"X-User-Id": user.user_id},
    )


@router.put("/networks/{network_id}/preferences")
async def update_network_preferences(
    network_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Update notification preferences for a specific network."""
    body = await request.json()
    return await proxy_notification_request(
        "PUT",
        f"/networks/{network_id}/preferences",
        json_body=body,
        headers={"X-User-Id": user.user_id},
    )


@router.delete("/networks/{network_id}/preferences")
async def delete_network_preferences(
    network_id: str,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Delete notification preferences for a network (reset to defaults)."""
    return await proxy_notification_request(
        "DELETE",
        f"/networks/{network_id}/preferences",
        headers={"X-User-Id": user.user_id},
    )


# ==================== Global Preferences (Cartographer Up/Down) ====================


@router.get("/global/preferences")
async def get_global_preferences(
    user: AuthenticatedUser = Depends(require_auth),
    cache: CacheService = Depends(get_cache),
):
    """Get global notification preferences for the current user (Cartographer Up/Down). Cached for 30 seconds."""
    cache_key = cache.make_key("notifications", "global", "preferences", user.user_id)

    async def fetch_global_preferences():
        response = await proxy_notification_request(
            "GET",
            "/global/preferences",
            headers={"X-User-Id": user.user_id},
        )
        if hasattr(response, "body"):
            return json.loads(response.body)
        return response

    return await cache.get_or_compute(cache_key, fetch_global_preferences, ttl=30)


@router.put("/global/preferences")
async def update_global_preferences(
    request: Request,
    user: AuthenticatedUser = Depends(require_auth),
    cache: CacheService = Depends(get_cache),
):
    """Update global notification preferences for the current user (Cartographer Up/Down)."""
    body = await request.json()
    # Invalidate cache on update
    cache_key = cache.make_key("notifications", "global", "preferences", user.user_id)
    await cache.delete(cache_key)
    return await proxy_notification_request(
        "PUT",
        "/global/preferences",
        json_body=body,
        headers={"X-User-Id": user.user_id},
    )


# ==================== User-Specific Network Preferences ====================


@router.get("/users/me/networks/{network_id}/preferences")
async def get_user_network_preferences(
    network_id: str,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Get current user's notification preferences for a specific network."""
    return await proxy_notification_request(
        "GET",
        f"/users/{user.user_id}/networks/{network_id}/preferences",
        use_user_path=True,
    )


@router.put("/users/me/networks/{network_id}/preferences")
async def update_user_network_preferences(
    network_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Update current user's notification preferences for a network."""
    body = await request.json()
    return await proxy_notification_request(
        "PUT",
        f"/users/{user.user_id}/networks/{network_id}/preferences",
        json_body=body,
        use_user_path=True,
    )


@router.delete("/users/me/networks/{network_id}/preferences")
async def delete_user_network_preferences(
    network_id: str,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Delete current user's network notification preferences (reset to defaults)."""
    return await proxy_notification_request(
        "DELETE",
        f"/users/{user.user_id}/networks/{network_id}/preferences",
        use_user_path=True,
    )


# ==================== User-Specific Global Preferences ====================


@router.get("/users/me/global/preferences")
async def get_user_global_preferences(
    user: AuthenticatedUser = Depends(require_auth),
):
    """Get current user's global notification preferences."""
    return await proxy_notification_request(
        "GET",
        f"/users/{user.user_id}/global/preferences",
        use_user_path=True,
    )


@router.put("/users/me/global/preferences")
async def update_user_global_preferences(
    request: Request,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Update current user's global notification preferences."""
    body = await request.json()
    return await proxy_notification_request(
        "PUT",
        f"/users/{user.user_id}/global/preferences",
        json_body=body,
        use_user_path=True,
    )


# ==================== Legacy Preferences (deprecated) ====================


@router.get("/preferences")
async def get_preferences(
    user: AuthenticatedUser = Depends(require_auth),
    cache: CacheService = Depends(get_cache),
):
    """DEPRECATED: Get notification preferences for the current user. Cached for 30 seconds."""
    cache_key = cache.make_key("notifications", "preferences", user.user_id)

    async def fetch_preferences():
        response = await proxy_notification_request(
            "GET",
            "/preferences",
            headers={"X-User-Id": user.user_id},
        )
        if hasattr(response, "body"):
            return json.loads(response.body)
        return response

    return await cache.get_or_compute(cache_key, fetch_preferences, ttl=30)


@router.put("/preferences")
async def update_preferences(
    request: Request,
    user: AuthenticatedUser = Depends(require_auth),
    cache: CacheService = Depends(get_cache),
):
    """DEPRECATED: Update notification preferences for the current user."""
    body = await request.json()
    # Invalidate cache on update
    cache_key = cache.make_key("notifications", "preferences", user.user_id)
    await cache.delete(cache_key)
    return await proxy_notification_request(
        "PUT",
        "/preferences",
        json_body=body,
        headers={"X-User-Id": user.user_id},
    )


@router.delete("/preferences")
async def delete_preferences(
    user: AuthenticatedUser = Depends(require_auth),
    cache: CacheService = Depends(get_cache),
):
    """DEPRECATED: Delete notification preferences (reset to defaults)."""
    # Invalidate cache on delete
    cache_key = cache.make_key("notifications", "preferences", user.user_id)
    await cache.delete(cache_key)
    return await proxy_notification_request(
        "DELETE",
        "/preferences",
        headers={"X-User-Id": user.user_id},
    )
