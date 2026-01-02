"""Database models for assistant service."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .database import Base


class UserRateLimit(Base):
    """Per-user rate limit configuration.

    - If daily_limit is NULL: user uses the system default (from ASSISTANT_CHAT_LIMIT_PER_DAY env var)
    - If daily_limit is -1: user has unlimited requests
    - If daily_limit is a positive number: user has that specific limit

    The is_exempt field tracks whether the user was given unlimited access due to their role
    being in ASSISTANT_RATE_LIMIT_EXEMPT_ROLES. This allows us to:
    - Set users to unlimited when their role qualifies
    - Revert them back to default when their role no longer qualifies
    """

    __tablename__ = "user_rate_limits"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)

    # NULL = use system default, -1 = unlimited, positive = custom limit
    daily_limit: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)

    # True if the unlimited status was set automatically due to role exemption
    # False if it was manually set by an admin
    is_role_exempt: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        limit_str = (
            "default"
            if self.daily_limit is None
            else ("unlimited" if self.daily_limit == -1 else str(self.daily_limit))
        )
        return f"<UserRateLimit(user_id={self.user_id}, limit={limit_str}, role_exempt={self.is_role_exempt})>"
