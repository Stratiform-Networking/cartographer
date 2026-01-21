"""Dependencies module for backend routes"""

from .auth import (
    AuthenticatedUser,
    UserRole,
    get_current_user,
    require_auth,
    require_owner,
    require_write_access,
)
from .service_auth import (
    optional_service_auth,
    require_service_auth,
    require_signed_request,
    require_specific_service,
)

__all__ = [
    # User authentication
    "AuthenticatedUser",
    "UserRole",
    "get_current_user",
    "require_auth",
    "require_write_access",
    "require_owner",
    # Service authentication
    "require_service_auth",
    "optional_service_auth",
    "require_signed_request",
    "require_specific_service",
]
