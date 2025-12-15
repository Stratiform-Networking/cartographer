"""
Service for dispatching notifications to users based on their preferences.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models import (
    NetworkEvent,
    NotificationType,
    NotificationPriority,
    NotificationRecord,
    NotificationChannel,
    DEFAULT_NOTIFICATION_TYPE_PRIORITIES,
    get_default_priority_for_type,
)
from ..models.database import (
    UserNetworkNotificationPrefs,
    UserGlobalNotificationPrefs,
    NotificationPriorityEnum,
)
from ..services.user_preferences import user_preferences_service
from ..services.email_service import send_notification_email, is_email_configured
from ..services.discord_service import send_discord_notification, is_discord_configured
# Note: get_db is not used here - db session is passed as parameter

logger = logging.getLogger(__name__)


class NotificationDispatchService:
    """Service for dispatching notifications to users"""
    
    def _should_notify_user(
        self,
        prefs: UserNetworkNotificationPrefs,
        event: NetworkEvent,
    ) -> tuple[bool, str]:
        """Check if a user should receive this notification"""
        # Check if at least one channel is enabled
        if not prefs.email_enabled and not prefs.discord_enabled:
            return False, "No notification channels enabled"
        
        # Check if notification type is enabled
        enabled_types = prefs.enabled_types or []
        if event.event_type.value not in enabled_types:
            return False, f"Notification type {event.event_type.value} not enabled"
        
        # Get effective priority (user override or default)
        type_priorities = prefs.type_priorities or {}
        effective_priority_str = type_priorities.get(event.event_type.value)
        
        if effective_priority_str:
            try:
                effective_priority = NotificationPriority(effective_priority_str)
            except ValueError:
                effective_priority = get_default_priority_for_type(event.event_type)
        else:
            effective_priority = get_default_priority_for_type(event.event_type)
        
        # Check minimum priority threshold
        priority_order = [
            NotificationPriority.LOW,
            NotificationPriority.MEDIUM,
            NotificationPriority.HIGH,
            NotificationPriority.CRITICAL,
        ]
        
        min_priority = NotificationPriority(prefs.minimum_priority.value if isinstance(prefs.minimum_priority, NotificationPriorityEnum) else prefs.minimum_priority)
        
        if priority_order.index(effective_priority) < priority_order.index(min_priority):
            return False, f"Priority {effective_priority.value} below minimum {min_priority.value}"
        
        # Check quiet hours
        if prefs.quiet_hours_enabled:
            if not self._is_quiet_hours(prefs):
                pass  # Not in quiet hours
            else:
                # Check bypass priority
                if prefs.quiet_hours_bypass_priority:
                    bypass_priority = NotificationPriority(
                        prefs.quiet_hours_bypass_priority.value if isinstance(prefs.quiet_hours_bypass_priority, NotificationPriorityEnum) else prefs.quiet_hours_bypass_priority
                    )
                    if priority_order.index(effective_priority) >= priority_order.index(bypass_priority):
                        pass  # High enough to bypass
                    else:
                        return False, f"In quiet hours and priority {effective_priority.value} below bypass threshold"
                else:
                    return False, "Currently in quiet hours"
        
        return True, ""
    
    def _is_quiet_hours(self, prefs: UserNetworkNotificationPrefs) -> bool:
        """Check if currently in quiet hours for user"""
        if not prefs.quiet_hours_start or not prefs.quiet_hours_end:
            return False
        
        # Get current time in user's timezone
        from zoneinfo import ZoneInfo
        try:
            tz = ZoneInfo(prefs.quiet_hours_timezone) if prefs.quiet_hours_timezone else None
            if tz:
                now = datetime.now(ZoneInfo("UTC")).astimezone(tz)
            else:
                now = datetime.now()
        except Exception:
            now = datetime.now()
        
        current_time = now.strftime("%H:%M")
        start = prefs.quiet_hours_start
        end = prefs.quiet_hours_end
        
        # Handle overnight quiet hours
        if start > end:
            return current_time >= start or current_time <= end
        else:
            return start <= current_time <= end
    
    async def send_to_user(
        self,
        db: AsyncSession,
        user_id: str,
        network_id: str,
        event: NetworkEvent,
        user_email: Optional[str] = None,
    ) -> List[NotificationRecord]:
        """Send notification to a single user based on their preferences"""
        records = []
        
        # Get user's network preferences
        prefs = await user_preferences_service.get_network_preferences(db, user_id, network_id)
        if not prefs:
            logger.debug(f"No preferences found for user {user_id} in network {network_id}")
            return records
        
        # Check if should notify
        should_notify, reason = self._should_notify_user(prefs, event)
        if not should_notify:
            logger.debug(f"Skipping notification for user {user_id}: {reason}")
            return records
        
        import uuid
        notification_id = str(uuid.uuid4())
        
        # Send email if enabled
        if prefs.email_enabled:
            if not is_email_configured():
                record = NotificationRecord(
                    notification_id=notification_id,
                    event_id=event.event_id,
                    network_id=network_id,
                    channel=NotificationChannel.EMAIL,
                    success=False,
                    error_message="Email service not configured",
                    title=event.title,
                    message=event.message,
                    priority=event.priority,
                )
                records.append(record)
            else:
                # Get user email from database if not provided
                if not user_email:
                    user_email = await user_preferences_service.get_user_email(db, user_id)
                
                if not user_email:
                    logger.warning(f"User email not found for user {user_id}, skipping email notification")
                else:
                    record = await send_notification_email(
                        to_email=user_email,
                        event=event,
                        notification_id=notification_id,
                    )
                    record.network_id = network_id
                    records.append(record)
        
        # Send Discord if enabled
        if prefs.discord_enabled and prefs.discord_user_id:
            if not is_discord_configured():
                record = NotificationRecord(
                    notification_id=notification_id,
                    event_id=event.event_id,
                    network_id=network_id,
                    channel=NotificationChannel.DISCORD,
                    success=False,
                    error_message="Discord service not configured",
                    title=event.title,
                    message=event.message,
                    priority=event.priority,
                )
                records.append(record)
            else:
                # Send Discord DM to user
                from ..services.discord_service import send_discord_dm
                try:
                    record = await send_discord_dm(
                        discord_user_id=prefs.discord_user_id,
                        event=event,
                        notification_id=notification_id,
                    )
                    record.network_id = network_id
                    records.append(record)
                except Exception as e:
                    logger.error(f"Failed to send Discord DM to user {user_id}: {e}")
                    record = NotificationRecord(
                        notification_id=notification_id,
                        event_id=event.event_id,
                        network_id=network_id,
                        channel=NotificationChannel.DISCORD,
                        success=False,
                        error_message=str(e),
                        title=event.title,
                        message=event.message,
                        priority=event.priority,
                    )
                    records.append(record)
        
        return records
    
    async def send_to_network_users(
        self,
        db: AsyncSession,
        network_id: str,
        user_ids: List[str],
        event: NetworkEvent,
        scheduled_at: Optional[datetime] = None,
    ) -> Dict[str, List[NotificationRecord]]:
        """Send notification to all users in a network"""
        results = {}
        
        # If scheduled, store for later (would need scheduled broadcast system)
        if scheduled_at and scheduled_at > datetime.now(timezone.utc):
            # TODO: Implement scheduled broadcast
            logger.warning("Scheduled notifications not yet implemented")
            return results
        
        # Send to each user
        for user_id in user_ids:
            # Get user email from database
            user_email = await user_preferences_service.get_user_email(db, user_id)
            
            user_records = await self.send_to_user(
                db=db,
                user_id=user_id,
                network_id=network_id,
                event=event,
                user_email=user_email,
            )
            results[user_id] = user_records
        
        return results
    
    async def send_global_notification(
        self,
        db: AsyncSession,
        event: NetworkEvent,
    ) -> Dict[str, List[NotificationRecord]]:
        """Send global notification (Cartographer Up/Down) to all subscribed users"""
        results = {}
        
        # Get all users with global notifications enabled
        users = await user_preferences_service.get_users_with_global_notifications_enabled(
            db, event.event_type
        )
        
        for prefs in users:
            # Check if should notify (similar logic to network)
            # Simplified for now - check minimum priority and quiet hours
            priority_order = [
                NotificationPriority.LOW,
                NotificationPriority.MEDIUM,
                NotificationPriority.HIGH,
                NotificationPriority.CRITICAL,
            ]
            
            min_priority = NotificationPriority(
                prefs.minimum_priority.value if isinstance(prefs.minimum_priority, NotificationPriorityEnum) else prefs.minimum_priority
            )
            
            if priority_order.index(event.priority) < priority_order.index(min_priority):
                continue  # Priority too low
            
            # Check quiet hours (simplified)
            # TODO: Implement full quiet hours check
            
            # Get user email from database
            user_email = await user_preferences_service.get_user_email(db, prefs.user_id)
            import uuid
            notification_id = str(uuid.uuid4())
            user_records = []
            
            if prefs.email_enabled and user_email and is_email_configured():
                record = await send_notification_email(
                    to_email=user_email,
                    event=event,
                    notification_id=notification_id,
                )
                record.network_id = None  # Global notifications
                user_records.append(record)
            
            if prefs.discord_enabled and prefs.discord_user_id:
                from ..services.discord_service import send_discord_dm
                try:
                    record = await send_discord_dm(
                        discord_user_id=prefs.discord_user_id,
                        event=event,
                        notification_id=notification_id,
                    )
                    record.network_id = None  # Global notifications
                    user_records.append(record)
                except Exception as e:
                    logger.error(f"Failed to send global Discord notification to user {prefs.user_id}: {e}")
            
            if user_records:
                results[prefs.user_id] = user_records
        
        return results


# Singleton instance
notification_dispatch_service = NotificationDispatchService()
