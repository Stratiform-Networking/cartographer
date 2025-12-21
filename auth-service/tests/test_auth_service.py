"""
Unit tests for auth_service module.
Tests for the database-backed AuthService.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from app.models import UserRole, UserResponse
from app.services.auth_service import (
    AuthService, 
    hash_password_async, 
    verify_password_async,
    JWT_SECRET, 
    JWT_ALGORITHM
)


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
            "exp": now - timedelta(hours=24)  # Expired 24 hours ago
        }
        expired_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
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
        mock_user.role = UserRole.MEMBER
        mock_user.created_at = datetime.now(timezone.utc)
        mock_user.updated_at = datetime.now(timezone.utc)
        mock_user.last_login_at = None
        mock_user.is_active = True
        
        response = service._to_response(mock_user)
        
        assert isinstance(response, UserResponse)
        assert response.id == mock_user.id
        assert response.username == mock_user.username


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
        
        with patch('app.services.auth_service.verify_password_async', new_callable=AsyncMock) as mock_verify, \
             patch('app.services.auth_service.hash_password_async', new_callable=AsyncMock) as mock_hash:
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
        
        with patch('app.services.auth_service.verify_password_async', new_callable=AsyncMock) as mock_verify:
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
        
        with patch('app.services.auth_service.verify_password_async', new_callable=AsyncMock) as mock_verify:
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
        
        with patch('app.services.auth_service.verify_password_async', new_callable=AsyncMock) as mock_verify:
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
        
        with patch('app.services.auth_service.verify_password_async', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = True
            
            result = await service.authenticate(mock_db, "testuser", "password123")
            
            assert result is None
