"""
Identity claims module for pluggable authentication providers.

This module defines the contract between identity providers and the application.
All providers must produce an IdentityClaims object that represents the
authenticated user.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID


class AuthProvider(str, Enum):
    """The identity provider that authenticated the user."""

    LOCAL = "local"
    CLERK = "clerk"
    WORKOS = "workos"


class AuthMethod(str, Enum):
    """How the user authenticated."""

    PASSWORD = "password"
    SOCIAL_OAUTH = "social_oauth"
    SAML_SSO = "saml_sso"
    OIDC_SSO = "oidc_sso"
    MAGIC_LINK = "magic_link"
    PASSKEY = "passkey"


@dataclass(frozen=True)
class IdentityClaims:
    """
    Standardized identity claims produced by any auth provider.

    This is the contract between identity providers and the application.
    All providers must map their user data to this structure.
    """

    # === Core Identity ===
    provider: AuthProvider  # Which provider authenticated
    provider_user_id: str  # User ID in the external provider
    auth_method: AuthMethod  # How they authenticated

    # === User Profile ===
    email: str  # Primary email (verified)
    email_verified: bool  # Whether email is verified
    username: str | None  # Username if available
    first_name: str | None  # Given name
    last_name: str | None  # Family name
    avatar_url: str | None  # Profile picture URL

    # === Session Info ===
    session_id: str | None  # External session ID
    issued_at: datetime  # When claims were issued
    expires_at: datetime | None  # When session expires

    # === Organization (if applicable) ===
    org_id: str | None  # External org ID (Clerk/WorkOS)
    org_slug: str | None  # Organization slug
    org_role: str | None  # Role within org

    # === Enterprise SSO (WorkOS) ===
    connection_id: str | None  # WorkOS connection ID
    connection_type: str | None  # "saml" or "oidc"
    idp_id: str | None  # Identity provider ID
    directory_id: str | None  # SCIM directory ID
    raw_attributes: dict | None  # Raw SAML/OIDC attributes

    # === Local Mapping ===
    local_user_id: UUID | None  # Mapped local user ID (populated after sync)


@dataclass
class ProviderConfig:
    """Configuration for an auth provider."""

    provider: AuthProvider
    enabled: bool

    # Clerk config
    clerk_publishable_key: str | None = None
    clerk_secret_key: str | None = None
    clerk_webhook_secret: str | None = None

    # WorkOS config
    workos_api_key: str | None = None
    workos_client_id: str | None = None
    workos_webhook_secret: str | None = None
