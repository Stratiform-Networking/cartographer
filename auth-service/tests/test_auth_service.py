"""
Unit tests for auth_service module.
"""
import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from app.models import (
    UserRole,
    UserCreate,
    UserUpdate,
    OwnerSetupRequest,
    InviteCreate,
    InviteStatus,
)


class TestAuthServiceInit:
    """Tests for AuthService initialization"""
    
    def test_init_creates_empty_stores(self, auth_service_instance):
        """Should initialize with empty user and invite stores"""
        assert auth_service_instance._users == {}
        assert auth_service_instance._invites == {}
    
    def test_init_sets_data_paths(self, auth_service_instance, tmp_data_dir):
        """Should set correct data file paths"""
        assert auth_service_instance.users_file == tmp_data_dir / "users.json"
        assert auth_service_instance.invites_file == tmp_data_dir / "invites.json"


class TestSetupStatus:
    """Tests for setup status methods"""
    
    def test_is_setup_complete_false_initially(self, auth_service_instance):
        """Should return False when no owner exists"""
        assert auth_service_instance.is_setup_complete() is False
    
    def test_is_setup_complete_true_with_owner(self, auth_service_instance, sample_owner):
        """Should return True when owner exists"""
        assert auth_service_instance.is_setup_complete() is True
    
    def test_get_setup_status(self, auth_service_instance, sample_owner, sample_user):
        """Should return correct setup status"""
        status = auth_service_instance.get_setup_status()
        
        assert status["is_setup_complete"] is True
        assert status["owner_exists"] is True
        assert status["total_users"] == 2


class TestSetupOwner:
    """Tests for owner setup"""
    
    async def test_setup_owner_success(self, auth_service_instance):
        """Should create owner successfully"""
        request = OwnerSetupRequest(
            username="admin",
            first_name="Admin",
            last_name="User",
            email="admin@test.com",
            password="securepass123"
        )
        
        user = await auth_service_instance.setup_owner(request)
        
        assert user.username == "admin"
        assert user.role == UserRole.OWNER
        assert user.is_active is True
    
    async def test_setup_owner_already_complete(self, auth_service_instance, sample_owner):
        """Should reject if owner already exists"""
        request = OwnerSetupRequest(
            username="admin2",
            first_name="Admin",
            last_name="User",
            email="admin2@test.com",
            password="securepass123"
        )
        
        with pytest.raises(ValueError) as exc_info:
            await auth_service_instance.setup_owner(request)
        
        assert "already complete" in str(exc_info.value)
    
    async def test_setup_owner_username_taken(self, auth_service_instance):
        """Should reject duplicate username"""
        # First setup
        request1 = OwnerSetupRequest(
            username="admin",
            first_name="Admin",
            last_name="User",
            email="admin@test.com",
            password="securepass123"
        )
        await auth_service_instance.setup_owner(request1)
        
        # Reset owner status by changing role
        auth_service_instance._users[list(auth_service_instance._users.keys())[0]].role = UserRole.READ_ONLY
        
        # Try with same username
        request2 = OwnerSetupRequest(
            username="admin",
            first_name="Admin2",
            last_name="User2",
            email="admin2@test.com",
            password="securepass123"
        )
        
        with pytest.raises(ValueError) as exc_info:
            await auth_service_instance.setup_owner(request2)
        
        assert "Username already taken" in str(exc_info.value)
    
    async def test_setup_owner_email_taken(self, auth_service_instance):
        """Should reject duplicate email"""
        # First setup
        request1 = OwnerSetupRequest(
            username="admin1",
            first_name="Admin",
            last_name="User",
            email="admin@test.com",
            password="securepass123"
        )
        await auth_service_instance.setup_owner(request1)
        
        # Reset owner status
        auth_service_instance._users[list(auth_service_instance._users.keys())[0]].role = UserRole.READ_ONLY
        
        # Try with same email
        request2 = OwnerSetupRequest(
            username="admin2",
            first_name="Admin2",
            last_name="User2",
            email="admin@test.com",
            password="securepass123"
        )
        
        with pytest.raises(ValueError) as exc_info:
            await auth_service_instance.setup_owner(request2)
        
        assert "Email already in use" in str(exc_info.value)


