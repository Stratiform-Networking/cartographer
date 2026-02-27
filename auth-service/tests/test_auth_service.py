"""
Unit tests for auth_service module.
Tests for the database-backed AuthService.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import settings
from app.models import UserResponse, UserRole
from app.services.auth_service import AuthService, hash_password_async, verify_password_async


class TestPasswordHashing:
    """Tests for password hashing functions"""

    async def test_hash_password(self):
        """Should hash password"""
        password = "testpassword123"
        hashed = await hash_password_async(password)

        assert hashed != password
        assert hashed.startswith("$2b$")

    async def test_verify_password(self):
        """Should verify correct password"""
        password = "testpassword123"
        hashed = await hash_password_async(password)

        is_valid = await verify_password_async(password, hashed)

        assert is_valid is True

    async def test_verify_wrong_password(self):
        """Should reject wrong password"""
        password = "testpassword123"
        hashed = await hash_password_async(password)

        is_valid = await verify_password_async("wrongpassword", hashed)

        assert is_valid is False


class TestTokenOperations:
    """Tests for JWT token operations"""

    def test_create_access_token(self):
        """Should create valid access token"""
        from unittest.mock import MagicMock

        from app.db_models import User

        service = AuthService()

        # Create mock user
        mock_user = MagicMock(spec=User)
        mock_user.id = "test-user-123"
        mock_user.username = "testuser"
        mock_user.role = UserRole.MEMBER

        token, expires_in = service.create_access_token(mock_user)

        assert token is not None
        assert len(token) > 0
        assert expires_in > 0

    def test_verify_token_valid(self):
        """Should verify valid token"""
        from unittest.mock import MagicMock

        from app.db_models import User

        service = AuthService()

        # Create mock user
        mock_user = MagicMock(spec=User)
        mock_user.id = "test-user-123"
        mock_user.username = "testuser"
        mock_user.role = UserRole.MEMBER

        token, _ = service.create_access_token(mock_user)
        payload = service.verify_token(token)

        assert payload is not None
        assert payload.sub == mock_user.id
        assert payload.username == mock_user.username
        assert payload.role == mock_user.role

    def test_verify_token_invalid(self):
        """Should return None for invalid token"""
        service = AuthService()

        payload = service.verify_token("invalid-token")

        assert payload is None

    def test_verify_token_expired(self):
        """Should return None for expired token"""
        import jwt

        service = AuthService()
        now = datetime.now(timezone.utc)

        # Create an expired token
        payload = {
            "sub": "test-user",
            "username": "test",
            "role": "member",
            "iat": now - timedelta(hours=48),
            "exp": now - timedelta(hours=24),  # Expired 24 hours ago
        }
        expired_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        result = service.verify_token(expired_token)

        assert result is None

    def test_decode_token_payload_valid(self):
        """Should decode valid token payload"""
        from unittest.mock import MagicMock

        from app.db_models import User

        service = AuthService()

        mock_user = MagicMock(spec=User)
        mock_user.id = "test-user-123"
        mock_user.username = "testuser"
        mock_user.role = UserRole.MEMBER

        token, _ = service.create_access_token(mock_user)
        payload = service.decode_token_payload(token)

        assert payload is not None
        assert payload["sub"] == mock_user.id

    def test_decode_token_payload_invalid(self):
        """Should return None for invalid token"""
        service = AuthService()

        payload = service.decode_token_payload("invalid-token")

        assert payload is None


class TestPermissions:
    """Tests for permission methods"""

    def test_get_permissions_owner(self):
        """Owner should have all permissions"""
        service = AuthService()

        perms = service.get_permissions(UserRole.OWNER)

        assert "read:users" in perms
        assert "write:users" in perms
        assert "delete:users" in perms
        assert "manage:all" in perms

    def test_get_permissions_admin(self):
        """Admin should have read/write permissions"""
        service = AuthService()

        perms = service.get_permissions(UserRole.ADMIN)

        assert "read:users" in perms
        assert "write:users" in perms

    def test_get_permissions_member(self):
        """Member should have limited permissions"""
        service = AuthService()

        perms = service.get_permissions(UserRole.MEMBER)

        assert "read:own_networks" in perms
        assert "write:own_networks" in perms


class TestServiceInit:
    """Tests for service initialization"""

    def test_init(self):
        """Should initialize AuthService"""
        service = AuthService()

        assert service is not None
        assert service.INVITE_EXPIRATION_HOURS > 0


class TestToResponse:
    """Tests for _to_response helper"""

    def test_to_response(self):
        """Should convert User to UserResponse"""
        from app.db_models import User

        service = AuthService()

        mock_user = MagicMock(spec=User)
        mock_user.id = "test-123"
        mock_user.username = "testuser"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.email = "test@example.com"
        mock_user.avatar_url = "https://example.com/avatar.jpg"
        mock_user.role = UserRole.MEMBER
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.updated_at = datetime.now(timezone.utc)
        mock_user.last_login_at = None
        mock_user.is_active = True

        response = service._to_response(mock_user)

        assert isinstance(response, UserResponse)
        assert response.id == mock_user.id
        assert response.username == mock_user.username
        assert response.avatar_url == mock_user.avatar_url


class TestGenerateInviteToken:
    """Tests for invite token generation"""

    def test_generate_invite_token(self):
        """Should generate secure random token"""
        service = AuthService()

        token1 = service._generate_invite_token()
        token2 = service._generate_invite_token()

        assert token1 is not None
        assert len(token1) > 20
        assert token1 != token2  # Should be unique


class TestInviteToResponse:
    """Tests for _invite_to_response helper"""

    def test_invite_to_response(self):
        """Should convert Invite to InviteResponse"""
        from app.db_models import Invite, InviteStatus
        from app.models import InviteResponse

        service = AuthService()

        mock_invite = MagicMock(spec=Invite)
        mock_invite.id = "invite-123"
        mock_invite.email = "new@test.com"
        mock_invite.role = UserRole.MEMBER
        mock_invite.status = InviteStatus.PENDING
        mock_invite.invited_by_username = "admin"
        mock_invite.invited_by_name = "Admin User"
        mock_invite.created_at = datetime.now(timezone.utc)
        mock_invite.expires_at = datetime.now(timezone.utc) + timedelta(hours=72)
        mock_invite.accepted_at = None

        response = service._invite_to_response(mock_invite)

        assert isinstance(response, InviteResponse)
        assert response.id == mock_invite.id
        assert response.email == mock_invite.email


class TestDatabaseOperations:
    """Tests for database operations with mocked sessions"""

    @pytest.mark.asyncio
    async def test_is_setup_complete_true(self):
        """Should return True when owner exists"""
        service = AuthService()

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()  # User exists
        mock_db.execute.return_value = mock_result

        result = await service.is_setup_complete(mock_db)

        assert result is True

    @pytest.mark.asyncio
    async def test_is_setup_complete_false(self):
        """Should return False when no owner exists"""
        service = AuthService()

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.is_setup_complete(mock_db)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_setup_status(self):
        """Should return setup status dict"""
        service = AuthService()

        mock_db = AsyncMock()

        # First call for owner check
        mock_owner_result = MagicMock()
        mock_owner_result.scalar_one_or_none.return_value = MagicMock()

        # Second call for user count
        mock_count_result = MagicMock()
        mock_count_result.scalars.return_value.all.return_value = [MagicMock(), MagicMock()]

        mock_db.execute.side_effect = [mock_owner_result, mock_count_result]

        result = await service.get_setup_status(mock_db)

        assert result["is_setup_complete"] is True
        assert result["owner_exists"] is True
        assert result["total_users"] == 2

    @pytest.mark.asyncio
    async def test_get_user(self):
        """Should get user by ID"""
        service = AuthService()

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = "user-123"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        result = await service.get_user(mock_db, "user-123")

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_get_user_not_found(self):
        """Should return None when user not found"""
        service = AuthService()

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_user(mock_db, "nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_by_username(self):
        """Should get user by username"""
        service = AuthService()

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.username = "testuser"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        result = await service.get_user_by_username(mock_db, "TestUser")

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_get_user_by_email(self):
        """Should get user by email"""
        service = AuthService()

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.email = "test@test.com"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        result = await service.get_user_by_email(mock_db, "Test@Test.com")

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_list_users(self):
        """Should list users"""
        service = AuthService()

        mock_db = AsyncMock()
        mock_user1 = MagicMock()
        mock_user2 = MagicMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_user1, mock_user2]
        mock_db.execute.return_value = mock_result

        # Mock _to_response
        service._to_response = MagicMock(side_effect=lambda u: MagicMock())

        mock_requesting_user = MagicMock()
        mock_requesting_user.role = UserRole.OWNER

        result = await service.list_users(mock_db, mock_requesting_user)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_change_password_success(self):
        """Should change password successfully"""
        service = AuthService()

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.hashed_password = "$2b$10$test_hash"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        with (
            patch(
                "app.services.auth_service.verify_password_async", new_callable=AsyncMock
            ) as mock_verify,
            patch(
                "app.services.auth_service.hash_password_async", new_callable=AsyncMock
            ) as mock_hash,
        ):
            mock_verify.return_value = True
            mock_hash.return_value = "new_hash"

            result = await service.change_password(mock_db, "user-123", "oldpass", "newpass")

            assert result is True
            assert mock_user.hashed_password == "new_hash"

    @pytest.mark.asyncio
    async def test_change_password_user_not_found(self):
        """Should raise ValueError when user not found"""
        service = AuthService()

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError) as exc_info:
            await service.change_password(mock_db, "nonexistent", "oldpass", "newpass")

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_change_password_wrong_password(self):
        """Should raise ValueError when current password is wrong"""
        service = AuthService()

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.hashed_password = "$2b$10$test_hash"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        with patch(
            "app.services.auth_service.verify_password_async", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = False

            with pytest.raises(ValueError) as exc_info:
                await service.change_password(mock_db, "user-123", "wrongpass", "newpass")

            assert "incorrect" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_invites(self):
        """Should list invites"""
        from app.db_models import InviteStatus

        service = AuthService()

        mock_db = AsyncMock()
        mock_invite = MagicMock()
        mock_invite.id = "invite-123"
        mock_invite.email = "test@test.com"
        mock_invite.role = UserRole.MEMBER
        mock_invite.status = InviteStatus.PENDING
        mock_invite.invited_by_username = "owner"
        mock_invite.invited_by_name = "Test Owner"
        mock_invite.created_at = datetime.now(timezone.utc)
        mock_invite.expires_at = datetime.now(timezone.utc) + timedelta(hours=72)
        mock_invite.accepted_at = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_invite]
        mock_db.execute.return_value = mock_result

        mock_requesting_user = MagicMock()
        mock_requesting_user.role = UserRole.OWNER

        result = await service.list_invites(mock_db, mock_requesting_user)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_invites_permission_denied(self):
        """Should raise PermissionError for non-owners"""
        service = AuthService()

        mock_db = AsyncMock()
        mock_requesting_user = MagicMock()
        mock_requesting_user.role = UserRole.MEMBER

        with pytest.raises(PermissionError):
            await service.list_invites(mock_db, mock_requesting_user)

    @pytest.mark.asyncio
    async def test_authenticate_success(self):
        """Should authenticate user successfully"""
        service = AuthService()

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.username = "testuser"
        mock_user.hashed_password = "$2b$10$test_hash"
        mock_user.is_active = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        with patch(
            "app.services.auth_service.verify_password_async", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = True

            result = await service.authenticate(mock_db, "testuser", "password123")

            assert result == mock_user

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self):
        """Should return None when user not found"""
        service = AuthService()

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.authenticate(mock_db, "nonexistent", "password")

        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self):
        """Should return None when password is wrong"""
        service = AuthService()

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.username = "testuser"
        mock_user.hashed_password = "$2b$10$test_hash"
        mock_user.is_active = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        with patch(
            "app.services.auth_service.verify_password_async", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = False

            result = await service.authenticate(mock_db, "testuser", "wrongpassword")

            assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_inactive_user(self):
        """Should return None for inactive user"""
        service = AuthService()

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.username = "testuser"
        mock_user.hashed_password = "$2b$10$test_hash"
        mock_user.is_active = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        with patch(
            "app.services.auth_service.verify_password_async", new_callable=AsyncMock
        ) as mock_verify:
            mock_verify.return_value = True

            result = await service.authenticate(mock_db, "testuser", "password123")

            assert result is None


class TestSetupOwner:
    """Tests for setup_owner method"""

    @pytest.mark.asyncio
    async def test_setup_owner_success(self):
        """Should create owner account successfully"""
        from app.models import OwnerSetupRequest

        service = AuthService()
        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        request = OwnerSetupRequest(
            username="admin",
            first_name="Admin",
            last_name="User",
            email="admin@test.com",
            password="password123",
        )

        with (
            patch.object(service, "is_setup_complete", new_callable=AsyncMock) as mock_setup,
            patch.object(
                service, "get_user_by_username", new_callable=AsyncMock
            ) as mock_get_username,
            patch.object(service, "get_user_by_email", new_callable=AsyncMock) as mock_get_email,
            patch(
                "app.services.auth_service.hash_password_async", new_callable=AsyncMock
            ) as mock_hash,
        ):
            mock_setup.return_value = False
            mock_get_username.return_value = None
            mock_get_email.return_value = None
            mock_hash.return_value = "hashed_password"

            # Mock the refresh to set created_at/updated_at
            async def mock_refresh_side_effect(user):
                user.created_at = datetime.now(timezone.utc)
                user.updated_at = datetime.now(timezone.utc)

            mock_db.refresh.side_effect = mock_refresh_side_effect

            result = await service.setup_owner(mock_db, request)

            assert result is not None
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_owner_already_complete(self):
        """Should raise error if setup already complete"""
        from app.models import OwnerSetupRequest

        service = AuthService()
        mock_db = AsyncMock()

        request = OwnerSetupRequest(
            username="admin",
            first_name="Admin",
            last_name="User",
            email="admin@test.com",
            password="password123",
        )

        with patch.object(service, "is_setup_complete", new_callable=AsyncMock) as mock_setup:
            mock_setup.return_value = True

            with pytest.raises(ValueError) as exc_info:
                await service.setup_owner(mock_db, request)

            assert "already complete" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_setup_owner_username_taken(self):
        """Should raise error if username already taken"""
        from app.models import OwnerSetupRequest

        service = AuthService()
        mock_db = AsyncMock()

        request = OwnerSetupRequest(
            username="admin",
            first_name="Admin",
            last_name="User",
            email="admin@test.com",
            password="password123",
        )

        with (
            patch.object(service, "is_setup_complete", new_callable=AsyncMock) as mock_setup,
            patch.object(
                service, "get_user_by_username", new_callable=AsyncMock
            ) as mock_get_username,
        ):
            mock_setup.return_value = False
            mock_get_username.return_value = MagicMock()  # User exists

            with pytest.raises(ValueError) as exc_info:
                await service.setup_owner(mock_db, request)

            assert "Username already taken" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_setup_owner_email_taken(self):
        """Should raise error if email already in use"""
        from app.models import OwnerSetupRequest

        service = AuthService()
        mock_db = AsyncMock()

        request = OwnerSetupRequest(
            username="admin",
            first_name="Admin",
            last_name="User",
            email="admin@test.com",
            password="password123",
        )

        with (
            patch.object(service, "is_setup_complete", new_callable=AsyncMock) as mock_setup,
            patch.object(
                service, "get_user_by_username", new_callable=AsyncMock
            ) as mock_get_username,
            patch.object(service, "get_user_by_email", new_callable=AsyncMock) as mock_get_email,
        ):
            mock_setup.return_value = False
            mock_get_username.return_value = None
            mock_get_email.return_value = MagicMock()  # Email exists

            with pytest.raises(ValueError) as exc_info:
                await service.setup_owner(mock_db, request)

            assert "Email already in use" in str(exc_info.value)


class TestCreateUser:
    """Tests for create_user method"""

    @pytest.mark.asyncio
    async def test_create_user_success(self):
        """Should create user successfully"""
        from app.models import UserCreate

        service = AuthService()
        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        mock_owner = MagicMock()
        mock_owner.role = UserRole.OWNER

        request = UserCreate(
            username="newuser",
            first_name="New",
            last_name="User",
            email="new@test.com",
            password="password123",
            role=UserRole.MEMBER,
        )

        with (
            patch.object(
                service, "get_user_by_username", new_callable=AsyncMock
            ) as mock_get_username,
            patch.object(service, "get_user_by_email", new_callable=AsyncMock) as mock_get_email,
            patch(
                "app.services.auth_service.hash_password_async", new_callable=AsyncMock
            ) as mock_hash,
        ):
            mock_get_username.return_value = None
            mock_get_email.return_value = None
            mock_hash.return_value = "hashed_password"

            # Mock the refresh to set created_at/updated_at
            async def mock_refresh_side_effect(user):
                user.created_at = datetime.now(timezone.utc)
                user.updated_at = datetime.now(timezone.utc)

            mock_db.refresh.side_effect = mock_refresh_side_effect

            result = await service.create_user(mock_db, request, mock_owner)

            assert result is not None
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_not_owner(self):
        """Should raise error if not owner"""
        from app.models import UserCreate

        service = AuthService()
        mock_db = AsyncMock()

        mock_user = MagicMock()
        mock_user.role = UserRole.MEMBER

        request = UserCreate(
            username="newuser",
            first_name="New",
            last_name="User",
            email="new@test.com",
            password="password123",
        )

        with pytest.raises(PermissionError):
            await service.create_user(mock_db, request, mock_user)

    @pytest.mark.asyncio
    async def test_create_user_cannot_create_owner(self):
        """Should raise error if trying to create owner"""
        from app.models import UserCreate

        service = AuthService()
        mock_db = AsyncMock()

        mock_owner = MagicMock()
        mock_owner.role = UserRole.OWNER

        request = UserCreate(
            username="newowner",
            first_name="New",
            last_name="Owner",
            email="newowner@test.com",
            password="password123",
            role=UserRole.OWNER,
        )

        with pytest.raises(ValueError) as exc_info:
            await service.create_user(mock_db, request, mock_owner)

        assert "Cannot create additional owner" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_user_username_taken(self):
        """Should raise error if username already taken"""
        from app.models import UserCreate

        service = AuthService()
        mock_db = AsyncMock()

        mock_owner = MagicMock()
        mock_owner.role = UserRole.OWNER

        request = UserCreate(
            username="existinguser",
            first_name="New",
            last_name="User",
            email="new@test.com",
            password="password123",
        )

        with patch.object(
            service, "get_user_by_username", new_callable=AsyncMock
        ) as mock_get_username:
            mock_get_username.return_value = MagicMock()  # User exists

            with pytest.raises(ValueError) as exc_info:
                await service.create_user(mock_db, request, mock_owner)

            assert "Username already taken" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_user_email_taken(self):
        """Should raise error if email already in use"""
        from app.models import UserCreate

        service = AuthService()
        mock_db = AsyncMock()

        mock_owner = MagicMock()
        mock_owner.role = UserRole.OWNER

        request = UserCreate(
            username="newuser",
            first_name="New",
            last_name="User",
            email="existing@test.com",
            password="password123",
        )

        with (
            patch.object(
                service, "get_user_by_username", new_callable=AsyncMock
            ) as mock_get_username,
            patch.object(service, "get_user_by_email", new_callable=AsyncMock) as mock_get_email,
        ):
            mock_get_username.return_value = None
            mock_get_email.return_value = MagicMock()  # Email exists

            with pytest.raises(ValueError) as exc_info:
                await service.create_user(mock_db, request, mock_owner)

            assert "Email already in use" in str(exc_info.value)


class TestUpdateUser:
    """Tests for update_user method"""

    @pytest.mark.asyncio
    async def test_update_user_success(self):
        """Should update user successfully"""
        from app.models import UserUpdate

        service = AuthService()
        mock_db = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.role = UserRole.MEMBER
        mock_user.first_name = "Original"
        mock_user.last_name = "User"
        mock_user.email = "test@test.com"
        mock_user.username = "testuser"
        mock_user.avatar_url = None
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.updated_at = datetime.now(timezone.utc)
        mock_user.last_login_at = None
        mock_user.is_active = True

        mock_owner = MagicMock()
        mock_owner.id = "owner-123"
        mock_owner.role = UserRole.OWNER

        request = UserUpdate(first_name="Updated")

        with patch.object(service, "get_user", new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = mock_user

            result = await service.update_user(mock_db, "user-123", request, mock_owner)

            assert result is not None
            assert mock_user.first_name == "Updated"
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_not_found(self):
        """Should raise error if user not found"""
        from app.models import UserUpdate

        service = AuthService()
        mock_db = AsyncMock()

        mock_owner = MagicMock()
        mock_owner.role = UserRole.OWNER

        request = UserUpdate(first_name="Updated")

        with patch.object(service, "get_user", new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = None

            with pytest.raises(ValueError) as exc_info:
                await service.update_user(mock_db, "nonexistent", request, mock_owner)

            assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_user_not_self_not_owner(self):
        """Should raise error if not self and not owner"""
        from app.models import UserUpdate

        service = AuthService()
        mock_db = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.role = UserRole.MEMBER

        mock_other_user = MagicMock()
        mock_other_user.id = "other-456"
        mock_other_user.role = UserRole.MEMBER

        request = UserUpdate(first_name="Updated")

        with patch.object(service, "get_user", new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = mock_user

            with pytest.raises(PermissionError):
                await service.update_user(mock_db, "user-123", request, mock_other_user)

    @pytest.mark.asyncio
    async def test_update_user_role_not_owner(self):
        """Should raise error if changing role and not owner"""
        from app.models import UserUpdate

        service = AuthService()
        mock_db = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.role = UserRole.MEMBER

        request = UserUpdate(role=UserRole.ADMIN)

        with patch.object(service, "get_user", new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = mock_user

            with pytest.raises(PermissionError) as exc_info:
                await service.update_user(mock_db, "user-123", request, mock_user)

            assert "role" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_update_user_cannot_change_owner_role(self):
        """Should raise error if trying to change owner's role"""
        from app.models import UserUpdate

        service = AuthService()
        mock_db = AsyncMock()

        mock_owner = MagicMock()
        mock_owner.id = "owner-123"
        mock_owner.role = UserRole.OWNER

        request = UserUpdate(role=UserRole.ADMIN)

        with patch.object(service, "get_user", new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = mock_owner

            with pytest.raises(ValueError) as exc_info:
                await service.update_user(mock_db, "owner-123", request, mock_owner)

            assert "owner's role" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_update_user_email_duplicate(self):
        """Should raise error if email already in use"""
        from app.models import UserUpdate

        service = AuthService()
        mock_db = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.role = UserRole.MEMBER
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.email = "test@test.com"
        mock_user.username = "testuser"

        mock_owner = MagicMock()
        mock_owner.id = "owner-123"
        mock_owner.role = UserRole.OWNER

        mock_existing = MagicMock()
        mock_existing.id = "other-456"

        request = UserUpdate(email="existing@test.com")

        with (
            patch.object(service, "get_user", new_callable=AsyncMock) as mock_get_user,
            patch.object(service, "get_user_by_email", new_callable=AsyncMock) as mock_get_email,
        ):
            mock_get_user.return_value = mock_user
            mock_get_email.return_value = mock_existing

            with pytest.raises(ValueError) as exc_info:
                await service.update_user(mock_db, "user-123", request, mock_owner)

            assert "Email already in use" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_user_with_password(self):
        """Should update user password"""
        from app.models import UserUpdate

        service = AuthService()
        mock_db = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.role = UserRole.MEMBER
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.email = "test@test.com"
        mock_user.username = "testuser"
        mock_user.avatar_url = None
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.updated_at = datetime.now(timezone.utc)
        mock_user.last_login_at = None
        mock_user.is_active = True
        mock_user.hashed_password = "old_hash"

        mock_owner = MagicMock()
        mock_owner.id = "owner-123"
        mock_owner.role = UserRole.OWNER

        request = UserUpdate(password="newpassword123")

        with (
            patch.object(service, "get_user", new_callable=AsyncMock) as mock_get_user,
            patch(
                "app.services.auth_service.hash_password_async", new_callable=AsyncMock
            ) as mock_hash,
        ):
            mock_get_user.return_value = mock_user
            mock_hash.return_value = "new_hash"

            result = await service.update_user(mock_db, "user-123", request, mock_owner)

            assert result is not None
            assert mock_user.hashed_password == "new_hash"


class TestDeleteUser:
    """Tests for delete_user method"""

    @pytest.mark.asyncio
    async def test_delete_user_success(self):
        """Should delete user successfully"""
        service = AuthService()
        mock_db = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.role = UserRole.MEMBER
        mock_user.username = "testuser"
        mock_user.is_active = True

        mock_owner = MagicMock()
        mock_owner.id = "owner-123"
        mock_owner.role = UserRole.OWNER

        with patch.object(service, "get_user", new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = mock_user

            result = await service.delete_user(mock_db, "user-123", mock_owner)

            assert result is True
            assert mock_user.is_active is False
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_not_owner(self):
        """Should raise error if not owner"""
        service = AuthService()
        mock_db = AsyncMock()

        mock_user = MagicMock()
        mock_user.role = UserRole.MEMBER

        with pytest.raises(PermissionError):
            await service.delete_user(mock_db, "user-123", mock_user)

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self):
        """Should raise error if user not found"""
        service = AuthService()
        mock_db = AsyncMock()

        mock_owner = MagicMock()
        mock_owner.role = UserRole.OWNER

        with patch.object(service, "get_user", new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = None

            with pytest.raises(ValueError) as exc_info:
                await service.delete_user(mock_db, "nonexistent", mock_owner)

            assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_user_cannot_delete_owner(self):
        """Should raise error if trying to delete owner"""
        service = AuthService()
        mock_db = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = "owner-456"
        mock_user.role = UserRole.OWNER

        mock_owner = MagicMock()
        mock_owner.id = "owner-123"
        mock_owner.role = UserRole.OWNER

        with patch.object(service, "get_user", new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = mock_user

            with pytest.raises(ValueError) as exc_info:
                await service.delete_user(mock_db, "owner-456", mock_owner)

            assert "Cannot delete owner" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_user_cannot_delete_self(self):
        """Should raise error if trying to delete self"""
        service = AuthService()
        mock_db = AsyncMock()

        mock_owner = MagicMock()
        mock_owner.id = "owner-123"
        mock_owner.role = UserRole.OWNER

        mock_user = MagicMock()
        mock_user.id = "owner-123"
        mock_user.role = UserRole.MEMBER  # Not owner, so we can test the "self" check

        with patch.object(service, "get_user", new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = mock_user

            with pytest.raises(ValueError) as exc_info:
                await service.delete_user(mock_db, "owner-123", mock_owner)

            assert "Cannot delete your own account" in str(exc_info.value)


class TestGetOwnerUser:
    """Tests for get_owner_user method"""

    @pytest.mark.asyncio
    async def test_get_owner_user_found(self):
        """Should return owner user"""
        service = AuthService()
        mock_db = AsyncMock()

        mock_owner = MagicMock()
        mock_owner.role = UserRole.OWNER

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_owner
        mock_db.execute.return_value = mock_result

        result = await service.get_owner_user(mock_db)

        assert result == mock_owner

    @pytest.mark.asyncio
    async def test_get_owner_user_not_found(self):
        """Should return None if no owner"""
        service = AuthService()
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_owner_user(mock_db)

        assert result is None


class TestGetAllUserIds:
    """Tests for get_all_user_ids method"""

    @pytest.mark.asyncio
    async def test_get_all_user_ids(self):
        """Should return all user IDs"""
        service = AuthService()
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.all.return_value = [("user-1",), ("user-2",), ("user-3",)]
        mock_db.execute.return_value = mock_result

        result = await service.get_all_user_ids(mock_db)

        assert result == ["user-1", "user-2", "user-3"]


class TestListUsersNonOwner:
    """Tests for list_users with non-owner user"""

    @pytest.mark.asyncio
    async def test_list_users_non_owner(self):
        """Non-owner should only see themselves"""
        service = AuthService()
        mock_db = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.role = UserRole.MEMBER
        mock_user.username = "testuser"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.email = "test@test.com"
        mock_user.avatar_url = None
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.updated_at = datetime.now(timezone.utc)
        mock_user.last_login_at = None
        mock_user.is_active = True

        result = await service.list_users(mock_db, mock_user)

        assert len(result) == 1
        assert result[0].id == "user-123"


class TestCreateInvite:
    """Tests for create_invite method"""

    @pytest.mark.asyncio
    async def test_create_invite_success(self):
        """Should create invite successfully"""
        from app.models import InviteCreate

        service = AuthService()
        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.execute = AsyncMock()

        mock_owner = MagicMock()
        mock_owner.id = "owner-123"
        mock_owner.role = UserRole.OWNER
        mock_owner.username = "owner"
        mock_owner.first_name = "Test"
        mock_owner.last_name = "Owner"

        request = InviteCreate(email="new@test.com", role=UserRole.MEMBER)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No existing user/invite
        mock_db.execute.return_value = mock_result

        # Mock the refresh to set created_at
        async def mock_refresh_side_effect(invite):
            invite.created_at = datetime.now(timezone.utc)

        mock_db.refresh.side_effect = mock_refresh_side_effect

        with (
            patch.object(service, "get_user_by_email", new_callable=AsyncMock) as mock_get_email,
            patch("app.services.email_service.is_email_configured", return_value=False),
        ):
            mock_get_email.return_value = None

            result, email_sent = await service.create_invite(mock_db, request, mock_owner)

            assert result is not None
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_invite_not_owner(self):
        """Should raise error if not owner"""
        from app.models import InviteCreate

        service = AuthService()
        mock_db = AsyncMock()

        mock_user = MagicMock()
        mock_user.role = UserRole.MEMBER

        request = InviteCreate(email="new@test.com")

        with pytest.raises(PermissionError):
            await service.create_invite(mock_db, request, mock_user)

    @pytest.mark.asyncio
    async def test_create_invite_user_exists(self):
        """Should raise error if user already exists"""
        from app.models import InviteCreate

        service = AuthService()
        mock_db = AsyncMock()

        mock_owner = MagicMock()
        mock_owner.role = UserRole.OWNER

        mock_existing = MagicMock()
        mock_existing.is_active = True

        request = InviteCreate(email="existing@test.com")

        with patch.object(service, "get_user_by_email", new_callable=AsyncMock) as mock_get_email:
            mock_get_email.return_value = mock_existing

            with pytest.raises(ValueError) as exc_info:
                await service.create_invite(mock_db, request, mock_owner)

            assert "already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_invite_duplicate_pending(self):
        """Should raise error if pending invite exists"""
        from app.models import InviteCreate

        service = AuthService()
        mock_db = AsyncMock()

        mock_owner = MagicMock()
        mock_owner.role = UserRole.OWNER

        mock_pending_invite = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_pending_invite
        mock_db.execute.return_value = mock_result

        request = InviteCreate(email="new@test.com")

        with patch.object(service, "get_user_by_email", new_callable=AsyncMock) as mock_get_email:
            mock_get_email.return_value = None

            with pytest.raises(ValueError) as exc_info:
                await service.create_invite(mock_db, request, mock_owner)

            assert "already exists" in str(exc_info.value)


class TestGetInviteByToken:
    """Tests for get_invite_by_token method"""

    @pytest.mark.asyncio
    async def test_get_invite_by_token_found(self):
        """Should return invite by token"""
        service = AuthService()
        mock_db = AsyncMock()

        mock_invite = MagicMock()
        mock_invite.token = "test-token"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_invite
        mock_db.execute.return_value = mock_result

        result = await service.get_invite_by_token(mock_db, "test-token")

        assert result == mock_invite

    @pytest.mark.asyncio
    async def test_get_invite_by_token_not_found(self):
        """Should return None if not found"""
        service = AuthService()
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_invite_by_token(mock_db, "invalid-token")

        assert result is None


class TestGetInviteTokenInfo:
    """Tests for get_invite_token_info method"""

    @pytest.mark.asyncio
    async def test_get_invite_token_info_valid(self):
        """Should return valid token info"""
        from app.db_models import InviteStatus

        service = AuthService()
        mock_db = AsyncMock()

        mock_invite = MagicMock()
        mock_invite.email = "test@test.com"
        mock_invite.role = UserRole.MEMBER
        mock_invite.invited_by_name = "Test Owner"
        mock_invite.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        mock_invite.status = InviteStatus.PENDING

        with patch.object(
            service, "get_invite_by_token", new_callable=AsyncMock
        ) as mock_get_invite:
            mock_get_invite.return_value = mock_invite

            result = await service.get_invite_token_info(mock_db, "test-token")

            assert result is not None
            assert result.is_valid is True
            assert result.email == "test@test.com"

    @pytest.mark.asyncio
    async def test_get_invite_token_info_not_found(self):
        """Should return None if not found"""
        service = AuthService()
        mock_db = AsyncMock()

        with patch.object(
            service, "get_invite_by_token", new_callable=AsyncMock
        ) as mock_get_invite:
            mock_get_invite.return_value = None

            result = await service.get_invite_token_info(mock_db, "invalid-token")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_invite_token_info_expired(self):
        """Should return invalid for expired invite"""
        from app.db_models import InviteStatus

        service = AuthService()
        mock_db = AsyncMock()

        mock_invite = MagicMock()
        mock_invite.email = "test@test.com"
        mock_invite.role = UserRole.MEMBER
        mock_invite.invited_by_name = "Test Owner"
        mock_invite.expires_at = datetime.now(timezone.utc) - timedelta(hours=24)  # Expired
        mock_invite.status = InviteStatus.PENDING

        with patch.object(
            service, "get_invite_by_token", new_callable=AsyncMock
        ) as mock_get_invite:
            mock_get_invite.return_value = mock_invite

            result = await service.get_invite_token_info(mock_db, "test-token")

            assert result is not None
            assert result.is_valid is False


class TestAcceptInvite:
    """Tests for accept_invite method"""

    @pytest.mark.asyncio
    async def test_accept_invite_success(self):
        """Should accept invite and create user"""
        from app.db_models import InviteStatus

        service = AuthService()
        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        mock_invite = MagicMock()
        mock_invite.email = "test@test.com"
        mock_invite.role = UserRole.MEMBER
        mock_invite.status = InviteStatus.PENDING
        mock_invite.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

        with (
            patch.object(service, "get_invite_by_token", new_callable=AsyncMock) as mock_get_invite,
            patch.object(
                service, "get_user_by_username", new_callable=AsyncMock
            ) as mock_get_username,
            patch.object(service, "get_user_by_email", new_callable=AsyncMock) as mock_get_email,
            patch(
                "app.services.auth_service.hash_password_async", new_callable=AsyncMock
            ) as mock_hash,
        ):
            mock_get_invite.return_value = mock_invite
            mock_get_username.return_value = None
            mock_get_email.return_value = None
            mock_hash.return_value = "hashed_password"

            # Mock the refresh to set created_at/updated_at
            async def mock_refresh_side_effect(user):
                user.created_at = datetime.now(timezone.utc)
                user.updated_at = datetime.now(timezone.utc)

            mock_db.refresh.side_effect = mock_refresh_side_effect

            result = await service.accept_invite(
                mock_db, "test-token", "newuser", "New", "User", "password123"
            )

            assert result is not None
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            assert mock_invite.status == InviteStatus.ACCEPTED

    @pytest.mark.asyncio
    async def test_accept_invite_invalid_token(self):
        """Should raise error for invalid token"""
        service = AuthService()
        mock_db = AsyncMock()

        with patch.object(
            service, "get_invite_by_token", new_callable=AsyncMock
        ) as mock_get_invite:
            mock_get_invite.return_value = None

            with pytest.raises(ValueError) as exc_info:
                await service.accept_invite(
                    mock_db, "invalid-token", "newuser", "New", "User", "password123"
                )

            assert "Invalid invitation token" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_accept_invite_not_pending(self):
        """Should raise error if invite not pending"""
        from app.db_models import InviteStatus

        service = AuthService()
        mock_db = AsyncMock()

        mock_invite = MagicMock()
        mock_invite.status = InviteStatus.ACCEPTED

        with patch.object(
            service, "get_invite_by_token", new_callable=AsyncMock
        ) as mock_get_invite:
            mock_get_invite.return_value = mock_invite

            with pytest.raises(ValueError) as exc_info:
                await service.accept_invite(
                    mock_db, "test-token", "newuser", "New", "User", "password123"
                )

            assert "no longer valid" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_accept_invite_expired(self):
        """Should raise error for expired invite"""
        from app.db_models import InviteStatus

        service = AuthService()
        mock_db = AsyncMock()

        mock_invite = MagicMock()
        mock_invite.status = InviteStatus.PENDING
        mock_invite.expires_at = datetime.now(timezone.utc) - timedelta(hours=24)  # Expired

        with patch.object(
            service, "get_invite_by_token", new_callable=AsyncMock
        ) as mock_get_invite:
            mock_get_invite.return_value = mock_invite

            with pytest.raises(ValueError) as exc_info:
                await service.accept_invite(
                    mock_db, "test-token", "newuser", "New", "User", "password123"
                )

            assert "expired" in str(exc_info.value)
            assert mock_invite.status == InviteStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_accept_invite_username_taken(self):
        """Should raise error if username taken"""
        from app.db_models import InviteStatus

        service = AuthService()
        mock_db = AsyncMock()

        mock_invite = MagicMock()
        mock_invite.status = InviteStatus.PENDING
        mock_invite.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

        with (
            patch.object(service, "get_invite_by_token", new_callable=AsyncMock) as mock_get_invite,
            patch.object(
                service, "get_user_by_username", new_callable=AsyncMock
            ) as mock_get_username,
        ):
            mock_get_invite.return_value = mock_invite
            mock_get_username.return_value = MagicMock()  # User exists

            with pytest.raises(ValueError) as exc_info:
                await service.accept_invite(
                    mock_db, "test-token", "existinguser", "New", "User", "password123"
                )

            assert "Username already taken" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_accept_invite_email_already_exists(self):
        """Should raise error if email already has active user"""
        from app.db_models import InviteStatus

        service = AuthService()
        mock_db = AsyncMock()

        mock_invite = MagicMock()
        mock_invite.status = InviteStatus.PENDING
        mock_invite.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        mock_invite.email = "test@test.com"

        mock_existing = MagicMock()
        mock_existing.is_active = True

        with (
            patch.object(service, "get_invite_by_token", new_callable=AsyncMock) as mock_get_invite,
            patch.object(
                service, "get_user_by_username", new_callable=AsyncMock
            ) as mock_get_username,
            patch.object(service, "get_user_by_email", new_callable=AsyncMock) as mock_get_email,
        ):
            mock_get_invite.return_value = mock_invite
            mock_get_username.return_value = None
            mock_get_email.return_value = mock_existing

            with pytest.raises(ValueError) as exc_info:
                await service.accept_invite(
                    mock_db, "test-token", "newuser", "New", "User", "password123"
                )

            assert "already exists" in str(exc_info.value)


class TestRevokeInvite:
    """Tests for revoke_invite method"""

    @pytest.mark.asyncio
    async def test_revoke_invite_success(self):
        """Should revoke invite successfully"""
        from app.db_models import InviteStatus

        service = AuthService()
        mock_db = AsyncMock()

        mock_owner = MagicMock()
        mock_owner.role = UserRole.OWNER
        mock_owner.username = "owner"

        mock_invite = MagicMock()
        mock_invite.status = InviteStatus.PENDING
        mock_invite.email = "test@test.com"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_invite
        mock_db.execute.return_value = mock_result

        result = await service.revoke_invite(mock_db, "invite-123", mock_owner)

        assert result is True
        assert mock_invite.status == InviteStatus.REVOKED
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_invite_not_owner(self):
        """Should raise error if not owner"""
        service = AuthService()
        mock_db = AsyncMock()

        mock_user = MagicMock()
        mock_user.role = UserRole.MEMBER

        with pytest.raises(PermissionError):
            await service.revoke_invite(mock_db, "invite-123", mock_user)

    @pytest.mark.asyncio
    async def test_revoke_invite_not_found(self):
        """Should raise error if invite not found"""
        service = AuthService()
        mock_db = AsyncMock()

        mock_owner = MagicMock()
        mock_owner.role = UserRole.OWNER

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError) as exc_info:
            await service.revoke_invite(mock_db, "nonexistent", mock_owner)

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_revoke_invite_not_pending(self):
        """Should raise error if invite not pending"""
        from app.db_models import InviteStatus

        service = AuthService()
        mock_db = AsyncMock()

        mock_owner = MagicMock()
        mock_owner.role = UserRole.OWNER

        mock_invite = MagicMock()
        mock_invite.status = InviteStatus.ACCEPTED

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_invite
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError) as exc_info:
            await service.revoke_invite(mock_db, "invite-123", mock_owner)

        assert "status" in str(exc_info.value)


class TestResendInvite:
    """Tests for resend_invite method"""

    @pytest.mark.asyncio
    async def test_resend_invite_not_owner(self):
        """Should raise error if not owner"""
        service = AuthService()
        mock_db = AsyncMock()

        mock_user = MagicMock()
        mock_user.role = UserRole.MEMBER

        with pytest.raises(PermissionError):
            await service.resend_invite(mock_db, "invite-123", mock_user)

    @pytest.mark.asyncio
    async def test_resend_invite_not_found(self):
        """Should raise error if invite not found"""
        service = AuthService()
        mock_db = AsyncMock()

        mock_owner = MagicMock()
        mock_owner.role = UserRole.OWNER

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError) as exc_info:
            await service.resend_invite(mock_db, "nonexistent", mock_owner)

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_resend_invite_not_pending(self):
        """Should raise error if invite not pending"""
        from app.db_models import InviteStatus

        service = AuthService()
        mock_db = AsyncMock()

        mock_owner = MagicMock()
        mock_owner.role = UserRole.OWNER

        mock_invite = MagicMock()
        mock_invite.status = InviteStatus.ACCEPTED

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_invite
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError) as exc_info:
            await service.resend_invite(mock_db, "invite-123", mock_owner)

        assert "status" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_resend_invite_email_not_configured(self):
        """Should raise error if email not configured"""
        from app.db_models import InviteStatus

        service = AuthService()
        mock_db = AsyncMock()

        mock_owner = MagicMock()
        mock_owner.role = UserRole.OWNER

        mock_invite = MagicMock()
        mock_invite.status = InviteStatus.PENDING
        mock_invite.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_invite
        mock_db.execute.return_value = mock_result

        with patch("app.services.email_service.is_email_configured", return_value=False):
            with pytest.raises(ValueError) as exc_info:
                await service.resend_invite(mock_db, "invite-123", mock_owner)

            assert "not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_resend_invite_success(self):
        """Should resend invite successfully"""
        from app.db_models import InviteStatus

        service = AuthService()
        mock_db = AsyncMock()

        mock_owner = MagicMock()
        mock_owner.role = UserRole.OWNER

        mock_invite = MagicMock()
        mock_invite.status = InviteStatus.PENDING
        mock_invite.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        mock_invite.email = "test@test.com"
        mock_invite.token = "test-token"
        mock_invite.invited_by_name = "Test Owner"
        mock_invite.role = UserRole.MEMBER

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_invite
        mock_db.execute.return_value = mock_result

        with (
            patch("app.services.email_service.is_email_configured", return_value=True),
            patch("app.services.email_service.send_invitation_email", return_value="email-123"),
        ):
            result = await service.resend_invite(mock_db, "invite-123", mock_owner)

            assert result is True

    @pytest.mark.asyncio
    async def test_resend_invite_extends_expiry(self):
        """Should extend expiry if expired"""
        from app.db_models import InviteStatus

        service = AuthService()
        mock_db = AsyncMock()

        mock_owner = MagicMock()
        mock_owner.role = UserRole.OWNER

        old_expiry = datetime.now(timezone.utc) - timedelta(hours=24)
        mock_invite = MagicMock()
        mock_invite.status = InviteStatus.PENDING
        mock_invite.expires_at = old_expiry
        mock_invite.email = "test@test.com"
        mock_invite.token = "test-token"
        mock_invite.invited_by_name = "Test Owner"
        mock_invite.role = UserRole.MEMBER

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_invite
        mock_db.execute.return_value = mock_result

        with (
            patch("app.services.email_service.is_email_configured", return_value=True),
            patch("app.services.email_service.send_invitation_email", return_value="email-123"),
        ):
            result = await service.resend_invite(mock_db, "invite-123", mock_owner)

            assert result is True
            # Check that expiry was extended (should be more recent than old expiry)
            assert mock_invite.expires_at > old_expiry

    @pytest.mark.asyncio
    async def test_resend_invite_email_failure(self):
        """Should raise error if email sending fails"""
        from app.db_models import InviteStatus

        service = AuthService()
        mock_db = AsyncMock()

        mock_owner = MagicMock()
        mock_owner.role = UserRole.OWNER

        mock_invite = MagicMock()
        mock_invite.status = InviteStatus.PENDING
        mock_invite.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        mock_invite.email = "test@test.com"
        mock_invite.token = "test-token"
        mock_invite.invited_by_name = "Test Owner"
        mock_invite.role = UserRole.MEMBER

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_invite
        mock_db.execute.return_value = mock_result

        with (
            patch("app.services.email_service.is_email_configured", return_value=True),
            patch("app.services.email_service.send_invitation_email", return_value=None),
        ):
            with pytest.raises(ValueError) as exc_info:
                await service.resend_invite(mock_db, "invite-123", mock_owner)

            assert "Failed to send email" in str(exc_info.value)


