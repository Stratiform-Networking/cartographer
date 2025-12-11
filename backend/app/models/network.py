"""
Network and NetworkPermission models.
Schema matches cartographer-cloud for future sync compatibility.
"""

from datetime import datetime
from typing import Optional
import enum

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, JSON, Integer
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..database import Base


class PermissionRole(str, enum.Enum):
    """
    Permission roles for network sharing.
    Note: The network creator is the owner (stored in Network.user_id).
    These roles are for users the owner shares the network with.
    """
    VIEWER = "viewer"   # Can view the network map
    EDITOR = "editor"   # Can view and modify the network map


class Network(Base):
    """
    User's network configurations.
    Schema matches cartographer-cloud for future sync compatibility.
    """
    __tablename__ = "networks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True)

    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Agent key for future cloud sync authentication
    agent_key: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, nullable=True
    )

    # Layout data (JSON blob with full tree + positions)
    # This stores the complete network map including nodes, positions, and metadata
    layout_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    permissions: Mapped[list["NetworkPermission"]] = relationship(
        back_populates="network", cascade="all, delete-orphan"
    )
    notification_settings: Mapped[Optional["NetworkNotificationSettings"]] = relationship(
        back_populates="network", cascade="all, delete-orphan", uselist=False
    )


class NetworkPermission(Base):
    """
    Permission assignments for network access.
    Allows sharing networks with other users.
    """
    __tablename__ = "network_permissions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    network_id: Mapped[int] = mapped_column(
        ForeignKey("networks.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), index=True)
    role: Mapped[PermissionRole] = mapped_column(
        SQLEnum(PermissionRole, name="permission_role")
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    network: Mapped["Network"] = relationship(back_populates="permissions")


class NetworkNotificationSettings(Base):
    """
    Per-network notification settings.
    Each network can have its own notification configuration.
    """
    __tablename__ = "network_notification_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    network_id: Mapped[int] = mapped_column(
        ForeignKey("networks.id", ondelete="CASCADE"), unique=True, index=True
    )
    
    # Master switch for this network's notifications
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Email configuration (stored as JSON)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    email_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Discord configuration (stored as JSON for flexibility)
    discord_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    discord_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Notification preferences (stored as JSON)
    # Contains: enabled_types, minimum_priority, quiet_hours, etc.
    preferences: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Relationships
    network: Mapped["Network"] = relationship(back_populates="notification_settings")

