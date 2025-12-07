"""
Notification manager service.

Coordinates notification preferences, rate limiting, and dispatching
notifications across all channels (email, Discord).
"""

import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from collections import deque
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import uuid

from ..models import (
    NotificationPreferences,
    NotificationPreferencesUpdate,
    NetworkEvent,
    NotificationType,
    NotificationPriority,
    NotificationRecord,
    NotificationChannel,
    NotificationHistoryResponse,
    NotificationStatsResponse,
    TestNotificationRequest,
    TestNotificationResponse,
    EmailConfig,
    DiscordConfig,
    ScheduledBroadcast,
    ScheduledBroadcastStatus,
    ScheduledBroadcastCreate,
    ScheduledBroadcastResponse,
)
from .email_service import send_notification_email, send_test_email, is_email_configured
from .discord_service import discord_service, send_discord_notification, send_test_discord, is_discord_configured
from .anomaly_detector import anomaly_detector

logger = logging.getLogger(__name__)

# Persistence
DATA_DIR = Path(os.environ.get("NOTIFICATION_DATA_DIR", "/app/data"))
PREFERENCES_FILE = DATA_DIR / "notification_preferences.json"
HISTORY_FILE = DATA_DIR / "notification_history.json"
SCHEDULED_FILE = DATA_DIR / "scheduled_broadcasts.json"
SILENCED_DEVICES_FILE = DATA_DIR / "silenced_devices.json"

# Rate limiting
MAX_HISTORY_SIZE = 1000  # Keep last 1000 notifications in memory


