"""
Unit tests for Discord service.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import (
    DiscordChannelConfig,
    DiscordConfig,
    DiscordDeliveryMethod,
    NetworkEvent,
    NotificationChannel,
    NotificationPriority,
    NotificationType,
)
from app.services.discord_service import (
    DiscordNotificationService,
    _build_discord_embed,
    discord_service,
    get_bot_invite_url,
    is_discord_configured,
    send_discord_notification,
    send_test_discord,
)
from app.utils import get_notification_icon, get_priority_color_discord


class TestDiscordConfiguration:
    """Tests for Discord configuration"""

    def test_is_discord_configured_false(self):
        """Should return False when no token"""
        with patch("app.services.discord_service.settings.discord_bot_token", ""):
            assert is_discord_configured() is False

    def test_is_discord_configured_true(self):
        """Should return True when token set"""
        with patch("app.services.discord_service.settings.discord_bot_token", "test-token"):
            assert is_discord_configured() is True

    def test_get_bot_invite_url_no_client_id(self):
        """Should return None when no client ID"""
        with patch("app.services.discord_service.settings.discord_client_id", ""):
            assert get_bot_invite_url() is None

    def test_get_bot_invite_url_success(self):
        """Should generate invite URL"""
        with patch("app.services.discord_service.settings.discord_client_id", "123456789"):
            url = get_bot_invite_url()

        assert url is not None
        assert "123456789" in url
        assert url.startswith("https://discord.com/")


class TestDiscordHelpers:
    """Tests for Discord helper functions"""

    def test_get_priority_color(self):
        """Should return correct colors"""
        assert get_priority_color_discord(NotificationPriority.LOW) == 0x64748B
        assert get_priority_color_discord(NotificationPriority.CRITICAL) == 0xEF4444

    def test_get_notification_icon(self):
        """Should return correct icons"""
        assert get_notification_icon(NotificationType.DEVICE_OFFLINE) == "🔴"
        assert get_notification_icon(NotificationType.DEVICE_ONLINE) == "🟢"


class TestDiscordEmbed:
    """Tests for Discord embed generation"""

    def test_build_embed_basic(self):
        """Should build basic embed"""
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            priority=NotificationPriority.HIGH,
            title="Test Event",
            message="Test message",
        )

        embed = _build_discord_embed(event)

        assert "Test Event" in embed["title"]
        assert embed["description"] == "Test message"

    def test_build_embed_with_device(self):
        """Should include device info"""
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            title="Test",
            message="Test",
            device_ip="192.168.1.100",
            device_name="Test Device",
        )

        embed = _build_discord_embed(event)

        device_field = next(f for f in embed["fields"] if "Device" in f["name"])
        assert "192.168.1.100" in device_field["value"]
        assert "Test Device" in device_field["value"]

    def test_build_embed_with_state_change(self):
        """Should include state change info"""
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            title="Test",
            message="Test",
            previous_state="online",
            current_state="offline",
        )

        embed = _build_discord_embed(event)

        state_field = next(f for f in embed["fields"] if "State" in f["name"])
        assert "online" in state_field["value"]
        assert "offline" in state_field["value"]

    def test_build_embed_with_anomaly(self):
        """Should include anomaly info"""
        event = NetworkEvent(
            event_type=NotificationType.ANOMALY_DETECTED,
            title="Test",
            message="Test",
            anomaly_score=0.85,
            is_predicted_anomaly=True,
        )

        embed = _build_discord_embed(event)

        anomaly_field = next(f for f in embed["fields"] if "Anomaly" in f["name"])
        assert "85%" in anomaly_field["value"]


class TestDiscordNotificationService:
    """Tests for DiscordNotificationService class"""

    def test_init(self):
        """Should initialize correctly"""
        service = DiscordNotificationService()

        assert service._client is None
        assert service._running is False

    async def test_start_not_configured(self):
        """Should fail when not configured"""
        service = DiscordNotificationService()

        with patch("app.services.discord_service.settings.discord_bot_token", ""):
            result = await service.start()

        assert result is False

    async def test_start_already_running(self):
        """Should return True if already running"""
        service = DiscordNotificationService()
        service._running = True

        with patch("app.services.discord_service.is_discord_configured", return_value=True):
            result = await service.start()

        assert result is True

    async def test_stop(self):
        """Should stop service"""
        service = DiscordNotificationService()
        service._client = AsyncMock()
        service._running = True

        await service.stop()

        assert service._client is None
        assert service._running is False

    def test_get_bot_info_not_connected(self):
        """Should return basic info when not connected"""
        service = DiscordNotificationService()

        info = service.get_bot_info()

        assert info.is_connected is False

    def test_get_bot_info_connected(self):
        """Should return full info when connected"""
        service = DiscordNotificationService()
        service._ready = asyncio.Event()
        service._ready.set()
        service._client = MagicMock()
        service._client.user = MagicMock()
        service._client.user.name = "Test Bot"
        service._client.user.id = 123456
        service._client.guilds = [MagicMock(), MagicMock()]

        info = service.get_bot_info()

        assert info.is_connected is True
        assert info.connected_guilds == 2

    async def test_get_guilds_not_connected(self):
        """Should return empty list when not connected"""
        service = DiscordNotificationService()

        guilds = await service.get_guilds()

        assert guilds == []

    async def test_get_channels_not_connected(self):
        """Should return empty list when not connected"""
        service = DiscordNotificationService()

        channels = await service.get_channels("123")

        assert channels == []

    async def test_send_notification_not_configured(self):
        """Should fail when not configured"""
        service = DiscordNotificationService()

        config = DiscordConfig(enabled=True)
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE, title="Test", message="Test"
        )

        with patch("app.services.discord_service.settings.discord_bot_token", ""):
            record = await service.send_notification(config, event, "notif-123")

        assert record.success is False

    async def test_send_notification_not_connected(self):
        """Should fail when not connected"""
        service = DiscordNotificationService()

        config = DiscordConfig(enabled=True)
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE, title="Test", message="Test"
        )

        with patch("app.services.discord_service.settings.discord_bot_token", "test-token"):
            record = await service.send_notification(config, event, "notif-123")

        assert record.success is False
        assert "not connected" in record.error_message.lower()

    async def test_send_notification_no_channel_config(self):
        """Should fail when no channel configured"""
        service = DiscordNotificationService()
        service._client = MagicMock()
        service._ready = asyncio.Event()
        service._ready.set()

        config = DiscordConfig(
            enabled=True, delivery_method=DiscordDeliveryMethod.CHANNEL, channel_config=None
        )
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE, title="Test", message="Test"
        )

        with patch("app.services.discord_service.settings.discord_bot_token", "test-token"):
            record = await service.send_notification(config, event, "notif-123")

        assert record.success is False
        assert "no channel" in record.error_message.lower()

    async def test_send_notification_dm_no_user(self):
        """Should fail when DM with no user ID"""
        service = DiscordNotificationService()
        service._client = MagicMock()
        service._ready = asyncio.Event()
        service._ready.set()

        config = DiscordConfig(
            enabled=True, delivery_method=DiscordDeliveryMethod.DM, discord_user_id=None
        )
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE, title="Test", message="Test"
        )

        with patch("app.services.discord_service.settings.discord_bot_token", "test-token"):
            record = await service.send_notification(config, event, "notif-123")

        assert record.success is False

    async def test_send_test_notification(self):
        """Should send test notification"""
        service = DiscordNotificationService()

        config = DiscordConfig(enabled=True)

        with patch.object(service, "send_notification") as mock_send:
            mock_send.return_value = MagicMock(success=True, error_message=None)

            result = await service.send_test_notification(config)

        assert result["success"] is True


class TestConvenienceFunctions:
    """Tests for convenience functions"""

    async def test_send_discord_notification(self):
        """Should call service send_notification"""
        config = DiscordConfig(enabled=True)
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE, title="Test", message="Test"
        )

        with patch.object(discord_service, "send_notification", AsyncMock()) as mock_send:
            await send_discord_notification(config, event, "notif-123")

        mock_send.assert_called_once()

    async def test_send_test_discord(self):
        """Should call service send_test_notification"""
        config = DiscordConfig(enabled=True)

        with patch.object(discord_service, "send_test_notification", AsyncMock()) as mock_send:
            await send_test_discord(config)

        mock_send.assert_called_once()


class TestDiscordServiceSendToChannel:
    """Tests for sending messages to channels"""

    async def test_send_to_channel_success(self):
        """Should send message to channel successfully"""
        service = DiscordNotificationService()
        service._ready = asyncio.Event()
        service._ready.set()

        mock_client = MagicMock()
        mock_channel = MagicMock()
        mock_channel.send = AsyncMock()
        mock_client.get_channel.return_value = mock_channel
        service._client = mock_client

        config = DiscordConfig(
            enabled=True,
            delivery_method=DiscordDeliveryMethod.CHANNEL,
            channel_config=DiscordChannelConfig(
                guild_id="123456789012345678",  # Discord IDs are numeric
                channel_id="987654321098765432",
            ),
        )
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE, title="Test", message="Test message"
        )

        with patch("app.services.discord_service.settings.discord_bot_token", "test-token"):
            record = await service.send_notification(config, event, "notif-123")

        assert record.success is True

    async def test_send_to_channel_not_found(self):
        """Should fail when channel not found"""
        service = DiscordNotificationService()
        service._ready = asyncio.Event()
        service._ready.set()

        mock_client = MagicMock()
        mock_client.get_channel.return_value = None  # Channel not found
        service._client = mock_client

        config = DiscordConfig(
            enabled=True,
            delivery_method=DiscordDeliveryMethod.CHANNEL,
            channel_config=DiscordChannelConfig(
                guild_id="123456789012345678", channel_id="987654321098765432"
            ),
        )
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE, title="Test", message="Test message"
        )

        with patch("app.services.discord_service.settings.discord_bot_token", "test-token"):
            record = await service.send_notification(config, event, "notif-123")

        assert record.success is False


class TestDiscordServiceSendDM:
    """Tests for sending DMs"""

    async def test_send_dm_user_not_found(self):
        """Should fail when user not found"""
        service = DiscordNotificationService()
        service._ready = asyncio.Event()
        service._ready.set()

        mock_client = MagicMock()
        mock_client.get_user.return_value = None
        mock_client.fetch_user = AsyncMock(side_effect=Exception("User not found"))
        service._client = mock_client

        config = DiscordConfig(
            enabled=True,
            delivery_method=DiscordDeliveryMethod.DM,
            discord_user_id="123456789012345678",
        )
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE, title="Test", message="Test message"
        )

        with patch("app.services.discord_service.settings.discord_bot_token", "test-token"):
            record = await service.send_notification(config, event, "notif-123")

        assert record.success is False
