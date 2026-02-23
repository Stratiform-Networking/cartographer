"""
Auth service with PostgreSQL database persistence.
Handles user authentication and management.
"""

import asyncio
import hashlib
import logging
import secrets
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db_models import Invite, InviteStatus, PasswordResetToken, User, UserRole
from ..models import (
    InviteCreate,
    InviteResponse,
    InviteTokenInfo,
    OwnerSetupRequest,
    TokenPayload,
    UserCreate,
    UserPreferences,
    UserPreferencesUpdate,
    UserResponse,
    UserUpdate,
)
from .plan_settings import apply_plan_to_user

logger = logging.getLogger(__name__)

# Password hashing - configured for better performance under load
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=10)

# Thread pool for CPU-bound password hashing operations
_password_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="pwd_hash_")


async def hash_password_async(password: str) -> str:
    """Hash a password asynchronously using a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_password_executor, pwd_context.hash, password)


async def verify_password_async(password: str, hash: str) -> bool:
    """Verify a password asynchronously using a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_password_executor, pwd_context.verify, password, hash)


class AuthService:
    """Handles user authentication and management with PostgreSQL persistence."""

    @property
    def INVITE_EXPIRATION_HOURS(self) -> int:
        """Get invite expiration hours from config (backwards compatible property)."""
        return settings.invite_expiration_hours

    # ==================== Setup & Status ====================

    async def is_setup_complete(self, db: AsyncSession) -> bool:
        """Check if initial setup (owner creation) is complete."""
        result = await db.execute(
            select(User).where(
                and_(User.role == UserRole.OWNER, User.is_active == True)  # noqa: E712
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_setup_status(self, db: AsyncSession) -> dict:
        """Get current setup status."""
        owner_result = await db.execute(
            select(User).where(
                and_(User.role == UserRole.OWNER, User.is_active == True)  # noqa: E712
            )
        )
        owner_exists = owner_result.scalar_one_or_none() is not None

        count_result = await db.execute(select(User).where(User.is_active == True))  # noqa: E712
        total_users = len(count_result.scalars().all())

        return {
            "is_setup_complete": owner_exists,
            "owner_exists": owner_exists,
            "total_users": total_users,
        }

    async def setup_owner(self, db: AsyncSession, request: OwnerSetupRequest) -> UserResponse:
        """Create the initial owner account (only works if no owner exists)."""
        if await self.is_setup_complete(db):
            raise ValueError("Setup already complete - owner account exists")

        # Check if username is taken
        if await self.get_user_by_username(db, request.username, include_inactive=True):
            raise ValueError("Username already taken")

        # Check if email is taken
        if await self.get_user_by_email(db, request.email, include_inactive=True):
            raise ValueError("Email already in use")

        password_hash = await hash_password_async(request.password)

        now = datetime.now(timezone.utc)
        user = User(
            id=str(uuid.uuid4()),
            username=request.username.lower(),
            first_name=request.first_name,
            last_name=request.last_name,
            email=request.email.lower(),
            role=UserRole.OWNER,
            hashed_password=password_hash,
            is_active=True,
            is_verified=True,
            created_at=now,
            updated_at=now,
        )

        db.add(user)
        await apply_plan_to_user(db, user.id, None, commit=False)
        try:
            await db.commit()
        except IntegrityError as e:
            await db.rollback()
            raise self._map_integrity_error(e)
        await db.refresh(user)

        logger.info(f"Owner account created: {user.username}")
        return self._to_response(user)

    # ==================== User CRUD ====================

    async def create_user(
        self, db: AsyncSession, request: UserCreate, created_by: User
    ) -> UserResponse:
        """Create a new user (only owners can create users)."""
        if created_by.role != UserRole.OWNER:
            raise PermissionError("Only owners can create new users")

        if request.role == UserRole.OWNER:
            raise ValueError("Cannot create additional owner accounts")

        if await self.get_user_by_username(db, request.username, include_inactive=True):
            raise ValueError("Username already taken")

        if await self.get_user_by_email(db, request.email, include_inactive=True):
            raise ValueError("Email already in use")

        password_hash = await hash_password_async(request.password)

        now = datetime.now(timezone.utc)
        user = User(
            id=str(uuid.uuid4()),
            username=request.username.lower(),
            first_name=request.first_name,
            last_name=request.last_name,
            email=request.email.lower(),
            role=request.role,
            hashed_password=password_hash,
            is_active=True,
            is_verified=True,
            created_at=now,
            updated_at=now,
        )

        db.add(user)
        await apply_plan_to_user(db, user.id, None, commit=False)
        try:
            await db.commit()
        except IntegrityError as e:
            await db.rollback()
            raise self._map_integrity_error(e)
        await db.refresh(user)

        logger.info(f"User created: {user.username} (role: {user.role})")
        return self._to_response(user)

    async def register_user(self, db: AsyncSession, request: UserCreate) -> tuple[User, str, int]:
        """
        Register a new user via open registration (cloud deployments).

        Creates a user with member role and returns the user, token, and expiration.
        This is the service-layer method for the /register endpoint.

        Returns:
            Tuple of (User, access_token, expires_in_seconds)

        Raises:
            ValueError: If username/email is taken or registration is disabled
        """
        if not settings.allow_open_registration:
            raise ValueError("Open registration is disabled. Use an invite to create an account.")

        if await self.get_user_by_username(db, request.username, include_inactive=True):
            raise ValueError("Username already taken")

        if await self.get_user_by_email(db, request.email, include_inactive=True):
            raise ValueError("Email already in use")

        password_hash = await hash_password_async(request.password)

        now = datetime.now(timezone.utc)
        user = User(
            id=str(uuid.uuid4()),
            username=request.username.lower(),
            first_name=request.first_name,
            last_name=request.last_name,
            email=request.email.lower(),
            role=UserRole.MEMBER,
            hashed_password=password_hash,
            is_active=True,
            is_verified=True,
            created_at=now,
            updated_at=now,
        )

        db.add(user)
        await apply_plan_to_user(db, user.id, None, commit=False)
        try:
            await db.commit()
        except IntegrityError as e:
            await db.rollback()
            raise self._map_integrity_error(e)
        await db.refresh(user)

        logger.info(f"User registered: {user.username}")

        # Create access token
        token, expires_in = self.create_access_token(user)
        return user, token, expires_in

    async def get_user(self, db: AsyncSession, user_id: str) -> User | None:
        """Get user by ID."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_username(
        self, db: AsyncSession, username: str, include_inactive: bool = False
    ) -> User | None:
        """Get user by username."""
        username_lower = username.lower()
        query = select(User).where(User.username == username_lower)
        if not include_inactive:
            query = query.where(User.is_active == True)  # noqa: E712
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_by_email(
        self, db: AsyncSession, email: str, include_inactive: bool = False
    ) -> User | None:
        """Get user by email."""
        email_lower = email.lower()
        query = select(User).where(User.email == email_lower)
        if not include_inactive:
            query = query.where(User.is_active == True)  # noqa: E712
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def list_users(self, db: AsyncSession, requester: User) -> list[UserResponse]:
        """List all users (only owners can see full list)."""
        if requester.role != UserRole.OWNER:
            return [self._to_response(requester)]

        result = await db.execute(select(User).where(User.is_active == True))  # noqa: E712
        users = result.scalars().all()
        return [self._to_response(u) for u in users]

    async def get_owner_user(self, db: AsyncSession) -> User | None:
        """Get the owner user (for internal service use)."""
        result = await db.execute(
            select(User).where(
                and_(User.role == UserRole.OWNER, User.is_active == True)  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def get_all_user_ids(self, db: AsyncSession) -> list[str]:
        """Get all active user IDs (for internal service use)."""
        result = await db.execute(select(User.id).where(User.is_active == True))  # noqa: E712
        return [row[0] for row in result.all()]

    async def update_user(
        self, db: AsyncSession, user_id: str, request: UserUpdate, updated_by: User
    ) -> UserResponse:
        """Update a user."""
        user = await self.get_user(db, user_id)
        if not user:
            raise ValueError("User not found")

        is_self = user_id == updated_by.id
        is_owner = updated_by.role == UserRole.OWNER

        if not is_self and not is_owner:
            raise PermissionError("Cannot update other users")

        if request.role is not None and not is_owner:
            raise PermissionError("Only owners can change user roles")

        if (
            user.role == UserRole.OWNER
            and request.role is not None
            and request.role != UserRole.OWNER
        ):
            raise ValueError("Cannot change owner's role")

        if request.first_name is not None:
            user.first_name = request.first_name

        if request.last_name is not None:
            user.last_name = request.last_name

        if request.email is not None:
            existing = await self.get_user_by_email(db, request.email, include_inactive=True)
            if existing and existing.id != user_id:
                raise ValueError("Email already in use")
            user.email = request.email.lower()

        if request.role is not None:
            user.role = request.role

        if request.password is not None:
            user.hashed_password = await hash_password_async(request.password)

        try:
            await db.commit()
        except IntegrityError as e:
            await db.rollback()
            raise self._map_integrity_error(e)
        await db.refresh(user)

        logger.info(f"User updated: {user.username}")
        return self._to_response(user)

    async def delete_user(self, db: AsyncSession, user_id: str, deleted_by: User) -> bool:
        """Delete a user (soft delete by setting is_active=False)."""
        if deleted_by.role != UserRole.OWNER:
            raise PermissionError("Only owners can delete users")

        user = await self.get_user(db, user_id)
        if not user:
            raise ValueError("User not found")

        if user.role == UserRole.OWNER:
            raise ValueError("Cannot delete owner account")

        if user_id == deleted_by.id:
            raise ValueError("Cannot delete your own account")

        user.is_active = False
        await db.commit()

        logger.info(f"User deleted: {user.username}")
        return True

    # ==================== Preferences ====================

    async def get_preferences(self, user: User) -> UserPreferences:
        """Get user preferences."""
        prefs = user.preferences or {}
        return UserPreferences(**prefs)

    async def update_preferences(
        self, db: AsyncSession, user: User, request: UserPreferencesUpdate
    ) -> UserPreferences:
        """
        Update user preferences (partial update).

        Only updates fields that are explicitly set in the request.
        Setting a field to None removes it from preferences.
        """
        # Get existing preferences or empty dict
        current_prefs = user.preferences or {}

        # Merge in new preferences (only non-None values)
        update_data = request.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                current_prefs[key] = value
            elif key in current_prefs:
                # Allow explicit None to remove a preference
                del current_prefs[key]

        # Update in database
        user.preferences = current_prefs if current_prefs else None
        await db.commit()
        await db.refresh(user)

        logger.info(f"User preferences updated: {user.username}")
        return UserPreferences(**(user.preferences or {}))

    # ==================== Authentication ====================

    async def authenticate(self, db: AsyncSession, username: str, password: str) -> User | None:
        """Authenticate user with username and password."""
        user = await self.get_user_by_username(db, username, include_inactive=True)
        if not user:
            logger.debug(f"Authentication failed: user not found ({username})")
            return None

        if not user.is_active:
            logger.debug(f"Authentication failed: user inactive ({username})")
            return None

        if not await verify_password_async(password, user.hashed_password):
            logger.debug(f"Authentication failed: invalid password ({username})")
            return None

        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(user)  # Refresh to reload all attributes after commit

        logger.info(f"User authenticated: {username}")
        return user

    def create_access_token(self, user: User) -> tuple[str, int]:
        """Create JWT access token for user. Returns (token, expires_in_seconds)."""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=settings.jwt_expiration_hours)
        expires_in = int((expires - now).total_seconds())

        payload = {
            "sub": user.id,
            "username": user.username,
            "role": user.role.value,
            "exp": expires,
            "iat": now,
        }

        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        return token, expires_in

    def verify_token(self, token: str) -> TokenPayload | None:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            return TokenPayload(
                sub=payload["sub"],
                username=payload["username"],
                role=UserRole(payload["role"]),
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
            )
        except jwt.ExpiredSignatureError:
            logger.debug("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.debug(f"Invalid token: {e}")
            return None

    def decode_token_payload(self, token: str) -> dict | None:
        """Decode JWT token and return raw payload dict."""
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            return payload
        except jwt.InvalidTokenError:
            return None

    async def change_password(
        self, db: AsyncSession, user_id: str, current_password: str, new_password: str
    ) -> bool:
        """Change user's password."""
        user = await self.get_user(db, user_id)
        if not user:
            raise ValueError("User not found")

        if not await verify_password_async(current_password, user.hashed_password):
            raise ValueError("Current password is incorrect")

        user.hashed_password = await hash_password_async(new_password)
        await db.commit()

        logger.info(f"Password changed for user: {user.username}")
        return True

    async def request_password_reset(self, db: AsyncSession, email: str) -> bool:
        """
        Request a password reset email.

        Always returns success semantics so callers don't leak account existence.
        """
        email_normalized = email.strip().lower()
        user = await self.get_user_by_email(db, email_normalized, include_inactive=False)
        if not user:
            logger.info("Password reset requested for unknown email: %s", email_normalized)
            return True

        now = datetime.now(timezone.utc)
        raw_token = self._generate_password_reset_token()
        token_hash = self._hash_password_reset_token(raw_token)
        expires_at = now + timedelta(minutes=settings.password_reset_expiration_minutes)

        # Invalidate older active reset tokens so only the latest link is usable.
        existing_tokens_result = await db.execute(
            select(PasswordResetToken).where(
                and_(
                    PasswordResetToken.user_id == user.id,
                    PasswordResetToken.used_at.is_(None),
                    PasswordResetToken.expires_at > now,
                )
            )
        )
        for token in existing_tokens_result.scalars().all():
            token.used_at = now

        reset_token = PasswordResetToken(
            id=str(uuid.uuid4()),
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(reset_token)
        await db.commit()

        try:
            from .email_service import is_email_configured, send_password_reset_email

            if is_email_configured():
                email_id = send_password_reset_email(
                    to_email=user.email,
                    reset_token=raw_token,
                    expires_minutes=settings.password_reset_expiration_minutes,
                )
                if not email_id:
                    logger.warning("Password reset email send failed for user: %s", user.username)
            else:
                logger.warning(
                    "Email not configured - password reset email not sent for %s", user.email
                )
        except Exception as e:
            logger.error(f"Failed to send password reset email: {e}")

        logger.info("Password reset requested for user: %s", user.username)
        return True

    async def confirm_password_reset(self, db: AsyncSession, token: str, new_password: str) -> bool:
        """Confirm password reset with a one-time token."""
        token_hash = self._hash_password_reset_token(token)
        now = datetime.now(timezone.utc)

        reset_result = await db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        reset_token = reset_result.scalar_one_or_none()

        if not reset_token or reset_token.used_at is not None or reset_token.expires_at <= now:
            raise ValueError("Invalid or expired reset token")

        user = await self.get_user(db, reset_token.user_id)
        if not user or not user.is_active:
            raise ValueError("Invalid or expired reset token")

        user.hashed_password = await hash_password_async(new_password)

        # Invalidate all currently active reset tokens for this user.
        tokens_result = await db.execute(
            select(PasswordResetToken).where(
                and_(
                    PasswordResetToken.user_id == user.id,
                    PasswordResetToken.used_at.is_(None),
                    PasswordResetToken.expires_at > now,
                )
            )
        )
        for token_row in tokens_result.scalars().all():
            token_row.used_at = now

        await db.commit()
        logger.info("Password reset completed for user: %s", user.username)
        return True

    # ==================== Helpers ====================

    def _to_response(self, user: User) -> UserResponse:
        """Convert User to UserResponse (strips password)."""
        return UserResponse(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            role=user.role,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=user.last_login_at,
            is_active=user.is_active,
        )

    def get_permissions(self, role: UserRole) -> list[str]:
        """Get list of permission strings for a role."""
        permissions = ["read:own_networks", "write:own_networks", "create:networks"]

        if role in [UserRole.ADMIN, UserRole.OWNER]:
            permissions.extend(["manage:users", "read:users", "write:users", "invite:users"])

        if role == UserRole.OWNER:
            permissions.extend(["delete:users", "admin:settings", "manage:all"])

        return permissions

    # ==================== Invitations ====================

    def _generate_invite_token(self) -> str:
        """Generate a secure random token for invitations."""
        return secrets.token_urlsafe(32)

    def _generate_password_reset_token(self) -> str:
        """Generate a secure random token for password resets."""
        return secrets.token_urlsafe(48)

    def _hash_password_reset_token(self, token: str) -> str:
        """Hash a raw password reset token for database storage."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def create_invite(
        self, db: AsyncSession, request: InviteCreate, invited_by: User
    ) -> tuple[Invite, bool]:
        """Create an invitation for a new user."""
        if invited_by.role != UserRole.OWNER:
            raise PermissionError("Only owners can invite new users")

        existing_user = await self.get_user_by_email(db, request.email, include_inactive=True)
        if existing_user:
            raise ValueError("A user with this email already exists")

        # Check for existing pending invite
        result = await db.execute(
            select(Invite).where(
                and_(
                    Invite.email == request.email.lower(),
                    Invite.status == InviteStatus.PENDING,
                    Invite.expires_at > datetime.now(timezone.utc),
                )
            )
        )
        if result.scalar_one_or_none():
            raise ValueError("An active invitation already exists for this email")

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=settings.invite_expiration_hours)
        token = self._generate_invite_token()

        invite = Invite(
            id=str(uuid.uuid4()),
            email=request.email.lower(),
            role=request.role,
            status=InviteStatus.PENDING,
            token=token,
            invited_by_id=invited_by.id,
            invited_by_username=invited_by.username,
            invited_by_name=f"{invited_by.first_name} {invited_by.last_name}",
            expires_at=expires_at,
        )

        db.add(invite)
        await db.commit()
        await db.refresh(invite)

        # Try to send email
        email_sent = False
        try:
            from .email_service import is_email_configured, send_invitation_email

            if is_email_configured():
                email_id = send_invitation_email(
                    to_email=invite.email,
                    invite_token=token,
                    invited_by_name=invite.invited_by_name,
                    role=invite.role.value,
                    expires_hours=settings.invite_expiration_hours,
                )
                email_sent = email_id is not None
            else:
                logger.warning("Email not configured - invite created but email not sent")
        except Exception as e:
            logger.error(f"Failed to send invitation email: {e}")

        logger.info(
            f"Invitation created for {invite.email} by {invited_by.username} (email_sent={email_sent})"
        )
        return invite, email_sent

    async def get_invite_by_token(self, db: AsyncSession, token: str) -> Invite | None:
        """Get invitation by token."""
        result = await db.execute(select(Invite).where(Invite.token == token))
        return result.scalar_one_or_none()

    async def get_invite_token_info(self, db: AsyncSession, token: str) -> InviteTokenInfo | None:
        """Get public info about an invite token."""
        invite = await self.get_invite_by_token(db, token)
        if not invite:
            return None

        now = datetime.now(timezone.utc)
        is_valid = invite.status == InviteStatus.PENDING and invite.expires_at > now

        return InviteTokenInfo(
            email=invite.email,
            role=invite.role,
            invited_by_name=invite.invited_by_name,
            expires_at=invite.expires_at,
            is_valid=is_valid,
        )

    async def accept_invite(
        self,
        db: AsyncSession,
        token: str,
        username: str,
        first_name: str,
        last_name: str,
        password: str,
    ) -> UserResponse:
        """Accept an invitation and create the user account."""
        invite = await self.get_invite_by_token(db, token)
        if not invite:
            raise ValueError("Invalid invitation token")

        if invite.status != InviteStatus.PENDING:
            raise ValueError(f"Invitation is no longer valid (status: {invite.status})")

        now = datetime.now(timezone.utc)
        if invite.expires_at <= now:
            invite.status = InviteStatus.EXPIRED
            await db.commit()
            raise ValueError("Invitation has expired")

        if await self.get_user_by_username(db, username, include_inactive=True):
            raise ValueError("Username already taken")

        existing = await self.get_user_by_email(db, invite.email, include_inactive=True)
        if existing:
            raise ValueError("A user with this email already exists")

        password_hash = await hash_password_async(password)

        user = User(
            id=str(uuid.uuid4()),
            username=username.lower(),
            first_name=first_name,
            last_name=last_name,
            email=invite.email,
            role=invite.role,
            hashed_password=password_hash,
            is_active=True,
            is_verified=True,
            created_at=now,
            updated_at=now,
        )

        db.add(user)
        await apply_plan_to_user(db, user.id, None, commit=False)

        invite.status = InviteStatus.ACCEPTED
        invite.accepted_at = now

        try:
            await db.commit()
        except IntegrityError as e:
            await db.rollback()
            raise self._map_integrity_error(e)
        await db.refresh(user)

        logger.info(f"Invitation accepted: {invite.email} -> {username}")
        return self._to_response(user)

    async def list_invites(self, db: AsyncSession, requester: User) -> list[InviteResponse]:
        """List all invitations (owner only)."""
        if requester.role != UserRole.OWNER:
            raise PermissionError("Only owners can view invitations")

        # Update expired invites
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(Invite).where(
                and_(Invite.status == InviteStatus.PENDING, Invite.expires_at <= now)
            )
        )
        for invite in result.scalars().all():
            invite.status = InviteStatus.EXPIRED
        await db.commit()

        # Get all invites
        result = await db.execute(select(Invite))
        invites = result.scalars().all()
        return [self._invite_to_response(inv) for inv in invites]

    async def revoke_invite(self, db: AsyncSession, invite_id: str, revoked_by: User) -> bool:
        """Revoke a pending invitation."""
        if revoked_by.role != UserRole.OWNER:
            raise PermissionError("Only owners can revoke invitations")

        result = await db.execute(select(Invite).where(Invite.id == invite_id))
        invite = result.scalar_one_or_none()

        if not invite:
            raise ValueError("Invitation not found")

        if invite.status != InviteStatus.PENDING:
            raise ValueError(f"Cannot revoke invitation with status: {invite.status}")

        invite.status = InviteStatus.REVOKED
        await db.commit()

        logger.info(f"Invitation revoked: {invite.email} by {revoked_by.username}")
        return True

    async def resend_invite(self, db: AsyncSession, invite_id: str, resent_by: User) -> bool:
        """Resend an invitation email."""
        if resent_by.role != UserRole.OWNER:
            raise PermissionError("Only owners can resend invitations")

        result = await db.execute(select(Invite).where(Invite.id == invite_id))
        invite = result.scalar_one_or_none()

        if not invite:
            raise ValueError("Invitation not found")

        if invite.status != InviteStatus.PENDING:
            raise ValueError(f"Cannot resend invitation with status: {invite.status}")

        now = datetime.now(timezone.utc)
        if invite.expires_at <= now:
            invite.expires_at = now + timedelta(hours=settings.invite_expiration_hours)
            await db.commit()

        try:
            from .email_service import is_email_configured, send_invitation_email

            if not is_email_configured():
                raise ValueError("Email is not configured")

            remaining_hours = int((invite.expires_at - now).total_seconds() / 3600)
            email_id = send_invitation_email(
                to_email=invite.email,
                invite_token=invite.token,
                invited_by_name=invite.invited_by_name,
                role=invite.role.value,
                expires_hours=remaining_hours,
            )

            if not email_id:
                raise ValueError("Failed to send email")

            logger.info(f"Invitation resent to {invite.email}")
            return True

        except Exception as e:
            logger.error(f"Failed to resend invitation email: {e}")
            raise ValueError(f"Failed to send email: {e}")

    def _invite_to_response(self, invite: Invite) -> InviteResponse:
        """Convert Invite to InviteResponse (strips token)."""
        return InviteResponse(
            id=invite.id,
            email=invite.email,
            role=invite.role,
            status=invite.status,
            invited_by=invite.invited_by_username,
            invited_by_name=invite.invited_by_name,
            created_at=invite.created_at,
            expires_at=invite.expires_at,
            accepted_at=invite.accepted_at,
        )

    def _map_integrity_error(self, error: IntegrityError) -> ValueError:
        """Convert DB integrity errors into user-friendly validation errors."""
        message = str(error).lower()
        if "ix_users_username" in message or "users_username_key" in message:
            return ValueError("Username already taken")
        if "ix_users_email" in message or "users_email_key" in message:
            return ValueError("Email already in use")
        return ValueError("Operation failed due to a database constraint")


# Singleton instance
auth_service = AuthService()
