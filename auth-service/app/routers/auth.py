"""
Auth router with database-backed authentication.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..db_models import Invite, User, UserRole
from ..models import (
    AcceptInviteRequest,
    ChangePasswordRequest,
    InviteCreate,
    InviteResponse,
    InviteTokenInfo,
    LoginRequest,
    LoginResponse,
    OwnerSetupRequest,
    SessionInfo,
    SetupStatus,
    UserCreate,
    UserPreferences,
    UserPreferencesUpdate,
    UserResponse,
    UserUpdate,
)
from ..services.auth_service import auth_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

# Security scheme for JWT
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Get current user from JWT token (returns None if not authenticated)."""
    if not credentials:
        return None

    token_payload = auth_service.verify_token(credentials.credentials)
    if not token_payload:
        return None

    user = await auth_service.get_user(db, token_payload.sub)
    if not user or not user.is_active:
        return None

    return user


async def require_auth(user: User | None = Depends(get_current_user)) -> User:
    """Require authenticated user."""
    if not user:
        raise HTTPException(
            status_code=401, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"}
        )
    return user


async def require_owner(user: User = Depends(require_auth)) -> User:
    """Require owner role."""
    if user.role != UserRole.OWNER:
        raise HTTPException(status_code=403, detail="Owner access required")
    return user


async def require_admin_access(user: User = Depends(require_auth)) -> User:
    """Require admin access (owner or admin)."""
    if user.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ==================== Setup Endpoints ====================


@router.get("/setup/status", response_model=SetupStatus)
async def get_setup_status(db: AsyncSession = Depends(get_db)):
    """Check if initial setup is complete."""
    status = await auth_service.get_setup_status(db)
    return SetupStatus(**status)


@router.post("/setup/owner", response_model=UserResponse)
async def setup_owner(request: OwnerSetupRequest, db: AsyncSession = Depends(get_db)):
    """Create the initial owner account (only works on first run)."""
    try:
        user = await auth_service.setup_owner(db, request)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Internal Endpoints (service-to-service) ====================


@router.get("/internal/owner")
async def get_owner_internal(db: AsyncSession = Depends(get_db)):
    """
    Get the owner user ID for internal service use.
    This endpoint is only accessible on the internal service port (8002)
    and is used by the migration script to assign ownership of migrated data.
    """
    owner = await auth_service.get_owner_user(db)
    if not owner:
        raise HTTPException(status_code=404, detail="No owner user found")
    return {"user_id": owner.id, "username": owner.username}


@router.get("/internal/users")
async def get_all_users_internal(db: AsyncSession = Depends(get_db)):
    """
    Get all user IDs for internal service use.
    Used by the migration script to detect orphaned networks.
    """
    users = await auth_service.get_all_user_ids(db)
    return [{"user_id": uid} for uid in users]


