import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..models import (
    UserRole, UserCreate, UserUpdate, UserResponse,
    LoginRequest, LoginResponse, OwnerSetupRequest, SetupStatus,
    ChangePasswordRequest, SessionInfo, ErrorResponse,
    InviteCreate, InviteResponse, AcceptInviteRequest, InviteTokenInfo
)
from ..services.auth_service import auth_service, UserInDB

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

# Security scheme for JWT
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[UserInDB]:
    """Get current user from JWT token (returns None if not authenticated)"""
    if not credentials:
        return None
    
    token_payload = auth_service.verify_token(credentials.credentials)
    if not token_payload:
        return None
    
    user = auth_service.get_user(token_payload.sub)
    if not user or not user.is_active:
        return None
    
    return user


async def require_auth(
    user: Optional[UserInDB] = Depends(get_current_user)
) -> UserInDB:
    """Require authenticated user"""
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


async def require_owner(
    user: UserInDB = Depends(require_auth)
) -> UserInDB:
    """Require owner role"""
    if user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=403,
            detail="Owner access required"
        )
    return user


async def require_admin_access(
    user: UserInDB = Depends(require_auth)
) -> UserInDB:
    """Require admin access (owner or admin)"""
    if user.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return user


# ==================== Setup Endpoints ====================

@router.get("/setup/status", response_model=SetupStatus)
async def get_setup_status():
    """Check if initial setup is complete"""
    status = auth_service.get_setup_status()
    return SetupStatus(**status)


@router.post("/setup/owner", response_model=UserResponse)
async def setup_owner(request: OwnerSetupRequest):
    """Create the initial owner account (only works on first run)"""
    try:
        user = await auth_service.setup_owner(request)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Internal Endpoints (service-to-service) ====================

@router.get("/internal/owner")
async def get_owner_internal():
    """
    Get the owner user ID for internal service use.
    This endpoint is only accessible on the internal service port (8002)
    and is used by the migration script to assign ownership of migrated data.
    """
    owner = auth_service.get_owner_user()
    if not owner:
        raise HTTPException(status_code=404, detail="No owner user found")
    return {"user_id": owner.id, "username": owner.username}


# ==================== Authentication Endpoints ====================

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate and get access token (async password verification for better load handling)"""
    user = await auth_service.authenticate(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )
    
    token, expires_in = auth_service.create_access_token(user)
    
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=auth_service._to_response(user)
    )


@router.post("/logout")
async def logout(user: UserInDB = Depends(require_auth)):
    """Logout current user (client should discard token)"""
    # JWT tokens are stateless - logout is handled client-side
    # This endpoint exists for API completeness and logging
    logger.info(f"User logged out: {user.username}")
    return {"message": "Logged out successfully"}


@router.get("/session", response_model=SessionInfo)
async def get_session(user: UserInDB = Depends(require_auth)):
    """Get current session information"""
    return SessionInfo(
        user=auth_service._to_response(user),
        permissions=auth_service.get_permissions(user.role)
    )


@router.post("/verify")
async def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    Verify if the current token is valid.
    
    Supports two types of tokens:
    1. User tokens - verified against the user database
    2. Service tokens - tokens with "service": true, used for service-to-service auth
    """
    if not credentials:
        return {"valid": False}
    
    # First, decode the token to check if it's a service token
    token_payload = auth_service.verify_token(credentials.credentials)
    if not token_payload:
        return {"valid": False}
    
    # Check if this is a service token (used for service-to-service communication)
    # Service tokens have a special "service" claim set to True
    raw_payload = auth_service.decode_token_payload(credentials.credentials)
    if raw_payload and raw_payload.get("service") is True:
        # Service token - valid if signature verification passed
        return {
            "valid": True,
            "user_id": token_payload.sub,
            "username": token_payload.username,
            "role": token_payload.role.value,
            "is_service": True
        }
    
    # Regular user token - verify user exists in database
    user = auth_service.get_user(token_payload.sub)
    if not user or not user.is_active:
        return {"valid": False}
    
    return {
        "valid": True,
        "user_id": user.id,
        "username": user.username,
        "role": user.role.value
    }


