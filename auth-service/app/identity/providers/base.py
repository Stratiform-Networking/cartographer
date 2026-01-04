"""
Base interface for authentication providers.

All auth providers must implement this interface to ensure consistent
behavior across different authentication mechanisms.
"""

from abc import ABC, abstractmethod

from fastapi import Request

from ..claims import IdentityClaims, ProviderConfig


class AuthProviderInterface(ABC):
    """
    Base interface for authentication providers.

    Each provider handles authentication and produces IdentityClaims.
    The claims are then synced to the local database.
    """

    def __init__(self, config: ProviderConfig):
        self.config = config

    @abstractmethod
    async def validate_token(self, token: str) -> IdentityClaims | None:
        """
        Validate an access token and return identity claims.

        Args:
            token: The bearer token from the Authorization header

        Returns:
            IdentityClaims if valid, None if invalid
        """
        pass

    @abstractmethod
    async def validate_session(self, request: Request) -> IdentityClaims | None:
        """
        Validate session from request (cookies/headers).

        Args:
            request: The FastAPI request object

        Returns:
            IdentityClaims if valid session, None otherwise
        """
        pass

    @abstractmethod
    async def handle_webhook(self, request: Request) -> dict:
        """
        Handle webhook events from the provider.

        Used for user sync, organization updates, etc.

        Args:
            request: The webhook request

        Returns:
            Response data for the webhook
        """
        pass

    @abstractmethod
    async def get_login_url(self, redirect_uri: str) -> str:
        """
        Get the URL to redirect users for login.

        Args:
            redirect_uri: Where to redirect after login

        Returns:
            The login URL
        """
        pass

    @abstractmethod
    async def get_logout_url(self, redirect_uri: str) -> str:
        """
        Get the URL to redirect users for logout.

        Args:
            redirect_uri: Where to redirect after logout

        Returns:
            The logout URL
        """
        pass

    @abstractmethod
    async def revoke_session(self, session_id: str) -> bool:
        """
        Revoke a user session.

        Args:
            session_id: The session to revoke

        Returns:
            True if revoked, False otherwise
        """
        pass
