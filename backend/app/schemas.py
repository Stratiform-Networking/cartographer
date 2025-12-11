"""
Pydantic schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field

from .models.network import PermissionRole


# ============================================================================
# Network Schemas
# ============================================================================

class NetworkCreate(BaseModel):
    """Network creation request."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class NetworkUpdate(BaseModel):
    """Network update request."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class NetworkResponse(BaseModel):
    """Network response."""
    id: int
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_sync_at: Optional[datetime]
    # Computed fields
    is_owner: bool = False
    permission: Optional[PermissionRole] = None

    class Config:
        from_attributes = True


class NetworkLayoutResponse(BaseModel):
    """Network layout data response."""
    id: int
    name: str
    layout_data: Optional[dict[str, Any]]
    updated_at: datetime

    class Config:
        from_attributes = True


class NetworkLayoutSave(BaseModel):
    """Network layout save request."""
    layout_data: dict[str, Any]


# ============================================================================
# Permission Schemas
# ============================================================================

class PermissionCreate(BaseModel):
    """Permission creation request."""
    user_id: str  # UUID as string
    role: PermissionRole


class PermissionResponse(BaseModel):
    """Permission response."""
    id: int
    network_id: int
    user_id: str
    role: PermissionRole
    created_at: datetime
    # Optional user info (populated if available)
    username: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# Network Notification Settings Schemas
# ============================================================================

class EmailConfigCreate(BaseModel):
    """Email notification configuration."""
    enabled: bool = False
    email_address: Optional[str] = None


class DiscordConfigCreate(BaseModel):
    """Discord notification configuration."""
    enabled: bool = False
    delivery_method: str = "channel"  # "channel" or "dm"
    discord_user_id: Optional[str] = None
    guild_id: Optional[str] = None
    channel_id: Optional[str] = None


class NotificationPreferencesCreate(BaseModel):
    """Notification preferences configuration."""
    enabled_types: list[str] = Field(default_factory=lambda: [
        "device_offline", "device_online", "device_degraded",
        "anomaly_detected", "high_latency", "packet_loss",
        "security_alert", "cartographer_down", "cartographer_up"
    ])
    minimum_priority: str = "medium"  # low, medium, high, critical
    quiet_hours_enabled: bool = False
    quiet_hours_start: Optional[str] = None  # HH:MM format
    quiet_hours_end: Optional[str] = None
    quiet_hours_bypass_priority: Optional[str] = None
    timezone: Optional[str] = None
    max_notifications_per_hour: int = 10


class NetworkNotificationSettingsCreate(BaseModel):
    """Create/update network notification settings."""
    enabled: bool = True
    email: Optional[EmailConfigCreate] = None
    discord: Optional[DiscordConfigCreate] = None
    preferences: Optional[NotificationPreferencesCreate] = None


class NetworkNotificationSettingsResponse(BaseModel):
    """Network notification settings response."""
    id: int
    network_id: int
    enabled: bool
    email_enabled: bool
    email_address: Optional[str]
    discord_enabled: bool
    discord_config: Optional[dict]
    preferences: Optional[dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

