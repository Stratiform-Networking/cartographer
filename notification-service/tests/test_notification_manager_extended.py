"""
Extended tests for NotificationManager to improve coverage.

Covers:
- Scheduler loop
- Scheduled broadcasts processing
- Network member notifications
- Global preferences migration
- Quiet hours with timezone
- Rate limiting edge cases
- History persistence
"""

import os
import json
import asyncio
import pytest
from datetime import datetime, timedelta, timezone as dt_timezone
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from zoneinfo import ZoneInfo

# Set test environment
os.environ["NOTIFICATION_DATA_DIR"] = "/tmp/test_notification_data_extended"

from app.models import (
    NotificationPreferences,
    NotificationPreferencesUpdate,
    GlobalUserPreferences,
    GlobalUserPreferencesUpdate,
    NetworkEvent,
    NotificationType,
    NotificationPriority,
    NotificationRecord,
    NotificationChannel,
    EmailConfig,
    DiscordConfig,
    ScheduledBroadcast,
    ScheduledBroadcastStatus,
    ScheduledBroadcastCreate,
    ScheduledBroadcastUpdate,
    TestNotificationRequest,
)


@pytest.fixture
def fresh_notification_manager():
    """Create a fresh NotificationManager instance for each test."""
    from app.services.notification_manager import NotificationManager
    
    manager = NotificationManager()
    manager._preferences.clear()
    manager._global_preferences.clear()
    manager._history.clear()
    manager._rate_limits.clear()
    manager._scheduled_broadcasts.clear()
    manager._silenced_devices.clear()
    
    yield manager


class TestScheduledBroadcastScheduler:
    """Tests for scheduled broadcast scheduler functionality."""
    
    @pytest.mark.asyncio
    async def test_start_scheduler(self, fresh_notification_manager):
        """Test starting the scheduler."""
        manager = fresh_notification_manager
        
        await manager.start_scheduler()
        
        assert manager._scheduler_task is not None
        
        # Clean up
        await manager.stop_scheduler()
    
    @pytest.mark.asyncio
    async def test_start_scheduler_already_running(self, fresh_notification_manager):
        """Test starting scheduler when already running does nothing."""
        manager = fresh_notification_manager
        
        await manager.start_scheduler()
        first_task = manager._scheduler_task
        
        await manager.start_scheduler()  # Should do nothing
        assert manager._scheduler_task is first_task
        
        await manager.stop_scheduler()
    
    @pytest.mark.asyncio
    async def test_stop_scheduler(self, fresh_notification_manager):
        """Test stopping the scheduler."""
        manager = fresh_notification_manager
        
        await manager.start_scheduler()
        await manager.stop_scheduler()
        
        assert manager._scheduler_task is None
    
    @pytest.mark.asyncio
    async def test_stop_scheduler_not_running(self, fresh_notification_manager):
        """Test stopping scheduler when not running."""
        manager = fresh_notification_manager
        
        await manager.stop_scheduler()  # Should not error
        assert manager._scheduler_task is None
    
    @pytest.mark.asyncio
    async def test_scheduler_loop_cancellation(self, fresh_notification_manager):
        """Test scheduler loop handles cancellation properly."""
        manager = fresh_notification_manager
        
        await manager.start_scheduler()
        await asyncio.sleep(0.1)  # Let loop start
        
        manager._scheduler_task.cancel()
        try:
            await manager._scheduler_task
        except asyncio.CancelledError:
            pass
        
        manager._scheduler_task = None


class TestScheduledBroadcastProcessing:
    """Tests for processing due broadcasts."""
    
    @pytest.mark.asyncio
    async def test_process_due_broadcasts_none_pending(self, fresh_notification_manager):
        """Test processing when no broadcasts are pending."""
        manager = fresh_notification_manager
        
        await manager._process_due_broadcasts()
        # Should complete without error
    
    @pytest.mark.asyncio
    async def test_process_due_broadcasts_not_yet_due(self, fresh_notification_manager):
        """Test processing broadcasts that are not yet due."""
        manager = fresh_notification_manager
        
        # Create a future broadcast
        broadcast = manager.create_scheduled_broadcast(
            title="Future Broadcast",
            message="This is scheduled for the future",
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
            created_by="testuser",
            network_id="test-network-id",
        )
        
        await manager._process_due_broadcasts()
        
        # Should still be pending
        assert broadcast.status == ScheduledBroadcastStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_process_due_broadcasts_skips_non_pending(self, fresh_notification_manager):
        """Test processing skips already sent broadcasts."""
        manager = fresh_notification_manager
        
        # Create and mark as sent
        broadcast = manager.create_scheduled_broadcast(
            title="Already Sent",
            message="This was already sent",
            scheduled_at=datetime.utcnow() - timedelta(minutes=5),
            created_by="testuser",
            network_id="test-network-id",
        )
        broadcast.status = ScheduledBroadcastStatus.SENT
        
        await manager._process_due_broadcasts()
        # Should not error and broadcast remains sent
        assert broadcast.status == ScheduledBroadcastStatus.SENT
    
    @pytest.mark.asyncio
    async def test_process_due_broadcasts_timezone_aware(self, fresh_notification_manager):
        """Test processing broadcasts with timezone-aware datetime."""
        manager = fresh_notification_manager
        
        # Create broadcast with timezone-aware datetime
        tz_aware_time = datetime.now(dt_timezone.utc) - timedelta(minutes=1)
        broadcast = manager.create_scheduled_broadcast(
            title="Timezone Aware Broadcast",
            message="This has a timezone-aware datetime",
            scheduled_at=tz_aware_time,
            created_by="testuser",
            network_id="test-network-id",
            timezone="America/New_York",
        )
        
        # Mock the send method
        with patch.object(manager, '_send_scheduled_broadcast', new_callable=AsyncMock) as mock_send:
            await manager._process_due_broadcasts()
            mock_send.assert_called_once()


