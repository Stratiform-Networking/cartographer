"""
SQLAlchemy database models for auth service.
Compatible with cartographer-cloud user format with additional role field.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4
from sqlalchemy import String, Text, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
import enum

from .database import Base


class UserRole(str, enum.Enum):
    """App-level user permission levels"""
    OWNER = "owner"    # Full access - can manage all users and app settings
    ADMIN = "admin"    # Can manage users (except owner) and invite new users
    MEMBER = "member"  # Basic user - can create and manage their own networks


class InviteStatus(str, enum.Enum):
    """Invitation status"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class User(Base):
    """
    User account model.
    Compatible with cartographer-cloud User model, with additional 'role' field
    for self-hosted multi-user permission management.
    """
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), 
        primary_key=True, 
        default=lambda: str(uuid4())
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    
    # Role for self-hosted permission management
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role", create_type=True),
        default=UserRole.MEMBER
    )

    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True)  # Self-hosted users are auto-verified

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Invite(Base):
    """User invitation model for inviting new users to the self-hosted instance."""
    __tablename__ = "invites"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role", create_type=False),
        default=UserRole.MEMBER
    )
    status: Mapped[InviteStatus] = mapped_column(
        SQLEnum(InviteStatus, name="invite_status", create_type=True),
        default=InviteStatus.PENDING
    )
    
    # Token for accepting the invite (hashed for security)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    
    # Who created the invite
    invited_by_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    invited_by_username: Mapped[str] = mapped_column(String(50))
    invited_by_name: Mapped[str] = mapped_column(String(200))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