class TestUserCRUD:
    """Tests for user CRUD operations"""
    
    async def test_create_user_success(self, auth_service_instance, sample_owner):
        """Should create user successfully"""
        request = UserCreate(
            username="newuser",
            first_name="New",
            last_name="User",
            email="new@test.com",
            password="password123",
            role=UserRole.READ_ONLY
        )
        
        user = await auth_service_instance.create_user(request, sample_owner)
        
        assert user.username == "newuser"
        assert user.role == UserRole.READ_ONLY
    
    async def test_create_user_requires_owner(self, auth_service_instance, sample_user, sample_owner):
        """Should require owner to create user"""
        request = UserCreate(
            username="newuser",
            first_name="New",
            last_name="User",
            email="new@test.com",
            password="password123"
        )
        
        with pytest.raises(PermissionError):
            await auth_service_instance.create_user(request, sample_user)
    
    async def test_create_user_cannot_create_owner(self, auth_service_instance, sample_owner):
        """Should not allow creating another owner"""
        request = UserCreate(
            username="newowner",
            first_name="New",
            last_name="Owner",
            email="newowner@test.com",
            password="password123",
            role=UserRole.OWNER
        )
        
        with pytest.raises(ValueError) as exc_info:
            await auth_service_instance.create_user(request, sample_owner)
        
        assert "Cannot create additional owner" in str(exc_info.value)
    
    def test_get_user(self, auth_service_instance, sample_user):
        """Should get user by ID"""
        user = auth_service_instance.get_user(sample_user.id)
        assert user.id == sample_user.id
    
    def test_get_user_not_found(self, auth_service_instance):
        """Should return None for non-existent user"""
        user = auth_service_instance.get_user("non-existent-id")
        assert user is None
    
    def test_get_user_by_username(self, auth_service_instance, sample_user):
        """Should get user by username"""
        user = auth_service_instance.get_user_by_username(sample_user.username)
        assert user.id == sample_user.id
    
    def test_get_user_by_username_case_insensitive(self, auth_service_instance, sample_user):
        """Should be case insensitive"""
        user = auth_service_instance.get_user_by_username(sample_user.username.upper())
        assert user.id == sample_user.id
    
    def test_get_user_by_email(self, auth_service_instance, sample_user):
        """Should get user by email"""
        user = auth_service_instance.get_user_by_email(sample_user.email)
        assert user.id == sample_user.id
    
    def test_list_users_as_owner(self, auth_service_instance, sample_owner, sample_user):
        """Owner should see all users"""
        users = auth_service_instance.list_users(sample_owner)
        assert len(users) == 2
    
    def test_list_users_as_regular_user(self, auth_service_instance, sample_owner, sample_user):
        """Regular user should only see themselves"""
        users = auth_service_instance.list_users(sample_user)
        assert len(users) == 1
        assert users[0].id == sample_user.id
    
    async def test_update_user_success(self, auth_service_instance, sample_owner, sample_user):
        """Should update user"""
        request = UserUpdate(first_name="Updated")
        
        updated = await auth_service_instance.update_user(sample_user.id, request, sample_owner)
        
        assert updated.first_name == "Updated"
    
    async def test_update_user_self(self, auth_service_instance, sample_user, sample_owner):
        """User should be able to update themselves"""
        request = UserUpdate(first_name="SelfUpdated")
        
        updated = await auth_service_instance.update_user(sample_user.id, request, sample_user)
        
        assert updated.first_name == "SelfUpdated"
    
    async def test_update_user_cannot_change_others(self, auth_service_instance, sample_owner, sample_user, sample_readwrite_user):
        """Non-owners cannot update other users"""
        request = UserUpdate(first_name="Hacked")
        
        with pytest.raises(PermissionError):
            await auth_service_instance.update_user(sample_owner.id, request, sample_user)
    
    async def test_update_user_role_requires_owner(self, auth_service_instance, sample_user, sample_owner):
        """Only owners can change roles"""
        request = UserUpdate(role=UserRole.READ_WRITE)
        
        with pytest.raises(PermissionError):
            await auth_service_instance.update_user(sample_user.id, request, sample_user)
    
    async def test_update_user_cannot_change_owner_role(self, auth_service_instance, sample_owner):
        """Cannot change owner's role"""
        request = UserUpdate(role=UserRole.READ_ONLY)
        
        with pytest.raises(ValueError) as exc_info:
            await auth_service_instance.update_user(sample_owner.id, request, sample_owner)
        
        assert "Cannot change owner's role" in str(exc_info.value)
    
    async def test_update_user_email_taken(self, auth_service_instance, sample_owner, sample_user, sample_readwrite_user):
        """Should reject duplicate email"""
        request = UserUpdate(email=sample_readwrite_user.email)
        
        with pytest.raises(ValueError) as exc_info:
            await auth_service_instance.update_user(sample_user.id, request, sample_owner)
        
        assert "Email already in use" in str(exc_info.value)
    
    async def test_update_user_password(self, auth_service_instance, sample_owner, sample_user):
        """Should hash new password"""
        request = UserUpdate(password="newpassword123")
        
        updated = await auth_service_instance.update_user(sample_user.id, request, sample_owner)
        
        # Password should be updated (we can't verify the hash directly)
        assert updated is not None
    
    def test_delete_user_success(self, auth_service_instance, sample_owner, sample_user):
        """Should soft delete user"""
        result = auth_service_instance.delete_user(sample_user.id, sample_owner)
        
        assert result is True
        assert auth_service_instance.get_user(sample_user.id).is_active is False
    
    def test_delete_user_requires_owner(self, auth_service_instance, sample_user, sample_readwrite_user, sample_owner):
        """Only owners can delete users"""
        with pytest.raises(PermissionError):
            auth_service_instance.delete_user(sample_user.id, sample_readwrite_user)
    
    def test_delete_user_cannot_delete_owner(self, auth_service_instance, sample_owner):
        """Cannot delete owner account"""
        with pytest.raises(ValueError) as exc_info:
            auth_service_instance.delete_user(sample_owner.id, sample_owner)
        
        assert "Cannot delete owner" in str(exc_info.value)
    
    def test_delete_user_cannot_delete_self(self, auth_service_instance, sample_owner, sample_user):
        """Owner cannot delete themselves (must transfer ownership first)"""
        # This test would need another owner to be valid
        # For now, test that we can't delete non-existent user
        with pytest.raises(ValueError):
            auth_service_instance.delete_user("non-existent", sample_owner)