class TestSendScheduledBroadcast:
    """Tests for sending scheduled broadcasts."""
    
    @pytest.mark.asyncio
    async def test_send_scheduled_broadcast_not_found(self, fresh_notification_manager):
        """Test sending broadcast that doesn't exist."""
        manager = fresh_notification_manager
        
        await manager._send_scheduled_broadcast("nonexistent-id")
        # Should complete without error
    
    @pytest.mark.asyncio
    async def test_send_scheduled_broadcast_exception(self, fresh_notification_manager):
        """Test sending broadcast handles exceptions."""
        manager = fresh_notification_manager
        
        broadcast = manager.create_scheduled_broadcast(
            title="Test Broadcast",
            message="Test message",
            scheduled_at=datetime.utcnow() - timedelta(minutes=1),
            created_by="testuser",
            network_id="test-network-id",
        )
        
        with patch.object(manager, '_get_network_member_user_ids', new_callable=AsyncMock, 
                         side_effect=Exception("Database error")):
            await manager._send_scheduled_broadcast(broadcast.id)
        
        assert broadcast.status == ScheduledBroadcastStatus.FAILED
        assert "Database error" in broadcast.error_message


class TestScheduledBroadcastManagement:
    """Tests for scheduled broadcast CRUD operations."""
    
    def test_create_scheduled_broadcast(self, fresh_notification_manager):
        """Test creating a scheduled broadcast."""
        manager = fresh_notification_manager
        
        broadcast = manager.create_scheduled_broadcast(
            title="Test Broadcast",
            message="Test message",
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
            created_by="testuser",
            network_id="test-network-id",
            event_type=NotificationType.SCHEDULED_MAINTENANCE,
            priority=NotificationPriority.HIGH,
            timezone="America/New_York",
        )
        
        assert broadcast.title == "Test Broadcast"
        assert broadcast.message == "Test message"
        assert broadcast.network_id == "test-network-id"
        assert broadcast.event_type == NotificationType.SCHEDULED_MAINTENANCE
        assert broadcast.priority == NotificationPriority.HIGH
        assert broadcast.timezone == "America/New_York"
        assert broadcast.status == ScheduledBroadcastStatus.PENDING
    
    def test_get_scheduled_broadcasts_pending_only(self, fresh_notification_manager):
        """Test getting only pending broadcasts."""
        manager = fresh_notification_manager
        
        # Create pending and sent broadcasts
        pending = manager.create_scheduled_broadcast(
            title="Pending",
            message="Pending message",
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
            created_by="testuser",
            network_id="test-network-id",
        )
        
        sent = manager.create_scheduled_broadcast(
            title="Sent",
            message="Sent message",
            scheduled_at=datetime.utcnow() - timedelta(hours=1),
            created_by="testuser",
            network_id="test-network-id",
        )
        sent.status = ScheduledBroadcastStatus.SENT
        
        response = manager.get_scheduled_broadcasts(include_completed=False)
        
        assert len(response.broadcasts) == 1
        assert response.broadcasts[0].title == "Pending"
    
    def test_get_scheduled_broadcasts_include_completed(self, fresh_notification_manager):
        """Test getting all broadcasts including completed."""
        manager = fresh_notification_manager
        
        pending = manager.create_scheduled_broadcast(
            title="Pending",
            message="Pending message",
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
            created_by="testuser",
            network_id="test-network-id",
        )
        
        sent = manager.create_scheduled_broadcast(
            title="Sent",
            message="Sent message",
            scheduled_at=datetime.utcnow() - timedelta(hours=1),
            created_by="testuser",
            network_id="test-network-id",
        )
        sent.status = ScheduledBroadcastStatus.SENT
        
        response = manager.get_scheduled_broadcasts(include_completed=True)
        
        assert len(response.broadcasts) == 2
    
    def test_get_scheduled_broadcasts_filters_seen(self, fresh_notification_manager):
        """Test that seen broadcasts are filtered after delay."""
        manager = fresh_notification_manager
        
        # Create a sent broadcast that was seen long ago
        sent = manager.create_scheduled_broadcast(
            title="Sent and Seen",
            message="Already seen",
            scheduled_at=datetime.utcnow() - timedelta(hours=1),
            created_by="testuser",
            network_id="test-network-id",
        )
        sent.status = ScheduledBroadcastStatus.SENT
        sent.seen_at = datetime.now(dt_timezone.utc) - timedelta(seconds=10)
        
        response = manager.get_scheduled_broadcasts(include_completed=True)
        
        # Should be filtered out
        assert len(response.broadcasts) == 0
    
    def test_get_scheduled_broadcast(self, fresh_notification_manager):
        """Test getting a specific broadcast."""
        manager = fresh_notification_manager
        
        broadcast = manager.create_scheduled_broadcast(
            title="Test",
            message="Test",
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
            created_by="testuser",
            network_id="test-network-id",
        )
        
        found = manager.get_scheduled_broadcast(broadcast.id)
        assert found.id == broadcast.id
        
        not_found = manager.get_scheduled_broadcast("nonexistent")
        assert not_found is None
    
    def test_cancel_scheduled_broadcast(self, fresh_notification_manager):
        """Test cancelling a broadcast."""
        manager = fresh_notification_manager
        
        broadcast = manager.create_scheduled_broadcast(
            title="Test",
            message="Test",
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
            created_by="testuser",
            network_id="test-network-id",
        )
        
        success = manager.cancel_scheduled_broadcast(broadcast.id)
        assert success is True
        assert broadcast.status == ScheduledBroadcastStatus.CANCELLED
    
    def test_cancel_scheduled_broadcast_not_found(self, fresh_notification_manager):
        """Test cancelling nonexistent broadcast."""
        manager = fresh_notification_manager
        
        success = manager.cancel_scheduled_broadcast("nonexistent")
        assert success is False
    
    def test_cancel_scheduled_broadcast_not_pending(self, fresh_notification_manager):
        """Test cancelling already sent broadcast."""
        manager = fresh_notification_manager
        
        broadcast = manager.create_scheduled_broadcast(
            title="Test",
            message="Test",
            scheduled_at=datetime.utcnow() - timedelta(hours=1),
            created_by="testuser",
            network_id="test-network-id",
        )
        broadcast.status = ScheduledBroadcastStatus.SENT
        
        success = manager.cancel_scheduled_broadcast(broadcast.id)
        assert success is False
    
    def test_delete_scheduled_broadcast(self, fresh_notification_manager):
        """Test deleting a cancelled broadcast."""
        manager = fresh_notification_manager
        
        broadcast = manager.create_scheduled_broadcast(
            title="Test",
            message="Test",
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
            created_by="testuser",
            network_id="test-network-id",
        )
        manager.cancel_scheduled_broadcast(broadcast.id)
        
        success = manager.delete_scheduled_broadcast(broadcast.id)
        assert success is True
        assert manager.get_scheduled_broadcast(broadcast.id) is None
    
    def test_delete_scheduled_broadcast_not_found(self, fresh_notification_manager):
        """Test deleting nonexistent broadcast."""
        manager = fresh_notification_manager
        
        success = manager.delete_scheduled_broadcast("nonexistent")
        assert success is False
    
    def test_delete_scheduled_broadcast_still_pending(self, fresh_notification_manager):
        """Test deleting pending broadcast fails."""
        manager = fresh_notification_manager
        
        broadcast = manager.create_scheduled_broadcast(
            title="Test",
            message="Test",
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
            created_by="testuser",
            network_id="test-network-id",
        )
        
        success = manager.delete_scheduled_broadcast(broadcast.id)
        assert success is False
    
    def test_mark_broadcast_seen(self, fresh_notification_manager):
        """Test marking a broadcast as seen."""
        manager = fresh_notification_manager
        
        broadcast = manager.create_scheduled_broadcast(
            title="Test",
            message="Test",
            scheduled_at=datetime.utcnow() - timedelta(hours=1),
            created_by="testuser",
            network_id="test-network-id",
        )
        broadcast.status = ScheduledBroadcastStatus.SENT
        
        result = manager.mark_broadcast_seen(broadcast.id)
        assert result is not None
        assert result.seen_at is not None
    
    def test_mark_broadcast_seen_not_found(self, fresh_notification_manager):
        """Test marking nonexistent broadcast as seen."""
        manager = fresh_notification_manager
        
        result = manager.mark_broadcast_seen("nonexistent")
        assert result is None
    
    def test_mark_broadcast_seen_not_sent(self, fresh_notification_manager):
        """Test marking non-sent broadcast as seen."""
        manager = fresh_notification_manager
        
        broadcast = manager.create_scheduled_broadcast(
            title="Test",
            message="Test",
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
            created_by="testuser",
            network_id="test-network-id",
        )
        
        result = manager.mark_broadcast_seen(broadcast.id)
        assert result is not None
        assert result.seen_at is None  # Not set for non-sent
    
    def test_mark_broadcast_seen_already_seen(self, fresh_notification_manager):
        """Test marking already-seen broadcast."""
        manager = fresh_notification_manager
        
        broadcast = manager.create_scheduled_broadcast(
            title="Test",
            message="Test",
            scheduled_at=datetime.utcnow() - timedelta(hours=1),
            created_by="testuser",
            network_id="test-network-id",
        )
        broadcast.status = ScheduledBroadcastStatus.SENT
        
        manager.mark_broadcast_seen(broadcast.id)
        first_seen = broadcast.seen_at
        
        manager.mark_broadcast_seen(broadcast.id)
        assert broadcast.seen_at == first_seen  # Unchanged
    
    def test_update_scheduled_broadcast(self, fresh_notification_manager):
        """Test updating a scheduled broadcast."""
        manager = fresh_notification_manager
        
        broadcast = manager.create_scheduled_broadcast(
            title="Original Title",
            message="Original message",
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
            created_by="testuser",
            network_id="test-network-id",
        )
        
        update = ScheduledBroadcastUpdate(
            title="Updated Title",
            message="Updated message",
            priority=NotificationPriority.CRITICAL,
        )
        
        updated = manager.update_scheduled_broadcast(broadcast.id, update)
        
        assert updated.title == "Updated Title"
        assert updated.message == "Updated message"
        assert updated.priority == NotificationPriority.CRITICAL
    
    def test_update_scheduled_broadcast_not_found(self, fresh_notification_manager):
        """Test updating nonexistent broadcast."""
        manager = fresh_notification_manager
        
        update = ScheduledBroadcastUpdate(title="New Title")
        result = manager.update_scheduled_broadcast("nonexistent", update)
        
        assert result is None
    
    def test_update_scheduled_broadcast_not_pending(self, fresh_notification_manager):
        """Test updating non-pending broadcast."""
        manager = fresh_notification_manager
        
        broadcast = manager.create_scheduled_broadcast(
            title="Test",
            message="Test",
            scheduled_at=datetime.utcnow() - timedelta(hours=1),
            created_by="testuser",
            network_id="test-network-id",
        )
        broadcast.status = ScheduledBroadcastStatus.SENT
        
        update = ScheduledBroadcastUpdate(title="New Title")
        result = manager.update_scheduled_broadcast(broadcast.id, update)
        
        assert result is None


