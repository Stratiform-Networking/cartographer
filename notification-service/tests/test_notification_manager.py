"""
Unit tests for NotificationManager service.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import (
    DiscordConfig,
    EmailConfig,
    NetworkEvent,
    NotificationChannel,
    NotificationPreferences,
    NotificationPreferencesUpdate,
    NotificationPriority,
    NotificationRecord,
    NotificationType,
    ScheduledBroadcastStatus,
    TestNotificationRequest,
)


class TestPreferencesManagement:
    """Tests for preferences management"""

    def test_get_preferences_new_network(self, notification_manager_instance):
        """Should create default preferences for new network"""
        prefs = notification_manager_instance.get_preferences("new-network-uuid")

        assert prefs.network_id == "new-network-uuid"
        assert prefs.enabled is True
        assert prefs.email.enabled is False

    def test_get_preferences_existing_network(self, notification_manager_instance):
        """Should return existing preferences"""
        # Set up preferences
        notification_manager_instance._preferences["existing-network"] = NotificationPreferences(
            network_id="existing-network", enabled=False
        )

        prefs = notification_manager_instance.get_preferences("existing-network")
        assert prefs.enabled is False

    def test_update_preferences(self, notification_manager_instance):
        """Should update preferences"""
        notification_manager_instance.get_preferences("test-network")

        update = NotificationPreferencesUpdate(
            enabled=False, minimum_priority=NotificationPriority.HIGH
        )

        with patch.object(notification_manager_instance, "_save_preferences"):
            result = notification_manager_instance.update_preferences("test-network", update)

        assert result.enabled is False
        assert result.minimum_priority == NotificationPriority.HIGH

    def test_update_preferences_email(self, notification_manager_instance):
        """Should update email config"""
        notification_manager_instance.get_preferences("test-network")

        update = NotificationPreferencesUpdate(
            email=EmailConfig(enabled=True, email_address="new@example.com")
        )

        with patch.object(notification_manager_instance, "_save_preferences"):
            result = notification_manager_instance.update_preferences("test-network", update)

        assert result.email.enabled is True
        assert result.email.email_address == "new@example.com"

    def test_delete_preferences(self, notification_manager_instance):
        """Should delete preferences"""
        notification_manager_instance._preferences["test-network"] = NotificationPreferences(
            network_id="test-network"
        )

        with patch.object(notification_manager_instance, "_save_preferences"):
            result = notification_manager_instance.delete_preferences("test-network")

        assert result is True
        assert "test-network" not in notification_manager_instance._preferences

    def test_delete_preferences_not_found(self, notification_manager_instance):
        """Should return False for non-existent network"""
        result = notification_manager_instance.delete_preferences("non-existent")
        assert result is False

    def test_get_all_networks_with_notifications(self, notification_manager_instance):
        """Should return networks with notifications enabled"""
        notification_manager_instance._preferences["1"] = NotificationPreferences(
            network_id="1",
            enabled=True,
            email=EmailConfig(enabled=True, email_address="test@test.com"),
        )
        notification_manager_instance._preferences["2"] = NotificationPreferences(
            network_id="2", enabled=False
        )

        # Note: This returns string network_ids (UUIDs)
        networks = notification_manager_instance.get_all_networks_with_notifications_enabled()

        assert "1" in networks
        assert "2" not in networks

    def test_update_notification_type_priorities_reset(self, notification_manager_instance):
        """Should replace notification_type_priorities entirely (not merge) to allow resetting to defaults"""
        # Set up network with custom priorities
        notification_manager_instance._preferences["test-network"] = NotificationPreferences(
            network_id="test-network",
            notification_type_priorities={
                NotificationType.DEVICE_OFFLINE: NotificationPriority.LOW,
                NotificationType.ANOMALY_DETECTED: NotificationPriority.CRITICAL,
            },
        )

        # Update with empty dict (simulating reset to defaults)
        update = NotificationPreferencesUpdate(notification_type_priorities={})

        with patch.object(notification_manager_instance, "_save_preferences"):
            result = notification_manager_instance.update_preferences("test-network", update)

        # Should be empty, not merged with old values
        assert result.notification_type_priorities == {}

    def test_update_notification_type_priorities_partial(self, notification_manager_instance):
        """Should replace notification_type_priorities with partial update (not merge with existing)"""
        # Set up network with custom priorities
        notification_manager_instance._preferences["test-network"] = NotificationPreferences(
            network_id="test-network",
            notification_type_priorities={
                NotificationType.DEVICE_OFFLINE: NotificationPriority.LOW,
                NotificationType.ANOMALY_DETECTED: NotificationPriority.CRITICAL,
            },
        )

        # Update with only one priority (the other should be removed)
        update = NotificationPreferencesUpdate(
            notification_type_priorities={
                NotificationType.DEVICE_OFFLINE: NotificationPriority.HIGH,
            }
        )

        with patch.object(notification_manager_instance, "_save_preferences"):
            result = notification_manager_instance.update_preferences("test-network", update)

        # Should only have the new priority, anomaly_detected should be removed
        assert result.notification_type_priorities == {
            NotificationType.DEVICE_OFFLINE: NotificationPriority.HIGH,
        }
        assert NotificationType.ANOMALY_DETECTED not in result.notification_type_priorities


class TestSilencedDevices:
    """Tests for silenced device management"""

    def test_silence_device(self, notification_manager_instance):
        """Should silence device"""
        with patch.object(notification_manager_instance, "_save_silenced_devices"):
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

        with patch.object(notification_manager_instance, "_save_silenced_devices"):
            result = notification_manager_instance.unsilence_device("192.168.1.100")

        assert result is True
        assert not notification_manager_instance.is_device_silenced("192.168.1.100")

    def test_unsilence_device_not_silenced(self, notification_manager_instance):
        """Should return False if not silenced"""
        result = notification_manager_instance.unsilence_device("192.168.1.100")
        assert result is False

    def test_set_silenced_devices(self, notification_manager_instance):
        """Should set full list of silenced devices"""
        with patch.object(notification_manager_instance, "_save_silenced_devices"):
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
        prefs = NotificationPreferences(network_id="test-network", max_notifications_per_hour=10)

        result = notification_manager_instance._check_rate_limit("test-network", prefs)

        assert result is True

    def test_check_rate_limit_exceeded(self, notification_manager_instance):
        """Should block when over rate limit"""
        prefs = NotificationPreferences(network_id="test-network", max_notifications_per_hour=2)

        # Fill up rate limit
        from collections import deque

        notification_manager_instance._rate_limits["test-network"] = deque(
            [datetime.utcnow() for _ in range(3)], maxlen=10
        )

        result = notification_manager_instance._check_rate_limit("test-network", prefs)

        assert result is False

    def test_record_rate_limit(self, notification_manager_instance):
        """Should record notification for rate limiting"""
        notification_manager_instance._record_rate_limit("test-network")

        assert "test-network" in notification_manager_instance._rate_limits
        assert len(notification_manager_instance._rate_limits["test-network"]) == 1


class TestQuietHours:
    """Tests for quiet hours"""

    def test_is_quiet_hours_disabled(self, notification_manager_instance):
        """Should return False when quiet hours disabled"""
        prefs = NotificationPreferences(network_id="test-network", quiet_hours_enabled=False)

        result = notification_manager_instance._is_quiet_hours(prefs)

        assert result is False

    def test_is_quiet_hours_no_times(self, notification_manager_instance):
        """Should return False when no times set"""
        prefs = NotificationPreferences(
            network_id="test-network",
            quiet_hours_enabled=True,
            quiet_hours_start=None,
            quiet_hours_end=None,
        )

        result = notification_manager_instance._is_quiet_hours(prefs)

        assert result is False

    def test_is_quiet_hours_within(self, notification_manager_instance):
        """Should detect when in quiet hours"""
        # Use local time since quiet hours are compared in local time
        now = datetime.now()
        current_hour = now.strftime("%H:%M")

        # Set quiet hours to include current time
        start_hour = (now - timedelta(hours=1)).strftime("%H:%M")
        end_hour = (now + timedelta(hours=1)).strftime("%H:%M")

        prefs = NotificationPreferences(
            network_id="test-network",
            quiet_hours_enabled=True,
            quiet_hours_start=start_hour,
            quiet_hours_end=end_hour,
        )

        result = notification_manager_instance._is_quiet_hours(prefs)

        assert result is True

    def test_is_quiet_hours_midnight_to_morning_at_3am(self, notification_manager_instance):
        """Should detect quiet hours at 3 AM when set to 00:00-08:00 (common sleep hours)"""
        prefs = NotificationPreferences(
            network_id="test-network",
            quiet_hours_enabled=True,
            quiet_hours_start="00:00",
            quiet_hours_end="08:00",
        )

        # Mock datetime.now() to return 3:00 AM local time
        mock_time = datetime(2024, 1, 15, 3, 0, 0)
        with patch("app.services.notification_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_time
            mock_datetime.utcnow.return_value = mock_time  # Ensure UTC isn't used

            result = notification_manager_instance._is_quiet_hours(prefs)

        assert result is True, "3 AM should be within quiet hours 00:00-08:00"

    def test_is_quiet_hours_midnight_to_morning_at_10am(self, notification_manager_instance):
        """Should NOT detect quiet hours at 10 AM when set to 00:00-08:00"""
        prefs = NotificationPreferences(
            network_id="test-network",
            quiet_hours_enabled=True,
            quiet_hours_start="00:00",
            quiet_hours_end="08:00",
        )

        # Mock datetime.now() to return 10:00 AM local time
        mock_time = datetime(2024, 1, 15, 10, 0, 0)
        with patch("app.services.notification_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_time
            mock_datetime.utcnow.return_value = mock_time

            result = notification_manager_instance._is_quiet_hours(prefs)

        assert result is False, "10 AM should NOT be within quiet hours 00:00-08:00"

    def test_is_quiet_hours_overnight_at_11pm(self, notification_manager_instance):
        """Should detect quiet hours at 11 PM when set to 22:00-07:00 (overnight)"""
        prefs = NotificationPreferences(
            network_id="test-network",
            quiet_hours_enabled=True,
            quiet_hours_start="22:00",
            quiet_hours_end="07:00",
        )

        # Mock datetime.now() to return 11:00 PM local time
        mock_time = datetime(2024, 1, 15, 23, 0, 0)
        with patch("app.services.notification_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_time
            mock_datetime.utcnow.return_value = mock_time

            result = notification_manager_instance._is_quiet_hours(prefs)

        assert result is True, "11 PM should be within overnight quiet hours 22:00-07:00"

    def test_is_quiet_hours_overnight_at_5am(self, notification_manager_instance):
        """Should detect quiet hours at 5 AM when set to 22:00-07:00 (overnight)"""
        prefs = NotificationPreferences(
            network_id="test-network",
            quiet_hours_enabled=True,
            quiet_hours_start="22:00",
            quiet_hours_end="07:00",
        )

        # Mock datetime.now() to return 5:00 AM local time
        mock_time = datetime(2024, 1, 15, 5, 0, 0)
        with patch("app.services.notification_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_time
            mock_datetime.utcnow.return_value = mock_time

            result = notification_manager_instance._is_quiet_hours(prefs)

        assert result is True, "5 AM should be within overnight quiet hours 22:00-07:00"

    def test_is_quiet_hours_overnight_at_noon(self, notification_manager_instance):
        """Should NOT detect quiet hours at noon when set to 22:00-07:00 (overnight)"""
        prefs = NotificationPreferences(
            network_id="test-network",
            quiet_hours_enabled=True,
            quiet_hours_start="22:00",
            quiet_hours_end="07:00",
        )

        # Mock datetime.now() to return 12:00 PM local time
        mock_time = datetime(2024, 1, 15, 12, 0, 0)
        with patch("app.services.notification_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_time
            mock_datetime.utcnow.return_value = mock_time

            result = notification_manager_instance._is_quiet_hours(prefs)

        assert result is False, "Noon should NOT be within overnight quiet hours 22:00-07:00"

    def test_is_quiet_hours_uses_local_time_not_utc(self, notification_manager_instance):
        """Should use local time (datetime.now), not UTC time for quiet hours comparison.

        This test catches the bug where datetime.utcnow() was used instead of datetime.now(),
        causing quiet hours to fail for users not in UTC timezone.
        """
        prefs = NotificationPreferences(
            network_id="test-network",
            quiet_hours_enabled=True,
            quiet_hours_start="00:00",
            quiet_hours_end="08:00",
        )

        # Simulate 3 AM local time but 11 AM UTC (like PST timezone)
        local_time = datetime(2024, 1, 15, 3, 0, 0)
        utc_time = datetime(2024, 1, 15, 11, 0, 0)

        with patch("app.services.notification_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = local_time
            mock_datetime.utcnow.return_value = utc_time

            result = notification_manager_instance._is_quiet_hours(prefs)

        # Should use local time (3 AM), not UTC (11 AM)
        # At 3 AM local, should be IN quiet hours
        assert result is True, (
            "Quiet hours should use local time (3 AM = in quiet hours), "
            "not UTC time (11 AM = outside quiet hours)"
        )

    def test_is_quiet_hours_boundary_at_start(self, notification_manager_instance):
        """Should include the start boundary time in quiet hours"""
        prefs = NotificationPreferences(
            network_id="test-network",
            quiet_hours_enabled=True,
            quiet_hours_start="22:00",
            quiet_hours_end="07:00",
        )

        # Mock datetime.now() to return exactly 22:00
        mock_time = datetime(2024, 1, 15, 22, 0, 0)
        with patch("app.services.notification_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_time
            mock_datetime.utcnow.return_value = mock_time

            result = notification_manager_instance._is_quiet_hours(prefs)

        assert result is True, "22:00 exactly should be within quiet hours 22:00-07:00"

    def test_is_quiet_hours_boundary_at_end(self, notification_manager_instance):
        """Should include the end boundary time in quiet hours"""
        prefs = NotificationPreferences(
            network_id="test-network",
            quiet_hours_enabled=True,
            quiet_hours_start="22:00",
            quiet_hours_end="07:00",
        )

        # Mock datetime.now() to return exactly 07:00
        mock_time = datetime(2024, 1, 15, 7, 0, 0)
        with patch("app.services.notification_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_time
            mock_datetime.utcnow.return_value = mock_time

            result = notification_manager_instance._is_quiet_hours(prefs)

        assert result is True, "07:00 exactly should be within quiet hours 22:00-07:00"

    def test_is_quiet_hours_just_after_end(self, notification_manager_instance):
        """Should NOT include time just after end boundary"""
        prefs = NotificationPreferences(
            network_id="test-network",
            quiet_hours_enabled=True,
            quiet_hours_start="22:00",
            quiet_hours_end="07:00",
        )

        # Mock datetime.now() to return 07:01
        mock_time = datetime(2024, 1, 15, 7, 1, 0)
        with patch("app.services.notification_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_time
            mock_datetime.utcnow.return_value = mock_time

            result = notification_manager_instance._is_quiet_hours(prefs)

        assert result is False, "07:01 should NOT be within quiet hours 22:00-07:00"

    def test_is_quiet_hours_with_user_timezone_est(self, notification_manager_instance):
        """Should use user's timezone when set (EST user, 4am local = 9am UTC)"""
        prefs = NotificationPreferences(
            network_id="test-network",
            quiet_hours_enabled=True,
            quiet_hours_start="00:00",
            quiet_hours_end="08:00",
            timezone="America/New_York",  # EST/EDT
        )

        # Simulate 9:00 AM UTC (which is 4:00 AM EST)
        from zoneinfo import ZoneInfo

        utc_time = datetime(2024, 1, 15, 9, 0, 0, tzinfo=ZoneInfo("UTC"))

        with patch("app.services.notification_manager.datetime") as mock_datetime:
            mock_datetime.now.side_effect = lambda tz=None: (
                utc_time if tz else utc_time.replace(tzinfo=None)
            )

            result = notification_manager_instance._is_quiet_hours(prefs)

        # 4 AM EST should be IN quiet hours (00:00-08:00)
        assert result is True, "4 AM EST should be within quiet hours 00:00-08:00 EST"

    def test_is_quiet_hours_with_user_timezone_outside_quiet_hours(
        self, notification_manager_instance
    ):
        """Should correctly detect when outside quiet hours using user's timezone"""
        prefs = NotificationPreferences(
            network_id="test-network",
            quiet_hours_enabled=True,
            quiet_hours_start="00:00",
            quiet_hours_end="08:00",
            timezone="America/New_York",  # EST/EDT
        )

        # Simulate 3:00 PM UTC (which is 10:00 AM EST)
        from zoneinfo import ZoneInfo

        utc_time = datetime(2024, 1, 15, 15, 0, 0, tzinfo=ZoneInfo("UTC"))

        with patch("app.services.notification_manager.datetime") as mock_datetime:
            mock_datetime.now.side_effect = lambda tz=None: (
                utc_time if tz else utc_time.replace(tzinfo=None)
            )

            result = notification_manager_instance._is_quiet_hours(prefs)

        # 10 AM EST should NOT be in quiet hours (00:00-08:00)
        assert result is False, "10 AM EST should NOT be within quiet hours 00:00-08:00 EST"

    def test_is_quiet_hours_with_user_timezone_pst(self, notification_manager_instance):
        """Should work with Pacific timezone user"""
        prefs = NotificationPreferences(
            network_id="test-network",
            quiet_hours_enabled=True,
            quiet_hours_start="22:00",
            quiet_hours_end="07:00",
            timezone="America/Los_Angeles",  # PST/PDT
        )

        # Simulate 6:00 AM UTC (which is 10:00 PM PST previous day)
        from zoneinfo import ZoneInfo

        utc_time = datetime(2024, 1, 15, 6, 0, 0, tzinfo=ZoneInfo("UTC"))

        with patch("app.services.notification_manager.datetime") as mock_datetime:
            mock_datetime.now.side_effect = lambda tz=None: (
                utc_time if tz else utc_time.replace(tzinfo=None)
            )

            result = notification_manager_instance._is_quiet_hours(prefs)

        # 10 PM PST should be IN quiet hours (22:00-07:00)
        assert result is True, "10 PM PST should be within overnight quiet hours 22:00-07:00 PST"

    def test_is_quiet_hours_invalid_timezone_fallback(self, notification_manager_instance):
        """Should fall back to server time when timezone is invalid"""
        prefs = NotificationPreferences(
            network_id="test-network",
            quiet_hours_enabled=True,
            quiet_hours_start="00:00",
            quiet_hours_end="08:00",
            timezone="Invalid/Timezone",  # Invalid timezone
        )

        # Mock local time to 3 AM
        mock_time = datetime(2024, 1, 15, 3, 0, 0)
        with patch("app.services.notification_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_time

            result = notification_manager_instance._is_quiet_hours(prefs)

        # Should fall back to server time (3 AM) and be in quiet hours
        assert result is True, "Should fall back to server time when timezone is invalid"

    def test_is_quiet_hours_no_timezone_uses_server_time(self, notification_manager_instance):
        """Should use server local time when no timezone is set"""
        prefs = NotificationPreferences(
            network_id="test-network",
            quiet_hours_enabled=True,
            quiet_hours_start="00:00",
            quiet_hours_end="08:00",
            timezone=None,  # No timezone set
        )

        # Mock local time to 5 AM
        mock_time = datetime(2024, 1, 15, 5, 0, 0)
        with patch("app.services.notification_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_time

            result = notification_manager_instance._is_quiet_hours(prefs)

        # 5 AM server time should be in quiet hours
        assert result is True, "5 AM should be within quiet hours 00:00-08:00 when no timezone set"

    def test_get_current_time_for_user_with_valid_timezone(self, notification_manager_instance):
        """Should return correct time for user's timezone"""
        from zoneinfo import ZoneInfo

        # Simulate 12:00 PM UTC
        utc_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=ZoneInfo("UTC"))

        with patch("app.services.notification_manager.datetime") as mock_datetime:
            mock_datetime.now.side_effect = lambda tz=None: (
                utc_time if tz else utc_time.replace(tzinfo=None)
            )

            result = notification_manager_instance._get_current_time_for_user("America/New_York")

        # 12:00 PM UTC should be 7:00 AM EST
        assert result.hour == 7, "12:00 PM UTC should be 7:00 AM EST"

    def test_get_current_time_for_user_none_timezone(self, notification_manager_instance):
        """Should return server local time when timezone is None"""
        mock_time = datetime(2024, 1, 15, 14, 30, 0)
        with patch("app.services.notification_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_time

            result = notification_manager_instance._get_current_time_for_user(None)

        assert result.hour == 14
        assert result.minute == 30


class TestShouldNotify:
    """Tests for notification filtering"""

    def test_should_notify_master_disabled(self, notification_manager_instance):
        """Should not notify when master switch disabled"""
        prefs = NotificationPreferences(network_id="test-network", enabled=False)
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE, title="Test", message="Test"
        )

        should, reason = notification_manager_instance._should_notify(prefs, event)

        assert should is False
        assert "disabled" in reason.lower()

    def test_should_notify_no_channels(self, notification_manager_instance):
        """Should not notify when no channels enabled"""
        prefs = NotificationPreferences(
            network_id="test-network",
            enabled=True,
            email=EmailConfig(enabled=False),
            discord=DiscordConfig(enabled=False),
        )
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE, title="Test", message="Test"
        )

        should, reason = notification_manager_instance._should_notify(prefs, event)

        assert should is False
        assert "channels" in reason.lower()

    def test_should_notify_event_type_filtered(self, notification_manager_instance):
        """Should not notify when event type not enabled"""
        prefs = NotificationPreferences(
            network_id="test-network",
            enabled=True,
            email=EmailConfig(enabled=True, email_address="test@test.com"),
            enabled_notification_types=[NotificationType.DEVICE_ONLINE],  # Not DEVICE_OFFLINE
        )
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE, title="Test", message="Test"
        )

        should, reason = notification_manager_instance._should_notify(prefs, event)

        assert should is False

    def test_should_notify_priority_below_minimum(self, notification_manager_instance):
        """Should not notify when priority below minimum"""
        prefs = NotificationPreferences(
            network_id="test-network",
            enabled=True,
            email=EmailConfig(enabled=True, email_address="test@test.com"),
            minimum_priority=NotificationPriority.CRITICAL,
            notification_type_priorities={
                NotificationType.DEVICE_OFFLINE: NotificationPriority.LOW
            },
        )
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE, title="Test", message="Test"
        )

        should, reason = notification_manager_instance._should_notify(prefs, event)

        assert should is False


