"""
Edge case and integration tests for additional coverage.
"""
import os
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
        from app.config import settings
        
        with patch.object(settings, 'resend_api_key', ''):
            assert email_service.is_email_configured() is False
    
    def test_is_email_configured_true(self):
        """Should return True when configured"""
        from app.services import email_service
        from app.config import settings
        
        with patch.object(settings, 'resend_api_key', 'test-api-key'):
            assert email_service.is_email_configured() is True


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


class TestInternalEndpoints:
    """Tests for internal service-to-service endpoints"""
    
    def test_get_owner_internal(self, app, client, mock_owner):
        """Should get owner user ID"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.get_owner_user = AsyncMock(return_value=mock_owner)
            
            response = client.get("/api/auth/internal/owner")
            
            assert response.status_code == 200
            assert response.json()["user_id"] == mock_owner.id
            assert response.json()["username"] == mock_owner.username
    
    def test_get_owner_internal_not_found(self, app, client):
        """Should return 404 if no owner"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.get_owner_user = AsyncMock(return_value=None)
            
            response = client.get("/api/auth/internal/owner")
            
            assert response.status_code == 404
    
    def test_get_all_users_internal(self, app, client):
        """Should get all user IDs"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.get_all_user_ids = AsyncMock(return_value=["user-1", "user-2", "user-3"])
            
            response = client.get("/api/auth/internal/users")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3
            assert data[0]["user_id"] == "user-1"
    
    def test_get_user_internal(self, app, client, mock_user):
        """Should get user info by ID"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.get_user = AsyncMock(return_value=mock_user)
            
            response = client.get(f"/api/auth/internal/users/{mock_user.id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == mock_user.id
            assert data["email"] == mock_user.email
    
    def test_get_user_internal_not_found(self, app, client):
        """Should return 404 if user not found"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.get_user = AsyncMock(return_value=None)
            
            response = client.get("/api/auth/internal/users/nonexistent")
            
            assert response.status_code == 404


class TestRegistrationEndpoint:
    """Tests for open registration endpoint"""
    
    def test_register_disabled(self, app, client):
        """Should return 403 when registration is disabled"""
        from app.config import settings
        
        with patch.object(settings, 'allow_open_registration', False):
            with patch('app.routers.auth.auth_service') as mock_service:
                mock_service.register_user = AsyncMock(side_effect=ValueError("Open registration is disabled"))
                
                response = client.post("/api/auth/register", json={
                    "username": "newuser",
                    "first_name": "New",
                    "last_name": "User",
                    "email": "new@test.com",
                    "password": "password123"
                })
                
                assert response.status_code == 403
    
    def test_register_username_taken(self, app, client):
        """Should return 400 if username taken"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.register_user = AsyncMock(side_effect=ValueError("Username already taken"))
            
            response = client.post("/api/auth/register", json={
                "username": "existinguser",
                "first_name": "New",
                "last_name": "User",
                "email": "new@test.com",
                "password": "password123"
            })
            
            assert response.status_code == 400
            assert "Username already taken" in response.json()["detail"]
    
    def test_register_email_taken(self, app, client):
        """Should return 400 if email taken"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.register_user = AsyncMock(side_effect=ValueError("Email already in use"))
            
            response = client.post("/api/auth/register", json={
                "username": "newuser",
                "first_name": "New",
                "last_name": "User",
                "email": "existing@test.com",
                "password": "password123"
            })
            
            assert response.status_code == 400
            assert "Email already in use" in response.json()["detail"]
    
    def test_register_success(self, app, client, mock_db_session):
        """Should register user successfully"""
        from app.models import UserResponse
        
        now = datetime.now(timezone.utc)
        mock_user = MagicMock()
        mock_user.id = "new-user-123"
        mock_user.username = "newuser"
        mock_user.first_name = "New"
        mock_user.last_name = "User"
        mock_user.email = "new@test.com"
        mock_user.role = UserRole.MEMBER
        mock_user.created_at = now
        mock_user.updated_at = now
        
        mock_response = UserResponse(
            id="new-user-123",
            username="newuser",
            first_name="New",
            last_name="User",
            email="new@test.com",
            role=UserRole.MEMBER,
            created_at=now,
            updated_at=now
        )
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.register_user = AsyncMock(return_value=(mock_user, "token123", 3600))
            mock_service._to_response.return_value = mock_response
            
            response = client.post("/api/auth/register", json={
                "username": "newuser",
                "first_name": "New",
                "last_name": "User",
                "email": "new@test.com",
                "password": "password123"
            })
            
            assert response.status_code == 201
            data = response.json()
            assert data["access_token"] == "token123"
    
    def test_register_exception(self, app, client, mock_db_session):
        """Should return 500 on exception"""
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.register_user = AsyncMock(side_effect=Exception("Test error"))
            
            response = client.post("/api/auth/register", json={
                "username": "newuser",
                "first_name": "New",
                "last_name": "User",
                "email": "new@test.com",
                "password": "password123"
            })
            
            assert response.status_code == 500


class TestGetInviteEndpoint:
    """Tests for get_invite endpoint"""
    
    def test_get_invite_success(self, app, client, mock_owner, mock_db_session):
        """Should get invite by ID"""
        from app.models import InviteResponse
        
        async def mock_get_current_user():
            return mock_owner
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        now = datetime.now(timezone.utc)
        mock_invite = MagicMock()
        mock_invite.id = "invite-123"
        mock_invite.email = "test@test.com"
        mock_invite.role = UserRole.MEMBER
        mock_invite.status = InviteStatus.PENDING
        mock_invite.invited_by_username = "owner"
        mock_invite.invited_by_name = "Test Owner"
        mock_invite.created_at = now
        mock_invite.expires_at = now + timedelta(hours=72)
        mock_invite.accepted_at = None
        
        mock_response = InviteResponse(
            id="invite-123",
            email="test@test.com",
            role=UserRole.MEMBER,
            status=InviteStatus.PENDING,
            invited_by="owner",
            invited_by_name="Test Owner",
            created_at=now,
            expires_at=now + timedelta(hours=72)
        )
        
        # Mock the database execute to return our mock invite
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_invite
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service._invite_to_response.return_value = mock_response
            
            response = client.get(
                "/api/auth/invites/invite-123",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "invite-123"
    
    def test_get_invite_not_found(self, app, client, mock_owner, mock_db_session):
        """Should return 404 if invite not found"""
        async def mock_get_current_user():
            return mock_owner
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        # Mock the database execute to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)
        
        response = client.get(
            "/api/auth/invites/nonexistent",
            headers={"Authorization": "Bearer token123"}
        )
        
        assert response.status_code == 404


class TestCreateInviteEndpoint:
    """Tests for create_invite endpoint error handling"""
    
    def test_create_invite_value_error(self, app, client, mock_owner):
        """Should return 400 on value error"""
        async def mock_get_current_user():
            return mock_owner
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.create_invite = AsyncMock(side_effect=ValueError("Invalid email"))
            
            response = client.post(
                "/api/auth/invites",
                headers={"Authorization": "Bearer token123"},
                json={"email": "invalid@test.com"}
            )
            
            assert response.status_code == 400
    
    def test_create_invite_permission_error(self, app, client, mock_owner):
        """Should return 400 on permission error"""
        async def mock_get_current_user():
            return mock_owner
        app.dependency_overrides[get_current_user] = mock_get_current_user
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.create_invite = AsyncMock(side_effect=PermissionError("Not allowed"))
            
            response = client.post(
                "/api/auth/invites",
                headers={"Authorization": "Bearer token123"},
                json={"email": "test@test.com"}
            )
            
            assert response.status_code == 400


class TestAcceptInviteEndpoint:
    """Tests for accept_invite endpoint error handling"""
    
    def test_accept_invite_value_error(self, client):
        """Should return 400 on value error"""
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


class TestVerifyTokenEdgeCases:
    """Tests for verify_token edge cases"""
    
    def test_verify_token_user_inactive(self, client, mock_user):
        """Should return invalid for inactive user"""
        mock_user.is_active = False
        
        with patch('app.routers.auth.auth_service') as mock_service:
            from app.models import TokenPayload
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_user.id,
                username=mock_user.username,
                role=mock_user.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc)
            )
            mock_service.decode_token_payload.return_value = {"service": False}
            mock_service.get_user = AsyncMock(return_value=mock_user)
            
            response = client.post(
                "/api/auth/verify",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 200
            assert response.json()["valid"] is False
    
    def test_verify_token_user_not_found(self, client):
        """Should return invalid if user not found"""
        with patch('app.routers.auth.auth_service') as mock_service:
            from app.models import TokenPayload
            mock_service.verify_token.return_value = TokenPayload(
                sub="nonexistent",
                username="test",
                role=UserRole.MEMBER,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc)
            )
            mock_service.decode_token_payload.return_value = {"service": False}
            mock_service.get_user = AsyncMock(return_value=None)
            
            response = client.post(
                "/api/auth/verify",
                headers={"Authorization": "Bearer token123"}
            )
            
            assert response.status_code == 200
            assert response.json()["valid"] is False


class TestGetCurrentUserEdgeCases:
    """Tests for get_current_user edge cases"""
    
    async def test_get_current_user_invalid_token(self):
        """Should return None for invalid token"""
        from fastapi.security import HTTPAuthorizationCredentials
        
        mock_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid")
        mock_db = AsyncMock()
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.verify_token.return_value = None
            
            result = await get_current_user(mock_credentials, mock_db)
            
            assert result is None
    
    async def test_get_current_user_user_not_found(self):
        """Should return None if user not found"""
        from fastapi.security import HTTPAuthorizationCredentials
        from app.models import TokenPayload
        
        mock_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token123")
        mock_db = AsyncMock()
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.verify_token.return_value = TokenPayload(
                sub="nonexistent",
                username="test",
                role=UserRole.MEMBER,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc)
            )
            mock_service.get_user = AsyncMock(return_value=None)
            
            result = await get_current_user(mock_credentials, mock_db)
            
            assert result is None
    
    async def test_get_current_user_inactive_user(self):
        """Should return None for inactive user"""
        from fastapi.security import HTTPAuthorizationCredentials
        from app.models import TokenPayload
        
        mock_credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token123")
        mock_db = AsyncMock()
        
        mock_user = MagicMock()
        mock_user.is_active = False
        
        with patch('app.routers.auth.auth_service') as mock_service:
            mock_service.verify_token.return_value = TokenPayload(
                sub="user-123",
                username="test",
                role=UserRole.MEMBER,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc)
            )
            mock_service.get_user = AsyncMock(return_value=mock_user)
            
            result = await get_current_user(mock_credentials, mock_db)
            
            assert result is None