class TestQuietHoursTimezone:
    """Tests for quiet hours with timezone support."""
    
    def test_get_current_time_with_valid_timezone(self, fresh_notification_manager):
        """Test getting current time with valid timezone."""
        manager = fresh_notification_manager
        
        time = manager._get_current_time_for_user("America/New_York")
        assert time is not None
    
    def test_get_current_time_with_invalid_timezone(self, fresh_notification_manager):
        """Test getting current time with invalid timezone falls back."""
        manager = fresh_notification_manager
        
        time = manager._get_current_time_for_user("Invalid/Timezone")
        assert time is not None  # Should fall back to local time
    
    def test_get_current_time_with_none_timezone(self, fresh_notification_manager):
        """Test getting current time with None timezone."""
        manager = fresh_notification_manager
        
        time = manager._get_current_time_for_user(None)
        assert time is not None
    
    def test_is_quiet_hours_not_enabled(self, fresh_notification_manager):
        """Test quiet hours when not enabled."""
        manager = fresh_notification_manager
        
        prefs = NotificationPreferences(
            network_id="test-network",
            quiet_hours_enabled=False,
        )
        
        assert manager._is_quiet_hours(prefs) is False
    
    def test_is_quiet_hours_no_times(self, fresh_notification_manager):
        """Test quiet hours with no times set."""
        manager = fresh_notification_manager
        
        prefs = NotificationPreferences(
            network_id="test-network",
            quiet_hours_enabled=True,
            quiet_hours_start=None,
            quiet_hours_end=None,
        )
        
        assert manager._is_quiet_hours(prefs) is False


