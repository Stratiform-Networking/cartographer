"""
Pydantic models for the Notification Service.

These models define notification preferences, events, and channel configurations.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# ==================== Notification Channels ====================


class NotificationChannel(str, Enum):
    """Available notification channels"""

    EMAIL = "email"
    DISCORD = "discord"


class NotificationPriority(str, Enum):
    """Notification priority levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationType(str, Enum):
    """Types of notifications that can be sent"""

    DEVICE_OFFLINE = "device_offline"
    DEVICE_ONLINE = "device_online"
    DEVICE_DEGRADED = "device_degraded"
    ANOMALY_DETECTED = "anomaly_detected"
    HIGH_LATENCY = "high_latency"
    PACKET_LOSS = "packet_loss"
    ISP_ISSUE = "isp_issue"
    SECURITY_ALERT = "security_alert"
    SCHEDULED_MAINTENANCE = "scheduled_maintenance"
    SYSTEM_STATUS = "system_status"
    CARTOGRAPHER_DOWN = "cartographer_down"
    CARTOGRAPHER_UP = "cartographer_up"
    MASS_OUTAGE = "mass_outage"
    MASS_RECOVERY = "mass_recovery"


# ==================== Email Configuration ====================


class EmailConfig(BaseModel):
    """Email notification configuration"""

    enabled: bool = False
    email_address: str = ""

    @field_validator("email_address")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if v and "@" not in v:
            raise ValueError("Invalid email address")
        return v


# ==================== Discord Configuration ====================


class DiscordDeliveryMethod(str, Enum):
    """How Discord notifications are delivered"""

    CHANNEL = "channel"  # Send to a server channel
    DM = "dm"  # Send direct message to user


class DiscordChannelConfig(BaseModel):
    """Discord channel configuration"""

    guild_id: str = Field(..., description="Discord server (guild) ID")
    channel_id: str = Field(..., description="Discord channel ID to send notifications to")
    guild_name: Optional[str] = None
    channel_name: Optional[str] = None


class DiscordConfig(BaseModel):
    """Discord notification configuration"""

    enabled: bool = False
    delivery_method: DiscordDeliveryMethod = DiscordDeliveryMethod.CHANNEL
    discord_user_id: Optional[str] = None  # For DM delivery
    channel_config: Optional[DiscordChannelConfig] = None  # For channel delivery


# ==================== Default Notification Type Priorities ====================

# These are the default priorities for each notification type
# Users can override these per notification type
DEFAULT_NOTIFICATION_TYPE_PRIORITIES: Dict[NotificationType, NotificationPriority] = {
    NotificationType.DEVICE_OFFLINE: NotificationPriority.HIGH,
    NotificationType.DEVICE_ONLINE: NotificationPriority.LOW,
    NotificationType.DEVICE_DEGRADED: NotificationPriority.MEDIUM,
    NotificationType.ANOMALY_DETECTED: NotificationPriority.HIGH,
    NotificationType.HIGH_LATENCY: NotificationPriority.MEDIUM,
    NotificationType.PACKET_LOSS: NotificationPriority.MEDIUM,
    NotificationType.ISP_ISSUE: NotificationPriority.HIGH,
    NotificationType.SECURITY_ALERT: NotificationPriority.CRITICAL,
    NotificationType.SCHEDULED_MAINTENANCE: NotificationPriority.LOW,
    NotificationType.SYSTEM_STATUS: NotificationPriority.LOW,
    NotificationType.CARTOGRAPHER_DOWN: NotificationPriority.CRITICAL,
    NotificationType.CARTOGRAPHER_UP: NotificationPriority.MEDIUM,
    NotificationType.MASS_OUTAGE: NotificationPriority.HIGH,
    NotificationType.MASS_RECOVERY: NotificationPriority.LOW,
}


def get_default_priority_for_type(notification_type: NotificationType) -> NotificationPriority:
    """Get the default priority for a notification type"""
    return DEFAULT_NOTIFICATION_TYPE_PRIORITIES.get(notification_type, NotificationPriority.MEDIUM)


# ==================== User Notification Preferences ====================


