"""
SQLAlchemy database models for auth service.
Compatible with cartographer-cloud user format with additional role field.
"""

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .database import Base


class UserRole(str, enum.Enum):
    """App-level user permission levels"""

    OWNER = "owner"  # Full access - can manage all users and app settings
    ADMIN = "admin"  # Can manage users (except owner) and invite new users
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
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Role for self-hosted permission management
    # Use values_callable to ensure SQLAlchemy uses lowercase enum values matching PostgreSQL
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(
            UserRole,
            name="user_role",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=UserRole.MEMBER,
    )

    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=True
    )  # Self-hosted users are auto-verified

    # User preferences (JSON blob for flexible storage)
    # Contains: { dark_mode?: boolean, ... }
    preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    provider_links: Mapped[list["ProviderLink"]] = relationship(
        "ProviderLink", back_populates="user", cascade="all, delete-orphan"
    )
    password_reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Invite(Base):
    """User invitation model for inviting new users to the self-hosted instance."""

    __tablename__ = "invites"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(
            UserRole,
            name="user_role",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=UserRole.MEMBER,
    )
    status: Mapped[InviteStatus] = mapped_column(
        SQLEnum(
            InviteStatus,
            name="invite_status",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=InviteStatus.PENDING,
    )

    # Token for accepting the invite (hashed for security)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    # Who created the invite
    invited_by_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    invited_by_username: Mapped[str] = mapped_column(String(50))
    invited_by_name: Mapped[str] = mapped_column(String(200))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProviderLink(Base):
    """
    Links external authentication provider users to local users.

    Allows a user to have multiple authentication methods linked
    (e.g., local password + Clerk social login + WorkOS SAML SSO).
    This enables seamless migration between auth providers.
    """

    __tablename__ = "provider_links"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # "local", "clerk", "workos"
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="provider_links")

    # Ensure unique provider + provider_user_id combination
    __table_args__ = (UniqueConstraint("provider", "provider_user_id", name="uq_provider_user"),)


class UserLimit(Base):
    """
    Per-user limit configuration.

    Stores custom limits for users that differ from system defaults.
    NULL values mean "use system default", -1 means unlimited.
    """

    __tablename__ = "user_limits"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    # Network limit: NULL = use system default, -1 = unlimited, positive = custom limit
    network_limit: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)

    # True if unlimited status was set automatically due to role exemption
    # False if it was manually set by an admin
    is_role_exempt: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UserPlanSettings(Base):
    """
    Per-user plan-derived values (centralized plan snapshot).

    This stores the current plan's values that are consumed by different
    services so the plan state is not scattered across service-specific tables.
    """

    __tablename__ = "user_plan_settings"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    plan_id: Mapped[str] = mapped_column(String(50), nullable=False, default="free")

    # Supported plan limits currently implemented in code.
    owned_networks_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    assistant_daily_chat_messages_limit: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5
    )
    automatic_full_scan_min_interval_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=7200
    )
    health_poll_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UserAssistantProviderKey(Base):
    """
    Per-user BYOK provider key storage.

    API keys are stored encrypted in `encrypted_api_key`.
    Model preference is stored as plaintext metadata.
    """

    __tablename__ = "user_assistant_provider_keys"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    provider: Mapped[str] = mapped_column(String(32), primary_key=True)
    encrypted_api_key: Mapped[str] = mapped_column(String(4096), nullable=False)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PasswordResetToken(Base):
    """Password reset tokens for one-time, time-limited password reset flows."""

    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="password_reset_tokens")
