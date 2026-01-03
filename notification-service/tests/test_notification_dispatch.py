"""
Tests for Notification Dispatch Service.

This module tests the NotificationDispatchService which handles dispatching
notifications to users via email and Discord, including filtering based on
user preferences, quiet hours, and rate limiting.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models import (
    NetworkEvent,
    NotificationChannel,
    NotificationPriority,
    NotificationRecord,
    NotificationType,
)


class TestNotificationDispatchService:
    """Tests for NotificationDispatchService"""

    @pytest.fixture
    def dispatch_service(self):
        """Create a notification dispatch service instance"""
        from app.services.notification_dispatch import NotificationDispatchService

        return NotificationDispatchService()

    @pytest.fixture
    def mock_prefs(self):
        """Create mock user network notification preferences"""
        prefs = MagicMock()
        prefs.email_enabled = True
        prefs.discord_enabled = False
        prefs.enabled_types = ["device_offline", "device_online"]
        prefs.type_priorities = {}
        prefs.minimum_priority = "medium"
        prefs.quiet_hours_enabled = False
        prefs.quiet_hours_start = "22:00"
        prefs.quiet_hours_end = "08:00"
        prefs.quiet_hours_timezone = None
        prefs.quiet_hours_bypass_priority = None
        prefs.discord_user_id = None
        return prefs

    @pytest.fixture
    def sample_event(self):
        """Sample network event"""
        return NetworkEvent(
            event_id="test-123",
            event_type=NotificationType.DEVICE_OFFLINE,
            priority=NotificationPriority.HIGH,
            title="Device Offline",
            message="Device at 192.168.1.1 is offline",
            network_id="network-123",
        )


class TestShouldNotifyUser:
    """Tests for _should_notify_user logic"""

    @pytest.fixture
    def dispatch_service(self):
        from app.services.notification_dispatch import NotificationDispatchService

        return NotificationDispatchService()

    @pytest.fixture
    def mock_prefs(self):
        prefs = MagicMock()
        prefs.email_enabled = True
        prefs.discord_enabled = False
        prefs.enabled_types = ["device_offline", "device_online"]
        prefs.type_priorities = {}
        prefs.minimum_priority = "medium"
        prefs.quiet_hours_enabled = False
        prefs.quiet_hours_start = "22:00"
        prefs.quiet_hours_end = "08:00"
        prefs.quiet_hours_timezone = None
        prefs.quiet_hours_bypass_priority = None
        prefs.discord_user_id = None
        return prefs

    @pytest.fixture
    def sample_event(self):
        return NetworkEvent(
            event_id="test-123",
            event_type=NotificationType.DEVICE_OFFLINE,
            priority=NotificationPriority.HIGH,
            title="Device Offline",
            message="Device at 192.168.1.1 is offline",
            network_id="network-123",
        )

    def test_should_notify_user_no_channels(self, dispatch_service, mock_prefs, sample_event):
        """Should return False when no channels enabled"""
        mock_prefs.email_enabled = False
        mock_prefs.discord_enabled = False

        should_notify, reason = dispatch_service._should_notify_user(mock_prefs, sample_event)

        assert should_notify is False
        assert "No notification channels enabled" in reason

    def test_should_notify_user_type_not_enabled(self, dispatch_service, mock_prefs, sample_event):
        """Should return False when event type not enabled"""
        mock_prefs.enabled_types = ["device_online"]

        should_notify, reason = dispatch_service._should_notify_user(mock_prefs, sample_event)

        assert should_notify is False
        assert "not enabled" in reason

    def test_should_notify_user_priority_below_minimum(
        self, dispatch_service, mock_prefs, sample_event
    ):
        """Should return False when priority below minimum"""
        mock_prefs.minimum_priority = "critical"
        sample_event.priority = NotificationPriority.LOW

        should_notify, reason = dispatch_service._should_notify_user(mock_prefs, sample_event)

        assert should_notify is False
        assert "Priority" in reason

    def test_should_notify_user_priority_with_override(
        self, dispatch_service, mock_prefs, sample_event
    ):
        """Should use user's priority override for event type"""
        mock_prefs.type_priorities = {"device_offline": "critical"}
        mock_prefs.minimum_priority = "high"
        sample_event.priority = NotificationPriority.LOW

        should_notify, reason = dispatch_service._should_notify_user(mock_prefs, sample_event)

        assert should_notify is True

    def test_should_notify_user_invalid_priority_override(
        self, dispatch_service, mock_prefs, sample_event
    ):
        """Should fall back when priority override is invalid"""
        mock_prefs.type_priorities = {"device_offline": "invalid_priority"}

        should_notify, reason = dispatch_service._should_notify_user(mock_prefs, sample_event)

        assert should_notify is True


