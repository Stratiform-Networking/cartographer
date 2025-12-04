"""
Proxy router for notification service requests.
Forwards /api/notifications/* requests to the notification microservice.
"""

import os
import httpx
from fastapi import APIRouter, HTTPException, Request, Depends, Query
from fastapi.responses import JSONResponse
from typing import Optional

from ..dependencies import (
    AuthenticatedUser,
    require_auth,
    require_write_access,
    require_owner,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])

# Notification service URL - defaults to localhost:8005 for host network mode
NOTIFICATION_SERVICE_URL = os.environ.get("NOTIFICATION_SERVICE_URL", "http://localhost:8005")


async def proxy_request(
    method: str,
    path: str,
    params: dict = None,
    json_body: dict = None,
    headers: dict = None,
    timeout: float = 30.0,
):
    """Forward a request to the notification service"""
    url = f"{NOTIFICATION_SERVICE_URL}/api/notifications{path}"
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            if method == "GET":
                response = await client.get(url, params=params, headers=headers)
            elif method == "POST":
                response = await client.post(url, params=params, json=json_body, headers=headers)
            elif method == "PUT":
                response = await client.put(url, params=params, json=json_body, headers=headers)
            elif method == "DELETE":
                response = await client.delete(url, params=params, headers=headers)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")
            
            # Try to parse JSON response
            try:
                content = response.json()
            except Exception:
                content = {"detail": response.text or "Unknown error"}
            
            return JSONResponse(
                content=content,
                status_code=response.status_code
            )
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail="Notification service unavailable. Make sure the notification-service is running."
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Notification service timeout"
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Notification service unavailable: {str(e)}"
            )


# ==================== Preferences Endpoints ====================

@router.get("/preferences")
async def get_preferences(user: AuthenticatedUser = Depends(require_auth)):
    """Get notification preferences for the current user."""
    return await proxy_request(
        "GET",
        "/preferences",
        headers={"X-User-Id": user.user_id}
    )


@router.put("/preferences")
async def update_preferences(request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """Update notification preferences for the current user."""
    body = await request.json()
    return await proxy_request(
        "PUT",
        "/preferences",
        json_body=body,
        headers={"X-User-Id": user.user_id}
    )


@router.delete("/preferences")
async def delete_preferences(user: AuthenticatedUser = Depends(require_auth)):
    """Delete notification preferences (reset to defaults)."""
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
async def get_ml_model_status(user: AuthenticatedUser = Depends(require_auth)):
    """Get ML anomaly detection model status."""
    return await proxy_request("GET", "/ml/status")


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
async def send_global_notification(request: Request, user: AuthenticatedUser = Depends(require_owner)):
    """
    Send a global notification to all users. Owner only.
    
    Expects a JSON body with:
    - title: str - The notification title
    - message: str - The notification message
    - event_type: str - The type of notification (e.g., 'scheduled_maintenance', 'system_status')
    - priority: str - The priority level ('low', 'medium', 'high', 'critical')
    """
    body = await request.json()
    
    # Build the network event for the notification service
    event = {
        "event_id": f"global-{user.user_id}-{body.get('title', 'notification')[:20]}",
        "event_type": body.get("event_type", "scheduled_maintenance"),
        "priority": body.get("priority", "medium"),
        "title": body.get("title", "System Notification"),
        "message": body.get("message", ""),
        "details": {
            "sent_by": user.username,
            "is_global": True,
        }
    }
    
    return await proxy_request(
        "POST",
        "/send-notification",
        json_body=event,
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