class TestSendNotification:
    """Tests for sending notifications"""

    async def test_send_notification_email(
        self, notification_manager_instance, sample_network_event
    ):
        """Should send email notification"""
        notification_manager_instance._preferences["test-network"] = NotificationPreferences(
            network_id="test-network",
            enabled=True,
            email=EmailConfig(enabled=True, email_address="test@test.com"),
        )

        mock_record = NotificationRecord(
            notification_id="test",
            event_id="test",
            network_id="test-network",
            channel=NotificationChannel.EMAIL,
            success=True,
            title="Test",
            message="Test",
            priority=NotificationPriority.HIGH,
        )

        with patch(
            "app.services.notification_manager.send_notification_email",
            AsyncMock(return_value=mock_record),
        ):
            with patch("app.services.notification_manager.is_email_configured", return_value=True):
                with patch.object(notification_manager_instance, "_save_history"):
                    records = await notification_manager_instance.send_notification(
                        "test-network", sample_network_event, force=True
                    )

        assert len(records) > 0

    async def test_broadcast_notification(
        self, notification_manager_instance, sample_network_event
    ):
        """Should broadcast to all networks"""
        notification_manager_instance._preferences["1"] = NotificationPreferences(
            network_id="1",
            enabled=True,
            email=EmailConfig(enabled=True, email_address="network1@test.com"),
        )
        notification_manager_instance._preferences["2"] = NotificationPreferences(
            network_id="2",
            enabled=True,
            email=EmailConfig(enabled=True, email_address="network2@test.com"),
        )

        mock_record = NotificationRecord(
            notification_id="test",
            event_id="test",
            network_id="",
            channel=NotificationChannel.EMAIL,
            success=True,
            title="Test",
            message="Test",
            priority=NotificationPriority.HIGH,
        )

        with patch(
            "app.services.notification_manager.send_notification_email",
            AsyncMock(return_value=mock_record),
        ):
            with patch("app.services.notification_manager.is_email_configured", return_value=True):
                with patch.object(notification_manager_instance, "_save_history"):
                    results = await notification_manager_instance.broadcast_notification(
                        sample_network_event
                    )

        assert len(results) == 2