class TestQuietHours:
    """Tests for quiet hours logic"""

    @pytest.fixture
    def dispatch_service(self):
        from app.services.notification_dispatch import NotificationDispatchService

        return NotificationDispatchService()

    @pytest.fixture
    def mock_prefs(self):
        prefs = MagicMock()
        prefs.email_enabled = True
        prefs.discord_enabled = False
        prefs.enabled_types = ["device_offline", "device_online"]
        prefs.type_priorities = {}
        prefs.minimum_priority = "medium"
        prefs.quiet_hours_enabled = False
        prefs.quiet_hours_start = "22:00"
        prefs.quiet_hours_end = "08:00"
        prefs.quiet_hours_timezone = None
        prefs.quiet_hours_bypass_priority = None
        prefs.discord_user_id = None
        return prefs

    @pytest.fixture
    def sample_event(self):
        return NetworkEvent(
            event_id="test-123",
            event_type=NotificationType.DEVICE_OFFLINE,
            priority=NotificationPriority.HIGH,
            title="Device Offline",
            message="Device at 192.168.1.1 is offline",
            network_id="network-123",
        )

    def test_should_notify_user_quiet_hours_not_in_quiet(
        self, dispatch_service, mock_prefs, sample_event
    ):
        """Should notify when quiet hours enabled but not currently in quiet hours"""
        mock_prefs.quiet_hours_enabled = True

        with patch.object(dispatch_service, "_is_quiet_hours", return_value=False):
            should_notify, reason = dispatch_service._should_notify_user(mock_prefs, sample_event)

        assert should_notify is True

    def test_should_notify_user_quiet_hours_blocked(
        self, dispatch_service, mock_prefs, sample_event
    ):
        """Should block notification during quiet hours"""
        mock_prefs.quiet_hours_enabled = True
        mock_prefs.quiet_hours_bypass_priority = None

        with patch.object(dispatch_service, "_is_quiet_hours", return_value=True):
            should_notify, reason = dispatch_service._should_notify_user(mock_prefs, sample_event)

        assert should_notify is False
        assert "quiet hours" in reason.lower()

    def test_should_notify_user_quiet_hours_bypass(
        self, dispatch_service, mock_prefs, sample_event
    ):
        """Should bypass quiet hours for high priority"""
        from app.models.database import NotificationPriorityEnum

        mock_prefs.quiet_hours_enabled = True
        mock_prefs.quiet_hours_bypass_priority = NotificationPriorityEnum.MEDIUM
        sample_event.priority = NotificationPriority.HIGH

        with patch.object(dispatch_service, "_is_quiet_hours", return_value=True):
            should_notify, reason = dispatch_service._should_notify_user(mock_prefs, sample_event)

        assert should_notify is True

    def test_is_quiet_hours_no_times(self, dispatch_service, mock_prefs):
        """Should return False when quiet hours times not set"""
        mock_prefs.quiet_hours_start = None
        mock_prefs.quiet_hours_end = None

        result = dispatch_service._is_quiet_hours(mock_prefs)

        assert result is False

    def test_is_quiet_hours_with_timezone(self, dispatch_service, mock_prefs):
        """Should check quiet hours with timezone"""
        mock_prefs.quiet_hours_start = "22:00"
        mock_prefs.quiet_hours_end = "08:00"
        mock_prefs.quiet_hours_timezone = "UTC"

        result = dispatch_service._is_quiet_hours(mock_prefs)

        assert isinstance(result, bool)

    def test_is_quiet_hours_invalid_timezone(self, dispatch_service, mock_prefs):
        """Should handle invalid timezone gracefully"""
        mock_prefs.quiet_hours_start = "22:00"
        mock_prefs.quiet_hours_end = "08:00"
        mock_prefs.quiet_hours_timezone = "Invalid/Timezone"

        result = dispatch_service._is_quiet_hours(mock_prefs)

        assert isinstance(result, bool)

    def test_is_quiet_hours_overnight(self, dispatch_service, mock_prefs):
        """Should handle overnight quiet hours (22:00 to 08:00)"""
        mock_prefs.quiet_hours_start = "22:00"
        mock_prefs.quiet_hours_end = "08:00"
        mock_prefs.quiet_hours_timezone = None

        result = dispatch_service._is_quiet_hours(mock_prefs)
        assert isinstance(result, bool)

    def test_is_quiet_hours_same_day(self, dispatch_service, mock_prefs):
        """Should handle same-day quiet hours (08:00 to 17:00)"""
        mock_prefs.quiet_hours_start = "08:00"
        mock_prefs.quiet_hours_end = "17:00"
        mock_prefs.quiet_hours_timezone = None

        result = dispatch_service._is_quiet_hours(mock_prefs)
        assert isinstance(result, bool)


