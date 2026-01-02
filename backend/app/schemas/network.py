"""
Network-related Pydantic schemas.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..models.network import PermissionRole


class NetworkCreate(BaseModel):
    """Network creation request."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)


class NetworkUpdate(BaseModel):
    """Network update request."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)


class NetworkResponse(BaseModel):
    """Network response."""

    model_config = ConfigDict(from_attributes=True)

    id: str  # UUID string
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_sync_at: datetime | None
    # Computed fields
    owner_id: str | None = None  # UUID of the network owner
    is_owner: bool = False
    permission: PermissionRole | None = None


class NetworkLayoutResponse(BaseModel):
    """Network layout data response."""

    model_config = ConfigDict(from_attributes=True)

    id: str  # UUID string
    name: str
    layout_data: dict[str, Any] | None
    updated_at: datetime


class NetworkLayoutSave(BaseModel):
    """Network layout save request."""

    layout_data: dict[str, Any]