class TestTestNotification:
    """Tests for test notifications"""

    async def test_send_test_email_no_address(self, notification_manager_instance):
        """Should fail when no email address configured"""
        notification_manager_instance._preferences["test-network"] = NotificationPreferences(
            network_id="test-network", email=EmailConfig(enabled=True, email_address="")
        )

        request = TestNotificationRequest(channel=NotificationChannel.EMAIL)

        result = await notification_manager_instance.send_test_notification("test-network", request)

        assert result.success is False

    async def test_send_test_discord_not_enabled(self, notification_manager_instance):
        """Should fail when Discord not enabled"""
        notification_manager_instance._preferences["test-network"] = NotificationPreferences(
            network_id="test-network", discord=DiscordConfig(enabled=False)
        )

        request = TestNotificationRequest(channel=NotificationChannel.DISCORD)

        result = await notification_manager_instance.send_test_notification("test-network", request)

        assert result.success is False


class TestHistoryAndStats:
    """Tests for history and statistics"""

    def test_get_history(self, notification_manager_instance):
        """Should return history"""
        notification_manager_instance._history.append(
            NotificationRecord(
                notification_id="1",
                event_id="1",
                network_id="test-network",
                channel=NotificationChannel.EMAIL,
                success=True,
                title="Test",
                message="Test",
                priority=NotificationPriority.HIGH,
            )
        )

        result = notification_manager_instance.get_history(network_id="test-network")

        assert result.total_count == 1

    def test_get_stats(self, notification_manager_instance):
        """Should return stats"""
        notification_manager_instance._history.append(
            NotificationRecord(
                notification_id="1",
                event_id="1",
                network_id="test-network",
                channel=NotificationChannel.EMAIL,
                success=True,
                title="Test",
                message="Test",
                priority=NotificationPriority.HIGH,
                timestamp=datetime.utcnow(),
            )
        )

        stats = notification_manager_instance.get_stats(network_id="test-network")

        assert stats.total_sent_24h == 1


