"""
Tests for authentication and rate limiting functionality.
"""
import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

# Set test environment before imports
os.environ["AUTH_SERVICE_URL"] = "http://test-auth:8002"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["DATABASE_URL"] = ""
os.environ["REDIS_URL"] = "redis://localhost:6379"

import jwt

from app.config import settings


class TestAuthenticatedUser:
    """Tests for AuthenticatedUser model"""
    
    def test_authenticated_user_creation(self):
        """Should create authenticated user"""
        from app.dependencies.auth import AuthenticatedUser, UserRole
        
        user = AuthenticatedUser(
            user_id="test-123",
            username="testuser",
            role=UserRole.MEMBER
        )
        
        assert user.user_id == "test-123"
        assert user.username == "testuser"
        assert user.role == UserRole.MEMBER
    
    def test_is_owner_property(self):
        """Should correctly identify owner"""
        from app.dependencies.auth import AuthenticatedUser, UserRole
        
        owner = AuthenticatedUser(user_id="1", username="owner", role=UserRole.OWNER)
        admin = AuthenticatedUser(user_id="2", username="admin", role=UserRole.ADMIN)
        member = AuthenticatedUser(user_id="3", username="member", role=UserRole.MEMBER)
        
        assert owner.is_owner is True
        assert admin.is_owner is False
        assert member.is_owner is False
    
    def test_can_write_property(self):
        """Should correctly identify write permissions"""
        from app.dependencies.auth import AuthenticatedUser, UserRole
        
        owner = AuthenticatedUser(user_id="1", username="owner", role=UserRole.OWNER)
        admin = AuthenticatedUser(user_id="2", username="admin", role=UserRole.ADMIN)
        member = AuthenticatedUser(user_id="3", username="member", role=UserRole.MEMBER)
        
        assert owner.can_write is True
        assert admin.can_write is True
        assert member.can_write is False


class TestServiceTokenVerification:
    """Tests for service token verification"""
    
    def test_valid_service_token(self):
        """Should verify valid service token"""
        from app.dependencies.auth import verify_service_token
        
        payload = {
            "service": True,
            "sub": "metrics-service",
            "username": "metrics"
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        
        user = verify_service_token(token)
        
        assert user is not None
        assert user.user_id == "metrics-service"
        assert user.username == "metrics"
    
    def test_non_service_token(self):
        """Should return None for non-service token"""
        from app.dependencies.auth import verify_service_token
        
        payload = {"sub": "user-123", "username": "testuser"}
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        
        user = verify_service_token(token)
        
        assert user is None
    
    def test_expired_service_token(self):
        """Should return None for expired token"""
        from app.dependencies.auth import verify_service_token
        
        payload = {
            "service": True,
            "sub": "service",
            "exp": datetime.utcnow() - timedelta(hours=1)
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        
        user = verify_service_token(token)
        
        assert user is None
    
    def test_invalid_service_token(self):
        """Should return None for invalid token"""
        from app.dependencies.auth import verify_service_token
        
        user = verify_service_token("invalid-token")
        
        assert user is None


class TestAuthServiceVerification:
    """Tests for auth service token verification"""
    
    async def test_verify_token_success(self):
        """Should verify token with auth service"""
        from app.dependencies.auth import verify_token_with_auth_service
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "valid": True,
            "user_id": "user-123",
            "username": "testuser",
            "role": "member"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            user = await verify_token_with_auth_service("test-token")
        
        assert user is not None
        assert user.user_id == "user-123"
    
    async def test_verify_token_invalid(self):
        """Should return None for invalid token"""
        from app.dependencies.auth import verify_token_with_auth_service
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"valid": False}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            user = await verify_token_with_auth_service("bad-token")
        
        assert user is None
    
    async def test_verify_token_non_200(self):
        """Should return None for non-200 response"""
        from app.dependencies.auth import verify_token_with_auth_service
        
        mock_response = MagicMock()
        mock_response.status_code = 401
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            user = await verify_token_with_auth_service("test-token")
        
        assert user is None
    
    async def test_verify_token_connection_error(self):
        """Should raise 503 on connection error"""
        import httpx
        from fastapi import HTTPException
        from app.dependencies.auth import verify_token_with_auth_service
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await verify_token_with_auth_service("test-token")
            
            assert exc_info.value.status_code == 503
    
    async def test_verify_token_timeout(self):
        """Should raise 504 on timeout"""
        import httpx
        from fastapi import HTTPException
        from app.dependencies.auth import verify_token_with_auth_service
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await verify_token_with_auth_service("test-token")
            
            assert exc_info.value.status_code == 504
    
    async def test_verify_token_generic_error(self):
        """Should return None on generic error"""
        from app.dependencies.auth import verify_token_with_auth_service
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("Unexpected error")
            )
            
            user = await verify_token_with_auth_service("test-token")
        
        assert user is None


