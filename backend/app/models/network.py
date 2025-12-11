"""
Network and NetworkPermission models.
Schema matches cartographer-cloud for future sync compatibility.
"""

from datetime import datetime
from typing import Optional
import enum

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..database import Base


class PermissionRole(str, enum.Enum):
    """Permission roles for network access."""
    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN = "admin"


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