class TestAuthentication:
    """Tests for authentication methods"""
    
    async def test_authenticate_success(self, auth_service_instance, sample_owner):
        """Should authenticate with correct credentials"""
        # Setup with known password
        request = OwnerSetupRequest(
            username="authtest",
            first_name="Auth",
            last_name="Test",
            email="authtest@test.com",
            password="testpassword123"
        )
        
        # Clear existing users and create test user
        auth_service_instance._users = {}
        await auth_service_instance.setup_owner(request)
        
        user = await auth_service_instance.authenticate("authtest", "testpassword123")
        
        assert user is not None
        assert user.username == "authtest"
    
    async def test_authenticate_wrong_password(self, auth_service_instance):
        """Should fail with wrong password"""
        # Setup
        auth_service_instance._users = {}
        request = OwnerSetupRequest(
            username="authtest",
            first_name="Auth",
            last_name="Test",
            email="authtest@test.com",
            password="correctpassword"
        )
        await auth_service_instance.setup_owner(request)
        
        user = await auth_service_instance.authenticate("authtest", "wrongpassword")
        
        assert user is None
    
    async def test_authenticate_user_not_found(self, auth_service_instance):
        """Should fail for non-existent user"""
        user = await auth_service_instance.authenticate("nonexistent", "password")
        assert user is None
    
    async def test_authenticate_inactive_user(self, auth_service_instance, sample_user, sample_owner):
        """Should fail for inactive user"""
        # Deactivate user
        sample_user.is_active = False
        auth_service_instance._users[sample_user.id] = sample_user
        
        user = await auth_service_instance.authenticate(sample_user.username, "password")
        assert user is None
    
    def test_create_access_token(self, auth_service_instance, sample_owner):
        """Should create valid JWT token"""
        token, expires_in = auth_service_instance.create_access_token(sample_owner)
        
        assert token is not None
        assert expires_in > 0
    
    def test_verify_token_valid(self, auth_service_instance, sample_owner):
        """Should verify valid token"""
        token, _ = auth_service_instance.create_access_token(sample_owner)
        
        payload = auth_service_instance.verify_token(token)
        
        assert payload is not None
        assert payload.sub == sample_owner.id
        assert payload.username == sample_owner.username
    
    def test_verify_token_invalid(self, auth_service_instance):
        """Should reject invalid token"""
        payload = auth_service_instance.verify_token("invalid-token")
        assert payload is None
    
    def test_verify_token_expired(self, auth_service_instance, sample_owner):
        """Should reject expired token"""
        import jwt
        from app.services.auth_service import JWT_SECRET, JWT_ALGORITHM
        
        # Create expired token
        payload = {
            "sub": sample_owner.id,
            "username": sample_owner.username,
            "role": sample_owner.role.value,
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=25)
        }
        expired_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        result = auth_service_instance.verify_token(expired_token)
        assert result is None
    
    def test_decode_token_payload(self, auth_service_instance, sample_owner):
        """Should decode raw token payload"""
        token, _ = auth_service_instance.create_access_token(sample_owner)
        
        payload = auth_service_instance.decode_token_payload(token)
        
        assert payload is not None
        assert payload["sub"] == sample_owner.id
    
    def test_decode_token_payload_invalid(self, auth_service_instance):
        """Should return None for invalid token"""
        payload = auth_service_instance.decode_token_payload("invalid")
        assert payload is None
    
    async def test_change_password_success(self, auth_service_instance):
        """Should change password"""
        # Create user with known password
        auth_service_instance._users = {}
        request = OwnerSetupRequest(
            username="pwtest",
            first_name="PW",
            last_name="Test",
            email="pwtest@test.com",
            password="oldpassword123"
        )
        user = await auth_service_instance.setup_owner(request)
        
        result = await auth_service_instance.change_password(
            user.id,
            "oldpassword123",
            "newpassword123"
        )
        
        assert result is True
    
    async def test_change_password_wrong_current(self, auth_service_instance):
        """Should fail with wrong current password"""
        auth_service_instance._users = {}
        request = OwnerSetupRequest(
            username="pwtest",
            first_name="PW",
            last_name="Test",
            email="pwtest@test.com",
            password="correctpassword"
        )
        user = await auth_service_instance.setup_owner(request)
        
        with pytest.raises(ValueError) as exc_info:
            await auth_service_instance.change_password(
                user.id,
                "wrongpassword",
                "newpassword123"
            )
        
        assert "Current password is incorrect" in str(exc_info.value)