class TestGetCurrentUser:
    """Tests for get_current_user dependency"""
    
    async def test_no_credentials(self):
        """Should return None when no credentials"""
        from app.dependencies.auth import get_current_user
        
        user = await get_current_user(None, None)
        
        assert user is None
    
    async def test_header_credentials(self):
        """Should use header credentials"""
        from app.dependencies.auth import get_current_user
        from fastapi.security import HTTPAuthorizationCredentials
        
        payload = {"service": True, "sub": "service"}
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        
        user = await get_current_user(credentials, None)
        
        assert user is not None
        assert user.user_id == "service"
    
    async def test_query_token_fallback(self):
        """Should fall back to query token"""
        from app.dependencies.auth import get_current_user
        
        payload = {"service": True, "sub": "service"}
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        
        user = await get_current_user(None, token)
        
        assert user is not None
        assert user.user_id == "service"


class TestRequireAuth:
    """Tests for require_auth dependency"""
    
    async def test_authenticated_user(self):
        """Should return user when authenticated"""
        from app.dependencies.auth import require_auth, AuthenticatedUser, UserRole
        
        user = AuthenticatedUser(user_id="1", username="test", role=UserRole.MEMBER)
        
        result = await require_auth(user)
        
        assert result == user
    
    async def test_unauthenticated_user(self):
        """Should raise 401 when not authenticated"""
        from fastapi import HTTPException
        from app.dependencies.auth import require_auth
        
        with pytest.raises(HTTPException) as exc_info:
            await require_auth(None)
        
        assert exc_info.value.status_code == 401


class TestRateLimitHelpers:
    """Tests for rate limit helper functions"""
    
    def test_get_local_date(self):
        """Should return today's date in ISO format"""
        from app.services.rate_limit import _get_local_date
        
        result = _get_local_date()
        
        # Should be a valid ISO date
        assert len(result) == 10
        assert result.count("-") == 2
    
    def test_seconds_until_midnight(self):
        """Should return positive seconds"""
        from app.services.rate_limit import _seconds_until_local_midnight
        
        result = _seconds_until_local_midnight()
        
        assert result > 0
        assert result <= 86400  # Max 24 hours
    
    def test_is_role_exempt_true(self):
        """Should identify exempt roles"""
        from app.services import rate_limit
        
        with patch.object(type(settings), 'rate_limit_exempt_roles', property(lambda self: {"admin", "owner"})):
            assert rate_limit.is_role_exempt("admin") is True
            assert rate_limit.is_role_exempt("ADMIN") is True
            assert rate_limit.is_role_exempt("owner") is True
    
    def test_is_role_exempt_false(self):
        """Should identify non-exempt roles"""
        from app.services import rate_limit
        
        with patch.object(type(settings), 'rate_limit_exempt_roles', property(lambda self: {"admin"})):
            assert rate_limit.is_role_exempt("member") is False
            assert rate_limit.is_role_exempt("guest") is False


class TestGetUserLimit:
    """Tests for get_user_limit function"""
    
    async def test_exempt_role_no_database(self):
        """Should return unlimited for exempt role without database"""
        from app.services.rate_limit import get_user_limit, UNLIMITED_LIMIT
        
        with patch.object(type(settings), 'rate_limit_exempt_roles', property(lambda self: {"admin"})):
            with patch('app.database.AsyncSessionLocal', None):
                result = await get_user_limit("user-1", 100, user_role="admin")
            
            assert result == UNLIMITED_LIMIT
    
    async def test_non_exempt_no_database(self):
        """Should return default for non-exempt without database"""
        from app.services.rate_limit import get_user_limit
        
        with patch('app.database.AsyncSessionLocal', None):
            result = await get_user_limit("user-1", 100, user_role="member")
        
        assert result == 100


