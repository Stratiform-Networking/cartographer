"""
Provider factory for authentication providers.

Creates the appropriate auth provider based on configuration.
Supports lazy initialization and singleton pattern.
"""

import logging

from ..config import settings
from .claims import AuthProvider, ProviderConfig
from .providers.base import AuthProviderInterface
from .providers.local import LocalAuthProvider

logger = logging.getLogger(__name__)


def get_auth_provider() -> AuthProviderInterface:
    """
    Factory function to get the configured auth provider.

    Uses AUTH_PROVIDER env var to determine which provider to use.

    Returns:
        An instance of the configured auth provider

    Raises:
        ValueError: If auth_provider is not a recognized value
    """
    auth_mode = settings.auth_provider.lower()

    if auth_mode == "local":
        return LocalAuthProvider(
            ProviderConfig(
                provider=AuthProvider.LOCAL,
                enabled=True,
            )
        )

    elif auth_mode == "cloud":
        # Cloud mode uses Clerk as primary with WorkOS for enterprise
        # Import here to avoid loading httpx when not in cloud mode
        from .providers.clerk import ClerkAuthProvider

        logger.info("Initializing Clerk auth provider for cloud mode")
        return ClerkAuthProvider(
            ProviderConfig(
                provider=AuthProvider.CLERK,
                enabled=True,
                clerk_publishable_key=settings.clerk_publishable_key,
                clerk_secret_key=settings.clerk_secret_key,
                clerk_webhook_secret=settings.clerk_webhook_secret,
            )
        )

    else:
        raise ValueError(
            f"Unknown auth provider: {auth_mode}. " f"Valid values are: 'local', 'cloud'"
        )


def get_workos_provider():
    """
    Get the WorkOS provider for enterprise SSO.

    Used alongside Clerk when enterprise customers need SAML/SCIM.

    Returns:
        WorkOSAuthProvider instance

    Raises:
        NotImplementedError: WorkOS integration is planned for Phase 3
    """
    # Note: WorkOS provider will be implemented in Phase 3
    raise NotImplementedError(
        "WorkOS provider is not yet implemented. "
        "This will be added in Phase 3 of the auth providers implementation."
    )


# Singleton instances
_auth_provider: AuthProviderInterface | None = None


def get_provider() -> AuthProviderInterface:
    """
    Get the singleton auth provider instance.

    This ensures that only one provider instance exists per process,
    which is important for connection pooling and resource management.

    Returns:
        The singleton auth provider instance
    """
    global _auth_provider
    if _auth_provider is None:
        _auth_provider = get_auth_provider()
    return _auth_provider


def reset_provider() -> None:
    """
    Reset the singleton provider instance.

    Useful for testing or when configuration changes.
    """
    global _auth_provider
    _auth_provider = None
