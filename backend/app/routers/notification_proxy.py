"""
Proxy router for notification service requests.
Forwards /api/notifications/* requests to the notification microservice.

This router handles core notification functionality while specialized
endpoints are delegated to sub-routers:
- notification/preferences.py - User and network preferences
- notification/discord.py - Discord integration and OAuth
- notification/broadcast.py - Broadcasts and scheduled messages
- notification/email.py - Email notifications and testing

Performance optimizations:
- Uses shared HTTP client pool with connection reuse
- Circuit breaker prevents cascade failures
- Connections are pre-warmed on startup
- Redis caching for status and preferences endpoints
"""

import json

from fastapi import APIRouter, Depends, Query, Request

from ..dependencies import AuthenticatedUser, require_auth, require_owner, require_write_access
from ..services.cache_service import CacheService, get_cache
from ..services.proxy_service import proxy_notification_request

# Import sub-routers
from .notification import broadcast_router, discord_router, email_router, preferences_router
from .notification.broadcast import (
    cancel_scheduled_broadcast,
    check_for_updates,
    create_cartographer_status_subscription,
    create_scheduled_broadcast,
    delete_cartographer_status_subscription,
    delete_scheduled_broadcast,
    get_cartographer_status_subscription,
    get_scheduled_broadcast,
    get_scheduled_broadcasts,
    get_version_status,
    mark_broadcast_seen,
    notify_service_down,
    notify_service_up,
    send_global_notification,
    send_network_notification,
    send_version_notification,
    test_global_discord,
    update_cartographer_status_subscription,
    update_scheduled_broadcast,
)
from .notification.discord import discord_oauth_callback, get_discord_channels, get_discord_guilds
from .notification.discord import get_discord_info as _get_discord_bot_info
from .notification.discord import get_discord_invite_url
from .notification.discord import (
    get_user_discord_info as get_discord_info,  # Re-export with legacy name for test compatibility
)
from .notification.discord import initiate_discord_oauth, unlink_discord
from .notification.email import (
    send_network_test_notification,
    send_test_notification,
    test_user_global_notification,
    test_user_network_notification,
)

# Re-export functions from sub-routers for backwards compatibility with tests
from .notification.preferences import (
    delete_network_preferences,
    delete_preferences,
    delete_user_network_preferences,
    get_global_preferences,
    get_network_preferences,
    get_preferences,
    get_user_global_preferences,
    get_user_network_preferences,
    update_global_preferences,
    update_network_preferences,
    update_preferences,
    update_user_global_preferences,
    update_user_network_preferences,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])

# Include sub-routers
router.include_router(preferences_router)
router.include_router(discord_router)
router.include_router(broadcast_router)
router.include_router(email_router)


# ==================== Service Status ====================


@router.get("/status")
async def get_service_status(
    user: AuthenticatedUser = Depends(require_auth),
    cache: CacheService = Depends(get_cache),
):
    """Get notification service status including available channels. Cached for 30 seconds."""
    cache_key = "notifications:status"

    async def fetch_status():
        response = await proxy_notification_request("GET", "/status")
        if hasattr(response, "body"):
            return json.loads(response.body)
        return response

    return await cache.get_or_compute(cache_key, fetch_status, ttl=30)


# ==================== History & Stats ====================


@router.get("/history")
async def get_notification_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    user: AuthenticatedUser = Depends(require_auth),
):
    """Get notification history for the current user."""
    return await proxy_notification_request(
        "GET",
        "/history",
        params={"page": page, "per_page": per_page},
        headers={"X-User-Id": user.user_id},
    )


@router.get("/networks/{network_id}/history")
async def get_network_notification_history(
    network_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    user: AuthenticatedUser = Depends(require_auth),
):
    """Get notification history for a specific network."""
    return await proxy_notification_request(
        "GET",
        f"/networks/{network_id}/history",
        params={"page": page, "per_page": per_page},
        headers={"X-User-Id": user.user_id},
    )


