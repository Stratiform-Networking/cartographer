"""
Extended tests for notification_dispatch.py to improve coverage.

Covers:
- User notification preferences checks
- Quiet hours handling
- Channel dispatch (email, Discord)
- Network member notifications
- Global notifications
"""

import os
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Set test environment
os.environ["NOTIFICATION_DATA_DIR"] = "/tmp/test_notification_data_dispatch"
os.environ["RESEND_API_KEY"] = ""
os.environ["DISCORD_BOT_TOKEN"] = ""

from app.models import (
    NetworkEvent,
    NotificationChannel,
    NotificationPriority,
    NotificationRecord,
    NotificationType,
)
from app.models.database import (
    NotificationPriorityEnum,
    UserGlobalNotificationPrefs,
    UserNetworkNotificationPrefs,
)
from app.services.notification_dispatch import (
    NotificationDispatchService,
    notification_dispatch_service,
)


class MockUserNetworkPrefs:
    """Mock user network notification preferences."""

    def __init__(
        self,
        user_id="test-user",
        network_id="test-network",
        email_enabled=True,
        discord_enabled=False,
        discord_user_id=None,
        enabled_types=None,
        type_priorities=None,
        minimum_priority=NotificationPriorityEnum.LOW,
        quiet_hours_enabled=False,
        quiet_hours_start=None,
        quiet_hours_end=None,
        quiet_hours_timezone=None,
        quiet_hours_bypass_priority=None,
    ):
        self.user_id = user_id
        self.network_id = network_id
        self.email_enabled = email_enabled
        self.discord_enabled = discord_enabled
        self.discord_user_id = discord_user_id
        self.enabled_types = enabled_types or [NotificationType.DEVICE_OFFLINE.value]
        self.type_priorities = type_priorities or {}
        self.minimum_priority = minimum_priority
        self.quiet_hours_enabled = quiet_hours_enabled
        self.quiet_hours_start = quiet_hours_start
        self.quiet_hours_end = quiet_hours_end
        self.quiet_hours_timezone = quiet_hours_timezone
        self.quiet_hours_bypass_priority = quiet_hours_bypass_priority


class MockUserGlobalPrefs:
    """Mock user global notification preferences."""

    def __init__(
        self,
        user_id="test-user",
        email_enabled=True,
        discord_enabled=False,
        discord_user_id=None,
        minimum_priority=NotificationPriorityEnum.LOW,
        quiet_hours_enabled=False,
        quiet_hours_start=None,
        quiet_hours_end=None,
        quiet_hours_timezone=None,
        quiet_hours_bypass_priority=None,
    ):
        self.user_id = user_id
        self.email_enabled = email_enabled
        self.discord_enabled = discord_enabled
        self.discord_user_id = discord_user_id
        self.minimum_priority = minimum_priority
        self.quiet_hours_enabled = quiet_hours_enabled
        self.quiet_hours_start = quiet_hours_start
        self.quiet_hours_end = quiet_hours_end
        self.quiet_hours_timezone = quiet_hours_timezone
        self.quiet_hours_bypass_priority = quiet_hours_bypass_priority


@pytest.fixture
def service():
    """Create dispatch service instance."""
    return NotificationDispatchService()


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return AsyncMock()


@pytest.fixture
def sample_event():
    """Create sample network event."""
    return NetworkEvent(
        event_type=NotificationType.DEVICE_OFFLINE,
        priority=NotificationPriority.HIGH,
        title="Test Event",
        message="Test message",
    )


