"""
Permission-related Pydantic schemas.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from ..models.network import PermissionRole


class PermissionCreate(BaseModel):
    """Permission creation request."""

    user_id: str  # UUID as string
    role: PermissionRole


class PermissionResponse(BaseModel):
    """Permission response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    network_id: str  # UUID string
    user_id: str
    role: PermissionRole
    created_at: datetime
    # Optional user info (populated if available)
    username: str | None = None