class TestGlobalUserPreferences:
    """Tests for global user preferences."""
    
    def test_get_global_preferences_new_user(self, fresh_notification_manager):
        """Test getting global preferences creates default for new user."""
        manager = fresh_notification_manager
        
        prefs = manager.get_global_preferences("new-user")
        
        assert prefs.user_id == "new-user"
        assert prefs.cartographer_up_enabled is True  # Default
        assert prefs.cartographer_down_enabled is True  # Default
    
    def test_update_global_preferences(self, fresh_notification_manager):
        """Test updating global preferences."""
        manager = fresh_notification_manager
        
        manager.get_global_preferences("test-user")
        
        update = GlobalUserPreferencesUpdate(
            email_address="updated@example.com",
            cartographer_up_enabled=False,
        )
        
        updated = manager.update_global_preferences("test-user", update)
        
        assert updated.email_address == "updated@example.com"
        assert updated.cartographer_up_enabled is False
    
    def test_get_users_with_global_notifications_cartographer_up(self, fresh_notification_manager):
        """Test getting users with Cartographer Up notifications enabled."""
        manager = fresh_notification_manager
        
        # Create users with different settings
        manager._global_preferences["user1"] = GlobalUserPreferences(
            user_id="user1",
            email_address="user1@example.com",
            cartographer_up_enabled=True,
            cartographer_down_enabled=False,
        )
        manager._global_preferences["user2"] = GlobalUserPreferences(
            user_id="user2",
            email_address="user2@example.com",
            cartographer_up_enabled=False,
            cartographer_down_enabled=True,
        )
        manager._global_preferences["user3"] = GlobalUserPreferences(
            user_id="user3",
            email_address=None,  # No email
            cartographer_up_enabled=True,
            cartographer_down_enabled=True,
        )
        
        users = manager.get_all_users_with_global_notifications_enabled(NotificationType.CARTOGRAPHER_UP)
        
        assert "user1" in users
        assert "user2" not in users
        assert "user3" not in users  # No email
    
    def test_get_users_with_global_notifications_cartographer_down(self, fresh_notification_manager):
        """Test getting users with Cartographer Down notifications enabled."""
        manager = fresh_notification_manager
        
        manager._global_preferences["user1"] = GlobalUserPreferences(
            user_id="user1",
            email_address="user1@example.com",
            cartographer_up_enabled=True,
            cartographer_down_enabled=False,
        )
        manager._global_preferences["user2"] = GlobalUserPreferences(
            user_id="user2",
            email_address="user2@example.com",
            cartographer_up_enabled=False,
            cartographer_down_enabled=True,
        )
        
        users = manager.get_all_users_with_global_notifications_enabled(NotificationType.CARTOGRAPHER_DOWN)
        
        assert "user1" not in users
        assert "user2" in users
    
    def test_get_users_with_global_notifications_other_type(self, fresh_notification_manager):
        """Test getting users with other notification types returns empty."""
        manager = fresh_notification_manager
        
        users = manager.get_all_users_with_global_notifications_enabled(NotificationType.DEVICE_OFFLINE)
        
        assert users == []


