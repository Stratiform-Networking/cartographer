"""
API router for notification service endpoints.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import (
    DeviceBaseline,
    DiscordBotInfo,
    DiscordChannelsResponse,
    DiscordGuildsResponse,
    GlobalUserPreferences,
    GlobalUserPreferencesUpdate,
    MLModelStatus,
    NetworkEvent,
    NotificationHistoryResponse,
    NotificationPreferences,
    NotificationPreferencesUpdate,
    NotificationPriority,
    NotificationStatsResponse,
    NotificationType,
    ScheduledBroadcast,
    ScheduledBroadcastCreate,
    ScheduledBroadcastResponse,
    ScheduledBroadcastUpdate,
    TestNotificationRequest,
    TestNotificationResponse,
    get_default_priority_for_type,
)
from ..services.anomaly_detector import anomaly_detector
from ..services.discord_service import discord_service, get_bot_invite_url, is_discord_configured
from ..services.email_service import is_email_configured
from ..services.network_anomaly_detector import network_anomaly_detector_manager
from ..services.notification_manager import notification_manager
from ..services.version_checker import version_checker

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Preferences (per-network) ====================


@router.get("/networks/{network_id}/preferences", response_model=NotificationPreferences)
async def get_network_preferences(
    network_id: str,
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """Get notification preferences for a specific network"""
    return notification_manager.get_preferences(network_id)


@router.put("/networks/{network_id}/preferences", response_model=NotificationPreferences)
async def update_network_preferences(
    network_id: str,
    update: NotificationPreferencesUpdate,
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """Update notification preferences for a specific network"""
    return notification_manager.update_preferences(network_id, update)


@router.delete("/networks/{network_id}/preferences")
async def delete_network_preferences(
    network_id: str,
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
    return NotificationPreferences(
        network_id="00000000-0000-0000-0000-000000000000", owner_user_id=x_user_id
    )


# ==================== Service Status ====================


@router.get("/status")
async def get_service_status():
    """Get notification service status including available channels"""
    return {
        "email_configured": is_email_configured(),
        "discord_configured": is_discord_configured(),
        "discord_bot_connected": (
            discord_service._ready.is_set() if discord_service._client else False
        ),
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
    network_id: str,
    request: TestNotificationRequest,
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """Send a test notification for a specific network"""
    return await notification_manager.send_test_notification(network_id, request)


# ==================== History & Stats (per-network) ====================


@router.get("/networks/{network_id}/history", response_model=NotificationHistoryResponse)
async def get_network_notification_history(
    network_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """Get notification history for a specific network"""
    return notification_manager.get_history(network_id=network_id, page=page, per_page=per_page)


@router.get("/networks/{network_id}/stats", response_model=NotificationStatsResponse)
async def get_network_notification_stats(
    network_id: str,
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """Get notification statistics for a specific network"""
    return notification_manager.get_stats(network_id=network_id)


# ==================== Anomaly Detection ====================


@router.get("/ml/status", response_model=MLModelStatus)
async def get_ml_model_status(
    network_id: Optional[str] = Query(None, description="Network ID (UUID) for per-network stats")
):
    """Get ML anomaly detection model status"""
    if network_id is not None:
        # Return per-network stats
        return network_anomaly_detector_manager.get_stats(network_id)
    else:
        # Return global stats (legacy - for backwards compatibility)
        return anomaly_detector.get_model_status()


@router.get("/ml/baseline/{device_ip}", response_model=Optional[DeviceBaseline])
async def get_device_baseline(
    device_ip: str,
    network_id: str = Query(..., description="Network ID (UUID) this device belongs to"),
):
    """Get learned baseline for a specific device in a network"""
    detector = network_anomaly_detector_manager.get_detector(network_id)
    baseline = detector.get_device_baseline(device_ip)
    if not baseline:
        raise HTTPException(
            status_code=404,
            detail=f"No baseline found for device {device_ip} in network {network_id}",
        )
    return baseline


@router.post("/ml/feedback/false-positive")
async def mark_false_positive(event_id: str):
    """Mark an anomaly detection as a false positive (for model improvement)"""
    anomaly_detector.mark_false_positive(event_id)
    return {"success": True, "message": f"Event {event_id} marked as false positive"}


@router.delete("/ml/baseline/{device_ip}")
async def reset_device_baseline(
    device_ip: str,
    network_id: str = Query(..., description="Network ID (UUID) this device belongs to"),
):
    """Reset learned baseline for a specific device in a network"""
    detector = network_anomaly_detector_manager.get_detector(network_id)
    # Note: NetworkAnomalyDetector doesn't have reset_device yet - would need to add it
    # For now, log a warning
    logger.warning(
        f"Reset device baseline requested for {device_ip} in network {network_id} - not yet implemented"
    )
    return {
        "success": True,
        "message": f"Baseline reset for device {device_ip} in network {network_id} (per-network reset coming soon)",
    }


@router.delete("/ml/reset")
async def reset_all_ml_data(
    network_id: Optional[str] = Query(
        None, description="Network ID (UUID) to reset (or all if not provided)"
    )
):
    """Reset ML model data (use with caution)"""
    if network_id is not None:
        # Reset specific network
        detector = network_anomaly_detector_manager.get_detector(network_id)
        # Would need to add reset method to NetworkAnomalyDetector
        logger.warning(f"Reset ML data requested for network {network_id} - not yet implemented")
        return {
            "success": True,
            "message": f"ML model data reset for network {network_id} (coming soon)",
        }
    else:
        # Reset all (legacy)
        anomaly_detector.reset_all()
        return {"success": True, "message": "All ML model data reset"}


@router.post("/ml/sync-devices")
async def sync_current_devices(
    device_ips: List[str],
    network_id: str = Query(..., description="Network ID (UUID) these devices belong to"),
):
    """
    Sync the list of devices currently in a network.

    This should be called by the health service when devices are registered
    or when the device list changes. It ensures the ML model status only
    reports tracking devices that are actually present in the network.
    """
    detector = network_anomaly_detector_manager.get_detector(network_id)
    detector.sync_current_devices(device_ips)
    return {
        "success": True,
        "devices_synced": len(device_ips),
        "network_id": network_id,
        "message": f"Synced {len(device_ips)} devices for ML tracking in network {network_id}",
    }


# ==================== Health Check Processing ====================


async def _dispatch_event_to_network(
    db: AsyncSession,
    network_id: str,
    event: NetworkEvent,
) -> int:
    """
    Helper to dispatch an event to all users in a network.

    Returns the number of users successfully notified.
    """
    from ..services.notification_dispatch import notification_dispatch_service
    from ..services.user_preferences import user_preferences_service

    user_ids = await user_preferences_service.get_network_member_user_ids(db, network_id)

    if not user_ids:
        logger.warning(f"No users found for network {network_id}")
        return 0

    results = await notification_dispatch_service.send_to_network_users(
        db=db,
        network_id=network_id,
        user_ids=user_ids,
        event=event,
        scheduled_at=None,
    )

    successful = sum(1 for r in results.values() if any(rec.success for rec in r))
    logger.info(
        f"Dispatched notification to {successful}/{len(user_ids)} users in network {network_id}"
    )
    return successful


@router.post("/process-health-check")
async def process_health_check(
    device_ip: str,
    success: bool,
    network_id: str,
    latency_ms: Optional[float] = None,
    packet_loss: Optional[float] = None,
    device_name: Optional[str] = None,
    previous_state: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Process a health check result from the health service.

    This endpoint should be called by the health service after each check.
    It will train the ML model and potentially send notifications.

    Mass outage detection: When 3+ devices go offline within 60 seconds,
    notifications are aggregated into a single "mass outage" notification
    instead of individual alerts for each device.

    Args:
        device_ip: IP address of the device
        success: Whether the health check succeeded
        network_id: The network this device belongs to (required)
        latency_ms: Optional latency measurement
        packet_loss: Optional packet loss percentage
        device_name: Optional device name
        previous_state: Optional previous state (online/offline)
    """
    from ..services.mass_outage_detector import mass_outage_detector
    from ..services.network_anomaly_detector import network_anomaly_detector_manager

    # Process health check with per-network detector
    event = await network_anomaly_detector_manager.process_health_check(
        network_id=network_id,
        device_ip=device_ip,
        success=success,
        latency_ms=latency_ms,
        packet_loss=packet_loss,
        device_name=device_name,
        previous_state=previous_state,
    )

    events_dispatched = 0

    # Handle device coming back online - remove from mass outage buffer if pending
    if success:
        mass_outage_detector.remove_device(network_id, device_ip)

    # If event created, handle based on type
    if event:
        event.network_id = network_id
        logger.info(
            f"Network event created for network {network_id}: {event.event_type.value} - {event.title}"
        )

        try:
            if event.event_type == NotificationType.DEVICE_OFFLINE:
                # Record offline event for potential mass outage aggregation
                mass_outage_detector.record_offline_event(
                    network_id=network_id,
                    device_ip=device_ip,
                    device_name=device_name,
                    event=event,
                )

                # Check if we've reached mass outage threshold
                if mass_outage_detector.should_aggregate(network_id):
                    # Create aggregated mass outage event
                    mass_event = mass_outage_detector.flush_and_create_mass_outage_event(network_id)
                    if mass_event:
                        logger.info(
                            f"Mass outage detected for network {network_id}: "
                            f"{mass_event.details.get('total_affected', 0)} devices affected"
                        )
                        await _dispatch_event_to_network(db, network_id, mass_event)
                        events_dispatched = 1
                else:
                    # Not a mass outage yet - check for expired individual events
                    expired_events = mass_outage_detector.get_expired_events(network_id)
                    for expired_event in expired_events:
                        logger.info(
                            f"Dispatching expired individual offline notification for "
                            f"{expired_event.device_ip} in network {network_id}"
                        )
                        await _dispatch_event_to_network(db, network_id, expired_event)
                        events_dispatched += 1

            else:
                # Non-offline events (DEVICE_ONLINE, HIGH_LATENCY, etc.) dispatch immediately
                await _dispatch_event_to_network(db, network_id, event)
                events_dispatched = 1

        except Exception as e:
            logger.error(
                f"Failed to dispatch notification for network {network_id}: {e}", exc_info=True
            )

    return {
        "success": True,
        "event_created": event is not None,
        "events_dispatched": events_dispatched,
    }