class TestRegisterUser:
    """Tests for register_user method"""

    @pytest.mark.asyncio
    async def test_register_user_success(self):
        """Should register user successfully when open registration is enabled"""
        from app.models import UserCreate

        service = AuthService()
        mock_db = AsyncMock()

        # Mock no existing user with same username or email
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        request = UserCreate(
            username="newuser",
            first_name="New",
            last_name="User",
            email="new@test.com",
            password="password123",
        )

        with patch.object(settings, "allow_open_registration", True):
            user, token, expires_in = await service.register_user(mock_db, request)

            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()
            assert token is not None
            assert expires_in > 0

    @pytest.mark.asyncio
    async def test_register_user_disabled(self):
        """Should raise error when open registration is disabled"""
        from app.models import UserCreate

        service = AuthService()
        mock_db = AsyncMock()

        request = UserCreate(
            username="newuser",
            first_name="New",
            last_name="User",
            email="new@test.com",
            password="password123",
        )

        with patch.object(settings, "allow_open_registration", False):
            with pytest.raises(ValueError) as exc_info:
                await service.register_user(mock_db, request)

            assert "disabled" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_register_user_username_taken(self):
        """Should raise error when username is taken"""
        from app.models import UserCreate

        service = AuthService()
        mock_db = AsyncMock()

        # Mock existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()
        mock_db.execute.return_value = mock_result

        request = UserCreate(
            username="existing",
            first_name="New",
            last_name="User",
            email="new@test.com",
            password="password123",
        )

        with patch.object(settings, "allow_open_registration", True):
            with pytest.raises(ValueError) as exc_info:
                await service.register_user(mock_db, request)

            assert "Username already taken" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_register_user_email_taken(self):
        """Should raise error when email is taken"""
        from app.models import UserCreate

        service = AuthService()
        mock_db = AsyncMock()

        # First call (username check) returns None, second call (email check) returns user
        call_count = [0]

        def mock_execute(query):
            result = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                # Username check - no user found
                result.scalar_one_or_none.return_value = None
            else:
                # Email check - user found
                result.scalar_one_or_none.return_value = MagicMock()
            return result

        mock_db.execute.side_effect = mock_execute

        request = UserCreate(
            username="newuser",
            first_name="New",
            last_name="User",
            email="existing@test.com",
            password="password123",
        )

        with patch.object(settings, "allow_open_registration", True):
            with pytest.raises(ValueError) as exc_info:
                await service.register_user(mock_db, request)

            assert "Email already in use" in str(exc_info.value)


