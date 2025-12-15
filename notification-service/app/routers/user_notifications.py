"""
API router for user-specific notification preferences.
"""

import logging
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Header, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..services.user_preferences import user_preferences_service
from ..services.email_service import send_test_email, is_email_configured
from ..services.discord_service import send_test_discord, is_discord_configured
from ..models import (
    NotificationType,
    NotificationPriority,
    NotificationChannel,
    TestNotificationResponse,
)
from ..models.database import (
    UserNetworkNotificationPrefs,
    UserGlobalNotificationPrefs,
    NotificationPriorityEnum,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Pydantic Models for API ====================

class NetworkPreferencesResponse(BaseModel):
    """Response model for network preferences"""
    user_id: str
    network_id: str  # UUID string
    email_enabled: bool
    discord_enabled: bool
    discord_user_id: Optional[str] = None
    enabled_types: List[str]
    type_priorities: Dict[str, str]
    minimum_priority: str
    quiet_hours_enabled: bool
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    quiet_hours_timezone: Optional[str] = None
    quiet_hours_bypass_priority: Optional[str] = None
    created_at: str
    updated_at: str

    @classmethod
    def from_db(cls, prefs: UserNetworkNotificationPrefs) -> "NetworkPreferencesResponse":
        """Convert from database model"""
        return cls(
            user_id=prefs.user_id,
            network_id=prefs.network_id,
            email_enabled=prefs.email_enabled,
            discord_enabled=prefs.discord_enabled,
            discord_user_id=prefs.discord_user_id,
            enabled_types=prefs.enabled_types or [],
            type_priorities={k: v.value if isinstance(v, NotificationPriorityEnum) else v 
                           for k, v in (prefs.type_priorities or {}).items()},
            minimum_priority=prefs.minimum_priority.value if isinstance(prefs.minimum_priority, NotificationPriorityEnum) else prefs.minimum_priority,
            quiet_hours_enabled=prefs.quiet_hours_enabled,
            quiet_hours_start=prefs.quiet_hours_start,
            quiet_hours_end=prefs.quiet_hours_end,
            quiet_hours_timezone=prefs.quiet_hours_timezone,
            quiet_hours_bypass_priority=prefs.quiet_hours_bypass_priority.value if prefs.quiet_hours_bypass_priority and isinstance(prefs.quiet_hours_bypass_priority, NotificationPriorityEnum) else prefs.quiet_hours_bypass_priority,
            created_at=prefs.created_at.isoformat(),
            updated_at=prefs.updated_at.isoformat(),
        )


class GlobalPreferencesResponse(BaseModel):
    """Response model for global preferences"""
    user_id: str
    email_enabled: bool
    discord_enabled: bool
    discord_user_id: Optional[str] = None
    cartographer_up_enabled: bool
    cartographer_down_enabled: bool
    minimum_priority: str
    quiet_hours_enabled: bool
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    quiet_hours_timezone: Optional[str] = None
    quiet_hours_bypass_priority: Optional[str] = None
    created_at: str
    updated_at: str

    @classmethod
    def from_db(cls, prefs: UserGlobalNotificationPrefs) -> "GlobalPreferencesResponse":
        """Convert from database model"""
        return cls(
            user_id=prefs.user_id,
            email_enabled=prefs.email_enabled,
            discord_enabled=prefs.discord_enabled,
            discord_user_id=prefs.discord_user_id,
            cartographer_up_enabled=prefs.cartographer_up_enabled,
            cartographer_down_enabled=prefs.cartographer_down_enabled,
            minimum_priority=prefs.minimum_priority.value if isinstance(prefs.minimum_priority, NotificationPriorityEnum) else prefs.minimum_priority,
            quiet_hours_enabled=prefs.quiet_hours_enabled,
            quiet_hours_start=prefs.quiet_hours_start,
            quiet_hours_end=prefs.quiet_hours_end,
            quiet_hours_timezone=prefs.quiet_hours_timezone,
            quiet_hours_bypass_priority=prefs.quiet_hours_bypass_priority.value if prefs.quiet_hours_bypass_priority and isinstance(prefs.quiet_hours_bypass_priority, NotificationPriorityEnum) else prefs.quiet_hours_bypass_priority,
            created_at=prefs.created_at.isoformat(),
            updated_at=prefs.updated_at.isoformat(),
        )


class NetworkPreferencesUpdate(BaseModel):
    """Update model for network preferences"""
    email_enabled: Optional[bool] = None
    discord_enabled: Optional[bool] = None
    discord_user_id: Optional[str] = None
    enabled_types: Optional[List[str]] = None
    type_priorities: Optional[Dict[str, str]] = None
    minimum_priority: Optional[str] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    quiet_hours_timezone: Optional[str] = None
    quiet_hours_bypass_priority: Optional[str] = None


class GlobalPreferencesUpdate(BaseModel):
    """Update model for global preferences"""
    email_enabled: Optional[bool] = None
    discord_enabled: Optional[bool] = None
    discord_user_id: Optional[str] = None
    cartographer_up_enabled: Optional[bool] = None
    cartographer_down_enabled: Optional[bool] = None
    minimum_priority: Optional[str] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    quiet_hours_timezone: Optional[str] = None
    quiet_hours_bypass_priority: Optional[str] = None


class TestNotificationRequest(BaseModel):
    """Request to send test notification"""
    channel: str  # "email" or "discord"


# ==================== Network Preferences ====================

@router.get("/users/{user_id}/networks/{network_id}/preferences", response_model=NetworkPreferencesResponse)
async def get_network_preferences(
    user_id: str,
    network_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get user's notification preferences for a specific network"""
    prefs = await user_preferences_service.get_or_create_network_preferences(
        db, user_id, network_id
    )
    return NetworkPreferencesResponse.from_db(prefs)


@router.put("/users/{user_id}/networks/{network_id}/preferences", response_model=NetworkPreferencesResponse)
async def update_network_preferences(
    user_id: str,
    network_id: str,
    update: NetworkPreferencesUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update user's notification preferences for a network"""
    update_data = update.model_dump(exclude_unset=True)
    
    # Convert string priorities to enum if needed
    if "minimum_priority" in update_data:
        update_data["minimum_priority"] = NotificationPriorityEnum(update_data["minimum_priority"])
    if "quiet_hours_bypass_priority" in update_data and update_data["quiet_hours_bypass_priority"]:
        update_data["quiet_hours_bypass_priority"] = NotificationPriorityEnum(update_data["quiet_hours_bypass_priority"])
    
    prefs = await user_preferences_service.update_network_preferences(
        db, user_id, network_id, update_data
    )
    return NetworkPreferencesResponse.from_db(prefs)


@router.delete("/users/{user_id}/networks/{network_id}/preferences")
async def delete_network_preferences(
    user_id: str,
    network_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete user's network notification preferences (reset to defaults)"""
    success = await user_preferences_service.delete_network_preferences(
        db, user_id, network_id
    )
    return {"success": success}


# ==================== Global Preferences ====================

@router.get("/users/{user_id}/global/preferences", response_model=GlobalPreferencesResponse)
async def get_global_preferences(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get user's global notification preferences"""
    prefs = await user_preferences_service.get_or_create_global_preferences(db, user_id)
    return GlobalPreferencesResponse.from_db(prefs)


@router.put("/users/{user_id}/global/preferences", response_model=GlobalPreferencesResponse)
async def update_global_preferences(
    user_id: str,
    update: GlobalPreferencesUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update user's global notification preferences"""
    update_data = update.model_dump(exclude_unset=True)
    
    # Convert string priorities to enum if needed
    if "minimum_priority" in update_data:
        update_data["minimum_priority"] = NotificationPriorityEnum(update_data["minimum_priority"])
    if "quiet_hours_bypass_priority" in update_data and update_data["quiet_hours_bypass_priority"]:
        update_data["quiet_hours_bypass_priority"] = NotificationPriorityEnum(update_data["quiet_hours_bypass_priority"])
    
    prefs = await user_preferences_service.update_global_preferences(
        db, user_id, update_data
    )
    return GlobalPreferencesResponse.from_db(prefs)


# ==================== Test Notifications ====================

@router.post("/users/{user_id}/networks/{network_id}/test", response_model=TestNotificationResponse)
async def test_network_notification(
    user_id: str,
    network_id: str,
    request: TestNotificationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send a test notification for user's network preferences"""
    prefs = await user_preferences_service.get_network_preferences(db, user_id, network_id)
    if not prefs:
        raise HTTPException(status_code=404, detail="Network preferences not found")
    
    channel = NotificationChannel(request.channel)
    
    if channel == NotificationChannel.EMAIL:
        if not prefs.email_enabled:
            return TestNotificationResponse(
                success=False,
                channel=channel,
                message="Email notifications not enabled",
                error="Please enable email notifications first",
            )
        
        if not is_email_configured():
            return TestNotificationResponse(
                success=False,
                channel=channel,
                message="Email service not configured",
                error="Email service is not configured on the server",
            )
        
        # Get user email from database
        user_email = await user_preferences_service.get_user_email(db, user_id)
        if not user_email:
            return TestNotificationResponse(
                success=False,
                channel=channel,
                message="Email address not found",
                error="User email address not found in database",
            )
        
        # Send test email
        result = await send_test_email(user_email)
        return TestNotificationResponse(
            success=result["success"],
            channel=channel,
            message="Test email sent successfully" if result["success"] else "Failed to send test email",
            error=result.get("error"),
        )
    
    elif channel == NotificationChannel.DISCORD:
        if not prefs.discord_enabled:
            return TestNotificationResponse(
                success=False,
                channel=channel,
                message="Discord notifications not enabled",
                error="Please enable Discord notifications first",
            )
        
        if not prefs.discord_user_id:
            return TestNotificationResponse(
                success=False,
                channel=channel,
                message="Discord account not linked",
                error="Please link your Discord account first",
            )
        
        # Send test Discord notification
        from ..services.discord_service import send_test_discord
        from ..models import DiscordConfig, DiscordDeliveryMethod
        
        test_config = DiscordConfig(
            enabled=True,
            delivery_method=DiscordDeliveryMethod.DM,
            discord_user_id=prefs.discord_user_id,
        )
        
        result = await send_test_discord(test_config)
        return TestNotificationResponse(
            success=result["success"],
            channel=channel,
            message="Test Discord notification sent" if result["success"] else "Failed to send Discord notification",
            error=result.get("error"),
        )
    
    return TestNotificationResponse(
        success=False,
        channel=channel,
        message="Unknown channel",
        error=f"Channel {channel} not supported",
    )


@router.post("/users/{user_id}/global/test", response_model=TestNotificationResponse)
async def test_global_notification(
    user_id: str,
    request: TestNotificationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send a test notification for user's global preferences"""
    prefs = await user_preferences_service.get_global_preferences(db, user_id)
    if not prefs:
        raise HTTPException(status_code=404, detail="Global preferences not found")
    
    channel = NotificationChannel(request.channel)
    
    if channel == NotificationChannel.EMAIL:
        if not prefs.email_enabled:
            return TestNotificationResponse(
                success=False,
                channel=channel,
                message="Email notifications not enabled",
                error="Please enable email notifications first",
            )
        
        # Get user email from database
        user_email = await user_preferences_service.get_user_email(db, user_id)
        if not user_email:
            return TestNotificationResponse(
                success=False,
                channel=channel,
                message="Email address not found",
                error="User email address not found in database",
            )
        
        # Send test email
        result = await send_test_email(user_email)
        return TestNotificationResponse(
            success=result["success"],
            channel=channel,
            message="Test email sent successfully" if result["success"] else "Failed to send test email",
            error=result.get("error"),
        )
    
    elif channel == NotificationChannel.DISCORD:
        if not prefs.discord_enabled:
            return TestNotificationResponse(
                success=False,
                channel=channel,
                message="Discord notifications not enabled",
                error="Please enable Discord notifications first",
            )
        
        if not prefs.discord_user_id:
            return TestNotificationResponse(
                success=False,
                channel=channel,
                message="Discord account not linked",
                error="Please link your Discord account first",
            )
        
        # Send test Discord notification
        from ..services.discord_service import send_test_discord
        from ..models import DiscordConfig, DiscordDeliveryMethod
        
        test_config = DiscordConfig(
            enabled=True,
            delivery_method=DiscordDeliveryMethod.DM,
            discord_user_id=prefs.discord_user_id,
        )
        
        result = await send_test_discord(test_config)
        return TestNotificationResponse(
            success=result["success"],
            channel=channel,
            message="Test Discord notification sent" if result["success"] else "Failed to send Discord notification",
            error=result.get("error"),
        )
    
    return TestNotificationResponse(
        success=False,
        channel=channel,
        message="Unknown channel",
        error=f"Channel {channel} not supported",
    )
