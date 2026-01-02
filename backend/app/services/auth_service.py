"""
Authentication service for token verification.

Handles:
- Service-to-service JWT token verification (local)
- User token verification via external auth service
"""

import logging

import httpx
import jwt
from fastapi import HTTPException

from ..config import get_settings

logger = logging.getLogger(__name__)


def verify_service_token(token: str, settings=None):
    """Verify a service-to-service JWT token locally.

    Service tokens are self-signed with the shared jwt_secret and have 'service: true' in the payload.

    Args:
        token: JWT token string
        settings: Optional settings override for testing

    Returns:
        Dict with user_id, username, role if valid, None otherwise
    """
    if settings is None:
        settings = get_settings()

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])

        # Check if this is a service token
        if not payload.get("service"):
            return None

        # Service tokens have full owner access
        return {
            "user_id": payload.get("sub", "service"),
            "username": payload.get("username", "service"),
            "role": "owner",  # Services have owner-level access
        }
    except jwt.ExpiredSignatureError:
        logger.debug("Service token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid service token: {e}")
        return None
    except Exception as e:
        logger.debug(f"Error verifying service token: {e}")
        return None


async def verify_token_with_auth_service(token: str, settings=None) -> dict | None:
    """Verify a token by calling the auth service.

    Args:
        token: JWT token string
        settings: Optional settings override for testing

    Returns:
        Dict with user_id, username, role if valid, None otherwise

    Raises:
        HTTPException: 503 if auth service unavailable, 504 if timeout
    """
    if settings is None:
        settings = get_settings()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.auth_service_url}/api/auth/verify",
                headers={"Authorization": f"Bearer {token}"},
            )

            if response.status_code != 200:
                logger.debug(f"Token verification failed with status {response.status_code}")
                return None

            data = response.json()
            if not data.get("valid"):
                return None

            return {"user_id": data["user_id"], "username": data["username"], "role": data["role"]}
    except httpx.ConnectError:
        logger.error(f"Failed to connect to auth service at {settings.auth_service_url}")
        raise HTTPException(status_code=503, detail="Auth service unavailable")
    except httpx.TimeoutException:
        logger.error("Timeout connecting to auth service")
        raise HTTPException(status_code=504, detail="Auth service timeout")
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        return None