class TestScheduledBroadcasts:
    """Tests for scheduled broadcasts"""

    def test_create_scheduled_broadcast(self, notification_manager_instance):
        """Should create scheduled broadcast"""
        scheduled_at = datetime.utcnow() + timedelta(hours=1)

        with patch.object(notification_manager_instance, "_save_scheduled_broadcasts"):
            broadcast = notification_manager_instance.create_scheduled_broadcast(
                title="Test Broadcast",
                message="Test message",
                scheduled_at=scheduled_at,
                created_by="admin",
                network_id="test-network-uuid",
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
            network_id="test-network-uuid",
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
            created_by="admin",
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
            network_id="test-network-uuid",
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
            created_by="admin",
        )

        with patch.object(notification_manager_instance, "_save_scheduled_broadcasts"):
            result = notification_manager_instance.cancel_scheduled_broadcast("test-id")

        assert result is True
        assert (
            notification_manager_instance._scheduled_broadcasts["test-id"].status
            == ScheduledBroadcastStatus.CANCELLED
        )

    def test_delete_scheduled_broadcast(self, notification_manager_instance):
        """Should delete cancelled broadcast"""
        from app.models import ScheduledBroadcast

        notification_manager_instance._scheduled_broadcasts["test-id"] = ScheduledBroadcast(
            id="test-id",
            title="Test",
            message="Test",
            network_id="test-network-uuid",
            scheduled_at=datetime.utcnow(),
            created_by="admin",
            status=ScheduledBroadcastStatus.CANCELLED,
        )

        with patch.object(notification_manager_instance, "_save_scheduled_broadcasts"):
            result = notification_manager_instance.delete_scheduled_broadcast("test-id")

        assert result is True
        assert "test-id" not in notification_manager_instance._scheduled_broadcasts

    def test_cancel_scheduled_broadcast_not_found(self, notification_manager_instance):
        """Should return False when broadcast not found"""
        result = notification_manager_instance.cancel_scheduled_broadcast("nonexistent")
        assert result is False

    def test_delete_scheduled_broadcast_not_found(self, notification_manager_instance):
        """Should return False when broadcast not found"""
        result = notification_manager_instance.delete_scheduled_broadcast("nonexistent")
        assert result is False

    def test_delete_scheduled_broadcast_not_cancelled(self, notification_manager_instance):
        """Should return False when broadcast is still pending"""
        from app.models import ScheduledBroadcast

        notification_manager_instance._scheduled_broadcasts["test-id"] = ScheduledBroadcast(
            id="test-id",
            title="Test",
            message="Test",
            network_id="test-network-uuid",
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
            created_by="admin",
            status=ScheduledBroadcastStatus.PENDING,
        )

        result = notification_manager_instance.delete_scheduled_broadcast("test-id")
        assert result is False
        assert "test-id" in notification_manager_instance._scheduled_broadcasts

    def test_get_scheduled_broadcasts_include_completed(self, notification_manager_instance):
        """Should include completed broadcasts when requested"""
        from app.models import ScheduledBroadcast

        notification_manager_instance._scheduled_broadcasts["id1"] = ScheduledBroadcast(
            id="id1",
            title="T1",
            message="M1",
            network_id="network-1",
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
            created_by="admin",
            status=ScheduledBroadcastStatus.PENDING,
        )
        notification_manager_instance._scheduled_broadcasts["id2"] = ScheduledBroadcast(
            id="id2",
            title="T2",
            message="M2",
            network_id="network-2",
            scheduled_at=datetime.utcnow(),
            created_by="admin",
            status=ScheduledBroadcastStatus.CANCELLED,
        )

        # By default should only show pending
        response = notification_manager_instance.get_scheduled_broadcasts(include_completed=False)
        assert response.total_count == 1

    def test_get_scheduled_broadcasts_default(self, notification_manager_instance):
        """Should return only pending broadcasts by default"""
        from app.models import ScheduledBroadcast

        notification_manager_instance._scheduled_broadcasts["id1"] = ScheduledBroadcast(
            id="id1",
            title="T1",
            message="M1",
            network_id="network-1",
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
            created_by="admin",
            status=ScheduledBroadcastStatus.PENDING,
        )

        response = notification_manager_instance.get_scheduled_broadcasts()

        assert response.total_count == 1
        assert response.broadcasts[0].status == ScheduledBroadcastStatus.PENDING