# ==================== User Management Endpoints ====================

@router.get("/users", response_model=List[UserResponse])
async def list_users(user: UserInDB = Depends(require_auth)):
    """List all users (owners see all, others see only themselves)"""
    return auth_service.list_users(user)


@router.post("/users", response_model=UserResponse)
async def create_user(request: UserCreate, user: UserInDB = Depends(require_owner)):
    """Create a new user (owner only)"""
    try:
        new_user = await auth_service.create_user(request, user)
        return new_user
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, user: UserInDB = Depends(require_auth)):
    """Get user by ID"""
    # Non-owners can only see themselves
    if user.role != UserRole.OWNER and user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    target = auth_service.get_user(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    
    return auth_service._to_response(target)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdate,
    user: UserInDB = Depends(require_auth)
):
    """Update a user"""
    try:
        updated = await auth_service.update_user(user_id, request, user)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, user: UserInDB = Depends(require_owner)):
    """Delete a user (owner only)"""
    try:
        auth_service.delete_user(user_id, user)
        return {"message": "User deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ==================== Profile Endpoints ====================

@router.get("/me", response_model=UserResponse)
async def get_current_profile(user: UserInDB = Depends(require_auth)):
    """Get current user's profile"""
    return auth_service._to_response(user)


@router.patch("/me", response_model=UserResponse)
async def update_current_profile(
    request: UserUpdate,
    user: UserInDB = Depends(require_auth)
):
    """Update current user's profile"""
    # Users can only update their own profile, not role
    if request.role is not None and user.role != UserRole.OWNER:
        raise HTTPException(status_code=403, detail="Cannot change your own role")
    
    try:
        updated = await auth_service.update_user(user.id, request, user)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/me/change-password")
async def change_password(
    request: ChangePasswordRequest,
    user: UserInDB = Depends(require_auth)
):
    """Change current user's password"""
    try:
        await auth_service.change_password(user.id, request.current_password, request.new_password)
        return {"message": "Password changed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Invitation Endpoints ====================

@router.get("/invites", response_model=List[InviteResponse])
async def list_invites(user: UserInDB = Depends(require_owner)):
    """List all invitations (owner only)"""
    try:
        return auth_service.list_invites(user)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/invites", response_model=InviteResponse)
async def create_invite(request: InviteCreate, user: UserInDB = Depends(require_owner)):
    """Create an invitation for a new user (owner only)"""
    try:
        invite, email_sent = auth_service.create_invite(request, user)
        response = auth_service._invite_to_response(invite)
        # Add email_sent info to response headers
        return response
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/invites/{invite_id}", response_model=InviteResponse)
async def get_invite(invite_id: str, user: UserInDB = Depends(require_owner)):
    """Get a specific invitation (owner only)"""
    invite = auth_service._invites.get(invite_id)
    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")
    return auth_service._invite_to_response(invite)


@router.delete("/invites/{invite_id}")
async def revoke_invite(invite_id: str, user: UserInDB = Depends(require_owner)):
    """Revoke a pending invitation (owner only)"""
    try:
        auth_service.revoke_invite(invite_id, user)
        return {"message": "Invitation revoked"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/invites/{invite_id}/resend")
async def resend_invite(invite_id: str, user: UserInDB = Depends(require_owner)):
    """Resend an invitation email (owner only)"""
    try:
        auth_service.resend_invite(invite_id, user)
        return {"message": "Invitation email resent"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ==================== Public Invitation Endpoints ====================
# These don't require authentication

@router.get("/invite/verify/{token}", response_model=InviteTokenInfo)
async def verify_invite_token(token: str):
    """Verify an invitation token and get its info (public endpoint)"""
    info = auth_service.get_invite_token_info(token)
    if not info:
        raise HTTPException(status_code=404, detail="Invalid invitation token")
    return info


@router.post("/invite/accept", response_model=UserResponse)
async def accept_invite(request: AcceptInviteRequest):
    """Accept an invitation and create account (public endpoint)"""
    try:
        user = await auth_service.accept_invite(
            token=request.token,
            username=request.username,
            first_name=request.first_name,
            last_name=request.last_name,
            password=request.password
        )
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
