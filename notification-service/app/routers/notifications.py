"""
API router for notification service endpoints.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Header

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
)
from ..services.notification_manager import notification_manager
from ..services.discord_service import discord_service, is_discord_configured, get_bot_invite_url
from ..services.email_service import is_email_configured
from ..services.anomaly_detector import anomaly_detector

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Preferences ====================

@router.get("/preferences", response_model=NotificationPreferences)
async def get_preferences(
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """Get notification preferences for the current user"""
    return notification_manager.get_preferences(x_user_id)


@router.put("/preferences", response_model=NotificationPreferences)
async def update_preferences(
    update: NotificationPreferencesUpdate,
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """Update notification preferences for the current user"""
    return notification_manager.update_preferences(x_user_id, update)


@router.delete("/preferences")
async def delete_preferences(
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """Delete notification preferences (reset to defaults)"""
    success = notification_manager.delete_preferences(x_user_id)
    return {"success": success}


# ==================== Service Status ====================

@router.get("/status")
async def get_service_status():
    """Get notification service status including available channels"""
    return {
        "email_configured": is_email_configured(),
        "discord_configured": is_discord_configured(),
        "discord_bot_connected": discord_service._ready.is_set() if discord_service._client else False,
        "ml_model_status": anomaly_detector.get_model_status().model_dump(),
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

@router.post("/test", response_model=TestNotificationResponse)
async def send_test_notification(
    request: TestNotificationRequest,
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """Send a test notification via a specific channel"""
    return await notification_manager.send_test_notification(x_user_id, request)


# ==================== History & Stats ====================

@router.get("/history", response_model=NotificationHistoryResponse)
async def get_notification_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """Get notification history for the current user"""
    return notification_manager.get_history(user_id=x_user_id, page=page, per_page=per_page)


@router.get("/stats", response_model=NotificationStatsResponse)
async def get_notification_stats(
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """Get notification statistics for the current user"""
    return notification_manager.get_stats(user_id=x_user_id)


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

