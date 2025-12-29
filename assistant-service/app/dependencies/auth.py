"""
Auth dependencies for assistant service routes.
Verifies tokens by calling the auth service or validating service tokens locally.
"""

import logging
from enum import Enum

import httpx
import jwt
from fastapi import HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from ..config import settings

logger = logging.getLogger(__name__)

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
    
    Service tokens are self-signed with the shared JWT_SECRET and have 'service: true' in the payload.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        
        # Check if this is a service token
        if not payload.get("service"):
            return None
        
        # Service tokens have full owner access
        return AuthenticatedUser(
            user_id=payload.get("sub", "service"),
            username=payload.get("username", "service"),
            role=UserRole.OWNER  # Services have owner-level access
        )
    except jwt.ExpiredSignatureError:
        logger.debug("Service token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid service token: {e}")
        return None
    except Exception as e:
        logger.debug(f"Error verifying service token: {e}")
        return None


async def verify_token_with_auth_service(token: str) -> AuthenticatedUser | None:
    """Verify a token by calling the auth service"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.auth_service_url}/api/auth/verify",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code != 200:
                logger.debug(f"Token verification failed with status {response.status_code}")
                return None
            
            data = response.json()
            if not data.get("valid"):
                return None
            
            return AuthenticatedUser(
                user_id=data["user_id"],
                username=data["username"],
                role=UserRole(data["role"])
            )
    except httpx.ConnectError:
        logger.error(f"Failed to connect to auth service at {settings.auth_service_url}")
        raise HTTPException(
            status_code=503,
            detail="Auth service unavailable"
        )
    except httpx.TimeoutException:
        logger.error("Timeout connecting to auth service")
        raise HTTPException(
            status_code=504,
            detail="Auth service timeout"
        )
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    token: str | None = Query(None, description="JWT token (for SSE/EventSource which doesn't support headers)")
) -> AuthenticatedUser | None:
    """Get current user from JWT token (returns None if not authenticated).
    
    Supports both:
    - Authorization header (standard approach)
    - Query parameter 'token' (for EventSource/SSE which doesn't support custom headers)
    
    Also supports service-to-service tokens (validated locally without auth service).
    """
    actual_token = None
    
    # Try Authorization header first
    if credentials:
        actual_token = credentials.credentials
    # Fall back to query parameter (for SSE/EventSource)
    elif token:
        actual_token = token
    
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
    user: AuthenticatedUser | None = Depends(get_current_user)
) -> AuthenticatedUser:
    """Require authenticated user"""
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


def require_auth_with_rate_limit(limit: int, endpoint: str):
    """
    Create a dependency that requires authentication AND enforces a daily rate limit.
    
    Users with roles specified in ASSISTANT_RATE_LIMIT_EXEMPT_ROLES env var are exempt.
    
    Args:
        limit: Maximum requests per day
        endpoint: Endpoint identifier for the rate limit key (e.g., "chat")
    
    Returns:
        A FastAPI dependency function
    """
    async def _dependency(
        user: AuthenticatedUser = Depends(require_auth)
    ) -> AuthenticatedUser:
        from ..services.rate_limit import check_rate_limit
        await check_rate_limit(user.user_id, endpoint, limit, user_role=user.role.value)
        return user
    
    return _dependency
