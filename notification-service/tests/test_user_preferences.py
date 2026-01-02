"""
Tests for User Preferences Service.

This module tests the UserPreferencesService which manages user notification
preferences stored in the database, including network-specific and global preferences.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestUserPreferencesService:
    """Tests for user preferences service"""

    @pytest.mark.asyncio
    async def test_get_network_preferences_not_found(self):
        """Should return None when preferences not found"""
        from app.services.user_preferences import UserPreferencesService

        service = UserPreferencesService()
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_network_preferences(mock_db, "user-123", "net-123")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_global_preferences_not_found(self):
        """Should return None when global preferences not found"""
        from app.services.user_preferences import UserPreferencesService

        service = UserPreferencesService()
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_global_preferences(mock_db, "user-123")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_discord_link_not_found(self):
        """Should return None when Discord link not found"""
        from app.services.user_preferences import UserPreferencesService

        service = UserPreferencesService()
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_discord_link(mock_db, "user-123")

        assert result is None


class TestUserPreferencesServiceEmail:
    """Tests for user email retrieval"""

    @pytest.mark.asyncio
    async def test_get_user_email_found(self):
        """Should return email when found"""
        from app.services.user_preferences import UserPreferencesService

        service = UserPreferencesService()
        mock_db = AsyncMock()

        mock_row = MagicMock()
        mock_row.__getitem__ = MagicMock(return_value="test@example.com")

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        result = await service.get_user_email(mock_db, "user-123")

        assert result == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_user_email_not_found(self):
        """Should return None when user email not found"""
        from app.services.user_preferences import UserPreferencesService

        service = UserPreferencesService()
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_user_email(mock_db, "user-123")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_email_exception(self):
        """Should return None on database error"""
        from app.services.user_preferences import UserPreferencesService

        service = UserPreferencesService()
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("Database error")

        result = await service.get_user_email(mock_db, "user-123")

        assert result is None


class TestUserPreferencesServiceCreate:
    """Tests for creating user preferences"""

    @pytest.mark.asyncio
    async def test_get_or_create_network_preferences_creates(self):
        """Should create preferences if not exists"""
        from app.services.user_preferences import UserPreferencesService

        service = UserPreferencesService()
        mock_db = AsyncMock()

        with patch.object(service, "get_network_preferences", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()

            result = await service.get_or_create_network_preferences(
                mock_db, "user-123", "network-123", "test@example.com"
            )

            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_global_preferences(self):
        """Should create global preferences if not exists"""
        from app.services.user_preferences import UserPreferencesService

        service = UserPreferencesService()
        mock_db = AsyncMock()

        with patch.object(service, "get_global_preferences", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()

            result = await service.get_or_create_global_preferences(
                mock_db, "user-123", "test@example.com"
            )

            mock_db.add.assert_called_once()


class TestUserPreferencesServiceUpdate:
    """Tests for updating user preferences"""

    @pytest.mark.asyncio
    async def test_update_network_preferences(self):
        """Should update network preferences"""
        from app.services.user_preferences import UserPreferencesService

        service = UserPreferencesService()
        mock_db = AsyncMock()
        mock_prefs = MagicMock()
        mock_prefs.updated_at = datetime.utcnow()

        with patch.object(
            service, "get_or_create_network_preferences", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_prefs
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()

            result = await service.update_network_preferences(
                mock_db, "user-123", "network-123", {"email_enabled": True}
            )

            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_global_preferences(self):
        """Should update global preferences"""
        from app.services.user_preferences import UserPreferencesService

        service = UserPreferencesService()
        mock_db = AsyncMock()
        mock_prefs = MagicMock()
        mock_prefs.updated_at = datetime.utcnow()

        with patch.object(
            service, "get_or_create_global_preferences", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = mock_prefs
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()

            result = await service.update_global_preferences(
                mock_db, "user-123", {"email_enabled": True}
            )

            mock_db.commit.assert_called_once()


class TestUserPreferencesServiceDelete:
    """Tests for deleting user preferences"""

    @pytest.mark.asyncio
    async def test_delete_network_preferences_exists(self):
        """Should delete existing preferences"""
        from app.services.user_preferences import UserPreferencesService

        service = UserPreferencesService()
        mock_db = AsyncMock()
        mock_prefs = MagicMock()

        with patch.object(service, "get_network_preferences", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_prefs
            mock_db.delete = AsyncMock()
            mock_db.commit = AsyncMock()

            result = await service.delete_network_preferences(mock_db, "user-123", "network-123")

            assert result is True
            mock_db.delete.assert_called_once_with(mock_prefs)

    @pytest.mark.asyncio
    async def test_delete_network_preferences_not_exists(self):
        """Should return False when preferences don't exist"""
        from app.services.user_preferences import UserPreferencesService

        service = UserPreferencesService()
        mock_db = AsyncMock()

        with patch.object(service, "get_network_preferences", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            result = await service.delete_network_preferences(mock_db, "user-123", "network-123")

            assert result is False


class TestUserPreferencesServiceNotifications:
    """Tests for notification-related preferences queries"""

    @pytest.mark.asyncio
    async def test_get_users_with_enabled_notifications(self):
        """Should get users with enabled notifications"""
        from app.models import NotificationType
        from app.services.user_preferences import UserPreferencesService

        service = UserPreferencesService()
        mock_db = AsyncMock()

        mock_prefs = MagicMock()
        mock_prefs.enabled_types = ["device_offline"]
        mock_prefs.email_enabled = True
        mock_prefs.discord_enabled = False

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_prefs]
        mock_db.execute.return_value = mock_result

        result = await service.get_users_with_enabled_notifications(
            mock_db, "network-123", NotificationType.DEVICE_OFFLINE
        )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_users_with_global_notifications_enabled_up(self):
        """Should get users with CARTOGRAPHER_UP notifications enabled"""
        from app.models import NotificationType
        from app.services.user_preferences import UserPreferencesService

        service = UserPreferencesService()
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await service.get_users_with_global_notifications_enabled(
            mock_db, NotificationType.CARTOGRAPHER_UP
        )

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_users_with_global_notifications_enabled_other(self):
        """Should return empty for other notification types"""
        from app.models import NotificationType
        from app.services.user_preferences import UserPreferencesService

        service = UserPreferencesService()
        mock_db = AsyncMock()

        result = await service.get_users_with_global_notifications_enabled(
            mock_db, NotificationType.DEVICE_OFFLINE
        )

        assert result == []


class TestUserPreferencesServiceNetworkMembers:
    """Tests for network member queries"""

    @pytest.mark.asyncio
    async def test_get_network_member_user_ids(self):
        """Should get network member user IDs"""
        from app.services.user_preferences import UserPreferencesService

        service = UserPreferencesService()
        mock_db = AsyncMock()

        mock_row1 = MagicMock()
        mock_row1.__getitem__ = MagicMock(return_value="user-1")
        mock_row2 = MagicMock()
        mock_row2.__getitem__ = MagicMock(return_value="user-2")

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row1, mock_row2]
        mock_db.execute.return_value = mock_result

        result = await service.get_network_member_user_ids(mock_db, "network-123")

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_network_member_user_ids_exception(self):
        """Should return empty list on exception"""
        from app.services.user_preferences import UserPreferencesService

        service = UserPreferencesService()
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("Database error")

        result = await service.get_network_member_user_ids(mock_db, "network-123")

        assert result == []