@router.get("/internal/users/{user_id}")
async def get_user_internal(user_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get user info by ID for internal service use.
    Used by notification service to get user emails for notifications.
    """
    user = await auth_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }


# ==================== Registration Endpoint (Cloud) ====================


@router.post("/register", response_model=LoginResponse, status_code=201)
async def register(request: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Open registration endpoint for cloud deployments.
    Creates a new user with 'member' role and returns access token.

    This endpoint allows public registration without requiring an invite.
    For self-hosted deployments, use the invite system instead.
    """
    try:
        user, token, expires_in = await auth_service.register_user(db, request)
        return LoginResponse(
            access_token=token,
            token_type="bearer",
            expires_in=expires_in,
            user=auth_service._to_response(user),
        )
    except ValueError as e:
        error_msg = str(e)
        if "disabled" in error_msg.lower():
            raise HTTPException(status_code=403, detail=error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")


# ==================== Authentication Endpoints ====================


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate and get access token (async password verification for better load handling)."""
    user = await auth_service.authenticate(db, request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token, expires_in = auth_service.create_access_token(user)

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=auth_service._to_response(user),
    )


@router.post("/logout")
async def logout(user: User = Depends(require_auth)):
    """Logout current user (client should discard token)."""
    logger.info(f"User logged out: {user.username}")
    return {"message": "Logged out successfully"}


@router.get("/session", response_model=SessionInfo)
async def get_session(user: User = Depends(require_auth)):
    """Get current session information."""
    return SessionInfo(
        user=auth_service._to_response(user), permissions=auth_service.get_permissions(user.role)
    )


@router.post("/verify")
async def verify_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify if the current token is valid.

    Supports two types of tokens:
    1. User tokens - verified against the user database
    2. Service tokens - tokens with "service": true, used for service-to-service auth
    """
    if not credentials:
        return {"valid": False}

    token_payload = auth_service.verify_token(credentials.credentials)
    if not token_payload:
        return {"valid": False}

    # Check if this is a service token
    raw_payload = auth_service.decode_token_payload(credentials.credentials)
    if raw_payload and raw_payload.get("service") is True:
        return {
            "valid": True,
            "user_id": token_payload.sub,
            "username": token_payload.username,
            "role": token_payload.role.value,
            "is_service": True,
        }

    # Regular user token - verify user exists in database
    user = await auth_service.get_user(db, token_payload.sub)
    if not user or not user.is_active:
        return {"valid": False}

    return {"valid": True, "user_id": user.id, "username": user.username, "role": user.role.value}


# ==================== User Management Endpoints ====================


@router.get("/users", response_model=list[UserResponse])
async def list_users(user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    """List all users (owners see all, others see only themselves)."""
    return await auth_service.list_users(db, user)


@router.post("/users", response_model=UserResponse)
async def create_user(
    request: UserCreate, user: User = Depends(require_owner), db: AsyncSession = Depends(get_db)
):
    """Create a new user (owner only)."""
    try:
        new_user = await auth_service.create_user(db, request, user)
        return new_user
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str, user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)
):
    """Get user by ID."""
    if user.role != UserRole.OWNER and user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    target = await auth_service.get_user(db, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    return auth_service._to_response(target)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdate,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Update a user."""
    try:
        updated = await auth_service.update_user(db, user_id, request, user)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str, user: User = Depends(require_owner), db: AsyncSession = Depends(get_db)
):
    """Delete a user (owner only)."""
    try:
        await auth_service.delete_user(db, user_id, user)
        return {"message": "User deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ==================== Profile Endpoints ====================


@router.get("/me", response_model=UserResponse)
async def get_current_profile(user: User = Depends(require_auth)):
    """Get current user's profile."""
    return auth_service._to_response(user)


@router.patch("/me", response_model=UserResponse)
async def update_current_profile(
    request: UserUpdate, user: User = Depends(require_auth), db: AsyncSession = Depends(get_db)
):
    """Update current user's profile."""
    if request.role is not None and user.role != UserRole.OWNER:
        raise HTTPException(status_code=403, detail="Cannot change your own role")

    try:
        updated = await auth_service.update_user(db, user.id, request, user)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/me/change-password")
async def change_password(
    request: ChangePasswordRequest,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Change current user's password."""
    try:
        await auth_service.change_password(
            db, user.id, request.current_password, request.new_password
        )
        return {"message": "Password changed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me/preferences", response_model=UserPreferences)
async def get_preferences(user: User = Depends(require_auth)):
    """Get current user's preferences."""
    return await auth_service.get_preferences(user)


@router.patch("/me/preferences", response_model=UserPreferences)
async def update_preferences(
    request: UserPreferencesUpdate,
    user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Update current user's preferences (partial update)."""
    return await auth_service.update_preferences(db, user, request)


# ==================== Invitation Endpoints ====================


@router.get("/invites", response_model=list[InviteResponse])
async def list_invites(user: User = Depends(require_owner), db: AsyncSession = Depends(get_db)):
    """List all invitations (owner only)."""
    try:
        return await auth_service.list_invites(db, user)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/invites", response_model=InviteResponse)
async def create_invite(
    request: InviteCreate, user: User = Depends(require_owner), db: AsyncSession = Depends(get_db)
):
    """Create an invitation for a new user (owner only)."""
    try:
        invite, email_sent = await auth_service.create_invite(db, request, user)
        response = auth_service._invite_to_response(invite)
        return response
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/invites/{invite_id}", response_model=InviteResponse)
async def get_invite(
    invite_id: str, user: User = Depends(require_owner), db: AsyncSession = Depends(get_db)
):
    """Get a specific invitation (owner only)."""
    result = await db.execute(select(Invite).where(Invite.id == invite_id))
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")
    return auth_service._invite_to_response(invite)


@router.delete("/invites/{invite_id}")
async def revoke_invite(
    invite_id: str, user: User = Depends(require_owner), db: AsyncSession = Depends(get_db)
):
    """Revoke a pending invitation (owner only)."""
    try:
        await auth_service.revoke_invite(db, invite_id, user)
        return {"message": "Invitation revoked"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/invites/{invite_id}/resend")
async def resend_invite(
    invite_id: str, user: User = Depends(require_owner), db: AsyncSession = Depends(get_db)
):
    """Resend an invitation email (owner only)."""
    try:
        await auth_service.resend_invite(db, invite_id, user)
        return {"message": "Invitation email resent"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ==================== Public Invitation Endpoints ====================


@router.get("/invite/verify/{token}", response_model=InviteTokenInfo)
async def verify_invite_token(token: str, db: AsyncSession = Depends(get_db)):
    """Verify an invitation token and get its info (public endpoint)."""
    info = await auth_service.get_invite_token_info(db, token)
    if not info:
        raise HTTPException(status_code=404, detail="Invalid invitation token")
    return info


@router.post("/invite/accept", response_model=UserResponse)
async def accept_invite(request: AcceptInviteRequest, db: AsyncSession = Depends(get_db)):
    """Accept an invitation and create account (public endpoint)."""
    try:
        user = await auth_service.accept_invite(
            db=db,
            token=request.token,
            username=request.username,
            first_name=request.first_name,
            last_name=request.last_name,
            password=request.password,
        )
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