class NotificationManager:
    """
    Manages notification preferences, rate limiting, and dispatching.
    """
    
    def __init__(self):
        self._preferences: Dict[str, NotificationPreferences] = {}
        self._history: deque = deque(maxlen=MAX_HISTORY_SIZE)
        self._rate_limits: Dict[str, deque] = {}  # user_id -> deque of timestamps
        self._scheduled_broadcasts: Dict[str, ScheduledBroadcast] = {}
        self._scheduler_task: Optional[asyncio.Task] = None
        self._silenced_devices: set = set()  # Device IPs with monitoring disabled
        
        # Load persisted data
        self._load_preferences()
        self._load_history()
        self._load_scheduled_broadcasts()
        self._load_silenced_devices()
    
    def _save_preferences(self):
        """Save preferences to disk"""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            
            data = {
                user_id: prefs.model_dump(mode="json")
                for user_id, prefs in self._preferences.items()
            }
            
            with open(PREFERENCES_FILE, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.debug(f"Saved {len(self._preferences)} notification preferences")
        except Exception as e:
            logger.error(f"Failed to save notification preferences: {e}")
    
    def _load_preferences(self):
        """Load preferences from disk"""
        try:
            if not PREFERENCES_FILE.exists():
                return
            
            with open(PREFERENCES_FILE, 'r') as f:
                data = json.load(f)
            
            for user_id, prefs_data in data.items():
                # Parse datetime strings
                if "created_at" in prefs_data and isinstance(prefs_data["created_at"], str):
                    prefs_data["created_at"] = datetime.fromisoformat(prefs_data["created_at"].replace("Z", "+00:00"))
                if "updated_at" in prefs_data and isinstance(prefs_data["updated_at"], str):
                    prefs_data["updated_at"] = datetime.fromisoformat(prefs_data["updated_at"].replace("Z", "+00:00"))
                
                self._preferences[user_id] = NotificationPreferences(**prefs_data)
            
            logger.info(f"Loaded {len(self._preferences)} notification preferences")
                
        except Exception as e:
            logger.error(f"Failed to load notification preferences: {e}")
    
    def _save_history(self):
        """Save history to disk"""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            
            data = [record.model_dump(mode="json") for record in self._history]
            
            with open(HISTORY_FILE, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save notification history: {e}")
    
    def _load_history(self):
        """Load history from disk"""
        try:
            if not HISTORY_FILE.exists():
                return
            
            with open(HISTORY_FILE, 'r') as f:
                data = json.load(f)
            
            for record_data in data:
                if "timestamp" in record_data and isinstance(record_data["timestamp"], str):
                    record_data["timestamp"] = datetime.fromisoformat(record_data["timestamp"].replace("Z", "+00:00"))
                self._history.append(NotificationRecord(**record_data))
            
            logger.info(f"Loaded {len(self._history)} notification records")
        except Exception as e:
            logger.error(f"Failed to load notification history: {e}")
    
    def _save_scheduled_broadcasts(self):
        """Save scheduled broadcasts to disk"""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            
            data = {
                broadcast_id: broadcast.model_dump(mode="json")
                for broadcast_id, broadcast in self._scheduled_broadcasts.items()
            }
            
            with open(SCHEDULED_FILE, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save scheduled broadcasts: {e}")
    
    def _load_scheduled_broadcasts(self):
        """Load scheduled broadcasts from disk"""
        try:
            if not SCHEDULED_FILE.exists():
                return
            
            with open(SCHEDULED_FILE, 'r') as f:
                data = json.load(f)
            
            for broadcast_id, broadcast_data in data.items():
                # Parse datetime strings
                for field in ["scheduled_at", "created_at", "sent_at"]:
                    if field in broadcast_data and broadcast_data[field] and isinstance(broadcast_data[field], str):
                        broadcast_data[field] = datetime.fromisoformat(broadcast_data[field].replace("Z", "+00:00"))
                
                self._scheduled_broadcasts[broadcast_id] = ScheduledBroadcast(**broadcast_data)
            
            logger.info(f"Loaded {len(self._scheduled_broadcasts)} scheduled broadcasts")
        except Exception as e:
            logger.error(f"Failed to load scheduled broadcasts: {e}")
    
    def _save_silenced_devices(self):
        """Save silenced devices list to disk"""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            
            with open(SILENCED_DEVICES_FILE, 'w') as f:
                json.dump(list(self._silenced_devices), f, indent=2)
            
            logger.debug(f"Saved {len(self._silenced_devices)} silenced devices")
        except Exception as e:
            logger.error(f"Failed to save silenced devices: {e}")
    
    def _load_silenced_devices(self):
        """Load silenced devices list from disk"""
        try:
            if not SILENCED_DEVICES_FILE.exists():
                return
            
            with open(SILENCED_DEVICES_FILE, 'r') as f:
                data = json.load(f)
            
            self._silenced_devices = set(data)
            logger.info(f"Loaded {len(self._silenced_devices)} silenced devices")
        except Exception as e:
            logger.error(f"Failed to load silenced devices: {e}")
    
    # ==================== Silenced Devices (Monitoring Disabled) ====================
    
    def is_device_silenced(self, device_ip: str) -> bool:
        """Check if a device has monitoring/notifications disabled"""
        return device_ip in self._silenced_devices
    
    def silence_device(self, device_ip: str) -> bool:
        """Silence notifications for a device (monitoring disabled)"""
        if device_ip in self._silenced_devices:
            return False
        
        self._silenced_devices.add(device_ip)
        self._save_silenced_devices()
        logger.info(f"Silenced device {device_ip}")
        return True
    
    def unsilence_device(self, device_ip: str) -> bool:
        """Re-enable notifications for a device (monitoring enabled)"""
        if device_ip not in self._silenced_devices:
            return False
        
        self._silenced_devices.discard(device_ip)
        self._save_silenced_devices()
        logger.info(f"Unsilenced device {device_ip}")
        return True
    
    def set_silenced_devices(self, device_ips: List[str]) -> None:
        """Set the full list of silenced devices"""
        self._silenced_devices = set(device_ips)
        self._save_silenced_devices()
        logger.info(f"Set {len(self._silenced_devices)} silenced devices")
    
    def get_silenced_devices(self) -> List[str]:
        """Get list of silenced device IPs"""
        return list(self._silenced_devices)
    
    # ==================== Scheduled Broadcast Scheduler ====================
    
    async def start_scheduler(self):
        """Start the background scheduler for processing scheduled broadcasts"""
        if self._scheduler_task is not None:
            return
        
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Scheduled broadcast scheduler started")
    
    async def stop_scheduler(self):
        """Stop the background scheduler"""
        if self._scheduler_task is not None:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
            self._scheduler_task = None
            logger.info("Scheduled broadcast scheduler stopped")
    
    async def _scheduler_loop(self):
        """Background loop to check and send scheduled broadcasts"""
        while True:
            try:
                await self._process_due_broadcasts()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _process_due_broadcasts(self):
        """Process any broadcasts that are due to be sent"""
        now = datetime.utcnow()
        
        for broadcast_id, broadcast in list(self._scheduled_broadcasts.items()):
            if broadcast.status != ScheduledBroadcastStatus.PENDING:
                continue
            
            # Handle both timezone-aware and naive datetimes
            scheduled_time = broadcast.scheduled_at
            if scheduled_time.tzinfo is not None:
                scheduled_time = scheduled_time.replace(tzinfo=None)
            
            if scheduled_time <= now:
                await self._send_scheduled_broadcast(broadcast_id)
    
    async def _send_scheduled_broadcast(self, broadcast_id: str):
        """Send a scheduled broadcast"""
        broadcast = self._scheduled_broadcasts.get(broadcast_id)
        if not broadcast:
            return
        
        try:
            # Create the network event
            event = NetworkEvent(
                event_id=f"scheduled-{broadcast_id}",
                event_type=broadcast.event_type,
                priority=broadcast.priority,
                title=broadcast.title,
                message=broadcast.message,
                details={
                    "scheduled_by": broadcast.created_by,
                    "scheduled_at": broadcast.scheduled_at.isoformat(),
                    "is_scheduled": True,
                }
            )
            
            # Broadcast to all users
            results = await self.broadcast_notification(event)
            
            # Update broadcast status
            broadcast.status = ScheduledBroadcastStatus.SENT
            broadcast.sent_at = datetime.utcnow()
            broadcast.users_notified = len(results)
            
            logger.info(f"Scheduled broadcast {broadcast_id} sent to {len(results)} users")
            
        except Exception as e:
            broadcast.status = ScheduledBroadcastStatus.FAILED
            broadcast.error_message = str(e)
            logger.error(f"Failed to send scheduled broadcast {broadcast_id}: {e}")
        
        self._save_scheduled_broadcasts()
    
    # ==================== Scheduled Broadcast Management ====================
    
    def create_scheduled_broadcast(
        self,
        title: str,
        message: str,
        scheduled_at: datetime,
        created_by: str,
        event_type: NotificationType = NotificationType.SCHEDULED_MAINTENANCE,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
    ) -> ScheduledBroadcast:
        """Create a new scheduled broadcast"""
        broadcast_id = str(uuid.uuid4())
        
        broadcast = ScheduledBroadcast(
            id=broadcast_id,
            title=title,
            message=message,
            event_type=event_type,
            priority=priority,
            scheduled_at=scheduled_at,
            created_by=created_by,
        )
        
        self._scheduled_broadcasts[broadcast_id] = broadcast
        self._save_scheduled_broadcasts()
        
        logger.info(f"Scheduled broadcast created: {broadcast_id} for {scheduled_at}")
        return broadcast
    
    def get_scheduled_broadcasts(
        self,
        include_completed: bool = False,
    ) -> ScheduledBroadcastResponse:
        """Get all scheduled broadcasts"""
        broadcasts = list(self._scheduled_broadcasts.values())
        
        if not include_completed:
            broadcasts = [b for b in broadcasts if b.status == ScheduledBroadcastStatus.PENDING]
        
        # Sort by scheduled time
        broadcasts.sort(key=lambda b: b.scheduled_at)
        
        return ScheduledBroadcastResponse(
            broadcasts=broadcasts,
            total_count=len(broadcasts),
        )
    
    def get_scheduled_broadcast(self, broadcast_id: str) -> Optional[ScheduledBroadcast]:
        """Get a specific scheduled broadcast"""
        return self._scheduled_broadcasts.get(broadcast_id)
    
    def cancel_scheduled_broadcast(self, broadcast_id: str) -> bool:
        """Cancel a scheduled broadcast"""
        broadcast = self._scheduled_broadcasts.get(broadcast_id)
        if not broadcast:
            return False
        
        if broadcast.status != ScheduledBroadcastStatus.PENDING:
            return False
        
        broadcast.status = ScheduledBroadcastStatus.CANCELLED
        self._save_scheduled_broadcasts()
        
        logger.info(f"Scheduled broadcast cancelled: {broadcast_id}")
        return True
    
    def delete_scheduled_broadcast(self, broadcast_id: str) -> bool:
        """Delete a scheduled broadcast (only if cancelled or completed)"""
        broadcast = self._scheduled_broadcasts.get(broadcast_id)
        if not broadcast:
            return False
        
        if broadcast.status == ScheduledBroadcastStatus.PENDING:
            return False  # Must cancel first
        
        del self._scheduled_broadcasts[broadcast_id]
        self._save_scheduled_broadcasts()
        
        logger.info(f"Scheduled broadcast deleted: {broadcast_id}")
        return True
    
    # ==================== Preferences Management ====================
    
    def get_preferences(self, user_id: str) -> NotificationPreferences:
        """Get notification preferences for a user (creates default if not exists)"""
        if user_id not in self._preferences:
            self._preferences[user_id] = NotificationPreferences(user_id=user_id)
            self._save_preferences()
        
        return self._preferences[user_id]
    
    def update_preferences(self, user_id: str, update: NotificationPreferencesUpdate) -> NotificationPreferences:
        """Update notification preferences for a user"""
        prefs = self.get_preferences(user_id)
        
        # Get current preferences as dict
        current_data = prefs.model_dump()
        
        # Get update data (only fields that were set)
        update_data = update.model_dump(exclude_unset=True)
        
        # Fields that should be replaced entirely, not merged
        # (e.g., notification_type_priorities should be replaced so deleted keys are removed)
        replace_fields = {'notification_type_priorities', 'enabled_notification_types'}
        
        # Merge update into current data (handles nested models properly)
        for key, value in update_data.items():
            if value is not None:
                if key in replace_fields:
                    # Replace these fields entirely (don't merge)
                    current_data[key] = value
                elif key in current_data and isinstance(current_data[key], dict) and isinstance(value, dict):
                    # Merge nested dicts (like email and discord configs)
                    current_data[key].update(value)
                else:
                    current_data[key] = value
        
        # Update timestamp
        current_data['updated_at'] = datetime.utcnow()
        
        # Recreate the preferences model with validated data
        self._preferences[user_id] = NotificationPreferences(**current_data)
        self._save_preferences()
        
        return self._preferences[user_id]
    
    def delete_preferences(self, user_id: str) -> bool:
        """Delete preferences for a user"""
        if user_id in self._preferences:
            del self._preferences[user_id]
            self._save_preferences()
            return True
        return False
    
    def get_all_users_with_notifications_enabled(self) -> List[str]:
        """Get list of user IDs with notifications enabled"""
        return [
            user_id for user_id, prefs in self._preferences.items()
            if prefs.enabled and (prefs.email.enabled or prefs.discord.enabled)
        ]
    
    # ==================== Rate Limiting ====================
    
    def _check_rate_limit(self, user_id: str, prefs: NotificationPreferences) -> bool:
        """Check if user is within rate limit. Returns True if allowed."""
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        
        if user_id not in self._rate_limits:
            self._rate_limits[user_id] = deque(maxlen=prefs.max_notifications_per_hour)
        
        # Clean old entries
        while self._rate_limits[user_id] and self._rate_limits[user_id][0] < hour_ago:
            self._rate_limits[user_id].popleft()
        
        # Check limit
        if len(self._rate_limits[user_id]) >= prefs.max_notifications_per_hour:
            return False
        
        return True
    
    def _record_rate_limit(self, user_id: str):
        """Record a notification for rate limiting"""
        now = datetime.utcnow()
        if user_id not in self._rate_limits:
            self._rate_limits[user_id] = deque()
        self._rate_limits[user_id].append(now)
    
    def _is_quiet_hours(self, prefs: NotificationPreferences) -> bool:
        """
        Check if currently in quiet hours.
        
        Uses the user's configured timezone if available, otherwise falls back
        to server's local time. This is important when running in Docker where
        the container may be in UTC while the user is in a different timezone.
        """
        if not prefs.quiet_hours_enabled:
            return False
        
        if not prefs.quiet_hours_start or not prefs.quiet_hours_end:
            return False
        
        # Get current time in user's timezone (or server local time as fallback)
        now = self._get_current_time_for_user(prefs.timezone)
        current_time = now.strftime("%H:%M")
        
        start = prefs.quiet_hours_start
        end = prefs.quiet_hours_end
        
        # Handle overnight quiet hours (e.g., 22:00 to 07:00)
        if start > end:
            return current_time >= start or current_time <= end
        else:
            return start <= current_time <= end
    
    def _get_current_time_for_user(self, timezone_str: Optional[str]) -> datetime:
        """
        Get current time in the user's timezone.
        
        Args:
            timezone_str: IANA timezone name (e.g., "America/New_York", "Europe/London")
                         If None or invalid, falls back to server's local time.
        
        Returns:
            datetime object representing current time in user's timezone
        """
        if timezone_str:
            try:
                user_tz = ZoneInfo(timezone_str)
                # Get current UTC time and convert to user's timezone
                utc_now = datetime.now(ZoneInfo("UTC"))
                return utc_now.astimezone(user_tz)
            except ZoneInfoNotFoundError:
                logger.warning(f"Invalid timezone '{timezone_str}', falling back to server local time")
            except Exception as e:
                logger.warning(f"Error getting timezone '{timezone_str}': {e}, falling back to server local time")
        
        # Fallback to server's local time (works if Docker is configured with host timezone)
        return datetime.now()
    
    # ==================== Notification Dispatch ====================
    
    def _should_notify(self, prefs: NotificationPreferences, event: NetworkEvent) -> tuple[bool, str]:
        """
        Check if a notification should be sent based on preferences.
        Returns (should_notify, reason_if_not).
        """
        # Master switch
        if not prefs.enabled:
            return False, "Notifications disabled for user"
        
        # Check if at least one channel is enabled
        if not prefs.email.enabled and not prefs.discord.enabled:
            return False, "No notification channels enabled"
        
        # Check event type filter
        if event.event_type not in prefs.enabled_notification_types:
            return False, f"Event type {event.event_type.value} not in enabled types"
        
        # Check priority threshold using user's effective priority for this notification type
        # This allows users to customize the priority of specific notification types
        priority_order = [
            NotificationPriority.LOW,
            NotificationPriority.MEDIUM,
            NotificationPriority.HIGH,
            NotificationPriority.CRITICAL,
        ]
        
        # Get the effective priority for this notification type (user override or default)
        effective_priority = prefs.get_effective_priority(event.event_type)
        
        if priority_order.index(effective_priority) < priority_order.index(prefs.minimum_priority):
            return False, f"Event type priority {effective_priority.value} below minimum {prefs.minimum_priority.value}"
        
        # Check quiet hours (with pass-through for high-priority alerts)
        if self._is_quiet_hours(prefs):
            # Check if this notification can bypass quiet hours
            if prefs.quiet_hours_bypass_priority is not None:
                bypass_index = priority_order.index(prefs.quiet_hours_bypass_priority)
                effective_index = priority_order.index(effective_priority)
                if effective_index >= bypass_index:
                    # Priority is high enough to bypass quiet hours
                    pass
                else:
                    return False, f"Currently in quiet hours (priority {effective_priority.value} below bypass threshold {prefs.quiet_hours_bypass_priority.value})"
            else:
                return False, "Currently in quiet hours"
        
        # Check rate limit
        if not self._check_rate_limit(prefs.user_id, prefs):
            return False, "Rate limit exceeded"
        
        return True, ""
    
    async def send_notification(
        self,
        user_id: str,
        event: NetworkEvent,
        force: bool = False,
    ) -> List[NotificationRecord]:
        """
        Send a notification to a user across all their enabled channels.
        
        Args:
            user_id: The user to notify
            event: The network event to notify about
            force: If True, bypass preference checks (for test notifications)
        
        Returns:
            List of NotificationRecord for each channel attempted
        """
        prefs = self.get_preferences(user_id)
        records = []
        
        if not force:
            should_notify, reason = self._should_notify(prefs, event)
            if not should_notify:
                logger.info(f"Skipping {event.event_type.value} notification for {user_id}: {reason}")
                return records
        
        notification_id = str(uuid.uuid4())
        
        # Send via email
        if prefs.email.enabled and prefs.email.email_address:
            record = await send_notification_email(
                to_email=prefs.email.email_address,
                event=event,
                notification_id=notification_id,
            )
            record.user_id = user_id
            records.append(record)
            self._history.append(record)
        
        # Send via Discord
        if prefs.discord.enabled:
            record = await send_discord_notification(
                config=prefs.discord,
                event=event,
                notification_id=notification_id,
                user_id=user_id,
            )
            records.append(record)
            self._history.append(record)
        
        # Record for rate limiting
        if records and not force:
            self._record_rate_limit(user_id)
        
        # Save history periodically
        if len(self._history) % 50 == 0:
            self._save_history()
        
        return records
    
    async def broadcast_notification(self, event: NetworkEvent) -> Dict[str, List[NotificationRecord]]:
        """
        Send a notification to all users who should receive it.
        
        Returns a dict of user_id -> list of records.
        """
        results = {}
        
        for user_id in self.get_all_users_with_notifications_enabled():
            records = await self.send_notification(user_id, event)
            if records:
                results[user_id] = records
        
        return results
    
    async def send_test_notification(
        self,
        user_id: str,
        request: TestNotificationRequest,
    ) -> TestNotificationResponse:
        """Send a test notification via a specific channel"""
        prefs = self.get_preferences(user_id)
        
        if request.channel == NotificationChannel.EMAIL:
            if not prefs.email.email_address:
                return TestNotificationResponse(
                    success=False,
                    channel=request.channel,
                    message="No email address configured",
                    error="Please configure an email address first",
                )
            
            result = await send_test_email(prefs.email.email_address)
            
            return TestNotificationResponse(
                success=result["success"],
                channel=request.channel,
                message="Test email sent successfully" if result["success"] else "Failed to send test email",
                error=result.get("error"),
            )
        
        elif request.channel == NotificationChannel.DISCORD:
            if not prefs.discord.enabled:
                return TestNotificationResponse(
                    success=False,
                    channel=request.channel,
                    message="Discord notifications not enabled",
                    error="Please enable Discord notifications first",
                )
            
            result = await send_test_discord(prefs.discord)
            
            return TestNotificationResponse(
                success=result["success"],
                channel=request.channel,
                message="Test Discord notification sent" if result["success"] else "Failed to send Discord notification",
                error=result.get("error"),
            )
        
        return TestNotificationResponse(
            success=False,
            channel=request.channel,
            message="Unknown notification channel",
            error=f"Channel {request.channel} not supported",
        )
    
    # ==================== History and Stats ====================
    
    def get_history(
        self,
        user_id: Optional[str] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> NotificationHistoryResponse:
        """Get notification history, optionally filtered by user"""
        records = list(self._history)
        
        if user_id:
            records = [r for r in records if r.user_id == user_id]
        
        # Sort by timestamp descending
        records.sort(key=lambda r: r.timestamp, reverse=True)
        
        total = len(records)
        start = (page - 1) * per_page
        end = start + per_page
        
        return NotificationHistoryResponse(
            notifications=records[start:end],
            total_count=total,
            page=page,
            per_page=per_page,
        )
    
    def get_stats(self, user_id: Optional[str] = None) -> NotificationStatsResponse:
        """Get notification statistics"""
        now = datetime.utcnow()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        
        records = list(self._history)
        
        if user_id:
            records = [r for r in records if r.user_id == user_id]
        
        records_24h = [r for r in records if r.timestamp > day_ago]
        records_7d = [r for r in records if r.timestamp > week_ago]
        
        by_channel = {}
        by_type = {}
        successful = 0
        total = len(records_7d)
        
        for record in records_7d:
            by_channel[record.channel.value] = by_channel.get(record.channel.value, 0) + 1
            if record.success:
                successful += 1
        
        # Get anomaly count from detector
        anomalies_24h = len([r for r in records_24h if "anomaly" in r.title.lower()])
        
        return NotificationStatsResponse(
            total_sent_24h=len(records_24h),
            total_sent_7d=len(records_7d),
            by_channel=by_channel,
            by_type=by_type,
            success_rate=successful / total if total > 0 else 1.0,
            anomalies_detected_24h=anomalies_24h,
        )
    
    # ==================== Integration with Health Service ====================
    
    async def process_health_check(
        self,
        device_ip: str,
        success: bool,
        latency_ms: Optional[float] = None,
        packet_loss: Optional[float] = None,
        device_name: Optional[str] = None,
        previous_state: Optional[str] = None,
    ):
        """
        Process a health check result and send notifications if needed.
        
        This should be called after each health check to train the ML model
        and potentially send notifications.
        
        Note: Devices with monitoring disabled (silenced) will still train the
        ML model but will not trigger notifications.
        """
        # Check if device has monitoring disabled (silenced)
        is_silenced = self.is_device_silenced(device_ip)
        
        # Let the anomaly detector analyze and potentially create an event
        # We still train the ML model even for silenced devices
        event = anomaly_detector.create_network_event(
            device_ip=device_ip,
            success=success,
            latency_ms=latency_ms,
            packet_loss=packet_loss,
            device_name=device_name,
            previous_state=previous_state,
        )
        
        if event and not is_silenced:
            # Broadcast to all users who should receive this notification
            results = await self.broadcast_notification(event)
            logger.info(f"Broadcasted notification to {len(results)} users: {event.title}")
        elif event and is_silenced:
            logger.debug(f"Skipping notification for silenced device {device_ip}: {event.title}")


# Singleton instance
notification_manager = NotificationManager()

