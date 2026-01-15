"""
Pydantic schemas for API request/response validation.

Domain-specific schemas are organized into submodules:
- network: Network CRUD schemas
- permission: Permission management schemas
- notification: Notification settings schemas
- agent_sync: Agent scan sync schemas

All schemas are re-exported here for backwards compatibility.
"""

from .agent_sync import (
    AgentHealthCheckRequest,
    AgentHealthCheckResponse,
    AgentSyncRequest,
    AgentSyncResponse,
    HealthCheckResult,
    NetworkInfo,
    SyncDevice,
)
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
    # Agent Sync
    "SyncDevice",
    "NetworkInfo",
    "AgentSyncRequest",
    "AgentSyncResponse",
    # Agent Health Check
    "HealthCheckResult",
    "AgentHealthCheckRequest",
    "AgentHealthCheckResponse",
]