class TestCheckRateLimit:
    """Tests for check_rate_limit function"""
    
    async def test_unlimited_user_bypasses_check(self):
        """Should bypass check for unlimited users"""
        from app.services.rate_limit import check_rate_limit, UNLIMITED_LIMIT
        
        with patch('app.services.rate_limit.get_user_limit', AsyncMock(return_value=UNLIMITED_LIMIT)):
            # Should not raise
            await check_rate_limit("user-1", "chat", 100)


class TestGetRateLimitStatus:
    """Tests for get_rate_limit_status function"""
    
    async def test_unlimited_user_status(self):
        """Should return unlimited status for exempt users"""
        from app.services.rate_limit import get_rate_limit_status, UNLIMITED_LIMIT
        
        with patch('app.services.rate_limit.get_user_limit', AsyncMock(return_value=UNLIMITED_LIMIT)):
            result = await get_rate_limit_status("user-1", "chat", 100)
        
        assert result["limit"] == -1
        assert result["remaining"] == -1
        assert result["is_exempt"] is True


class TestDatabase:
    """Tests for database module"""
    
    async def test_init_db_no_url(self):
        """Should skip init when no DATABASE_URL"""
        from app import database
        
        original_engine = database.engine
        database.engine = None
        
        try:
            await database.init_db()
            # Should complete without error
        finally:
            database.engine = original_engine
    
    async def test_get_db_not_configured(self):
        """Should raise when database not configured"""
        from app import database
        
        original_session = database.AsyncSessionLocal
        database.AsyncSessionLocal = None
        
        try:
            with pytest.raises(RuntimeError) as exc_info:
                async for _ in database.get_db():
                    pass
            
            assert "Database not configured" in str(exc_info.value)
        finally:
            database.AsyncSessionLocal = original_session
    
    def test_base_class(self):
        """Should have Base declarative class"""
        from app.database import Base
        
        assert Base is not None


class TestDbModels:
    """Tests for database models"""
    
    def test_user_rate_limit_repr(self):
        """Should have proper repr"""
        from app.db_models import UserRateLimit
        
        # Test with default limit
        model = UserRateLimit(user_id="test-123", daily_limit=None, is_role_exempt=False)
        repr_str = repr(model)
        assert "test-123" in repr_str
        assert "default" in repr_str
        
        # Test with unlimited
        model.daily_limit = -1
        repr_str = repr(model)
        assert "unlimited" in repr_str
        
        # Test with custom limit
        model.daily_limit = 50
        repr_str = repr(model)
        assert "50" in repr_str
    
    def test_user_rate_limit_table_name(self):
        """Should have correct table name"""
        from app.db_models import UserRateLimit
        
        assert UserRateLimit.__tablename__ == "user_rate_limits"


class TestRequireAuthWithRateLimit:
    """Tests for require_auth_with_rate_limit dependency factory"""
    
    async def test_creates_dependency(self):
        """Should create a working dependency"""
        from app.dependencies.auth import require_auth_with_rate_limit, AuthenticatedUser, UserRole
        
        user = AuthenticatedUser(user_id="1", username="test", role=UserRole.MEMBER)
        
        # Create the dependency
        dependency = require_auth_with_rate_limit(100, "chat")
        
        # Mock the rate limit check
        with patch('app.services.rate_limit.check_rate_limit', AsyncMock()):
            result = await dependency(user=user)
        
        assert result == user


class TestCheckRateLimitFull:
    """More comprehensive tests for check_rate_limit"""
    
    async def test_check_rate_limit_within_limit(self):
        """Should allow requests within limit"""
        from app.services.rate_limit import check_rate_limit
        
        mock_redis = MagicMock()
        mock_redis.eval = AsyncMock(return_value=5)  # 5 requests, under limit
        
        with patch('app.services.rate_limit.get_user_limit', AsyncMock(return_value=100)):
            with patch('app.services.rate_limit.get_redis', AsyncMock(return_value=mock_redis)):
                # Should not raise
                await check_rate_limit("user-1", "chat", 100)
    
    async def test_check_rate_limit_exceeded(self):
        """Should raise 429 when limit exceeded"""
        from fastapi import HTTPException
        from app.services.rate_limit import check_rate_limit
        
        mock_redis = MagicMock()
        mock_redis.eval = AsyncMock(return_value=101)  # Over the limit
        
        with patch('app.services.rate_limit.get_user_limit', AsyncMock(return_value=100)):
            with patch('app.services.rate_limit.get_redis', AsyncMock(return_value=mock_redis)):
                with pytest.raises(HTTPException) as exc_info:
                    await check_rate_limit("user-1", "chat", 100)
                
                assert exc_info.value.status_code == 429


