"""
Proxy router for notification service requests.
Forwards /api/notifications/* requests to the notification microservice.

Performance optimizations:
- Uses shared HTTP client pool with connection reuse
- Circuit breaker prevents cascade failures
- Connections are pre-warmed on startup
"""

from fastapi import APIRouter, HTTPException, Request, Depends, Query
from fastapi import Request as FastAPIRequest
from fastapi.responses import JSONResponse, RedirectResponse
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import (
    AuthenticatedUser,
    require_auth,
    require_write_access,
    require_owner,
)
from ..database import get_db
from ..services.http_client import http_pool
from ..routers.networks import get_network_member_user_ids

router = APIRouter(prefix="/notifications", tags=["notifications"])


async def proxy_request(
    method: str,
    path: str,
    params: dict = None,
    json_body: dict = None,
    headers: dict = None,
    timeout: float = 30.0,
    use_user_path: bool = False,
):
    """Forward a request to the notification service using the shared client pool"""
    if use_user_path:
        # Use direct API path (not /api/notifications prefix)
        full_path = f"/api{path}"
    else:
        full_path = f"/api/notifications{path}"
    
    return await http_pool.request(
        service_name="notification",
        method=method,
        path=full_path,
        params=params,
        json_body=json_body,
        headers=headers,
        timeout=timeout
    )


# ==================== Per-Network Preferences Endpoints ====================

@router.get("/networks/{network_id}/preferences")
async def get_network_preferences(network_id: str, user: AuthenticatedUser = Depends(require_auth)):
    """Get notification preferences for a specific network."""
    return await proxy_request(
        "GET",
        f"/networks/{network_id}/preferences",
        headers={"X-User-Id": user.user_id}
    )


