"""
Unit tests for NotificationManager service.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from app.models import (
    NotificationPreferences,
    NotificationPreferencesUpdate,
    NetworkEvent,
    NotificationType,
    NotificationPriority,
    NotificationChannel,
    NotificationRecord,
    TestNotificationRequest,
    EmailConfig,
    DiscordConfig,
    ScheduledBroadcastStatus,
)


class TestPreferencesManagement:
    """Tests for preferences management"""
    
    def test_get_preferences_new_user(self, notification_manager_instance):
        """Should create default preferences for new user"""
        prefs = notification_manager_instance.get_preferences("new-user")
        
        assert prefs.user_id == "new-user"
        assert prefs.enabled is True
        assert prefs.email.enabled is False
    
    def test_get_preferences_existing_user(self, notification_manager_instance):
        """Should return existing preferences"""
        # Set up preferences
        notification_manager_instance._preferences["existing-user"] = NotificationPreferences(
            user_id="existing-user",
            enabled=False
        )
        
        prefs = notification_manager_instance.get_preferences("existing-user")
        assert prefs.enabled is False
    
    def test_update_preferences(self, notification_manager_instance):
        """Should update preferences"""
        notification_manager_instance.get_preferences("test-user")
        
        update = NotificationPreferencesUpdate(
            enabled=False,
            minimum_priority=NotificationPriority.HIGH
        )
        
        with patch.object(notification_manager_instance, '_save_preferences'):
            result = notification_manager_instance.update_preferences("test-user", update)
        
        assert result.enabled is False
        assert result.minimum_priority == NotificationPriority.HIGH
    
    def test_update_preferences_email(self, notification_manager_instance):
        """Should update email config"""
        notification_manager_instance.get_preferences("test-user")
        
        update = NotificationPreferencesUpdate(
            email=EmailConfig(enabled=True, email_address="new@example.com")
        )
        
        with patch.object(notification_manager_instance, '_save_preferences'):
            result = notification_manager_instance.update_preferences("test-user", update)
        
        assert result.email.enabled is True
        assert result.email.email_address == "new@example.com"
    
    def test_delete_preferences(self, notification_manager_instance):
        """Should delete preferences"""
        notification_manager_instance._preferences["test-user"] = NotificationPreferences(
            user_id="test-user"
        )
        
        with patch.object(notification_manager_instance, '_save_preferences'):
            result = notification_manager_instance.delete_preferences("test-user")
        
        assert result is True
        assert "test-user" not in notification_manager_instance._preferences
    
    def test_delete_preferences_not_found(self, notification_manager_instance):
        """Should return False for non-existent user"""
        result = notification_manager_instance.delete_preferences("non-existent")
        assert result is False
    
    def test_get_all_users_with_notifications(self, notification_manager_instance):
        """Should return users with notifications enabled"""
        notification_manager_instance._preferences["user1"] = NotificationPreferences(
            user_id="user1",
            enabled=True,
            email=EmailConfig(enabled=True, email_address="test@test.com")
        )
        notification_manager_instance._preferences["user2"] = NotificationPreferences(
            user_id="user2",
            enabled=False
        )
        
        users = notification_manager_instance.get_all_users_with_notifications_enabled()
        
        assert "user1" in users
        assert "user2" not in users


class TestSilencedDevices:
    """Tests for silenced device management"""
    
    def test_silence_device(self, notification_manager_instance):
        """Should silence device"""
        with patch.object(notification_manager_instance, '_save_silenced_devices'):
            result = notification_manager_instance.silence_device("192.168.1.100")
        
        assert result is True
        assert notification_manager_instance.is_device_silenced("192.168.1.100")
    
    def test_silence_device_already_silenced(self, notification_manager_instance):
        """Should return False if already silenced"""
        notification_manager_instance._silenced_devices.add("192.168.1.100")
        
        result = notification_manager_instance.silence_device("192.168.1.100")
        
        assert result is False
    
    def test_unsilence_device(self, notification_manager_instance):
        """Should unsilence device"""
        notification_manager_instance._silenced_devices.add("192.168.1.100")
        
        with patch.object(notification_manager_instance, '_save_silenced_devices'):
            result = notification_manager_instance.unsilence_device("192.168.1.100")
        
        assert result is True
        assert not notification_manager_instance.is_device_silenced("192.168.1.100")
    
    def test_unsilence_device_not_silenced(self, notification_manager_instance):
        """Should return False if not silenced"""
        result = notification_manager_instance.unsilence_device("192.168.1.100")
        assert result is False
    
    def test_set_silenced_devices(self, notification_manager_instance):
        """Should set full list of silenced devices"""
        with patch.object(notification_manager_instance, '_save_silenced_devices'):
            notification_manager_instance.set_silenced_devices(["192.168.1.1", "192.168.1.2"])
        
        assert len(notification_manager_instance.get_silenced_devices()) == 2
    
    def test_get_silenced_devices(self, notification_manager_instance):
        """Should return list of silenced devices"""
        notification_manager_instance._silenced_devices = {"192.168.1.1", "192.168.1.2"}
        
        devices = notification_manager_instance.get_silenced_devices()
        
        assert len(devices) == 2


class TestRateLimiting:
    """Tests for rate limiting"""
    
    def test_check_rate_limit_allowed(self, notification_manager_instance):
        """Should allow when under rate limit"""
        prefs = NotificationPreferences(user_id="test", max_notifications_per_hour=10)
        
        result = notification_manager_instance._check_rate_limit("test", prefs)
        
        assert result is True
    
    def test_check_rate_limit_exceeded(self, notification_manager_instance):
        """Should block when over rate limit"""
        prefs = NotificationPreferences(user_id="test", max_notifications_per_hour=2)
        
        # Fill up rate limit
        from collections import deque
        notification_manager_instance._rate_limits["test"] = deque(
            [datetime.utcnow() for _ in range(3)],
            maxlen=10
        )
        
        result = notification_manager_instance._check_rate_limit("test", prefs)
        
        assert result is False
    
    def test_record_rate_limit(self, notification_manager_instance):
        """Should record notification for rate limiting"""
        notification_manager_instance._record_rate_limit("test")
        
        assert "test" in notification_manager_instance._rate_limits
        assert len(notification_manager_instance._rate_limits["test"]) == 1


class TestQuietHours:
    """Tests for quiet hours"""
    
    def test_is_quiet_hours_disabled(self, notification_manager_instance):
        """Should return False when quiet hours disabled"""
        prefs = NotificationPreferences(user_id="test", quiet_hours_enabled=False)
        
        result = notification_manager_instance._is_quiet_hours(prefs)
        
        assert result is False
    
    def test_is_quiet_hours_no_times(self, notification_manager_instance):
        """Should return False when no times set"""
        prefs = NotificationPreferences(
            user_id="test",
            quiet_hours_enabled=True,
            quiet_hours_start=None,
            quiet_hours_end=None
        )
        
        result = notification_manager_instance._is_quiet_hours(prefs)
        
        assert result is False
    
    def test_is_quiet_hours_within(self, notification_manager_instance):
        """Should detect when in quiet hours"""
        now = datetime.utcnow()
        current_hour = now.strftime("%H:%M")
        
        # Set quiet hours to include current time
        start_hour = (now - timedelta(hours=1)).strftime("%H:%M")
        end_hour = (now + timedelta(hours=1)).strftime("%H:%M")
        
        prefs = NotificationPreferences(
            user_id="test",
            quiet_hours_enabled=True,
            quiet_hours_start=start_hour,
            quiet_hours_end=end_hour
        )
        
        result = notification_manager_instance._is_quiet_hours(prefs)
        
        assert result is True


class TestShouldNotify:
    """Tests for notification filtering"""
    
    def test_should_notify_master_disabled(self, notification_manager_instance):
        """Should not notify when master switch disabled"""
        prefs = NotificationPreferences(user_id="test", enabled=False)
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            title="Test",
            message="Test"
        )
        
        should, reason = notification_manager_instance._should_notify(prefs, event)
        
        assert should is False
        assert "disabled" in reason.lower()
    
    def test_should_notify_no_channels(self, notification_manager_instance):
        """Should not notify when no channels enabled"""
        prefs = NotificationPreferences(
            user_id="test",
            enabled=True,
            email=EmailConfig(enabled=False),
            discord=DiscordConfig(enabled=False)
        )
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            title="Test",
            message="Test"
        )
        
        should, reason = notification_manager_instance._should_notify(prefs, event)
        
        assert should is False
        assert "channels" in reason.lower()
    
    def test_should_notify_event_type_filtered(self, notification_manager_instance):
        """Should not notify when event type not enabled"""
        prefs = NotificationPreferences(
            user_id="test",
            enabled=True,
            email=EmailConfig(enabled=True, email_address="test@test.com"),
            enabled_notification_types=[NotificationType.DEVICE_ONLINE]  # Not DEVICE_OFFLINE
        )
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            title="Test",
            message="Test"
        )
        
        should, reason = notification_manager_instance._should_notify(prefs, event)
        
        assert should is False
    
    def test_should_notify_priority_below_minimum(self, notification_manager_instance):
        """Should not notify when priority below minimum"""
        prefs = NotificationPreferences(
            user_id="test",
            enabled=True,
            email=EmailConfig(enabled=True, email_address="test@test.com"),
            minimum_priority=NotificationPriority.CRITICAL,
            notification_type_priorities={
                NotificationType.DEVICE_OFFLINE: NotificationPriority.LOW
            }
        )
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            title="Test",
            message="Test"
        )
        
        should, reason = notification_manager_instance._should_notify(prefs, event)
        
        assert should is False


class TestSendNotification:
    """Tests for sending notifications"""
    
    async def test_send_notification_email(self, notification_manager_instance, sample_network_event):
        """Should send email notification"""
        notification_manager_instance._preferences["test-user"] = NotificationPreferences(
            user_id="test-user",
            enabled=True,
            email=EmailConfig(enabled=True, email_address="test@test.com"),
        )
        
        mock_record = NotificationRecord(
            notification_id="test",
            event_id="test",
            user_id="test-user",
            channel=NotificationChannel.EMAIL,
            success=True,
            title="Test",
            message="Test",
            priority=NotificationPriority.HIGH
        )
        
        with patch('app.services.notification_manager.send_notification_email', AsyncMock(return_value=mock_record)):
            with patch.object(notification_manager_instance, '_save_history'):
                records = await notification_manager_instance.send_notification(
                    "test-user",
                    sample_network_event,
                    force=True
                )
        
        assert len(records) > 0
    
    async def test_broadcast_notification(self, notification_manager_instance, sample_network_event):
        """Should broadcast to all users"""
        notification_manager_instance._preferences["user1"] = NotificationPreferences(
            user_id="user1",
            enabled=True,
            email=EmailConfig(enabled=True, email_address="user1@test.com"),
        )
        notification_manager_instance._preferences["user2"] = NotificationPreferences(
            user_id="user2",
            enabled=True,
            email=EmailConfig(enabled=True, email_address="user2@test.com"),
        )
        
        mock_record = NotificationRecord(
            notification_id="test",
            event_id="test",
            user_id="",
            channel=NotificationChannel.EMAIL,
            success=True,
            title="Test",
            message="Test",
            priority=NotificationPriority.HIGH
        )
        
        with patch('app.services.notification_manager.send_notification_email', AsyncMock(return_value=mock_record)):
            with patch.object(notification_manager_instance, '_save_history'):
                results = await notification_manager_instance.broadcast_notification(sample_network_event)
        
        assert len(results) == 2


class TestTestNotification:
    """Tests for test notifications"""
    
    async def test_send_test_email_no_address(self, notification_manager_instance):
        """Should fail when no email address configured"""
        notification_manager_instance._preferences["test-user"] = NotificationPreferences(
            user_id="test-user",
            email=EmailConfig(enabled=True, email_address="")
        )
        
        request = TestNotificationRequest(channel=NotificationChannel.EMAIL)
        
        result = await notification_manager_instance.send_test_notification("test-user", request)
        
        assert result.success is False
    
    async def test_send_test_discord_not_enabled(self, notification_manager_instance):
        """Should fail when Discord not enabled"""
        notification_manager_instance._preferences["test-user"] = NotificationPreferences(
            user_id="test-user",
            discord=DiscordConfig(enabled=False)
        )
        
        request = TestNotificationRequest(channel=NotificationChannel.DISCORD)
        
        result = await notification_manager_instance.send_test_notification("test-user", request)
        
        assert result.success is False


class TestHistoryAndStats:
    """Tests for history and statistics"""
    
    def test_get_history(self, notification_manager_instance):
        """Should return history"""
        notification_manager_instance._history.append(
            NotificationRecord(
                notification_id="1",
                event_id="1",
                user_id="test-user",
                channel=NotificationChannel.EMAIL,
                success=True,
                title="Test",
                message="Test",
                priority=NotificationPriority.HIGH
            )
        )
        
        result = notification_manager_instance.get_history(user_id="test-user")
        
        assert result.total_count == 1
    
    def test_get_stats(self, notification_manager_instance):
        """Should return stats"""
        notification_manager_instance._history.append(
            NotificationRecord(
                notification_id="1",
                event_id="1",
                user_id="test-user",
                channel=NotificationChannel.EMAIL,
                success=True,
                title="Test",
                message="Test",
                priority=NotificationPriority.HIGH,
                timestamp=datetime.utcnow()
            )
        )
        
        stats = notification_manager_instance.get_stats(user_id="test-user")
        
        assert stats.total_sent_24h == 1


class TestScheduledBroadcasts:
    """Tests for scheduled broadcasts"""
    
    def test_create_scheduled_broadcast(self, notification_manager_instance):
        """Should create scheduled broadcast"""
        scheduled_at = datetime.utcnow() + timedelta(hours=1)
        
        with patch.object(notification_manager_instance, '_save_scheduled_broadcasts'):
            broadcast = notification_manager_instance.create_scheduled_broadcast(
                title="Test Broadcast",
                message="Test message",
                scheduled_at=scheduled_at,
                created_by="admin"
            )
        
        assert broadcast.title == "Test Broadcast"
        assert broadcast.status == ScheduledBroadcastStatus.PENDING
    
    def test_get_scheduled_broadcasts(self, notification_manager_instance):
        """Should return scheduled broadcasts"""
        from app.models import ScheduledBroadcast
        
        notification_manager_instance._scheduled_broadcasts["test-id"] = ScheduledBroadcast(
            id="test-id",
            title="Test",
            message="Test",
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
            created_by="admin"
        )
        
        response = notification_manager_instance.get_scheduled_broadcasts()
        
        assert response.total_count == 1
    
    def test_cancel_scheduled_broadcast(self, notification_manager_instance):
        """Should cancel scheduled broadcast"""
        from app.models import ScheduledBroadcast
        
        notification_manager_instance._scheduled_broadcasts["test-id"] = ScheduledBroadcast(
            id="test-id",
            title="Test",
            message="Test",
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
            created_by="admin"
        )
        
        with patch.object(notification_manager_instance, '_save_scheduled_broadcasts'):
            result = notification_manager_instance.cancel_scheduled_broadcast("test-id")
        
        assert result is True
        assert notification_manager_instance._scheduled_broadcasts["test-id"].status == ScheduledBroadcastStatus.CANCELLED
    
    def test_delete_scheduled_broadcast(self, notification_manager_instance):
        """Should delete cancelled broadcast"""
        from app.models import ScheduledBroadcast
        
        notification_manager_instance._scheduled_broadcasts["test-id"] = ScheduledBroadcast(
            id="test-id",
            title="Test",
            message="Test",
            scheduled_at=datetime.utcnow(),
            created_by="admin",
            status=ScheduledBroadcastStatus.CANCELLED
        )
        
        with patch.object(notification_manager_instance, '_save_scheduled_broadcasts'):
            result = notification_manager_instance.delete_scheduled_broadcast("test-id")
        
        assert result is True
        assert "test-id" not in notification_manager_instance._scheduled_broadcasts

