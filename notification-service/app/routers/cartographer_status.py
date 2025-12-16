"""
API endpoints for Cartographer status notifications (Up/Down).

This is a separate system from network-scoped notifications.
"""

import uuid
import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from ..services.cartographer_status import cartographer_status_service, CartographerStatusSubscription
from ..services.email_service import send_notification_email, is_email_configured
from ..services.discord_service import discord_service, is_discord_configured
from ..models import NetworkEvent, NotificationType, NotificationPriority, get_default_priority_for_type, DiscordConfig, DiscordDeliveryMethod, DiscordChannelConfig

logger = logging.getLogger(__name__)


class CartographerStatusNotifyRequest(BaseModel):
    """Request model for Cartographer status notification"""
    event_type: str  # "up" or "down"
    message: Optional[str] = None
    downtime_minutes: Optional[int] = None
    affected_services: Optional[List[str]] = None

router = APIRouter()


@router.get("/subscription")
async def get_cartographer_status_subscription(
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """Get the user's Cartographer status subscription"""
    subscription = cartographer_status_service.get_subscription(x_user_id)
    
    if not subscription:
        # Return default (not subscribed)
        return {
            "user_id": x_user_id,
            "email_address": None,
            "cartographer_up_enabled": True,
            "cartographer_down_enabled": True,
            "cartographer_up_priority": "medium",
            "cartographer_down_priority": "critical",
            "email_enabled": False,
            "discord_enabled": False,
            "discord_delivery_method": "dm",
            "discord_guild_id": None,
            "discord_channel_id": None,
            "discord_user_id": None,
            "minimum_priority": "medium",
            "quiet_hours_enabled": False,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00",
            "quiet_hours_bypass_priority": None,
            "timezone": None,
            "subscribed": False,
        }
    
    return {
        "user_id": subscription.user_id,
        "email_address": subscription.email_address,
        "cartographer_up_enabled": subscription.cartographer_up_enabled,
        "cartographer_down_enabled": subscription.cartographer_down_enabled,
        "cartographer_up_priority": subscription.cartographer_up_priority,
        "cartographer_down_priority": subscription.cartographer_down_priority,
        "email_enabled": subscription.email_enabled,
        "discord_enabled": subscription.discord_enabled,
        "discord_delivery_method": subscription.discord_delivery_method,
        "discord_guild_id": subscription.discord_guild_id,
        "discord_channel_id": subscription.discord_channel_id,
        "discord_user_id": subscription.discord_user_id,
        "minimum_priority": subscription.minimum_priority,
        "quiet_hours_enabled": subscription.quiet_hours_enabled,
        "quiet_hours_start": subscription.quiet_hours_start,
        "quiet_hours_end": subscription.quiet_hours_end,
        "quiet_hours_bypass_priority": subscription.quiet_hours_bypass_priority,
        "timezone": subscription.timezone,
        "subscribed": True,
        "created_at": subscription.created_at.isoformat(),
        "updated_at": subscription.updated_at.isoformat(),
    }


class CreateSubscriptionRequest(BaseModel):
    """Request model for creating a subscription"""
    email_address: str
    cartographer_up_enabled: bool = True
    cartographer_down_enabled: bool = True
    cartographer_up_priority: str = "medium"
    cartographer_down_priority: str = "critical"
    email_enabled: bool = False
    discord_enabled: bool = False
    discord_delivery_method: str = "dm"
    discord_guild_id: Optional[str] = None
    discord_channel_id: Optional[str] = None
    discord_user_id: Optional[str] = None
    minimum_priority: str = "medium"
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "08:00"
    quiet_hours_bypass_priority: Optional[str] = None
    timezone: Optional[str] = None


@router.post("/subscription")
async def create_cartographer_status_subscription(
    request: CreateSubscriptionRequest,
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """Create or update Cartographer status subscription"""
    if not request.email_address:
        raise HTTPException(status_code=400, detail="email_address is required")
    
    if not is_email_configured():
        raise HTTPException(
            status_code=503,
            detail="Email service is not configured. Please contact your administrator."
        )
    
    subscription = cartographer_status_service.create_or_update_subscription(
        user_id=x_user_id,
        email_address=request.email_address,
        cartographer_up_enabled=request.cartographer_up_enabled,
        cartographer_down_enabled=request.cartographer_down_enabled,
        cartographer_up_priority=request.cartographer_up_priority,
        cartographer_down_priority=request.cartographer_down_priority,
        email_enabled=request.email_enabled,
        discord_enabled=request.discord_enabled,
        discord_delivery_method=request.discord_delivery_method,
        discord_guild_id=request.discord_guild_id,
        discord_channel_id=request.discord_channel_id,
        discord_user_id=request.discord_user_id,
        minimum_priority=request.minimum_priority,
        quiet_hours_enabled=request.quiet_hours_enabled,
        quiet_hours_start=request.quiet_hours_start,
        quiet_hours_end=request.quiet_hours_end,
        quiet_hours_bypass_priority=request.quiet_hours_bypass_priority,
        timezone=request.timezone,
        _bypass_priority_provided=True,
        _timezone_provided=True,
        _discord_guild_id_provided=True,
        _discord_channel_id_provided=True,
        _discord_user_id_provided=True,
    )
    
    return {
        "user_id": subscription.user_id,
        "email_address": subscription.email_address,
        "cartographer_up_enabled": subscription.cartographer_up_enabled,
        "cartographer_down_enabled": subscription.cartographer_down_enabled,
        "cartographer_up_priority": subscription.cartographer_up_priority,
        "cartographer_down_priority": subscription.cartographer_down_priority,
        "email_enabled": subscription.email_enabled,
        "discord_enabled": subscription.discord_enabled,
        "discord_delivery_method": subscription.discord_delivery_method,
        "discord_guild_id": subscription.discord_guild_id,
        "discord_channel_id": subscription.discord_channel_id,
        "discord_user_id": subscription.discord_user_id,
        "minimum_priority": subscription.minimum_priority,
        "quiet_hours_enabled": subscription.quiet_hours_enabled,
        "quiet_hours_start": subscription.quiet_hours_start,
        "quiet_hours_end": subscription.quiet_hours_end,
        "quiet_hours_bypass_priority": subscription.quiet_hours_bypass_priority,
        "timezone": subscription.timezone,
        "subscribed": True,
        "created_at": subscription.created_at.isoformat(),
        "updated_at": subscription.updated_at.isoformat(),
    }


class UpdateSubscriptionRequest(BaseModel):
    """Request model for updating a subscription"""
    email_address: Optional[str] = None
    cartographer_up_enabled: Optional[bool] = None
    cartographer_down_enabled: Optional[bool] = None
    cartographer_up_priority: Optional[str] = None
    cartographer_down_priority: Optional[str] = None
    email_enabled: Optional[bool] = None
    discord_enabled: Optional[bool] = None
    discord_delivery_method: Optional[str] = None
    discord_guild_id: Optional[str] = None
    discord_channel_id: Optional[str] = None
    discord_user_id: Optional[str] = None
    minimum_priority: Optional[str] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    quiet_hours_bypass_priority: Optional[str] = None
    timezone: Optional[str] = None


@router.put("/subscription")
async def update_cartographer_status_subscription(
    request: UpdateSubscriptionRequest,
    x_user_id: str = Header(..., description="User ID from auth service"),
    x_user_email: str = Header(None, description="User email from auth service"),
):
    """Update Cartographer status subscription (creates if not exists)"""
    subscription = cartographer_status_service.get_subscription(x_user_id)
    
    # If no subscription exists, we'll create one - determine email to use
    email_to_use = request.email_address
    if not subscription and not email_to_use:
        # Use email from header or a placeholder for new subscriptions
        email_to_use = x_user_email or f"{x_user_id}@cartographer.local"
        logger.info(f"Creating new subscription for user {x_user_id} with email {email_to_use}")
    
    # Validate email if provided
    if request.email_address is not None and not request.email_address:
        raise HTTPException(status_code=400, detail="email_address cannot be empty")
    
    # Check if nullable fields were explicitly provided in the request
    request_dict = request.model_dump(exclude_unset=True)
    bypass_provided = "quiet_hours_bypass_priority" in request_dict
    timezone_provided = "timezone" in request_dict
    discord_guild_id_provided = "discord_guild_id" in request_dict
    discord_channel_id_provided = "discord_channel_id" in request_dict
    discord_user_id_provided = "discord_user_id" in request_dict
    
    updated = cartographer_status_service.create_or_update_subscription(
        user_id=x_user_id,
        email_address=email_to_use,
        cartographer_up_enabled=request.cartographer_up_enabled,
        cartographer_down_enabled=request.cartographer_down_enabled,
        cartographer_up_priority=request.cartographer_up_priority,
        cartographer_down_priority=request.cartographer_down_priority,
        email_enabled=request.email_enabled,
        discord_enabled=request.discord_enabled,
        discord_delivery_method=request.discord_delivery_method,
        discord_guild_id=request.discord_guild_id,
        discord_channel_id=request.discord_channel_id,
        discord_user_id=request.discord_user_id,
        minimum_priority=request.minimum_priority,
        quiet_hours_enabled=request.quiet_hours_enabled,
        quiet_hours_start=request.quiet_hours_start,
        quiet_hours_end=request.quiet_hours_end,
        quiet_hours_bypass_priority=request.quiet_hours_bypass_priority,
        timezone=request.timezone,
        _bypass_priority_provided=bypass_provided,
        _timezone_provided=timezone_provided,
        _discord_guild_id_provided=discord_guild_id_provided,
        _discord_channel_id_provided=discord_channel_id_provided,
        _discord_user_id_provided=discord_user_id_provided,
    )
    
    return {
        "user_id": updated.user_id,
        "email_address": updated.email_address,
        "cartographer_up_enabled": updated.cartographer_up_enabled,
        "cartographer_down_enabled": updated.cartographer_down_enabled,
        "cartographer_up_priority": updated.cartographer_up_priority,
        "cartographer_down_priority": updated.cartographer_down_priority,
        "email_enabled": updated.email_enabled,
        "discord_enabled": updated.discord_enabled,
        "discord_delivery_method": updated.discord_delivery_method,
        "discord_guild_id": updated.discord_guild_id,
        "discord_channel_id": updated.discord_channel_id,
        "discord_user_id": updated.discord_user_id,
        "minimum_priority": updated.minimum_priority,
        "quiet_hours_enabled": updated.quiet_hours_enabled,
        "quiet_hours_start": updated.quiet_hours_start,
        "quiet_hours_end": updated.quiet_hours_end,
        "quiet_hours_bypass_priority": updated.quiet_hours_bypass_priority,
        "timezone": updated.timezone,
        "subscribed": True,
        "created_at": updated.created_at.isoformat(),
        "updated_at": updated.updated_at.isoformat(),
    }


@router.delete("/subscription")
async def delete_cartographer_status_subscription(
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """Delete Cartographer status subscription"""
    success = cartographer_status_service.delete_subscription(x_user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return {"success": True, "message": "Subscription deleted"}


@router.post("/notify")
async def notify_cartographer_status(
    request: CartographerStatusNotifyRequest,
):
    """
    Send Cartographer status notification to all subscribers.
    
    This endpoint is called by the service itself or external monitoring.
    """
    # Map event type string to NotificationType
    event_type_lower = request.event_type.lower()
    if event_type_lower == "up":
        notification_type = NotificationType.CARTOGRAPHER_UP
    elif event_type_lower == "down":
        notification_type = NotificationType.CARTOGRAPHER_DOWN
    else:
        raise HTTPException(status_code=400, detail="event_type must be 'up' or 'down'")
    
    # Build message
    if notification_type == NotificationType.CARTOGRAPHER_UP:
        downtime_str = ""
        if request.downtime_minutes:
            downtime_str = f"Service was down for approximately {request.downtime_minutes} minutes. "
        title = "Cartographer is Back Online"
        default_message = f"{downtime_str}The Cartographer monitoring service is now operational."
    else:
        services_str = ""
        if request.affected_services:
            services_str = f"Affected services: {', '.join(request.affected_services)}. "
        title = "Cartographer Service Alert"
        default_message = f"{services_str}The Cartographer monitoring service may be unavailable."
    
    event = NetworkEvent(
        event_type=notification_type,
        priority=get_default_priority_for_type(notification_type),
        title=title,
        message=request.message or default_message,
        network_id=None,  # Not network-specific
        details={
            "service": "cartographer",
            "downtime_minutes": request.downtime_minutes,
            "affected_services": request.affected_services or [],
            "reported_at": datetime.utcnow().isoformat(),
        },
    )
    
    # Get all subscribers for this event type
    subscribers = cartographer_status_service.get_subscribers_for_event(notification_type)
    
    if not subscribers:
        logger.info(f"No subscribers found for {event_type_lower} notification")
        return {
            "success": True,
            "subscribers_notified": 0,
            "message": "No active subscriptions",
        }
    
    # Check available notification services
    email_available = is_email_configured()
    discord_available = is_discord_configured()
    
    if not email_available and not discord_available:
        logger.error("Cannot send Cartographer status notifications: Neither email nor Discord is configured")
        return {
            "success": False,
            "subscribers_notified": 0,
            "error": "No notification services configured",
        }
    
    # Send to each subscriber via their preferred channels
    notification_id = str(uuid.uuid4())
    successful = 0
    failed = 0
    
    for subscriber in subscribers:
        subscriber_notified = False
        
        # Send via email if enabled
        if subscriber.email_enabled and subscriber.email_address and email_available:
            try:
                logger.info(f"Sending {event_type_lower} email to {subscriber.email_address} (user {subscriber.user_id})")
                record = await send_notification_email(
                    to_email=subscriber.email_address,
                    event=event,
                    notification_id=notification_id,
                )
                
                if record.success:
                    logger.info(f"✓ Cartographer {event_type_lower} email sent to {subscriber.email_address}")
                    subscriber_notified = True
                else:
                    logger.error(f"✗ Failed to send email to {subscriber.email_address}: {record.error_message}")
            except Exception as e:
                logger.error(f"✗ Exception sending email to {subscriber.email_address}: {e}", exc_info=True)
        
        # Send via Discord if enabled
        if subscriber.discord_enabled and discord_available:
            try:
                # Build Discord config based on subscriber preferences
                if subscriber.discord_delivery_method == "channel" and subscriber.discord_channel_id:
                    discord_config = DiscordConfig(
                        enabled=True,
                        delivery_method=DiscordDeliveryMethod.CHANNEL,
                        channel_config=DiscordChannelConfig(
                            guild_id=subscriber.discord_guild_id or "",
                            channel_id=subscriber.discord_channel_id,
                        ),
                    )
                elif subscriber.discord_delivery_method == "dm" and subscriber.discord_user_id:
                    discord_config = DiscordConfig(
                        enabled=True,
                        delivery_method=DiscordDeliveryMethod.DM,
                        discord_user_id=subscriber.discord_user_id,
                    )
                else:
                    logger.warning(f"Discord enabled but no channel/user configured for user {subscriber.user_id}")
                    discord_config = None
                
                if discord_config:
                    logger.info(f"Sending {event_type_lower} Discord notification to user {subscriber.user_id}")
                    from ..services.discord_service import send_discord_notification
                    record = await send_discord_notification(discord_config, event, notification_id)
                    
                    if record.success:
                        logger.info(f"✓ Cartographer {event_type_lower} Discord sent to user {subscriber.user_id}")
                        subscriber_notified = True
                    else:
                        logger.error(f"✗ Failed to send Discord to user {subscriber.user_id}: {record.error_message}")
            except Exception as e:
                logger.error(f"✗ Exception sending Discord to user {subscriber.user_id}: {e}", exc_info=True)
        
        if subscriber_notified:
            successful += 1
        else:
            failed += 1
    
    logger.info(
        f"Cartographer {event_type_lower} notification complete: "
        f"{successful} successful, {failed} failed out of {len(subscribers)} subscribers"
    )
    
    return {
        "success": successful > 0,
        "subscribers_notified": successful,
        "total_subscribers": len(subscribers),
        "failed": failed,
    }


class TestDiscordRequest(BaseModel):
    """Request model for testing Discord notifications"""
    channel_id: Optional[str] = None
    user_id: Optional[str] = None


@router.post("/test/discord")
async def test_global_discord(
    request: TestDiscordRequest,
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """Test Discord notifications for global settings"""
    if not is_discord_configured():
        raise HTTPException(status_code=503, detail="Discord bot is not configured")
    
    if not request.channel_id and not request.user_id:
        raise HTTPException(status_code=400, detail="Either channel_id or user_id must be provided")
    
    try:
        # Build Discord config based on request
        if request.channel_id:
            # Channel delivery
            config = DiscordConfig(
                enabled=True,
                delivery_method=DiscordDeliveryMethod.CHANNEL,
                channel_config=DiscordChannelConfig(
                    guild_id="",  # Not needed for sending
                    channel_id=request.channel_id,
                ),
            )
        else:
            # DM delivery
            config = DiscordConfig(
                enabled=True,
                delivery_method=DiscordDeliveryMethod.DM,
                discord_user_id=request.user_id,
            )
        
        result = await discord_service.send_test_notification(config)
        
        if result.get("success"):
            return {"success": True, "message": "Test Discord notification sent successfully"}
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to send test notification"))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send test Discord notification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
