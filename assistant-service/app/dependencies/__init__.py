"""
Auth dependencies for assistant service routes.
"""
from .auth import (
    AuthenticatedUser,
    UserRole,
    get_current_user,
    require_auth,
    require_auth_with_rate_limit,
)

__all__ = [
    "AuthenticatedUser",
    "UserRole",
    "get_current_user",
    "require_auth",
    "require_auth_with_rate_limit",
]