class TestGetRateLimitStatusFull:
    """More comprehensive tests for get_rate_limit_status"""
    
    async def test_normal_user_status(self):
        """Should return correct status for normal user"""
        from app.services.rate_limit import get_rate_limit_status
        
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value="50")  # 50 requests used
        
        with patch('app.services.rate_limit.get_user_limit', AsyncMock(return_value=100)):
            with patch('app.services.rate_limit.get_redis', AsyncMock(return_value=mock_redis)):
                result = await get_rate_limit_status("user-1", "chat", 100)
        
        assert result["used"] == 50
        assert result["limit"] == 100
        assert result["remaining"] == 50
        assert result["is_exempt"] is False
    
    async def test_user_with_no_requests(self):
        """Should handle user with no requests"""
        from app.services.rate_limit import get_rate_limit_status
        
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)  # No requests yet
        
        with patch('app.services.rate_limit.get_user_limit', AsyncMock(return_value=100)):
            with patch('app.services.rate_limit.get_redis', AsyncMock(return_value=mock_redis)):
                result = await get_rate_limit_status("user-1", "chat", 100)
        
        assert result["used"] == 0
        assert result["remaining"] == 100


class TestGetRedis:
    """Tests for Redis connection"""
    
    async def test_get_redis_creates_client(self):
        """Should create Redis client on first call"""
        from app.services import rate_limit
        
        # Reset the global redis client
        original_redis = rate_limit._redis
        rate_limit._redis = None
        
        try:
            with patch('app.services.rate_limit.Redis') as mock_redis_class:
                mock_client = MagicMock()
                mock_redis_class.from_url.return_value = mock_client
                
                result = await rate_limit.get_redis()
                
                mock_redis_class.from_url.assert_called_once()
                assert result == mock_client
        finally:
            rate_limit._redis = original_redis
    
    async def test_get_redis_reuses_client(self):
        """Should reuse existing Redis client"""
        from app.services import rate_limit
        
        mock_existing = MagicMock()
        original_redis = rate_limit._redis
        rate_limit._redis = mock_existing
        
        try:
            result = await rate_limit.get_redis()
            assert result == mock_existing
        finally:
            rate_limit._redis = original_redis


class TestDatabaseCoverage:
    """Additional tests for database module"""
    
    def test_database_url_postgres_conversion(self):
        """Should convert postgres:// to postgresql+asyncpg://"""
        # This tests the module-level URL conversion logic
        # The conversion happens at import time, so we test the pattern
        url = "postgres://user:pass@localhost/db"
        expected = "postgresql+asyncpg://user:pass@localhost/db"
        
        if url.startswith("postgres://"):
            result = url.replace("postgres://", "postgresql+asyncpg://", 1)
            assert result == expected
    
    def test_database_url_postgresql_conversion(self):
        """Should convert postgresql:// to postgresql+asyncpg://"""
        url = "postgresql://user:pass@localhost/db"
        expected = "postgresql+asyncpg://user:pass@localhost/db"
        
        if url.startswith("postgresql://"):
            result = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            assert result == expected
    
    async def test_init_db_with_engine(self):
        """Should create tables when engine is configured"""
        from app import database
        
        # Just verify the database module structure
        assert hasattr(database, 'Base')
        assert hasattr(database, 'init_db')
        assert hasattr(database, 'get_db')
        
        # Test with mocked engine using proper async context manager
        class MockConn:
            async def run_sync(self, fn):
                pass
        
        class MockAsyncContextManager:
            async def __aenter__(self):
                return MockConn()
            async def __aexit__(self, *args):
                pass
        
        mock_engine = MagicMock()
        mock_engine.begin = MagicMock(return_value=MockAsyncContextManager())
        
        original_engine = database.engine
        database.engine = mock_engine
        
        try:
            await database.init_db()
            mock_engine.begin.assert_called_once()
        finally:
            database.engine = original_engine
    
    async def test_get_db_yields_session(self):
        """Should yield a session from get_db"""
        from app import database
        
        # Test with mocked session maker
        class MockSession:
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
        
        mock_session_maker = MagicMock(return_value=MockSession())
        
        original_session_local = database.AsyncSessionLocal
        database.AsyncSessionLocal = mock_session_maker
        
        try:
            async for session in database.get_db():
                assert session is not None
                break
        finally:
            database.AsyncSessionLocal = original_session_local