class TestShouldNotifyUser:
    """Tests for _should_notify_user method."""

    def test_no_channels_enabled(self, service):
        """Test when no channels are enabled."""
        prefs = MockUserNetworkPrefs(email_enabled=False, discord_enabled=False)
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            priority=NotificationPriority.HIGH,
            title="Test",
            message="Test",
        )

        should_notify, reason = service._should_notify_user(prefs, event)

        assert should_notify is False
        assert "No notification channels" in reason

    def test_event_type_not_enabled(self, service):
        """Test when event type is not enabled."""
        prefs = MockUserNetworkPrefs(enabled_types=[NotificationType.DEVICE_ONLINE.value])
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            priority=NotificationPriority.HIGH,
            title="Test",
            message="Test",
        )

        should_notify, reason = service._should_notify_user(prefs, event)

        assert should_notify is False
        assert "not enabled" in reason

    def test_priority_below_minimum(self, service):
        """Test when priority is below minimum."""
        prefs = MockUserNetworkPrefs(minimum_priority=NotificationPriorityEnum.HIGH)
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            priority=NotificationPriority.LOW,
            title="Test",
            message="Test",
        )

        should_notify, reason = service._should_notify_user(prefs, event)

        assert should_notify is False
        assert "below minimum" in reason

    def test_priority_override_below_minimum(self, service):
        """Test when overridden priority is below minimum."""
        prefs = MockUserNetworkPrefs(
            minimum_priority=NotificationPriorityEnum.HIGH,
            type_priorities={NotificationType.DEVICE_OFFLINE.value: "low"},
        )
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            priority=NotificationPriority.CRITICAL,  # Original is high
            title="Test",
            message="Test",
        )

        should_notify, reason = service._should_notify_user(prefs, event)

        assert should_notify is False
        assert "below minimum" in reason

    def test_in_quiet_hours_no_bypass(self, service):
        """Test when in quiet hours without bypass."""
        prefs = MockUserNetworkPrefs(
            quiet_hours_enabled=True,
            quiet_hours_start="00:00",
            quiet_hours_end="23:59",
            quiet_hours_bypass_priority=None,
        )
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            priority=NotificationPriority.HIGH,
            title="Test",
            message="Test",
        )

        with patch.object(service, "_is_quiet_hours", return_value=True):
            should_notify, reason = service._should_notify_user(prefs, event)

        assert should_notify is False
        assert "quiet hours" in reason

    def test_in_quiet_hours_below_bypass(self, service):
        """Test when in quiet hours and below bypass threshold."""
        prefs = MockUserNetworkPrefs(
            quiet_hours_enabled=True,
            quiet_hours_start="00:00",
            quiet_hours_end="23:59",
            quiet_hours_bypass_priority=NotificationPriorityEnum.CRITICAL,
        )
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            priority=NotificationPriority.HIGH,
            title="Test",
            message="Test",
        )

        with patch.object(service, "_is_quiet_hours", return_value=True):
            should_notify, reason = service._should_notify_user(prefs, event)

        assert should_notify is False
        assert "quiet hours" in reason

    def test_in_quiet_hours_above_bypass(self, service):
        """Test when in quiet hours and above bypass threshold."""
        prefs = MockUserNetworkPrefs(
            quiet_hours_enabled=True,
            quiet_hours_start="00:00",
            quiet_hours_end="23:59",
            quiet_hours_bypass_priority=NotificationPriorityEnum.HIGH,
        )
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            priority=NotificationPriority.CRITICAL,
            title="Test",
            message="Test",
        )

        with patch.object(service, "_is_quiet_hours", return_value=True):
            should_notify, reason = service._should_notify_user(prefs, event)

        assert should_notify is True

    def test_should_notify_success(self, service):
        """Test successful notification check."""
        prefs = MockUserNetworkPrefs()
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            priority=NotificationPriority.HIGH,
            title="Test",
            message="Test",
        )

        should_notify, reason = service._should_notify_user(prefs, event)

        assert should_notify is True
        assert reason == ""


