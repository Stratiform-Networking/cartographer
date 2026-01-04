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
from uuid import UUID, uuid4

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

    def test_get_auth_provider_cloud_not_implemented(self):
        """Should raise NotImplementedError for cloud mode"""
        from app.identity.factory import get_auth_provider

        with patch("app.identity.factory.settings") as mock_settings:
            mock_settings.auth_provider = "cloud"

            with pytest.raises(NotImplementedError) as exc_info:
                get_auth_provider()

            assert "Cloud auth provider" in str(exc_info.value)

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

        result = await link_provider(mock_db, "user-123", AuthProvider.CLERK, "clerk_456")

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
        assert hasattr(identity, "LocalAuthProvider")

        # Sync functions
        assert hasattr(identity, "sync_provider_user")
        assert hasattr(identity, "deactivate_provider_user")
        assert hasattr(identity, "get_provider_links")
        assert hasattr(identity, "link_provider")
        assert hasattr(identity, "unlink_provider")