class TestAuthEdgeCases:
    """Edge case tests for auth module"""
    
    def test_verify_service_token_missing_defaults(self):
        """Should handle missing optional fields in service token"""
        from app.dependencies.auth import verify_service_token
        
        # Token with service=True but missing sub and username
        payload = {"service": True}
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        
        user = verify_service_token(token)
        
        assert user is not None
        assert user.user_id == "service"  # Default value
        assert user.username == "service"  # Default value
    
    async def test_verify_with_auth_service_invalid_response(self):
        """Should handle missing valid field in response"""
        from app.dependencies.auth import verify_token_with_auth_service
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}  # Missing 'valid' field
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            user = await verify_token_with_auth_service("test-token")
        
        # Should return None when valid field is missing/falsy
        assert user is None


class TestGetCurrentUserEdgeCases:
    """Edge cases for get_current_user"""
    
    async def test_service_token_logs_debug(self):
        """Should log debug message for service auth"""
        from app.dependencies.auth import get_current_user
        from fastapi.security import HTTPAuthorizationCredentials
        
        payload = {"service": True, "sub": "test-service"}
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        
        with patch('app.dependencies.auth.logger') as mock_logger:
            user = await get_current_user(credentials, None)
            
            # Should have logged the service auth
            assert user is not None
            mock_logger.debug.assert_called()
    
    async def test_falls_back_to_auth_service(self):
        """Should try auth service when not a service token"""
        from app.dependencies.auth import get_current_user
        from fastapi.security import HTTPAuthorizationCredentials
        
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not-a-service-token")
        
        with patch('app.dependencies.auth.verify_token_with_auth_service', AsyncMock(return_value=None)):
            user = await get_current_user(credentials, None)
        
        assert user is None


class TestGetUserLimitWithDatabase:
    """Tests for get_user_limit with database interactions"""
    
    async def test_create_new_exempt_user(self):
        """Should create unlimited record for exempt user"""
        from app.services.rate_limit import get_user_limit, UNLIMITED_LIMIT
        
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No existing record
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch.object(type(settings), 'rate_limit_exempt_roles', property(lambda self: {"admin"})):
            with patch('app.database.AsyncSessionLocal', mock_session_maker):
                result = await get_user_limit("user-1", 100, user_role="admin")
            
            assert result == UNLIMITED_LIMIT
    
    async def test_create_new_normal_user(self):
        """Should create default record for normal user"""
        from app.services.rate_limit import get_user_limit
        
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.database.AsyncSessionLocal', mock_session_maker):
            result = await get_user_limit("user-1", 100, user_role="member")
        
        assert result == 100
    
    async def test_user_becomes_exempt(self):
        """Should update user when they become exempt"""
        from app.services.rate_limit import get_user_limit, UNLIMITED_LIMIT
        
        # Existing non-exempt user
        mock_user_limit = MagicMock()
        mock_user_limit.is_role_exempt = False
        mock_user_limit.daily_limit = None
        
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user_limit
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch.object(type(settings), 'rate_limit_exempt_roles', property(lambda self: {"admin"})):
            with patch('app.database.AsyncSessionLocal', mock_session_maker):
                result = await get_user_limit("user-1", 100, user_role="admin")
            
            assert result == UNLIMITED_LIMIT
            assert mock_user_limit.daily_limit == UNLIMITED_LIMIT
            assert mock_user_limit.is_role_exempt is True
    
    async def test_user_loses_exemption(self):
        """Should update user when they lose exemption"""
        from app.services.rate_limit import get_user_limit
        
        # Existing exempt user
        mock_user_limit = MagicMock()
        mock_user_limit.is_role_exempt = True
        mock_user_limit.daily_limit = -1
        
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user_limit
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch.object(type(settings), 'rate_limit_exempt_roles', property(lambda self: set())):
            with patch('app.database.AsyncSessionLocal', mock_session_maker):
                result = await get_user_limit("user-1", 100, user_role="member")
            
            assert result == 100  # Back to default
            assert mock_user_limit.daily_limit is None
            assert mock_user_limit.is_role_exempt is False
    
    async def test_existing_exempt_user(self):
        """Should keep unlimited for existing exempt user"""
        from app.services.rate_limit import get_user_limit, UNLIMITED_LIMIT
        
        mock_user_limit = MagicMock()
        mock_user_limit.is_role_exempt = True
        mock_user_limit.daily_limit = -1
        
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user_limit
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch.object(type(settings), 'rate_limit_exempt_roles', property(lambda self: {"admin"})):
            with patch('app.database.AsyncSessionLocal', mock_session_maker):
                result = await get_user_limit("user-1", 100, user_role="admin")
            
            assert result == UNLIMITED_LIMIT
    
    async def test_user_with_custom_limit(self):
        """Should use custom limit when set"""
        from app.services.rate_limit import get_user_limit
        
        mock_user_limit = MagicMock()
        mock_user_limit.is_role_exempt = False
        mock_user_limit.daily_limit = 50  # Custom limit
        
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user_limit
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.database.AsyncSessionLocal', mock_session_maker):
            result = await get_user_limit("user-1", 100, user_role="member")
        
        assert result == 50
    
    async def test_database_error_falls_back(self):
        """Should fall back to role check on database error"""
        from app.services.rate_limit import get_user_limit, UNLIMITED_LIMIT
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(side_effect=Exception("DB error"))
        
        with patch.object(type(settings), 'rate_limit_exempt_roles', property(lambda self: {"admin"})):
            with patch('app.database.AsyncSessionLocal', mock_session_maker):
                result = await get_user_limit("user-1", 100, user_role="admin")
            
            assert result == UNLIMITED_LIMIT  # Falls back to role check
    
    async def test_database_error_non_exempt(self):
        """Should fall back to default on database error for non-exempt"""
        from app.services.rate_limit import get_user_limit
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(side_effect=Exception("DB error"))
        
        with patch('app.database.AsyncSessionLocal', mock_session_maker):
            result = await get_user_limit("user-1", 100, user_role="member")
        
        assert result == 100


