"""
Auth dependencies for backend routes.
Verifies tokens by calling the auth service.
"""

import logging
from enum import Enum

from fastapi import Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from ..config import get_settings
from ..services.auth_service import verify_service_token as _verify_service_token
from ..services.auth_service import (
    verify_token_with_auth_service as _verify_token_with_auth_service,
)
from .token_extractor import resolve_request_token

logger = logging.getLogger(__name__)
settings = get_settings()

# Security scheme for JWT
security = HTTPBearer(auto_error=False)


class UserRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class AuthenticatedUser(BaseModel):
    """Authenticated user information from token verification"""

    user_id: str
    username: str
    role: UserRole

    @property
    def is_owner(self) -> bool:
        return self.role == UserRole.OWNER

    @property
    def can_write(self) -> bool:
        return self.role in [UserRole.OWNER, UserRole.ADMIN]


def verify_service_token(token: str) -> AuthenticatedUser | None:
    """Verify a service-to-service JWT token locally.

    Service tokens are self-signed with the shared jwt_secret and have 'service: true' in the payload.
    """
    result = _verify_service_token(token, settings)
    if result is None:
        return None
    return AuthenticatedUser(
        user_id=result["user_id"], username=result["username"], role=UserRole(result["role"])
    )


async def verify_token_with_auth_service(token: str) -> AuthenticatedUser | None:
    """Verify a token by calling the auth service"""
    result = await _verify_token_with_auth_service(token, settings)
    if result is None:
        return None
    return AuthenticatedUser(
        user_id=result["user_id"], username=result["username"], role=UserRole(result["role"])
    )


async def get_current_user(
    request: Request = None,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    token: str | None = Query(
        None, description="JWT token (for SSE/EventSource which doesn't support headers)"
    ),
) -> AuthenticatedUser | None:
    """Get current user from JWT token (returns None if not authenticated).

    Supports both:
    - Authorization header (standard approach)
    - Query parameter 'token' (for EventSource/SSE which doesn't support custom headers)

    Also supports service-to-service tokens (validated locally without auth service).
    """
    actual_token = resolve_request_token(
        request=request,
        credentials=credentials,
        query_token=token,
    )

    if not actual_token:
        return None

    # Try service token validation first (for internal service-to-service calls)
    service_user = verify_service_token(actual_token)
    if service_user:
        logger.debug("Authenticated as service")
        return service_user

    # Fall back to auth service validation for user tokens
    return await verify_token_with_auth_service(actual_token)


async def require_auth(
    user: AuthenticatedUser | None = Depends(get_current_user),
) -> AuthenticatedUser:
    """Require authenticated user"""
    if not user:
        raise HTTPException(
            status_code=401, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"}
        )
    return user


async def require_write_access(
    user: AuthenticatedUser = Depends(require_auth),
) -> AuthenticatedUser:
    """Require write access (owner or readwrite)"""
    if not user.can_write:
        raise HTTPException(status_code=403, detail="Write access required")
    return user


async def require_owner(user: AuthenticatedUser = Depends(require_auth)) -> AuthenticatedUser:
    """Require owner role"""
    if not user.is_owner:
        raise HTTPException(status_code=403, detail="Owner access required")
    return user