class TestIsQuietHours:
    """Tests for _is_quiet_hours method."""

    def test_no_times_configured(self, service):
        """Test when quiet hours times are not configured."""
        prefs = MockUserNetworkPrefs(
            quiet_hours_enabled=True,
            quiet_hours_start=None,
            quiet_hours_end=None,
        )

        result = service._is_quiet_hours(prefs)

        assert result is False

    def test_in_quiet_hours_daytime(self, service):
        """Test checking quiet hours during day (non-overnight)."""
        prefs = MockUserNetworkPrefs(
            quiet_hours_enabled=True,
            quiet_hours_start="10:00",
            quiet_hours_end="14:00",
        )

        # Mock current time to be 12:00
        with patch("app.services.notification_dispatch.datetime") as mock_dt:
            mock_now = MagicMock()
            mock_now.strftime.return_value = "12:00"
            mock_dt.now.return_value = mock_now

            result = service._is_quiet_hours(prefs)

        assert result is True

    def test_outside_quiet_hours_daytime(self, service):
        """Test checking quiet hours outside daytime range."""
        prefs = MockUserNetworkPrefs(
            quiet_hours_enabled=True,
            quiet_hours_start="10:00",
            quiet_hours_end="14:00",
        )

        # Mock current time to be 08:00
        with patch("app.services.notification_dispatch.datetime") as mock_dt:
            mock_now = MagicMock()
            mock_now.strftime.return_value = "08:00"
            mock_dt.now.return_value = mock_now

            result = service._is_quiet_hours(prefs)

        assert result is False

    def test_in_quiet_hours_overnight_early(self, service):
        """Test checking overnight quiet hours (early morning)."""
        prefs = MockUserNetworkPrefs(
            quiet_hours_enabled=True,
            quiet_hours_start="22:00",
            quiet_hours_end="07:00",
        )

        # Mock current time to be 03:00 (in overnight quiet hours)
        with patch("app.services.notification_dispatch.datetime") as mock_dt:
            mock_now = MagicMock()
            mock_now.strftime.return_value = "03:00"
            mock_dt.now.return_value = mock_now

            result = service._is_quiet_hours(prefs)

        assert result is True

    def test_in_quiet_hours_overnight_late(self, service):
        """Test checking overnight quiet hours (late night)."""
        prefs = MockUserNetworkPrefs(
            quiet_hours_enabled=True,
            quiet_hours_start="22:00",
            quiet_hours_end="07:00",
        )

        # Mock current time to be 23:00 (in overnight quiet hours)
        with patch("app.services.notification_dispatch.datetime") as mock_dt:
            mock_now = MagicMock()
            mock_now.strftime.return_value = "23:00"
            mock_dt.now.return_value = mock_now

            result = service._is_quiet_hours(prefs)

        assert result is True

    def test_with_timezone(self, service):
        """Test checking quiet hours with timezone."""
        prefs = MockUserNetworkPrefs(
            quiet_hours_enabled=True,
            quiet_hours_start="10:00",
            quiet_hours_end="14:00",
            quiet_hours_timezone="America/New_York",
        )

        result = service._is_quiet_hours(prefs)
        # Just verify it doesn't error with timezone
        assert result in [True, False]

    def test_with_invalid_timezone(self, service):
        """Test checking quiet hours with invalid timezone."""
        prefs = MockUserNetworkPrefs(
            quiet_hours_enabled=True,
            quiet_hours_start="10:00",
            quiet_hours_end="14:00",
            quiet_hours_timezone="Invalid/Timezone",
        )

        # Should not error, falls back to local time
        result = service._is_quiet_hours(prefs)
        assert result in [True, False]