class TestMigrateUsersToGlobalPreferences:
    """Tests for migration of users to global preferences."""
    
    def test_migrate_users_with_email(self, fresh_notification_manager):
        """Test migration creates global prefs for users with email."""
        manager = fresh_notification_manager
        
        # Create network preferences with owner and email
        manager._preferences["network1"] = NotificationPreferences(
            network_id="network1",
            owner_user_id="owner1",
            email=EmailConfig(enabled=True, email_address="owner1@example.com"),
        )
        
        manager._migrate_users_to_global_preferences()
        
        assert "owner1" in manager._global_preferences
        assert manager._global_preferences["owner1"].email_address == "owner1@example.com"
    
    def test_migrate_users_skips_no_email(self, fresh_notification_manager):
        """Test migration skips users without email."""
        manager = fresh_notification_manager
        
        manager._preferences["network1"] = NotificationPreferences(
            network_id="network1",
            owner_user_id="owner1",
            email=EmailConfig(enabled=False),
        )
        
        manager._migrate_users_to_global_preferences()
        
        assert "owner1" not in manager._global_preferences
    
    def test_migrate_users_skips_existing(self, fresh_notification_manager):
        """Test migration skips users who already have global prefs."""
        manager = fresh_notification_manager
        
        # Create existing global preferences
        manager._global_preferences["owner1"] = GlobalUserPreferences(
            user_id="owner1",
            email_address="original@example.com",
        )
        
        # Create network preferences
        manager._preferences["network1"] = NotificationPreferences(
            network_id="network1",
            owner_user_id="owner1",
            email=EmailConfig(enabled=True, email_address="new@example.com"),
        )
        
        manager._migrate_users_to_global_preferences()
        
        # Should keep original email
        assert manager._global_preferences["owner1"].email_address == "original@example.com"


class TestBroadcastNotifications:
    """Tests for broadcast notification functionality."""
    
    @pytest.mark.asyncio
    async def test_broadcast_notification_no_networks(self, fresh_notification_manager):
        """Test broadcasting when no networks have notifications enabled."""
        manager = fresh_notification_manager
        
        event = NetworkEvent(
            event_type=NotificationType.SYSTEM_STATUS,
            priority=NotificationPriority.MEDIUM,
            title="Test",
            message="Test message",
        )
        
        results = await manager.broadcast_notification(event)
        
        assert results == {}
    
    @pytest.mark.asyncio
    async def test_broadcast_global_notification_non_global_type(self, fresh_notification_manager):
        """Test global broadcast with non-global event type."""
        manager = fresh_notification_manager
        
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            priority=NotificationPriority.HIGH,
            title="Test",
            message="Test message",
        )
        
        results = await manager.broadcast_global_notification(event)
        
        assert results == {}
    
    @pytest.mark.asyncio
    async def test_broadcast_global_notification_email_not_configured(self, fresh_notification_manager):
        """Test global broadcast when email not configured."""
        manager = fresh_notification_manager
        
        event = NetworkEvent(
            event_type=NotificationType.CARTOGRAPHER_UP,
            priority=NotificationPriority.HIGH,
            title="Test",
            message="Test message",
        )
        
        with patch('app.services.notification_manager.is_email_configured', return_value=False):
            results = await manager.broadcast_global_notification(event)
        
        assert results == {}
    
    @pytest.mark.asyncio
    async def test_broadcast_global_notification_no_subscribers(self, fresh_notification_manager):
        """Test global broadcast with no subscribers."""
        manager = fresh_notification_manager
        
        event = NetworkEvent(
            event_type=NotificationType.CARTOGRAPHER_UP,
            priority=NotificationPriority.HIGH,
            title="Test",
            message="Test message",
        )
        
        with patch('app.services.notification_manager.is_email_configured', return_value=True):
            results = await manager.broadcast_global_notification(event)
        
        assert results == {}