class TestPreferences:
    """Tests for user preferences methods"""

    @pytest.mark.asyncio
    async def test_get_preferences_with_data(self):
        """Should return user preferences"""
        service = AuthService()

        mock_user = MagicMock()
        mock_user.preferences = {"dark_mode": True, "theme": "dark"}

        result = await service.get_preferences(mock_user)

        assert result.dark_mode is True

    @pytest.mark.asyncio
    async def test_get_preferences_empty(self):
        """Should return empty preferences when none set"""
        service = AuthService()

        mock_user = MagicMock()
        mock_user.preferences = None

        result = await service.get_preferences(mock_user)

        # Should return default preferences
        assert result is not None

    @pytest.mark.asyncio
    async def test_update_preferences_set_value(self):
        """Should update preferences with new values"""
        from app.models import UserPreferencesUpdate

        service = AuthService()
        mock_db = AsyncMock()

        mock_user = MagicMock()
        mock_user.username = "testuser"
        mock_user.preferences = {"dark_mode": False}

        request = UserPreferencesUpdate(dark_mode=True)

        await service.update_preferences(mock_db, mock_user, request)

        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        assert mock_user.preferences["dark_mode"] is True

    @pytest.mark.asyncio
    async def test_update_preferences_remove_value(self):
        """Should remove preference when set to None explicitly"""

        service = AuthService()
        mock_db = AsyncMock()

        mock_user = MagicMock()
        mock_user.username = "testuser"
        # Create a real dict for preferences so we can test deletion
        mock_user.preferences = {"dark_mode": True, "other_pref": "value"}

        # Test updating with explicit None (exclude_unset will include this)
        request = MagicMock()
        request.model_dump.return_value = {"dark_mode": None}

        await service.update_preferences(mock_db, mock_user, request)

        mock_db.commit.assert_called_once()
        # dark_mode should be removed since it was explicitly set to None
        # other_pref should still exist
        assert mock_user.preferences.get("dark_mode") is None or "dark_mode" not in (
            mock_user.preferences or {}
        )

    @pytest.mark.asyncio
    async def test_update_preferences_from_empty(self):
        """Should create preferences when starting from empty"""
        from app.models import UserPreferencesUpdate

        service = AuthService()
        mock_db = AsyncMock()

        mock_user = MagicMock()
        mock_user.username = "testuser"
        mock_user.preferences = None

        request = UserPreferencesUpdate(dark_mode=True)

        await service.update_preferences(mock_db, mock_user, request)

        mock_db.commit.assert_called_once()
        assert mock_user.preferences is not None

    @pytest.mark.asyncio
    async def test_get_assistant_settings_masks_keys(self):
        """Should return masked provider keys for public assistant settings."""
        service = AuthService()
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = "user-123"

        row = MagicMock()
        row.provider = "openai"
        row.encrypted_api_key = service._encrypt_assistant_api_key("sk-openai-abcdef123456")
        row.model = "gpt-4o-mini"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [row]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.get_assistant_settings(mock_db, mock_user)

        assert result.openai.has_api_key is True
        assert result.openai.api_key_masked is not None
        assert result.openai.model == "gpt-4o-mini"
        assert result.anthropic.has_api_key is False

    @pytest.mark.asyncio
    async def test_get_assistant_settings_internal_includes_raw_keys(self):
        """Should include raw keys in internal assistant settings payload."""
        service = AuthService()
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = "user-123"

        row = MagicMock()
        row.provider = "anthropic"
        row.encrypted_api_key = service._encrypt_assistant_api_key("sk-ant-123")
        row.model = "claude-sonnet"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [row]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service.get_assistant_settings_internal(mock_db, mock_user)

        assert result.anthropic.api_key == "sk-ant-123"
        assert result.anthropic.model == "claude-sonnet"
        assert result.openai.api_key is None

    @pytest.mark.asyncio
    async def test_update_assistant_settings_sets_and_clears_keys(self):
        """Should update and clear provider API keys in encrypted provider table."""
        from app.models import UserAssistantSettingsUpdate

        service = AuthService()
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.username = "testuser"

        existing_row = MagicMock()
        existing_row.provider = "openai"
        existing_row.encrypted_api_key = service._encrypt_assistant_api_key("old-key")
        existing_row.model = "gpt-old"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing_row]
        mock_db.execute = AsyncMock(side_effect=[mock_result, mock_result])

        request = UserAssistantSettingsUpdate(
            openai={"api_key": "new-openai-key", "model": "gpt-4o-mini"},
            anthropic={"api_key": ""},
        )

        result = await service.update_assistant_settings(mock_db, mock_user, request)

        mock_db.commit.assert_called_once()
        assert result.openai.has_api_key is True
        assert result.openai.model == "gpt-4o-mini"
        assert (
            service._decrypt_assistant_api_key(existing_row.encrypted_api_key) == "new-openai-key"
        )
        assert existing_row.model == "gpt-4o-mini"
        mock_db.delete.assert_not_called()

    def test_get_assistant_cipher_requires_env_key(self):
        """Should reject BYOK encryption/decryption when env key is unset."""
        service = AuthService()

        with patch.object(settings, "assistant_keys_encryption_key", ""):
            with pytest.raises(ValueError, match="ASSISTANT_KEYS_ENCRYPTION_KEY"):
                service._get_assistant_cipher()

    def test_decrypt_assistant_api_key_invalid_token_raises(self):
        """Should raise a helpful error when ciphertext cannot be decrypted."""
        service = AuthService()

        with pytest.raises(ValueError, match="Failed to decrypt stored assistant provider key"):
            service._decrypt_assistant_api_key("not-a-valid-fernet-token")

    @pytest.mark.asyncio
    async def test_migrate_legacy_assistant_preferences_skips_when_key_missing(self):
        """Should not migrate legacy plaintext settings without encryption key."""
        service = AuthService()
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.preferences = {
            "assistant_provider_settings": {
                "openai": {"api_key": "sk-openai-legacy", "model": "gpt-4o-mini"}
            }
        }

        with patch.object(settings, "assistant_keys_encryption_key", ""):
            await service._migrate_legacy_assistant_preferences_if_needed(mock_db, mock_user)

        mock_db.commit.assert_not_called()
        assert "assistant_provider_settings" in mock_user.preferences

    @pytest.mark.asyncio
    async def test_migrate_legacy_assistant_preferences_moves_plaintext_to_encrypted_rows(self):
        """Should migrate legacy plaintext preferences into encrypted provider rows."""
        service = AuthService()
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.preferences = {
            "dark_mode": True,
            "assistant_provider_settings": {
                "openai": {"api_key": "sk-openai-migrate", "model": "gpt-4o-mini"},
                "anthropic": {"api_key": "", "model": "claude-3-5-sonnet"},
            },
        }

        empty_result = MagicMock()
        empty_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=empty_result)

        await service._migrate_legacy_assistant_preferences_if_needed(mock_db, mock_user)

        mock_db.add.assert_called_once()
        added_row = mock_db.add.call_args.args[0]
        assert added_row.provider == "openai"
        assert added_row.model == "gpt-4o-mini"
        assert (
            service._decrypt_assistant_api_key(added_row.encrypted_api_key) == "sk-openai-migrate"
        )
        assert mock_user.preferences == {"dark_mode": True}
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_assistant_settings_deletes_existing_row_when_key_cleared(self):
        """Should delete provider row when api_key is cleared."""
        from app.models import UserAssistantSettingsUpdate

        service = AuthService()
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.username = "testuser"
        mock_user.preferences = None

        existing_row = MagicMock()
        existing_row.provider = "openai"
        existing_row.encrypted_api_key = service._encrypt_assistant_api_key("old-openai-key")
        existing_row.model = "gpt-old"

        row_result = MagicMock()
        row_result.scalars.return_value.all.return_value = [existing_row]
        mock_db.execute = AsyncMock(side_effect=[row_result, row_result])

        request = UserAssistantSettingsUpdate(openai={"api_key": "   "})
        result = await service.update_assistant_settings(mock_db, mock_user, request)

        mock_db.delete.assert_called_once_with(existing_row)
        mock_db.commit.assert_called_once()
        assert result.openai.has_api_key is False
        assert result.openai.model is None

    @pytest.mark.asyncio
    async def test_update_assistant_settings_creates_row_for_new_provider_key(self):
        """Should create a new provider row when adding a key for a provider."""
        from app.models import UserAssistantSettingsUpdate

        service = AuthService()
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.username = "testuser"
        mock_user.preferences = None

        empty_result = MagicMock()
        empty_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[empty_result, empty_result])

        request = UserAssistantSettingsUpdate(
            gemini={"api_key": "gemini-user-key", "model": "gemini-2.0-pro"}
        )
        result = await service.update_assistant_settings(mock_db, mock_user, request)

        mock_db.add.assert_called_once()
        added_row = mock_db.add.call_args.args[0]
        assert added_row.provider == "gemini"
        assert added_row.model == "gemini-2.0-pro"
        assert service._decrypt_assistant_api_key(added_row.encrypted_api_key) == "gemini-user-key"
        mock_db.commit.assert_called_once()
        assert result.gemini.has_api_key is True
        assert result.gemini.model == "gemini-2.0-pro"