@router.get("/stats")
async def get_notification_stats(
    user: AuthenticatedUser = Depends(require_auth),
):
    """Get notification statistics for the current user."""
    return await proxy_notification_request(
        "GET",
        "/stats",
        headers={"X-User-Id": user.user_id},
    )


@router.get("/networks/{network_id}/stats")
async def get_network_notification_stats(
    network_id: str,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Get notification statistics for a specific network."""
    return await proxy_notification_request(
        "GET",
        f"/networks/{network_id}/stats",
        headers={"X-User-Id": user.user_id},
    )


# ==================== ML / Anomaly Detection ====================


@router.get("/ml/status")
async def get_ml_model_status(
    network_id: str = Query(None, description="Network ID for per-network stats"),
    user: AuthenticatedUser = Depends(require_auth),
):
    """Get ML anomaly detection model status."""
    params = {}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_notification_request("GET", "/ml/status", params=params)


@router.get("/ml/baseline/{device_ip}")
async def get_device_baseline(
    device_ip: str,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Get learned baseline for a specific device."""
    return await proxy_notification_request("GET", f"/ml/baseline/{device_ip}")


@router.post("/ml/feedback/false-positive")
async def mark_false_positive(
    event_id: str,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Mark an anomaly detection as a false positive (for model improvement)."""
    return await proxy_notification_request(
        "POST",
        "/ml/feedback/false-positive",
        params={"event_id": event_id},
    )


@router.delete("/ml/baseline/{device_ip}")
async def reset_device_baseline(
    device_ip: str,
    user: AuthenticatedUser = Depends(require_owner),
):
    """Reset learned baseline for a specific device. Owner only."""
    return await proxy_notification_request("DELETE", f"/ml/baseline/{device_ip}")


@router.delete("/ml/reset")
async def reset_all_ml_data(
    user: AuthenticatedUser = Depends(require_owner),
):
    """Reset all ML model data. Owner only."""
    return await proxy_notification_request("DELETE", "/ml/reset")


# ==================== Silenced Devices (Monitoring Disabled) ====================


@router.get("/silenced-devices")
async def get_silenced_devices(
    user: AuthenticatedUser = Depends(require_auth),
):
    """Get list of devices with notifications silenced."""
    return await proxy_notification_request("GET", "/silenced-devices")


@router.post("/silenced-devices")
async def set_silenced_devices(
    request: Request,
    user: AuthenticatedUser = Depends(require_write_access),
):
    """Set the full list of silenced devices. Requires write access."""
    body = await request.json()
    return await proxy_notification_request("POST", "/silenced-devices", json_body=body)


@router.post("/silenced-devices/{device_ip}")
async def silence_device(
    device_ip: str,
    user: AuthenticatedUser = Depends(require_write_access),
):
    """Silence notifications for a device. Requires write access."""
    return await proxy_notification_request("POST", f"/silenced-devices/{device_ip}")


@router.delete("/silenced-devices/{device_ip}")
async def unsilence_device(
    device_ip: str,
    user: AuthenticatedUser = Depends(require_write_access),
):
    """Re-enable notifications for a device. Requires write access."""
    return await proxy_notification_request("DELETE", f"/silenced-devices/{device_ip}")


@router.get("/silenced-devices/{device_ip}")
async def check_device_silenced(
    device_ip: str,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Check if a device is silenced."""
    return await proxy_notification_request("GET", f"/silenced-devices/{device_ip}")


# ==================== Internal Endpoints (for health service integration) ====================


@router.post("/internal/process-health-check")
async def process_health_check(
    device_ip: str,
    success: bool,
    latency_ms: float | None = None,
    packet_loss: float | None = None,
    device_name: str | None = None,
    previous_state: str | None = None,
):
    """
    Process a health check result from the health service.

    This internal endpoint is called by the health service after each check.
    It trains the ML model and potentially sends notifications.
    """
    return await proxy_notification_request(
        "POST",
        "/process-health-check",
        params={
            "device_ip": device_ip,
            "success": success,
            "latency_ms": latency_ms,
            "packet_loss": packet_loss,
            "device_name": device_name,
            "previous_state": previous_state,
        },
    )
