"""
SQLAlchemy database models for notification service.
Uses the same PostgreSQL database as the main application.
"""

from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID, ENUM as PgEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional
import enum

from ..database import Base


class NotificationPriorityEnum(str, enum.Enum):
    """Notification priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    
    def __str__(self):
        return self.value


class UserNetworkNotificationPrefs(Base):
    """Per-user notification preferences for a specific network"""
    __tablename__ = "user_network_notification_prefs"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True)
    network_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True)  # FK to networks.id (UUID in main app)
    
    # Channels
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    discord_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    discord_user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Types enabled (JSON list of NotificationType strings)
    enabled_types: Mapped[dict] = mapped_column(JSON, default=list)
    
    # Priority overrides per type (JSON dict: {type: priority})
    type_priorities: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Filters
    minimum_priority: Mapped[str] = mapped_column(
        PgEnum('low', 'medium', 'high', 'critical', name='notification_priority', create_type=False),
        default="medium"
    )
    quiet_hours_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    quiet_hours_start: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # HH:MM
    quiet_hours_end: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # HH:MM
    quiet_hours_timezone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # IANA timezone
    quiet_hours_bypass_priority: Mapped[Optional[str]] = mapped_column(
        PgEnum('low', 'medium', 'high', 'critical', name='notification_priority', create_type=False),
        nullable=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Unique constraint: one preference record per user per network
    __table_args__ = (
        {"comment": "Per-user notification preferences for networks"},
    )


class UserGlobalNotificationPrefs(Base):
    """Per-user global notification preferences"""
    __tablename__ = "user_global_notification_prefs"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), unique=True, index=True)
    
    # Channels
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    discord_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    discord_user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Global notification types
    cartographer_up_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    cartographer_down_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Filters
    minimum_priority: Mapped[str] = mapped_column(
        PgEnum('low', 'medium', 'high', 'critical', name='notification_priority', create_type=False),
        default="medium"
    )
    quiet_hours_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    quiet_hours_start: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # HH:MM
    quiet_hours_end: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # HH:MM
    quiet_hours_timezone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # IANA timezone
    quiet_hours_bypass_priority: Mapped[Optional[str]] = mapped_column(
        PgEnum('low', 'medium', 'high', 'critical', name='notification_priority', create_type=False),
        nullable=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    __table_args__ = (
        {"comment": "Per-user global notification preferences"},
    )


class DiscordUserLink(Base):
    """Links Cartographer user to Discord account via OAuth - per context (network or global)"""
    __tablename__ = "discord_user_links"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True)
    
    # Context: "network" or "global" - allows different Discord accounts per network and global
    context_type: Mapped[str] = mapped_column(String(20), default="global")  # "network" or "global"
    context_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)  # network_id (UUID) for "network", null for "global"
    
    discord_id: Mapped[str] = mapped_column(String(255), index=True)
    discord_username: Mapped[str] = mapped_column(String(255))
    discord_avatar: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # OAuth tokens (should be encrypted in production)
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    __table_args__ = (
        # Unique constraint: one Discord link per user per context
        # For networks: (user_id, "network", network_id) must be unique
        # For global: (user_id, "global", null) must be unique
        {"comment": "Discord OAuth links for users - per context (network or global)"},
    )