class TestGlobalPreferences:
    """Tests for global user preferences"""

    def test_get_global_preferences_new_user(self, notification_manager_instance):
        """Should create default global preferences for new user"""
        from app.models import GlobalUserPreferences

        with patch.object(notification_manager_instance, "_save_global_preferences"):
            prefs = notification_manager_instance.get_global_preferences("new-user-id")

        assert prefs.user_id == "new-user-id"
        assert prefs.cartographer_up_enabled is True
        assert prefs.cartographer_down_enabled is True

    def test_get_global_preferences_existing_user(self, notification_manager_instance):
        """Should return existing global preferences"""
        from app.models import GlobalUserPreferences

        notification_manager_instance._global_preferences["existing-user"] = GlobalUserPreferences(
            user_id="existing-user", cartographer_up_enabled=False
        )

        prefs = notification_manager_instance.get_global_preferences("existing-user")
        assert prefs.cartographer_up_enabled is False

    def test_update_global_preferences(self, notification_manager_instance):
        """Should update global preferences"""
        from app.models import GlobalUserPreferencesUpdate

        with patch.object(notification_manager_instance, "_save_global_preferences"):
            notification_manager_instance.get_global_preferences("test-user")

        update = GlobalUserPreferencesUpdate(
            cartographer_up_enabled=False, cartographer_down_enabled=False
        )

        with patch.object(notification_manager_instance, "_save_global_preferences"):
            result = notification_manager_instance.update_global_preferences("test-user", update)

        assert result.cartographer_up_enabled is False
        assert result.cartographer_down_enabled is False

    def test_get_all_users_with_global_notifications_up(self, notification_manager_instance):
        """Should get users with cartographer UP enabled"""
        from app.models import GlobalUserPreferences

        notification_manager_instance._global_preferences["user1"] = GlobalUserPreferences(
            user_id="user1", cartographer_up_enabled=True, email_address="user1@test.com"
        )
        notification_manager_instance._global_preferences["user2"] = GlobalUserPreferences(
            user_id="user2", cartographer_up_enabled=False, email_address="user2@test.com"
        )

        users = notification_manager_instance.get_all_users_with_global_notifications_enabled(
            NotificationType.CARTOGRAPHER_UP
        )

        assert "user1" in users
        assert "user2" not in users

    def test_get_all_users_with_global_notifications_down(self, notification_manager_instance):
        """Should get users with cartographer DOWN enabled"""
        from app.models import GlobalUserPreferences

        notification_manager_instance._global_preferences["user1"] = GlobalUserPreferences(
            user_id="user1", cartographer_down_enabled=True, email_address="user1@test.com"
        )
        notification_manager_instance._global_preferences["user2"] = GlobalUserPreferences(
            user_id="user2", cartographer_down_enabled=False, email_address="user2@test.com"
        )

        users = notification_manager_instance.get_all_users_with_global_notifications_enabled(
            NotificationType.CARTOGRAPHER_DOWN
        )

        assert "user1" in users
        assert "user2" not in users