class TestUpdateUserExtended:
    """Extended tests for update_user to cover additional fields"""

    @pytest.mark.asyncio
    async def test_update_user_last_name(self):
        """Should update last name"""
        from app.models import UserUpdate

        service = AuthService()
        mock_db = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.username = "testuser"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.email = "test@test.com"
        mock_user.role = UserRole.MEMBER
        mock_user.avatar_url = None
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.updated_at = datetime.now(timezone.utc)
        mock_user.is_active = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        mock_owner = MagicMock()
        mock_owner.id = "owner-123"
        mock_owner.role = UserRole.OWNER

        request = UserUpdate(last_name="NewLastName")

        await service.update_user(mock_db, "user-123", request, mock_owner)

        assert mock_user.last_name == "NewLastName"

    @pytest.mark.asyncio
    async def test_update_user_email(self):
        """Should update email"""
        from app.models import UserUpdate

        service = AuthService()
        mock_db = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.username = "testuser"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.email = "old@test.com"
        mock_user.role = UserRole.MEMBER
        mock_user.avatar_url = None
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.updated_at = datetime.now(timezone.utc)
        mock_user.is_active = True

        # First call returns user, second call (email check) returns None
        call_count = [0]

        def mock_execute(query):
            result = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                result.scalar_one_or_none.return_value = mock_user
            else:
                result.scalar_one_or_none.return_value = None
            return result

        mock_db.execute.side_effect = mock_execute

        mock_owner = MagicMock()
        mock_owner.id = "owner-123"
        mock_owner.role = UserRole.OWNER

        request = UserUpdate(email="new@test.com")

        await service.update_user(mock_db, "user-123", request, mock_owner)

        assert mock_user.email == "new@test.com"

    @pytest.mark.asyncio
    async def test_update_user_role(self):
        """Should update role when owner"""
        from app.models import UserUpdate

        service = AuthService()
        mock_db = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.username = "testuser"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.email = "test@test.com"
        mock_user.role = UserRole.MEMBER
        mock_user.avatar_url = None
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.updated_at = datetime.now(timezone.utc)
        mock_user.is_active = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        mock_owner = MagicMock()
        mock_owner.id = "owner-123"
        mock_owner.role = UserRole.OWNER

        request = UserUpdate(role=UserRole.ADMIN)

        await service.update_user(mock_db, "user-123", request, mock_owner)

        assert mock_user.role == UserRole.ADMIN