class TestSendToUser:
    """Tests for send_to_user method."""

    @pytest.mark.asyncio
    async def test_send_email_not_configured(self, service, mock_db, sample_event):
        """Test sending email when not configured."""
        prefs = MockUserNetworkPrefs(email_enabled=True)

        with (
            patch("app.services.notification_dispatch.user_preferences_service") as mock_prefs_svc,
            patch("app.services.notification_dispatch.is_email_configured", return_value=False),
        ):

            mock_prefs_svc.get_or_create_network_preferences = AsyncMock(return_value=prefs)

            records = await service.send_to_user(mock_db, "test-user", "test-network", sample_event)

        assert len(records) == 1
        assert records[0].success is False
        assert "not configured" in records[0].error_message

    @pytest.mark.asyncio
    async def test_send_email_no_address(self, service, mock_db, sample_event):
        """Test sending email when no address available."""
        prefs = MockUserNetworkPrefs(email_enabled=True)

        with (
            patch("app.services.notification_dispatch.user_preferences_service") as mock_prefs_svc,
            patch("app.services.notification_dispatch.is_email_configured", return_value=True),
        ):

            mock_prefs_svc.get_or_create_network_preferences = AsyncMock(return_value=prefs)
            mock_prefs_svc.get_user_email = AsyncMock(return_value=None)

            records = await service.send_to_user(
                mock_db, "test-user", "test-network", sample_event, user_email=None
            )

        # No records since no email address
        assert len(records) == 0

    @pytest.mark.asyncio
    async def test_send_email_success(self, service, mock_db, sample_event):
        """Test successful email sending."""
        prefs = MockUserNetworkPrefs(email_enabled=True)
        mock_record = MagicMock(spec=NotificationRecord)
        mock_record.success = True
        mock_record.network_id = None

        with (
            patch("app.services.notification_dispatch.user_preferences_service") as mock_prefs_svc,
            patch("app.services.notification_dispatch.is_email_configured", return_value=True),
            patch(
                "app.services.notification_dispatch.send_notification_email", new_callable=AsyncMock
            ) as mock_send,
        ):

            mock_prefs_svc.get_or_create_network_preferences = AsyncMock(return_value=prefs)
            mock_send.return_value = mock_record

            records = await service.send_to_user(
                mock_db, "test-user", "test-network", sample_event, user_email="test@example.com"
            )

        assert len(records) == 1
        assert records[0].success is True

    @pytest.mark.asyncio
    async def test_send_discord_not_configured(self, service, mock_db, sample_event):
        """Test sending Discord when not configured."""
        prefs = MockUserNetworkPrefs(
            email_enabled=False,
            discord_enabled=True,
            discord_user_id="123456789",
        )

        with (
            patch("app.services.notification_dispatch.user_preferences_service") as mock_prefs_svc,
            patch("app.services.notification_dispatch.is_discord_configured", return_value=False),
        ):

            mock_prefs_svc.get_or_create_network_preferences = AsyncMock(return_value=prefs)

            records = await service.send_to_user(mock_db, "test-user", "test-network", sample_event)

        assert len(records) == 1
        assert records[0].success is False
        assert "not configured" in records[0].error_message

    @pytest.mark.asyncio
    async def test_send_with_discord_disabled(self, service, mock_db, sample_event):
        """Test sending when Discord is disabled."""
        prefs = MockUserNetworkPrefs(
            email_enabled=False,
            discord_enabled=False,  # Disabled
            discord_user_id="123456789",
        )

        with patch("app.services.notification_dispatch.user_preferences_service") as mock_prefs_svc:
            mock_prefs_svc.get_or_create_network_preferences = AsyncMock(return_value=prefs)

            records = await service.send_to_user(mock_db, "test-user", "test-network", sample_event)

        # Should skip since no channels enabled
        assert len(records) == 0

    @pytest.mark.asyncio
    async def test_skip_notification(self, service, mock_db, sample_event):
        """Test skipping notification when should_notify is False."""
        prefs = MockUserNetworkPrefs(email_enabled=False, discord_enabled=False)

        with patch("app.services.notification_dispatch.user_preferences_service") as mock_prefs_svc:
            mock_prefs_svc.get_or_create_network_preferences = AsyncMock(return_value=prefs)

            records = await service.send_to_user(mock_db, "test-user", "test-network", sample_event)

        assert len(records) == 0


class TestSendToNetworkUsers:
    """Tests for send_to_network_users method."""

    @pytest.mark.asyncio
    async def test_send_to_multiple_users(self, service, mock_db, sample_event):
        """Test sending to multiple network users."""
        prefs = MockUserNetworkPrefs(email_enabled=True)
        mock_record = MagicMock(spec=NotificationRecord)
        mock_record.success = True
        mock_record.network_id = None

        with (
            patch("app.services.notification_dispatch.user_preferences_service") as mock_prefs_svc,
            patch("app.services.notification_dispatch.is_email_configured", return_value=True),
            patch(
                "app.services.notification_dispatch.send_notification_email", new_callable=AsyncMock
            ) as mock_send,
        ):

            mock_prefs_svc.get_or_create_network_preferences = AsyncMock(return_value=prefs)
            mock_prefs_svc.get_user_email = AsyncMock(return_value="test@example.com")
            mock_send.return_value = mock_record

            results = await service.send_to_network_users(
                mock_db, "test-network", ["user1", "user2"], sample_event
            )

        assert len(results) == 2
        assert "user1" in results
        assert "user2" in results

    @pytest.mark.asyncio
    async def test_scheduled_notification_warning(self, service, mock_db, sample_event):
        """Test scheduled notifications show warning."""
        future_time = datetime.now(dt_timezone.utc) + timedelta(hours=1)

        results = await service.send_to_network_users(
            mock_db, "test-network", ["user1"], sample_event, scheduled_at=future_time
        )

        # Should return empty (not implemented)
        assert results == {}


