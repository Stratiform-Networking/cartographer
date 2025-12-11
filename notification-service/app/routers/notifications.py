"""
API router for notification service endpoints.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Header

from datetime import datetime
from ..models import (
    NotificationPreferences,
    NotificationPreferencesUpdate,
    NotificationHistoryResponse,
    NotificationStatsResponse,
    TestNotificationRequest,
    TestNotificationResponse,
    DiscordBotInfo,
    DiscordGuildsResponse,
    DiscordChannelsResponse,
    MLModelStatus,
    DeviceBaseline,
    NetworkEvent,
    NotificationType,
    NotificationPriority,
    ScheduledBroadcast,
    ScheduledBroadcastCreate,
    ScheduledBroadcastResponse,
    get_default_priority_for_type,
)
from ..services.notification_manager import notification_manager
from ..services.discord_service import discord_service, is_discord_configured, get_bot_invite_url
from ..services.email_service import is_email_configured
from ..services.anomaly_detector import anomaly_detector
from ..services.version_checker import version_checker

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Preferences (per-network) ====================

@router.get("/networks/{network_id}/preferences", response_model=NotificationPreferences)
async def get_network_preferences(
    network_id: int,
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """Get notification preferences for a specific network"""
    return notification_manager.get_preferences(network_id)


@router.put("/networks/{network_id}/preferences", response_model=NotificationPreferences)
async def update_network_preferences(
    network_id: int,
    update: NotificationPreferencesUpdate,
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """Update notification preferences for a specific network"""
    return notification_manager.update_preferences(network_id, update)


@router.delete("/networks/{network_id}/preferences")
async def delete_network_preferences(
    network_id: int,
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """Delete notification preferences for a network (reset to defaults)"""
    success = notification_manager.delete_preferences(network_id)
    return {"success": success}


# Legacy endpoints (for backwards compatibility during migration)
@router.get("/preferences", response_model=NotificationPreferences, deprecated=True)
async def get_preferences_legacy(
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """DEPRECATED: Use /networks/{network_id}/preferences instead"""
    # Return default preferences for backwards compatibility
    return NotificationPreferences(network_id=0, owner_user_id=x_user_id)


# ==================== Service Status ====================

@router.get("/status")
async def get_service_status():
    """Get notification service status including available channels"""
    return {
        "email_configured": is_email_configured(),
        "discord_configured": is_discord_configured(),
        "discord_bot_connected": discord_service._ready.is_set() if discord_service._client else False,
        "ml_model_status": anomaly_detector.get_model_status().model_dump(),
        "version_checker": version_checker.get_status(),
    }


# ==================== Discord Integration ====================

@router.get("/discord/info", response_model=DiscordBotInfo)
async def get_discord_info():
    """Get Discord bot information and invite URL"""
    return discord_service.get_bot_info()


@router.get("/discord/guilds", response_model=DiscordGuildsResponse)
async def get_discord_guilds():
    """Get list of Discord servers (guilds) the bot is in"""
    if not is_discord_configured():
        raise HTTPException(status_code=503, detail="Discord not configured")
    
    guilds = await discord_service.get_guilds()
    return DiscordGuildsResponse(guilds=guilds)


@router.get("/discord/guilds/{guild_id}/channels", response_model=DiscordChannelsResponse)
async def get_discord_channels(guild_id: str):
    """Get list of text channels in a Discord server"""
    if not is_discord_configured():
        raise HTTPException(status_code=503, detail="Discord not configured")
    
    channels = await discord_service.get_channels(guild_id)
    return DiscordChannelsResponse(guild_id=guild_id, channels=channels)


@router.get("/discord/invite-url")
async def get_discord_invite_url():
    """Get the bot invite URL"""
    url = get_bot_invite_url()
    if not url:
        raise HTTPException(status_code=503, detail="Discord client ID not configured")
    
    return {"invite_url": url}


# ==================== Testing ====================

@router.post("/networks/{network_id}/test", response_model=TestNotificationResponse)
async def send_test_notification(
    network_id: int,
    request: TestNotificationRequest,
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """Send a test notification for a specific network"""
    return await notification_manager.send_test_notification(network_id, request)


# ==================== History & Stats (per-network) ====================

@router.get("/networks/{network_id}/history", response_model=NotificationHistoryResponse)
async def get_network_notification_history(
    network_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """Get notification history for a specific network"""
    return notification_manager.get_history(network_id=network_id, page=page, per_page=per_page)


@router.get("/networks/{network_id}/stats", response_model=NotificationStatsResponse)
async def get_network_notification_stats(
    network_id: int,
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """Get notification statistics for a specific network"""
    return notification_manager.get_stats(network_id=network_id)


# ==================== Anomaly Detection ====================

@router.get("/ml/status", response_model=MLModelStatus)
async def get_ml_model_status():
    """Get ML anomaly detection model status"""
    return anomaly_detector.get_model_status()


@router.get("/ml/baseline/{device_ip}", response_model=Optional[DeviceBaseline])
async def get_device_baseline(device_ip: str):
    """Get learned baseline for a specific device"""
    baseline = anomaly_detector.get_device_baseline(device_ip)
    if not baseline:
        raise HTTPException(status_code=404, detail=f"No baseline found for device {device_ip}")
    return baseline


@router.post("/ml/feedback/false-positive")
async def mark_false_positive(event_id: str):
    """Mark an anomaly detection as a false positive (for model improvement)"""
    anomaly_detector.mark_false_positive(event_id)
    return {"success": True, "message": f"Event {event_id} marked as false positive"}


@router.delete("/ml/baseline/{device_ip}")
async def reset_device_baseline(device_ip: str):
    """Reset learned baseline for a specific device"""
    anomaly_detector.reset_device(device_ip)
    return {"success": True, "message": f"Baseline reset for device {device_ip}"}


@router.delete("/ml/reset")
async def reset_all_ml_data():
    """Reset all ML model data (use with caution)"""
    anomaly_detector.reset_all()
    return {"success": True, "message": "All ML data reset"}


@router.post("/ml/sync-devices")
async def sync_current_devices(device_ips: List[str]):
    """
    Sync the list of devices currently in the network.
    
    This should be called by the health service when devices are registered
    or when the device list changes. It ensures the ML model status only
    reports tracking devices that are actually present in the network.
    """
    anomaly_detector.sync_current_devices(device_ips)
    return {
        "success": True,
        "devices_synced": len(device_ips),
        "message": f"Synced {len(device_ips)} devices for ML tracking",
    }


# ==================== Health Check Processing ====================

@router.post("/process-health-check")
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
    
    This endpoint should be called by the health service after each check.
    It will train the ML model and potentially send notifications.
    """
    await notification_manager.process_health_check(
        device_ip=device_ip,
        success=success,
        latency_ms=latency_ms,
        packet_loss=packet_loss,
        device_name=device_name,
        previous_state=previous_state,
    )
    
    return {"success": True}


