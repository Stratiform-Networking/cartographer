"""
Unit tests for notification service models.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models import (
    DEFAULT_NOTIFICATION_TYPE_PRIORITIES,
    AnomalyDetectionResult,
    AnomalyType,
    DeviceBaseline,
    DiscordBotInfo,
    DiscordChannel,
    DiscordChannelConfig,
    DiscordChannelsResponse,
    DiscordConfig,
    DiscordDeliveryMethod,
    DiscordGuild,
    DiscordGuildsResponse,
    DiscordOAuthState,
    DiscordUserInfo,
    EmailConfig,
    MLModelStatus,
    NetworkEvent,
    NotificationChannel,
    NotificationHistoryResponse,
    NotificationPreferences,
    NotificationPreferencesUpdate,
    NotificationPriority,
    NotificationRecord,
    NotificationStatsResponse,
    NotificationType,
    ScheduledBroadcast,
    ScheduledBroadcastCreate,
    ScheduledBroadcastResponse,
    ScheduledBroadcastStatus,
    TestNotificationRequest,
    TestNotificationResponse,
    get_default_priority_for_type,
)


class TestEnums:
    """Tests for enum types"""

    def test_notification_channel_values(self):
        """Should have expected channel values"""
        assert NotificationChannel.EMAIL.value == "email"
        assert NotificationChannel.DISCORD.value == "discord"

    def test_notification_priority_values(self):
        """Should have expected priority values"""
        assert NotificationPriority.LOW.value == "low"
        assert NotificationPriority.MEDIUM.value == "medium"
        assert NotificationPriority.HIGH.value == "high"
        assert NotificationPriority.CRITICAL.value == "critical"

    def test_notification_type_values(self):
        """Should have expected type values"""
        assert NotificationType.DEVICE_ADDED.value == "device_added"
        assert NotificationType.DEVICE_REMOVED.value == "device_removed"
        assert NotificationType.DEVICE_OFFLINE.value == "device_offline"
        assert NotificationType.DEVICE_ONLINE.value == "device_online"
        assert NotificationType.ANOMALY_DETECTED.value == "anomaly_detected"
        assert NotificationType.CARTOGRAPHER_UP.value == "cartographer_up"

    def test_discord_delivery_method_values(self):
        """Should have expected delivery method values"""
        assert DiscordDeliveryMethod.CHANNEL.value == "channel"
        assert DiscordDeliveryMethod.DM.value == "dm"

    def test_anomaly_type_values(self):
        """Should have expected anomaly type values"""
        assert AnomalyType.UNEXPECTED_OFFLINE.value == "unexpected_offline"
        assert AnomalyType.UNUSUAL_LATENCY_SPIKE.value == "unusual_latency_spike"

    def test_scheduled_broadcast_status_values(self):
        """Should have expected status values"""
        assert ScheduledBroadcastStatus.PENDING.value == "pending"
        assert ScheduledBroadcastStatus.SENT.value == "sent"
        assert ScheduledBroadcastStatus.CANCELLED.value == "cancelled"


class TestEmailConfig:
    """Tests for EmailConfig model"""

    def test_email_config_default(self):
        """Should have default values"""
        config = EmailConfig()
        assert config.enabled is False
        assert config.email_address == ""

    def test_email_config_valid_email(self):
        """Should accept valid email"""
        config = EmailConfig(enabled=True, email_address="test@example.com")
        assert config.email_address == "test@example.com"

    def test_email_config_invalid_email(self):
        """Should reject invalid email"""
        with pytest.raises(ValidationError):
            EmailConfig(enabled=True, email_address="not-an-email")


class TestDiscordConfig:
    """Tests for Discord configuration models"""

    def test_discord_channel_config(self):
        """Should create channel config"""
        config = DiscordChannelConfig(
            guild_id="123", channel_id="456", guild_name="Test Server", channel_name="notifications"
        )
        assert config.guild_id == "123"
        assert config.channel_id == "456"

    def test_discord_config_default(self):
        """Should have default values"""
        config = DiscordConfig()
        assert config.enabled is False
        assert config.delivery_method == DiscordDeliveryMethod.CHANNEL

    def test_discord_config_with_channel(self, sample_discord_config):
        """Should accept channel config"""
        assert sample_discord_config.enabled is True
        assert sample_discord_config.channel_config.guild_id == "123456789"


class TestNotificationPreferences:
    """Tests for NotificationPreferences model"""

    def test_notification_preferences_default(self):
        """Should have default values"""
        prefs = NotificationPreferences(network_id="test-network-uuid")
        assert prefs.enabled is True
        assert prefs.email.enabled is False
        assert prefs.discord.enabled is False
        assert prefs.minimum_priority == NotificationPriority.MEDIUM

    def test_notification_preferences_enabled_types(self):
        """Should have default enabled notification types"""
        prefs = NotificationPreferences(network_id="test-network-uuid")
        assert NotificationType.DEVICE_ADDED in prefs.enabled_notification_types
        assert NotificationType.DEVICE_REMOVED in prefs.enabled_notification_types
        assert NotificationType.DEVICE_OFFLINE in prefs.enabled_notification_types
        assert NotificationType.CARTOGRAPHER_UP in prefs.enabled_notification_types
        assert prefs.enabled_notification_types[-2] == NotificationType.DEVICE_ADDED
        assert prefs.enabled_notification_types[-1] == NotificationType.DEVICE_REMOVED

    def test_default_priority_for_device_added_removed(self):
        """Device add/remove defaults should be high priority."""
        assert (
            get_default_priority_for_type(NotificationType.DEVICE_ADDED)
            == NotificationPriority.HIGH
        )
        assert (
            get_default_priority_for_type(NotificationType.DEVICE_REMOVED)
            == NotificationPriority.HIGH
        )

    def test_get_effective_priority_default(self):
        """Should return default priority when no override"""
        prefs = NotificationPreferences(network_id="test-network-uuid")
        priority = prefs.get_effective_priority(NotificationType.DEVICE_OFFLINE)
        assert priority == NotificationPriority.HIGH

    def test_get_effective_priority_override(self):
        """Should return user override priority"""
        prefs = NotificationPreferences(
            network_id="test-network-uuid",
            notification_type_priorities={
                NotificationType.DEVICE_OFFLINE: NotificationPriority.LOW
            },
        )
        priority = prefs.get_effective_priority(NotificationType.DEVICE_OFFLINE)
        assert priority == NotificationPriority.LOW


class TestNotificationPreferencesUpdate:
    """Tests for NotificationPreferencesUpdate model"""

    def test_update_all_optional(self):
        """Should allow all fields optional"""
        update = NotificationPreferencesUpdate()
        assert update.enabled is None
        assert update.email is None

    def test_update_with_values(self):
        """Should accept update values"""
        update = NotificationPreferencesUpdate(
            enabled=False, minimum_priority=NotificationPriority.HIGH
        )
        assert update.enabled is False
        assert update.minimum_priority == NotificationPriority.HIGH


class TestNetworkEvent:
    """Tests for NetworkEvent model"""

    def test_network_event_required_fields(self):
        """Should require essential fields"""
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE, title="Test Event", message="Test message"
        )
        assert event.event_type == NotificationType.DEVICE_OFFLINE
        assert event.priority == NotificationPriority.MEDIUM

    def test_network_event_with_device_info(self, sample_network_event):
        """Should accept device information"""
        assert sample_network_event.device_ip == "192.168.1.100"
        assert sample_network_event.device_name == "Test Device"

    def test_network_event_anomaly_fields(self):
        """Should accept anomaly fields"""
        event = NetworkEvent(
            event_type=NotificationType.ANOMALY_DETECTED,
            title="Anomaly",
            message="Anomaly detected",
            anomaly_score=0.85,
            is_predicted_anomaly=True,
            ml_model_version="1.0.0",
        )
        assert event.anomaly_score == 0.85
        assert event.is_predicted_anomaly is True


class TestNotificationRecord:
    """Tests for NotificationRecord model"""

    def test_notification_record(self):
        """Should create notification record"""
        record = NotificationRecord(
            notification_id="notif-123",
            event_id="event-123",
            network_id="network-uuid-123",
            channel=NotificationChannel.EMAIL,
            success=True,
            title="Test",
            message="Test message",
            priority=NotificationPriority.HIGH,
        )
        assert record.success is True
        assert record.channel == NotificationChannel.EMAIL


class TestDiscordModels:
    """Tests for Discord-related models"""

    def test_discord_bot_info(self):
        """Should create bot info"""
        info = DiscordBotInfo(is_connected=True, connected_guilds=5)
        assert info.bot_name == "Cartographer Bot"
        assert info.is_connected is True

    def test_discord_guild(self):
        """Should create guild info"""
        guild = DiscordGuild(id="123", name="Test Server")
        assert guild.id == "123"

    def test_discord_channel(self):
        """Should create channel info"""
        channel = DiscordChannel(id="456", name="general", type="text")
        assert channel.type == "text"

    def test_discord_guilds_response(self):
        """Should create guilds response"""
        response = DiscordGuildsResponse(guilds=[])
        assert len(response.guilds) == 0

    def test_discord_channels_response(self):
        """Should create channels response"""
        response = DiscordChannelsResponse(guild_id="123", channels=[])
        assert response.guild_id == "123"


class TestAnomalyDetectionModels:
    """Tests for anomaly detection models"""

    def test_device_baseline(self):
        """Should create device baseline"""
        baseline = DeviceBaseline(device_ip="192.168.1.1", avg_latency_ms=25.0, check_count=100)
        assert baseline.device_ip == "192.168.1.1"
        assert baseline.model_version == "1.0.0"

    def test_anomaly_detection_result(self):
        """Should create detection result"""
        result = AnomalyDetectionResult(
            is_anomaly=True,
            anomaly_score=0.75,
            anomaly_type=AnomalyType.UNUSUAL_LATENCY_SPIKE,
            reason="High latency detected",
        )
        assert result.is_anomaly is True
        assert result.confidence == 0.5  # Default

    def test_ml_model_status(self):
        """Should create model status"""
        status = MLModelStatus(
            model_version="1.0.0",
            samples_count=1000,
            devices_tracked=10,
            is_trained=True,
            is_online_learning=True,
            training_status="online_learning",
        )
        assert status.is_trained is True
        assert status.is_online_learning is True
        assert status.training_status == "online_learning"


class TestScheduledBroadcastModels:
    """Tests for scheduled broadcast models"""

    def test_scheduled_broadcast(self):
        """Should create scheduled broadcast"""
        broadcast = ScheduledBroadcast(
            id="broadcast-123",
            title="Maintenance Notice",
            message="System maintenance scheduled",
            network_id="network-uuid-123",
            scheduled_at=datetime.utcnow(),
            created_by="admin",
        )
        assert broadcast.status == ScheduledBroadcastStatus.PENDING

    def test_scheduled_broadcast_create(self):
        """Should create broadcast request"""
        request = ScheduledBroadcastCreate(
            title="Test",
            message="Test broadcast",
            network_id="network-uuid-123",
            scheduled_at=datetime.utcnow(),
        )
        assert request.event_type == NotificationType.SCHEDULED_MAINTENANCE

    def test_scheduled_broadcast_response(self):
        """Should create response"""
        response = ScheduledBroadcastResponse(broadcasts=[], total_count=0)
        assert response.total_count == 0


class TestApiModels:
    """Tests for API request/response models"""

    def test_test_notification_request(self):
        """Should create test request"""
        request = TestNotificationRequest(channel=NotificationChannel.EMAIL)
        assert request.channel == NotificationChannel.EMAIL
        assert "test notification" in request.message.lower()

    def test_test_notification_response(self):
        """Should create test response"""
        response = TestNotificationResponse(
            success=True, channel=NotificationChannel.EMAIL, message="Sent"
        )
        assert response.success is True

    def test_notification_stats_response(self):
        """Should create stats response"""
        stats = NotificationStatsResponse()
        assert stats.total_sent_24h == 0
        assert stats.success_rate == 1.0


class TestDefaultPriorities:
    """Tests for default priority mappings"""

    def test_default_priorities_defined(self):
        """Should have default priorities for all types"""
        for notification_type in NotificationType:
            assert notification_type in DEFAULT_NOTIFICATION_TYPE_PRIORITIES

    def test_get_default_priority_known_type(self):
        """Should return correct default priority"""
        priority = get_default_priority_for_type(NotificationType.DEVICE_OFFLINE)
        assert priority == NotificationPriority.HIGH

    def test_security_alert_is_critical(self):
        """Security alerts should be critical priority"""
        priority = get_default_priority_for_type(NotificationType.SECURITY_ALERT)
        assert priority == NotificationPriority.CRITICAL
