"""
Pydantic schemas for API request/response validation.

Domain-specific schemas are organized into submodules:
- network: Network CRUD schemas
- permission: Permission management schemas
- notification: Notification settings schemas

All schemas are re-exported here for backwards compatibility.
"""

from .network import (
    NetworkCreate,
    NetworkLayoutResponse,
    NetworkLayoutSave,
    NetworkResponse,
    NetworkUpdate,
)
from .notification import (
    DiscordConfigCreate,
    EmailConfigCreate,
    NetworkNotificationSettingsCreate,
    NetworkNotificationSettingsResponse,
    NotificationPreferencesCreate,
)
from .permission import PermissionCreate, PermissionResponse

__all__ = [
    # Network
    "NetworkCreate",
    "NetworkUpdate",
    "NetworkResponse",
    "NetworkLayoutResponse",
    "NetworkLayoutSave",
    # Permission
    "PermissionCreate",
    "PermissionResponse",
    # Notification
    "EmailConfigCreate",
    "DiscordConfigCreate",
    "NotificationPreferencesCreate",
    "NetworkNotificationSettingsCreate",
    "NetworkNotificationSettingsResponse",
]
