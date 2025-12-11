import os
import json
import uuid
import secrets
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, List
from passlib.context import CryptContext
import jwt

from ..models import (
    UserRole, UserCreate, UserUpdate, UserResponse, UserInDB,
    TokenPayload, OwnerSetupRequest,
    InviteStatus, InviteCreate, InviteResponse, InviteInDB, InviteTokenInfo
)

logger = logging.getLogger(__name__)

# Password hashing - configured for better performance under load
# Using bcrypt with explicit rounds (default is 12, we use 10 for faster hashing)
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=10  # Reduce rounds from default 12 for better performance
)

# Thread pool for CPU-bound password hashing operations
# This prevents blocking the event loop during password verification/hashing
_password_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="pwd_hash_")


async def hash_password_async(password: str) -> str:
    """
    Hash a password asynchronously using a thread pool.
    
    Bcrypt is CPU-bound and blocks the event loop when run synchronously.
    This runs the hashing in a thread pool to keep the server responsive.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_password_executor, pwd_context.hash, password)


async def verify_password_async(password: str, hash: str) -> bool:
    """
    Verify a password asynchronously using a thread pool.
    
    Bcrypt verification is CPU-bound and blocks the event loop.
    This runs the verification in a thread pool to keep the server responsive.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_password_executor, pwd_context.verify, password, hash)

