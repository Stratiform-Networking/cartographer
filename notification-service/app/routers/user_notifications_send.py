"""
Send network notification endpoint (separate file for organization).
"""

import logging
import uuid
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..services.notification_dispatch import notification_dispatch_service
from ..models import NetworkEvent, NotificationType, NotificationPriority

logger = logging.getLogger(__name__)

router = APIRouter()


class SendNetworkNotificationRequest(BaseModel):
    """Request to send a notification to all network users"""
    user_ids: List[str]  # Provided by backend
    type: str  # NotificationType value
    priority: str  # NotificationPriority value
    title: str
    message: str
    scheduled_at: Optional[str] = None  # ISO datetime string


@router.post("/networks/{network_id}/notifications/send")
async def send_network_notification(
    network_id: str,
    request: SendNetworkNotificationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a notification to all users in a network.
    Backend provides user_ids list, we fetch each user's preferences and send accordingly.
    """
    try:
        event_type = NotificationType(request.type)
        priority = NotificationPriority(request.priority)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid notification type or priority: {e}")
    
    scheduled_at = None
    if request.scheduled_at:
        try:
            scheduled_at = datetime.fromisoformat(request.scheduled_at.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid scheduled_at format")
    
    # Create network event
    event = NetworkEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        priority=priority,
        title=request.title,
        message=request.message,
        network_id=network_id,
        details={
            "is_manual_notification": True,
            "scheduled_at": request.scheduled_at,
        }
    )
    
    # Dispatch to all users
    results = await notification_dispatch_service.send_to_network_users(
        db=db,
        network_id=network_id,
        user_ids=request.user_ids,
        event=event,
        scheduled_at=scheduled_at,
    )
    
    return {
        "success": True,
        "event_id": event.event_id,
        "users_notified": len([r for r in results.values() if any(rec.success for rec in r)]),
        "total_users": len(request.user_ids),
        "results": results,
    }
