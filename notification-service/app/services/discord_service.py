"""
Discord notification service using Discord.py.

Handles Discord bot integration for sending notifications to channels and DMs.
"""

import asyncio
import logging
from datetime import datetime

from ..config import settings
from ..models import (
    DiscordBotInfo,
    DiscordChannel,
    DiscordChannelConfig,
    DiscordConfig,
    DiscordDeliveryMethod,
    DiscordGuild,
    NetworkEvent,
    NotificationChannel,
    NotificationPriority,
    NotificationRecord,
    NotificationType,
)
from ..utils import get_notification_icon, get_priority_color_discord

logger = logging.getLogger(__name__)

# Discord bot instance (singleton)
_discord_client = None
_bot_ready = asyncio.Event()


def is_discord_configured() -> bool:
    """Check if Discord bot is configured"""
    return settings.is_discord_configured


def get_bot_invite_url() -> str | None:
    """Generate Discord bot invite URL"""
    if not settings.discord_client_id:
        return None

    # Permissions needed:
    # - Send Messages (2048)
    # - Embed Links (16384)
    # - Read Message History (65536)
    # - View Channels (1024)
    permissions = 2048 + 16384 + 65536 + 1024

    return f"https://discord.com/api/oauth2/authorize?client_id={settings.discord_client_id}&permissions={permissions}&scope=bot"


def _build_discord_embed(event: NetworkEvent) -> dict[str, any]:
    """Build a Discord embed for a network event"""
    icon = get_notification_icon(event.event_type)
    color = get_priority_color_discord(event.priority)

    # Build embed
    embed = {
        "title": f"{icon} {event.title}",
        "description": event.message,
        "color": color,
        "timestamp": event.timestamp.isoformat(),
        "footer": {
            "text": f"Cartographer • Priority: {event.priority.value.upper()}",
        },
        "fields": [],
    }

    # Add device info fields
    if event.device_name or event.device_ip:
        device_value = ""
        if event.device_name:
            device_value += f"**Name:** {event.device_name}\n"
        if event.device_ip:
            device_value += f"**IP:** {event.device_ip}\n"
        if event.device_hostname:
            device_value += f"**Hostname:** {event.device_hostname}\n"

        embed["fields"].append(
            {
                "name": "🖥️ Device",
                "value": device_value.strip(),
                "inline": True,
            }
        )

    # Add state change info
    if event.previous_state or event.current_state:
        state_value = ""
        if event.previous_state:
            state_value += f"**From:** {event.previous_state}\n"
        if event.current_state:
            state_value += f"**To:** {event.current_state}\n"

        embed["fields"].append(
            {
                "name": "📊 State Change",
                "value": state_value.strip(),
                "inline": True,
            }
        )

    # Add anomaly score if present
    if event.anomaly_score is not None:
        anomaly_percent = int(event.anomaly_score * 100)
        embed["fields"].append(
            {
                "name": "🤖 Anomaly Detection",
                "value": f"Score: **{anomaly_percent}%**\nML-flagged: {'Yes' if event.is_predicted_anomaly else 'No'}",
                "inline": True,
            }
        )

    # Add extra details (limit to first 3 to avoid cluttering)
    if event.details:
        details_count = 0
        for key, value in event.details.items():
            if details_count >= 3:
                break
            display_key = key.replace("_", " ").title()
            embed["fields"].append(
                {
                    "name": display_key,
                    "value": str(value),
                    "inline": True,
                }
            )
            details_count += 1

    return embed


