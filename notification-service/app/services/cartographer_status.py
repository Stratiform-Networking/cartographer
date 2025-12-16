"""
Cartographer Status Notification Service

Separate system for managing Cartographer Up/Down notifications.
Users can subscribe to receive notifications when Cartographer itself goes up or down.
"""

import os
import json
import logging
import uuid
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from ..models import (
    NetworkEvent,
    NotificationType,
    NotificationPriority,
    NotificationRecord,
    NotificationChannel,
)

logger = logging.getLogger(__name__)

# Persistence
DATA_DIR = Path(os.environ.get("NOTIFICATION_DATA_DIR", "/app/data"))
SUBSCRIPTIONS_FILE = DATA_DIR / "cartographer_status_subscriptions.json"


class CartographerStatusSubscription:
    """A user's subscription to Cartographer status notifications"""
    
    def __init__(
        self,
        user_id: str,
        email_address: str,
        cartographer_up_enabled: bool = True,
        cartographer_down_enabled: bool = True,
        cartographer_up_priority: str = "medium",
        cartographer_down_priority: str = "critical",
        email_enabled: bool = False,
        discord_enabled: bool = False,
        discord_delivery_method: str = "dm",
        discord_guild_id: Optional[str] = None,
        discord_channel_id: Optional[str] = None,
        discord_user_id: Optional[str] = None,
        minimum_priority: str = "medium",
        quiet_hours_enabled: bool = False,
        quiet_hours_start: str = "22:00",
        quiet_hours_end: str = "08:00",
        quiet_hours_bypass_priority: Optional[str] = None,
        timezone: Optional[str] = None,
    ):
        self.user_id = user_id
        self.email_address = email_address
        self.cartographer_up_enabled = cartographer_up_enabled
        self.cartographer_down_enabled = cartographer_down_enabled
        self.cartographer_up_priority = cartographer_up_priority
        self.cartographer_down_priority = cartographer_down_priority
        self.email_enabled = email_enabled
        self.discord_enabled = discord_enabled
        self.discord_delivery_method = discord_delivery_method
        self.discord_guild_id = discord_guild_id
        self.discord_channel_id = discord_channel_id
        self.discord_user_id = discord_user_id
        self.minimum_priority = minimum_priority
        self.quiet_hours_enabled = quiet_hours_enabled
        self.quiet_hours_start = quiet_hours_start
        self.quiet_hours_end = quiet_hours_end
        self.quiet_hours_bypass_priority = quiet_hours_bypass_priority
        self.timezone = timezone
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "user_id": self.user_id,
            "email_address": self.email_address,
            "cartographer_up_enabled": self.cartographer_up_enabled,
            "cartographer_down_enabled": self.cartographer_down_enabled,
            "cartographer_up_priority": self.cartographer_up_priority,
            "cartographer_down_priority": self.cartographer_down_priority,
            "email_enabled": self.email_enabled,
            "discord_enabled": self.discord_enabled,
            "discord_delivery_method": self.discord_delivery_method,
            "discord_guild_id": self.discord_guild_id,
            "discord_channel_id": self.discord_channel_id,
            "discord_user_id": self.discord_user_id,
            "minimum_priority": self.minimum_priority,
            "quiet_hours_enabled": self.quiet_hours_enabled,
            "quiet_hours_start": self.quiet_hours_start,
            "quiet_hours_end": self.quiet_hours_end,
            "quiet_hours_bypass_priority": self.quiet_hours_bypass_priority,
            "timezone": self.timezone,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "CartographerStatusSubscription":
        """Create from dictionary"""
        sub = cls(
            user_id=data["user_id"],
            email_address=data["email_address"],
            cartographer_up_enabled=data.get("cartographer_up_enabled", True),
            cartographer_down_enabled=data.get("cartographer_down_enabled", True),
            cartographer_up_priority=data.get("cartographer_up_priority", "medium"),
            cartographer_down_priority=data.get("cartographer_down_priority", "critical"),
            email_enabled=data.get("email_enabled", False),
            discord_enabled=data.get("discord_enabled", False),
            discord_delivery_method=data.get("discord_delivery_method", "dm"),
            discord_guild_id=data.get("discord_guild_id"),
            discord_channel_id=data.get("discord_channel_id"),
            discord_user_id=data.get("discord_user_id"),
            minimum_priority=data.get("minimum_priority", "medium"),
            quiet_hours_enabled=data.get("quiet_hours_enabled", False),
            quiet_hours_start=data.get("quiet_hours_start", "22:00"),
            quiet_hours_end=data.get("quiet_hours_end", "08:00"),
            quiet_hours_bypass_priority=data.get("quiet_hours_bypass_priority"),
            timezone=data.get("timezone"),
        )
        if "created_at" in data and isinstance(data["created_at"], str):
            sub.created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        if "updated_at" in data and isinstance(data["updated_at"], str):
            sub.updated_at = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
        return sub