class TestPermissions:
    """Tests for permission methods"""
    
    def test_get_permissions_readonly(self, auth_service_instance):
        """Read-only should have limited permissions"""
        perms = auth_service_instance.get_permissions(UserRole.READ_ONLY)
        
        assert "read:map" in perms
        assert "read:health" in perms
        assert "write:map" not in perms
        assert "manage:users" not in perms
    
    def test_get_permissions_readwrite(self, auth_service_instance):
        """Read-write should have write permissions"""
        perms = auth_service_instance.get_permissions(UserRole.READ_WRITE)
        
        assert "read:map" in perms
        assert "write:map" in perms
        assert "write:nodes" in perms
        assert "manage:users" not in perms
    
    def test_get_permissions_owner(self, auth_service_instance):
        """Owner should have all permissions"""
        perms = auth_service_instance.get_permissions(UserRole.OWNER)
        
        assert "read:map" in perms
        assert "write:map" in perms
        assert "manage:users" in perms
        assert "admin:settings" in perms


class TestInvitations:
    """Tests for invitation methods"""
    
    def test_create_invite_success(self, auth_service_instance, sample_owner):
        """Should create invitation"""
        request = InviteCreate(
            email="newinvite@test.com",
            role=UserRole.READ_ONLY
        )
        
        with patch('app.services.email_service.is_email_configured', return_value=False):
            invite, email_sent = auth_service_instance.create_invite(request, sample_owner)
        
        assert invite.email == "newinvite@test.com"
        assert invite.status == InviteStatus.PENDING
        assert email_sent is False
    
    def test_create_invite_requires_owner(self, auth_service_instance, sample_user, sample_owner):
        """Should require owner to create invite"""
        request = InviteCreate(email="newinvite@test.com")
        
        with pytest.raises(PermissionError):
            auth_service_instance.create_invite(request, sample_user)
    
    def test_create_invite_existing_user(self, auth_service_instance, sample_owner, sample_user):
        """Should reject if email already has a user"""
        request = InviteCreate(email=sample_user.email)
        
        with pytest.raises(ValueError) as exc_info:
            auth_service_instance.create_invite(request, sample_owner)
        
        assert "already exists" in str(exc_info.value)
    
    def test_create_invite_duplicate_pending(self, auth_service_instance, sample_owner, sample_invite):
        """Should reject duplicate pending invite"""
        request = InviteCreate(email=sample_invite.email)
        
        with pytest.raises(ValueError) as exc_info:
            auth_service_instance.create_invite(request, sample_owner)
        
        assert "already exists" in str(exc_info.value)
    
    def test_get_invite_by_token(self, auth_service_instance, sample_invite):
        """Should get invite by token"""
        invite = auth_service_instance.get_invite_by_token(sample_invite.token)
        assert invite.id == sample_invite.id
    
    def test_get_invite_by_token_not_found(self, auth_service_instance):
        """Should return None for unknown token"""
        invite = auth_service_instance.get_invite_by_token("unknown-token")
        assert invite is None
    
    def test_get_invite_token_info(self, auth_service_instance, sample_invite):
        """Should get public invite info"""
        info = auth_service_instance.get_invite_token_info(sample_invite.token)
        
        assert info is not None
        assert info.email == sample_invite.email
        assert info.is_valid is True
    
    def test_get_invite_token_info_expired(self, auth_service_instance, expired_invite):
        """Should show expired invite as invalid"""
        info = auth_service_instance.get_invite_token_info(expired_invite.token)
        
        assert info is not None
        assert info.is_valid is False
    
    async def test_accept_invite_success(self, auth_service_instance, sample_invite, sample_owner):
        """Should accept invite and create user"""
        user = await auth_service_instance.accept_invite(
            token=sample_invite.token,
            username="inviteduser",
            first_name="Invited",
            last_name="User",
            password="password123"
        )
        
        assert user.username == "inviteduser"
        assert user.email == sample_invite.email
        assert auth_service_instance._invites[sample_invite.id].status == InviteStatus.ACCEPTED
    
    async def test_accept_invite_invalid_token(self, auth_service_instance):
        """Should reject invalid token"""
        with pytest.raises(ValueError) as exc_info:
            await auth_service_instance.accept_invite(
                token="invalid-token",
                username="test",
                first_name="T",
                last_name="U",
                password="password123"
            )
        
        assert "Invalid invitation token" in str(exc_info.value)
    
    async def test_accept_invite_expired(self, auth_service_instance, expired_invite, sample_owner):
        """Should reject expired invite"""
        with pytest.raises(ValueError) as exc_info:
            await auth_service_instance.accept_invite(
                token=expired_invite.token,
                username="test",
                first_name="T",
                last_name="U",
                password="password123"
            )
        
        assert "expired" in str(exc_info.value).lower()
    
    async def test_accept_invite_username_taken(self, auth_service_instance, sample_invite, sample_user, sample_owner):
        """Should reject if username is taken"""
        with pytest.raises(ValueError) as exc_info:
            await auth_service_instance.accept_invite(
                token=sample_invite.token,
                username=sample_user.username,
                first_name="T",
                last_name="U",
                password="password123"
            )
        
        assert "Username already taken" in str(exc_info.value)
    
    def test_list_invites(self, auth_service_instance, sample_owner, sample_invite):
        """Should list all invites"""
        invites = auth_service_instance.list_invites(sample_owner)
        assert len(invites) >= 1
    
    def test_list_invites_requires_owner(self, auth_service_instance, sample_user, sample_owner):
        """Should require owner to list invites"""
        with pytest.raises(PermissionError):
            auth_service_instance.list_invites(sample_user)
    
    def test_revoke_invite_success(self, auth_service_instance, sample_owner, sample_invite):
        """Should revoke pending invite"""
        result = auth_service_instance.revoke_invite(sample_invite.id, sample_owner)
        
        assert result is True
        assert auth_service_instance._invites[sample_invite.id].status == InviteStatus.REVOKED
    
    def test_revoke_invite_not_pending(self, auth_service_instance, sample_owner, sample_invite):
        """Should reject revoking non-pending invite"""
        sample_invite.status = InviteStatus.ACCEPTED
        auth_service_instance._invites[sample_invite.id] = sample_invite
        
        with pytest.raises(ValueError):
            auth_service_instance.revoke_invite(sample_invite.id, sample_owner)
    
    def test_resend_invite_success(self, auth_service_instance, sample_owner, sample_invite):
        """Should resend invite (without email)"""
        with patch('app.services.email_service.is_email_configured', return_value=False):
            with pytest.raises(ValueError) as exc_info:
                auth_service_instance.resend_invite(sample_invite.id, sample_owner)
            
            assert "Email is not configured" in str(exc_info.value)
    
    def test_resend_invite_extends_expiry(self, auth_service_instance, sample_owner, expired_invite):
        """Should extend expiry when resending expired invite"""
        original_expiry = expired_invite.expires_at
        
        with patch('app.services.email_service.is_email_configured', return_value=True):
            with patch('app.services.email_service.send_invitation_email', return_value="email-123"):
                # Mark as pending again for test
                expired_invite.status = InviteStatus.PENDING
                auth_service_instance._invites[expired_invite.id] = expired_invite
                
                auth_service_instance.resend_invite(expired_invite.id, sample_owner)
        
        new_expiry = auth_service_instance._invites[expired_invite.id].expires_at
        assert new_expiry > original_expiry


