"""
Authentication service for token verification.

Handles:
- Service-to-service JWT token verification (local)
- User token verification via external auth service
- Cached token verification to reduce auth service load

Performance optimizations:
- Uses shared HTTP client pool (connection reuse)
- Redis caching for verified tokens (5 minute TTL)
- Local JWT decode for expired token fast-fail
"""

import json
import hashlib
import logging

import jwt
from fastapi import HTTPException

from ..config import get_settings
from .http_client import http_pool
from .cache_service import cache_service

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

    Uses the shared HTTP client pool for connection reuse and adds
    Redis caching to reduce auth service load.

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

    token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
    cache_key = f"auth:verify:{token_hash}"

    # Check cache first
    cached = await cache_service.get(cache_key)
    if cached is not None:
        logger.debug("Token verification cache HIT")
        return cached

    try:
        # Use shared HTTP pool instead of creating new client
        response = await http_pool.request(
            service_name="auth",
            method="POST",
            path="/api/auth/verify",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

        # http_pool returns JSONResponse, extract content
        if response.status_code != 200:
            logger.debug(f"Token verification failed with status {response.status_code}")
            return None

        # Parse response body
        data = json.loads(response.body)
        if not data.get("valid"):
            return None

        result = {"user_id": data["user_id"], "username": data["username"], "role": data["role"]}

        # Cache successful verification for 5 minutes
        # This dramatically reduces auth service load under high concurrency
        await cache_service.set(cache_key, result, ttl=300)
        logger.debug("Token verification cached")

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        return None
