"""
Local authentication provider using bcrypt + JWT.

This wraps the existing auth system to conform to the provider interface,
allowing seamless switching between local and cloud authentication modes.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

import jwt
from fastapi import Request

from ...config import settings
from ..claims import AuthMethod, AuthProvider, IdentityClaims
from .base import AuthProviderInterface

if TYPE_CHECKING:
    from ...db_models import User


class LocalAuthProvider(AuthProviderInterface):
    """
    Local authentication provider using bcrypt + JWT.

    This wraps the existing auth system to conform to the provider interface.
    For local mode, the provider_user_id is the same as the local_user_id.
    """

    async def validate_token(self, token: str) -> IdentityClaims | None:
        """Validate local JWT token and return identity claims."""
        try:
            payload = jwt.decode(
                token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
            )

            # Import here to avoid circular imports
            from ...services.auth_service import auth_service
            from ...database import async_session_maker

            async with async_session_maker() as db:
                user = await auth_service.get_user(db, payload["sub"])
                if not user or not user.is_active:
                    return None

                return self._user_to_claims(user, payload)

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    async def validate_session(self, request: Request) -> IdentityClaims | None:
        """
        Validate session from request.

        Local auth uses token-based auth via Authorization header.
        """
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return await self.validate_token(token)
        return None

    async def handle_webhook(self, request: Request) -> dict:
        """Local auth doesn't use webhooks."""
        return {"status": "not_applicable", "message": "Local auth does not support webhooks"}

    async def get_login_url(self, redirect_uri: str) -> str:
        """Return frontend login page URL."""
        return f"/login?redirect={redirect_uri}"

    async def get_logout_url(self, redirect_uri: str) -> str:
        """Return frontend logout handler URL."""
        return f"/logout?redirect={redirect_uri}"

    async def revoke_session(self, session_id: str) -> bool:
        """
        Revoke a user session.

        Local JWT tokens are stateless and cannot be revoked directly.
        A token blocklist could be implemented if needed.
        """
        # JWT tokens are stateless - cannot be revoked without a blocklist
        # Return True to indicate "success" in the sense that no action is needed
        return True

    def _user_to_claims(self, user: "User", jwt_payload: dict) -> IdentityClaims:
        """Convert a User model and JWT payload to IdentityClaims."""
        return IdentityClaims(
            provider=AuthProvider.LOCAL,
            provider_user_id=str(user.id),
            auth_method=AuthMethod.PASSWORD,
            email=user.email,
            email_verified=user.is_verified,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            avatar_url=None,  # Local auth doesn't support avatars yet
            session_id=None,  # JWT-based auth doesn't have session IDs
            issued_at=datetime.fromtimestamp(jwt_payload["iat"], tz=timezone.utc),
            expires_at=datetime.fromtimestamp(jwt_payload["exp"], tz=timezone.utc),
            org_id=None,
            org_slug=None,
            org_role=None,
            connection_id=None,
            connection_type=None,
            idp_id=None,
            directory_id=None,
            raw_attributes=None,
            local_user_id=UUID(user.id),
        )