class TestNotificationSending:
    """Tests for notification sending functionality."""
    
    @pytest.mark.asyncio
    async def test_send_notification_to_network_disabled(self, fresh_notification_manager):
        """Test sending when notifications disabled."""
        manager = fresh_notification_manager
        
        # Create disabled preferences
        manager._preferences["test-network"] = NotificationPreferences(
            network_id="test-network",
            enabled=False,
        )
        
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            priority=NotificationPriority.HIGH,
            title="Test",
            message="Test message",
        )
        
        records = await manager.send_notification_to_network("test-network", event)
        
        assert records == []
    
    @pytest.mark.asyncio
    async def test_send_notification_to_network_no_channels(self, fresh_notification_manager):
        """Test sending when no channels enabled."""
        manager = fresh_notification_manager
        
        manager._preferences["test-network"] = NotificationPreferences(
            network_id="test-network",
            enabled=True,
            email=EmailConfig(enabled=False),
            discord=DiscordConfig(enabled=False),
        )
        
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            priority=NotificationPriority.HIGH,
            title="Test",
            message="Test message",
        )
        
        records = await manager.send_notification_to_network("test-network", event)
        
        assert records == []
    
    @pytest.mark.asyncio
    async def test_send_notification_to_network_rate_limited(self, fresh_notification_manager):
        """Test sending when rate limited."""
        manager = fresh_notification_manager
        
        manager._preferences["test-network"] = NotificationPreferences(
            network_id="test-network",
            enabled=True,
            email=EmailConfig(enabled=True, email_address="test@example.com"),
            max_notifications_per_hour=1,
            enabled_notification_types=[NotificationType.DEVICE_OFFLINE],
        )
        
        # Fill rate limit
        from collections import deque
        manager._rate_limits["test-network"] = deque([datetime.utcnow()])
        
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            priority=NotificationPriority.HIGH,
            title="Test",
            message="Test message",
        )
        
        records = await manager.send_notification_to_network("test-network", event)
        
        assert records == []
    
    @pytest.mark.asyncio
    async def test_send_notification_force_bypasses_checks(self, fresh_notification_manager):
        """Test force flag bypasses preference checks."""
        manager = fresh_notification_manager
        
        # Disabled preferences
        manager._preferences["test-network"] = NotificationPreferences(
            network_id="test-network",
            enabled=False,
            email=EmailConfig(enabled=True, email_address="test@example.com"),
        )
        
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            priority=NotificationPriority.HIGH,
            title="Test",
            message="Test message",
        )
        
        with patch('app.services.notification_manager.is_email_configured', return_value=False):
            records = await manager.send_notification_to_network("test-network", event, force=True)
        
        # Should attempt but fail due to config
        assert len(records) == 1
        assert records[0].success is False


class TestTestNotifications:
    """Tests for test notification functionality."""
    
    @pytest.mark.asyncio
    async def test_send_test_notification_email_no_address(self, fresh_notification_manager):
        """Test sending test email without address configured."""
        manager = fresh_notification_manager
        
        manager._preferences["test-network"] = NotificationPreferences(
            network_id="test-network",
        )
        
        request = TestNotificationRequest(channel=NotificationChannel.EMAIL)
        response = await manager.send_test_notification("test-network", request)
        
        assert response.success is False
        assert "email address" in response.message.lower() or "email address" in (response.error or "").lower()
    
    @pytest.mark.asyncio
    async def test_send_test_notification_discord_not_enabled(self, fresh_notification_manager):
        """Test sending test Discord when not enabled."""
        manager = fresh_notification_manager
        
        manager._preferences["test-network"] = NotificationPreferences(
            network_id="test-network",
            discord=DiscordConfig(enabled=False),
        )
        
        request = TestNotificationRequest(channel=NotificationChannel.DISCORD)
        response = await manager.send_test_notification("test-network", request)
        
        assert response.success is False
        assert "not enabled" in response.message.lower() or "enable" in (response.error or "").lower()
    
    @pytest.mark.asyncio
    async def test_send_test_notification_email_success(self, fresh_notification_manager):
        """Test sending test email successfully."""
        manager = fresh_notification_manager
        
        manager._preferences["test-network"] = NotificationPreferences(
            network_id="test-network",
            email=EmailConfig(enabled=True, email_address="test@example.com"),
        )
        
        request = TestNotificationRequest(channel=NotificationChannel.EMAIL)
        
        with patch('app.services.notification_manager.send_test_email', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"success": True}
            response = await manager.send_test_notification("test-network", request)
        
        assert response.success is True