@router.post("/networks/{network_id}/send-notification")
async def send_network_notification(
    network_id: str,
    request: Request,
):
    """
    Send a notification to a specific network (for broadcasts).

    Expects JSON body with:
    - Either: event: NetworkEvent object
    - Or: event fields directly (event_type, title, message, priority, etc.)
    - user_ids: Optional[List[str]] - List of user IDs who are network members

    If user_ids is provided, sends to those specific network members based on their preferences.
    Otherwise, sends to the network's configured notification channels.
    """
    body = await request.json()
    user_ids = body.get("user_ids")

    # Parse the event - support both formats
    if "event" in body:
        # Format 1: event object
        event_data = body.get("event")
        event = NetworkEvent(**event_data)
    else:
        # Format 2: event fields directly in body
        event = NetworkEvent(**body)

    # Ensure event has the correct network_id
    event.network_id = network_id

    if user_ids:
        # Send to specific network members based on their preferences
        logger.info(
            f"Broadcast request for network {network_id} to {len(user_ids)} users: {event.title}"
        )
        results = await notification_manager.send_notification_to_network_members(
            network_id, user_ids, event, force=True
        )

        # Count successful and failed records
        total_records = 0
        successful_records = 0
        failed_records = 0
        for user_id, records in results.items():
            for record in records:
                total_records += 1
                if record.success:
                    successful_records += 1
                else:
                    failed_records += 1

        success = successful_records > 0

        logger.info(
            f"Broadcast result for network {network_id}: "
            f"success={success}, users={len(results)}, "
            f"total_records={total_records}, successful={successful_records}, failed={failed_records}"
        )

        return {
            "success": success,
            "users_notified": len(results),
            "total_records": total_records,
            "successful_records": successful_records,
            "failed_records": failed_records,
            "network_id": network_id,
        }
    else:
        # Fallback to network-level preferences
        logger.info(f"Network-level notification request for network {network_id}: {event.title}")
        records = await notification_manager.send_notification_to_network(
            network_id, event, force=True
        )
        successful = [r for r in records if r.success]
        failed = [r for r in records if not r.success]

        logger.info(
            f"Network-level notification result for network {network_id}: "
            f"success={len(successful) > 0}, total={len(records)}, "
            f"successful={len(successful)}, failed={len(failed)}"
        )

        return {
            "success": len(successful) > 0,
            "total_records": len(records),
            "successful_records": len(successful),
            "failed_records": len(failed),
            "records": [r.model_dump() for r in records],
            "network_id": network_id,
        }