class DiscordNotificationService:
    """Service for sending Discord notifications"""

    def __init__(self):
        self._client = None
        self._ready = asyncio.Event()
        self._running = False

    async def start(self) -> bool:
        """Start the Discord bot"""
        if not is_discord_configured():
            logger.warning("Discord bot not configured - DISCORD_BOT_TOKEN not set")
            return False

        if self._running:
            logger.info("Discord bot already running")
            return True

        try:
            import discord
            from discord import Intents

            intents = Intents.default()
            intents.guilds = True
            intents.messages = True

            self._client = discord.Client(intents=intents)

            @self._client.event
            async def on_ready():
                logger.info(f"Discord bot connected as {self._client.user}")
                self._ready.set()

            # Start bot in background task
            asyncio.create_task(self._run_bot())
            self._running = True

            # Wait for bot to be ready (with timeout)
            try:
                await asyncio.wait_for(self._ready.wait(), timeout=30.0)
                return True
            except asyncio.TimeoutError:
                logger.error("Discord bot failed to connect within timeout")
                return False

        except ImportError:
            logger.error("discord.py not installed")
            return False
        except Exception as e:
            logger.error(f"Failed to start Discord bot: {e}")
            return False

    async def _run_bot(self):
        """Run the Discord bot"""
        try:
            await self._client.start(settings.discord_bot_token)
        except Exception as e:
            logger.error(f"Discord bot error: {e}")
            self._running = False

    async def stop(self):
        """Stop the Discord bot"""
        if self._client:
            await self._client.close()
            self._client = None
            self._running = False
            self._ready.clear()

    def get_bot_info(self) -> DiscordBotInfo:
        """Get information about the Discord bot"""
        info = DiscordBotInfo(
            invite_url=get_bot_invite_url(),
        )

        if self._client and self._ready.is_set():
            info.is_connected = True
            info.bot_name = str(self._client.user.name) if self._client.user else "Cartographer Bot"
            info.bot_id = str(self._client.user.id) if self._client.user else None
            info.connected_guilds = len(self._client.guilds)

        return info

    async def get_guilds(self) -> list[DiscordGuild]:
        """Get list of guilds the bot is in"""
        if not self._client or not self._ready.is_set():
            return []

        guilds = []
        for guild in self._client.guilds:
            guilds.append(
                DiscordGuild(
                    id=str(guild.id),
                    name=guild.name,
                    icon_url=str(guild.icon.url) if guild.icon else None,
                    member_count=guild.member_count,
                )
            )

        return guilds

    async def get_channels(self, guild_id: str) -> list[DiscordChannel]:
        """Get list of text channels in a guild"""
        if not self._client or not self._ready.is_set():
            return []

        import discord

        guild = self._client.get_guild(int(guild_id))
        if not guild:
            return []

        channels = []
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel):
                channels.append(
                    DiscordChannel(
                        id=str(channel.id),
                        name=channel.name,
                        type="text",
                    )
                )

        return sorted(channels, key=lambda c: c.name)

    async def send_notification(
        self,
        config: DiscordConfig,
        event: NetworkEvent,
        notification_id: str,
    ) -> NotificationRecord:
        """Send a notification via Discord"""
        record = NotificationRecord(
            notification_id=notification_id,
            event_id=event.event_id,
            network_id=event.network_id,
            channel=NotificationChannel.DISCORD,
            title=event.title,
            message=event.message,
            priority=event.priority,
            success=False,
        )

        if not is_discord_configured():
            record.error_message = "Discord not configured - DISCORD_BOT_TOKEN not set"
            return record

        if not self._client or not self._ready.is_set():
            record.error_message = "Discord bot not connected"
            return record

        try:
            import discord

            embed_data = _build_discord_embed(event)
            embed = discord.Embed.from_dict(embed_data)

            # Add link button
            view = discord.ui.View()
            view.add_item(
                discord.ui.Button(
                    label="View Network Map",
                    url=settings.application_url,
                    style=discord.ButtonStyle.link,
                )
            )

            if config.delivery_method == DiscordDeliveryMethod.CHANNEL:
                if not config.channel_config:
                    record.error_message = "No channel configured"
                    return record

                channel = self._client.get_channel(int(config.channel_config.channel_id))
                if not channel:
                    record.error_message = f"Channel {config.channel_config.channel_id} not found"
                    return record

                await channel.send(embed=embed, view=view)
                record.success = True
                logger.info(
                    f"Discord notification sent to channel {config.channel_config.channel_id}"
                )

            elif config.delivery_method == DiscordDeliveryMethod.DM:
                if not config.discord_user_id:
                    record.error_message = "No Discord user ID configured for DM"
                    return record

                user = await self._client.fetch_user(int(config.discord_user_id))
                if not user:
                    record.error_message = f"Discord user {config.discord_user_id} not found"
                    return record

                await user.send(embed=embed, view=view)
                record.success = True
                logger.info(f"Discord DM notification sent to user {config.discord_user_id}")

        except Exception as e:
            record.error_message = str(e)
            logger.error(f"Failed to send Discord notification: {e}")

        return record

    async def send_test_notification(self, config: DiscordConfig) -> dict[str, any]:
        """Send a test notification via Discord"""
        test_event = NetworkEvent(
            event_id="test-event",
            event_type=NotificationType.SYSTEM_STATUS,
            priority=NotificationPriority.LOW,
            title="Test Notification",
            message="This is a test notification from Cartographer. If you see this message, your Discord notification settings are working correctly!",
            details={
                "test": True,
                "sent_at": datetime.utcnow().isoformat(),
            },
        )

        record = await self.send_notification(config, test_event, "test-notification")

        return {
            "success": record.success,
            "error": record.error_message,
        }


# Singleton instance
discord_service = DiscordNotificationService()


async def send_discord_notification(
    config: DiscordConfig,
    event: NetworkEvent,
    notification_id: str,
    user_id: str = "",
) -> NotificationRecord:
    """
    Convenience function to send Discord notification.

    Note: user_id parameter is accepted for API compatibility but is not used.
    The Discord service uses config.discord_user_id from the config instead.
    """
    return await discord_service.send_notification(config, event, notification_id)


async def send_test_discord(config: DiscordConfig) -> dict[str, any]:
    """Convenience function to send test Discord notification"""
    return await discord_service.send_test_notification(config)


async def send_discord_dm(
    discord_user_id: str,
    event: NetworkEvent,
    notification_id: str,
) -> NotificationRecord:
    """
    Send a Discord DM directly to a user by their Discord user ID.
    Used for per-user notifications.
    """
    from ..models import DiscordConfig, DiscordDeliveryMethod

    # Create a temporary config for DM delivery
    config = DiscordConfig(
        enabled=True,
        delivery_method=DiscordDeliveryMethod.DM,
        discord_user_id=discord_user_id,
    )

    return await discord_service.send_notification(config, event, notification_id)
