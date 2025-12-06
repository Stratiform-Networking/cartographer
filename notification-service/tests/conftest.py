"""
Shared test fixtures for notification service unit tests.
"""
import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

# Set test environment before imports
os.environ["RESEND_API_KEY"] = ""
os.environ["DISCORD_BOT_TOKEN"] = ""
os.environ["DISCORD_CLIENT_ID"] = ""
os.environ["NOTIFICATION_DATA_DIR"] = "/tmp/test_notification_data"


@pytest.fixture
def sample_network_event():
    """Sample network event for testing"""
    from app.models import NetworkEvent, NotificationType, NotificationPriority
    return NetworkEvent(
        event_id="test-event-123",
        event_type=NotificationType.DEVICE_OFFLINE,
        priority=NotificationPriority.HIGH,
        device_ip="192.168.1.100",
        device_name="Test Device",
        title="Device Offline: Test Device",
        message="The device at 192.168.1.100 is no longer responding.",
        details={"test": True},
    )


@pytest.fixture
def sample_preferences():
    """Sample notification preferences"""
    from app.models import (
        NotificationPreferences,
        EmailConfig,
        DiscordConfig,
        NotificationType,
        NotificationPriority,
    )
    return NotificationPreferences(
        user_id="test-user-1",
        enabled=True,
        email=EmailConfig(enabled=True, email_address="test@example.com"),
        discord=DiscordConfig(enabled=False),
        enabled_notification_types=[
            NotificationType.DEVICE_OFFLINE,
            NotificationType.DEVICE_ONLINE,
            NotificationType.ANOMALY_DETECTED,
        ],
        minimum_priority=NotificationPriority.MEDIUM,
    )


@pytest.fixture
def sample_discord_config():
    """Sample Discord config"""
    from app.models import DiscordConfig, DiscordDeliveryMethod, DiscordChannelConfig
    return DiscordConfig(
        enabled=True,
        delivery_method=DiscordDeliveryMethod.CHANNEL,
        channel_config=DiscordChannelConfig(
            guild_id="123456789",
            channel_id="987654321",
            guild_name="Test Server",
            channel_name="notifications",
        ),
    )


@pytest.fixture
def sample_device_stats():
    """Sample device stats for anomaly detection"""
    from app.services.anomaly_detector import DeviceStats, LatencyStats
    from datetime import datetime
    
    stats = DeviceStats(
        device_ip="192.168.1.100",
        device_name="Test Device",
    )
    stats.total_checks = 100
    stats.successful_checks = 95
    stats.failed_checks = 5
    stats.latency_stats.count = 95
    stats.latency_stats.mean = 25.0
    stats.latency_stats.m2 = 500.0  # For std_dev ~ 5
    stats.consecutive_successes = 10
    stats.first_seen = datetime.utcnow() - timedelta(days=7)
    stats.last_updated = datetime.utcnow()
    stats.last_state = "online"
    stats.last_check_time = datetime.utcnow()
    
    return stats


@pytest.fixture
def mock_resend():
    """Mock resend module"""
    mock = MagicMock()
    mock.Emails.send = MagicMock(return_value={"id": "email-123"})
    return mock


@pytest.fixture
def mock_discord_client():
    """Mock Discord client"""
    mock = AsyncMock()
    mock.user = MagicMock()
    mock.user.name = "Test Bot"
    mock.user.id = 123456789
    mock.guilds = []
    return mock


@pytest.fixture
def notification_manager_instance():
    """Fresh NotificationManager instance for testing"""
    from app.services.notification_manager import NotificationManager
    
    # Create fresh instance
    manager = NotificationManager()
    
    # Clear any loaded state
    manager._preferences.clear()
    manager._history.clear()
    manager._rate_limits.clear()
    manager._scheduled_broadcasts.clear()
    manager._silenced_devices.clear()
    
    yield manager


@pytest.fixture
def anomaly_detector_instance():
    """Fresh AnomalyDetector instance for testing"""
    from app.services.anomaly_detector import AnomalyDetector
    
    detector = AnomalyDetector()
    detector._device_stats.clear()
    detector._anomalies_detected = 0
    detector._false_positives = 0
    detector._notified_offline.clear()
    
    yield detector


@pytest.fixture
def version_checker_instance():
    """Fresh VersionChecker instance for testing"""
    from app.services.version_checker import VersionChecker
    
    checker = VersionChecker()
    checker._last_notified_version = None
    checker._last_check_time = None
    
    yield checker

