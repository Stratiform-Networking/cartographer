"""Dependencies module for backend routes"""

from .auth import (
    AuthenticatedUser,
    UserRole,
    get_current_user,
    require_auth,
    require_owner,
    require_write_access,
)

__all__ = [
    "AuthenticatedUser",
    "UserRole",
    "get_current_user",
    "require_auth",
    "require_write_access",
    "require_owner",
]
