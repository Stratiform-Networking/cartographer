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
from ..models import NetworkEvent, NotificationType, NotificationPriority, get_default_priority_for_type

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
            "cartographer_up_enabled": False,
            "cartographer_down_enabled": False,
            "email_enabled": True,
            "discord_enabled": False,
            "minimum_priority": "medium",
            "quiet_hours_enabled": False,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00",
            "subscribed": False,
        }
    
    return {
        "user_id": subscription.user_id,
        "email_address": subscription.email_address,
        "cartographer_up_enabled": subscription.cartographer_up_enabled,
        "cartographer_down_enabled": subscription.cartographer_down_enabled,
        "email_enabled": subscription.email_enabled,
        "discord_enabled": subscription.discord_enabled,
        "minimum_priority": subscription.minimum_priority,
        "quiet_hours_enabled": subscription.quiet_hours_enabled,
        "quiet_hours_start": subscription.quiet_hours_start,
        "quiet_hours_end": subscription.quiet_hours_end,
        "subscribed": True,
        "created_at": subscription.created_at.isoformat(),
        "updated_at": subscription.updated_at.isoformat(),
    }


class CreateSubscriptionRequest(BaseModel):
    """Request model for creating a subscription"""
    email_address: str
    cartographer_up_enabled: bool = True
    cartographer_down_enabled: bool = True
    email_enabled: bool = True
    discord_enabled: bool = False
    minimum_priority: str = "medium"
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "08:00"


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
        email_enabled=request.email_enabled,
        discord_enabled=request.discord_enabled,
        minimum_priority=request.minimum_priority,
        quiet_hours_enabled=request.quiet_hours_enabled,
        quiet_hours_start=request.quiet_hours_start,
        quiet_hours_end=request.quiet_hours_end,
    )
    
    return {
        "user_id": subscription.user_id,
        "email_address": subscription.email_address,
        "cartographer_up_enabled": subscription.cartographer_up_enabled,
        "cartographer_down_enabled": subscription.cartographer_down_enabled,
        "email_enabled": subscription.email_enabled,
        "discord_enabled": subscription.discord_enabled,
        "minimum_priority": subscription.minimum_priority,
        "quiet_hours_enabled": subscription.quiet_hours_enabled,
        "quiet_hours_start": subscription.quiet_hours_start,
        "quiet_hours_end": subscription.quiet_hours_end,
        "subscribed": True,
        "created_at": subscription.created_at.isoformat(),
        "updated_at": subscription.updated_at.isoformat(),
    }


class UpdateSubscriptionRequest(BaseModel):
    """Request model for updating a subscription"""
    email_address: Optional[str] = None
    cartographer_up_enabled: Optional[bool] = None
    cartographer_down_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    discord_enabled: Optional[bool] = None
    minimum_priority: Optional[str] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None


@router.put("/subscription")
async def update_cartographer_status_subscription(
    request: UpdateSubscriptionRequest,
    x_user_id: str = Header(..., description="User ID from auth service"),
):
    """Update Cartographer status subscription"""
    subscription = cartographer_status_service.get_subscription(x_user_id)
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found. Create one first with POST /subscription")
    
    # Validate email if provided
    if request.email_address is not None and not request.email_address:
        raise HTTPException(status_code=400, detail="email_address cannot be empty")
    
    updated = cartographer_status_service.create_or_update_subscription(
        user_id=x_user_id,
        email_address=request.email_address,
        cartographer_up_enabled=request.cartographer_up_enabled,
        cartographer_down_enabled=request.cartographer_down_enabled,
        email_enabled=request.email_enabled,
        discord_enabled=request.discord_enabled,
        minimum_priority=request.minimum_priority,
        quiet_hours_enabled=request.quiet_hours_enabled,
        quiet_hours_start=request.quiet_hours_start,
        quiet_hours_end=request.quiet_hours_end,
    )
    
    return {
        "user_id": updated.user_id,
        "email_address": updated.email_address,
        "cartographer_up_enabled": updated.cartographer_up_enabled,
        "cartographer_down_enabled": updated.cartographer_down_enabled,
        "email_enabled": updated.email_enabled,
        "discord_enabled": updated.discord_enabled,
        "minimum_priority": updated.minimum_priority,
        "quiet_hours_enabled": updated.quiet_hours_enabled,
        "quiet_hours_start": updated.quiet_hours_start,
        "quiet_hours_end": updated.quiet_hours_end,
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
    
    # Check email service
    if not is_email_configured():
        logger.error("Cannot send Cartographer status notifications: Email service not configured")
        return {
            "success": False,
            "subscribers_notified": 0,
            "error": "Email service not configured",
        }
    
    # Send to each subscriber
    notification_id = str(uuid.uuid4())
    successful = 0
    failed = 0
    
    for subscriber in subscribers:
        try:
            logger.info(f"Sending {event_type_lower} notification to {subscriber.email_address} (user {subscriber.user_id})")
            record = await send_notification_email(
                to_email=subscriber.email_address,
                event=event,
                notification_id=notification_id,
            )
            
            if record.success:
                logger.info(f"✓ Cartographer {event_type_lower} notification sent to {subscriber.email_address}")
                successful += 1
            else:
                logger.error(f"✗ Failed to send to {subscriber.email_address}: {record.error_message}")
                failed += 1
        except Exception as e:
            logger.error(f"✗ Exception sending to {subscriber.email_address}: {e}", exc_info=True)
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
