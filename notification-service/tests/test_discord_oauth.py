"""
Tests for Discord OAuth Service.

This module tests the Discord OAuth flow including authorization URL generation,
token exchange, user info retrieval, and link management.
"""

import os
import re
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestDiscordOAuthService:
    """Tests for Discord OAuth service"""

    def test_get_authorization_url_no_client_id(self):
        """Should raise error when client ID not configured"""
        from app.services.discord_oauth import DiscordOAuthService

        with patch("app.services.discord_oauth.settings.discord_client_id", ""):
            service = DiscordOAuthService()

            with pytest.raises(ValueError, match="DISCORD_CLIENT_ID not configured"):
                service.get_authorization_url("user-123")

    def test_get_authorization_url_success(self):
        """Should generate authorization URL"""
        from app.services.discord_oauth import DiscordOAuthService

        with patch("app.services.discord_oauth.settings.discord_client_id", "test-client-id-12345"):
            service = DiscordOAuthService()
            url = service.get_authorization_url("user-123", "network", "net-uuid")

            assert "discord.com" in url
            assert "client_id=test-client-id-12345" in url
            assert "state=" in url

    def test_get_authorization_url_global_context(self):
        """Should generate URL for global context"""
        from app.services.discord_oauth import DiscordOAuthService

        with patch("app.services.discord_oauth.settings.discord_client_id", "test-client-id-12345"):
            service = DiscordOAuthService()
            url = service.get_authorization_url("user-123", "global", None)

            assert "discord.com" in url

    def test_validate_state_invalid(self):
        """Should return None for invalid state"""
        from app.services.discord_oauth import DiscordOAuthService

        service = DiscordOAuthService()
        result = service.validate_state("invalid-state-token-xyz")

        assert result is None

    def test_validate_state_valid(self):
        """Should return context for valid state"""
        from app.services import discord_oauth
        from app.services.discord_oauth import DiscordOAuthService

        with patch("app.services.discord_oauth.settings.discord_client_id", "test-client-id-12345"):
            service = DiscordOAuthService()
            url = service.get_authorization_url("user-abc", "network", "net-xyz")

            match = re.search(r"state=([^&]+)", url)
            assert match is not None

            state = match.group(1)
            result = service.validate_state(state)

            assert result is not None
            user_id, context_type, context_id = result
            assert user_id == "user-abc"
            assert context_type == "network"
            assert context_id == "net-xyz"

    def test_validate_state_expired(self):
        """Should return None for expired state"""
        from app.services import discord_oauth
        from app.services.discord_oauth import DiscordOAuthService

        with patch("app.services.discord_oauth.settings.discord_client_id", "test-client-id-12345"):
            service = DiscordOAuthService()
            url = service.get_authorization_url("user-123")

            match = re.search(r"state=([^&]+)", url)
            if match:
                state = match.group(1)

                if state in discord_oauth._oauth_states:
                    discord_oauth._oauth_states[state][
                        "created_at"
                    ] = datetime.utcnow() - timedelta(minutes=10)

                result = service.validate_state(state)
                assert result is None


class TestDiscordOAuthTokenExchange:
    """Tests for Discord OAuth token exchange"""

    @pytest.mark.asyncio
    async def test_exchange_code_not_configured(self):
        """Should raise error when OAuth not configured"""
        from app.services.discord_oauth import DiscordOAuthService

        with patch("app.services.discord_oauth.settings.discord_client_id", ""):
            with patch("app.services.discord_oauth.settings.discord_client_secret", ""):
                service = DiscordOAuthService()

                with pytest.raises(ValueError, match="Discord OAuth not configured"):
                    await service.exchange_code_for_tokens("test-code")

    @pytest.mark.asyncio
    async def test_exchange_code_success(self):
        """Should exchange code for tokens"""
        from app.services.discord_oauth import DiscordOAuthService

        with patch("app.services.discord_oauth.settings.discord_client_id", "test-client-id"):
            with patch("app.services.discord_oauth.settings.discord_client_secret", "test-secret"):
                service = DiscordOAuthService()

                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "access_token": "test-token",
                    "refresh_token": "test-refresh",
                    "expires_in": 3600,
                }

                with patch("httpx.AsyncClient") as mock_client:
                    mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                        return_value=mock_response
                    )

                    result = await service.exchange_code_for_tokens("test-code")

                    assert result["access_token"] == "test-token"

    @pytest.mark.asyncio
    async def test_exchange_code_failure(self):
        """Should raise error on token exchange failure"""
        from app.services.discord_oauth import DiscordOAuthService

        with patch("app.services.discord_oauth.settings.discord_client_id", "test-client-id"):
            with patch("app.services.discord_oauth.settings.discord_client_secret", "test-secret"):
                service = DiscordOAuthService()

                mock_response = MagicMock()
                mock_response.status_code = 400
                mock_response.text = "Invalid code"

                with patch("httpx.AsyncClient") as mock_client:
                    mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                        return_value=mock_response
                    )

                    with pytest.raises(ValueError, match="Failed to exchange code"):
                        await service.exchange_code_for_tokens("invalid-code")


