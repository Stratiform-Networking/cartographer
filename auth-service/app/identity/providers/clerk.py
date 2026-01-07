"""
Clerk authentication provider.

Handles user authentication via Clerk's session tokens and webhooks.
Provides social login, MFA, and organization features.
"""

import base64
import json
import logging
from datetime import datetime, timezone

import httpx
import svix
from fastapi import Request

from ..claims import AuthMethod, AuthProvider, IdentityClaims, ProviderConfig
from .base import AuthProviderInterface

logger = logging.getLogger(__name__)


def decode_jwt_payload(token: str) -> dict | None:
    """Decode JWT payload without verification (verification done by Clerk API)."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        # Add padding if needed
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception:
        return None


class ClerkAuthProvider(AuthProviderInterface):
    """
    Clerk authentication provider.

    Handles:
    - User management and sessions
    - Social login (Google, GitHub, etc.)
    - Clerk Organizations
    - Pre-built UI components (handled by frontend)
    """

    CLERK_API_BASE = "https://api.clerk.com/v1"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.secret_key = config.clerk_secret_key
        self.publishable_key = config.clerk_publishable_key

    async def validate_token(self, token: str) -> IdentityClaims | None:
        """
        Validate Clerk session token.

        Clerk uses short-lived session tokens that can be validated
        via their Backend API.

        Args:
            token: The session token from Clerk

        Returns:
            IdentityClaims if valid, None if invalid
        """
        if not self.secret_key:
            logger.error("Clerk secret key not configured")
            return None

        # Decode JWT to get session_id (sid claim)
        jwt_payload = decode_jwt_payload(token)
        if not jwt_payload:
            logger.warning("Failed to decode Clerk session token")
            return None

        session_id = jwt_payload.get("sid")
        if not session_id:
            logger.warning("No session_id (sid) in Clerk token")
            return None

        async with httpx.AsyncClient() as client:
            try:
                # Verify session with Clerk API using the correct endpoint
                response = await client.post(
                    f"{self.CLERK_API_BASE}/sessions/{session_id}/verify",
                    headers={
                        "Authorization": f"Bearer {self.secret_key}",
                        "Content-Type": "application/json",
                    },
                    json={"token": token},
                )

                if response.status_code != 200:
                    logger.debug(
                        f"Clerk session verification failed: {response.status_code} - {response.text}"
                    )
                    return None

                session_data = response.json()
                user_id = session_data.get("user_id")

                if not user_id:
                    logger.warning("No user_id in Clerk session response")
                    return None

                # Get full user profile
                user_response = await client.get(
                    f"{self.CLERK_API_BASE}/users/{user_id}",
                    headers={"Authorization": f"Bearer {self.secret_key}"},
                )

                if user_response.status_code != 200:
                    logger.warning(f"Failed to fetch Clerk user: {user_response.status_code}")
                    return None

                user = user_response.json()

                # Determine auth method from session
                auth_method = self._get_auth_method(session_data)

                # Get primary email
                primary_email = self._get_primary_email(user)

                return IdentityClaims(
                    provider=AuthProvider.CLERK,
                    provider_user_id=user["id"],
                    auth_method=auth_method,
                    email=primary_email.get("email_address", ""),
                    email_verified=primary_email.get("verification", {}).get("status")
                    == "verified",
                    username=user.get("username"),
                    first_name=user.get("first_name"),
                    last_name=user.get("last_name"),
                    avatar_url=user.get("image_url"),
                    session_id=session_data.get("id"),
                    issued_at=datetime.fromtimestamp(
                        session_data.get("created_at", 0) / 1000, tz=timezone.utc
                    ),
                    expires_at=(
                        datetime.fromtimestamp(
                            session_data.get("expire_at", 0) / 1000, tz=timezone.utc
                        )
                        if session_data.get("expire_at")
                        else None
                    ),
                    org_id=session_data.get("last_active_organization_id"),
                    org_slug=None,  # Would need separate org lookup
                    org_role=None,  # Would need membership lookup
                    connection_id=None,
                    connection_type=None,
                    idp_id=None,
                    directory_id=None,
                    raw_attributes=user.get("public_metadata"),
                    local_user_id=None,  # Set after sync
                )
            except httpx.RequestError as e:
                logger.error(f"Error communicating with Clerk API: {e}")
                return None

    async def validate_session(self, request: Request) -> IdentityClaims | None:
        """
        Validate Clerk session from cookies or Authorization header.

        Args:
            request: The FastAPI request object

        Returns:
            IdentityClaims if valid session, None otherwise
        """
        # Check for Clerk session cookie
        session_token = request.cookies.get("__session")
        if session_token:
            return await self.validate_token(session_token)

        # Fall back to Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return await self.validate_token(auth_header[7:])

        return None

    async def handle_webhook(self, request: Request) -> dict:
        """
        Handle Clerk webhook events.

        Events handled:
        - user.created: Create local user
        - user.updated: Update local user profile
        - user.deleted: Deactivate local user
        - organization.created/updated: Sync org to local
        - organizationMembership.created/deleted: Update user roles

        Args:
            request: The webhook request

        Returns:
            Response data for the webhook
        """

        # Verify webhook signature
        webhook_secret = self.config.clerk_webhook_secret
        if not webhook_secret:
            logger.error("Clerk webhook secret not configured")
            return {"error": "Webhook not configured"}

        svix_headers = {
            "svix-id": request.headers.get("svix-id", ""),
            "svix-timestamp": request.headers.get("svix-timestamp", ""),
            "svix-signature": request.headers.get("svix-signature", ""),
        }

        body = await request.body()
        wh = svix.Webhook(webhook_secret)

        try:
            payload = wh.verify(body, svix_headers)
        except svix.WebhookVerificationError as e:
            logger.warning(f"Clerk webhook signature verification failed: {e}")
            return {"error": "Invalid signature"}

        event_type = payload.get("type")
        data = payload.get("data", {})

        logger.info(f"Received Clerk webhook event: {event_type}")

        return {"received": True, "type": event_type, "data": data}

    def _get_auth_method(self, session_data: dict) -> AuthMethod:
        """
        Determine auth method from Clerk session.

        Args:
            session_data: The session data from Clerk

        Returns:
            The appropriate AuthMethod enum value
        """
        # Clerk includes the strategy used for auth
        strategy = session_data.get("authentication_strategy", "")

        if "oauth" in strategy:
            return AuthMethod.SOCIAL_OAUTH
        elif "passkey" in strategy:
            return AuthMethod.PASSKEY
        elif "email_link" in strategy:
            return AuthMethod.MAGIC_LINK
        else:
            return AuthMethod.PASSWORD

    def _get_primary_email(self, user: dict) -> dict:
        """
        Get the primary email address from Clerk user data.

        Args:
            user: The user data from Clerk

        Returns:
            The primary email address object, or empty dict if none
        """
        return next(
            (
                e
                for e in user.get("email_addresses", [])
                if e["id"] == user.get("primary_email_address_id")
            ),
            {},
        )

    def data_to_claims(self, data: dict) -> IdentityClaims:
        """
        Convert Clerk webhook data to IdentityClaims.

        This is used when processing webhook events to create claims
        without having a session.

        Args:
            data: User data from Clerk webhook

        Returns:
            IdentityClaims populated from the webhook data
        """
        primary_email = self._get_primary_email(data)

        return IdentityClaims(
            provider=AuthProvider.CLERK,
            provider_user_id=data["id"],
            auth_method=AuthMethod.PASSWORD,  # Default, actual method unknown in webhook
            email=primary_email.get("email_address", ""),
            email_verified=primary_email.get("verification", {}).get("status") == "verified",
            username=data.get("username"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            avatar_url=data.get("image_url"),
            session_id=None,
            issued_at=datetime.now(timezone.utc),
            expires_at=None,
            org_id=None,
            org_slug=None,
            org_role=None,
            connection_id=None,
            connection_type=None,
            idp_id=None,
            directory_id=None,
            raw_attributes=data.get("public_metadata"),
            local_user_id=None,
        )

    async def get_login_url(self, redirect_uri: str) -> str:
        """
        Get the login URL for Clerk.

        Clerk handles login via frontend components, so this returns
        the frontend sign-in path.

        Args:
            redirect_uri: Where to redirect after login

        Returns:
            The login URL
        """
        return f"/sign-in?redirect_url={redirect_uri}"

    async def get_logout_url(self, redirect_uri: str) -> str:
        """
        Get the logout URL for Clerk.

        Args:
            redirect_uri: Where to redirect after logout

        Returns:
            The logout URL
        """
        return f"/sign-out?redirect_url={redirect_uri}"

    async def revoke_session(self, session_id: str) -> bool:
        """
        Revoke a Clerk session.

        Args:
            session_id: The session ID to revoke

        Returns:
            True if revoked successfully, False otherwise
        """
        if not self.secret_key:
            logger.error("Clerk secret key not configured")
            return False

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.CLERK_API_BASE}/sessions/{session_id}/revoke",
                    headers={"Authorization": f"Bearer {self.secret_key}"},
                )
                return response.status_code == 200
            except httpx.RequestError as e:
                logger.error(f"Error revoking Clerk session: {e}")
                return False

    async def get_user_by_id(self, user_id: str) -> dict | None:
        """
        Fetch a user from Clerk by their ID.

        Args:
            user_id: The Clerk user ID

        Returns:
            User data dict if found, None otherwise
        """
        if not self.secret_key:
            logger.error("Clerk secret key not configured")
            return None

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.CLERK_API_BASE}/users/{user_id}",
                    headers={"Authorization": f"Bearer {self.secret_key}"},
                )
                if response.status_code == 200:
                    return response.json()
                return None
            except httpx.RequestError as e:
                logger.error(f"Error fetching Clerk user: {e}")
                return None
