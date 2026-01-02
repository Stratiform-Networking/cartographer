"""
Tests for User Notifications Router endpoints.

Tests the API endpoints for managing user notification preferences
including network-specific and global preferences, and test notifications.
"""

from datetime import datetime, timezone
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


class TestNetworkPreferencesEndpoints:
    """Tests for network preferences endpoints"""

    def test_get_network_preferences(self, test_client, mock_db_session):
        """Should get network preferences"""
        with patch("app.routers.user_notifications.user_preferences_service") as mock_service:
            mock_prefs = MagicMock()
            mock_prefs.user_id = "user-123"
            mock_prefs.network_id = "network-uuid"
            mock_prefs.email_enabled = True
            mock_prefs.discord_enabled = False
            mock_prefs.discord_user_id = None
            mock_prefs.enabled_types = ["device_offline", "device_online"]
            mock_prefs.type_priorities = {}
            mock_prefs.minimum_priority = "medium"
            mock_prefs.quiet_hours_enabled = False
            mock_prefs.quiet_hours_start = None
            mock_prefs.quiet_hours_end = None
            mock_prefs.quiet_hours_timezone = None
            mock_prefs.quiet_hours_bypass_priority = None
            mock_prefs.created_at = datetime.now(timezone.utc)
            mock_prefs.updated_at = datetime.now(timezone.utc)

            mock_service.get_or_create_network_preferences = AsyncMock(return_value=mock_prefs)

            response = test_client.get("/api/users/user-123/networks/network-uuid/preferences")

            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == "user-123"
            assert data["network_id"] == "network-uuid"

    def test_update_network_preferences(self, test_client, mock_db_session):
        """Should update network preferences"""
        with patch("app.routers.user_notifications.user_preferences_service") as mock_service:
            mock_prefs = MagicMock()
            mock_prefs.user_id = "user-123"
            mock_prefs.network_id = "network-uuid"
            mock_prefs.email_enabled = True
            mock_prefs.discord_enabled = True
            mock_prefs.discord_user_id = "discord-123"
            mock_prefs.enabled_types = ["device_offline"]
            mock_prefs.type_priorities = {}
            mock_prefs.minimum_priority = "high"
            mock_prefs.quiet_hours_enabled = False
            mock_prefs.quiet_hours_start = None
            mock_prefs.quiet_hours_end = None
            mock_prefs.quiet_hours_timezone = None
            mock_prefs.quiet_hours_bypass_priority = None
            mock_prefs.created_at = datetime.now(timezone.utc)
            mock_prefs.updated_at = datetime.now(timezone.utc)

            mock_service.update_network_preferences = AsyncMock(return_value=mock_prefs)

            response = test_client.put(
                "/api/users/user-123/networks/network-uuid/preferences",
                json={"email_enabled": True, "discord_enabled": True, "minimum_priority": "high"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["email_enabled"] is True

    def test_delete_network_preferences(self, test_client, mock_db_session):
        """Should delete network preferences"""
        with patch("app.routers.user_notifications.user_preferences_service") as mock_service:
            mock_service.delete_network_preferences = AsyncMock(return_value=True)

            response = test_client.delete("/api/users/user-123/networks/network-uuid/preferences")

            assert response.status_code == 200
            assert response.json()["success"] is True


class TestGlobalPreferencesEndpoints:
    """Tests for global preferences endpoints"""

    def test_get_global_preferences(self, test_client, mock_db_session):
        """Should get global preferences"""
        with patch("app.routers.user_notifications.user_preferences_service") as mock_service:
            mock_prefs = MagicMock()
            mock_prefs.user_id = "user-123"
            mock_prefs.email_enabled = True
            mock_prefs.discord_enabled = False
            mock_prefs.discord_user_id = None
            mock_prefs.cartographer_up_enabled = True
            mock_prefs.cartographer_down_enabled = True
            mock_prefs.minimum_priority = "medium"
            mock_prefs.quiet_hours_enabled = False
            mock_prefs.quiet_hours_start = None
            mock_prefs.quiet_hours_end = None
            mock_prefs.quiet_hours_timezone = None
            mock_prefs.quiet_hours_bypass_priority = None
            mock_prefs.created_at = datetime.now(timezone.utc)
            mock_prefs.updated_at = datetime.now(timezone.utc)

            mock_service.get_or_create_global_preferences = AsyncMock(return_value=mock_prefs)

            response = test_client.get("/api/users/user-123/global/preferences")

            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == "user-123"
            assert data["cartographer_up_enabled"] is True

    def test_update_global_preferences(self, test_client, mock_db_session):
        """Should update global preferences"""
        with patch("app.routers.user_notifications.user_preferences_service") as mock_service:
            mock_prefs = MagicMock()
            mock_prefs.user_id = "user-123"
            mock_prefs.email_enabled = True
            mock_prefs.discord_enabled = True
            mock_prefs.discord_user_id = "discord-456"
            mock_prefs.cartographer_up_enabled = False
            mock_prefs.cartographer_down_enabled = True
            mock_prefs.minimum_priority = "critical"
            mock_prefs.quiet_hours_enabled = True
            mock_prefs.quiet_hours_start = "22:00"
            mock_prefs.quiet_hours_end = "08:00"
            mock_prefs.quiet_hours_timezone = "America/New_York"
            mock_prefs.quiet_hours_bypass_priority = "critical"
            mock_prefs.created_at = datetime.now(timezone.utc)
            mock_prefs.updated_at = datetime.now(timezone.utc)

            mock_service.update_global_preferences = AsyncMock(return_value=mock_prefs)

            response = test_client.put(
                "/api/users/user-123/global/preferences",
                json={
                    "email_enabled": True,
                    "cartographer_up_enabled": False,
                    "minimum_priority": "critical",
                },
            )

            assert response.status_code == 200


class TestNetworkTestNotificationEndpoints:
    """Tests for network test notification endpoints"""

    def test_test_email_notification_not_enabled(self, test_client, mock_db_session):
        """Should fail when email not enabled"""
        with patch("app.routers.user_notifications.user_preferences_service") as mock_service:
            mock_prefs = MagicMock()
            mock_prefs.email_enabled = False
            mock_prefs.discord_enabled = False

            mock_service.get_network_preferences = AsyncMock(return_value=mock_prefs)

            response = test_client.post(
                "/api/users/user-123/networks/network-uuid/test", json={"channel": "email"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False

    def test_test_notification_not_found(self, test_client, mock_db_session):
        """Should return 404 when preferences not found"""
        with patch("app.routers.user_notifications.user_preferences_service") as mock_service:
            mock_service.get_network_preferences = AsyncMock(return_value=None)

            response = test_client.post(
                "/api/users/user-123/networks/network-uuid/test", json={"channel": "email"}
            )

            assert response.status_code == 404

    def test_test_email_not_configured(self, test_client, mock_db_session):
        """Should fail when email service not configured"""
        with patch("app.routers.user_notifications.user_preferences_service") as mock_service:
            with patch("app.routers.user_notifications.is_email_configured", return_value=False):
                mock_prefs = MagicMock()
                mock_prefs.email_enabled = True
                mock_prefs.discord_enabled = False

                mock_service.get_network_preferences = AsyncMock(return_value=mock_prefs)

                response = test_client.post(
                    "/api/users/user-123/networks/network-uuid/test", json={"channel": "email"}
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is False
                assert "not configured" in data["error"].lower()

    def test_test_discord_not_enabled(self, test_client, mock_db_session):
        """Should fail when Discord not enabled"""
        with patch("app.routers.user_notifications.user_preferences_service") as mock_service:
            mock_prefs = MagicMock()
            mock_prefs.email_enabled = False
            mock_prefs.discord_enabled = False
            mock_prefs.discord_user_id = None

            mock_service.get_network_preferences = AsyncMock(return_value=mock_prefs)

            response = test_client.post(
                "/api/users/user-123/networks/network-uuid/test", json={"channel": "discord"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False

    def test_test_discord_no_user_id(self, test_client, mock_db_session):
        """Should fail when Discord user ID not linked"""
        with patch("app.routers.user_notifications.user_preferences_service") as mock_service:
            mock_prefs = MagicMock()
            mock_prefs.email_enabled = False
            mock_prefs.discord_enabled = True
            mock_prefs.discord_user_id = None

            mock_service.get_network_preferences = AsyncMock(return_value=mock_prefs)

            response = test_client.post(
                "/api/users/user-123/networks/network-uuid/test", json={"channel": "discord"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            # Check for "link" since error message is "Please link your Discord account first"
            assert "link" in data["error"].lower()


class TestGlobalTestNotificationEndpoints:
    """Tests for global test notification endpoints"""

    def test_test_global_notification_not_found(self, test_client, mock_db_session):
        """Should return 404 when preferences not found"""
        with patch("app.routers.user_notifications.user_preferences_service") as mock_service:
            mock_service.get_global_preferences = AsyncMock(return_value=None)

            response = test_client.post(
                "/api/users/user-123/global/test", json={"channel": "email"}
            )

            assert response.status_code == 404

    def test_test_global_email_not_enabled(self, test_client, mock_db_session):
        """Should fail when email not enabled"""
        with patch("app.routers.user_notifications.user_preferences_service") as mock_service:
            mock_prefs = MagicMock()
            mock_prefs.email_enabled = False
            mock_prefs.discord_enabled = False

            mock_service.get_global_preferences = AsyncMock(return_value=mock_prefs)

            response = test_client.post(
                "/api/users/user-123/global/test", json={"channel": "email"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False

    def test_test_global_discord_not_enabled(self, test_client, mock_db_session):
        """Should fail when Discord not enabled"""
        with patch("app.routers.user_notifications.user_preferences_service") as mock_service:
            mock_prefs = MagicMock()
            mock_prefs.email_enabled = False
            mock_prefs.discord_enabled = False
            mock_prefs.discord_user_id = None

            mock_service.get_global_preferences = AsyncMock(return_value=mock_prefs)

            response = test_client.post(
                "/api/users/user-123/global/test", json={"channel": "discord"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False

    def test_test_global_discord_no_user_id(self, test_client, mock_db_session):
        """Should fail when Discord user ID not linked"""
        with patch("app.routers.user_notifications.user_preferences_service") as mock_service:
            mock_prefs = MagicMock()
            mock_prefs.email_enabled = False
            mock_prefs.discord_enabled = True
            mock_prefs.discord_user_id = None

            mock_service.get_global_preferences = AsyncMock(return_value=mock_prefs)

            response = test_client.post(
                "/api/users/user-123/global/test", json={"channel": "discord"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False


class TestPreferencesResponseModels:
    """Tests for preference response models"""

    def test_network_preferences_response_from_db(self):
        """Should convert database model to response"""
        from app.models.database import NotificationPriorityEnum
        from app.routers.user_notifications import NetworkPreferencesResponse

        mock_prefs = MagicMock()
        mock_prefs.user_id = "user-123"
        mock_prefs.network_id = "network-uuid"
        mock_prefs.email_enabled = True
        mock_prefs.discord_enabled = False
        mock_prefs.discord_user_id = None
        mock_prefs.enabled_types = ["device_offline"]
        mock_prefs.type_priorities = {"device_offline": NotificationPriorityEnum.HIGH}
        mock_prefs.minimum_priority = NotificationPriorityEnum.MEDIUM
        mock_prefs.quiet_hours_enabled = False
        mock_prefs.quiet_hours_start = None
        mock_prefs.quiet_hours_end = None
        mock_prefs.quiet_hours_timezone = None
        mock_prefs.quiet_hours_bypass_priority = NotificationPriorityEnum.CRITICAL
        mock_prefs.created_at = datetime.now(timezone.utc)
        mock_prefs.updated_at = datetime.now(timezone.utc)

        response = NetworkPreferencesResponse.from_db(mock_prefs)

        assert response.user_id == "user-123"
        assert response.minimum_priority == "medium"
        assert response.type_priorities["device_offline"] == "high"

    def test_global_preferences_response_from_db(self):
        """Should convert database model to response"""
        from app.models.database import NotificationPriorityEnum
        from app.routers.user_notifications import GlobalPreferencesResponse

        mock_prefs = MagicMock()
        mock_prefs.user_id = "user-123"
        mock_prefs.email_enabled = True
        mock_prefs.discord_enabled = False
        mock_prefs.discord_user_id = None
        mock_prefs.cartographer_up_enabled = True
        mock_prefs.cartographer_down_enabled = True
        mock_prefs.minimum_priority = NotificationPriorityEnum.HIGH
        mock_prefs.quiet_hours_enabled = True
        mock_prefs.quiet_hours_start = "22:00"
        mock_prefs.quiet_hours_end = "08:00"
        mock_prefs.quiet_hours_timezone = "America/New_York"
        mock_prefs.quiet_hours_bypass_priority = NotificationPriorityEnum.CRITICAL
        mock_prefs.created_at = datetime.now(timezone.utc)
        mock_prefs.updated_at = datetime.now(timezone.utc)

        response = GlobalPreferencesResponse.from_db(mock_prefs)

        assert response.user_id == "user-123"
        assert response.minimum_priority == "high"
        assert response.quiet_hours_bypass_priority == "critical"