class CartographerStatusService:
    """
    Manages Cartographer Up/Down notification subscriptions.
    
    This is completely separate from network-scoped notifications.
    """
    
    def __init__(self):
        self._subscriptions: Dict[str, CartographerStatusSubscription] = {}
        self._load_subscriptions()
        self._migrate_from_global_preferences()
    
    def _save_subscriptions(self):
        """Save subscriptions to disk"""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            
            data = {
                user_id: sub.to_dict()
                for user_id, sub in self._subscriptions.items()
            }
            
            with open(SUBSCRIPTIONS_FILE, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.debug(f"Saved {len(self._subscriptions)} Cartographer status subscriptions")
        except Exception as e:
            logger.error(f"Failed to save Cartographer status subscriptions: {e}")
    
    def _load_subscriptions(self):
        """Load subscriptions from disk"""
        try:
            if not SUBSCRIPTIONS_FILE.exists():
                return
            
            with open(SUBSCRIPTIONS_FILE, 'r') as f:
                data = json.load(f)
            
            for user_id, sub_data in data.items():
                try:
                    self._subscriptions[user_id] = CartographerStatusSubscription.from_dict(sub_data)
                except Exception as e:
                    logger.warning(f"Failed to load Cartographer status subscription for user {user_id}: {e}")
                    continue
            
            logger.info(f"Loaded {len(self._subscriptions)} Cartographer status subscriptions")
        except Exception as e:
            logger.error(f"Failed to load Cartographer status subscriptions: {e}")
    
    def get_subscription(self, user_id: str) -> Optional[CartographerStatusSubscription]:
        """Get subscription for a user"""
        return self._subscriptions.get(user_id)
    
    def create_or_update_subscription(
        self,
        user_id: str,
        email_address: Optional[str] = None,
        cartographer_up_enabled: Optional[bool] = None,
        cartographer_down_enabled: Optional[bool] = None,
        cartographer_up_priority: Optional[str] = None,
        cartographer_down_priority: Optional[str] = None,
        email_enabled: Optional[bool] = None,
        discord_enabled: Optional[bool] = None,
        discord_delivery_method: Optional[str] = None,
        discord_guild_id: Optional[str] = None,
        discord_channel_id: Optional[str] = None,
        discord_user_id: Optional[str] = None,
        minimum_priority: Optional[str] = None,
        quiet_hours_enabled: Optional[bool] = None,
        quiet_hours_start: Optional[str] = None,
        quiet_hours_end: Optional[str] = None,
        quiet_hours_bypass_priority: Optional[str] = None,
        timezone: Optional[str] = None,
        # Use sentinel value to distinguish between "not provided" and "set to None"
        _bypass_priority_provided: bool = False,
        _timezone_provided: bool = False,
        _discord_guild_id_provided: bool = False,
        _discord_channel_id_provided: bool = False,
        _discord_user_id_provided: bool = False,
    ) -> CartographerStatusSubscription:
        """Create or update a subscription"""
        if user_id in self._subscriptions:
            # Update existing - only update fields that are provided
            sub = self._subscriptions[user_id]
            if email_address is not None:
                sub.email_address = email_address
            if cartographer_up_enabled is not None:
                sub.cartographer_up_enabled = cartographer_up_enabled
            if cartographer_down_enabled is not None:
                sub.cartographer_down_enabled = cartographer_down_enabled
            if cartographer_up_priority is not None:
                sub.cartographer_up_priority = cartographer_up_priority
            if cartographer_down_priority is not None:
                sub.cartographer_down_priority = cartographer_down_priority
            if email_enabled is not None:
                sub.email_enabled = email_enabled
            if discord_enabled is not None:
                sub.discord_enabled = discord_enabled
            if discord_delivery_method is not None:
                sub.discord_delivery_method = discord_delivery_method
            if _discord_guild_id_provided:
                sub.discord_guild_id = discord_guild_id
            if _discord_channel_id_provided:
                sub.discord_channel_id = discord_channel_id
            if _discord_user_id_provided:
                sub.discord_user_id = discord_user_id
            if minimum_priority is not None:
                sub.minimum_priority = minimum_priority
            if quiet_hours_enabled is not None:
                sub.quiet_hours_enabled = quiet_hours_enabled
            if quiet_hours_start is not None:
                sub.quiet_hours_start = quiet_hours_start
            if quiet_hours_end is not None:
                sub.quiet_hours_end = quiet_hours_end
            if _bypass_priority_provided:
                sub.quiet_hours_bypass_priority = quiet_hours_bypass_priority
            if _timezone_provided:
                sub.timezone = timezone
            sub.updated_at = datetime.utcnow()
        else:
            # Create new - require email_address for new subscriptions
            if not email_address:
                raise ValueError("email_address is required for new subscriptions")
            sub = CartographerStatusSubscription(
                user_id=user_id,
                email_address=email_address,
                cartographer_up_enabled=cartographer_up_enabled if cartographer_up_enabled is not None else True,
                cartographer_down_enabled=cartographer_down_enabled if cartographer_down_enabled is not None else True,
                cartographer_up_priority=cartographer_up_priority if cartographer_up_priority is not None else "medium",
                cartographer_down_priority=cartographer_down_priority if cartographer_down_priority is not None else "critical",
                email_enabled=email_enabled if email_enabled is not None else False,
                discord_enabled=discord_enabled if discord_enabled is not None else False,
                discord_delivery_method=discord_delivery_method if discord_delivery_method is not None else "dm",
                discord_guild_id=discord_guild_id,
                discord_channel_id=discord_channel_id,
                discord_user_id=discord_user_id,
                minimum_priority=minimum_priority if minimum_priority is not None else "medium",
                quiet_hours_enabled=quiet_hours_enabled if quiet_hours_enabled is not None else False,
                quiet_hours_start=quiet_hours_start if quiet_hours_start is not None else "22:00",
                quiet_hours_end=quiet_hours_end if quiet_hours_end is not None else "08:00",
                quiet_hours_bypass_priority=quiet_hours_bypass_priority,
                timezone=timezone,
            )
            self._subscriptions[user_id] = sub
        
        self._save_subscriptions()
        logger.info(f"Updated Cartographer status subscription for user {user_id}")
        return sub
    
    def delete_subscription(self, user_id: str) -> bool:
        """Delete a subscription"""
        if user_id not in self._subscriptions:
            return False
        
        del self._subscriptions[user_id]
        self._save_subscriptions()
        logger.info(f"Deleted Cartographer status subscription for user {user_id}")
        return True
    
    def get_all_subscriptions(self) -> List[CartographerStatusSubscription]:
        """Get all subscriptions"""
        return list(self._subscriptions.values())
    
    def get_subscribers_for_event(self, event_type: NotificationType) -> List[CartographerStatusSubscription]:
        """Get all subscribers for a specific event type who have at least one notification channel enabled"""
        if event_type == NotificationType.CARTOGRAPHER_UP:
            return [
                sub for sub in self._subscriptions.values()
                if sub.cartographer_up_enabled and (
                    (sub.email_enabled and sub.email_address) or 
                    (sub.discord_enabled and (sub.discord_channel_id or sub.discord_user_id))
                )
            ]
        elif event_type == NotificationType.CARTOGRAPHER_DOWN:
            return [
                sub for sub in self._subscriptions.values()
                if sub.cartographer_down_enabled and (
                    (sub.email_enabled and sub.email_address) or 
                    (sub.discord_enabled and (sub.discord_channel_id or sub.discord_user_id))
                )
            ]
        return []
    
    def _migrate_from_global_preferences(self):
        """Migrate users from old global preferences system to new subscription system"""
        try:
            from .notification_manager import notification_manager
            
            migrated_count = 0
            
            # Check each network preference for owners with email
            for network_id_str, network_prefs in notification_manager._preferences.items():
                if not network_prefs.owner_user_id or not network_prefs.email.email_address:
                    continue
                
                user_id = network_prefs.owner_user_id
                
                # Skip if already migrated
                if user_id in self._subscriptions:
                    continue
                
                # Check if user has global preferences (old system)
                global_prefs = notification_manager._global_preferences.get(user_id)
                if global_prefs and global_prefs.email_address:
                    # Migrate from global preferences
                    self.create_or_update_subscription(
                        user_id=user_id,
                        email_address=global_prefs.email_address,
                        cartographer_up_enabled=global_prefs.cartographer_up_enabled,
                        cartographer_down_enabled=global_prefs.cartographer_down_enabled,
                    )
                    migrated_count += 1
                    logger.info(f"Migrated user {user_id} from global preferences to Cartographer status subscription")
                elif network_prefs.email.email_address:
                    # Auto-subscribe network owners (they likely want these notifications)
                    self.create_or_update_subscription(
                        user_id=user_id,
                        email_address=network_prefs.email.email_address,
                        cartographer_up_enabled=True,
                        cartographer_down_enabled=True,
                    )
                    migrated_count += 1
                    logger.info(f"Auto-subscribed network owner {user_id} to Cartographer status notifications")
            
            if migrated_count > 0:
                logger.info(f"Migration complete: {migrated_count} users migrated to Cartographer status subscriptions")
        except Exception as e:
            logger.error(f"Failed to migrate from global preferences: {e}", exc_info=True)


# Singleton instance
cartographer_status_service = CartographerStatusService()
