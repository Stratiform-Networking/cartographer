"""
Broadcast notification router.

Handles broadcast and scheduled notification endpoints:
- Network-wide broadcasts
- Scheduled broadcasts
- Service status notifications (up/down)
- Version update notifications
- Cartographer status subscriptions
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import Request
from fastapi import Request as FastAPIRequest
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...dependencies import AuthenticatedUser, require_auth, require_owner, require_write_access
from ...services.network_service import get_network_member_user_ids
from ...services.proxy_service import proxy_cartographer_status_request, proxy_notification_request

router = APIRouter(tags=["notification-broadcast"])


# ==================== Network Broadcast (Owner Only) ====================


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
    return await proxy_notification_request(
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
            "user_ids": user_ids,
        },
    )


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
    return await proxy_notification_request(
        "POST",
        f"/networks/{network_id}/notifications/send",
        json_body={
            **body,
            "user_ids": user_ids,
        },
        use_user_path=True,
    )


# ==================== Scheduled Broadcasts (Owner Only) ====================


@router.get("/scheduled")
async def get_scheduled_broadcasts(
    include_completed: bool = Query(False),
    user: AuthenticatedUser = Depends(require_owner),
):
    """Get all scheduled broadcasts. Owner only."""
    return await proxy_notification_request(
        "GET",
        "/scheduled",
        params={"include_completed": include_completed},
    )


@router.post("/scheduled")
async def create_scheduled_broadcast(
    request: Request,
    user: AuthenticatedUser = Depends(require_owner),
):
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
    return await proxy_notification_request(
        "POST",
        "/scheduled",
        json_body=body,
        headers={"X-Username": user.username},
    )


@router.get("/scheduled/{broadcast_id}")
async def get_scheduled_broadcast(
    broadcast_id: str,
    user: AuthenticatedUser = Depends(require_owner),
):
    """Get a specific scheduled broadcast. Owner only."""
    return await proxy_notification_request("GET", f"/scheduled/{broadcast_id}")


@router.patch("/scheduled/{broadcast_id}")
async def update_scheduled_broadcast(
    broadcast_id: str,
    request: Request,
    user: AuthenticatedUser = Depends(require_owner),
):
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
    return await proxy_notification_request("PATCH", f"/scheduled/{broadcast_id}", json_body=body)


@router.post("/scheduled/{broadcast_id}/cancel")
async def cancel_scheduled_broadcast(
    broadcast_id: str,
    user: AuthenticatedUser = Depends(require_owner),
):
    """Cancel a scheduled broadcast. Owner only."""
    return await proxy_notification_request("POST", f"/scheduled/{broadcast_id}/cancel")


@router.delete("/scheduled/{broadcast_id}")
async def delete_scheduled_broadcast(
    broadcast_id: str,
    user: AuthenticatedUser = Depends(require_owner),
):
    """Delete a scheduled broadcast. Owner only."""
    return await proxy_notification_request("DELETE", f"/scheduled/{broadcast_id}")


@router.post("/scheduled/{broadcast_id}/seen")
async def mark_broadcast_seen(
    broadcast_id: str,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Mark a sent broadcast as seen by the user."""
    return await proxy_notification_request("POST", f"/scheduled/{broadcast_id}/seen")


# ==================== Service Status Notifications ====================


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
    return await proxy_notification_request(
        "POST",
        "/service-status/up",
        params={
            "message": body.get("message"),
            "downtime_minutes": body.get("downtime_minutes"),
        },
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
    return await proxy_notification_request(
        "POST",
        "/service-status/down",
        json_body={
            "message": body.get("message"),
            "affected_services": body.get("affected_services"),
        },
    )


# ==================== Version Update Notifications ====================


@router.get("/version")
async def get_version_status(
    user: AuthenticatedUser = Depends(require_auth),
):
    """
    Get current version status and last check info.

    Returns information about the current version, latest available version,
    and whether an update is available.
    """
    return await proxy_notification_request("GET", "/version")


@router.post("/version/check")
async def check_for_updates(
    user: AuthenticatedUser = Depends(require_auth),
):
    """
    Manually trigger a version check and get results.

    This will check GitHub for the latest version and return whether
    an update is available.
    """
    return await proxy_notification_request("POST", "/version/check")


@router.post("/version/notify")
async def send_version_notification(
    user: AuthenticatedUser = Depends(require_auth),
):
    """
    Send a version update notification to all subscribed users.

    This will check for updates and send SYSTEM_STATUS notifications
    to all users who have that notification type enabled.
    """
    return await proxy_notification_request("POST", "/version/notify")


# ==================== Cartographer Status Subscriptions ====================


@router.get("/cartographer-status/subscription")
async def get_cartographer_status_subscription(
    user: AuthenticatedUser = Depends(require_auth),
):
    """Get user's Cartographer status subscription"""
    return await proxy_cartographer_status_request("GET", "/subscription", user_id=user.user_id)


@router.post("/cartographer-status/subscription")
async def create_cartographer_status_subscription(
    body: dict,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Create or update Cartographer status subscription"""
    return await proxy_cartographer_status_request(
        "POST", "/subscription", json_body=body, user_id=user.user_id
    )


@router.put("/cartographer-status/subscription")
async def update_cartographer_status_subscription(
    body: dict,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Update Cartographer status subscription"""
    return await proxy_cartographer_status_request(
        "PUT", "/subscription", json_body=body, user_id=user.user_id
    )


@router.delete("/cartographer-status/subscription")
async def delete_cartographer_status_subscription(
    user: AuthenticatedUser = Depends(require_auth),
):
    """Delete Cartographer status subscription"""
    return await proxy_cartographer_status_request("DELETE", "/subscription", user_id=user.user_id)


@router.post("/cartographer-status/test/discord")
async def test_global_discord(
    body: dict,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Test Discord notifications for global settings"""
    return await proxy_cartographer_status_request(
        "POST", "/test/discord", json_body=body, user_id=user.user_id
    )
