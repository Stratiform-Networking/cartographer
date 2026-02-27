"""
Pydantic models for request/response validation.
"""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# Import UserRole from db_models for consistency
from .db_models import InviteStatus, UserRole


class UserBase(BaseModel):
    """Base user fields."""

    username: str = Field(..., min_length=3, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", v):
            raise ValueError(
                "Username must start with a letter and contain only letters, numbers, underscores, and hyphens"
            )
        return v.lower()


class UserCreate(UserBase):
    """Request to create a new user."""

    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.MEMBER

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class OwnerSetupRequest(BaseModel):
    """Request to create the initial owner account (first-run setup)."""

    username: str = Field(..., min_length=3, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", v):
            raise ValueError(
                "Username must start with a letter and contain only letters, numbers, underscores, and hyphens"
            )
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserUpdate(BaseModel):
    """Request to update a user."""

    first_name: str | None = Field(None, max_length=50)
    last_name: str | None = Field(None, max_length=50)
    email: EmailStr | None = None
    role: UserRole | None = None
    password: str | None = Field(None, min_length=8)


class UserResponse(BaseModel):
    """User data returned to clients (no password)."""

    id: str
    username: str
    first_name: str
    last_name: str
    email: str
    avatar_url: str | None = None
    role: UserRole
    created_at: datetime
    updated_at: datetime
    last_login: datetime | None = None
    is_active: bool = True


class LoginRequest(BaseModel):
    """Login credentials."""

    username: str
    password: str


class LoginResponse(BaseModel):
    """Successful login response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until expiration
    user: UserResponse


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # user id
    username: str
    role: UserRole
    exp: datetime
    iat: datetime


class SetupStatus(BaseModel):
    """Application setup status."""

    is_setup_complete: bool
    owner_exists: bool
    total_users: int


class AuthConfig(BaseModel):
    """Auth provider configuration exposed to frontend."""

    provider: str  # "local" or "cloud"
    clerk_publishable_key: str | None = None
    clerk_proxy_url: str | None = None  # Custom Clerk domain
    allow_registration: bool = False


class ChangePasswordRequest(BaseModel):
    """Request to change password."""

    current_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class PasswordResetRequest(BaseModel):
    """Request to start password reset via email."""

    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    """Request to complete password reset with token + new password."""

    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class SessionInfo(BaseModel):
    """Current session information."""

    user: UserResponse
    permissions: list[str]


class ErrorResponse(BaseModel):
    """Error response."""

    detail: str
    code: str | None = None


# ==================== Preferences Models ====================


class UserPreferences(BaseModel):
    """User preferences (stored as JSON in database)."""

    dark_mode: bool | None = None
    # Add more preferences here as needed
    # timezone: str | None = None
    # locale: str | None = None


class UserPreferencesUpdate(BaseModel):
    """Request to update user preferences (partial update)."""

    dark_mode: bool | None = None


# ==================== Invitation Models ====================


class InviteCreate(BaseModel):
    """Request to create an invitation."""

    email: EmailStr
    role: UserRole = UserRole.MEMBER

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: UserRole) -> UserRole:
        if v == UserRole.OWNER:
            raise ValueError("Cannot invite users with owner role")
        return v


class InviteResponse(BaseModel):
    """Invitation data returned to clients."""

    id: str
    email: str
    role: UserRole
    status: InviteStatus
    invited_by: str  # username of inviter
    invited_by_name: str  # full name of inviter
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None = None


class AcceptInviteRequest(BaseModel):
    """Request to accept an invitation and create account."""

    token: str
    username: str = Field(..., min_length=3, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=8)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", v):
            raise ValueError(
                "Username must start with a letter and contain only letters, numbers, underscores, and hyphens"
            )
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class InviteTokenInfo(BaseModel):
    """Public info about an invite token (for the accept page)."""

    email: str
    role: UserRole
    invited_by_name: str
    expires_at: datetime
    is_valid: bool


# ==================== Network Limit Models ====================


class NetworkLimitStatus(BaseModel):
    """Network limit status for a user."""

    used: int  # Number of networks owned
    limit: int  # Max networks allowed (-1 = unlimited)
    remaining: int  # Networks that can still be created (-1 = unlimited)
    is_exempt: bool  # Whether user is exempt from limits
    message: str | None = (
        None  # Message to display when limit is reached (only included when limit reached)
    )


class NetworkLimitUpdate(BaseModel):
    """Request to update a user's network limit."""

    network_limit: int | None = Field(
        None,
        description="Network limit: -1 = unlimited, null = reset to default, positive = custom limit",
    )

    @field_validator("network_limit")
    @classmethod
    def validate_limit(cls, v: int | None) -> int | None:
        if v is not None and v < -1:
            raise ValueError(
                "Network limit must be -1 (unlimited), null (default), or a positive number"
            )
        return v


class UserPlanSettingsResponse(BaseModel):
    """Current plan-derived settings for a user."""

    user_id: str
    plan_id: str
    owned_networks_limit: int
    assistant_daily_chat_messages_limit: int
    automatic_full_scan_min_interval_seconds: int
    health_poll_interval_seconds: int


class UserPlanSettingsUpdate(BaseModel):
    """Update a user's current plan and refresh plan-derived settings."""

    plan_id: str = Field(..., min_length=1, max_length=50)

    @field_validator("plan_id")
    @classmethod
    def validate_plan_id(cls, v: str) -> str:
        return v.strip().lower()


# ==================== Internal Database Models ====================


class UserInDB(BaseModel):
    """User with hashed password - internal use for auth operations."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str
    first_name: str
    last_name: str
    role: UserRole
    hashed_password: str
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    last_login: datetime | None = None


class InviteInDB(BaseModel):
    """Internal invite model with token."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    role: UserRole
    status: InviteStatus
    token: str
    invited_by_id: str
    invited_by_username: str
    invited_by_name: str
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None = None