@router.post("/send-notification")
async def send_manual_notification(
    event: NetworkEvent,
    user_id: Optional[str] = None,
):
    """
    Manually send a notification (for testing or admin use).

    DEPRECATED: Use /networks/{network_id}/send-notification for network-scoped notifications.
    """
    if user_id:
        # Legacy support - try to find network_id from user_id (not recommended)
        logger.warning("send_notification with user_id is deprecated, use network_id instead")
        # For backwards compatibility, we'll skip this
        return {
            "success": False,
            "error": "user_id parameter is deprecated, use network_id instead",
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
        from datetime import timezone as dt_timezone

        scheduled_time = scheduled_time.astimezone(dt_timezone.utc).replace(tzinfo=None)

    if scheduled_time <= now:
        raise HTTPException(status_code=400, detail="Scheduled time must be in the future")

    logger.info(
        f"Creating scheduled broadcast: title='{request.title}', "
        f"scheduled_at={request.scheduled_at.isoformat()}, timezone={request.timezone}"
    )

    return notification_manager.create_scheduled_broadcast(
        title=request.title,
        message=request.message,
        scheduled_at=request.scheduled_at,
        created_by=x_username,
        network_id=request.network_id,
        event_type=request.event_type,
        priority=request.priority,
        timezone=request.timezone,
    )


@router.get("/scheduled/{broadcast_id}", response_model=ScheduledBroadcast)
async def get_scheduled_broadcast(broadcast_id: str):
    """Get a specific scheduled broadcast"""
    broadcast = notification_manager.get_scheduled_broadcast(broadcast_id)
    if not broadcast:
        raise HTTPException(status_code=404, detail="Scheduled broadcast not found")
    return broadcast


@router.patch("/scheduled/{broadcast_id}", response_model=ScheduledBroadcast)
async def update_scheduled_broadcast(
    broadcast_id: str,
    request: ScheduledBroadcastUpdate,
):
    """
    Update a scheduled broadcast (only pending broadcasts can be updated).

    Only the fields provided in the request will be updated.
    """
    # If updating scheduled_at, validate it's in the future
    if request.scheduled_at is not None:
        scheduled_time = request.scheduled_at
        now = datetime.utcnow()

        if scheduled_time.tzinfo is not None:
            from datetime import timezone as dt_timezone

            scheduled_time = scheduled_time.astimezone(dt_timezone.utc).replace(tzinfo=None)

        if scheduled_time <= now:
            raise HTTPException(status_code=400, detail="Scheduled time must be in the future")

    broadcast = notification_manager.update_scheduled_broadcast(broadcast_id, request)
    if not broadcast:
        raise HTTPException(
            status_code=400, detail="Cannot update broadcast (not found or not pending)"
        )

    logger.info(f"Updated scheduled broadcast: {broadcast_id}")
    return broadcast


@router.post("/scheduled/{broadcast_id}/cancel")
async def cancel_scheduled_broadcast(broadcast_id: str):
    """Cancel a scheduled broadcast"""
    success = notification_manager.cancel_scheduled_broadcast(broadcast_id)
    if not success:
        raise HTTPException(
            status_code=400, detail="Cannot cancel broadcast (not found or already sent)"
        )
    return {"success": True, "message": "Broadcast cancelled"}


@router.delete("/scheduled/{broadcast_id}")
async def delete_scheduled_broadcast(broadcast_id: str):
    """Delete a scheduled broadcast (must be cancelled or completed first)"""
    success = notification_manager.delete_scheduled_broadcast(broadcast_id)
    if not success:
        raise HTTPException(
            status_code=400, detail="Cannot delete broadcast (not found or still pending)"
        )
    return {"success": True, "message": "Broadcast deleted"}


@router.post("/scheduled/{broadcast_id}/seen")
async def mark_broadcast_seen(broadcast_id: str):
    """
    Mark a sent broadcast as seen by the user.
    Sets the seen_at timestamp if not already set.
    After being marked seen, the broadcast will be hidden after a short delay.
    """
    broadcast = notification_manager.mark_broadcast_seen(broadcast_id)
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    return {
        "success": True,
        "broadcast_id": broadcast_id,
        "seen_at": broadcast.seen_at.isoformat() if broadcast.seen_at else None,
    }


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


# ==================== Global User Preferences (for Cartographer Up/Down) ====================


@router.get("/global/preferences", response_model=GlobalUserPreferences)
async def get_global_preferences(
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """Get global notification preferences for the current user (Cartographer Up/Down)"""
    return notification_manager.get_global_preferences(x_user_id)


@router.put("/global/preferences", response_model=GlobalUserPreferences)
async def update_global_preferences(
    update: GlobalUserPreferencesUpdate,
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """Update global notification preferences for the current user (Cartographer Up/Down)"""
    return notification_manager.update_global_preferences(x_user_id, update)


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

    NOTE: This endpoint now uses the new Cartographer Status service.
    """
    from ..models import (
        NetworkEvent,
        NotificationPriority,
        NotificationType,
        get_default_priority_for_type,
    )
    from ..services.cartographer_status import cartographer_status_service
    from ..services.email_service import is_email_configured, send_notification_email

    if not is_email_configured():
        return {
            "success": False,
            "subscribers_notified": 0,
            "error": "Email service not configured",
        }

    downtime_str = ""
    if downtime_minutes:
        downtime_str = f"Service was down for approximately {downtime_minutes} minutes. "

    event = NetworkEvent(
        event_type=NotificationType.CARTOGRAPHER_UP,
        priority=get_default_priority_for_type(NotificationType.CARTOGRAPHER_UP),
        title="Cartographer is Back Online",
        message=message or f"{downtime_str}The Cartographer monitoring service is now operational.",
        network_id=None,
        details={
            "service": "cartographer",
            "downtime_minutes": downtime_minutes,
            "reported_at": datetime.utcnow().isoformat(),
        },
    )

    subscribers = cartographer_status_service.get_subscribers_for_event(
        NotificationType.CARTOGRAPHER_UP
    )
    notification_id = str(uuid.uuid4())
    successful = 0

    for subscriber in subscribers:
        try:
            record = await send_notification_email(
                to_email=subscriber.email_address,
                event=event,
                notification_id=notification_id,
            )
            if record.success:
                successful += 1
        except Exception as e:
            logger.error(f"Failed to send to {subscriber.email_address}: {e}")

    return {
        "success": successful > 0,
        "subscribers_notified": successful,
        "total_subscribers": len(subscribers),
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

    NOTE: This endpoint now uses the new Cartographer Status service.
    """
    from ..models import (
        NetworkEvent,
        NotificationPriority,
        NotificationType,
        get_default_priority_for_type,
    )
    from ..services.cartographer_status import cartographer_status_service
    from ..services.email_service import is_email_configured, send_notification_email

    if not is_email_configured():
        return {
            "success": False,
            "subscribers_notified": 0,
            "error": "Email service not configured",
        }

    services_str = ""
    if affected_services:
        services_str = f"Affected services: {', '.join(affected_services)}. "

    event = NetworkEvent(
        event_type=NotificationType.CARTOGRAPHER_DOWN,
        priority=get_default_priority_for_type(NotificationType.CARTOGRAPHER_DOWN),
        title="Cartographer Service Alert",
        message=message or f"{services_str}The Cartographer monitoring service may be unavailable.",
        network_id=None,
        details={
            "service": "cartographer",
            "affected_services": affected_services or [],
            "reported_at": datetime.utcnow().isoformat(),
        },
    )

    subscribers = cartographer_status_service.get_subscribers_for_event(
        NotificationType.CARTOGRAPHER_DOWN
    )
    notification_id = str(uuid.uuid4())
    successful = 0

    for subscriber in subscribers:
        try:
            record = await send_notification_email(
                to_email=subscriber.email_address,
                event=event,
                notification_id=notification_id,
            )
            if record.success:
                successful += 1
        except Exception as e:
            logger.error(f"Failed to send to {subscriber.email_address}: {e}")

    return {
        "success": successful > 0,
        "subscribers_notified": successful,
        "total_subscribers": len(subscribers),
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
async def check_for_updates(send_notification: bool = True):
    """
    Manually trigger a version check and get results.

    This will check GitHub for the latest version and return whether
    an update is available. If an update is found and send_notification is True,
    this will also trigger notifications to all networks with SYSTEM_STATUS enabled.

    Args:
        send_notification: If True (default), send notifications when update found
    """
    return await version_checker.check_now(send_notification=send_notification)


@router.post("/version/notify")
async def send_version_notification():
    """
    Manually send a version update notification to all subscribed users.

    This will check for updates and force-send notifications regardless
    of whether users have already been notified about this version.

    Networks must have SYSTEM_STATUS in their enabled_notification_types
    to receive version update notifications.
    """
    # Force send notification (bypass "already notified" check)
    return await version_checker.check_now(send_notification=True, force=True)
