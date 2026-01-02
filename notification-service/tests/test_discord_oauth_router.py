"""
Tests for Discord OAuth Router endpoints.

Tests the API endpoints for Discord OAuth flow including authorization initiation,
callback handling, and link management (get/delete).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.database import get_db


@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.refresh = AsyncMock()
    return mock_db


@pytest.fixture
def test_app(mock_db_session):
    """Create test app with mocked lifespan and database"""
    from app.main import create_app

    with patch("app.main.lifespan"):
        app = create_app()

        # Override the database dependency
        async def override_get_db():
            yield mock_db_session

        app.dependency_overrides[get_db] = override_get_db
        yield app
        app.dependency_overrides.clear()


@pytest.fixture
def test_client(test_app):
    """Create test client"""
    return TestClient(test_app)


class TestDiscordOAuthInitiate:
    """Tests for Discord OAuth initiation endpoint"""

    def test_initiate_discord_oauth_success(self, test_client):
        """Should return authorization URL"""
        with patch("app.routers.discord_oauth.discord_oauth_service") as mock_service:
            mock_service.get_authorization_url.return_value = (
                "https://discord.com/authorize?client_id=123"
            )

            response = test_client.get(
                "/api/auth/discord/link",
                params={
                    "user_id": "user-123",
                    "context_type": "global",
                },
            )

            assert response.status_code == 200
            assert "authorization_url" in response.json()

    def test_initiate_discord_oauth_network_context(self, test_client):
        """Should return authorization URL for network context"""
        with patch("app.routers.discord_oauth.discord_oauth_service") as mock_service:
            mock_service.get_authorization_url.return_value = (
                "https://discord.com/authorize?client_id=123"
            )

            response = test_client.get(
                "/api/auth/discord/link",
                params={
                    "user_id": "user-123",
                    "context_type": "network",
                    "network_id": "network-uuid",
                },
            )

            assert response.status_code == 200

    def test_initiate_discord_oauth_error(self, test_client):
        """Should return 500 on service error"""
        with patch("app.routers.discord_oauth.discord_oauth_service") as mock_service:
            mock_service.get_authorization_url.side_effect = ValueError("Discord not configured")

            response = test_client.get(
                "/api/auth/discord/link",
                params={
                    "user_id": "user-123",
                },
            )

            assert response.status_code == 500


class TestDiscordOAuthCallback:
    """Tests for Discord OAuth callback endpoint"""

    def test_callback_invalid_state(self, test_client):
        """Should redirect with error on invalid state"""
        with patch("app.routers.discord_oauth.discord_oauth_service") as mock_service:
            mock_service.validate_state.return_value = None

            response = test_client.get(
                "/api/auth/discord/callback",
                params={
                    "code": "test-code",
                    "state": "invalid-state",
                },
                follow_redirects=False,
            )

            assert response.status_code == 307
            assert "discord_oauth=error" in response.headers["location"]

    def test_callback_success_global(self, test_client, mock_db_session):
        """Should handle successful OAuth callback for global context"""
        with patch("app.routers.discord_oauth.discord_oauth_service") as mock_service:
            with patch("app.routers.discord_oauth.user_preferences_service") as mock_prefs:
                # Mock state validation
                mock_service.validate_state.return_value = ("user-123", "global", None)

                # Mock token exchange
                mock_service.exchange_code_for_tokens = AsyncMock(
                    return_value={
                        "access_token": "test-token",
                        "refresh_token": "test-refresh",
                        "expires_in": 3600,
                    }
                )

                # Mock user info
                mock_service.get_user_info = AsyncMock(
                    return_value={
                        "id": "discord-123",
                        "username": "testuser",
                        "avatar": None,
                    }
                )

                # Mock link creation
                mock_service.create_or_update_link = AsyncMock(return_value=MagicMock())

                # Mock global prefs
                mock_prefs.get_global_preferences = AsyncMock(return_value=None)

                response = test_client.get(
                    "/api/auth/discord/callback",
                    params={
                        "code": "test-code",
                        "state": "valid-state",
                    },
                    follow_redirects=False,
                )

                # Should redirect
                assert response.status_code == 307

    def test_callback_success_with_existing_global_prefs(self, test_client, mock_db_session):
        """Should handle callback when global prefs exist"""
        with patch("app.routers.discord_oauth.discord_oauth_service") as mock_service:
            with patch("app.routers.discord_oauth.user_preferences_service") as mock_prefs:
                mock_service.validate_state.return_value = ("user-123", "global", None)

                mock_service.exchange_code_for_tokens = AsyncMock(
                    return_value={
                        "access_token": "test-token",
                        "refresh_token": "test-refresh",
                        "expires_in": 3600,
                    }
                )

                mock_service.get_user_info = AsyncMock(
                    return_value={
                        "id": "discord-123",
                        "username": "testuser",
                        "avatar": None,
                    }
                )

                mock_service.create_or_update_link = AsyncMock(return_value=MagicMock())

                # Mock existing global prefs
                mock_existing_prefs = MagicMock()
                mock_existing_prefs.discord_user_id = None
                mock_existing_prefs.discord_enabled = False
                mock_prefs.get_global_preferences = AsyncMock(return_value=mock_existing_prefs)

                response = test_client.get(
                    "/api/auth/discord/callback",
                    params={
                        "code": "test-code",
                        "state": "valid-state",
                    },
                    follow_redirects=False,
                )

                assert response.status_code == 307
                # Verify prefs were updated
                assert mock_existing_prefs.discord_user_id == "discord-123"
                assert mock_existing_prefs.discord_enabled is True

    def test_callback_success_network_context(self, test_client, mock_db_session):
        """Should handle callback for network context"""
        with patch("app.routers.discord_oauth.discord_oauth_service") as mock_service:
            with patch("app.routers.discord_oauth.user_preferences_service") as mock_prefs:
                mock_service.validate_state.return_value = ("user-123", "network", "network-uuid")

                mock_service.exchange_code_for_tokens = AsyncMock(
                    return_value={
                        "access_token": "test-token",
                        "refresh_token": "test-refresh",
                        "expires_in": 3600,
                    }
                )

                mock_service.get_user_info = AsyncMock(
                    return_value={
                        "id": "discord-123",
                        "username": "testuser",
                        "avatar": None,
                    }
                )

                mock_service.create_or_update_link = AsyncMock(return_value=MagicMock())

                response = test_client.get(
                    "/api/auth/discord/callback",
                    params={
                        "code": "test-code",
                        "state": "valid-state",
                    },
                    follow_redirects=False,
                )

                assert response.status_code == 307
                # Should have called execute for network prefs update
                mock_db_session.execute.assert_called()

    def test_callback_exception_handling(self, test_client):
        """Should redirect with error on exception"""
        with patch("app.routers.discord_oauth.discord_oauth_service") as mock_service:
            mock_service.validate_state.return_value = ("user-123", "global", None)
            mock_service.exchange_code_for_tokens = AsyncMock(side_effect=Exception("API Error"))

            response = test_client.get(
                "/api/auth/discord/callback",
                params={
                    "code": "test-code",
                    "state": "valid-state",
                },
                follow_redirects=False,
            )

            assert response.status_code == 307
            assert "discord_oauth=error" in response.headers["location"]


class TestDiscordOAuthUnlink:
    """Tests for Discord unlink endpoint"""

    def test_unlink_discord_success(self, test_client, mock_db_session):
        """Should unlink Discord account successfully"""
        with patch("app.routers.discord_oauth.discord_oauth_service") as mock_service:
            mock_service.delete_link = AsyncMock(return_value=True)

            response = test_client.delete(
                "/api/users/user-123/discord/link", params={"context_type": "global"}
            )

            assert response.status_code == 200
            assert response.json()["success"] is True

    def test_unlink_discord_network_context(self, test_client, mock_db_session):
        """Should unlink Discord account for network context"""
        with patch("app.routers.discord_oauth.discord_oauth_service") as mock_service:
            mock_service.delete_link = AsyncMock(return_value=True)

            response = test_client.delete(
                "/api/users/user-123/discord/link",
                params={"context_type": "network", "network_id": "network-uuid"},
            )

            assert response.status_code == 200

    def test_unlink_discord_not_linked(self, test_client, mock_db_session):
        """Should return success=false when not linked"""
        with patch("app.routers.discord_oauth.discord_oauth_service") as mock_service:
            mock_service.delete_link = AsyncMock(return_value=False)

            response = test_client.delete(
                "/api/users/user-123/discord/link",
            )

            assert response.status_code == 200
            assert response.json()["success"] is False


class TestDiscordOAuthGetInfo:
    """Tests for Discord info endpoint"""

    def test_get_discord_info_linked(self, test_client, mock_db_session):
        """Should return Discord info when linked"""
        with patch("app.routers.discord_oauth.discord_oauth_service") as mock_service:
            mock_link = MagicMock()
            mock_link.discord_id = "discord-123"
            mock_link.discord_username = "testuser"
            mock_link.discord_avatar = "https://cdn.discord.com/avatar.png"

            mock_service.get_link = AsyncMock(return_value=mock_link)

            response = test_client.get(
                "/api/users/user-123/discord", params={"context_type": "global"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["linked"] is True
            assert data["discord_id"] == "discord-123"
            assert data["discord_username"] == "testuser"

    def test_get_discord_info_not_linked(self, test_client, mock_db_session):
        """Should return linked=false when not linked"""
        with patch("app.routers.discord_oauth.discord_oauth_service") as mock_service:
            mock_service.get_link = AsyncMock(return_value=None)

            response = test_client.get(
                "/api/users/user-123/discord",
            )

            assert response.status_code == 200
            data = response.json()
            assert data["linked"] is False

    def test_get_discord_info_network_context(self, test_client, mock_db_session):
        """Should return Discord info for network context"""
        with patch("app.routers.discord_oauth.discord_oauth_service") as mock_service:
            mock_service.get_link = AsyncMock(return_value=None)

            response = test_client.get(
                "/api/users/user-123/discord",
                params={"context_type": "network", "network_id": "network-uuid"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["context_type"] == "network"
            assert data["network_id"] == "network-uuid"
