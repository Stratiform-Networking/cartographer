"""
Unit tests for auth dependencies.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.dependencies.auth import (
    AuthenticatedUser,
    UserRole,
    get_current_user,
    require_auth,
    require_owner,
    require_write_access,
    verify_token_with_auth_service,
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
    def mock_http_pool(self):
        """Mock http_pool.request for auth service calls"""
        with patch("app.services.auth_service.http_pool.request") as mock:
            yield mock

    @pytest.fixture
    def mock_cache_service(self):
        """Mock cache_service for token caching"""
        # cache_service is imported dynamically inside the function
        with patch("app.services.cache_service.cache_service") as mock:
            mock.get = AsyncMock(return_value=None)  # Cache miss
            mock.set = AsyncMock(return_value=True)
            yield mock

    async def test_valid_token_returns_user(self, mock_http_pool, mock_cache_service, mock_auth_response):
        """Valid token should return AuthenticatedUser"""
        import json

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.body = json.dumps(mock_auth_response).encode()
        mock_http_pool.return_value = mock_response

        user = await verify_token_with_auth_service("valid-token")

        assert user is not None
        assert user.user_id == "user-123"
        assert user.username == "testuser"
        assert user.role == UserRole.OWNER

    async def test_invalid_token_returns_none(self, mock_http_pool, mock_cache_service):
        """Invalid token should return None"""
        import json

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.body = json.dumps({"valid": False}).encode()
        mock_http_pool.return_value = mock_response

        user = await verify_token_with_auth_service("invalid-token")

        assert user is None

    async def test_auth_service_401_returns_none(self, mock_http_pool, mock_cache_service):
        """401 from auth service should return None"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_http_pool.return_value = mock_response

        user = await verify_token_with_auth_service("bad-token")

        assert user is None

    async def test_auth_service_503_raises_exception(self, mock_http_pool, mock_cache_service):
        """503 from http_pool should be re-raised"""
        mock_http_pool.side_effect = HTTPException(status_code=503, detail="Auth service unavailable")

        with pytest.raises(HTTPException) as exc_info:
            await verify_token_with_auth_service("token")

        assert exc_info.value.status_code == 503

    async def test_unexpected_error_returns_none(self, mock_http_pool, mock_cache_service):
        """Unexpected error should return None (not crash)"""
        mock_http_pool.side_effect = ValueError("Unexpected error")

        user = await verify_token_with_auth_service("token")

        assert user is None

    async def test_cached_token_returns_cached_result(self, mock_http_pool, mock_cache_service):
        """Cached token verification should return cached result without calling http_pool"""
        cached_user = {"user_id": "cached-123", "username": "cacheduser", "role": "owner"}
        mock_cache_service.get = AsyncMock(return_value=cached_user)

        user = await verify_token_with_auth_service("cached-token")

        # The wrapper converts to AuthenticatedUser
        assert user.user_id == "cached-123"
        assert user.username == "cacheduser"
        assert user.role == UserRole.OWNER
        mock_http_pool.assert_not_called()  # Should not make HTTP call


class TestVerifyServiceToken:
    """Tests for service token verification"""

    def test_valid_service_token(self):
        """Valid service token should return AuthenticatedUser"""
        import jwt

        from app.dependencies.auth import settings, verify_service_token

        # Create a valid service token
        payload = {
            "service": True,
            "sub": "metrics-service",
            "username": "metrics",
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        user = verify_service_token(token)

        assert user is not None
        assert user.user_id == "metrics-service"
        assert user.username == "metrics"
        assert user.role == UserRole.OWNER

    def test_non_service_token_returns_none(self):
        """Token without service flag should return None"""
        import jwt

        from app.dependencies.auth import settings, verify_service_token

        # Create a non-service token
        payload = {
            "sub": "user-123",
            "username": "testuser",
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        user = verify_service_token(token)

        assert user is None

    def test_expired_service_token_returns_none(self):
        """Expired service token should return None"""
        import time

        import jwt

        from app.dependencies.auth import settings, verify_service_token

        # Create an expired token
        payload = {
            "service": True,
            "sub": "service",
            "exp": int(time.time()) - 3600,  # Expired 1 hour ago
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        user = verify_service_token(token)

        assert user is None

    def test_invalid_service_token_returns_none(self):
        """Invalid service token should return None"""
        from app.dependencies.auth import verify_service_token

        user = verify_service_token("invalid-token")

        assert user is None

    def test_service_token_with_generic_exception(self):
        """Generic exception during verification should return None"""
        from app.dependencies.auth import verify_service_token

        with patch(
            "app.services.auth_service.jwt.decode", side_effect=Exception("Unexpected error")
        ):
            user = verify_service_token("some-token")

            assert user is None


class TestGetCurrentUser:
    """Tests for get_current_user dependency"""

    @pytest.fixture
    def mock_verify(self):
        """Mock verify_token_with_auth_service"""
        with patch("app.dependencies.auth.verify_token_with_auth_service") as mock:
            yield mock

    async def test_service_token_takes_priority(self):
        """Service token should be validated first"""
        import jwt

        from app.dependencies.auth import get_current_user, settings

        # Create a valid service token
        payload = {
            "service": True,
            "sub": "metrics-service",
            "username": "metrics",
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        user = await get_current_user(credentials=credentials, token=None)

        # Should authenticate as service without calling auth service
        assert user is not None
        assert user.user_id == "metrics-service"
        assert user.role == UserRole.OWNER

    async def test_with_authorization_header(self, mock_verify, sample_user_data):
        """Should extract token from Authorization header"""
        mock_verify.return_value = AuthenticatedUser(**sample_user_data)

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="header-token")

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

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="header-token")

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