@router.post("/send-notification")
async def send_manual_notification(
    event: NetworkEvent,
    user_id: Optional[str] = None,
):
    """
    Manually send a notification (for testing or admin use).
    
    If user_id is provided, sends only to that user.
    Otherwise, broadcasts to all users.
    """
    if user_id:
        records = await notification_manager.send_notification(user_id, event, force=True)
        return {
            "success": len([r for r in records if r.success]) > 0,
            "records": [r.model_dump() for r in records],
        }
    else:
        results = await notification_manager.broadcast_notification(event)
        return {
            "success": True,
            "users_notified": len(results),
        }


# ==================== Scheduled Broadcasts ====================

@router.get("/scheduled", response_model=ScheduledBroadcastResponse)
async def get_scheduled_broadcasts(
    include_completed: bool = Query(False, description="Include sent/cancelled broadcasts"),
):
    """Get all scheduled broadcasts"""
    return notification_manager.get_scheduled_broadcasts(include_completed=include_completed)


@router.post("/scheduled", response_model=ScheduledBroadcast)
async def create_scheduled_broadcast(
    request: ScheduledBroadcastCreate,
    x_username: str = Header(..., description="Username of the owner creating the broadcast"),
):
    """Create a new scheduled broadcast (owner only)"""
    # Validate scheduled time is in the future
    # Handle both timezone-aware and naive datetimes
    scheduled_time = request.scheduled_at
    now = datetime.utcnow()
    
    # If scheduled_time is timezone-aware, convert to naive UTC for comparison
    if scheduled_time.tzinfo is not None:
        scheduled_time = scheduled_time.replace(tzinfo=None)
    
    if scheduled_time <= now:
        raise HTTPException(status_code=400, detail="Scheduled time must be in the future")
    
    return notification_manager.create_scheduled_broadcast(
        title=request.title,
        message=request.message,
        scheduled_at=request.scheduled_at,
        created_by=x_username,
        event_type=request.event_type,
        priority=request.priority,
    )