class NotificationPreferences(BaseModel):
    """Network's notification preferences (per-network settings)"""

    # Network identification - notifications are scoped per-network
    network_id: str  # UUID string
    network_name: Optional[str] = None  # For display purposes

    # Owner's user_id for system-wide notifications (cartographer up/down)
    owner_user_id: Optional[str] = None

    enabled: bool = True  # Master switch for notifications

    # Channel configurations
    email: EmailConfig = Field(default_factory=EmailConfig)
    discord: DiscordConfig = Field(default_factory=DiscordConfig)

    # Event type filters (which types of notifications to receive)
    # Default includes most notification types - users can disable specific ones
    enabled_notification_types: List[NotificationType] = Field(
        default_factory=lambda: [
            NotificationType.DEVICE_OFFLINE,
            NotificationType.DEVICE_ONLINE,
            NotificationType.DEVICE_DEGRADED,
            NotificationType.ANOMALY_DETECTED,
            NotificationType.HIGH_LATENCY,
            NotificationType.PACKET_LOSS,
            NotificationType.ISP_ISSUE,
            NotificationType.SECURITY_ALERT,
            NotificationType.SCHEDULED_MAINTENANCE,
            NotificationType.SYSTEM_STATUS,
            NotificationType.CARTOGRAPHER_DOWN,
            NotificationType.CARTOGRAPHER_UP,
            NotificationType.MASS_OUTAGE,
            NotificationType.MASS_RECOVERY,
        ]
    )

    # Minimum priority level to notify (ignore lower priority)
    minimum_priority: NotificationPriority = NotificationPriority.MEDIUM

    # Per-notification-type priority overrides
    # Users can customize the priority of specific notification types
    # If not set for a type, the default priority will be used
    notification_type_priorities: Dict[NotificationType, NotificationPriority] = Field(
        default_factory=dict
    )

    # Quiet hours (don't send notifications during these times)
    quiet_hours_enabled: bool = False
    quiet_hours_start: Optional[str] = None  # HH:MM format
    quiet_hours_end: Optional[str] = None  # HH:MM format
    # Allow high-priority alerts to bypass quiet hours
    # If set, notifications with this priority or higher will still be sent during quiet hours
    # None means no pass-through (all notifications blocked during quiet hours)
    quiet_hours_bypass_priority: Optional[NotificationPriority] = None
    # User's timezone for quiet hours calculation (IANA timezone name, e.g., "America/New_York")
    # If not set, falls back to server's local time (which may cause issues in Docker)
    timezone: Optional[str] = None

    # Rate limiting
    max_notifications_per_hour: int = 10

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def get_effective_priority(self, notification_type: NotificationType) -> NotificationPriority:
        """
        Get the effective priority for a notification type.
        Returns user's custom priority if set, otherwise the default.
        """
        if notification_type in self.notification_type_priorities:
            return self.notification_type_priorities[notification_type]
        return get_default_priority_for_type(notification_type)


class NotificationPreferencesUpdate(BaseModel):
    """Request to update notification preferences"""

    enabled: Optional[bool] = None
    email: Optional[EmailConfig] = None
    discord: Optional[DiscordConfig] = None
    enabled_notification_types: Optional[List[NotificationType]] = None
    minimum_priority: Optional[NotificationPriority] = None
    notification_type_priorities: Optional[Dict[NotificationType, NotificationPriority]] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    quiet_hours_bypass_priority: Optional[NotificationPriority] = None
    timezone: Optional[str] = None
    max_notifications_per_hour: Optional[int] = None


# ==================== Notification Events ====================


class NetworkEvent(BaseModel):
    """A network event that may trigger a notification"""

    event_id: str = Field(default_factory=lambda: "")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: NotificationType
    priority: NotificationPriority = NotificationPriority.MEDIUM

    # Network context - notifications are per-network
    network_id: Optional[str] = None  # UUID string
    network_name: Optional[str] = None

    # Device information
    device_ip: Optional[str] = None
    device_name: Optional[str] = None
    device_hostname: Optional[str] = None

    # Event details
    title: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)

    # Previous state (for change detection)
    previous_state: Optional[str] = None
    current_state: Optional[str] = None

    # Anomaly detection metadata
    anomaly_score: Optional[float] = None  # 0.0 to 1.0, higher = more anomalous
    is_predicted_anomaly: bool = False
    ml_model_version: Optional[str] = None