class TestSendGlobalNotification:
    """Tests for send_global_notification method."""

    @pytest.mark.asyncio
    async def test_send_global_notification_no_users(self, service, mock_db, sample_event):
        """Test global notification with no subscribers."""
        with patch("app.services.notification_dispatch.user_preferences_service") as mock_prefs_svc:
            mock_prefs_svc.get_users_with_global_notifications_enabled = AsyncMock(return_value=[])

            results = await service.send_global_notification(mock_db, sample_event)

        assert results == {}

    @pytest.mark.asyncio
    async def test_send_global_notification_priority_filter(self, service, mock_db):
        """Test global notification filters by priority."""
        event = NetworkEvent(
            event_type=NotificationType.CARTOGRAPHER_UP,
            priority=NotificationPriority.LOW,
            title="Test",
            message="Test",
        )

        prefs = MockUserGlobalPrefs(
            user_id="test-user",
            email_enabled=True,
            minimum_priority=NotificationPriorityEnum.HIGH,
        )

        with patch("app.services.notification_dispatch.user_preferences_service") as mock_prefs_svc:
            mock_prefs_svc.get_users_with_global_notifications_enabled = AsyncMock(
                return_value=[prefs]
            )

            results = await service.send_global_notification(mock_db, event)

        # Should filter out due to priority
        assert results == {}

    @pytest.mark.asyncio
    async def test_send_global_notification_email_success(self, service, mock_db):
        """Test successful global notification via email."""
        event = NetworkEvent(
            event_type=NotificationType.CARTOGRAPHER_UP,
            priority=NotificationPriority.HIGH,
            title="Test",
            message="Test",
        )

        prefs = MockUserGlobalPrefs(
            user_id="test-user",
            email_enabled=True,
        )

        mock_record = MagicMock(spec=NotificationRecord)
        mock_record.success = True
        mock_record.network_id = None

        with (
            patch("app.services.notification_dispatch.user_preferences_service") as mock_prefs_svc,
            patch("app.services.notification_dispatch.is_email_configured", return_value=True),
            patch(
                "app.services.notification_dispatch.send_notification_email", new_callable=AsyncMock
            ) as mock_send,
        ):

            mock_prefs_svc.get_users_with_global_notifications_enabled = AsyncMock(
                return_value=[prefs]
            )
            mock_prefs_svc.get_user_email = AsyncMock(return_value="test@example.com")
            mock_send.return_value = mock_record

            results = await service.send_global_notification(mock_db, event)

        assert len(results) == 1
        assert "test-user" in results

    @pytest.mark.asyncio
    async def test_send_global_notification_no_discord(self, service, mock_db):
        """Test global notification when Discord is disabled."""
        event = NetworkEvent(
            event_type=NotificationType.CARTOGRAPHER_UP,
            priority=NotificationPriority.HIGH,
            title="Test",
            message="Test",
        )

        prefs = MockUserGlobalPrefs(
            user_id="test-user",
            email_enabled=False,
            discord_enabled=False,  # Disabled
            discord_user_id="123456789",
        )

        with patch("app.services.notification_dispatch.user_preferences_service") as mock_prefs_svc:
            mock_prefs_svc.get_users_with_global_notifications_enabled = AsyncMock(
                return_value=[prefs]
            )
            mock_prefs_svc.get_user_email = AsyncMock(return_value=None)

            results = await service.send_global_notification(mock_db, event)

        # User not in results since no channels enabled
        assert results == {}
