"""
Edge case and integration tests for additional coverage.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.models import (
    UserRole,
    UserResponse,
    UserUpdate,
    InviteStatus,
    TokenPayload,
)
from app.routers.auth import router, get_current_user, require_auth
from app.database import get_db
from app.db_models import User


def create_mock_user(
    id="owner-123",
    username="owner",
    first_name="Test",
    last_name="Owner",
    email="owner@test.com",
    role=UserRole.OWNER,
    is_active=True
):
    """Create a mock User database model object"""
    user = MagicMock(spec=User)
    user.id = id
    user.username = username
    user.first_name = first_name
    user.last_name = last_name
    user.email = email
    user.role = role
    user.is_active = is_active
    user.hashed_password = "hash"
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    user.last_login_at = None
    return user


@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    return AsyncMock()


@pytest.fixture
def app(mock_db_session):
    """Create test app with auth router and mocked DB"""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/auth")
    
    # Override the database dependency
    async def mock_get_db():
        yield mock_db_session
    
    test_app.dependency_overrides[get_db] = mock_get_db
    
    return test_app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_owner():
    """Create mock owner user (DB model)"""
    return create_mock_user(
        id="owner-123",
        username="owner",
        first_name="Test",
        last_name="Owner",
        email="owner@test.com",
        role=UserRole.OWNER
    )


@pytest.fixture
def mock_user():
    """Create mock regular user (DB model)"""
    return create_mock_user(
        id="user-456",
        username="testuser",
        first_name="Test",
        last_name="User",
        email="user@test.com",
        role=UserRole.MEMBER
    )


class TestRouterErrorHandling:
    """Tests for router error handling paths"""
    
    def test_create_user_value_error(self, app, client, mock_owner):
        """Should return 400 on ValueError"""
        async def mock_get_current_user():
            return mock_owner
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        with patch('app.routers.auth.auth_service') as mock_service:
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
    
    def test_create_user_permission_error(self, app, client, mock_owner):
        """Should return 400 on PermissionError"""
        async def mock_get_current_user():
            return mock_owner
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        with patch('app.routers.auth.auth_service') as mock_service:
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
    
    def test_get_user_not_found(self, app, client, mock_owner):
        """Should return 404 when user not found"""
        async def mock_get_current_user():
            return mock_owner
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.get_user = AsyncMock(return_value=None)
            
            response = client.get(
                "/api/auth/users/nonexistent",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 404
    
    def test_update_user_permission_error(self, app, client, mock_owner):
        """Should return 403 on PermissionError"""
        async def mock_get_current_user():
            return mock_owner
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.update_user = AsyncMock(side_effect=PermissionError("Not allowed"))
            
            response = client.patch(
                f"/api/auth/users/{mock_owner.id}",
                headers={"Authorization": "Bearer token123"},
                json={"first_name": "Updated"}
            )
            
            assert response.status_code == 403
    
    def test_update_user_value_error(self, app, client, mock_owner):
        """Should return 400 on ValueError"""
        async def mock_get_current_user():
            return mock_owner
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.update_user = AsyncMock(side_effect=ValueError("Invalid"))
            
            response = client.patch(
                f"/api/auth/users/{mock_owner.id}",
                headers={"Authorization": "Bearer token123"},
                json={"first_name": "Updated"}
            )
            
            assert response.status_code == 400
    
    def test_delete_user_value_error(self, app, client, mock_owner, mock_user):
        """Should return 400 on ValueError"""
        async def mock_get_current_user():
            return mock_owner
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.delete_user = AsyncMock(side_effect=ValueError("Cannot delete"))
            
            response = client.delete(
                f"/api/auth/users/{mock_user.id}",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 400
    
    def test_delete_user_permission_error(self, app, client, mock_owner, mock_user):
        """Should return 403 on PermissionError"""
        async def mock_get_current_user():
            return mock_owner
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.delete_user = AsyncMock(side_effect=PermissionError("Not owner"))
            
            response = client.delete(
                f"/api/auth/users/{mock_user.id}",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 403


class TestDependencyHelpers:
    """Tests for dependency helper functions"""
    
    async def test_get_current_user_no_credentials(self):
        """Should return None without credentials"""
        result = await get_current_user(None, MagicMock())
        assert result is None
    
    async def test_require_auth_raises_without_user(self):
        """Should raise 401 without user"""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await require_auth(None)
        
        assert exc_info.value.status_code == 401


class TestEmailService:
    """Tests for email service functions"""
    
    def test_is_email_configured_false(self):
        """Should return False when not configured"""
        from app.services import email_service
        
        original = email_service.RESEND_API_KEY
        email_service.RESEND_API_KEY = ""
        
        try:
            assert email_service.is_email_configured() is False
        finally:
            email_service.RESEND_API_KEY = original
    
    def test_is_email_configured_true(self):
        """Should return True when configured"""
        from app.services import email_service
        
        original = email_service.RESEND_API_KEY
        email_service.RESEND_API_KEY = "test-api-key"
        
        try:
            assert email_service.is_email_configured() is True
        finally:
            email_service.RESEND_API_KEY = original


class TestMoreRouterEndpoints:
    """Additional router endpoint tests"""
    
    def test_change_password_success(self, app, client, mock_owner):
        """Should change password successfully"""
        async def mock_get_current_user():
            return mock_owner
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.change_password = AsyncMock(return_value=True)
            
            response = client.post(
                "/api/auth/me/change-password",
                headers={"Authorization": "Bearer token123"},
                json={
                    "current_password": "oldpassword123",
                    "new_password": "newpassword123"
                }
            )
            
            assert response.status_code == 200
    
    def test_change_password_error(self, app, client, mock_owner):
        """Should return 400 on password change error"""
        async def mock_get_current_user():
            return mock_owner
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.change_password = AsyncMock(side_effect=ValueError("Incorrect password"))
            
            response = client.post(
                "/api/auth/me/change-password",
                headers={"Authorization": "Bearer token123"},
                json={
                    "current_password": "wrongpassword",
                    "new_password": "newpassword123"
                }
            )
            
            assert response.status_code == 400
    
    def test_list_invites_success(self, app, client, mock_owner):
        """Should list invites"""
        async def mock_get_current_user():
            return mock_owner
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.list_invites = AsyncMock(return_value=[])
            
            response = client.get(
                "/api/auth/invites",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 200
    
    def test_list_invites_permission_error(self, app, client, mock_owner):
        """Should return 403 on permission error"""
        async def mock_get_current_user():
            return mock_owner
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.list_invites = AsyncMock(side_effect=PermissionError("Not allowed"))
            
            response = client.get(
                "/api/auth/invites",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 403
    
    def test_get_current_profile_success(self, app, client, mock_owner):
        """Should get current user profile"""
        from app.models import UserResponse
        
        async def mock_get_current_user():
            return mock_owner
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        mock_response = UserResponse(
            id=mock_owner.id,
            username=mock_owner.username,
            first_name=mock_owner.first_name,
            last_name=mock_owner.last_name,
            email=mock_owner.email,
            role=mock_owner.role,
            created_at=mock_owner.created_at,
            updated_at=mock_owner.updated_at
        )
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service._to_response.return_value = mock_response
            mock_service.get_permissions.return_value = ["read:own_networks"]
            
            response = client.get(
                "/api/auth/me",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 200
    
    def test_revoke_invite_success(self, app, client, mock_owner):
        """Should revoke invite"""
        from app.models import InviteResponse, InviteStatus
        
        async def mock_get_current_user():
            return mock_owner
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        mock_invite_response = InviteResponse(
            id="invite-123",
            email="test@test.com",
            role=UserRole.MEMBER,
            status=InviteStatus.REVOKED,
            invited_by="owner",
            invited_by_name="Test Owner",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=72)
        )
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.revoke_invite = AsyncMock(return_value=mock_invite_response)
            
            response = client.delete(
                "/api/auth/invites/invite-123",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 200
    
    def test_revoke_invite_value_error(self, app, client, mock_owner):
        """Should return 400 on value error"""
        async def mock_get_current_user():
            return mock_owner
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.revoke_invite = AsyncMock(side_effect=ValueError("Not found"))
            
            response = client.delete(
                "/api/auth/invites/invite-123",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 400
    
    def test_revoke_invite_permission_error(self, app, client, mock_owner):
        """Should return 403 on permission error"""
        async def mock_get_current_user():
            return mock_owner
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.revoke_invite = AsyncMock(side_effect=PermissionError("Not allowed"))
            
            response = client.delete(
                "/api/auth/invites/invite-123",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 403
    
    def test_resend_invite_success(self, app, client, mock_owner):
        """Should resend invite"""
        from app.models import InviteResponse, InviteStatus
        
        async def mock_get_current_user():
            return mock_owner
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        mock_invite_response = InviteResponse(
            id="invite-123",
            email="test@test.com",
            role=UserRole.MEMBER,
            status=InviteStatus.PENDING,
            invited_by="owner",
            invited_by_name="Test Owner",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=72)
        )
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.resend_invite = AsyncMock(return_value=(mock_invite_response, "new-token"))
            
            response = client.post(
                "/api/auth/invites/invite-123/resend",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 200
    
    def test_resend_invite_value_error(self, app, client, mock_owner):
        """Should return 400 on value error"""
        async def mock_get_current_user():
            return mock_owner
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.resend_invite = AsyncMock(side_effect=ValueError("Not found"))
            
            response = client.post(
                "/api/auth/invites/invite-123/resend",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 400
    
    def test_resend_invite_permission_error(self, app, client, mock_owner):
        """Should return 403 on permission error"""
        async def mock_get_current_user():
            return mock_owner
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.resend_invite = AsyncMock(side_effect=PermissionError("Not allowed"))
            
            response = client.post(
                "/api/auth/invites/invite-123/resend",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 403
    
    def test_update_profile_success(self, app, client, mock_owner):
        """Should update profile"""
        from app.models import UserResponse
        
        async def mock_get_current_user():
            return mock_owner
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        mock_response = UserResponse(
            id=mock_owner.id,
            username=mock_owner.username,
            first_name="Updated",
            last_name=mock_owner.last_name,
            email=mock_owner.email,
            role=mock_owner.role,
            created_at=mock_owner.created_at,
            updated_at=mock_owner.updated_at
        )
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.update_user = AsyncMock(return_value=mock_response)
            
            response = client.patch(
                "/api/auth/me",
                headers={"Authorization": "Bearer token123"},
                json={"first_name": "Updated"}
            )
            
            assert response.status_code == 200
    
    def test_update_profile_value_error(self, app, client, mock_owner):
        """Should return 400 on value error"""
        async def mock_get_current_user():
            return mock_owner
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.update_user = AsyncMock(side_effect=ValueError("Invalid update"))
            
            response = client.patch(
                "/api/auth/me",
                headers={"Authorization": "Bearer token123"},
                json={"first_name": "Updated"}
            )
            
            assert response.status_code == 400
