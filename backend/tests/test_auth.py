"""
Unit tests for auth dependencies.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.dependencies.auth import (
    AuthenticatedUser,
    UserRole,
    verify_token_with_auth_service,
    get_current_user,
    require_auth,
    require_write_access,
    require_owner,
)


class TestUserRole:
    """Tests for the UserRole enum"""
    
    def test_role_values(self):
        """Verify role enum values"""
        assert UserRole.OWNER.value == "owner"
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.MEMBER.value == "member"


class TestAuthenticatedUser:
    """Tests for the AuthenticatedUser model"""
    
    def test_owner_is_owner(self, sample_user_data):
        """Owner role should return True for is_owner"""
        user = AuthenticatedUser(**sample_user_data)
        assert user.is_owner is True
    
    def test_member_is_not_owner(self, sample_readonly_user):
        """Member role should return False for is_owner"""
        user = AuthenticatedUser(**sample_readonly_user)
        assert user.is_owner is False
    
    def test_admin_is_not_owner(self, sample_readwrite_user):
        """Admin role should return False for is_owner"""
        user = AuthenticatedUser(**sample_readwrite_user)
        assert user.is_owner is False
    
    def test_owner_can_write(self, sample_user_data):
        """Owner role should have write access"""
        user = AuthenticatedUser(**sample_user_data)
        assert user.can_write is True
    
    def test_admin_can_write(self, sample_readwrite_user):
        """Admin role should have write access"""
        user = AuthenticatedUser(**sample_readwrite_user)
        assert user.can_write is True
    
    def test_member_cannot_write(self, sample_readonly_user):
        """Member role should not have write access"""
        user = AuthenticatedUser(**sample_readonly_user)
        assert user.can_write is False


class TestVerifyTokenWithAuthService:
    """Tests for token verification with auth service"""
    
    @pytest.fixture
    def mock_httpx(self):
        """Mock httpx.AsyncClient for auth service calls"""
        with patch('app.dependencies.auth.httpx.AsyncClient') as mock:
            yield mock
    
    async def test_valid_token_returns_user(self, mock_httpx, mock_auth_response):
        """Valid token should return AuthenticatedUser"""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_auth_response
        mock_client.post.return_value = mock_response
        
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        user = await verify_token_with_auth_service("valid-token")
        
        assert user is not None
        assert user.user_id == "user-123"
        assert user.username == "testuser"
        assert user.role == UserRole.OWNER
    
    async def test_invalid_token_returns_none(self, mock_httpx):
        """Invalid token should return None"""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"valid": False}
        mock_client.post.return_value = mock_response
        
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        user = await verify_token_with_auth_service("invalid-token")
        
        assert user is None
    
    async def test_auth_service_401_returns_none(self, mock_httpx):
        """401 from auth service should return None"""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_client.post.return_value = mock_response
        
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        user = await verify_token_with_auth_service("bad-token")
        
        assert user is None
    
    async def test_auth_service_connect_error_raises_503(self, mock_httpx):
        """Connection error to auth service should raise 503"""
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        with pytest.raises(HTTPException) as exc_info:
            await verify_token_with_auth_service("token")
        
        assert exc_info.value.status_code == 503
        assert "Auth service unavailable" in exc_info.value.detail
    
    async def test_auth_service_timeout_raises_504(self, mock_httpx):
        """Timeout from auth service should raise 504"""
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("Timeout")
        
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        with pytest.raises(HTTPException) as exc_info:
            await verify_token_with_auth_service("token")
        
        assert exc_info.value.status_code == 504
        assert "Auth service timeout" in exc_info.value.detail
    
    async def test_unexpected_error_returns_none(self, mock_httpx):
        """Unexpected error should return None (not crash)"""
        mock_client = AsyncMock()
        mock_client.post.side_effect = ValueError("Unexpected error")
        
        mock_httpx.return_value.__aenter__.return_value = mock_client
        
        user = await verify_token_with_auth_service("token")
        
        assert user is None


class TestGetCurrentUser:
    """Tests for get_current_user dependency"""
    
    @pytest.fixture
    def mock_verify(self):
        """Mock verify_token_with_auth_service"""
        with patch('app.dependencies.auth.verify_token_with_auth_service') as mock:
            yield mock
    
    async def test_with_authorization_header(self, mock_verify, sample_user_data):
        """Should extract token from Authorization header"""
        mock_verify.return_value = AuthenticatedUser(**sample_user_data)
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="header-token"
        )
        
        user = await get_current_user(credentials=credentials, token=None)
        
        assert user is not None
        mock_verify.assert_called_once_with("header-token")
    
    async def test_with_query_token(self, mock_verify, sample_user_data):
        """Should extract token from query parameter when no header"""
        mock_verify.return_value = AuthenticatedUser(**sample_user_data)
        
        user = await get_current_user(credentials=None, token="query-token")
        
        assert user is not None
        mock_verify.assert_called_once_with("query-token")
    
    async def test_header_takes_precedence_over_query(self, mock_verify, sample_user_data):
        """Authorization header should be preferred over query param"""
        mock_verify.return_value = AuthenticatedUser(**sample_user_data)
        
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="header-token"
        )
        
        user = await get_current_user(credentials=credentials, token="query-token")
        
        mock_verify.assert_called_once_with("header-token")
    
    async def test_no_token_returns_none(self, mock_verify):
        """No token provided should return None"""
        user = await get_current_user(credentials=None, token=None)
        
        assert user is None
        mock_verify.assert_not_called()


class TestRequireAuth:
    """Tests for require_auth dependency"""
    
    async def test_authenticated_user_passes(self, sample_user_data):
        """Authenticated user should be returned"""
        user = AuthenticatedUser(**sample_user_data)
        
        result = await require_auth(user=user)
        
        assert result == user
    
    async def test_no_user_raises_401(self):
        """No user should raise 401 Unauthorized"""
        with pytest.raises(HTTPException) as exc_info:
            await require_auth(user=None)
        
        assert exc_info.value.status_code == 401
        assert "Not authenticated" in exc_info.value.detail
        assert exc_info.value.headers["WWW-Authenticate"] == "Bearer"


class TestRequireWriteAccess:
    """Tests for require_write_access dependency"""
    
    async def test_owner_has_write_access(self, sample_user_data):
        """Owner should have write access"""
        user = AuthenticatedUser(**sample_user_data)
        
        result = await require_write_access(user=user)
        
        assert result == user
    
    async def test_admin_has_write_access(self, sample_readwrite_user):
        """Admin user should have write access"""
        user = AuthenticatedUser(**sample_readwrite_user)
        
        result = await require_write_access(user=user)
        
        assert result == user
    
    async def test_member_denied_write_access(self, sample_readonly_user):
        """Member user should be denied write access"""
        user = AuthenticatedUser(**sample_readonly_user)
        
        with pytest.raises(HTTPException) as exc_info:
            await require_write_access(user=user)
        
        assert exc_info.value.status_code == 403
        assert "Write access required" in exc_info.value.detail


class TestRequireOwner:
    """Tests for require_owner dependency"""
    
    async def test_owner_passes(self, sample_user_data):
        """Owner should pass owner check"""
        user = AuthenticatedUser(**sample_user_data)
        
        result = await require_owner(user=user)
        
        assert result == user
    
    async def test_admin_denied_owner_access(self, sample_readwrite_user):
        """Admin user should be denied owner access"""
        user = AuthenticatedUser(**sample_readwrite_user)
        
        with pytest.raises(HTTPException) as exc_info:
            await require_owner(user=user)
        
        assert exc_info.value.status_code == 403
        assert "Owner access required" in exc_info.value.detail
    
    async def test_member_denied_owner_access(self, sample_readonly_user):
        """Member user should be denied owner access"""
        user = AuthenticatedUser(**sample_readonly_user)
        
        with pytest.raises(HTTPException) as exc_info:
            await require_owner(user=user)
        
        assert exc_info.value.status_code == 403
        assert "Owner access required" in exc_info.value.detail