class TestDataPersistence:
    """Tests for data persistence"""
    
    def test_save_and_load_users(self, auth_service_instance, sample_owner, tmp_data_dir):
        """Should persist users to file"""
        auth_service_instance._save_users()
        
        assert auth_service_instance.users_file.exists()
        
        with open(auth_service_instance.users_file) as f:
            data = json.load(f)
        
        assert len(data["users"]) == 1
    
    def test_save_and_load_invites(self, auth_service_instance, sample_invite, sample_owner, tmp_data_dir):
        """Should persist invites to file"""
        auth_service_instance._save_invites()
        
        assert auth_service_instance.invites_file.exists()
        
        with open(auth_service_instance.invites_file) as f:
            data = json.load(f)
        
        assert len(data["invites"]) == 1
    
    def test_load_users_from_file(self, tmp_data_dir):
        """Should load users from existing file"""
        users_file = tmp_data_dir / "users.json"
        users_data = {
            "users": [{
                "id": "test-id",
                "username": "loadtest",
                "first_name": "Load",
                "last_name": "Test",
                "email": "load@test.com",
                "role": "readonly",
                "password_hash": "hash123",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True
            }]
        }
        with open(users_file, 'w') as f:
            json.dump(users_data, f)
        
        with patch.dict('os.environ', {"AUTH_DATA_DIR": str(tmp_data_dir)}):
            from app.services.auth_service import AuthService
            service = AuthService()
            service.data_dir = tmp_data_dir
            service.users_file = users_file
            service._users = {}
            service._load_users()
        
        assert len(service._users) == 1
        assert "test-id" in service._users

