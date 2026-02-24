"""
Unit tests for auth router endpoints.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models import InviteInDB, InviteStatus, UserInDB, UserResponse, UserRole
from app.routers.auth import (
    get_current_user,
    require_admin_access,
    require_auth,
    require_owner,
    router,
)


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
        hashed_password="hash",
        created_at=now,
        updated_at=now,
        is_active=True,
    )


@pytest.fixture
def mock_user():
    """Create mock regular user (member role)"""
    now = datetime.now(timezone.utc)
    return UserInDB(
        id="user-456",
        username="testuser",
        first_name="Test",
        last_name="User",
        email="user@test.com",
        role=UserRole.MEMBER,
        hashed_password="hash",
        created_at=now,
        updated_at=now,
        is_active=True,
    )


@pytest.fixture
def mock_rw_user():
    """Create mock admin (read-write) user"""
    now = datetime.now(timezone.utc)
    return UserInDB(
        id="rw-789",
        username="rwuser",
        first_name="RW",
        last_name="User",
        email="rw@test.com",
        role=UserRole.ADMIN,
        hashed_password="hash",
        created_at=now,
        updated_at=now,
        is_active=True,
    )


class TestSetupEndpoints:
    """Tests for setup endpoints"""

    def test_get_setup_status(self, client):
        """Should return setup status"""
        mock_status = {"is_setup_complete": True, "owner_exists": True, "total_users": 3}

        with patch("app.routers.auth.auth_service") as mock_service:
            mock_service.get_setup_status = AsyncMock(return_value=mock_status)

            response = client.get("/api/auth/setup/status")

            assert response.status_code == 200
            assert response.json()["is_setup_complete"] is True

    def test_setup_owner_success(self, client, mock_owner):
        """Should create owner"""
        with patch("app.routers.auth.auth_service") as mock_service:
            mock_service.setup_owner = AsyncMock(
                return_value=UserResponse(
                    id=mock_owner.id,
                    username=mock_owner.username,
                    first_name=mock_owner.first_name,
                    last_name=mock_owner.last_name,
                    email=mock_owner.email,
                    role=mock_owner.role,
                    created_at=mock_owner.created_at,
                    updated_at=mock_owner.updated_at,
                )
            )

            response = client.post(
                "/api/auth/setup/owner",
                json={
                    "username": "admin",
                    "first_name": "Admin",
                    "last_name": "User",
                    "email": "admin@test.com",
                    "password": "password123",
                },
            )

            assert response.status_code == 200

    def test_setup_owner_error(self, client):
        """Should return 400 on error"""
        with patch("app.routers.auth.auth_service") as mock_service:
            mock_service.setup_owner = AsyncMock(side_effect=ValueError("Setup already complete"))

            response = client.post(
                "/api/auth/setup/owner",
                json={
                    "username": "admin",
                    "first_name": "Admin",
                    "last_name": "User",
                    "email": "admin@test.com",
                    "password": "password123",
                },
            )

            assert response.status_code == 400


class TestAuthConfigEndpoint:
    """Tests for auth config endpoint."""

    def test_get_auth_config_local_mode(self, client):
        with patch("app.routers.auth.settings") as mock_settings:
            mock_settings.auth_provider = "local"
            mock_settings.clerk_publishable_key = "pk_local_ignored"
            mock_settings.clerk_proxy_url = "https://clerk.local"
            mock_settings.allow_open_registration = False

            response = client.get("/api/auth/config")

            assert response.status_code == 200
            data = response.json()
            assert data["provider"] == "local"
            assert data["clerk_publishable_key"] is None
            assert data["clerk_proxy_url"] is None
            assert data["allow_registration"] is False

    def test_get_auth_config_cloud_mode(self, client):
        with patch("app.routers.auth.settings") as mock_settings:
            mock_settings.auth_provider = "cloud"
            mock_settings.clerk_publishable_key = "pk_test_123"
            mock_settings.clerk_proxy_url = "https://clerk.example.com"
            mock_settings.allow_open_registration = True

            response = client.get("/api/auth/config")

            assert response.status_code == 200
            data = response.json()
            assert data["provider"] == "cloud"
            assert data["clerk_publishable_key"] == "pk_test_123"
            assert data["clerk_proxy_url"] == "https://clerk.example.com"
            assert data["allow_registration"] is True


class TestInternalPlanSettingsEndpoints:
    """Tests for internal user plan-settings endpoints."""

    def test_get_user_plan_settings_internal_success(self, client, mock_user):
        plan_row = MagicMock()
        plan_row.user_id = mock_user.id
        plan_row.plan_id = "free"
        plan_row.owned_networks_limit = 1
        plan_row.assistant_daily_chat_messages_limit = 5
        plan_row.automatic_full_scan_min_interval_seconds = 7200
        plan_row.health_poll_interval_seconds = 60

        with (
            patch("app.routers.auth.auth_service") as mock_service,
            patch("app.routers.auth.get_user_plan_settings", new=AsyncMock(return_value=plan_row)),
        ):
            mock_service.get_user = AsyncMock(return_value=mock_user)

            response = client.get(f"/api/auth/internal/users/{mock_user.id}/plan-settings")

            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == mock_user.id
            assert data["plan_id"] == "free"
            assert data["owned_networks_limit"] == 1

    def test_get_user_plan_settings_internal_returns_404_when_user_missing(self, client):
        with patch("app.routers.auth.auth_service") as mock_service:
            mock_service.get_user = AsyncMock(return_value=None)

            response = client.get("/api/auth/internal/users/missing/plan-settings")

            assert response.status_code == 404
            assert response.json()["detail"] == "User not found"

    def test_get_user_plan_settings_internal_returns_500_when_settings_missing(
        self, client, mock_user
    ):
        with (
            patch("app.routers.auth.auth_service") as mock_service,
            patch("app.routers.auth.get_user_plan_settings", new=AsyncMock(return_value=None)),
        ):
            mock_service.get_user = AsyncMock(return_value=mock_user)

            response = client.get(f"/api/auth/internal/users/{mock_user.id}/plan-settings")

            assert response.status_code == 500
            assert "Failed to resolve user plan settings" in response.json()["detail"]

    def test_set_user_plan_settings_internal_success(self, client, mock_user):
        plan_row = MagicMock()
        plan_row.user_id = mock_user.id
        plan_row.plan_id = "pro"
        plan_row.owned_networks_limit = 3
        plan_row.assistant_daily_chat_messages_limit = 50
        plan_row.automatic_full_scan_min_interval_seconds = 60
        plan_row.health_poll_interval_seconds = 30

        with (
            patch("app.routers.auth.auth_service") as mock_service,
            patch(
                "app.routers.auth.apply_plan_to_user", new=AsyncMock(return_value=plan_row)
            ) as mock_apply,
        ):
            mock_service.get_user = AsyncMock(return_value=mock_user)

            response = client.put(
                f"/api/auth/internal/users/{mock_user.id}/plan-settings",
                json={"plan_id": "pro"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["plan_id"] == "pro"
            assert data["assistant_daily_chat_messages_limit"] == 50
            mock_apply.assert_awaited_once()

    def test_set_user_plan_settings_internal_returns_404_when_user_missing(self, client):
        with patch("app.routers.auth.auth_service") as mock_service:
            mock_service.get_user = AsyncMock(return_value=None)

            response = client.put(
                "/api/auth/internal/users/missing/plan-settings",
                json={"plan_id": "pro"},
            )

            assert response.status_code == 404
            assert response.json()["detail"] == "User not found"


class TestAuthenticationEndpoints:
    """Tests for authentication endpoints"""

    def test_login_success(self, client, mock_owner):
        """Should login and return token"""
        with patch("app.routers.auth.auth_service") as mock_service:
            mock_service.authenticate = AsyncMock(return_value=mock_owner)
            mock_service.create_access_token.return_value = ("token123", 3600)
            mock_service._to_response.return_value = UserResponse(
                id=mock_owner.id,
                username=mock_owner.username,
                first_name=mock_owner.first_name,
                last_name=mock_owner.last_name,
                email=mock_owner.email,
                role=mock_owner.role,
                created_at=mock_owner.created_at,
                updated_at=mock_owner.updated_at,
            )

            response = client.post(
                "/api/auth/login", json={"username": "owner", "password": "password123"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "token123"
            assert data["token_type"] == "bearer"

    def test_login_failure(self, client):
        """Should return 401 on failed login"""
        with patch("app.routers.auth.auth_service") as mock_service:
            mock_service.authenticate = AsyncMock(return_value=None)

            response = client.post(
                "/api/auth/login", json={"username": "wrong", "password": "wrong"}
            )

            assert response.status_code == 401

    def test_request_password_reset_generic_success(self, client):
        """Should always return generic success message for reset request."""
        with patch("app.routers.auth.auth_service") as mock_service:
            mock_service.request_password_reset = AsyncMock(return_value=True)

            response = client.post(
                "/api/auth/password-reset/request",
                json={"email": "owner@test.com"},
            )

            assert response.status_code == 200
            assert "If an account with that email exists" in response.json()["message"]
            mock_service.request_password_reset.assert_awaited_once_with(ANY, "owner@test.com")

    def test_confirm_password_reset_success(self, client):
        """Should reset password with a valid reset token."""
        with patch("app.routers.auth.auth_service") as mock_service:
            mock_service.confirm_password_reset = AsyncMock(return_value=True)

            response = client.post(
                "/api/auth/password-reset/confirm",
                json={"token": "valid-reset-token", "new_password": "newpassword123"},
            )

            assert response.status_code == 200
            assert response.json()["message"] == "Password has been reset successfully"

    def test_confirm_password_reset_invalid_token(self, client):
        """Should return 400 for invalid/expired reset tokens."""
        with patch("app.routers.auth.auth_service") as mock_service:
            mock_service.confirm_password_reset = AsyncMock(
                side_effect=ValueError("Invalid or expired reset token")
            )

            response = client.post(
                "/api/auth/password-reset/confirm",
                json={"token": "invalid-token", "new_password": "newpassword123"},
            )

            assert response.status_code == 400
            assert response.json()["detail"] == "Invalid or expired reset token"

    def test_logout(self, client, mock_owner):
        """Should logout user"""
        with patch("app.routers.auth.auth_service") as mock_service:
            from app.models import TokenPayload

            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc),
            )
            mock_service.get_user = AsyncMock(return_value=mock_owner)

            response = client.post("/api/auth/logout", headers={"Authorization": "Bearer token123"})

            assert response.status_code == 200

    def test_get_session(self, client, mock_owner):
        """Should get session info"""
        with patch("app.routers.auth.auth_service") as mock_service:
            from app.models import TokenPayload

            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc),
            )
            mock_service.get_user = AsyncMock(return_value=mock_owner)
            mock_service._to_response.return_value = UserResponse(
                id=mock_owner.id,
                username=mock_owner.username,
                first_name=mock_owner.first_name,
                last_name=mock_owner.last_name,
                email=mock_owner.email,
                role=mock_owner.role,
                created_at=mock_owner.created_at,
                updated_at=mock_owner.updated_at,
            )
            mock_service.get_permissions = MagicMock(return_value=["read:map"])

            response = client.get("/api/auth/session", headers={"Authorization": "Bearer token123"})

            assert response.status_code == 200

    def test_verify_token_valid(self, client, mock_owner):
        """Should verify valid token"""
        with patch("app.routers.auth.auth_service") as mock_service:
            from app.models import TokenPayload

            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc),
            )
            mock_service.decode_token_payload.return_value = {"service": False}
            mock_service.get_user = AsyncMock(return_value=mock_owner)

            response = client.post("/api/auth/verify", headers={"Authorization": "Bearer token123"})

            assert response.status_code == 200
            assert response.json()["valid"] is True

    def test_verify_token_service_token(self, client, mock_owner):
        """Should verify service token"""
        with patch("app.routers.auth.auth_service") as mock_service:
            from app.models import TokenPayload

            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc),
            )
            mock_service.decode_token_payload.return_value = {"service": True}

            response = client.post("/api/auth/verify", headers={"Authorization": "Bearer token123"})

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["is_service"] is True

    def test_verify_token_no_credentials(self, client):
        """Should return invalid for no credentials"""
        response = client.post("/api/auth/verify")

        assert response.status_code == 200
        assert response.json()["valid"] is False

    def test_verify_token_invalid(self, client):
        """Should return invalid for bad token"""
        with patch("app.routers.auth.auth_service") as mock_service:
            mock_service.verify_token.return_value = None

            response = client.post("/api/auth/verify", headers={"Authorization": "Bearer invalid"})

            assert response.status_code == 200
            assert response.json()["valid"] is False


class TestClerkExchangeEndpoint:
    """Tests for Clerk token exchange endpoint."""

    def test_exchange_clerk_token_rejects_when_not_in_cloud_mode(self, client):
        with patch("app.routers.auth.settings") as mock_settings:
            mock_settings.auth_provider = "local"

            response = client.post(
                "/api/auth/clerk/exchange", headers={"Authorization": "Bearer clerk-token"}
            )

            assert response.status_code == 400
            assert "cloud mode" in response.json()["detail"]

    def test_exchange_clerk_token_requires_credentials(self, client):
        with patch("app.routers.auth.settings") as mock_settings:
            mock_settings.auth_provider = "cloud"

            response = client.post("/api/auth/clerk/exchange")

            assert response.status_code == 401
            assert "required" in response.json()["detail"]

    def test_exchange_clerk_token_returns_500_when_sync_fails(self, client):
        from app.identity.claims import AuthMethod, AuthProvider, IdentityClaims

        claims = IdentityClaims(
            provider=AuthProvider.CLERK,
            provider_user_id="clerk-user-1",
            auth_method=AuthMethod.SOCIAL_OAUTH,
            email="sync@test.com",
            email_verified=True,
            username="syncuser",
            first_name="Sync",
            last_name="User",
            avatar_url=None,
            session_id="sess_123",
            issued_at=datetime.now(timezone.utc),
            expires_at=None,
            org_id=None,
            org_slug=None,
            org_role=None,
            connection_id=None,
            connection_type=None,
            idp_id=None,
            directory_id=None,
            raw_attributes=None,
            local_user_id=None,
        )

        provider = MagicMock()
        provider.validate_token = AsyncMock(return_value=claims)

        with (
            patch("app.routers.auth.settings") as mock_settings,
            patch("app.routers.auth.get_provider", return_value=provider),
            patch(
                "app.routers.auth.sync_provider_user",
                new=AsyncMock(return_value=(None, False, False)),
            ),
        ):
            mock_settings.auth_provider = "cloud"

            response = client.post(
                "/api/auth/clerk/exchange", headers={"Authorization": "Bearer clerk-token"}
            )

            assert response.status_code == 500
            assert "Failed to sync user" in response.json()["detail"]

    def test_exchange_clerk_token_returns_500_when_synced_user_not_found(self, client):
        from app.identity.claims import AuthMethod, AuthProvider, IdentityClaims

        claims = IdentityClaims(
            provider=AuthProvider.CLERK,
            provider_user_id="clerk-user-2",
            auth_method=AuthMethod.SOCIAL_OAUTH,
            email="found@test.com",
            email_verified=True,
            username="founduser",
            first_name="Found",
            last_name="User",
            avatar_url=None,
            session_id="sess_234",
            issued_at=datetime.now(timezone.utc),
            expires_at=None,
            org_id=None,
            org_slug=None,
            org_role=None,
            connection_id=None,
            connection_type=None,
            idp_id=None,
            directory_id=None,
            raw_attributes=None,
            local_user_id=None,
        )

        provider = MagicMock()
        provider.validate_token = AsyncMock(return_value=claims)

        with (
            patch("app.routers.auth.settings") as mock_settings,
            patch("app.routers.auth.get_provider", return_value=provider),
            patch(
                "app.routers.auth.sync_provider_user",
                new=AsyncMock(return_value=("local-123", True, False)),
            ),
            patch("app.routers.auth.auth_service") as mock_service,
        ):
            mock_settings.auth_provider = "cloud"
            mock_service.get_user = AsyncMock(return_value=None)

            response = client.post(
                "/api/auth/clerk/exchange", headers={"Authorization": "Bearer clerk-token"}
            )

            assert response.status_code == 500
            assert "retrieve synced user" in response.json()["detail"]


class TestUserManagementEndpoints:
    """Tests for user management endpoints"""

    def test_list_users(self, client, mock_owner):
        """Should list users"""
        with patch("app.routers.auth.auth_service") as mock_service:
            from app.models import TokenPayload

            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc),
            )
            mock_service.get_user = AsyncMock(return_value=mock_owner)
            mock_service.list_users = AsyncMock(
                return_value=[
                    UserResponse(
                        id=mock_owner.id,
                        username=mock_owner.username,
                        first_name=mock_owner.first_name,
                        last_name=mock_owner.last_name,
                        email=mock_owner.email,
                        role=mock_owner.role,
                        created_at=mock_owner.created_at,
                        updated_at=mock_owner.updated_at,
                    )
                ]
            )

            response = client.get("/api/auth/users", headers={"Authorization": "Bearer token123"})

            assert response.status_code == 200

    def test_create_user(self, client, mock_owner):
        """Should create user"""
        with patch("app.routers.auth.auth_service") as mock_service:
            from app.models import TokenPayload

            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc),
            )
            mock_service.get_user = AsyncMock(return_value=mock_owner)
            mock_service.create_user = AsyncMock(
                return_value=UserResponse(
                    id="new-user-123",
                    username="newuser",
                    first_name="New",
                    last_name="User",
                    email="new@test.com",
                    role=UserRole.MEMBER,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            )

            response = client.post(
                "/api/auth/users",
                headers={"Authorization": "Bearer token123"},
                json={
                    "username": "newuser",
                    "first_name": "New",
                    "last_name": "User",
                    "email": "new@test.com",
                    "password": "password123",
                },
            )

            assert response.status_code == 200

    def test_get_user(self, client, mock_owner):
        """Should get user by ID"""
        with patch("app.routers.auth.auth_service") as mock_service:
            from app.models import TokenPayload

            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc),
            )
            mock_service.get_user = AsyncMock(return_value=mock_owner)
            mock_service._to_response.return_value = UserResponse(
                id=mock_owner.id,
                username=mock_owner.username,
                first_name=mock_owner.first_name,
                last_name=mock_owner.last_name,
                email=mock_owner.email,
                role=mock_owner.role,
                created_at=mock_owner.created_at,
                updated_at=mock_owner.updated_at,
            )

            response = client.get(
                f"/api/auth/users/{mock_owner.id}", headers={"Authorization": "Bearer token123"}
            )

            assert response.status_code == 200

    def test_get_user_access_denied(self, client, mock_user, mock_owner):
        """Should deny access to other users"""
        with patch("app.routers.auth.auth_service") as mock_service:
            from app.models import TokenPayload

            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_user.id,
                username=mock_user.username,
                role=mock_user.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc),
            )
            mock_service.get_user = AsyncMock(return_value=mock_user)

            response = client.get(
                f"/api/auth/users/{mock_owner.id}", headers={"Authorization": "Bearer token123"}
            )

            assert response.status_code == 403

    def test_update_user(self, client, mock_owner):
        """Should update user"""
        with patch("app.routers.auth.auth_service") as mock_service:
            from app.models import TokenPayload

            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc),
            )
            mock_service.get_user = AsyncMock(return_value=mock_owner)
            mock_service.update_user = AsyncMock(
                return_value=UserResponse(
                    id=mock_owner.id,
                    username=mock_owner.username,
                    first_name="Updated",
                    last_name=mock_owner.last_name,
                    email=mock_owner.email,
                    role=mock_owner.role,
                    created_at=mock_owner.created_at,
                    updated_at=mock_owner.updated_at,
                )
            )

            response = client.patch(
                f"/api/auth/users/{mock_owner.id}",
                headers={"Authorization": "Bearer token123"},
                json={"first_name": "Updated"},
            )

            assert response.status_code == 200

    def test_delete_user(self, client, mock_owner, mock_user):
        """Should delete user"""
        with patch("app.routers.auth.auth_service") as mock_service:
            from app.models import TokenPayload

            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc),
            )
            mock_service.get_user = AsyncMock(return_value=mock_owner)
            mock_service.delete_user = AsyncMock(return_value=True)

            response = client.delete(
                f"/api/auth/users/{mock_user.id}", headers={"Authorization": "Bearer token123"}
            )

            assert response.status_code == 200


class TestNetworkLimitEndpoints:
    """Tests for network limit endpoints."""

    def test_get_network_limit_for_authenticated_user(self, client, mock_user):
        from app.models import TokenPayload

        with (
            patch("app.routers.auth.auth_service") as mock_service,
            patch(
                "app.services.network_limit.get_network_limit_status",
                new=AsyncMock(
                    return_value={
                        "used": 1,
                        "limit": 2,
                        "remaining": 1,
                        "is_exempt": False,
                        "message": None,
                    }
                ),
            ),
        ):
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_user.id,
                username=mock_user.username,
                role=mock_user.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc),
            )
            mock_service.get_user = AsyncMock(return_value=mock_user)

            response = client.get(
                "/api/auth/network-limit", headers={"Authorization": "Bearer token123"}
            )

            assert response.status_code == 200
            assert response.json()["remaining"] == 1

    def test_get_user_network_limit_returns_404_for_missing_target(self, client, mock_owner):
        from app.models import TokenPayload

        with patch("app.routers.auth.auth_service") as mock_service:
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc),
            )
            mock_service.get_user = AsyncMock(side_effect=[mock_owner, None])

            response = client.get(
                "/api/auth/users/missing-user/network-limit",
                headers={"Authorization": "Bearer token123"},
            )

            assert response.status_code == 404

    def test_get_user_network_limit_success(self, client, mock_owner, mock_user):
        from app.models import TokenPayload

        with (
            patch("app.routers.auth.auth_service") as mock_service,
            patch(
                "app.services.network_limit.get_network_limit_status",
                new=AsyncMock(
                    return_value={
                        "used": 0,
                        "limit": 1,
                        "remaining": 1,
                        "is_exempt": False,
                        "message": None,
                    }
                ),
            ),
        ):
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc),
            )
            mock_service.get_user = AsyncMock(side_effect=[mock_owner, mock_user])

            response = client.get(
                f"/api/auth/users/{mock_user.id}/network-limit",
                headers={"Authorization": "Bearer token123"},
            )

            assert response.status_code == 200
            assert response.json()["limit"] == 1

    def test_set_user_network_limit_returns_404_for_missing_target(self, client, mock_owner):
        from app.models import TokenPayload

        with patch("app.routers.auth.auth_service") as mock_service:
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc),
            )
            mock_service.get_user = AsyncMock(side_effect=[mock_owner, None])

            response = client.put(
                "/api/auth/users/missing-user/network-limit",
                headers={"Authorization": "Bearer token123"},
                json={"network_limit": 2},
            )

            assert response.status_code == 404

    def test_set_user_network_limit_success(self, client, mock_owner, mock_user):
        from app.models import TokenPayload

        with (
            patch("app.routers.auth.auth_service") as mock_service,
            patch(
                "app.services.network_limit.set_user_network_limit",
                new=AsyncMock(
                    return_value={
                        "user_id": mock_user.id,
                        "network_limit": 4,
                        "is_role_exempt": False,
                    }
                ),
            ),
        ):
            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc),
            )
            mock_service.get_user = AsyncMock(side_effect=[mock_owner, mock_user])

            response = client.put(
                f"/api/auth/users/{mock_user.id}/network-limit",
                headers={"Authorization": "Bearer token123"},
                json={"network_limit": 4},
            )

            assert response.status_code == 200
            assert response.json()["network_limit"] == 4


class TestProfileEndpoints:
    """Tests for profile endpoints"""

    def test_get_current_profile(self, client, mock_owner):
        """Should get current user's profile"""
        with patch("app.routers.auth.auth_service") as mock_service:
            from app.models import TokenPayload

            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc),
            )
            mock_service.get_user = AsyncMock(return_value=mock_owner)
            mock_service._to_response.return_value = UserResponse(
                id=mock_owner.id,
                username=mock_owner.username,
                first_name=mock_owner.first_name,
                last_name=mock_owner.last_name,
                email=mock_owner.email,
                role=mock_owner.role,
                created_at=mock_owner.created_at,
                updated_at=mock_owner.updated_at,
            )

            response = client.get("/api/auth/me", headers={"Authorization": "Bearer token123"})

            assert response.status_code == 200

    def test_update_current_profile(self, client, mock_owner):
        """Should update own profile"""
        with patch("app.routers.auth.auth_service") as mock_service:
            from app.models import TokenPayload

            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc),
            )
            mock_service.get_user = AsyncMock(return_value=mock_owner)
            mock_service.update_user = AsyncMock(
                return_value=UserResponse(
                    id=mock_owner.id,
                    username=mock_owner.username,
                    first_name="Updated",
                    last_name=mock_owner.last_name,
                    email=mock_owner.email,
                    role=mock_owner.role,
                    created_at=mock_owner.created_at,
                    updated_at=mock_owner.updated_at,
                )
            )

            response = client.patch(
                "/api/auth/me",
                headers={"Authorization": "Bearer token123"},
                json={"first_name": "Updated"},
            )

            assert response.status_code == 200

    def test_update_profile_cannot_change_role(self, client, mock_user):
        """Non-owners cannot change their role"""
        with patch("app.routers.auth.auth_service") as mock_service:
            from app.models import TokenPayload

            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_user.id,
                username=mock_user.username,
                role=mock_user.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc),
            )
            mock_service.get_user = AsyncMock(return_value=mock_user)

            response = client.patch(
                "/api/auth/me", headers={"Authorization": "Bearer token123"}, json={"role": "admin"}
            )

            assert response.status_code == 403

    def test_change_password(self, client, mock_owner):
        """Should change password"""
        with patch("app.routers.auth.auth_service") as mock_service:
            from app.models import TokenPayload

            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc),
            )
            mock_service.get_user = AsyncMock(return_value=mock_owner)
            mock_service.change_password = AsyncMock(return_value=True)

            response = client.post(
                "/api/auth/me/change-password",
                headers={"Authorization": "Bearer token123"},
                json={"current_password": "oldpassword", "new_password": "newpassword123"},
            )

            assert response.status_code == 200


