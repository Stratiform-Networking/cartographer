"""
Notification settings Pydantic schemas.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EmailConfigCreate(BaseModel):
    """Email notification configuration."""

    enabled: bool = False
    email_address: str | None = None


class DiscordConfigCreate(BaseModel):
    """Discord notification configuration."""

    enabled: bool = False
    delivery_method: str = "channel"  # "channel" or "dm"
    discord_user_id: str | None = None
    guild_id: str | None = None
    channel_id: str | None = None


class NotificationPreferencesCreate(BaseModel):
    """Notification preferences configuration."""

    enabled_types: list[str] = Field(
        default_factory=lambda: [
            "device_offline",
            "device_online",
            "device_degraded",
            "anomaly_detected",
            "high_latency",
            "packet_loss",
            "security_alert",
            "cartographer_down",
            "cartographer_up",
            "device_added",
            "device_removed",
        ]
    )
    minimum_priority: str = "medium"  # low, medium, high, critical
    quiet_hours_enabled: bool = False
    quiet_hours_start: str | None = None  # HH:MM format
    quiet_hours_end: str | None = None
    quiet_hours_bypass_priority: str | None = None
    timezone: str | None = None
    max_notifications_per_hour: int = 10


class NetworkNotificationSettingsCreate(BaseModel):
    """Create/update network notification settings."""

    enabled: bool = True
    email: EmailConfigCreate | None = None
    discord: DiscordConfigCreate | None = None
    preferences: NotificationPreferencesCreate | None = None


class NetworkNotificationSettingsResponse(BaseModel):
    """Network notification settings response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    network_id: str  # UUID string
    enabled: bool
    email_enabled: bool
    email_address: str | None
    discord_enabled: bool
    discord_config: dict | None
    preferences: dict | None
    created_at: datetime
    updated_at: datetime