class TestSendToUser:
    """Tests for send_to_user functionality"""

    @pytest.fixture
    def dispatch_service(self):
        from app.services.notification_dispatch import NotificationDispatchService

        return NotificationDispatchService()

    @pytest.fixture
    def sample_event(self):
        return NetworkEvent(
            event_id="test-123",
            event_type=NotificationType.DEVICE_OFFLINE,
            priority=NotificationPriority.HIGH,
            title="Device Offline",
            message="Device at 192.168.1.1 is offline",
            network_id="network-123",
        )

    @pytest.mark.asyncio
    async def test_send_to_user_email_configured(self, dispatch_service, sample_event):
        """Should send email when configured"""
        mock_db = AsyncMock()
        mock_prefs = MagicMock()
        mock_prefs.email_enabled = True
        mock_prefs.discord_enabled = False
        mock_prefs.enabled_types = ["device_offline"]
        mock_prefs.type_priorities = {}
        mock_prefs.minimum_priority = "low"
        mock_prefs.quiet_hours_enabled = False
        mock_prefs.discord_user_id = None

        mock_record = NotificationRecord(
            notification_id="test",
            event_id="test",
            network_id="network-123",
            channel=NotificationChannel.EMAIL,
            success=True,
            title="Test",
            message="Test",
            priority=NotificationPriority.HIGH,
        )

        with patch("app.services.notification_dispatch.user_preferences_service") as mock_ups:
            mock_ups.get_or_create_network_preferences = AsyncMock(return_value=mock_prefs)
            mock_ups.get_user_email = AsyncMock(return_value="test@example.com")

            with patch("app.services.notification_dispatch.is_email_configured", return_value=True):
                with patch(
                    "app.services.notification_dispatch.send_notification_email",
                    new_callable=AsyncMock,
                ) as mock_send:
                    mock_send.return_value = mock_record

                    records = await dispatch_service.send_to_user(
                        mock_db, "user-123", "network-123", sample_event
                    )

        assert len(records) == 1
        assert records[0].success is True

    @pytest.mark.asyncio
    async def test_send_to_user_email_not_configured(self, dispatch_service, sample_event):
        """Should record failure when email not configured"""
        mock_db = AsyncMock()
        mock_prefs = MagicMock()
        mock_prefs.email_enabled = True
        mock_prefs.discord_enabled = False
        mock_prefs.enabled_types = ["device_offline"]
        mock_prefs.type_priorities = {}
        mock_prefs.minimum_priority = "low"
        mock_prefs.quiet_hours_enabled = False
        mock_prefs.discord_user_id = None

        with patch("app.services.notification_dispatch.user_preferences_service") as mock_ups:
            mock_ups.get_or_create_network_preferences = AsyncMock(return_value=mock_prefs)

            with patch(
                "app.services.notification_dispatch.is_email_configured", return_value=False
            ):
                records = await dispatch_service.send_to_user(
                    mock_db, "user-123", "network-123", sample_event
                )

        assert len(records) == 1
        assert records[0].success is False
        assert "not configured" in records[0].error_message

    @pytest.mark.asyncio
    async def test_send_to_user_discord_not_configured(self, dispatch_service, sample_event):
        """Should record failure when Discord not configured"""
        mock_db = AsyncMock()
        mock_prefs = MagicMock()
        mock_prefs.email_enabled = False
        mock_prefs.discord_enabled = True
        mock_prefs.discord_user_id = "discord-123"
        mock_prefs.enabled_types = ["device_offline"]
        mock_prefs.type_priorities = {}
        mock_prefs.minimum_priority = "low"
        mock_prefs.quiet_hours_enabled = False

        with patch("app.services.notification_dispatch.user_preferences_service") as mock_ups:
            mock_ups.get_or_create_network_preferences = AsyncMock(return_value=mock_prefs)

            with patch(
                "app.services.notification_dispatch.is_discord_configured", return_value=False
            ):
                records = await dispatch_service.send_to_user(
                    mock_db, "user-123", "network-123", sample_event
                )

        assert len(records) == 1
        assert records[0].success is False