class TestSilencedDevices:
    """Tests for silenced devices functionality."""
    
    def test_is_device_silenced(self, fresh_notification_manager):
        """Test checking if device is silenced."""
        manager = fresh_notification_manager
        
        manager._silenced_devices.add("192.168.1.1")
        
        assert manager.is_device_silenced("192.168.1.1") is True
        assert manager.is_device_silenced("192.168.1.2") is False
    
    def test_silence_device(self, fresh_notification_manager):
        """Test silencing a device."""
        manager = fresh_notification_manager
        
        result = manager.silence_device("192.168.1.1")
        assert result is True
        assert "192.168.1.1" in manager._silenced_devices
        
        # Second call returns False
        result = manager.silence_device("192.168.1.1")
        assert result is False
    
    def test_unsilence_device(self, fresh_notification_manager):
        """Test unsilencing a device."""
        manager = fresh_notification_manager
        
        manager._silenced_devices.add("192.168.1.1")
        
        result = manager.unsilence_device("192.168.1.1")
        assert result is True
        assert "192.168.1.1" not in manager._silenced_devices
        
        # Second call returns False
        result = manager.unsilence_device("192.168.1.1")
        assert result is False
    
    def test_set_silenced_devices(self, fresh_notification_manager):
        """Test setting silenced devices list."""
        manager = fresh_notification_manager
        
        manager.set_silenced_devices(["192.168.1.1", "192.168.1.2"])
        
        assert len(manager._silenced_devices) == 2
        assert "192.168.1.1" in manager._silenced_devices
        assert "192.168.1.2" in manager._silenced_devices
    
    def test_get_silenced_devices(self, fresh_notification_manager):
        """Test getting silenced devices list."""
        manager = fresh_notification_manager
        
        manager._silenced_devices = {"192.168.1.1", "192.168.1.2"}
        
        devices = manager.get_silenced_devices()
        
        assert len(devices) == 2
        assert "192.168.1.1" in devices
        assert "192.168.1.2" in devices


class TestPreferencesPersistence:
    """Tests for preferences persistence."""
    
    def test_load_preferences_no_file(self, fresh_notification_manager):
        """Test loading preferences when file doesn't exist."""
        manager = fresh_notification_manager
        
        # Should not error
        manager._load_preferences()
    
    def test_load_preferences_invalid_data(self, fresh_notification_manager):
        """Test loading preferences with invalid data."""
        manager = fresh_notification_manager
        
        # Create file with invalid data
        from app.services.notification_manager import DATA_DIR, PREFERENCES_FILE
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(PREFERENCES_FILE, 'w') as f:
            json.dump({"bad_key": {"invalid": "data"}}, f)
        
        manager._load_preferences()
        # Should handle gracefully
    
    def test_load_history_migration_user_id(self, fresh_notification_manager):
        """Test loading history migrates user_id to network_id."""
        manager = fresh_notification_manager
        
        from app.services.notification_manager import DATA_DIR, HISTORY_FILE
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create file with old format
        old_record = {
            "notification_id": "test-id",
            "event_id": "event-id",
            "user_id": "old-user",  # Old format
            "channel": "email",
            "timestamp": datetime.utcnow().isoformat(),
            "success": True,
            "title": "Test",
            "message": "Test",
            "priority": "high",
        }
        
        with open(HISTORY_FILE, 'w') as f:
            json.dump([old_record], f)
        
        manager._load_history()
        
        # Should migrate
        assert len(manager._history) == 1
        assert manager._history[0].network_id is None


class TestLoadScheduledBroadcasts:
    """Tests for loading scheduled broadcasts."""
    
    def test_load_scheduled_broadcasts_missing_network_id(self, fresh_notification_manager):
        """Test loading broadcasts without network_id skips them."""
        manager = fresh_notification_manager
        
        from app.services.notification_manager import DATA_DIR, SCHEDULED_FILE
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create file with old format (no network_id)
        old_broadcast = {
            "id": "test-id",
            "title": "Old Broadcast",
            "message": "Old message",
            "scheduled_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "created_by": "testuser",
            "status": "pending",
            "event_type": "scheduled_maintenance",
            "priority": "medium",
        }
        
        with open(SCHEDULED_FILE, 'w') as f:
            json.dump({"test-id": old_broadcast}, f)
        
        manager._scheduled_broadcasts.clear()
        manager._load_scheduled_broadcasts()
        
        # Should skip broadcast without network_id
        assert "test-id" not in manager._scheduled_broadcasts