# JWT Configuration
JWT_SECRET = os.environ.get("JWT_SECRET", "cartographer-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.environ.get("JWT_EXPIRATION_HOURS", "24"))


class AuthService:
    """Handles user authentication and management with file-based persistence"""
    
    # Invitation expiration (hours)
    INVITE_EXPIRATION_HOURS = int(os.environ.get("INVITE_EXPIRATION_HOURS", "72"))
    
    def __init__(self):
        # Determine data directory
        self.data_dir = Path(os.environ.get("AUTH_DATA_DIR", "/app/data"))
        if not self.data_dir.exists():
            # Fallback for local development
            self.data_dir = Path(__file__).resolve().parents[3]
        
        self.users_file = self.data_dir / "users.json"
        self.invites_file = self.data_dir / "invites.json"
        self._users: dict[str, UserInDB] = {}
        self._invites: dict[str, InviteInDB] = {}
        self._load_users()
        self._load_invites()
    
    def _load_users(self) -> None:
        """Load users from JSON file"""
        if self.users_file.exists():
            try:
                with open(self.users_file, 'r') as f:
                    data = json.load(f)
                    for user_data in data.get("users", []):
                        user = UserInDB(**user_data)
                        self._users[user.id] = user
                logger.info(f"Loaded {len(self._users)} users from {self.users_file}")
            except Exception as e:
                logger.error(f"Failed to load users: {e}")
                self._users = {}
        else:
            logger.info("No users file found, starting fresh")
            self._users = {}
    
    def _save_users(self) -> None:
        """Save users to JSON file"""
        try:
            # Ensure directory exists
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            users_data = {
                "users": [user.model_dump(mode='json') for user in self._users.values()]
            }
            with open(self.users_file, 'w') as f:
                json.dump(users_data, f, indent=2, default=str)
            logger.debug(f"Saved {len(self._users)} users to {self.users_file}")
        except Exception as e:
            logger.error(f"Failed to save users: {e}")
            raise
    
    # ==================== Setup & Status ====================
    
    def is_setup_complete(self) -> bool:
        """Check if initial setup (owner creation) is complete"""
        return any(u.role == UserRole.OWNER for u in self._users.values())
    
    def get_setup_status(self) -> dict:
        """Get current setup status"""
        owner_exists = any(u.role == UserRole.OWNER for u in self._users.values())
        return {
            "is_setup_complete": owner_exists,
            "owner_exists": owner_exists,
            "total_users": len(self._users)
        }
    
    async def setup_owner(self, request: OwnerSetupRequest) -> UserResponse:
        """Create the initial owner account (only works if no owner exists)"""
        if self.is_setup_complete():
            raise ValueError("Setup already complete - owner account exists")
        
        # Check if username is taken
        if self.get_user_by_username(request.username):
            raise ValueError("Username already taken")
        
        # Check if email is taken
        if self.get_user_by_email(request.email):
            raise ValueError("Email already in use")
        
        # Create the owner user
        now = datetime.now(timezone.utc)
        user_id = str(uuid.uuid4())
        
        # Hash password asynchronously to avoid blocking event loop
        password_hash = await hash_password_async(request.password)
        
        user = UserInDB(
            id=user_id,
            username=request.username.lower(),
            first_name=request.first_name,
            last_name=request.last_name,
            email=request.email.lower(),
            role=UserRole.OWNER,
            password_hash=password_hash,
            created_at=now,
            updated_at=now,
            is_active=True
        )
        
        self._users[user_id] = user
        self._save_users()
        
        logger.info(f"Owner account created: {user.username}")
        return self._to_response(user)
    
    # ==================== User CRUD ====================
    
    async def create_user(self, request: UserCreate, created_by: UserInDB) -> UserResponse:
        """Create a new user (only owners can create users)"""
        if created_by.role != UserRole.OWNER:
            raise PermissionError("Only owners can create new users")
        
        # Cannot create another owner
        if request.role == UserRole.OWNER:
            raise ValueError("Cannot create additional owner accounts")
        
        # Check if username is taken
        if self.get_user_by_username(request.username):
            raise ValueError("Username already taken")
        
        # Check if email is taken
        if self.get_user_by_email(request.email):
            raise ValueError("Email already in use")
        
        now = datetime.now(timezone.utc)
        user_id = str(uuid.uuid4())
        
        # Hash password asynchronously to avoid blocking event loop
        password_hash = await hash_password_async(request.password)
        
        user = UserInDB(
            id=user_id,
            username=request.username.lower(),
            first_name=request.first_name,
            last_name=request.last_name,
            email=request.email.lower(),
            role=request.role,
            password_hash=password_hash,
            created_at=now,
            updated_at=now,
            is_active=True
        )
        
        self._users[user_id] = user
        self._save_users()
        
        logger.info(f"User created: {user.username} (role: {user.role})")
        return self._to_response(user)
    
    def get_user(self, user_id: str) -> Optional[UserInDB]:
        """Get user by ID"""
        return self._users.get(user_id)
    
    def get_user_by_username(self, username: str, include_inactive: bool = False) -> Optional[UserInDB]:
        """Get user by username (only active users by default)"""
        username_lower = username.lower()
        for user in self._users.values():
            if user.username == username_lower:
                if include_inactive or user.is_active:
                    return user
        return None
    
    def get_user_by_email(self, email: str, include_inactive: bool = False) -> Optional[UserInDB]:
        """Get user by email (only active users by default)"""
        email_lower = email.lower()
        for user in self._users.values():
            if user.email == email_lower:
                if include_inactive or user.is_active:
                    return user
        return None
    
    def list_users(self, requester: UserInDB) -> List[UserResponse]:
        """List all users (only owners can see full list)"""
        if requester.role != UserRole.OWNER:
            # Non-owners can only see themselves
            return [self._to_response(requester)]
        
        return [self._to_response(u) for u in self._users.values() if u.is_active]
    
    def get_owner_user(self) -> Optional[UserInDB]:
        """Get the owner user (for internal service use)"""
        for user in self._users.values():
            if user.role == UserRole.OWNER and user.is_active:
                return user
        return None
    
    def get_all_user_ids(self) -> List[str]:
        """Get all active user IDs (for internal service use)"""
        return [user.id for user in self._users.values() if user.is_active]
    
    async def update_user(self, user_id: str, request: UserUpdate, updated_by: UserInDB) -> UserResponse:
        """Update a user"""
        user = self.get_user(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Permission checks
        is_self = user_id == updated_by.id
        is_owner = updated_by.role == UserRole.OWNER
        
        if not is_self and not is_owner:
            raise PermissionError("Cannot update other users")
        
        # Only owners can change roles
        if request.role is not None and not is_owner:
            raise PermissionError("Only owners can change user roles")
        
        # Cannot change owner's role
        if user.role == UserRole.OWNER and request.role is not None and request.role != UserRole.OWNER:
            raise ValueError("Cannot change owner's role")
        
        # Apply updates
        if request.first_name is not None:
            user.first_name = request.first_name
        
        if request.last_name is not None:
            user.last_name = request.last_name
        
        if request.email is not None:
            # Check if email is taken by another user
            existing = self.get_user_by_email(request.email)
            if existing and existing.id != user_id:
                raise ValueError("Email already in use")
            user.email = request.email.lower()
        
        if request.role is not None:
            user.role = request.role
        
        if request.password is not None:
            # Hash password asynchronously to avoid blocking event loop
            user.password_hash = await hash_password_async(request.password)
        
        user.updated_at = datetime.now(timezone.utc)
        
        self._users[user_id] = user
        self._save_users()
        
        logger.info(f"User updated: {user.username}")
        return self._to_response(user)
    
    def delete_user(self, user_id: str, deleted_by: UserInDB) -> bool:
        """Delete a user (soft delete by setting is_active=False)"""
        if deleted_by.role != UserRole.OWNER:
            raise PermissionError("Only owners can delete users")
        
        user = self.get_user(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Cannot delete owner
        if user.role == UserRole.OWNER:
            raise ValueError("Cannot delete owner account")
        
        # Cannot delete yourself
        if user_id == deleted_by.id:
            raise ValueError("Cannot delete your own account")
        
        # Soft delete
        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        self._users[user_id] = user
        self._save_users()
        
        logger.info(f"User deleted: {user.username}")
        return True
    
    # ==================== Authentication ====================
    
    async def authenticate(self, username: str, password: str) -> Optional[UserInDB]:
        """Authenticate user with username and password (async for non-blocking password verification)"""
        user = self.get_user_by_username(username, include_inactive=True)
        if not user:
            logger.debug(f"Authentication failed: user not found ({username})")
            return None
        
        if not user.is_active:
            logger.debug(f"Authentication failed: user inactive ({username})")
            return None
        
        # Verify password asynchronously to avoid blocking event loop
        # This is the slowest operation (~7 seconds avg in load test)
        if not await verify_password_async(password, user.password_hash):
            logger.debug(f"Authentication failed: invalid password ({username})")
            return None
        
        # Update last login
        user.last_login = datetime.now(timezone.utc)
        self._users[user.id] = user
        self._save_users()
        
        logger.info(f"User authenticated: {username}")
        return user
    
    def create_access_token(self, user: UserInDB) -> tuple[str, int]:
        """Create JWT access token for user. Returns (token, expires_in_seconds)"""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=JWT_EXPIRATION_HOURS)
        expires_in = int((expires - now).total_seconds())
        
        payload = {
            "sub": user.id,
            "username": user.username,
            "role": user.role.value,
            "exp": expires,
            "iat": now
        }
        
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return token, expires_in
    
    def verify_token(self, token: str) -> Optional[TokenPayload]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return TokenPayload(
                sub=payload["sub"],
                username=payload["username"],
                role=UserRole(payload["role"]),
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
            )
        except jwt.ExpiredSignatureError:
            logger.debug("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.debug(f"Invalid token: {e}")
            return None
    
    def decode_token_payload(self, token: str) -> Optional[dict]:
        """
        Decode JWT token and return raw payload dict.
        Used to access additional claims like 'service' flag.
        """
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.InvalidTokenError:
            return None
    
    async def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """Change user's password (async for non-blocking password operations)"""
        user = self.get_user(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Verify current password asynchronously
        if not await verify_password_async(current_password, user.password_hash):
            raise ValueError("Current password is incorrect")
        
        # Hash new password asynchronously
        user.password_hash = await hash_password_async(new_password)
        user.updated_at = datetime.now(timezone.utc)
        self._users[user_id] = user
        self._save_users()
        
        logger.info(f"Password changed for user: {user.username}")
        return True
    
    # ==================== Helpers ====================
    
    def _to_response(self, user: UserInDB) -> UserResponse:
        """Convert UserInDB to UserResponse (strips password)"""
        return UserResponse(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            role=user.role,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=user.last_login,
            is_active=user.is_active
        )
    
    def get_permissions(self, role: UserRole) -> List[str]:
        """Get list of permission strings for a role"""
        # All users can create and manage their own networks
        permissions = ["read:own_networks", "write:own_networks", "create:networks"]
        
        if role in [UserRole.ADMIN, UserRole.OWNER]:
            permissions.extend([
                "manage:users",
                "read:users",
                "write:users",
                "invite:users"
            ])
        
        if role == UserRole.OWNER:
            permissions.extend([
                "delete:users",
                "admin:settings",
                "manage:all"
            ])
        
        return permissions
    
    # ==================== Invitations ====================
    
    def _load_invites(self) -> None:
        """Load invitations from JSON file"""
        if self.invites_file.exists():
            try:
                with open(self.invites_file, 'r') as f:
                    data = json.load(f)
                    for invite_data in data.get("invites", []):
                        invite = InviteInDB(**invite_data)
                        self._invites[invite.id] = invite
                logger.info(f"Loaded {len(self._invites)} invites from {self.invites_file}")
            except Exception as e:
                logger.error(f"Failed to load invites: {e}")
                self._invites = {}
        else:
            logger.info("No invites file found, starting fresh")
            self._invites = {}
    
    def _save_invites(self) -> None:
        """Save invitations to JSON file"""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            invites_data = {
                "invites": [invite.model_dump(mode='json') for invite in self._invites.values()]
            }
            with open(self.invites_file, 'w') as f:
                json.dump(invites_data, f, indent=2, default=str)
            logger.debug(f"Saved {len(self._invites)} invites to {self.invites_file}")
        except Exception as e:
            logger.error(f"Failed to save invites: {e}")
            raise
    
    def _generate_invite_token(self) -> str:
        """Generate a secure random token for invitations"""
        return secrets.token_urlsafe(32)
    
    def create_invite(self, request: InviteCreate, invited_by: UserInDB) -> tuple[InviteInDB, bool]:
        """
        Create an invitation for a new user.
        Returns (invite, email_sent) tuple.
        """
        if invited_by.role != UserRole.OWNER:
            raise PermissionError("Only owners can invite new users")
        
        # Check if email already has an active user
        existing_user = self.get_user_by_email(request.email)
        if existing_user and existing_user.is_active:
            raise ValueError("A user with this email already exists")
        
        # Check for existing pending invite to same email
        for invite in self._invites.values():
            if (invite.email.lower() == request.email.lower() and 
                invite.status == InviteStatus.PENDING and
                invite.expires_at > datetime.now(timezone.utc)):
                raise ValueError("An active invitation already exists for this email")
        
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=self.INVITE_EXPIRATION_HOURS)
        
        invite_id = str(uuid.uuid4())
        token = self._generate_invite_token()
        
        invite = InviteInDB(
            id=invite_id,
            email=request.email.lower(),
            role=request.role,
            status=InviteStatus.PENDING,
            invited_by=invited_by.username,
            invited_by_name=f"{invited_by.first_name} {invited_by.last_name}",
            invited_by_id=invited_by.id,
            token=token,
            created_at=now,
            expires_at=expires_at
        )
        
        self._invites[invite_id] = invite
        self._save_invites()
        
        # Try to send email
        email_sent = False
        try:
            from .email_service import send_invitation_email, is_email_configured
            
            if is_email_configured():
                email_id = send_invitation_email(
                    to_email=invite.email,
                    invite_token=token,
                    invited_by_name=invite.invited_by_name,
                    role=invite.role.value,
                    expires_hours=self.INVITE_EXPIRATION_HOURS
                )
                email_sent = email_id is not None
            else:
                logger.warning("Email not configured - invite created but email not sent")
        except Exception as e:
            logger.error(f"Failed to send invitation email: {e}")
        
        logger.info(f"Invitation created for {invite.email} by {invited_by.username} (email_sent={email_sent})")
        return invite, email_sent
    
    def get_invite_by_token(self, token: str) -> Optional[InviteInDB]:
        """Get invitation by token"""
        for invite in self._invites.values():
            if invite.token == token:
                return invite
        return None
    
    def get_invite_token_info(self, token: str) -> Optional[InviteTokenInfo]:
        """Get public info about an invite token (for the accept page)"""
        invite = self.get_invite_by_token(token)
        if not invite:
            return None
        
        now = datetime.now(timezone.utc)
        is_valid = (
            invite.status == InviteStatus.PENDING and
            invite.expires_at > now
        )
        
        return InviteTokenInfo(
            email=invite.email,
            role=invite.role,
            invited_by_name=invite.invited_by_name,
            expires_at=invite.expires_at,
            is_valid=is_valid
        )
    
    async def accept_invite(
        self, 
        token: str, 
        username: str, 
        first_name: str, 
        last_name: str, 
        password: str
    ) -> UserResponse:
        """Accept an invitation and create the user account (async for password hashing)"""
        invite = self.get_invite_by_token(token)
        if not invite:
            raise ValueError("Invalid invitation token")
        
        if invite.status != InviteStatus.PENDING:
            raise ValueError(f"Invitation is no longer valid (status: {invite.status})")
        
        now = datetime.now(timezone.utc)
        if invite.expires_at <= now:
            # Mark as expired
            invite.status = InviteStatus.EXPIRED
            self._invites[invite.id] = invite
            self._save_invites()
            raise ValueError("Invitation has expired")
        
        # Check if username is taken
        if self.get_user_by_username(username):
            raise ValueError("Username already taken")
        
        # Check if email is taken (shouldn't happen but double-check)
        existing = self.get_user_by_email(invite.email)
        if existing and existing.is_active:
            raise ValueError("A user with this email already exists")
        
        # Hash password asynchronously to avoid blocking event loop
        password_hash = await hash_password_async(password)
        
        # Create the user
        user_id = str(uuid.uuid4())
        user = UserInDB(
            id=user_id,
            username=username.lower(),
            first_name=first_name,
            last_name=last_name,
            email=invite.email,
            role=invite.role,
            password_hash=password_hash,
            created_at=now,
            updated_at=now,
            is_active=True
        )
        
        self._users[user_id] = user
        self._save_users()
        
        # Mark invitation as accepted
        invite.status = InviteStatus.ACCEPTED
        invite.accepted_at = now
        self._invites[invite.id] = invite
        self._save_invites()
        
        logger.info(f"Invitation accepted: {invite.email} -> {username}")
        return self._to_response(user)
    
    def list_invites(self, requester: UserInDB) -> List[InviteResponse]:
        """List all invitations (owner only)"""
        if requester.role != UserRole.OWNER:
            raise PermissionError("Only owners can view invitations")
        
        # Update expired invites
        now = datetime.now(timezone.utc)
        for invite in self._invites.values():
            if invite.status == InviteStatus.PENDING and invite.expires_at <= now:
                invite.status = InviteStatus.EXPIRED
        self._save_invites()
        
        return [self._invite_to_response(inv) for inv in self._invites.values()]
    
    def revoke_invite(self, invite_id: str, revoked_by: UserInDB) -> bool:
        """Revoke a pending invitation"""
        if revoked_by.role != UserRole.OWNER:
            raise PermissionError("Only owners can revoke invitations")
        
        invite = self._invites.get(invite_id)
        if not invite:
            raise ValueError("Invitation not found")
        
        if invite.status != InviteStatus.PENDING:
            raise ValueError(f"Cannot revoke invitation with status: {invite.status}")
        
        invite.status = InviteStatus.REVOKED
        self._invites[invite_id] = invite
        self._save_invites()
        
        logger.info(f"Invitation revoked: {invite.email} by {revoked_by.username}")
        return True
    
    def resend_invite(self, invite_id: str, resent_by: UserInDB) -> bool:
        """Resend an invitation email"""
        if resent_by.role != UserRole.OWNER:
            raise PermissionError("Only owners can resend invitations")
        
        invite = self._invites.get(invite_id)
        if not invite:
            raise ValueError("Invitation not found")
        
        if invite.status != InviteStatus.PENDING:
            raise ValueError(f"Cannot resend invitation with status: {invite.status}")
        
        # Check if expired and extend if needed
        now = datetime.now(timezone.utc)
        if invite.expires_at <= now:
            # Extend the invitation
            invite.expires_at = now + timedelta(hours=self.INVITE_EXPIRATION_HOURS)
            self._invites[invite_id] = invite
            self._save_invites()
        
        # Try to send email
        try:
            from .email_service import send_invitation_email, is_email_configured
            
            if not is_email_configured():
                raise ValueError("Email is not configured")
            
            remaining_hours = int((invite.expires_at - now).total_seconds() / 3600)
            email_id = send_invitation_email(
                to_email=invite.email,
                invite_token=invite.token,
                invited_by_name=invite.invited_by_name,
                role=invite.role.value,
                expires_hours=remaining_hours
            )
            
            if not email_id:
                raise ValueError("Failed to send email")
            
            logger.info(f"Invitation resent to {invite.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resend invitation email: {e}")
            raise ValueError(f"Failed to send email: {e}")
    
    def _invite_to_response(self, invite: InviteInDB) -> InviteResponse:
        """Convert InviteInDB to InviteResponse (strips token)"""
        return InviteResponse(
            id=invite.id,
            email=invite.email,
            role=invite.role,
            status=invite.status,
            invited_by=invite.invited_by,
            invited_by_name=invite.invited_by_name,
            created_at=invite.created_at,
            expires_at=invite.expires_at,
            accepted_at=invite.accepted_at
        )


# Singleton instance
auth_service = AuthService()