class TestSendToNetworkUsers:
    """Tests for send_to_network_users functionality"""

    @pytest.fixture
    def dispatch_service(self):
        from app.services.notification_dispatch import NotificationDispatchService

        return NotificationDispatchService()

    @pytest.fixture
    def sample_event(self):
        return NetworkEvent(
            event_id="test-123",
            event_type=NotificationType.DEVICE_OFFLINE,
            priority=NotificationPriority.HIGH,
            title="Device Offline",
            message="Device at 192.168.1.1 is offline",
            network_id="network-123",
        )

    @pytest.mark.asyncio
    async def test_send_to_network_users(self, dispatch_service, sample_event):
        """Should send to multiple users"""
        mock_db = AsyncMock()

        # Create mock prefs that will pass _should_notify_user check
        mock_prefs = MagicMock()
        mock_prefs.email_enabled = True
        mock_prefs.discord_enabled = False
        mock_prefs.enabled_types = ["device_offline"]
        mock_prefs.type_priorities = {}
        mock_prefs.minimum_priority = "low"
        mock_prefs.quiet_hours_enabled = False
        mock_prefs.discord_user_id = None

        with patch("app.services.notification_dispatch.user_preferences_service") as mock_ups:
            # Mock batch methods that are awaited
            mock_ups.get_user_emails_batch = AsyncMock(
                return_value={"user1": "u1@example.com", "user2": "u2@example.com", "user3": "u3@example.com"}
            )
            mock_ups.get_network_preferences_batch = AsyncMock(
                return_value={"user1": mock_prefs, "user2": mock_prefs, "user3": mock_prefs}
            )

            # Mock the dispatch method
            with patch.object(
                dispatch_service, "_dispatch_notifications_for_user", new_callable=AsyncMock
            ) as mock_dispatch:
                mock_dispatch.return_value = []

                results = await dispatch_service.send_to_network_users(
                    mock_db, "network-123", ["user1", "user2", "user3"], sample_event
                )

        assert len(results) == 3
        assert mock_dispatch.call_count == 3

    @pytest.mark.asyncio
    async def test_send_to_network_users_scheduled(self, dispatch_service, sample_event):
        """Should skip scheduled notifications (not yet implemented)"""
        mock_db = AsyncMock()
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)

        results = await dispatch_service.send_to_network_users(
            mock_db, "network-123", ["user1"], sample_event, scheduled_at=future_time
        )

        assert len(results) == 0


class TestNotificationDispatchServiceSingleton:
    """Tests for notification dispatch service singleton"""

    def test_service_exists(self):
        """Should have singleton dispatch service"""
        from app.services.notification_dispatch import notification_dispatch_service

        assert notification_dispatch_service is not None

    def test_service_class_import(self):
        """Should import notification dispatch service class"""
        from app.services.notification_dispatch import NotificationDispatchService

        service = NotificationDispatchService()

        assert service is not None