class NotificationRecord(BaseModel):
    """Record of a sent notification"""

    notification_id: str
    event_id: str
    network_id: Optional[str] = (
        None  # UUID string - which network this notification was for (None for global)
    )
    channel: NotificationChannel
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Status
    success: bool
    error_message: Optional[str] = None

    # Notification content
    title: str
    message: str
    priority: NotificationPriority


class NotificationHistoryResponse(BaseModel):
    """Response with notification history"""

    notifications: List[NotificationRecord]
    total_count: int
    page: int = 1
    per_page: int = 50


# ==================== Discord Bot Configuration ====================


class DiscordBotInfo(BaseModel):
    """Discord bot information"""

    bot_name: str = "Cartographer Bot"
    bot_id: Optional[str] = None
    invite_url: Optional[str] = None
    is_connected: bool = False
    connected_guilds: int = 0


class DiscordGuild(BaseModel):
    """Discord server (guild) info"""

    id: str
    name: str
    icon_url: Optional[str] = None
    member_count: Optional[int] = None


class DiscordChannel(BaseModel):
    """Discord channel info"""

    id: str
    name: str
    type: str  # text, voice, etc.


class DiscordGuildsResponse(BaseModel):
    """Response with list of Discord guilds the bot is in"""

    guilds: List[DiscordGuild]


class DiscordChannelsResponse(BaseModel):
    """Response with list of channels in a guild"""

    guild_id: str
    channels: List[DiscordChannel]


# ==================== Anomaly Detection ====================


class AnomalyType(str, Enum):
    """Types of anomalies detected"""

    UNEXPECTED_OFFLINE = "unexpected_offline"
    UNUSUAL_LATENCY_SPIKE = "unusual_latency_spike"
    UNUSUAL_PACKET_LOSS = "unusual_packet_loss"
    PATTERN_DEVIATION = "pattern_deviation"
    NEW_DEVICE = "new_device"
    MISSING_DEVICE = "missing_device"
    TIME_BASED_ANOMALY = "time_based_anomaly"


class DeviceBaseline(BaseModel):
    """Baseline metrics for a device used in anomaly detection"""

    device_ip: str
    device_name: Optional[str] = None

    # Normal operating parameters (learned over time)
    avg_latency_ms: Optional[float] = None
    latency_std_dev: Optional[float] = None
    avg_packet_loss: Optional[float] = None
    typical_online_hours: List[int] = Field(
        default_factory=list
    )  # Hours when device is typically online

    # Pattern data
    check_count: int = 0
    online_count: int = 0
    offline_count: int = 0

    # Time-based patterns
    hourly_availability: Dict[int, float] = Field(default_factory=dict)  # hour -> availability %
    daily_availability: Dict[int, float] = Field(
        default_factory=dict
    )  # day_of_week -> availability %

    # Stable state detection
    is_stable_offline: bool = False  # True if device is consistently offline (normal behavior)
    is_stable_online: bool = False  # True if device is consistently online (normal behavior)
    state_transitions: int = 0  # Number of times device changed state (online <-> offline)

    # Timestamps
    first_seen: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    # Model metadata
    model_version: str = "1.0.0"
    samples_count: int = 0


class AnomalyDetectionResult(BaseModel):
    """Result of anomaly detection analysis"""

    is_anomaly: bool
    anomaly_score: float = Field(ge=0.0, le=1.0)
    anomaly_type: Optional[AnomalyType] = None

    # Explanation
    reason: str
    contributing_factors: List[str] = Field(default_factory=list)

    # Comparison to baseline
    expected_value: Optional[float] = None
    actual_value: Optional[float] = None
    deviation_percent: Optional[float] = None

    # Confidence
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class MLModelStatus(BaseModel):
    """Status of the ML anomaly detection model"""

    model_version: str
    last_training: Optional[datetime] = None
    samples_count: int = 0
    devices_tracked: int = 0
    anomalies_detected_total: int = 0
    anomalies_detected_24h: int = 0
    false_positive_rate: Optional[float] = None
    # Deprecated: use is_online_learning instead. Kept for backward compatibility.
    is_trained: bool = False
    # The model is always online learning - it continuously adapts to network state
    is_online_learning: bool = False
    # Status: "initializing" (no data yet), "online_learning" (actively learning)
    training_status: str = "initializing"


