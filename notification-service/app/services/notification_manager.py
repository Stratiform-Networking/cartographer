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
    GlobalUserPreferences,
    GlobalUserPreferencesUpdate,
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
GLOBAL_PREFERENCES_FILE = DATA_DIR / "global_user_preferences.json"
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
        self._global_preferences: Dict[str, GlobalUserPreferences] = {}  # user_id -> preferences
        self._history: deque = deque(maxlen=MAX_HISTORY_SIZE)
        self._rate_limits: Dict[str, deque] = {}  # network_id -> deque of timestamps
        self._scheduled_broadcasts: Dict[str, ScheduledBroadcast] = {}
        self._scheduler_task: Optional[asyncio.Task] = None
        self._silenced_devices: set = set()  # Device IPs with monitoring disabled
        
        # Load persisted data
        self._load_preferences()
        self._load_global_preferences()
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
            
            for key, prefs_data in data.items():
                # Parse datetime strings
                if "created_at" in prefs_data and isinstance(prefs_data["created_at"], str):
                    prefs_data["created_at"] = datetime.fromisoformat(prefs_data["created_at"].replace("Z", "+00:00"))
                if "updated_at" in prefs_data and isinstance(prefs_data["updated_at"], str):
                    prefs_data["updated_at"] = datetime.fromisoformat(prefs_data["updated_at"].replace("Z", "+00:00"))
                
                # Handle migration from old user_id based preferences to network_id based
                # Old format had 'user_id', new format has 'network_id'
                if "user_id" in prefs_data and "network_id" not in prefs_data:
                    # Skip old user-based preferences (they'll be recreated per-network)
                    logger.info(f"Skipping old user-based preferences for key {key}")
                    continue
                
                # Ensure network_id exists (for new format)
                if "network_id" not in prefs_data:
                    # Try to use key as network_id if it looks like an integer
                    try:
                        prefs_data["network_id"] = int(key)
                    except ValueError:
                        logger.warning(f"Skipping preferences with invalid key: {key}")
                        continue
                
                try:
                    self._preferences[key] = NotificationPreferences(**prefs_data)
                except Exception as e:
                    logger.warning(f"Failed to load preferences for key {key}: {e}")
                    continue
            
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
                
                # Handle migration from old user_id based records to network_id based
                if "user_id" in record_data and "network_id" not in record_data:
                    # Set network_id to 0 for old records (they'll still be viewable)
                    record_data["network_id"] = 0
                    del record_data["user_id"]
                
                try:
                    self._history.append(NotificationRecord(**record_data))
                except Exception as e:
                    logger.warning(f"Failed to load history record: {e}")
                    continue
            
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
    
    async def _send_scheduled_broadcast(self, broadcast_id: str, user_ids: Optional[List[str]] = None):
        """
        Send a scheduled broadcast to all users in the network.
        
        Args:
            broadcast_id: The scheduled broadcast ID
            user_ids: Optional list of network member user IDs. If provided, sends to those members.
                      If None, sends to network's preferences (for backwards compatibility).
        """
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
                network_id=broadcast.network_id,
                details={
                    "scheduled_by": broadcast.created_by,
                    "scheduled_at": broadcast.scheduled_at.isoformat(),
                    "is_scheduled": True,
                }
            )
            
            if user_ids:
                # Send to specific network members based on their preferences
                results = await self.send_notification_to_network_members(
                    broadcast.network_id, user_ids, event
                )
                users_notified = len(results)
                total_records = sum(len(records) for records in results.values())
            else:
                # Fallback to network-level preferences (backwards compatibility)
                records = await self.send_notification_to_network(broadcast.network_id, event)
                users_notified = 1 if records else 0
                total_records = len(records)
            
            # Update broadcast status
            broadcast.status = ScheduledBroadcastStatus.SENT
            broadcast.sent_at = datetime.utcnow()
            broadcast.users_notified = users_notified
            
            logger.info(f"Scheduled broadcast {broadcast_id} sent to network {broadcast.network_id} ({users_notified} users, {total_records} channels)")
            
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
        network_id: int,
        event_type: NotificationType = NotificationType.SCHEDULED_MAINTENANCE,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
    ) -> ScheduledBroadcast:
        """
        Create a new scheduled broadcast for a specific network.
        
        Args:
            title: Broadcast title
            message: Broadcast message
            scheduled_at: When to send the broadcast
            created_by: Username of the owner creating the broadcast
            network_id: The network this broadcast belongs to (required)
            event_type: Type of notification event
            priority: Notification priority
        """
        broadcast_id = str(uuid.uuid4())
        
        broadcast = ScheduledBroadcast(
            id=broadcast_id,
            title=title,
            message=message,
            event_type=event_type,
            priority=priority,
            network_id=network_id,
            scheduled_at=scheduled_at,
            created_by=created_by,
        )
        
        self._scheduled_broadcasts[broadcast_id] = broadcast
        self._save_scheduled_broadcasts()
        
        logger.info(f"Scheduled broadcast created: {broadcast_id} for network {network_id} at {scheduled_at}")
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
    
    # ==================== Preferences Management (per-network) ====================
    
    def get_preferences(self, network_id: int) -> NotificationPreferences:
        """Get notification preferences for a network (creates default if not exists)"""
        key = str(network_id)
        if key not in self._preferences:
            self._preferences[key] = NotificationPreferences(network_id=network_id)
            self._save_preferences()
        
        return self._preferences[key]
    
    def update_preferences(self, network_id: int, update: NotificationPreferencesUpdate) -> NotificationPreferences:
        """Update notification preferences for a network"""
        prefs = self.get_preferences(network_id)
        
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
        key = str(network_id)
        self._preferences[key] = NotificationPreferences(**current_data)
        self._save_preferences()
        
        return self._preferences[key]
    
    def delete_preferences(self, network_id: int) -> bool:
        """Delete preferences for a network"""
        key = str(network_id)
        if key in self._preferences:
            del self._preferences[key]
            self._save_preferences()
            return True
        return False
    
    def get_all_networks_with_notifications_enabled(self) -> List[int]:
        """Get list of network IDs with notifications enabled"""
        return [
            int(network_id) for network_id, prefs in self._preferences.items()
            if prefs.enabled and (prefs.email.enabled or prefs.discord.enabled)
        ]
    
    # ==================== Global User Preferences Management ====================
    
    def _save_global_preferences(self):
        """Save global preferences to disk"""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            
            data = {
                user_id: prefs.model_dump(mode="json")
                for user_id, prefs in self._global_preferences.items()
            }
            
            with open(GLOBAL_PREFERENCES_FILE, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.debug(f"Saved {len(self._global_preferences)} global user preferences")
        except Exception as e:
            logger.error(f"Failed to save global preferences: {e}")
    
    def _load_global_preferences(self):
        """Load global preferences from disk"""
        try:
            if not GLOBAL_PREFERENCES_FILE.exists():
                return
            
            with open(GLOBAL_PREFERENCES_FILE, 'r') as f:
                data = json.load(f)
            
            for user_id, prefs_data in data.items():
                # Parse datetime strings
                if "created_at" in prefs_data and isinstance(prefs_data["created_at"], str):
                    prefs_data["created_at"] = datetime.fromisoformat(prefs_data["created_at"].replace("Z", "+00:00"))
                if "updated_at" in prefs_data and isinstance(prefs_data["updated_at"], str):
                    prefs_data["updated_at"] = datetime.fromisoformat(prefs_data["updated_at"].replace("Z", "+00:00"))
                
                try:
                    self._global_preferences[user_id] = GlobalUserPreferences(**prefs_data)
                except Exception as e:
                    logger.warning(f"Failed to load global preferences for user {user_id}: {e}")
                    continue
            
            logger.info(f"Loaded {len(self._global_preferences)} global user preferences")
        except Exception as e:
            logger.error(f"Failed to load global preferences: {e}")
    
    def get_global_preferences(self, user_id: str) -> GlobalUserPreferences:
        """Get global notification preferences for a user (creates default if not exists)"""
        if user_id not in self._global_preferences:
            self._global_preferences[user_id] = GlobalUserPreferences(user_id=user_id)
            self._save_global_preferences()
        
        return self._global_preferences[user_id]
    
    def update_global_preferences(self, user_id: str, update: GlobalUserPreferencesUpdate) -> GlobalUserPreferences:
        """Update global notification preferences for a user"""
        prefs = self.get_global_preferences(user_id)
        
        # Get current preferences as dict
        current_data = prefs.model_dump()
        
        # Get update data (only fields that were set)
        update_data = update.model_dump(exclude_unset=True)
        
        # Merge update into current data
        for key, value in update_data.items():
            if value is not None:
                current_data[key] = value
        
        # Update timestamp
        current_data['updated_at'] = datetime.utcnow()
        
        # Recreate the preferences model with validated data
        self._global_preferences[user_id] = GlobalUserPreferences(**current_data)
        self._save_global_preferences()
        
        return self._global_preferences[user_id]
    
    def get_all_users_with_global_notifications_enabled(self, event_type: NotificationType) -> List[str]:
        """
        Get list of user IDs who have global notifications enabled for a specific event type.
        
        Only returns users who have:
        - cartographer_up_enabled=True for CARTOGRAPHER_UP events
        - cartographer_down_enabled=True for CARTOGRAPHER_DOWN events
        - email_address configured
        """
        if event_type == NotificationType.CARTOGRAPHER_UP:
            return [
                user_id for user_id, prefs in self._global_preferences.items()
                if prefs.cartographer_up_enabled and prefs.email_address
            ]
        elif event_type == NotificationType.CARTOGRAPHER_DOWN:
            return [
                user_id for user_id, prefs in self._global_preferences.items()
                if prefs.cartographer_down_enabled and prefs.email_address
            ]
        return []
    
    # ==================== Rate Limiting ====================
    
    def _check_rate_limit(self, network_id: int, prefs: NotificationPreferences) -> bool:
        """Check if network is within rate limit. Returns True if allowed."""
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        key = str(network_id)
        
        if key not in self._rate_limits:
            self._rate_limits[key] = deque(maxlen=prefs.max_notifications_per_hour)
        
        # Clean old entries
        while self._rate_limits[key] and self._rate_limits[key][0] < hour_ago:
            self._rate_limits[key].popleft()
        
        # Check limit
        if len(self._rate_limits[key]) >= prefs.max_notifications_per_hour:
            return False
        
        return True
    
    def _record_rate_limit(self, network_id: int):
        """Record a notification for rate limiting"""
        now = datetime.utcnow()
        key = str(network_id)
        if key not in self._rate_limits:
            self._rate_limits[key] = deque()
        self._rate_limits[key].append(now)
    
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
        if not self._check_rate_limit(prefs.network_id, prefs):
            return False, "Rate limit exceeded"
        
        return True, ""
    
    async def send_notification_to_network(
        self,
        network_id: int,
        event: NetworkEvent,
        force: bool = False,
    ) -> List[NotificationRecord]:
        """
        Send a notification to a network using the network's preferences.
        
        Args:
            network_id: The network to notify
            event: The network event to notify about
            force: If True, bypass preference checks (for test notifications)
        
        Returns:
            List of NotificationRecord for each channel attempted
        """
        prefs = self.get_preferences(network_id)
        records = []
        
        # Set network_id on event if not already set
        if event.network_id is None:
            event.network_id = network_id
        
        if not force:
            should_notify, reason = self._should_notify(prefs, event)
            if not should_notify:
                logger.info(f"Skipping {event.event_type.value} notification for network {network_id}: {reason}")
                logger.debug(
                    f"  Network {network_id} prefs: enabled={prefs.enabled}, "
                    f"email={prefs.email.enabled} ({prefs.email.email_address}), "
                    f"discord={prefs.discord.enabled}, "
                    f"enabled_types={[t.value for t in prefs.enabled_notification_types]}, "
                    f"min_priority={prefs.minimum_priority.value}"
                )
                return records
        
        notification_id = str(uuid.uuid4())
        
        # Send via email
        if prefs.email.enabled and prefs.email.email_address:
            record = await send_notification_email(
                to_email=prefs.email.email_address,
                event=event,
                notification_id=notification_id,
            )
            record.network_id = network_id
            records.append(record)
            self._history.append(record)
        
        # Send via Discord
        if prefs.discord.enabled:
            record = await send_discord_notification(
                config=prefs.discord,
                event=event,
                notification_id=notification_id,
                user_id=prefs.owner_user_id or "",
            )
            record.network_id = network_id
            records.append(record)
            self._history.append(record)
        
        # Record for rate limiting
        if records and not force:
            self._record_rate_limit(network_id)
        
        # Save history periodically
        if len(self._history) % 50 == 0:
            self._save_history()
        
        return records
    
    async def send_notification_to_network_members(
        self,
        network_id: int,
        user_ids: List[str],
        event: NetworkEvent,
        force: bool = False,
    ) -> Dict[str, List[NotificationRecord]]:
        """
        Send a notification to all network members based on the network's notification preferences.
        
        Note: Currently, notification preferences are per-network (shared by all members).
        All members receive notifications via the network's configured email/Discord channels.
        In the future, this could be enhanced to support per-user preferences per network.
        
        Args:
            network_id: The network this notification is for
            user_ids: List of user IDs who are members of the network
            event: The network event to notify about
            force: If True, bypass preference checks (for test notifications)
        
        Returns:
            Dict mapping user_id -> list of NotificationRecord for each channel attempted
        """
        results = {}
        
        # Set network_id on event if not already set
        if event.network_id is None:
            event.network_id = network_id
        
        # Get network preferences (shared preferences for all network members)
        network_prefs = self.get_preferences(network_id)
        
        # Check if we should send based on network preferences
        if not force:
            should_notify, reason = self._should_notify(network_prefs, event)
            if not should_notify:
                logger.info(f"Skipping broadcast notification for network {network_id}: {reason}")
                return results
        
        notification_id = str(uuid.uuid4())
        
        # Send to network's configured channels (shared by all members)
        # All members will receive the notification through the network's email/Discord
        # We send once per channel, but track that all members received it
        
        # Send via email if enabled
        if network_prefs.email.enabled and network_prefs.email.email_address:
            try:
                record = await send_notification_email(
                    to_email=network_prefs.email.email_address,
                    event=event,
                    notification_id=notification_id,
                )
                record.network_id = network_id
                # Record for all members (they all share the same email address)
                for user_id in user_ids:
                    if user_id not in results:
                        results[user_id] = []
                    # Create a copy of the record for each user for tracking purposes
                    user_record = NotificationRecord(
                        notification_id=record.notification_id,
                        event_id=record.event_id,
                        network_id=record.network_id,
                        channel=record.channel,
                        timestamp=record.timestamp,
                        success=record.success,
                        error_message=record.error_message,
                        title=record.title,
                        message=record.message,
                        priority=record.priority,
                    )
                    results[user_id].append(user_record)
                # Add one record to history (the actual sent notification)
                self._history.append(record)
            except Exception as e:
                logger.error(f"Failed to send email notification for network {network_id}: {e}")
                # Record failure for all members
                for user_id in user_ids:
                    if user_id not in results:
                        results[user_id] = []
                    results[user_id].append(NotificationRecord(
                        notification_id=notification_id,
                        event_id=event.event_id,
                        network_id=network_id,
                        channel=NotificationChannel.EMAIL,
                        success=False,
                        error_message=str(e),
                        title=event.title,
                        message=event.message,
                        priority=event.priority,
                    ))
        
        # Send via Discord if enabled
        if network_prefs.discord.enabled:
            try:
                # Discord notifications can be sent to a channel (shared) or DM (per-user)
                # For broadcasts, we send to the configured channel which all members can see
                record = await send_discord_notification(
                    config=network_prefs.discord,
                    event=event,
                    notification_id=notification_id,
                    user_id=network_prefs.owner_user_id or "",
                )
                record.network_id = network_id
                # Record for all members (they all see the same Discord channel)
                for user_id in user_ids:
                    if user_id not in results:
                        results[user_id] = []
                    # Create a copy of the record for each user for tracking purposes
                    user_record = NotificationRecord(
                        notification_id=record.notification_id,
                        event_id=record.event_id,
                        network_id=record.network_id,
                        channel=record.channel,
                        timestamp=record.timestamp,
                        success=record.success,
                        error_message=record.error_message,
                        title=record.title,
                        message=record.message,
                        priority=record.priority,
                    )
                    results[user_id].append(user_record)
                # Add one record to history (the actual sent notification)
                self._history.append(record)
            except Exception as e:
                logger.error(f"Failed to send Discord notification for network {network_id}: {e}")
                # Record failure for all members
                for user_id in user_ids:
                    if user_id not in results:
                        results[user_id] = []
                    results[user_id].append(NotificationRecord(
                        notification_id=notification_id,
                        event_id=event.event_id,
                        network_id=network_id,
                        channel=NotificationChannel.DISCORD,
                        success=False,
                        error_message=str(e),
                        title=event.title,
                        message=event.message,
                        priority=event.priority,
                    ))
        
        # Record for rate limiting (once per network, not per user)
        if results and not force:
            self._record_rate_limit(network_id)
        
        # Save history periodically
        if len(self._history) % 50 == 0:
            self._save_history()
        
        logger.info(f"Sent broadcast notification to {len(user_ids)} network members in network {network_id} via {len([r for r in results.values() if r])} channels")
        return results
    
    async def send_notification(
        self,
        network_id: int,
        event: NetworkEvent,
        force: bool = False,
    ) -> List[NotificationRecord]:
        """
        Send a notification to a network (alias for send_notification_to_network for backwards compatibility).
        
        Args:
            network_id: The network to notify
            event: The network event to notify about
            force: If True, bypass preference checks (for test notifications)
        
        Returns:
            List of NotificationRecord for each channel attempted
        """
        return await self.send_notification_to_network(network_id, event, force)
    
    async def broadcast_notification(self, event: NetworkEvent) -> Dict[str, List[NotificationRecord]]:
        """
        Send a notification to all networks with notifications enabled.
        
        Returns a dict of network_id -> list of records.
        """
        results = {}
        
        enabled_networks = self.get_all_networks_with_notifications_enabled()
        logger.info(f"Broadcasting {event.event_type.value} notification to {len(enabled_networks)} networks")
        
        if not enabled_networks:
            logger.warning(f"No networks have notifications enabled for {event.event_type.value} notifications")
            return results
        
        for network_id in enabled_networks:
            # Create a copy of the event with the network_id set
            # Use model_dump and recreate to avoid mutating the original event
            event_dict = event.model_dump()
            event_dict['network_id'] = network_id
            event_copy = NetworkEvent(**event_dict)
            
            records = await self.send_notification(network_id, event_copy)
            if records:
                results[str(network_id)] = records
                logger.debug(f"Sent notification to network {network_id}: {len(records)} channels")
            else:
                logger.debug(f"No notifications sent to network {network_id} (filtered by preferences)")
        
        logger.info(f"Broadcast complete: {len(results)} networks notified out of {len(enabled_networks)} enabled")
        return results
    
    async def broadcast_global_notification(self, event: NetworkEvent) -> Dict[str, List[NotificationRecord]]:
        """
        Send a global notification (Cartographer Up/Down) to all users who have global preferences enabled.
        
        This is separate from network-scoped notifications and uses global user preferences.
        Only sends via email (global preferences don't support Discord).
        
        Returns a dict of user_id -> list of records.
        """
        results = {}
        
        # Only handle Cartographer Up/Down events
        if event.event_type not in (NotificationType.CARTOGRAPHER_UP, NotificationType.CARTOGRAPHER_DOWN):
            logger.warning(f"broadcast_global_notification called for non-global event type: {event.event_type}")
            return results
        
        # Get all users who have this notification type enabled
        user_ids = self.get_all_users_with_global_notifications_enabled(event.event_type)
        
        if not user_ids:
            logger.debug(f"No users have global notifications enabled for {event.event_type.value}")
            return results
        
        notification_id = str(uuid.uuid4())
        
        # Send email to each user
        for user_id in user_ids:
            prefs = self._global_preferences[user_id]
            
            if not prefs.email_address:
                continue
            
            try:
                record = await send_notification_email(
                    to_email=prefs.email_address,
                    event=event,
                    notification_id=notification_id,
                )
                # Use network_id=0 for global notifications (not network-specific)
                record.network_id = 0
                results[user_id] = [record]
                self._history.append(record)
            except Exception as e:
                logger.error(f"Failed to send global notification to user {user_id}: {e}")
                # Create a failed record
                record = NotificationRecord(
                    notification_id=notification_id,
                    event_id=event.event_id,
                    network_id=0,
                    channel=NotificationChannel.EMAIL,
                    success=False,
                    error_message=str(e),
                    title=event.title,
                    message=event.message,
                    priority=event.priority,
                )
                results[user_id] = [record]
                self._history.append(record)
        
        # Save history periodically
        if len(self._history) % 50 == 0:
            self._save_history()
        
        logger.info(f"Broadcasted global notification to {len(results)} users: {event.title}")
        return results
    
    async def send_test_notification(
        self,
        network_id: int,
        request: TestNotificationRequest,
    ) -> TestNotificationResponse:
        """Send a test notification via a specific channel"""
        prefs = self.get_preferences(network_id)
        
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
        network_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> NotificationHistoryResponse:
        """Get notification history, optionally filtered by network"""
        records = list(self._history)
        
        if network_id is not None:
            records = [r for r in records if r.network_id == network_id]
        
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
    
    def get_stats(self, network_id: Optional[int] = None) -> NotificationStatsResponse:
        """Get notification statistics"""
        now = datetime.utcnow()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        
        records = list(self._history)
        
        if network_id is not None:
            records = [r for r in records if r.network_id == network_id]
        
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
        network_id: int,
        latency_ms: Optional[float] = None,
        packet_loss: Optional[float] = None,
        device_name: Optional[str] = None,
        previous_state: Optional[str] = None,
    ):
        """
        Process a health check result and send notifications if needed.
        
        This should be called after each health check to train the ML model
        and potentially send notifications.
        
        Args:
            device_ip: IP address of the device
            success: Whether the health check succeeded
            network_id: The network this device belongs to
            latency_ms: Optional latency measurement
            packet_loss: Optional packet loss percentage
            device_name: Optional device name
            previous_state: Optional previous state (online/offline)
        
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
            # Set network_id on the event
            event.network_id = network_id
            
            logger.info(f"Processing health check for device {device_ip} in network {network_id}: event_type={event.event_type.value}, success={success}")
            
            # Send notification only to the specific network
            records = await self.send_notification_to_network(network_id, event)
            if records:
                logger.info(f"✓ Sent notification to network {network_id} for device {device_ip}: {event.title} ({len(records)} channels)")
            else:
                # Get preferences to see why it was filtered
                prefs = self.get_preferences(network_id)
                should_notify, reason = self._should_notify(prefs, event)
                logger.warning(
                    f"✗ No notifications sent for network {network_id}, device {device_ip}, event {event.event_type.value}: {reason}. "
                    f"Prefs: enabled={prefs.enabled}, email={prefs.email.enabled}, discord={prefs.discord.enabled}, "
                    f"event_type_in_enabled={event.event_type in prefs.enabled_notification_types}"
                )
        elif event and is_silenced:
            logger.debug(f"Skipping notification for silenced device {device_ip}: {event.title}")
        elif not event:
            logger.debug(f"No event created for device {device_ip} (network {network_id}) - likely not notification-worthy")


# Singleton instance
notification_manager = NotificationManager()