class TestCreateInviteEmailPaths:
    """Tests for create_invite email sending paths"""

    @pytest.mark.asyncio
    async def test_create_invite_email_configured_success(self):
        """Should send email when configured"""
        from app.models import InviteCreate

        service = AuthService()
        mock_db = AsyncMock()

        mock_owner = MagicMock()
        mock_owner.id = "owner-123"
        mock_owner.username = "owner"
        mock_owner.first_name = "Test"
        mock_owner.last_name = "Owner"
        mock_owner.role = UserRole.OWNER

        # Mock no existing user/invite
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        request = InviteCreate(email="new@test.com", role=UserRole.MEMBER)

        with (
            patch("app.services.email_service.is_email_configured", return_value=True),
            patch("app.services.email_service.send_invitation_email", return_value="email-123"),
        ):
            invite, email_sent = await service.create_invite(mock_db, request, mock_owner)

            assert email_sent is True

    @pytest.mark.asyncio
    async def test_create_invite_email_not_configured(self):
        """Should handle when email is not configured"""
        from app.models import InviteCreate

        service = AuthService()
        mock_db = AsyncMock()

        mock_owner = MagicMock()
        mock_owner.id = "owner-123"
        mock_owner.username = "owner"
        mock_owner.first_name = "Test"
        mock_owner.last_name = "Owner"
        mock_owner.role = UserRole.OWNER

        # Mock no existing user/invite
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        request = InviteCreate(email="new@test.com", role=UserRole.MEMBER)

        with patch("app.services.email_service.is_email_configured", return_value=False):
            invite, email_sent = await service.create_invite(mock_db, request, mock_owner)

            assert email_sent is False

    @pytest.mark.asyncio
    async def test_create_invite_email_exception(self):
        """Should handle email sending exception gracefully"""
        from app.models import InviteCreate

        service = AuthService()
        mock_db = AsyncMock()

        mock_owner = MagicMock()
        mock_owner.id = "owner-123"
        mock_owner.username = "owner"
        mock_owner.first_name = "Test"
        mock_owner.last_name = "Owner"
        mock_owner.role = UserRole.OWNER

        # Mock no existing user/invite
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        request = InviteCreate(email="new@test.com", role=UserRole.MEMBER)

        with (
            patch("app.services.email_service.is_email_configured", return_value=True),
            patch(
                "app.services.email_service.send_invitation_email",
                side_effect=Exception("Email error"),
            ),
        ):
            invite, email_sent = await service.create_invite(mock_db, request, mock_owner)

            # Should still create invite but email_sent should be False
            assert email_sent is False