@router.put("/networks/{network_id}/preferences")
async def update_network_preferences(network_id: str, request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """Update notification preferences for a specific network."""
    body = await request.json()
    return await proxy_request(
        "PUT",
        f"/networks/{network_id}/preferences",
        json_body=body,
        headers={"X-User-Id": user.user_id}
    )


@router.delete("/networks/{network_id}/preferences")
async def delete_network_preferences(network_id: str, user: AuthenticatedUser = Depends(require_auth)):
    """Delete notification preferences for a network (reset to defaults)."""
    return await proxy_request(
        "DELETE",
        f"/networks/{network_id}/preferences",
        headers={"X-User-Id": user.user_id}
    )


@router.post("/networks/{network_id}/test")
async def send_network_test_notification(network_id: str, request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """Send a test notification for a specific network."""
    body = await request.json()
    return await proxy_request(
        "POST",
        f"/networks/{network_id}/test",
        json_body=body,
        headers={"X-User-Id": user.user_id}
    )


@router.get("/networks/{network_id}/history")
async def get_network_notification_history(
    network_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    user: AuthenticatedUser = Depends(require_auth),
):
    """Get notification history for a specific network."""
    return await proxy_request(
        "GET",
        f"/networks/{network_id}/history",
        params={"page": page, "per_page": per_page},
        headers={"X-User-Id": user.user_id}
    )


@router.get("/networks/{network_id}/stats")
async def get_network_notification_stats(network_id: str, user: AuthenticatedUser = Depends(require_auth)):
    """Get notification statistics for a specific network."""
    return await proxy_request(
        "GET",
        f"/networks/{network_id}/stats",
        headers={"X-User-Id": user.user_id}
    )


# ==================== Legacy Preferences Endpoints (deprecated) ====================

@router.get("/preferences")
async def get_preferences(user: AuthenticatedUser = Depends(require_auth)):
    """DEPRECATED: Get notification preferences for the current user."""
    return await proxy_request(
        "GET",
        "/preferences",
        headers={"X-User-Id": user.user_id}
    )


@router.put("/preferences")
async def update_preferences(request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """DEPRECATED: Update notification preferences for the current user."""
    body = await request.json()
    return await proxy_request(
        "PUT",
        "/preferences",
        json_body=body,
        headers={"X-User-Id": user.user_id}
    )


@router.delete("/preferences")
async def delete_preferences(user: AuthenticatedUser = Depends(require_auth)):
    """DEPRECATED: Delete notification preferences (reset to defaults)."""
    return await proxy_request(
        "DELETE",
        "/preferences",
        headers={"X-User-Id": user.user_id}
    )


# ==================== Service Status ====================

@router.get("/status")
async def get_service_status(user: AuthenticatedUser = Depends(require_auth)):
    """Get notification service status including available channels."""
    return await proxy_request("GET", "/status")


# ==================== Discord Integration ====================

@router.get("/discord/info")
async def get_discord_info(user: AuthenticatedUser = Depends(require_auth)):
    """Get Discord bot information and invite URL."""
    return await proxy_request("GET", "/discord/info")


@router.get("/discord/guilds")
async def get_discord_guilds(user: AuthenticatedUser = Depends(require_auth)):
    """Get list of Discord servers (guilds) the bot is in."""
    return await proxy_request("GET", "/discord/guilds")


@router.get("/discord/guilds/{guild_id}/channels")
async def get_discord_channels(guild_id: str, user: AuthenticatedUser = Depends(require_auth)):
    """Get list of text channels in a Discord server."""
    return await proxy_request("GET", f"/discord/guilds/{guild_id}/channels")


@router.get("/discord/invite-url")
async def get_discord_invite_url(user: AuthenticatedUser = Depends(require_auth)):
    """Get the bot invite URL."""
    return await proxy_request("GET", "/discord/invite-url")


# ==================== Testing ====================

@router.post("/test")
async def send_test_notification(request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """Send a test notification via a specific channel."""
    body = await request.json()
    return await proxy_request(
        "POST",
        "/test",
        json_body=body,
        headers={"X-User-Id": user.user_id}
    )


# ==================== History & Stats ====================

@router.get("/history")
async def get_notification_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    user: AuthenticatedUser = Depends(require_auth),
):
    """Get notification history for the current user."""
    return await proxy_request(
        "GET",
        "/history",
        params={"page": page, "per_page": per_page},
        headers={"X-User-Id": user.user_id}
    )


@router.get("/stats")
async def get_notification_stats(user: AuthenticatedUser = Depends(require_auth)):
    """Get notification statistics for the current user."""
    return await proxy_request(
        "GET",
        "/stats",
        headers={"X-User-Id": user.user_id}
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
    return await proxy_request("GET", "/ml/status", params=params)


@router.get("/ml/baseline/{device_ip}")
async def get_device_baseline(device_ip: str, user: AuthenticatedUser = Depends(require_auth)):
    """Get learned baseline for a specific device."""
    return await proxy_request("GET", f"/ml/baseline/{device_ip}")


@router.post("/ml/feedback/false-positive")
async def mark_false_positive(event_id: str, user: AuthenticatedUser = Depends(require_auth)):
    """Mark an anomaly detection as a false positive (for model improvement)."""
    return await proxy_request(
        "POST",
        "/ml/feedback/false-positive",
        params={"event_id": event_id}
    )


@router.delete("/ml/baseline/{device_ip}")
async def reset_device_baseline(device_ip: str, user: AuthenticatedUser = Depends(require_owner)):
    """Reset learned baseline for a specific device. Owner only."""
    return await proxy_request("DELETE", f"/ml/baseline/{device_ip}")


@router.delete("/ml/reset")
async def reset_all_ml_data(user: AuthenticatedUser = Depends(require_owner)):
    """Reset all ML model data. Owner only."""
    return await proxy_request("DELETE", "/ml/reset")


# ==================== Global Notifications (Owner Only) ====================

@router.post("/broadcast")
async def send_global_notification(
    request: Request, 
    user: AuthenticatedUser = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a network-scoped broadcast notification to all users in a network. Owner only.
    
    Expects a JSON body with:
    - network_id: str - The network UUID to broadcast to (required)
    - title: str - The notification title
    - message: str - The notification message
    - event_type: str - The type of notification (e.g., 'scheduled_maintenance', 'system_status')
    - priority: str - The priority level ('low', 'medium', 'high', 'critical')
    """
    body = await request.json()
    network_id = body.get("network_id")
    
    if not network_id:
        raise HTTPException(status_code=400, detail="network_id is required")
    
    # Ensure network_id is a string (UUID)
    network_id = str(network_id)
    
    # Get all network members (owner + users with permissions)
    try:
        user_ids = await get_network_member_user_ids(network_id, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get network members: {str(e)}")
    
    # Build the network event for the notification service
    # Send event fields directly (not wrapped in "event" key) along with user_ids
    return await proxy_request(
        "POST",
        f"/networks/{network_id}/send-notification",
        json_body={
            "event_id": f"broadcast-{user.user_id}-{network_id}-{body.get('title', 'notification')[:20]}",
        "event_type": body.get("event_type", "scheduled_maintenance"),
        "priority": body.get("priority", "medium"),
        "title": body.get("title", "System Notification"),
        "message": body.get("message", ""),
            "network_id": network_id,
        "details": {
            "sent_by": user.username,
                "is_broadcast": True,
            },
            "user_ids": user_ids,  # Pass list of network member user IDs
        },
    )


# ==================== Global Preferences (Cartographer Up/Down) ====================

@router.get("/global/preferences")
async def get_global_preferences(user: AuthenticatedUser = Depends(require_auth)):
    """Get global notification preferences for the current user (Cartographer Up/Down)."""
    return await proxy_request(
        "GET",
        "/global/preferences",
        headers={"X-User-Id": user.user_id}
    )


@router.put("/global/preferences")
async def update_global_preferences(request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """Update global notification preferences for the current user (Cartographer Up/Down)."""
    body = await request.json()
    return await proxy_request(
        "PUT",
        "/global/preferences",
        json_body=body,
        headers={"X-User-Id": user.user_id}
    )


# ==================== Scheduled Broadcasts (Owner Only) ====================

@router.get("/scheduled")
async def get_scheduled_broadcasts(
    include_completed: bool = Query(False),
    user: AuthenticatedUser = Depends(require_owner),
):
    """Get all scheduled broadcasts. Owner only."""
    return await proxy_request(
        "GET",
        "/scheduled",
        params={"include_completed": include_completed},
    )


@router.post("/scheduled")
async def create_scheduled_broadcast(request: Request, user: AuthenticatedUser = Depends(require_owner)):
    """
    Create a new scheduled broadcast. Owner only.
    
    Expects a JSON body with:
    - title: str - The notification title
    - message: str - The notification message
    - event_type: str - The type of notification (default: 'scheduled_maintenance')
    - priority: str - The priority level (default: 'medium')
    - scheduled_at: str - ISO datetime when to send the broadcast
    """
    body = await request.json()
    
    return await proxy_request(
        "POST",
        "/scheduled",
        json_body=body,
        headers={"X-Username": user.username},
    )


@router.get("/scheduled/{broadcast_id}")
async def get_scheduled_broadcast(broadcast_id: str, user: AuthenticatedUser = Depends(require_owner)):
    """Get a specific scheduled broadcast. Owner only."""
    return await proxy_request("GET", f"/scheduled/{broadcast_id}")


@router.patch("/scheduled/{broadcast_id}")
async def update_scheduled_broadcast(broadcast_id: str, request: Request, user: AuthenticatedUser = Depends(require_owner)):
    """
    Update a scheduled broadcast. Owner only.
    Only pending broadcasts can be updated.
    
    Expects a JSON body with any of:
    - title: str - The notification title
    - message: str - The notification message
    - event_type: str - The type of notification
    - priority: str - The priority level
    - scheduled_at: str - ISO datetime when to send the broadcast
    - timezone: str - IANA timezone name for display
    """
    body = await request.json()
    return await proxy_request("PATCH", f"/scheduled/{broadcast_id}", json_body=body)


@router.post("/scheduled/{broadcast_id}/cancel")
async def cancel_scheduled_broadcast(broadcast_id: str, user: AuthenticatedUser = Depends(require_owner)):
    """Cancel a scheduled broadcast. Owner only."""
    return await proxy_request("POST", f"/scheduled/{broadcast_id}/cancel")


@router.delete("/scheduled/{broadcast_id}")
async def delete_scheduled_broadcast(broadcast_id: str, user: AuthenticatedUser = Depends(require_owner)):
    """Delete a scheduled broadcast. Owner only."""
    return await proxy_request("DELETE", f"/scheduled/{broadcast_id}")


# ==================== Silenced Devices (Monitoring Disabled) ====================

@router.get("/silenced-devices")
async def get_silenced_devices(user: AuthenticatedUser = Depends(require_auth)):
    """Get list of devices with notifications silenced."""
    return await proxy_request("GET", "/silenced-devices")


@router.post("/silenced-devices")
async def set_silenced_devices(request: Request, user: AuthenticatedUser = Depends(require_write_access)):
    """Set the full list of silenced devices. Requires write access."""
    body = await request.json()
    return await proxy_request("POST", "/silenced-devices", json_body=body)


@router.post("/silenced-devices/{device_ip}")
async def silence_device(device_ip: str, user: AuthenticatedUser = Depends(require_write_access)):
    """Silence notifications for a device. Requires write access."""
    return await proxy_request("POST", f"/silenced-devices/{device_ip}")


@router.delete("/silenced-devices/{device_ip}")
async def unsilence_device(device_ip: str, user: AuthenticatedUser = Depends(require_write_access)):
    """Re-enable notifications for a device. Requires write access."""
    return await proxy_request("DELETE", f"/silenced-devices/{device_ip}")


@router.get("/silenced-devices/{device_ip}")
async def check_device_silenced(device_ip: str, user: AuthenticatedUser = Depends(require_auth)):
    """Check if a device is silenced."""
    return await proxy_request("GET", f"/silenced-devices/{device_ip}")


# ==================== Internal Endpoints (for health service integration) ====================

@router.post("/internal/process-health-check")
async def process_health_check(
    device_ip: str,
    success: bool,
    latency_ms: Optional[float] = None,
    packet_loss: Optional[float] = None,
    device_name: Optional[str] = None,
    previous_state: Optional[str] = None,
):
    """
    Process a health check result from the health service.
    
    This internal endpoint is called by the health service after each check.
    It trains the ML model and potentially sends notifications.
    """
    return await proxy_request(
        "POST",
        "/process-health-check",
        params={
            "device_ip": device_ip,
            "success": success,
            "latency_ms": latency_ms,
            "packet_loss": packet_loss,
            "device_name": device_name,
            "previous_state": previous_state,
        }
    )


# ==================== Cartographer Service Status Notifications ====================

@router.post("/service-status/up")
async def notify_service_up(
    request: Request,
    user: AuthenticatedUser = Depends(require_owner),
):
    """
    Send a notification that Cartographer is back online. Owner only.
    
    Can be used by administrators or external monitoring systems.
    """
    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    
    return await proxy_request(
        "POST",
        "/service-status/up",
        params={
            "message": body.get("message"),
            "downtime_minutes": body.get("downtime_minutes"),
        }
    )


@router.post("/service-status/down")
async def notify_service_down(
    request: Request,
    user: AuthenticatedUser = Depends(require_owner),
):
    """
    Send a notification that Cartographer is going/has gone down. Owner only.
    
    Can be used:
    - Before planned maintenance
    - By external monitoring systems
    - For alerting about service degradation
    """
    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    
    return await proxy_request(
        "POST",
        "/service-status/down",
        json_body={
            "message": body.get("message"),
            "affected_services": body.get("affected_services"),
        }
    )


# ==================== Version Update Notifications ====================

@router.get("/version")
async def get_version_status(user: AuthenticatedUser = Depends(require_auth)):
    """
    Get current version status and last check info.
    
    Returns information about the current version, latest available version,
    and whether an update is available.
    """
    return await proxy_request("GET", "/version")


@router.post("/version/check")
async def check_for_updates(user: AuthenticatedUser = Depends(require_auth)):
    """
    Manually trigger a version check and get results.
    
    This will check GitHub for the latest version and return whether
    an update is available.
    """
    return await proxy_request("POST", "/version/check")


@router.post("/version/notify")
async def send_version_notification(user: AuthenticatedUser = Depends(require_auth)):
    """
    Send a version update notification to all subscribed users.
    
    This will check for updates and send SYSTEM_STATUS notifications
    to all users who have that notification type enabled.
    """
    return await proxy_request("POST", "/version/notify")


# ==================== Cartographer Status Notifications ====================

async def proxy_cartographer_status_request(
    method: str,
    path: str,
    json_body: dict = None,
    user: AuthenticatedUser = None,
):
    """Forward a request to the Cartographer status service"""
    headers = {}
    if user:
        headers["X-User-Id"] = user.user_id
        # AuthenticatedUser doesn't have email - use username as fallback for email header
        if hasattr(user, 'email') and user.email:
            headers["X-User-Email"] = user.email
    
    return await http_pool.request(
        service_name="notification",
        method=method,
        path=f"/api/cartographer-status{path}",
        json_body=json_body,
        headers=headers,
        timeout=30.0
    )


@router.get("/cartographer-status/subscription")
async def get_cartographer_status_subscription(
    user: AuthenticatedUser = Depends(require_auth),
):
    """Get user's Cartographer status subscription"""
    return await proxy_cartographer_status_request("GET", "/subscription", user=user)


@router.post("/cartographer-status/subscription")
async def create_cartographer_status_subscription(
    body: dict,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Create or update Cartographer status subscription"""
    return await proxy_cartographer_status_request("POST", "/subscription", json_body=body, user=user)


@router.put("/cartographer-status/subscription")
async def update_cartographer_status_subscription(
    body: dict,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Update Cartographer status subscription"""
    return await proxy_cartographer_status_request("PUT", "/subscription", json_body=body, user=user)


@router.delete("/cartographer-status/subscription")
async def delete_cartographer_status_subscription(
    user: AuthenticatedUser = Depends(require_auth),
):
    """Delete Cartographer status subscription"""
    return await proxy_cartographer_status_request("DELETE", "/subscription", user=user)


@router.post("/cartographer-status/test/discord")
async def test_global_discord(
    body: dict,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Test Discord notifications for global settings"""
    return await proxy_cartographer_status_request("POST", "/test/discord", json_body=body, user=user)


# ==================== User-Specific Notification Preferences ====================

@router.get("/users/me/networks/{network_id}/preferences")
async def get_user_network_preferences(
    network_id: str,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Get current user's notification preferences for a specific network."""
    return await proxy_request(
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
    return await proxy_request(
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
    return await proxy_request(
        "DELETE",
        f"/users/{user.user_id}/networks/{network_id}/preferences",
        use_user_path=True,
    )


@router.get("/users/me/global/preferences")
async def get_user_global_preferences(
    user: AuthenticatedUser = Depends(require_auth),
):
    """Get current user's global notification preferences."""
    return await proxy_request(
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
    return await proxy_request(
        "PUT",
        f"/users/{user.user_id}/global/preferences",
        json_body=body,
        use_user_path=True,
    )


@router.post("/users/me/networks/{network_id}/test")
async def test_user_network_notification(
    network_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Send a test notification for current user's network preferences."""
    body = await request.json()
    return await proxy_request(
        "POST",
        f"/users/{user.user_id}/networks/{network_id}/test",
        json_body=body,
        use_user_path=True,
    )


@router.post("/users/me/global/test")
async def test_user_global_notification(
    request: Request,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Send a test notification for current user's global preferences."""
    body = await request.json()
    return await proxy_request(
        "POST",
        f"/users/{user.user_id}/global/test",
        json_body=body,
        use_user_path=True,
    )


# ==================== Discord OAuth ====================

@router.get("/auth/discord/link")
async def initiate_discord_oauth(
    context_type: str = Query("global", description="Context type: 'network' or 'global'"),
    network_id: Optional[str] = Query(None, description="Network ID (UUID) if context_type is 'network'"),
    user: AuthenticatedUser = Depends(require_auth),
):
    """
    Initiate Discord OAuth flow for current user.
    
    Args:
        context_type: "network" for per-network Discord link, "global" for global link
        network_id: The network_id if context_type is "network"
    """
    params = f"user_id={user.user_id}&context_type={context_type}"
    if network_id is not None:
        params += f"&network_id={network_id}"
    return await proxy_request(
        "GET",
        f"/auth/discord/link?{params}",
        use_user_path=True,
    )


@router.get("/auth/discord/callback")
async def discord_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
):
    """Handle Discord OAuth callback (no auth required - handled by notification service)."""
    # For OAuth callbacks, we need to handle redirects specially
    # The notification service returns a RedirectResponse, not JSON
    from ..services.http_client import http_pool
    
    service = http_pool._services.get("notification")
    if not service:
        raise HTTPException(status_code=500, detail="Notification service not available")
    
    if not service.client:
        await service.initialize()
    
    # Make request with follow_redirects=False to get the redirect response
    response = await service.client.get(
        f"/api/auth/discord/callback",
        params={"code": code, "state": state},
        follow_redirects=False
    )
    
    # If it's a redirect (302/303), return a RedirectResponse
    if response.status_code in (302, 303, 307, 308):
        redirect_url = response.headers.get("location")
        if redirect_url:
            return RedirectResponse(url=redirect_url)
    
    # Otherwise, try to parse as JSON
    try:
        content = response.json()
    except Exception:
        content = {"detail": response.text or "Empty response"}
    
    return JSONResponse(
        content=content,
        status_code=response.status_code
    )


@router.delete("/users/me/discord/link")
async def unlink_discord(
    context_type: str = Query("global", description="Context type: 'network' or 'global'"),
    network_id: Optional[str] = Query(None, description="Network ID (UUID) if context_type is 'network'"),
    user: AuthenticatedUser = Depends(require_auth),
):
    """
    Unlink Discord account from current user for a specific context.
    
    Args:
        context_type: "network" for per-network Discord link, "global" for global link
        network_id: The network_id if context_type is "network"
    """
    params = {"context_type": context_type}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_request(
        "DELETE",
        f"/users/{user.user_id}/discord/link",
        params=params,
        use_user_path=True,
    )


@router.get("/users/me/discord")
async def get_discord_info(
    context_type: str = Query("global", description="Context type: 'network' or 'global'"),
    network_id: Optional[str] = Query(None, description="Network ID (UUID) if context_type is 'network'"),
    user: AuthenticatedUser = Depends(require_auth),
):
    """
    Get linked Discord account info for current user in a specific context.
    
    Args:
        context_type: "network" for per-network Discord link, "global" for global link
        network_id: The network_id if context_type is "network"
    """
    params = {"context_type": context_type}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_request(
        "GET",
        f"/users/{user.user_id}/discord",
        params=params,
        use_user_path=True,
    )


# ==================== Send Network Notification ====================

@router.post("/networks/{network_id}/send")
async def send_network_notification(
    network_id: str,
    request: FastAPIRequest,
    user: AuthenticatedUser = Depends(require_write_access),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a notification to all users in a network.
    
    Backend fetches network members, then proxies to notification service.
    """
    body = await request.json()
    
    # Get all network members
    try:
        user_ids = await get_network_member_user_ids(network_id, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get network members: {str(e)}")
    
    # Proxy to notification service with user_ids
    return await proxy_request(
        "POST",
        f"/networks/{network_id}/notifications/send",
        json_body={
            **body,
            "user_ids": user_ids,
        },
        use_user_path=True,
    )

