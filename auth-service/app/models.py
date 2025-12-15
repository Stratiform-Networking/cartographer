from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Optional, List
from datetime import datetime
import re

# Import UserRole from db_models for consistency
from .db_models import UserRole, InviteStatus


class UserBase(BaseModel):
    """Base user fields"""
    username: str = Field(..., min_length=3, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', v):
            raise ValueError('Username must start with a letter and contain only letters, numbers, underscores, and hyphens')
        return v.lower()


class UserCreate(UserBase):
    """Request to create a new user"""
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.MEMBER
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class OwnerSetupRequest(BaseModel):
    """Request to create the initial owner account (first-run setup)"""
    username: str = Field(..., min_length=3, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', v):
            raise ValueError('Username must start with a letter and contain only letters, numbers, underscores, and hyphens')
        return v.lower()
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class UserUpdate(BaseModel):
    """Request to update a user"""
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    password: Optional[str] = Field(None, min_length=8)


class UserResponse(BaseModel):
    """User data returned to clients (no password)"""
    id: str
    username: str
    first_name: str
    last_name: str
    email: str
    role: UserRole
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True


class LoginRequest(BaseModel):
    """Login credentials"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Successful login response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until expiration
    user: UserResponse


class TokenPayload(BaseModel):
    """JWT token payload"""
    sub: str  # user id
    username: str
    role: UserRole
    exp: datetime
    iat: datetime


class SetupStatus(BaseModel):
    """Application setup status"""
    is_setup_complete: bool
    owner_exists: bool
    total_users: int


class ChangePasswordRequest(BaseModel):
    """Request to change password"""
    current_password: str
    new_password: str = Field(..., min_length=8)
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class SessionInfo(BaseModel):
    """Current session information"""
    user: UserResponse
    permissions: List[str]


class ErrorResponse(BaseModel):
    """Error response"""
    detail: str
    code: Optional[str] = None


# ==================== Invitation Models ====================

class InviteCreate(BaseModel):
    """Request to create an invitation"""
    email: EmailStr
    role: UserRole = UserRole.MEMBER
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: UserRole) -> UserRole:
        if v == UserRole.OWNER:
            raise ValueError('Cannot invite users with owner role')
        return v


class InviteResponse(BaseModel):
    """Invitation data returned to clients"""
    id: str
    email: str
    role: UserRole
    status: InviteStatus
    invited_by: str  # username of inviter
    invited_by_name: str  # full name of inviter
    created_at: datetime
    expires_at: datetime
    accepted_at: Optional[datetime] = None


class AcceptInviteRequest(BaseModel):
    """Request to accept an invitation and create account"""
    token: str
    username: str = Field(..., min_length=3, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=8)
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', v):
            raise ValueError('Username must start with a letter and contain only letters, numbers, underscores, and hyphens')
        return v.lower()
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class InviteTokenInfo(BaseModel):
    """Public info about an invite token (for the accept page)"""
    email: str
    role: UserRole
    invited_by_name: str
    expires_at: datetime
    is_valid: bool


# ==================== Internal Database Models ====================

class UserInDB(BaseModel):
    """User with hashed password - internal use for auth operations"""
    id: str
    username: str
    email: str
    first_name: str
    last_name: str
    role: UserRole
    hashed_password: str
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class InviteInDB(BaseModel):
    """Internal invite model with token"""
    id: str
    email: str
    role: UserRole
    status: InviteStatus
    token: str
    invited_by_id: str
    invited_by_username: str
    invited_by_name: str
    created_at: datetime
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