@router.get("/scheduled/{broadcast_id}", response_model=ScheduledBroadcast)
async def get_scheduled_broadcast(broadcast_id: str):
    """Get a specific scheduled broadcast"""
    broadcast = notification_manager.get_scheduled_broadcast(broadcast_id)
    if not broadcast:
        raise HTTPException(status_code=404, detail="Scheduled broadcast not found")
    return broadcast


@router.post("/scheduled/{broadcast_id}/cancel")
async def cancel_scheduled_broadcast(broadcast_id: str):
    """Cancel a scheduled broadcast"""
    success = notification_manager.cancel_scheduled_broadcast(broadcast_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel broadcast (not found or already sent)")
    return {"success": True, "message": "Broadcast cancelled"}


@router.delete("/scheduled/{broadcast_id}")
async def delete_scheduled_broadcast(broadcast_id: str):
    """Delete a scheduled broadcast (must be cancelled or completed first)"""
    success = notification_manager.delete_scheduled_broadcast(broadcast_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot delete broadcast (not found or still pending)")
    return {"success": True, "message": "Broadcast deleted"}


# ==================== Silenced Devices (Monitoring Disabled) ====================

@router.get("/silenced-devices")
async def get_silenced_devices():
    """Get list of devices with notifications silenced (monitoring disabled)"""
    return {"devices": notification_manager.get_silenced_devices()}


@router.post("/silenced-devices")
async def set_silenced_devices(device_ips: List[str]):
    """Set the full list of silenced devices"""
    notification_manager.set_silenced_devices(device_ips)
    return {"success": True, "count": len(device_ips)}


@router.post("/silenced-devices/{device_ip}")
async def silence_device(device_ip: str):
    """Silence notifications for a specific device (disable monitoring)"""
    success = notification_manager.silence_device(device_ip)
    return {"success": True, "already_silenced": not success}


@router.delete("/silenced-devices/{device_ip}")
async def unsilence_device(device_ip: str):
    """Re-enable notifications for a device (enable monitoring)"""
    success = notification_manager.unsilence_device(device_ip)
    return {"success": True, "was_silenced": success}


@router.get("/silenced-devices/{device_ip}")
async def check_device_silenced(device_ip: str):
    """Check if a specific device is silenced"""
    is_silenced = notification_manager.is_device_silenced(device_ip)
    return {"device_ip": device_ip, "silenced": is_silenced}


# ==================== Cartographer Service Status Notifications ====================

@router.post("/service-status/up")
async def notify_cartographer_up(
    message: Optional[str] = None,
    downtime_minutes: Optional[int] = None,
):
    """
    Send a notification that Cartographer is back online.
    
    This can be called by external monitoring systems when they detect
    the service has recovered from downtime.
    """
    downtime_str = ""
    if downtime_minutes:
        downtime_str = f"Service was down for approximately {downtime_minutes} minutes. "
    
    event = NetworkEvent(
        event_type=NotificationType.CARTOGRAPHER_UP,
        priority=get_default_priority_for_type(NotificationType.CARTOGRAPHER_UP),
        title="Cartographer is Back Online",
        message=message or f"{downtime_str}The Cartographer monitoring service is now operational.",
        details={
            "service": "cartographer",
            "downtime_minutes": downtime_minutes,
            "reported_at": datetime.utcnow().isoformat(),
        },
    )
    
    results = await notification_manager.broadcast_notification(event)
    return {
        "success": True,
        "users_notified": len(results),
    }


@router.post("/service-status/down")
async def notify_cartographer_down(
    message: Optional[str] = None,
    affected_services: Optional[List[str]] = None,
):
    """
    Send a notification that Cartographer is going down or has gone down.
    
    This can be called by:
    - External monitoring systems when they detect the service is unreachable
    - Administrators before planned maintenance
    - The service itself before a graceful shutdown
    """
    services_str = ""
    if affected_services:
        services_str = f"Affected services: {', '.join(affected_services)}. "
    
    event = NetworkEvent(
        event_type=NotificationType.CARTOGRAPHER_DOWN,
        priority=get_default_priority_for_type(NotificationType.CARTOGRAPHER_DOWN),
        title="Cartographer Service Alert",
        message=message or f"{services_str}The Cartographer monitoring service may be unavailable.",
        details={
            "service": "cartographer",
            "affected_services": affected_services or [],
            "reported_at": datetime.utcnow().isoformat(),
        },
    )
    
    results = await notification_manager.broadcast_notification(event)
    return {
        "success": True,
        "users_notified": len(results),
    }


# ==================== Version Update Notifications ====================

@router.get("/version")
async def get_version_status():
    """
    Get current version status and last check info.
    
    Returns information about the current version, latest available version,
    and whether an update is available.
    """
    return version_checker.get_status()


@router.post("/version/check")
async def check_for_updates():
    """
    Manually trigger a version check and get results.
    
    This will check GitHub for the latest version and return whether
    an update is available. If an update is found and users haven't
    been notified yet, this will also trigger notifications.
    """
    return await version_checker.check_now()


@router.post("/version/notify")
async def send_version_notification():
    """
    Manually send a version update notification to all subscribed users.
    
    This will check for updates and force-send notifications regardless
    of whether users have already been notified about this version.
    """
    # First check for the latest version
    result = await version_checker.check_now()
    
    if not result.get("success"):
        return {
            "success": False,
            "error": result.get("error", "Failed to check for updates"),
        }
    
    if not result.get("has_update"):
        return {
            "success": False,
            "message": "No update available",
            "current_version": result.get("current_version"),
            "latest_version": result.get("latest_version"),
        }
    
    # Import the helper functions from version_checker
    from ..services.version_checker import (
        get_update_priority,
        get_update_title,
        get_update_message,
        CHANGELOG_URL,
    )
    
    update_type = result.get("update_type")
    current_version = result.get("current_version")
    latest_version = result.get("latest_version")
    
    # Create and send the notification
    event = NetworkEvent(
        event_type=NotificationType.SYSTEM_STATUS,
        priority=get_update_priority(update_type),
        title=get_update_title(update_type, latest_version),
        message=get_update_message(update_type, current_version, latest_version),
        details={
            "update_type": update_type,
            "current_version": current_version,
            "latest_version": latest_version,
            "changelog_url": CHANGELOG_URL,
            "is_version_update": True,
            "manual_trigger": True,
        },
    )
    
    results = await notification_manager.broadcast_notification(event)
    
    return {
        "success": True,
        "users_notified": len(results),
        "current_version": current_version,
        "latest_version": latest_version,
        "update_type": update_type,
    }

