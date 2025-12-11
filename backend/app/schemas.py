"""
Pydantic schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field

from .models.network import PermissionRole


# ============================================================================
# Network Schemas
# ============================================================================

class NetworkCreate(BaseModel):
    """Network creation request."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class NetworkUpdate(BaseModel):
    """Network update request."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class NetworkResponse(BaseModel):
    """Network response."""
    id: int
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_sync_at: Optional[datetime]
    # Computed fields
    is_owner: bool = False
    permission: Optional[PermissionRole] = None

    class Config:
        from_attributes = True


class NetworkLayoutResponse(BaseModel):
    """Network layout data response."""
    id: int
    name: str
    layout_data: Optional[dict[str, Any]]
    updated_at: datetime

    class Config:
        from_attributes = True


class NetworkLayoutSave(BaseModel):
    """Network layout save request."""
    layout_data: dict[str, Any]


# ============================================================================
# Permission Schemas
# ============================================================================

class PermissionCreate(BaseModel):
    """Permission creation request."""
    user_id: str  # UUID as string
    role: PermissionRole


class PermissionResponse(BaseModel):
    """Permission response."""
    id: int
    network_id: int
    user_id: str
    role: PermissionRole
    created_at: datetime
    # Optional user info (populated if available)
    username: Optional[str] = None

    class Config:
        from_attributes = True