class TestPasswordResetFlows:
    """Tests for password reset request/confirm service methods."""

    @pytest.mark.asyncio
    async def test_request_password_reset_creates_hashed_token_and_sends_email(self):
        service = AuthService()
        mock_db = AsyncMock()
        mock_db.add = MagicMock()

        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"

        empty_tokens_result = MagicMock()
        empty_tokens_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = empty_tokens_result

        with (
            patch.object(service, "get_user_by_email", new_callable=AsyncMock) as mock_get_user,
            patch("app.services.email_service.is_email_configured", return_value=True),
            patch(
                "app.services.email_service.send_password_reset_email",
                return_value="email-123",
            ) as mock_send_email,
        ):
            mock_get_user.return_value = mock_user

            result = await service.request_password_reset(mock_db, "test@example.com")

            assert result is True
            mock_db.add.assert_called_once()
            token_row = mock_db.add.call_args[0][0]
            assert token_row.user_id == mock_user.id
            assert len(token_row.token_hash) == 64
            assert token_row.token_hash != "email-123"
            mock_send_email.assert_called_once()
            await_count = mock_db.commit.await_count
            assert await_count == 1

    @pytest.mark.asyncio
    async def test_request_password_reset_is_noop_for_unknown_email(self):
        service = AuthService()
        mock_db = AsyncMock()

        with patch.object(service, "get_user_by_email", new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = None

            result = await service.request_password_reset(mock_db, "missing@example.com")

            assert result is True
            assert not mock_db.execute.await_count

    @pytest.mark.asyncio
    async def test_confirm_password_reset_updates_password_and_invalidates_active_tokens(self):
        service = AuthService()
        mock_db = AsyncMock()

        raw_token = "raw-reset-token"
        token_hash = service._hash_password_reset_token(raw_token)

        reset_token = MagicMock()
        reset_token.user_id = "user-123"
        reset_token.token_hash = token_hash
        reset_token.used_at = None
        reset_token.expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        other_token = MagicMock()
        other_token.used_at = None

        reset_result = MagicMock()
        reset_result.scalar_one_or_none.return_value = reset_token
        active_tokens_result = MagicMock()
        active_tokens_result.scalars.return_value.all.return_value = [reset_token, other_token]
        mock_db.execute = AsyncMock(side_effect=[reset_result, active_tokens_result])

        mock_user = MagicMock()
        mock_user.id = "user-123"
        mock_user.username = "testuser"
        mock_user.is_active = True
        mock_user.hashed_password = "old-hash"

        with (
            patch.object(service, "get_user", new_callable=AsyncMock) as mock_get_user,
            patch(
                "app.services.auth_service.hash_password_async", new_callable=AsyncMock
            ) as mock_hash,
        ):
            mock_get_user.return_value = mock_user
            mock_hash.return_value = "new-hash"

            result = await service.confirm_password_reset(mock_db, raw_token, "newpassword123")

            assert result is True
            assert mock_user.hashed_password == "new-hash"
            assert reset_token.used_at is not None
            assert other_token.used_at is not None
            assert mock_db.commit.await_count == 1

    @pytest.mark.asyncio
    async def test_confirm_password_reset_rejects_invalid_or_expired_token(self):
        service = AuthService()
        mock_db = AsyncMock()

        missing_result = MagicMock()
        missing_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = missing_result

        with pytest.raises(ValueError, match="Invalid or expired reset token"):
            await service.confirm_password_reset(mock_db, "invalid", "newpassword123")
