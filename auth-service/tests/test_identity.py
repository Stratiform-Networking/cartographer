"""
Unit tests for the identity module.

Tests for:
- Identity claims and enums
- Pydantic models
- Provider factory
- LocalAuthProvider
- User sync service
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.identity.claims import AuthMethod, AuthProvider, IdentityClaims, ProviderConfig


class TestAuthProviderEnum:
    """Tests for AuthProvider enum"""

    def test_local_value(self):
        """Should have correct local value"""
        assert AuthProvider.LOCAL.value == "local"

    def test_clerk_value(self):
        """Should have correct clerk value"""
        assert AuthProvider.CLERK.value == "clerk"

    def test_workos_value(self):
        """Should have correct workos value"""
        assert AuthProvider.WORKOS.value == "workos"

    def test_is_string_enum(self):
        """Should be a string enum"""
        assert isinstance(AuthProvider.LOCAL, str)
        assert AuthProvider.LOCAL == "local"


class TestAuthMethodEnum:
    """Tests for AuthMethod enum"""

    def test_password_value(self):
        """Should have correct password value"""
        assert AuthMethod.PASSWORD.value == "password"

    def test_social_oauth_value(self):
        """Should have correct social_oauth value"""
        assert AuthMethod.SOCIAL_OAUTH.value == "social_oauth"

    def test_saml_sso_value(self):
        """Should have correct saml_sso value"""
        assert AuthMethod.SAML_SSO.value == "saml_sso"

    def test_oidc_sso_value(self):
        """Should have correct oidc_sso value"""
        assert AuthMethod.OIDC_SSO.value == "oidc_sso"

    def test_magic_link_value(self):
        """Should have correct magic_link value"""
        assert AuthMethod.MAGIC_LINK.value == "magic_link"

    def test_passkey_value(self):
        """Should have correct passkey value"""
        assert AuthMethod.PASSKEY.value == "passkey"


class TestIdentityClaims:
    """Tests for IdentityClaims dataclass"""

    def test_create_minimal_claims(self):
        """Should create claims with required fields"""
        now = datetime.now(timezone.utc)
        claims = IdentityClaims(
            provider=AuthProvider.LOCAL,
            provider_user_id="user-123",
            auth_method=AuthMethod.PASSWORD,
            email="test@example.com",
            email_verified=True,
            username="testuser",
            first_name="Test",
            last_name="User",
            avatar_url=None,
            session_id=None,
            issued_at=now,
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

        assert claims.provider == AuthProvider.LOCAL
        assert claims.provider_user_id == "user-123"
        assert claims.auth_method == AuthMethod.PASSWORD
        assert claims.email == "test@example.com"
        assert claims.email_verified is True

    def test_create_full_claims(self):
        """Should create claims with all fields populated"""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=24)
        user_id = uuid4()

        claims = IdentityClaims(
            provider=AuthProvider.CLERK,
            provider_user_id="clerk_user_123",
            auth_method=AuthMethod.SOCIAL_OAUTH,
            email="user@company.com",
            email_verified=True,
            username="johndoe",
            first_name="John",
            last_name="Doe",
            avatar_url="https://example.com/avatar.jpg",
            session_id="session_abc",
            issued_at=now,
            expires_at=expires,
            org_id="org_123",
            org_slug="acme-corp",
            org_role="admin",
            connection_id="conn_xyz",
            connection_type="saml",
            idp_id="idp_456",
            directory_id="dir_789",
            raw_attributes={"department": "Engineering"},
            local_user_id=user_id,
        )

        assert claims.provider == AuthProvider.CLERK
        assert claims.avatar_url == "https://example.com/avatar.jpg"
        assert claims.org_slug == "acme-corp"
        assert claims.raw_attributes == {"department": "Engineering"}
        assert claims.local_user_id == user_id

    def test_claims_are_frozen(self):
        """Should be immutable (frozen dataclass)"""
        now = datetime.now(timezone.utc)
        claims = IdentityClaims(
            provider=AuthProvider.LOCAL,
            provider_user_id="user-123",
            auth_method=AuthMethod.PASSWORD,
            email="test@example.com",
            email_verified=True,
            username=None,
            first_name=None,
            last_name=None,
            avatar_url=None,
            session_id=None,
            issued_at=now,
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

        with pytest.raises(Exception):  # FrozenInstanceError
            claims.email = "new@example.com"


class TestProviderConfig:
    """Tests for ProviderConfig dataclass"""

    def test_create_local_config(self):
        """Should create local provider config"""
        config = ProviderConfig(
            provider=AuthProvider.LOCAL,
            enabled=True,
        )

        assert config.provider == AuthProvider.LOCAL
        assert config.enabled is True
        assert config.clerk_secret_key is None
        assert config.workos_api_key is None

    def test_create_clerk_config(self):
        """Should create Clerk provider config"""
        config = ProviderConfig(
            provider=AuthProvider.CLERK,
            enabled=True,
            clerk_publishable_key="pk_test_123",
            clerk_secret_key="sk_test_456",
            clerk_webhook_secret="whsec_789",
        )

        assert config.provider == AuthProvider.CLERK
        assert config.clerk_publishable_key == "pk_test_123"
        assert config.clerk_secret_key == "sk_test_456"
        assert config.clerk_webhook_secret == "whsec_789"

    def test_create_workos_config(self):
        """Should create WorkOS provider config"""
        config = ProviderConfig(
            provider=AuthProvider.WORKOS,
            enabled=True,
            workos_api_key="sk_workos_123",
            workos_client_id="client_456",
            workos_webhook_secret="whsec_workos_789",
        )

        assert config.provider == AuthProvider.WORKOS
        assert config.workos_api_key == "sk_workos_123"
        assert config.workos_client_id == "client_456"


class TestIdentityModels:
    """Tests for Pydantic identity models"""

    def test_identity_claims_response(self):
        """Should create IdentityClaimsResponse"""
        from app.identity.models import IdentityClaimsResponse

        now = datetime.now(timezone.utc)
        response = IdentityClaimsResponse(
            provider=AuthProvider.LOCAL,
            provider_user_id="user-123",
            auth_method=AuthMethod.PASSWORD,
            email="test@example.com",
            email_verified=True,
            issued_at=now,
        )

        assert response.provider == AuthProvider.LOCAL
        assert response.email == "test@example.com"
        assert response.username is None
        assert response.local_user_id is None

    def test_user_sync_request(self):
        """Should create UserSyncRequest"""
        from app.identity.models import IdentityClaimsResponse, UserSyncRequest

        now = datetime.now(timezone.utc)
        claims = IdentityClaimsResponse(
            provider=AuthProvider.CLERK,
            provider_user_id="clerk_123",
            auth_method=AuthMethod.SOCIAL_OAUTH,
            email="user@example.com",
            email_verified=True,
            issued_at=now,
        )

        request = UserSyncRequest(
            claims=claims,
            create_if_missing=True,
            update_profile=False,
        )

        assert request.claims.provider == AuthProvider.CLERK
        assert request.create_if_missing is True
        assert request.update_profile is False

    def test_user_sync_response(self):
        """Should create UserSyncResponse"""
        from app.identity.models import UserSyncResponse

        user_id = uuid4()
        response = UserSyncResponse(
            local_user_id=user_id,
            created=True,
            updated=False,
            provider_linked=True,
        )

        assert response.local_user_id == user_id
        assert response.created is True
        assert response.provider_linked is True

    def test_provider_link_response(self):
        """Should create ProviderLinkResponse"""
        from app.identity.models import ProviderLinkResponse

        now = datetime.now(timezone.utc)
        link_id = uuid4()
        user_id = uuid4()

        response = ProviderLinkResponse(
            id=link_id,
            user_id=user_id,
            provider=AuthProvider.CLERK,
            provider_user_id="clerk_user_123",
            created_at=now,
        )

        assert response.id == link_id
        assert response.provider == AuthProvider.CLERK

    def test_provider_info_response(self):
        """Should create ProviderInfoResponse"""
        from app.identity.models import ProviderInfoResponse

        response = ProviderInfoResponse(
            provider=AuthProvider.CLERK,
            enabled=True,
            display_name="Clerk",
            supports_sso=False,
            supports_social=True,
        )

        assert response.provider == AuthProvider.CLERK
        assert response.supports_social is True


class TestProviderFactory:
    """Tests for provider factory functions"""

    def test_get_auth_provider_local(self):
        """Should return LocalAuthProvider for local mode"""
        from app.identity.factory import get_auth_provider
        from app.identity.providers.local import LocalAuthProvider

        with patch("app.identity.factory.settings") as mock_settings:
            mock_settings.auth_provider = "local"

            provider = get_auth_provider()

            assert isinstance(provider, LocalAuthProvider)
            assert provider.config.provider == AuthProvider.LOCAL

    def test_get_auth_provider_cloud(self):
        """Should return ClerkAuthProvider for cloud mode"""
        from app.identity.factory import get_auth_provider
        from app.identity.providers.clerk import ClerkAuthProvider

        with patch("app.identity.factory.settings") as mock_settings:
            mock_settings.auth_provider = "cloud"
            mock_settings.clerk_publishable_key = "pk_test_123"
            mock_settings.clerk_secret_key = "sk_test_456"
            mock_settings.clerk_webhook_secret = "whsec_789"

            provider = get_auth_provider()

            assert isinstance(provider, ClerkAuthProvider)
            assert provider.config.provider == AuthProvider.CLERK

    def test_get_auth_provider_invalid(self):
        """Should raise ValueError for invalid provider"""
        from app.identity.factory import get_auth_provider

        with patch("app.identity.factory.settings") as mock_settings:
            mock_settings.auth_provider = "invalid"

            with pytest.raises(ValueError) as exc_info:
                get_auth_provider()

            assert "Unknown auth provider" in str(exc_info.value)

    def test_get_provider_singleton(self):
        """Should return same instance on multiple calls"""
        from app.identity.factory import get_provider, reset_provider

        # Reset to ensure clean state
        reset_provider()

        with patch("app.identity.factory.settings") as mock_settings:
            mock_settings.auth_provider = "local"

            provider1 = get_provider()
            provider2 = get_provider()

            assert provider1 is provider2

        # Clean up
        reset_provider()

    def test_reset_provider(self):
        """Should reset singleton instance"""
        from app.identity.factory import get_provider, reset_provider

        with patch("app.identity.factory.settings") as mock_settings:
            mock_settings.auth_provider = "local"

            provider1 = get_provider()
            reset_provider()
            provider2 = get_provider()

            assert provider1 is not provider2

        # Clean up
        reset_provider()

    def test_get_workos_provider_not_implemented(self):
        """Should raise NotImplementedError for WorkOS"""
        from app.identity.factory import get_workos_provider

        with pytest.raises(NotImplementedError) as exc_info:
            get_workos_provider()

        assert "WorkOS provider" in str(exc_info.value)


class TestLocalAuthProvider:
    """Tests for LocalAuthProvider"""

    def test_init(self):
        """Should initialize with config"""
        from app.identity.providers.local import LocalAuthProvider

        config = ProviderConfig(
            provider=AuthProvider.LOCAL,
            enabled=True,
        )

        provider = LocalAuthProvider(config)

        assert provider.config == config

    async def test_validate_token_invalid(self):
        """Should return None for invalid token"""
        from app.identity.providers.local import LocalAuthProvider

        config = ProviderConfig(provider=AuthProvider.LOCAL, enabled=True)
        provider = LocalAuthProvider(config)

        result = await provider.validate_token("invalid-token")

        assert result is None

    async def test_validate_token_expired(self):
        """Should return None for expired token"""
        import jwt

        from app.config import settings
        from app.identity.providers.local import LocalAuthProvider

        config = ProviderConfig(provider=AuthProvider.LOCAL, enabled=True)
        provider = LocalAuthProvider(config)

        # Create expired token
        expired_payload = {
            "sub": "user-123",
            "username": "testuser",
            "role": "member",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        }
        expired_token = jwt.encode(
            expired_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )

        result = await provider.validate_token(expired_token)

        assert result is None

    async def test_validate_session_no_auth_header(self):
        """Should return None when no Authorization header"""
        from app.identity.providers.local import LocalAuthProvider

        config = ProviderConfig(provider=AuthProvider.LOCAL, enabled=True)
        provider = LocalAuthProvider(config)

        mock_request = MagicMock()
        mock_request.headers.get.return_value = ""

        result = await provider.validate_session(mock_request)

        assert result is None

    async def test_validate_session_with_bearer_token(self):
        """Should validate token from Authorization header"""
        from app.identity.providers.local import LocalAuthProvider

        config = ProviderConfig(provider=AuthProvider.LOCAL, enabled=True)
        provider = LocalAuthProvider(config)

        mock_request = MagicMock()
        mock_request.headers.get.return_value = "Bearer invalid-token"

        result = await provider.validate_session(mock_request)

        assert result is None  # Invalid token returns None

    async def test_handle_webhook(self):
        """Should return not_applicable for webhooks"""
        from app.identity.providers.local import LocalAuthProvider

        config = ProviderConfig(provider=AuthProvider.LOCAL, enabled=True)
        provider = LocalAuthProvider(config)

        mock_request = MagicMock()
        result = await provider.handle_webhook(mock_request)

        assert result["status"] == "not_applicable"

    async def test_get_login_url(self):
        """Should return login URL with redirect"""
        from app.identity.providers.local import LocalAuthProvider

        config = ProviderConfig(provider=AuthProvider.LOCAL, enabled=True)
        provider = LocalAuthProvider(config)

        url = await provider.get_login_url("/dashboard")

        assert url == "/login?redirect=/dashboard"

    async def test_get_logout_url(self):
        """Should return logout URL with redirect"""
        from app.identity.providers.local import LocalAuthProvider

        config = ProviderConfig(provider=AuthProvider.LOCAL, enabled=True)
        provider = LocalAuthProvider(config)

        url = await provider.get_logout_url("/")

        assert url == "/logout?redirect=/"

    async def test_revoke_session(self):
        """Should return True (JWT is stateless)"""
        from app.identity.providers.local import LocalAuthProvider

        config = ProviderConfig(provider=AuthProvider.LOCAL, enabled=True)
        provider = LocalAuthProvider(config)

        result = await provider.revoke_session("any-session-id")

        assert result is True

    def test_user_to_claims(self):
        """Should convert user and JWT payload to IdentityClaims"""
        from app.identity.providers.local import LocalAuthProvider

        config = ProviderConfig(provider=AuthProvider.LOCAL, enabled=True)
        provider = LocalAuthProvider(config)

        user_id = str(uuid4())
        now = datetime.now(timezone.utc)

        # Mock user
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = "test@example.com"
        mock_user.is_verified = True
        mock_user.username = "testuser"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"

        # JWT payload
        jwt_payload = {
            "sub": user_id,
            "username": "testuser",
            "role": "member",
            "exp": int((now + timedelta(hours=24)).timestamp()),
            "iat": int(now.timestamp()),
        }

        result = provider._user_to_claims(mock_user, jwt_payload)

        assert result.provider == AuthProvider.LOCAL
        assert result.provider_user_id == user_id
        assert result.auth_method == AuthMethod.PASSWORD
        assert result.email == "test@example.com"
        assert result.email_verified is True
        assert result.username == "testuser"
        assert result.first_name == "Test"
        assert result.last_name == "User"
        assert str(result.local_user_id) == user_id


class TestUserSync:
    """Tests for user sync service"""

    async def test_sync_provider_user_existing_link(self):
        """Should update user when provider link exists"""
        from app.identity.sync import sync_provider_user

        now = datetime.now(timezone.utc)
        claims = IdentityClaims(
            provider=AuthProvider.CLERK,
            provider_user_id="clerk_123",
            auth_method=AuthMethod.PASSWORD,
            email="test@example.com",
            email_verified=True,
            username="testuser",
            first_name="Updated",
            last_name="Name",
            avatar_url="https://example.com/clerk-avatar.jpg",
            session_id=None,
            issued_at=now,
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

        # Mock DB session
        mock_db = AsyncMock()
        mock_link = MagicMock()
        mock_link.user_id = str(uuid4())

        mock_user = MagicMock()
        mock_user.first_name = "Old"
        mock_user.last_name = "Name"

        # Setup execute to return link, then user
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = mock_link

        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = mock_user

        mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_result2])
        mock_db.commit = AsyncMock()

        user_id, created, updated = await sync_provider_user(mock_db, claims)

        assert user_id is not None
        assert created is False
        assert updated is True
        assert mock_user.avatar_url == "https://example.com/clerk-avatar.jpg"

    async def test_sync_provider_user_no_link_email_match(self):
        """Should create link when user exists with matching email"""
        from app.identity.sync import sync_provider_user

        now = datetime.now(timezone.utc)
        claims = IdentityClaims(
            provider=AuthProvider.CLERK,
            provider_user_id="clerk_123",
            auth_method=AuthMethod.PASSWORD,
            email="existing@example.com",
            email_verified=True,
            username="newuser",
            first_name="Test",
            last_name="User",
            avatar_url=None,
            session_id=None,
            issued_at=now,
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

        # Mock DB session
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = str(uuid4())
        mock_user.first_name = "Existing"

        # No existing link
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = None

        # Existing user by email
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = mock_user

        mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_result2])
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        user_id, created, updated = await sync_provider_user(mock_db, claims)

        assert user_id is not None
        assert created is False
        assert updated is True
        mock_db.add.assert_called_once()  # ProviderLink added

    async def test_sync_manual_signup_then_oauth_same_email(self):
        """Should link OAuth to manually created account with same email (case-insensitive)."""
        from app.identity.sync import sync_provider_user

        now = datetime.now(timezone.utc)
        # OAuth claims with mixed-case email (as might come from Google)
        claims = IdentityClaims(
            provider=AuthProvider.CLERK,
            provider_user_id="clerk_google_456",
            auth_method=AuthMethod.SOCIAL_OAUTH,
            email="User@Gmail.com",
            email_verified=True,
            username=None,
            first_name="Test",
            last_name="User",
            avatar_url=None,
            session_id=None,
            issued_at=now,
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

        mock_db = AsyncMock()
        # Simulate a manually-created user (no ProviderLink)
        existing_user = MagicMock()
        existing_user.id = str(uuid4())
        existing_user.email = "user@gmail.com"  # stored lowercase from manual signup
        existing_user.first_name = "Manual"

        # No existing provider link
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = None

        # Email match found (case-insensitive via func.lower)
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = existing_user

        mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_result2])
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        user_id, created, updated = await sync_provider_user(mock_db, claims)

        assert str(user_id) == existing_user.id
        assert created is False  # Should NOT create a new user
        mock_db.add.assert_called_once()  # Should add ProviderLink only

    async def test_sync_empty_email_skips_match(self):
        """Should skip email matching and create new user when email is empty."""
        from app.identity.sync import sync_provider_user

        now = datetime.now(timezone.utc)
        claims = IdentityClaims(
            provider=AuthProvider.CLERK,
            provider_user_id="clerk_no_email",
            auth_method=AuthMethod.SOCIAL_OAUTH,
            email="",
            email_verified=False,
            username="noemailer",
            first_name="No",
            last_name="Email",
            avatar_url=None,
            session_id=None,
            issued_at=now,
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

        mock_db = AsyncMock()

        # No existing link
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = None

        # Username check for _create_new_user (no existing username)
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_result2])
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()

        user_id, created, updated = await sync_provider_user(mock_db, claims)

        assert user_id is not None
        assert created is True
        # Should only have 1 execute call for provider link check
        # No email match query since email is empty
        # Username check happens inside _create_new_user via _get_unique_username
        # but the first execute is the provider link check
        assert mock_db.execute.call_count >= 1

    async def test_sync_integrity_error_falls_back_to_link(self):
        """Should fall back to linking existing user when create fails with IntegrityError."""
        from sqlalchemy.exc import IntegrityError

        from app.identity.sync import sync_provider_user

        now = datetime.now(timezone.utc)
        claims = IdentityClaims(
            provider=AuthProvider.CLERK,
            provider_user_id="clerk_race_789",
            auth_method=AuthMethod.SOCIAL_OAUTH,
            email="race@example.com",
            email_verified=True,
            username=None,
            first_name="Race",
            last_name="Condition",
            avatar_url=None,
            session_id=None,
            issued_at=now,
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

        mock_db = AsyncMock()
        existing_user = MagicMock()
        existing_user.id = str(uuid4())
        existing_user.first_name = "Existing"

        # No existing link
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = None

        # No email match on first check (race condition: user created between check and insert)
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = None

        # Username check
        mock_result3 = MagicMock()
        mock_result3.scalar_one_or_none.return_value = None

        # After rollback, email match finds the user
        mock_result4 = MagicMock()
        mock_result4.scalar_one_or_none.return_value = existing_user

        mock_db.execute = AsyncMock(
            side_effect=[mock_result1, mock_result2, mock_result3, mock_result4]
        )
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock(side_effect=IntegrityError("", {}, Exception("duplicate key")))
        mock_db.rollback = AsyncMock()
        mock_db.commit = AsyncMock()

        user_id, created, updated = await sync_provider_user(mock_db, claims)

        assert str(user_id) == existing_user.id
        assert created is False  # Fell back to linking, not creating
        mock_db.rollback.assert_called_once()

    async def test_sync_provider_user_create_new(self):
        """Should create new user when no match found"""
        from app.identity.sync import sync_provider_user

        now = datetime.now(timezone.utc)
        claims = IdentityClaims(
            provider=AuthProvider.CLERK,
            provider_user_id="clerk_new_123",
            auth_method=AuthMethod.PASSWORD,
            email="newuser@example.com",
            email_verified=True,
            username=None,  # Will be derived from email
            first_name="New",
            last_name="User",
            avatar_url="https://example.com/new-avatar.jpg",
            session_id=None,
            issued_at=now,
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

        # Mock DB session
        mock_db = AsyncMock()

        # No existing link
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = None

        # No existing user by email
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = None

        # No existing user by username
        mock_result3 = MagicMock()
        mock_result3.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_result2, mock_result3])
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()

        user_id, created, updated = await sync_provider_user(mock_db, claims)

        assert user_id is not None
        assert created is True
        assert updated is False
        assert mock_db.add.call_count == 2  # User + ProviderLink
        created_user = mock_db.add.call_args_list[0].args[0]
        assert created_user.avatar_url == "https://example.com/new-avatar.jpg"

    async def test_sync_provider_user_no_create(self):
        """Should return None when user not found and create_if_missing=False"""
        from app.identity.sync import sync_provider_user

        now = datetime.now(timezone.utc)
        claims = IdentityClaims(
            provider=AuthProvider.CLERK,
            provider_user_id="clerk_123",
            auth_method=AuthMethod.PASSWORD,
            email="notfound@example.com",
            email_verified=True,
            username="notfound",
            first_name=None,
            last_name=None,
            avatar_url=None,
            session_id=None,
            issued_at=now,
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

        # Mock DB session
        mock_db = AsyncMock()

        # No existing link
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = None

        # No existing user
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_result2])

        user_id, created, updated = await sync_provider_user(
            mock_db, claims, create_if_missing=False
        )

        assert user_id is None
        assert created is False
        assert updated is False

    async def test_deactivate_provider_user(self):
        """Should deactivate user when provider link found"""
        from app.identity.sync import deactivate_provider_user

        mock_db = AsyncMock()
        mock_link = MagicMock()
        mock_link.user_id = str(uuid4())

        mock_user = MagicMock()
        mock_user.is_active = True

        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = mock_link

        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = mock_user

        mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_result2])
        mock_db.commit = AsyncMock()

        result = await deactivate_provider_user(mock_db, AuthProvider.CLERK, "clerk_123")

        assert result is True
        assert mock_user.is_active is False

    async def test_deactivate_provider_user_not_found(self):
        """Should return False when provider link not found"""
        from app.identity.sync import deactivate_provider_user

        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await deactivate_provider_user(mock_db, AuthProvider.CLERK, "nonexistent")

        assert result is False

    async def test_get_provider_links(self):
        """Should return list of provider links for user"""
        from app.identity.sync import get_provider_links

        mock_db = AsyncMock()
        mock_links = [MagicMock(), MagicMock()]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_links

        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await get_provider_links(mock_db, "user-123")

        assert len(result) == 2

    async def test_link_provider_new(self):
        """Should create new provider link"""
        from app.identity.sync import link_provider

        mock_db = AsyncMock()

        # No existing link
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        await link_provider(mock_db, "user-123", AuthProvider.CLERK, "clerk_456")

        mock_db.add.assert_called_once()

    async def test_link_provider_already_linked_same_user(self):
        """Should return existing link if already linked to same user"""
        from app.identity.sync import link_provider

        mock_db = AsyncMock()
        mock_existing = MagicMock()
        mock_existing.user_id = "user-123"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing

        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await link_provider(mock_db, "user-123", AuthProvider.CLERK, "clerk_456")

        assert result == mock_existing

    async def test_link_provider_already_linked_different_user(self):
        """Should raise ValueError if linked to different user"""
        from app.identity.sync import link_provider

        mock_db = AsyncMock()
        mock_existing = MagicMock()
        mock_existing.user_id = "different-user-456"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_existing

        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError) as exc_info:
            await link_provider(mock_db, "user-123", AuthProvider.CLERK, "clerk_456")

        assert "already linked to another user" in str(exc_info.value)

    async def test_unlink_provider(self):
        """Should unlink provider from user"""
        from app.identity.sync import unlink_provider

        mock_db = AsyncMock()
        mock_link = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_link

        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        result = await unlink_provider(mock_db, "user-123", AuthProvider.CLERK)

        assert result is True
        mock_db.delete.assert_called_once_with(mock_link)

    async def test_unlink_provider_not_found(self):
        """Should return False when link not found"""
        from app.identity.sync import unlink_provider

        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await unlink_provider(mock_db, "user-123", AuthProvider.CLERK)

        assert result is False


class TestClerkAuthProvider:
    """Tests for ClerkAuthProvider"""

    def test_init(self):
        """Should initialize with config"""
        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(
            provider=AuthProvider.CLERK,
            enabled=True,
            clerk_publishable_key="pk_test_123",
            clerk_secret_key="sk_test_456",
            clerk_webhook_secret="whsec_789",
        )

        provider = ClerkAuthProvider(config)

        assert provider.config == config
        assert provider.secret_key == "sk_test_456"
        assert provider.publishable_key == "pk_test_123"

    async def test_validate_token_no_secret_key(self):
        """Should return None when secret key not configured"""
        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(
            provider=AuthProvider.CLERK,
            enabled=True,
            clerk_secret_key=None,
        )
        provider = ClerkAuthProvider(config)

        result = await provider.validate_token("some-token")

        assert result is None

    async def test_validate_token_api_error(self):
        """Should return None on API error"""
        import base64
        import json

        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(
            provider=AuthProvider.CLERK,
            enabled=True,
            clerk_secret_key="sk_test_123",
        )
        provider = ClerkAuthProvider(config)

        # Create a mock JWT token with session ID (sid) claim
        header = base64.urlsafe_b64encode(json.dumps({"alg": "RS256"}).encode()).rstrip(b"=")
        payload = base64.urlsafe_b64encode(
            json.dumps({"sid": "sess_123", "sub": "user_456"}).encode()
        ).rstrip(b"=")
        signature = base64.urlsafe_b64encode(b"fake-signature").rstrip(b"=")
        mock_jwt = f"{header.decode()}.{payload.decode()}.{signature.decode()}"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_client.post.return_value = mock_response

            result = await provider.validate_token(mock_jwt)

            assert result is None

    async def test_validate_token_success(self):
        """Should return IdentityClaims on successful validation"""
        import base64
        import json
        import time

        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(
            provider=AuthProvider.CLERK,
            enabled=True,
            clerk_secret_key="sk_test_123",
        )
        provider = ClerkAuthProvider(config)

        user_data = {
            "id": "user_456",
            "email_addresses": [
                {
                    "id": "email_1",
                    "email_address": "test@example.com",
                    "verification": {"status": "verified"},
                }
            ],
            "primary_email_address_id": "email_1",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "image_url": "https://example.com/avatar.jpg",
            "public_metadata": {"role": "admin"},
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock user fetch response
            mock_user_response = MagicMock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = user_data

            mock_client.get.return_value = mock_user_response

            # Create a mock JWT token with required claims
            now = int(time.time())
            header = base64.urlsafe_b64encode(json.dumps({"alg": "RS256"}).encode()).rstrip(b"=")
            payload = base64.urlsafe_b64encode(
                json.dumps(
                    {
                        "sid": "sess_123",
                        "sub": "user_456",
                        "iat": now,
                        "exp": now + 3600,  # 1 hour from now
                    }
                ).encode()
            ).rstrip(b"=")
            signature = base64.urlsafe_b64encode(b"fake-signature").rstrip(b"=")
            mock_jwt = f"{header.decode()}.{payload.decode()}.{signature.decode()}"

            result = await provider.validate_token(mock_jwt)

            assert result is not None
            assert result.provider == AuthProvider.CLERK
            assert result.provider_user_id == "user_456"
            assert result.email == "test@example.com"
            assert result.email_verified is True
            assert result.username == "testuser"
            assert result.first_name == "Test"
            assert result.last_name == "User"

    async def test_validate_session_from_cookie(self):
        """Should validate session from cookie"""
        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(
            provider=AuthProvider.CLERK,
            enabled=True,
            clerk_secret_key="sk_test_123",
        )
        provider = ClerkAuthProvider(config)

        mock_request = MagicMock()
        mock_request.cookies.get.return_value = "session-token"
        mock_request.headers.get.return_value = ""

        with patch.object(provider, "validate_token", new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = None

            await provider.validate_session(mock_request)

            mock_validate.assert_called_once_with("session-token")

    async def test_validate_session_from_header(self):
        """Should validate session from Authorization header"""
        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(
            provider=AuthProvider.CLERK,
            enabled=True,
            clerk_secret_key="sk_test_123",
        )
        provider = ClerkAuthProvider(config)

        mock_request = MagicMock()
        mock_request.cookies.get.return_value = None
        mock_request.headers.get.return_value = "Bearer header-token"

        with patch.object(provider, "validate_token", new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = None

            await provider.validate_session(mock_request)

            mock_validate.assert_called_once_with("header-token")

    async def test_validate_session_no_credentials(self):
        """Should return None when no credentials present"""
        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(
            provider=AuthProvider.CLERK,
            enabled=True,
            clerk_secret_key="sk_test_123",
        )
        provider = ClerkAuthProvider(config)

        mock_request = MagicMock()
        mock_request.cookies.get.return_value = None
        mock_request.headers.get.return_value = ""

        result = await provider.validate_session(mock_request)

        assert result is None

    def test_get_auth_method_password(self):
        """Should return PASSWORD for password strategy"""
        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(provider=AuthProvider.CLERK, enabled=True)
        provider = ClerkAuthProvider(config)

        result = provider._get_auth_method({"authentication_strategy": "password"})

        assert result == AuthMethod.PASSWORD

    def test_get_auth_method_oauth(self):
        """Should return SOCIAL_OAUTH for oauth strategy"""
        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(provider=AuthProvider.CLERK, enabled=True)
        provider = ClerkAuthProvider(config)

        result = provider._get_auth_method({"authentication_strategy": "oauth_google"})

        assert result == AuthMethod.SOCIAL_OAUTH

    def test_get_auth_method_passkey(self):
        """Should return PASSKEY for passkey strategy"""
        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(provider=AuthProvider.CLERK, enabled=True)
        provider = ClerkAuthProvider(config)

        result = provider._get_auth_method({"authentication_strategy": "passkey"})

        assert result == AuthMethod.PASSKEY

    def test_get_auth_method_magic_link(self):
        """Should return MAGIC_LINK for email_link strategy"""
        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(provider=AuthProvider.CLERK, enabled=True)
        provider = ClerkAuthProvider(config)

        result = provider._get_auth_method({"authentication_strategy": "email_link"})

        assert result == AuthMethod.MAGIC_LINK

    def test_data_to_claims(self):
        """Should convert Clerk webhook data to IdentityClaims"""
        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(provider=AuthProvider.CLERK, enabled=True)
        provider = ClerkAuthProvider(config)

        data = {
            "id": "user_123",
            "email_addresses": [
                {
                    "id": "email_1",
                    "email_address": "test@example.com",
                    "verification": {"status": "verified"},
                }
            ],
            "primary_email_address_id": "email_1",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "image_url": "https://example.com/avatar.jpg",
            "public_metadata": {"role": "admin"},
        }

        result = provider.data_to_claims(data)

        assert result.provider == AuthProvider.CLERK
        assert result.provider_user_id == "user_123"
        assert result.email == "test@example.com"
        assert result.email_verified is True
        assert result.username == "testuser"
        assert result.first_name == "Test"
        assert result.last_name == "User"

    async def test_get_login_url(self):
        """Should return login URL with redirect"""
        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(provider=AuthProvider.CLERK, enabled=True)
        provider = ClerkAuthProvider(config)

        url = await provider.get_login_url("/dashboard")

        assert url == "/sign-in?redirect_url=/dashboard"

    async def test_get_logout_url(self):
        """Should return logout URL with redirect"""
        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(provider=AuthProvider.CLERK, enabled=True)
        provider = ClerkAuthProvider(config)

        url = await provider.get_logout_url("/")

        assert url == "/sign-out?redirect_url=/"

    async def test_revoke_session_no_secret_key(self):
        """Should return False when secret key not configured"""
        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(
            provider=AuthProvider.CLERK,
            enabled=True,
            clerk_secret_key=None,
        )
        provider = ClerkAuthProvider(config)

        result = await provider.revoke_session("session-123")

        assert result is False

    async def test_revoke_session_success(self):
        """Should return True on successful revocation"""
        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(
            provider=AuthProvider.CLERK,
            enabled=True,
            clerk_secret_key="sk_test_123",
        )
        provider = ClerkAuthProvider(config)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response

            result = await provider.revoke_session("session-123")

            assert result is True

    async def test_get_user_by_id_no_secret_key(self):
        """Should return None when secret key not configured"""
        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(
            provider=AuthProvider.CLERK,
            enabled=True,
            clerk_secret_key=None,
        )
        provider = ClerkAuthProvider(config)

        result = await provider.get_user_by_id("user-123")

        assert result is None

    async def test_get_user_by_id_success(self):
        """Should return user data on success"""
        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(
            provider=AuthProvider.CLERK,
            enabled=True,
            clerk_secret_key="sk_test_123",
        )
        provider = ClerkAuthProvider(config)

        user_data = {"id": "user_123", "email": "test@example.com"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = user_data
            mock_client.get.return_value = mock_response

            result = await provider.get_user_by_id("user-123")

            assert result == user_data

    async def test_get_user_by_id_not_found(self):
        """Should return None when user not found (404)"""
        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(
            provider=AuthProvider.CLERK,
            enabled=True,
            clerk_secret_key="sk_test_123",
        )
        provider = ClerkAuthProvider(config)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_client.get.return_value = mock_response

            result = await provider.get_user_by_id("nonexistent-user")

            assert result is None

    async def test_get_user_by_id_request_error(self):
        """Should return None on request error"""
        import httpx

        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(
            provider=AuthProvider.CLERK,
            enabled=True,
            clerk_secret_key="sk_test_123",
        )
        provider = ClerkAuthProvider(config)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.RequestError("Connection failed")

            result = await provider.get_user_by_id("user-123")

            assert result is None

    async def test_revoke_session_request_error(self):
        """Should return False on request error"""
        import httpx

        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(
            provider=AuthProvider.CLERK,
            enabled=True,
            clerk_secret_key="sk_test_123",
        )
        provider = ClerkAuthProvider(config)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.RequestError("Connection failed")

            result = await provider.revoke_session("session-123")

            assert result is False

    async def test_revoke_session_non_200(self):
        """Should return False on non-200 response"""
        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(
            provider=AuthProvider.CLERK,
            enabled=True,
            clerk_secret_key="sk_test_123",
        )
        provider = ClerkAuthProvider(config)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_client.post.return_value = mock_response

            result = await provider.revoke_session("nonexistent-session")

            assert result is False

    async def test_validate_token_no_user_id_in_response(self):
        """Should return None when no user_id in session response"""
        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(
            provider=AuthProvider.CLERK,
            enabled=True,
            clerk_secret_key="sk_test_123",
        )
        provider = ClerkAuthProvider(config)

        session_data = {
            "id": "sess_123",
            # user_id is missing
            "created_at": 1700000000000,
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_session_response = MagicMock()
            mock_session_response.status_code = 200
            mock_session_response.json.return_value = session_data

            mock_client.post.return_value = mock_session_response

            result = await provider.validate_token("token-without-user")

            assert result is None

    async def test_validate_token_user_fetch_fails(self):
        """Should return None when user fetch fails after session verification"""
        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(
            provider=AuthProvider.CLERK,
            enabled=True,
            clerk_secret_key="sk_test_123",
        )
        provider = ClerkAuthProvider(config)

        session_data = {
            "id": "sess_123",
            "user_id": "user_456",
            "created_at": 1700000000000,
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_session_response = MagicMock()
            mock_session_response.status_code = 200
            mock_session_response.json.return_value = session_data

            mock_user_response = MagicMock()
            mock_user_response.status_code = 404

            mock_client.post.return_value = mock_session_response
            mock_client.get.return_value = mock_user_response

            result = await provider.validate_token("valid-session-but-no-user")

            assert result is None

    async def test_validate_token_request_error(self):
        """Should return None on httpx RequestError"""
        import httpx

        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(
            provider=AuthProvider.CLERK,
            enabled=True,
            clerk_secret_key="sk_test_123",
        )
        provider = ClerkAuthProvider(config)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.RequestError("Connection timeout")

            result = await provider.validate_token("some-token")

            assert result is None

    async def test_handle_webhook_no_secret(self):
        """Should return error when webhook secret not configured"""
        import sys

        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(
            provider=AuthProvider.CLERK,
            enabled=True,
            clerk_secret_key="sk_test_123",
            clerk_webhook_secret=None,
        )
        provider = ClerkAuthProvider(config)

        mock_request = MagicMock()

        # Mock svix module
        mock_svix = MagicMock()
        with patch.dict(sys.modules, {"svix": mock_svix}):
            result = await provider.handle_webhook(mock_request)

            assert "error" in result
            assert "not configured" in result["error"]

    async def test_handle_webhook_invalid_signature(self):
        """Should return error on invalid signature"""
        import sys

        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(
            provider=AuthProvider.CLERK,
            enabled=True,
            clerk_secret_key="sk_test_123",
            clerk_webhook_secret="whsec_test",
        )
        provider = ClerkAuthProvider(config)

        mock_request = MagicMock()
        mock_request.headers.get.return_value = ""
        mock_request.body = AsyncMock(return_value=b"{}")

        class MockWebhookVerificationError(Exception):
            pass

        mock_webhook = MagicMock()
        mock_webhook.verify.side_effect = MockWebhookVerificationError("Invalid")

        mock_svix = MagicMock()
        mock_svix.Webhook.return_value = mock_webhook
        mock_svix.WebhookVerificationError = MockWebhookVerificationError

        with patch.dict(sys.modules, {"svix": mock_svix}):
            result = await provider.handle_webhook(mock_request)

            assert "error" in result
            assert "Invalid signature" in result["error"]

    async def test_handle_webhook_success(self):
        """Should return payload on successful verification"""
        from app.identity.providers.clerk import ClerkAuthProvider

        config = ProviderConfig(
            provider=AuthProvider.CLERK,
            enabled=True,
            clerk_secret_key="sk_test_123",
            clerk_webhook_secret="whsec_test",
        )
        provider = ClerkAuthProvider(config)

        mock_request = MagicMock()
        mock_request.headers.get.return_value = ""
        mock_request.body = AsyncMock(return_value=b"{}")

        mock_webhook = MagicMock()
        mock_webhook.verify.return_value = {
            "type": "user.created",
            "data": {"id": "user_123"},
        }

        with patch("app.identity.providers.clerk.svix.Webhook", return_value=mock_webhook):
            result = await provider.handle_webhook(mock_request)

            assert result["received"] is True
            assert result["type"] == "user.created"
            assert result["data"]["id"] == "user_123"


class TestLocalAuthProviderValidateTokenSuccess:
    """Tests for LocalAuthProvider validate_token success path"""

    async def test_validate_token_success(self):
        """Should return IdentityClaims for valid token with active user"""
        import jwt

        from app.config import settings
        from app.identity.providers.local import LocalAuthProvider

        config = ProviderConfig(provider=AuthProvider.LOCAL, enabled=True)
        provider = LocalAuthProvider(config)

        user_id = str(uuid4())
        now = datetime.now(timezone.utc)

        # Create valid token
        valid_payload = {
            "sub": user_id,
            "username": "testuser",
            "role": "member",
            "exp": now + timedelta(hours=24),
            "iat": now,
        }
        valid_token = jwt.encode(
            valid_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )

        # Mock user
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = "test@example.com"
        mock_user.is_verified = True
        mock_user.is_active = True
        mock_user.username = "testuser"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"

        # Mock database session context manager
        mock_db = AsyncMock()

        # Create a proper async context manager
        class MockSessionMaker:
            def __call__(self):
                return self

            async def __aenter__(self):
                return mock_db

            async def __aexit__(self, *args):
                pass

        mock_auth = MagicMock()
        mock_auth.get_user = AsyncMock(return_value=mock_user)

        with (
            patch("app.database.async_session_maker", MockSessionMaker()),
            patch("app.services.auth_service.auth_service", mock_auth),
        ):
            result = await provider.validate_token(valid_token)

            assert result is not None
            assert result.provider == AuthProvider.LOCAL
            assert result.provider_user_id == user_id
            assert result.email == "test@example.com"
            assert result.username == "testuser"

    async def test_validate_token_inactive_user(self):
        """Should return None for inactive user"""
        import jwt

        from app.config import settings
        from app.identity.providers.local import LocalAuthProvider

        config = ProviderConfig(provider=AuthProvider.LOCAL, enabled=True)
        provider = LocalAuthProvider(config)

        user_id = str(uuid4())
        now = datetime.now(timezone.utc)

        valid_payload = {
            "sub": user_id,
            "username": "testuser",
            "role": "member",
            "exp": now + timedelta(hours=24),
            "iat": now,
        }
        valid_token = jwt.encode(
            valid_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )

        # Mock inactive user
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.is_active = False

        mock_db = AsyncMock()

        class MockSessionMaker:
            def __call__(self):
                return self

            async def __aenter__(self):
                return mock_db

            async def __aexit__(self, *args):
                pass

        mock_auth = MagicMock()
        mock_auth.get_user = AsyncMock(return_value=mock_user)

        with (
            patch("app.database.async_session_maker", MockSessionMaker()),
            patch("app.services.auth_service.auth_service", mock_auth),
        ):
            result = await provider.validate_token(valid_token)

            assert result is None

    async def test_validate_token_user_not_found(self):
        """Should return None when user not found"""
        import jwt

        from app.config import settings
        from app.identity.providers.local import LocalAuthProvider

        config = ProviderConfig(provider=AuthProvider.LOCAL, enabled=True)
        provider = LocalAuthProvider(config)

        user_id = str(uuid4())
        now = datetime.now(timezone.utc)

        valid_payload = {
            "sub": user_id,
            "username": "testuser",
            "role": "member",
            "exp": now + timedelta(hours=24),
            "iat": now,
        }
        valid_token = jwt.encode(
            valid_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )

        mock_db = AsyncMock()

        class MockSessionMaker:
            def __call__(self):
                return self

            async def __aenter__(self):
                return mock_db

            async def __aexit__(self, *args):
                pass

        mock_auth = MagicMock()
        mock_auth.get_user = AsyncMock(return_value=None)

        with (
            patch("app.database.async_session_maker", MockSessionMaker()),
            patch("app.services.auth_service.auth_service", mock_auth),
        ):
            result = await provider.validate_token(valid_token)

            assert result is None


class TestModuleExports:
    """Tests for module __init__.py exports"""

    def test_identity_module_exports(self):
        """Should export all public symbols"""
        from app import identity

        # Claims and enums
        assert hasattr(identity, "AuthMethod")
        assert hasattr(identity, "AuthProvider")
        assert hasattr(identity, "IdentityClaims")
        assert hasattr(identity, "ProviderConfig")

        # Factory functions
        assert hasattr(identity, "get_provider")
        assert hasattr(identity, "reset_provider")

        # Pydantic models
        assert hasattr(identity, "IdentityClaimsResponse")
        assert hasattr(identity, "ProviderInfoResponse")
        assert hasattr(identity, "ProviderLinkResponse")
        assert hasattr(identity, "UserSyncRequest")
        assert hasattr(identity, "UserSyncResponse")

        # Provider classes
        assert hasattr(identity, "AuthProviderInterface")
        assert hasattr(identity, "ClerkAuthProvider")
        assert hasattr(identity, "LocalAuthProvider")

        # Sync functions
        assert hasattr(identity, "sync_provider_user")
        assert hasattr(identity, "deactivate_provider_user")
        assert hasattr(identity, "get_provider_links")
        assert hasattr(identity, "link_provider")
        assert hasattr(identity, "unlink_provider")