class TestInviteEndpoints:
    """Tests for invitation endpoints"""

    def test_list_invites(self, client, mock_owner):
        """Should list invites"""
        with patch("app.routers.auth.auth_service") as mock_service:
            from app.models import TokenPayload

            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=datetime.now(timezone.utc) + timedelta(hours=1),
                iat=datetime.now(timezone.utc),
            )
            mock_service.get_user = AsyncMock(return_value=mock_owner)
            mock_service.list_invites = AsyncMock(return_value=[])

            response = client.get("/api/auth/invites", headers={"Authorization": "Bearer token123"})

            assert response.status_code == 200

    def test_create_invite(self, client, mock_owner):
        """Should create invite"""
        with patch("app.routers.auth.auth_service") as mock_service:
            from app.models import InviteResponse, TokenPayload

            now = datetime.now(timezone.utc)

            mock_service.verify_token.return_value = TokenPayload(
                sub=mock_owner.id,
                username=mock_owner.username,
                role=mock_owner.role,
                exp=now + timedelta(hours=1),
                iat=now,
            )
            mock_service.get_user = AsyncMock(return_value=mock_owner)

            mock_invite = InviteInDB(
                id="invite-123",
                email="new@test.com",
                role=UserRole.MEMBER,
                status=InviteStatus.PENDING,
                invited_by_username=mock_owner.username,
                invited_by_name=f"{mock_owner.first_name} {mock_owner.last_name}",
                invited_by_id=mock_owner.id,
                token="token123",
                created_at=now,
                expires_at=now + timedelta(hours=72),
            )
            mock_service.create_invite = AsyncMock(return_value=(mock_invite, False))
            mock_service._invite_to_response.return_value = InviteResponse(
                id=mock_invite.id,
                email=mock_invite.email,
                role=mock_invite.role,
                status=mock_invite.status,
                invited_by=mock_invite.invited_by_username,
                invited_by_name=mock_invite.invited_by_name,
                created_at=mock_invite.created_at,
                expires_at=mock_invite.expires_at,
            )

            response = client.post(
                "/api/auth/invites",
                headers={"Authorization": "Bearer token123"},
                json={"email": "new@test.com", "role": "member"},
            )

            assert response.status_code == 200

    def test_verify_invite_token(self, client):
        """Should verify invite token"""
        with patch("app.routers.auth.auth_service") as mock_service:
            from app.models import InviteTokenInfo

            mock_service.get_invite_token_info = AsyncMock(
                return_value=InviteTokenInfo(
                    email="invite@test.com",
                    role=UserRole.MEMBER,
                    invited_by_name="Admin User",
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
                    is_valid=True,
                )
            )

            response = client.get("/api/auth/invite/verify/test-token")

            assert response.status_code == 200
            assert response.json()["is_valid"] is True

    def test_verify_invite_token_not_found(self, client):
        """Should return 404 for invalid token"""
        with patch("app.routers.auth.auth_service") as mock_service:
            mock_service.get_invite_token_info = AsyncMock(return_value=None)

            response = client.get("/api/auth/invite/verify/invalid-token")

            assert response.status_code == 404

    def test_accept_invite(self, client, mock_owner):
        """Should accept invite"""
        with patch("app.routers.auth.auth_service") as mock_service:
            now = datetime.now(timezone.utc)

            mock_service.accept_invite = AsyncMock(
                return_value=UserResponse(
                    id="new-user-123",
                    username="newuser",
                    first_name="New",
                    last_name="User",
                    email="invite@test.com",
                    role=UserRole.MEMBER,
                    created_at=now,
                    updated_at=now,
                )
            )

            response = client.post(
                "/api/auth/invite/accept",
                json={
                    "token": "valid-token",
                    "username": "newuser",
                    "first_name": "New",
                    "last_name": "User",
                    "password": "password123",
                },
            )

            assert response.status_code == 200


class TestDependencies:
    """Tests for auth dependencies"""

    async def test_get_current_user_no_credentials(self):
        """Should return None without credentials"""
        user = await get_current_user(None)
        assert user is None

    async def test_require_auth_raises_without_user(self):
        """Should raise HTTPException without user"""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await require_auth(None)

        assert exc_info.value.status_code == 401

    async def test_require_owner_raises_for_non_owner(self, mock_user):
        """Should raise HTTPException for non-owner"""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await require_owner(mock_user)

        assert exc_info.value.status_code == 403

    async def test_require_owner_passes_for_owner(self, mock_owner):
        """Should pass for owner"""
        result = await require_owner(mock_owner)
        assert result == mock_owner

    async def test_require_admin_access_member_denied(self, mock_user):
        """Should deny member users"""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await require_admin_access(mock_user)

        assert exc_info.value.status_code == 403

    async def test_require_admin_access_admin_allowed(self, mock_rw_user):
        """Should allow admin users"""
        result = await require_admin_access(mock_rw_user)
        assert result == mock_rw_user
