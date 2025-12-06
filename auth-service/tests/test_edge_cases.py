"""
Edge case and integration tests for additional coverage.
"""
import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.models import (
    UserRole,
    UserResponse,
    UserInDB,
    UserUpdate,
    InviteStatus,
    InviteInDB,
    TokenPayload,
)
from app.routers.auth import router


@pytest.fixture
def app():
    """Create test app with auth router"""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/auth")
    return test_app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_owner():
    """Create mock owner user"""
    now = datetime.now(timezone.utc)
    return UserInDB(
        id="owner-123",
        username="owner",
        first_name="Test",
        last_name="Owner",
        email="owner@test.com",
        role=UserRole.OWNER,
        password_hash="hash",
        created_at=now,
        updated_at=now,
        is_active=True
    )


@pytest.fixture
def mock_user():
    """Create mock regular user"""
    now = datetime.now(timezone.utc)
    return UserInDB(
        id="user-456",
        username="testuser",
        first_name="Test",
        last_name="User",
        email="user@test.com",
        role=UserRole.READ_ONLY,
        password_hash="hash",
        created_at=now,
        updated_at=now,
        is_active=True
    )


class TestRouterErrorHandling:
    """Tests for router error handling paths"""
    
    def test_create_user_value_error(self, client, mock_owner):
        """Should return 400 on ValueError"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc)
            )
            mock_service.get_user.return_value = mock_owner
            mock_service.create_user = AsyncMock(side_effect=ValueError("Username taken"))
            
            response = client.post(
                "/api/auth/users",
                headers={"Authorization": "Bearer token123"},
                json={
                    "username": "newuser",
                    "first_name": "New",
                    "last_name": "User",
                    "email": "new@test.com",
                    "password": "password123"
                }
            )
            
            assert response.status_code == 400
    
    def test_create_user_permission_error(self, client, mock_owner):
        """Should return 400 on PermissionError"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc)
            )
            mock_service.get_user.return_value = mock_owner
            mock_service.create_user = AsyncMock(side_effect=PermissionError("Not allowed"))
            
            response = client.post(
                "/api/auth/users",
                headers={"Authorization": "Bearer token123"},
                json={
                    "username": "newuser",
                    "first_name": "New",
                    "last_name": "User",
                    "email": "new@test.com",
                    "password": "password123"
                }
            )
            
            assert response.status_code == 400
    
    def test_get_user_not_found(self, client, mock_owner):
        """Should return 404 when user not found"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc)
            )
            # First call for auth, second for target user
            mock_service.get_user.side_effect = [mock_owner, None]
            
            response = client.get(
                "/api/auth/users/nonexistent",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 404
    
    def test_update_user_permission_error(self, client, mock_owner):
        """Should return 403 on PermissionError"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc)
            )
            mock_service.get_user.return_value = mock_owner
            mock_service.update_user = AsyncMock(side_effect=PermissionError("Not allowed"))
            
            response = client.patch(
                f"/api/auth/users/{mock_owner.id}",
                headers={"Authorization": "Bearer token123"},
                json={"first_name": "Updated"}
            )
            
            assert response.status_code == 403
    
    def test_update_user_value_error(self, client, mock_owner):
        """Should return 400 on ValueError"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc)
            )
            mock_service.get_user.return_value = mock_owner
            mock_service.update_user = AsyncMock(side_effect=ValueError("Invalid"))
            
            response = client.patch(
                f"/api/auth/users/{mock_owner.id}",
                headers={"Authorization": "Bearer token123"},
                json={"first_name": "Updated"}
            )
            
            assert response.status_code == 400
    
    def test_delete_user_value_error(self, client, mock_owner, mock_user):
        """Should return 400 on ValueError"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc)
            )
            mock_service.get_user.return_value = mock_owner
            mock_service.delete_user.side_effect = ValueError("Cannot delete")
            
            response = client.delete(
                f"/api/auth/users/{mock_user.id}",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 400
    
    def test_delete_user_permission_error(self, client, mock_owner, mock_user):
        """Should return 403 on PermissionError"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc)
            )
            mock_service.get_user.return_value = mock_owner
            mock_service.delete_user.side_effect = PermissionError("Not owner")
            
            response = client.delete(
                f"/api/auth/users/{mock_user.id}",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 403
    
    def test_update_profile_value_error(self, client, mock_owner):
        """Should return 400 on ValueError for profile update"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc)
            )
            mock_service.get_user.return_value = mock_owner
            mock_service.update_user = AsyncMock(side_effect=ValueError("Invalid"))
            
            response = client.patch(
                "/api/auth/me",
                headers={"Authorization": "Bearer token123"},
                json={"first_name": "Updated"}
            )
            
            assert response.status_code == 400
    
    def test_change_password_error(self, client, mock_owner):
        """Should return 400 on password change error"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc)
            )
            mock_service.get_user.return_value = mock_owner
            mock_service.change_password = AsyncMock(side_effect=ValueError("Wrong password"))
            
            response = client.post(
                "/api/auth/me/change-password",
                headers={"Authorization": "Bearer token123"},
                json={
                    "current_password": "wrongpassword",
                    "new_password": "newpassword123"
                }
            )
            
            assert response.status_code == 400
    
    def test_list_invites_permission_error(self, client, mock_owner):
        """Should return 403 on permission error listing invites"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc)
            )
            mock_service.get_user.return_value = mock_owner
            mock_service.list_invites.side_effect = PermissionError("Not owner")
            
            response = client.get(
                "/api/auth/invites",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 403
    
    def test_create_invite_errors(self, client, mock_owner):
        """Should return 400 on invite creation errors"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc)
            )
            mock_service.get_user.return_value = mock_owner
            mock_service.create_invite.side_effect = ValueError("Email exists")
            
            response = client.post(
                "/api/auth/invites",
                headers={"Authorization": "Bearer token123"},
                json={"email": "existing@test.com", "role": "readonly"}
            )
            
            assert response.status_code == 400
    
    def test_get_invite_not_found(self, client, mock_owner):
        """Should return 404 for non-existent invite"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc)
            )
            mock_service.get_user.return_value = mock_owner
            mock_service._invites = {}
            
            response = client.get(
                "/api/auth/invites/nonexistent",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 404
    
    def test_revoke_invite_value_error(self, client, mock_owner):
        """Should return 400 on ValueError"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc)
            )
            mock_service.get_user.return_value = mock_owner
            mock_service.revoke_invite.side_effect = ValueError("Already revoked")
            
            response = client.delete(
                "/api/auth/invites/invite-123",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 400
    
    def test_revoke_invite_permission_error(self, client, mock_owner):
        """Should return 403 on PermissionError"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc)
            )
            mock_service.get_user.return_value = mock_owner
            mock_service.revoke_invite.side_effect = PermissionError("Not owner")
            
            response = client.delete(
                "/api/auth/invites/invite-123",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 403
    
    def test_resend_invite_errors(self, client, mock_owner):
        """Should return 400 on resend errors"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc)
            )
            mock_service.get_user.return_value = mock_owner
            mock_service.resend_invite.side_effect = ValueError("Cannot resend")
            
            response = client.post(
                "/api/auth/invites/invite-123/resend",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 400
    
    def test_resend_invite_permission_error(self, client, mock_owner):
        """Should return 403 on permission error"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc)
            )
            mock_service.get_user.return_value = mock_owner
            mock_service.resend_invite.side_effect = PermissionError("Not owner")
            
            response = client.post(
                "/api/auth/invites/invite-123/resend",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 403
    
    def test_accept_invite_error(self, client):
        """Should return 400 on accept error"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.accept_invite = AsyncMock(side_effect=ValueError("Invalid token"))
            
            response = client.post("/api/auth/invite/accept", json={
                "token": "invalid-token",
                "username": "newuser",
                "first_name": "New",
                "last_name": "User",
                "password": "password123"
            })
            
            assert response.status_code == 400
    
    def test_verify_token_inactive_user(self, client, mock_owner):
        """Should return invalid for inactive user"""
        mock_owner.is_active = False
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc)
            )
            mock_service.decode_token_payload.return_value = {}
            mock_service.get_user.return_value = mock_owner
            
            response = client.post(
                "/api/auth/verify",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 200
            assert response.json()["valid"] is False


class TestAuthServiceEdgeCases:
    """Edge cases for auth service"""
    
    def test_get_user_by_username_inactive_excluded(self, auth_service_instance, sample_user, sample_owner):
        """Should exclude inactive users by default"""
        sample_user.is_active = False
        auth_service_instance._users[sample_user.id] = sample_user
        
        user = auth_service_instance.get_user_by_username(sample_user.username)
        assert user is None
    
    def test_get_user_by_username_inactive_included(self, auth_service_instance, sample_user, sample_owner):
        """Should include inactive users when requested"""
        sample_user.is_active = False
        auth_service_instance._users[sample_user.id] = sample_user
        
        user = auth_service_instance.get_user_by_username(sample_user.username, include_inactive=True)
        assert user is not None
    
    def test_get_user_by_email_inactive_excluded(self, auth_service_instance, sample_user, sample_owner):
        """Should exclude inactive users by default"""
        sample_user.is_active = False
        auth_service_instance._users[sample_user.id] = sample_user
        
        user = auth_service_instance.get_user_by_email(sample_user.email)
        assert user is None
    
    def test_get_user_by_email_inactive_included(self, auth_service_instance, sample_user, sample_owner):
        """Should include inactive users when requested"""
        sample_user.is_active = False
        auth_service_instance._users[sample_user.id] = sample_user
        
        user = auth_service_instance.get_user_by_email(sample_user.email, include_inactive=True)
        assert user is not None
    
    async def test_update_user_not_found(self, auth_service_instance, sample_owner):
        """Should raise for non-existent user"""
        from app.models import UserUpdate
        
        with pytest.raises(ValueError) as exc_info:
            await auth_service_instance.update_user("nonexistent", UserUpdate(), sample_owner)
        
        assert "not found" in str(exc_info.value)
    
    def test_delete_user_not_found(self, auth_service_instance, sample_owner):
        """Should raise for non-existent user"""
        with pytest.raises(ValueError) as exc_info:
            auth_service_instance.delete_user("nonexistent", sample_owner)
        
        assert "not found" in str(exc_info.value)
    
    def test_delete_user_cannot_delete_self(self, auth_service_instance, sample_owner):
        """Should prevent owner from deleting themselves"""
        # Create a non-owner to test with
        from app.models import UserInDB
        now = datetime.now(timezone.utc)
        other_owner = UserInDB(
            id="other-owner",
            username="otherowner",
            first_name="Other",
            last_name="Owner",
            email="other@test.com",
            role=UserRole.OWNER,
            password_hash="hash",
            created_at=now,
            updated_at=now,
            is_active=True
        )
        auth_service_instance._users[other_owner.id] = other_owner
        
        with pytest.raises(ValueError) as exc_info:
            auth_service_instance.delete_user(sample_owner.id, sample_owner)
        
        assert "Cannot delete" in str(exc_info.value)
    
    async def test_change_password_user_not_found(self, auth_service_instance):
        """Should raise for non-existent user"""
        with pytest.raises(ValueError) as exc_info:
            await auth_service_instance.change_password("nonexistent", "old", "new")
        
        assert "not found" in str(exc_info.value)
    
    def test_revoke_invite_not_found(self, auth_service_instance, sample_owner):
        """Should raise for non-existent invite"""
        with pytest.raises(ValueError) as exc_info:
            auth_service_instance.revoke_invite("nonexistent", sample_owner)
        
        assert "not found" in str(exc_info.value)
    
    def test_resend_invite_not_found(self, auth_service_instance, sample_owner):
        """Should raise for non-existent invite"""
        with pytest.raises(ValueError) as exc_info:
            auth_service_instance.resend_invite("nonexistent", sample_owner)
        
        assert "not found" in str(exc_info.value)
    
    def test_resend_invite_not_pending(self, auth_service_instance, sample_owner, sample_invite):
        """Should raise for non-pending invite"""
        sample_invite.status = InviteStatus.ACCEPTED
        auth_service_instance._invites[sample_invite.id] = sample_invite
        
        with pytest.raises(ValueError) as exc_info:
            auth_service_instance.resend_invite(sample_invite.id, sample_owner)
        
        assert "Cannot resend" in str(exc_info.value)
    
    async def test_accept_invite_not_pending(self, auth_service_instance, sample_invite, sample_owner):
        """Should raise for non-pending invite"""
        sample_invite.status = InviteStatus.REVOKED
        auth_service_instance._invites[sample_invite.id] = sample_invite
        
        with pytest.raises(ValueError) as exc_info:
            await auth_service_instance.accept_invite(
                token=sample_invite.token,
                username="test",
                first_name="T",
                last_name="U",
                password="password123"
            )
        
        assert "no longer valid" in str(exc_info.value)
    
    async def test_accept_invite_email_already_exists(self, auth_service_instance, sample_invite, sample_owner):
        """Should handle edge case of email already existing"""
        # Create user with same email as invite
        from app.models import UserInDB
        now = datetime.now(timezone.utc)
        existing = UserInDB(
            id="existing-user",
            username="existing",
            first_name="Existing",
            last_name="User",
            email=sample_invite.email,
            role=UserRole.READ_ONLY,
            password_hash="hash",
            created_at=now,
            updated_at=now,
            is_active=True
        )
        auth_service_instance._users[existing.id] = existing
        
        with pytest.raises(ValueError) as exc_info:
            await auth_service_instance.accept_invite(
                token=sample_invite.token,
                username="newuser",
                first_name="New",
                last_name="User",
                password="password123"
            )
        
        assert "already exists" in str(exc_info.value)


class TestPersistenceErrors:
    """Tests for persistence error handling"""
    
    def test_load_users_handles_error(self, tmp_data_dir):
        """Should handle errors loading users"""
        users_file = tmp_data_dir / "users.json"
        users_file.write_text("invalid json {{{")
        
        with patch.dict('os.environ', {"AUTH_DATA_DIR": str(tmp_data_dir)}):
            from app.services.auth_service import AuthService
            service = AuthService()
            service.data_dir = tmp_data_dir
            service.users_file = users_file
            service._users = {}
            service._load_users()
            
            # Should have empty users after error
            assert service._users == {}
    
    def test_load_invites_handles_error(self, tmp_data_dir):
        """Should handle errors loading invites"""
        invites_file = tmp_data_dir / "invites.json"
        invites_file.write_text("invalid json {{{")
        
        with patch.dict('os.environ', {"AUTH_DATA_DIR": str(tmp_data_dir)}):
            from app.services.auth_service import AuthService
            service = AuthService()
            service.data_dir = tmp_data_dir
            service.invites_file = invites_file
            service._invites = {}
            service._load_invites()
            
            # Should have empty invites after error
            assert service._invites == {}
    
    def test_save_users_handles_error(self, auth_service_instance):
        """Should raise on save error"""
        with patch('builtins.open', side_effect=PermissionError("Read only")):
            with pytest.raises(PermissionError):
                auth_service_instance._save_users()
    
    def test_save_invites_handles_error(self, auth_service_instance):
        """Should raise on save error"""
        with patch('builtins.open', side_effect=PermissionError("Read only")):
            with pytest.raises(PermissionError):
                auth_service_instance._save_invites()


class TestDependencyHelpers:
    """Tests for dependency helper functions"""
    
    async def test_get_current_user_invalid_token(self):
        """Should return None for invalid token"""
        from fastapi.security import HTTPAuthorizationCredentials
        from app.routers.auth import get_current_user
        
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid")
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.verify_token.return_value = None
            
            user = await get_current_user(creds)
            
            assert user is None
    
    async def test_get_current_user_inactive_user(self, mock_owner):
        """Should return None for inactive user"""
        from fastapi.security import HTTPAuthorizationCredentials
        from app.routers.auth import get_current_user
        
        mock_owner.is_active = False
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc)
            )
            mock_service.get_user.return_value = mock_owner
            
            user = await get_current_user(creds)
            
            assert user is None
    
    async def test_get_current_user_user_not_found(self, mock_owner):
        """Should return None if user not found"""
        from fastapi.security import HTTPAuthorizationCredentials
        from app.routers.auth import get_current_user
        
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc)
            )
            mock_service.get_user.return_value = None
            
            user = await get_current_user(creds)
            
            assert user is None