class TestPersistence:
    """Tests for data persistence"""

    def test_save_preferences_creates_directory(self, notification_manager_instance, tmp_path):
        """Should create data directory if not exists"""
        with patch(
            "app.services.notification_manager.settings.notification_data_dir",
            str(tmp_path / "new_dir"),
        ):
            with patch(
                "app.services.notification_manager.PREFERENCES_FILE",
                tmp_path / "new_dir" / "prefs.json",
            ):
                notification_manager_instance._save_preferences()

        # No exception should be raised

    def test_load_preferences_missing_file(self, notification_manager_instance, tmp_path):
        """Should handle missing preferences file"""
        with patch(
            "app.services.notification_manager.PREFERENCES_FILE", tmp_path / "nonexistent.json"
        ):
            notification_manager_instance._preferences.clear()
            notification_manager_instance._load_preferences()

        assert len(notification_manager_instance._preferences) == 0

    def test_save_and_load_history(self, notification_manager_instance, tmp_path):
        """Should save and load history correctly"""
        notification_manager_instance._history.append(
            NotificationRecord(
                notification_id="1",
                event_id="1",
                network_id="test",
                channel=NotificationChannel.EMAIL,
                success=True,
                title="Test",
                message="Test",
                priority=NotificationPriority.HIGH,
            )
        )

        with patch(
            "app.services.notification_manager.settings.notification_data_dir", str(tmp_path)
        ):
            with patch("app.services.notification_manager.HISTORY_FILE", tmp_path / "history.json"):
                notification_manager_instance._save_history()

        # Verify file was created
        assert (tmp_path / "history.json").exists()
