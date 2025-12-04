"""
Pydantic models for the Notification Service.

These models define notification preferences, events, and channel configurations.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


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


# ==================== Email Configuration ====================

class EmailConfig(BaseModel):
    """Email notification configuration"""
    enabled: bool = False
    email_address: str = ""
    
    @field_validator('email_address')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if v and '@' not in v:
            raise ValueError('Invalid email address')
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
    

# ==================== User Notification Preferences ====================

class NotificationPreferences(BaseModel):
    """User's notification preferences"""
    user_id: str
    enabled: bool = True  # Master switch for notifications
    
    # Channel configurations
    email: EmailConfig = Field(default_factory=EmailConfig)
    discord: DiscordConfig = Field(default_factory=DiscordConfig)
    
    # Event type filters (which types of notifications to receive)
    enabled_notification_types: List[NotificationType] = Field(
        default_factory=lambda: [
            NotificationType.DEVICE_OFFLINE,
            NotificationType.ANOMALY_DETECTED,
            NotificationType.SECURITY_ALERT,
            NotificationType.ISP_ISSUE,
        ]
    )
    
    # Minimum priority level to notify (ignore lower priority)
    minimum_priority: NotificationPriority = NotificationPriority.MEDIUM
    
    # Quiet hours (don't send notifications during these times)
    quiet_hours_enabled: bool = False
    quiet_hours_start: Optional[str] = None  # HH:MM format
    quiet_hours_end: Optional[str] = None  # HH:MM format
    
    # Rate limiting
    max_notifications_per_hour: int = 10
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class NotificationPreferencesUpdate(BaseModel):
    """Request to update notification preferences"""
    enabled: Optional[bool] = None
    email: Optional[EmailConfig] = None
    discord: Optional[DiscordConfig] = None
    enabled_notification_types: Optional[List[NotificationType]] = None
    minimum_priority: Optional[NotificationPriority] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    max_notifications_per_hour: Optional[int] = None


# ==================== Notification Events ====================

class NetworkEvent(BaseModel):
    """A network event that may trigger a notification"""
    event_id: str = Field(default_factory=lambda: "")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: NotificationType
    priority: NotificationPriority = NotificationPriority.MEDIUM
    
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
    user_id: str
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
    typical_online_hours: List[int] = Field(default_factory=list)  # Hours when device is typically online
    
    # Pattern data
    check_count: int = 0
    online_count: int = 0
    offline_count: int = 0
    
    # Time-based patterns
    hourly_availability: Dict[int, float] = Field(default_factory=dict)  # hour -> availability %
    daily_availability: Dict[int, float] = Field(default_factory=dict)  # day_of_week -> availability %
    
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
    false_positive_rate: Optional[float] = None
    is_trained: bool = False


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