class TestDiscordOAuthUserInfo:
    """Tests for Discord OAuth user info retrieval"""

    @pytest.mark.asyncio
    async def test_get_user_info_success(self):
        """Should get user info from Discord"""
        from app.services.discord_oauth import DiscordOAuthService

        service = DiscordOAuthService()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "123456789",
            "username": "testuser",
            "avatar": "abcdef",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await service.get_user_info("test-token")

            assert result["id"] == "123456789"
            assert result["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_get_user_info_failure(self):
        """Should raise error on user info failure"""
        from app.services.discord_oauth import DiscordOAuthService

        service = DiscordOAuthService()

        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(ValueError, match="Failed to get user info"):
                await service.get_user_info("invalid-token")


class TestDiscordOAuthLinkOperations:
    """Tests for Discord OAuth link operations"""

    @pytest.mark.asyncio
    async def test_get_link_global(self):
        """Should get global Discord link"""
        from app.services.discord_oauth import DiscordOAuthService

        service = DiscordOAuthService()
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_link(mock_db, "user-123", "global")

        assert result is None
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_link_network(self):
        """Should get network-specific Discord link"""
        from app.services.discord_oauth import DiscordOAuthService

        service = DiscordOAuthService()
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_link(mock_db, "user-123", "network", "network-uuid")

        assert result is None
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_link_exists(self):
        """Should delete existing link"""
        from app.services.discord_oauth import DiscordOAuthService

        service = DiscordOAuthService()
        mock_db = AsyncMock()
        mock_link = MagicMock()

        with patch.object(service, "get_link", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_link

            result = await service.delete_link(mock_db, "user-123")

            assert result is True
            mock_db.delete.assert_called_once_with(mock_link)

    @pytest.mark.asyncio
    async def test_delete_link_not_exists(self):
        """Should return False when link doesn't exist"""
        from app.services.discord_oauth import DiscordOAuthService

        service = DiscordOAuthService()
        mock_db = AsyncMock()

        with patch.object(service, "get_link", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            result = await service.delete_link(mock_db, "user-123")

            assert result is False

    @pytest.mark.asyncio
    async def test_create_link_new(self):
        """Should create new link"""
        from app.services.discord_oauth import DiscordOAuthService

        service = DiscordOAuthService()
        mock_db = AsyncMock()

        with patch.object(service, "get_link", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()

            result = await service.create_or_update_link(
                db=mock_db,
                user_id="user-123",
                discord_id="123456789",
                discord_username="testuser",
                discord_avatar="abc123",
                access_token="token",
                refresh_token="refresh",
                expires_in=3600,
                context_type="global",
                context_id=None,
            )

            mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_existing_link(self):
        """Should update existing link"""
        from app.services.discord_oauth import DiscordOAuthService

        service = DiscordOAuthService()
        mock_db = AsyncMock()

        existing_link = MagicMock()
        existing_link.discord_id = "old-id"

        with patch.object(service, "get_link", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = existing_link
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()

            result = await service.create_or_update_link(
                db=mock_db,
                user_id="user-123",
                discord_id="new-id",
                discord_username="newuser",
                discord_avatar="xyz",
                access_token="newtoken",
                refresh_token="newrefresh",
                expires_in=7200,
            )

            assert existing_link.discord_id == "new-id"


class TestDiscordOAuthRouter:
    """Tests for Discord OAuth router endpoints"""

    def test_discord_oauth_module_import(self):
        """Should import Discord OAuth router"""
        from app.routers import discord_oauth

        assert discord_oauth is not None
