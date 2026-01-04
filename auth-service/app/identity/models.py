"""
Pydantic models for identity claims API responses.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from .claims import AuthMethod, AuthProvider


class IdentityClaimsResponse(BaseModel):
    """API response model for identity claims."""

    provider: AuthProvider
    provider_user_id: str
    auth_method: AuthMethod

    email: EmailStr
    email_verified: bool
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None

    session_id: str | None = None
    issued_at: datetime
    expires_at: datetime | None = None

    org_id: str | None = None
    org_slug: str | None = None
    org_role: str | None = None

    local_user_id: UUID | None = None

    model_config = {"from_attributes": True}


class UserSyncRequest(BaseModel):
    """Request to sync external user to local database."""

    claims: IdentityClaimsResponse
    create_if_missing: bool = True
    update_profile: bool = True


class UserSyncResponse(BaseModel):
    """Response from user sync operation."""

    local_user_id: UUID
    created: bool
    updated: bool
    provider_linked: bool


class ProviderLinkResponse(BaseModel):
    """Response model for a provider link."""

    id: UUID
    user_id: UUID
    provider: AuthProvider
    provider_user_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ProviderInfoResponse(BaseModel):
    """Information about available auth providers."""

    provider: AuthProvider
    enabled: bool
    display_name: str
    supports_sso: bool = False
    supports_social: bool = False