# ==================== Scheduled Broadcasts ====================


class ScheduledBroadcastStatus(str, Enum):
    """Status of a scheduled broadcast"""

    PENDING = "pending"
    SENT = "sent"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ScheduledBroadcast(BaseModel):
    """A scheduled broadcast notification"""

    id: str = Field(default_factory=lambda: "")
    title: str
    message: str
    event_type: NotificationType = NotificationType.SCHEDULED_MAINTENANCE
    priority: NotificationPriority = NotificationPriority.MEDIUM
    network_id: str  # UUID string - the network this broadcast belongs to (required)
    scheduled_at: datetime
    timezone: Optional[str] = None  # IANA timezone name (e.g., "America/New_York") for display
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str  # Username of the owner who created it
    status: ScheduledBroadcastStatus = ScheduledBroadcastStatus.PENDING
    sent_at: Optional[datetime] = None
    seen_at: Optional[datetime] = None  # When a user first viewed this after it was sent
    users_notified: int = 0
    error_message: Optional[str] = None


class ScheduledBroadcastCreate(BaseModel):
    """Request to create a scheduled broadcast"""

    title: str
    message: str
    event_type: NotificationType = NotificationType.SCHEDULED_MAINTENANCE
    priority: NotificationPriority = NotificationPriority.MEDIUM
    network_id: str  # UUID string - the network this broadcast belongs to (required)
    scheduled_at: datetime
    timezone: Optional[str] = None  # IANA timezone name for display purposes


class ScheduledBroadcastUpdate(BaseModel):
    """Request to update a scheduled broadcast (only pending broadcasts can be updated)"""

    title: Optional[str] = None
    message: Optional[str] = None
    event_type: Optional[NotificationType] = None
    priority: Optional[NotificationPriority] = None
    scheduled_at: Optional[datetime] = None
    timezone: Optional[str] = None


class ScheduledBroadcastResponse(BaseModel):
    """Response with scheduled broadcast info"""

    broadcasts: List[ScheduledBroadcast]
    total_count: int


# ==================== API Requests/Responses ====================


class TestNotificationRequest(BaseModel):
    """Request to send a test notification"""

    channel: NotificationChannel
    message: Optional[str] = "This is a test notification from Cartographer!"


class TestNotificationResponse(BaseModel):
    """Response from test notification"""

    success: bool
    channel: NotificationChannel
    message: str
    error: Optional[str] = None


class NotificationStatsResponse(BaseModel):
    """Statistics about notifications"""

    total_sent_24h: int = 0
    total_sent_7d: int = 0
    by_channel: Dict[str, int] = Field(default_factory=dict)
    by_type: Dict[str, int] = Field(default_factory=dict)
    success_rate: float = 1.0
    anomalies_detected_24h: int = 0


# ==================== Discord OAuth ====================


class DiscordOAuthState(BaseModel):
    """State for Discord OAuth flow"""

    user_id: str
    state_token: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime


class DiscordUserInfo(BaseModel):
    """Discord user information from OAuth"""

    discord_id: str
    username: str
    discriminator: Optional[str] = None
    avatar_url: Optional[str] = None
    email: Optional[str] = None


# ==================== Global User Preferences (for Cartographer Up/Down) ====================


class GlobalUserPreferences(BaseModel):
    """Global notification preferences for app-wide notifications (Cartographer Up/Down)"""

    user_id: str
    email_address: Optional[str] = None
    cartographer_up_enabled: bool = True
    cartographer_down_enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class GlobalUserPreferencesUpdate(BaseModel):
    """Request to update global user preferences"""

    email_address: Optional[str] = None
    cartographer_up_enabled: Optional[bool] = None
    cartographer_down_enabled: Optional[bool] = None