class TestShouldNotifyPriorityLogic:
    """Tests for notification priority filtering logic."""
    
    def test_should_notify_priority_below_minimum(self, fresh_notification_manager):
        """Test filtering when priority below minimum."""
        manager = fresh_notification_manager
        
        prefs = NotificationPreferences(
            network_id="test-network",
            enabled=True,
            email=EmailConfig(enabled=True, email_address="test@example.com"),
            minimum_priority=NotificationPriority.HIGH,
            enabled_notification_types=[NotificationType.DEVICE_OFFLINE],
            # Override DEVICE_OFFLINE to LOW priority so it's below minimum
            notification_type_priorities={NotificationType.DEVICE_OFFLINE: NotificationPriority.LOW},
        )
        
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            priority=NotificationPriority.LOW,
            title="Test",
            message="Test",
        )
        
        should_notify, reason = manager._should_notify(prefs, event)
        
        assert should_notify is False
        assert "below minimum" in reason.lower()
    
    def test_should_notify_in_quiet_hours_below_bypass(self, fresh_notification_manager):
        """Test filtering during quiet hours when below bypass priority."""
        manager = fresh_notification_manager
        
        # Mock time to be in quiet hours
        with patch.object(manager, '_is_quiet_hours', return_value=True):
            prefs = NotificationPreferences(
                network_id="test-network",
                enabled=True,
                email=EmailConfig(enabled=True, email_address="test@example.com"),
                quiet_hours_enabled=True,
                quiet_hours_start="22:00",
                quiet_hours_end="07:00",
                quiet_hours_bypass_priority=NotificationPriority.CRITICAL,
                enabled_notification_types=[NotificationType.DEVICE_OFFLINE],
            )
            
            event = NetworkEvent(
                event_type=NotificationType.DEVICE_OFFLINE,
                priority=NotificationPriority.HIGH,  # Below CRITICAL
                title="Test",
                message="Test",
            )
            
            should_notify, reason = manager._should_notify(prefs, event)
        
        assert should_notify is False
        assert "quiet hours" in reason
    
    def test_should_notify_in_quiet_hours_above_bypass(self, fresh_notification_manager):
        """Test allowing during quiet hours when above bypass priority."""
        manager = fresh_notification_manager
        
        with patch.object(manager, '_is_quiet_hours', return_value=True):
            prefs = NotificationPreferences(
                network_id="test-network",
                enabled=True,
                email=EmailConfig(enabled=True, email_address="test@example.com"),
                quiet_hours_enabled=True,
                quiet_hours_start="22:00",
                quiet_hours_end="07:00",
                quiet_hours_bypass_priority=NotificationPriority.HIGH,
                enabled_notification_types=[NotificationType.DEVICE_OFFLINE],
            )
            
            event = NetworkEvent(
                event_type=NotificationType.DEVICE_OFFLINE,
                priority=NotificationPriority.CRITICAL,  # Above HIGH
                title="Test",
                message="Test",
            )
            
            should_notify, reason = manager._should_notify(prefs, event)
        
        assert should_notify is True
    
    def test_should_notify_in_quiet_hours_no_bypass(self, fresh_notification_manager):
        """Test filtering during quiet hours with no bypass set."""
        manager = fresh_notification_manager
        
        with patch.object(manager, '_is_quiet_hours', return_value=True):
            prefs = NotificationPreferences(
                network_id="test-network",
                enabled=True,
                email=EmailConfig(enabled=True, email_address="test@example.com"),
                quiet_hours_enabled=True,
                quiet_hours_start="22:00",
                quiet_hours_end="07:00",
                quiet_hours_bypass_priority=None,
                enabled_notification_types=[NotificationType.DEVICE_OFFLINE],
            )
            
            event = NetworkEvent(
                event_type=NotificationType.DEVICE_OFFLINE,
                priority=NotificationPriority.CRITICAL,
                title="Test",
                message="Test",
            )
            
            should_notify, reason = manager._should_notify(prefs, event)
        
        assert should_notify is False
        assert "quiet hours" in reason


class TestGetNetworkMemberUserIds:
    """Tests for _get_network_member_user_ids with mocked database."""
    
    @pytest.mark.asyncio
    async def test_get_network_members_success(self, fresh_notification_manager):
        """Test getting network members successfully."""
        manager = fresh_notification_manager
        
        mock_session = AsyncMock()
        mock_result1 = MagicMock()
        mock_result1.fetchone.return_value = ("owner-user",)
        mock_result2 = MagicMock()
        mock_result2.fetchall.return_value = [("user1",), ("user2",)]
        
        mock_session.execute = AsyncMock(side_effect=[mock_result1, mock_result2])
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.database.async_session_maker', mock_session_maker):
            user_ids = await manager._get_network_member_user_ids("test-network-id")
        
        assert "owner-user" in user_ids
        assert "user1" in user_ids
        assert "user2" in user_ids
    
    @pytest.mark.asyncio
    async def test_get_network_members_not_found(self, fresh_notification_manager):
        """Test getting members for non-existent network."""
        manager = fresh_notification_manager
        
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.database.async_session_maker', mock_session_maker):
            user_ids = await manager._get_network_member_user_ids("nonexistent-network")
        
        assert user_ids == []
    
    @pytest.mark.asyncio
    async def test_get_network_members_database_error(self, fresh_notification_manager):
        """Test handling database error."""
        manager = fresh_notification_manager
        
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception("Database error"))
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.database.async_session_maker', mock_session_maker):
            user_ids = await manager._get_network_member_user_ids("test-network-id")
        
        assert user_ids == []



