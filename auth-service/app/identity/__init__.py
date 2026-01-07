"""
Identity module for pluggable authentication providers.

This module provides a unified identity contract and provider abstraction
that allows Cartographer to support multiple authentication backends:

- Local: bcrypt/JWT authentication (self-hosted)
- Clerk: Consumer CIAM with social login, MFA (cloud)
- WorkOS: Enterprise SSO with SAML/SCIM (cloud)

Usage:
    from app.identity import get_provider, IdentityClaims

    provider = get_provider()
    claims = await provider.validate_token(token)
    if claims:
        print(f"Authenticated: {claims.email}")
"""

from .claims import AuthMethod, AuthProvider, IdentityClaims, ProviderConfig
from .factory import get_provider, reset_provider
from .models import (
    IdentityClaimsResponse,
    ProviderInfoResponse,
    ProviderLinkResponse,
    UserSyncRequest,
    UserSyncResponse,
)
from .providers import AuthProviderInterface, ClerkAuthProvider, LocalAuthProvider
from .sync import (
    deactivate_provider_user,
    get_provider_links,
    link_provider,
    sync_provider_user,
    unlink_provider,
)

__all__ = [
    # Claims and enums
    "AuthMethod",
    "AuthProvider",
    "IdentityClaims",
    "ProviderConfig",
    # Factory functions
    "get_provider",
    "reset_provider",
    # Pydantic models
    "IdentityClaimsResponse",
    "ProviderInfoResponse",
    "ProviderLinkResponse",
    "UserSyncRequest",
    "UserSyncResponse",
    # Provider classes
    "AuthProviderInterface",
    "ClerkAuthProvider",
    "LocalAuthProvider",
    # Sync functions
    "deactivate_provider_user",
    "get_provider_links",
    "link_provider",
    "sync_provider_user",
    "unlink_provider",
]