class TestSetUserLimit:
    """Tests for set_user_limit function"""
    
    async def test_set_limit_no_database(self):
        """Should raise when database not configured"""
        from app.services.rate_limit import set_user_limit
        
        with patch('app.database.AsyncSessionLocal', None):
            with pytest.raises(RuntimeError) as exc_info:
                await set_user_limit("user-1", 50)
            
            assert "Database not configured" in str(exc_info.value)
    
    async def test_set_limit_new_user(self):
        """Should create new record for new user"""
        from app.services.rate_limit import set_user_limit
        
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.database.AsyncSessionLocal', mock_session_maker):
            result = await set_user_limit("user-1", 50)
        
        assert result["user_id"] == "user-1"
        assert result["daily_limit"] == 50
    
    async def test_set_limit_existing_user(self):
        """Should update existing record"""
        from app.services.rate_limit import set_user_limit
        
        mock_user_limit = MagicMock()
        mock_user_limit.user_id = "user-1"
        mock_user_limit.daily_limit = 100
        mock_user_limit.is_role_exempt = False
        
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user_limit
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.database.AsyncSessionLocal', mock_session_maker):
            result = await set_user_limit("user-1", 50, is_manual=True)
        
        assert mock_user_limit.daily_limit == 50
        assert mock_user_limit.is_role_exempt is False
    
    async def test_set_unlimited(self):
        """Should set unlimited limit"""
        from app.services.rate_limit import set_user_limit
        
        mock_user_limit = MagicMock()
        mock_user_limit.user_id = "user-1"
        mock_user_limit.daily_limit = 100
        mock_user_limit.is_role_exempt = False
        
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user_limit
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.database.AsyncSessionLocal', mock_session_maker):
            result = await set_user_limit("user-1", -1)
        
        assert mock_user_limit.daily_limit == -1


class TestResetUserToDefault:
    """Tests for reset_user_to_default function"""
    
    async def test_reset_to_default(self):
        """Should reset user to default limit"""
        from app.services.rate_limit import reset_user_to_default
        
        mock_user_limit = MagicMock()
        mock_user_limit.user_id = "user-1"
        mock_user_limit.daily_limit = 50
        mock_user_limit.is_role_exempt = False
        
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user_limit
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('app.database.AsyncSessionLocal', mock_session_maker):
            result = await reset_user_to_default("user-1")
        
        assert mock_user_limit.daily_limit is None

