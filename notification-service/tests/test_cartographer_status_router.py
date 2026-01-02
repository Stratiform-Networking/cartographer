"""
Tests for Cartographer Status Router endpoints.

Tests the API endpoints for Cartographer status notifications including
subscription management and status notification delivery.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_app():
    """Create test app with mocked lifespan"""
    from app.main import create_app

    with patch("app.main.lifespan"):
        return create_app()


@pytest.fixture
def test_client(test_app):
    """Create test client"""
    return TestClient(test_app)


class TestGetSubscription:
    """Tests for get subscription endpoint"""

    def test_get_subscription_exists(self, test_client):
        """Should return existing subscription"""
        with patch("app.routers.cartographer_status.cartographer_status_service") as mock_service:
            mock_subscription = MagicMock()
            mock_subscription.user_id = "user-123"
            mock_subscription.email_address = "test@example.com"
            mock_subscription.cartographer_up_enabled = True
            mock_subscription.cartographer_down_enabled = True
            mock_subscription.cartographer_up_priority = "medium"
            mock_subscription.cartographer_down_priority = "critical"
            mock_subscription.email_enabled = True
            mock_subscription.discord_enabled = False
            mock_subscription.discord_delivery_method = "dm"
            mock_subscription.discord_guild_id = None
            mock_subscription.discord_channel_id = None
            mock_subscription.discord_user_id = None
            mock_subscription.minimum_priority = "medium"
            mock_subscription.quiet_hours_enabled = False
            mock_subscription.quiet_hours_start = "22:00"
            mock_subscription.quiet_hours_end = "08:00"
            mock_subscription.quiet_hours_bypass_priority = None
            mock_subscription.timezone = "America/New_York"
            mock_subscription.created_at = datetime.now(timezone.utc)
            mock_subscription.updated_at = datetime.now(timezone.utc)

            mock_service.get_subscription.return_value = mock_subscription

            response = test_client.get(
                "/api/cartographer-status/subscription", headers={"X-User-Id": "user-123"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == "user-123"
            assert data["subscribed"] is True
            assert data["email_address"] == "test@example.com"

    def test_get_subscription_not_exists(self, test_client):
        """Should return default values when not subscribed"""
        with patch("app.routers.cartographer_status.cartographer_status_service") as mock_service:
            mock_service.get_subscription.return_value = None

            response = test_client.get(
                "/api/cartographer-status/subscription", headers={"X-User-Id": "user-123"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == "user-123"
            assert data["subscribed"] is False
            assert data["email_address"] is None


class TestCreateSubscription:
    """Tests for create subscription endpoint"""

    def test_create_subscription_success(self, test_client):
        """Should create subscription"""
        with patch("app.routers.cartographer_status.cartographer_status_service") as mock_service:
            with patch("app.routers.cartographer_status.is_email_configured", return_value=True):
                mock_subscription = MagicMock()
                mock_subscription.user_id = "user-123"
                mock_subscription.email_address = "test@example.com"
                mock_subscription.cartographer_up_enabled = True
                mock_subscription.cartographer_down_enabled = True
                mock_subscription.cartographer_up_priority = "medium"
                mock_subscription.cartographer_down_priority = "critical"
                mock_subscription.email_enabled = True
                mock_subscription.discord_enabled = False
                mock_subscription.discord_delivery_method = "dm"
                mock_subscription.discord_guild_id = None
                mock_subscription.discord_channel_id = None
                mock_subscription.discord_user_id = None
                mock_subscription.minimum_priority = "medium"
                mock_subscription.quiet_hours_enabled = False
                mock_subscription.quiet_hours_start = "22:00"
                mock_subscription.quiet_hours_end = "08:00"
                mock_subscription.quiet_hours_bypass_priority = None
                mock_subscription.timezone = None
                mock_subscription.created_at = datetime.now(timezone.utc)
                mock_subscription.updated_at = datetime.now(timezone.utc)

                mock_service.create_or_update_subscription.return_value = mock_subscription

                response = test_client.post(
                    "/api/cartographer-status/subscription",
                    headers={"X-User-Id": "user-123"},
                    json={
                        "email_address": "test@example.com",
                        "email_enabled": True,
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["subscribed"] is True

    def test_create_subscription_no_email(self, test_client):
        """Should return 400 when email address is empty"""
        response = test_client.post(
            "/api/cartographer-status/subscription",
            headers={"X-User-Id": "user-123"},
            json={
                "email_address": "",
            },
        )

        assert response.status_code == 400

    def test_create_subscription_email_not_configured(self, test_client):
        """Should return 503 when email service not configured"""
        with patch("app.routers.cartographer_status.is_email_configured", return_value=False):
            response = test_client.post(
                "/api/cartographer-status/subscription",
                headers={"X-User-Id": "user-123"},
                json={
                    "email_address": "test@example.com",
                },
            )

            assert response.status_code == 503


class TestUpdateSubscription:
    """Tests for update subscription endpoint"""

    def test_update_subscription_exists(self, test_client):
        """Should update existing subscription"""
        with patch("app.routers.cartographer_status.cartographer_status_service") as mock_service:
            mock_subscription = MagicMock()
            mock_subscription.user_id = "user-123"
            mock_subscription.email_address = "updated@example.com"
            mock_subscription.cartographer_up_enabled = False
            mock_subscription.cartographer_down_enabled = True
            mock_subscription.cartographer_up_priority = "medium"
            mock_subscription.cartographer_down_priority = "critical"
            mock_subscription.email_enabled = True
            mock_subscription.discord_enabled = False
            mock_subscription.discord_delivery_method = "dm"
            mock_subscription.discord_guild_id = None
            mock_subscription.discord_channel_id = None
            mock_subscription.discord_user_id = None
            mock_subscription.minimum_priority = "high"
            mock_subscription.quiet_hours_enabled = True
            mock_subscription.quiet_hours_start = "23:00"
            mock_subscription.quiet_hours_end = "07:00"
            mock_subscription.quiet_hours_bypass_priority = "critical"
            mock_subscription.timezone = "America/Los_Angeles"
            mock_subscription.created_at = datetime.now(timezone.utc)
            mock_subscription.updated_at = datetime.now(timezone.utc)

            mock_service.get_subscription.return_value = mock_subscription
            mock_service.create_or_update_subscription.return_value = mock_subscription

            response = test_client.put(
                "/api/cartographer-status/subscription",
                headers={"X-User-Id": "user-123"},
                json={
                    "email_address": "updated@example.com",
                    "cartographer_up_enabled": False,
                    "minimum_priority": "high",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["subscribed"] is True

    def test_update_subscription_create_new(self, test_client):
        """Should create new subscription if not exists"""
        with patch("app.routers.cartographer_status.cartographer_status_service") as mock_service:
            mock_subscription = MagicMock()
            mock_subscription.user_id = "user-123"
            mock_subscription.email_address = "new@example.com"
            mock_subscription.cartographer_up_enabled = True
            mock_subscription.cartographer_down_enabled = True
            mock_subscription.cartographer_up_priority = "medium"
            mock_subscription.cartographer_down_priority = "critical"
            mock_subscription.email_enabled = False
            mock_subscription.discord_enabled = False
            mock_subscription.discord_delivery_method = "dm"
            mock_subscription.discord_guild_id = None
            mock_subscription.discord_channel_id = None
            mock_subscription.discord_user_id = None
            mock_subscription.minimum_priority = "medium"
            mock_subscription.quiet_hours_enabled = False
            mock_subscription.quiet_hours_start = "22:00"
            mock_subscription.quiet_hours_end = "08:00"
            mock_subscription.quiet_hours_bypass_priority = None
            mock_subscription.timezone = None
            mock_subscription.created_at = datetime.now(timezone.utc)
            mock_subscription.updated_at = datetime.now(timezone.utc)

            mock_service.get_subscription.return_value = None
            mock_service.create_or_update_subscription.return_value = mock_subscription

            response = test_client.put(
                "/api/cartographer-status/subscription",
                headers={"X-User-Id": "user-123", "X-User-Email": "new@example.com"},
                json={
                    "email_enabled": True,
                },
            )

            assert response.status_code == 200


class TestDeleteSubscription:
    """Tests for delete subscription endpoint"""

    def test_delete_subscription_success(self, test_client):
        """Should delete subscription"""
        with patch("app.routers.cartographer_status.cartographer_status_service") as mock_service:
            mock_service.delete_subscription.return_value = True

            response = test_client.delete(
                "/api/cartographer-status/subscription", headers={"X-User-Id": "user-123"}
            )

            assert response.status_code == 200
            assert response.json()["success"] is True

    def test_delete_subscription_not_found(self, test_client):
        """Should return 404 when subscription not found"""
        with patch("app.routers.cartographer_status.cartographer_status_service") as mock_service:
            mock_service.delete_subscription.return_value = False

            response = test_client.delete(
                "/api/cartographer-status/subscription", headers={"X-User-Id": "user-123"}
            )

            assert response.status_code == 404


class TestNotifyCartographerStatus:
    """Tests for notify endpoint"""

    def test_notify_up_success(self, test_client):
        """Should send up notification"""
        with patch("app.routers.cartographer_status.cartographer_status_service") as mock_service:
            with patch("app.routers.cartographer_status.is_email_configured", return_value=True):
                with patch(
                    "app.routers.cartographer_status.is_discord_configured", return_value=False
                ):
                    with patch(
                        "app.routers.cartographer_status.send_notification_email",
                        new_callable=AsyncMock,
                    ) as mock_send:
                        mock_subscriber = MagicMock()
                        mock_subscriber.user_id = "user-123"
                        mock_subscriber.email_address = "test@example.com"
                        mock_subscriber.email_enabled = True
                        mock_subscriber.discord_enabled = False

                        mock_service.get_subscribers_for_event.return_value = [mock_subscriber]

                        mock_record = MagicMock()
                        mock_record.success = True
                        mock_send.return_value = mock_record

                        response = test_client.post(
                            "/api/cartographer-status/notify",
                            json={
                                "event_type": "up",
                                "message": "Service restored",
                                "downtime_minutes": 15,
                            },
                        )

                        assert response.status_code == 200
                        data = response.json()
                        assert data["success"] is True
                        assert data["subscribers_notified"] == 1

    def test_notify_down_success(self, test_client):
        """Should send down notification"""
        with patch("app.routers.cartographer_status.cartographer_status_service") as mock_service:
            with patch("app.routers.cartographer_status.is_email_configured", return_value=True):
                with patch(
                    "app.routers.cartographer_status.is_discord_configured", return_value=False
                ):
                    with patch(
                        "app.routers.cartographer_status.send_notification_email",
                        new_callable=AsyncMock,
                    ) as mock_send:
                        mock_subscriber = MagicMock()
                        mock_subscriber.user_id = "user-123"
                        mock_subscriber.email_address = "test@example.com"
                        mock_subscriber.email_enabled = True
                        mock_subscriber.discord_enabled = False

                        mock_service.get_subscribers_for_event.return_value = [mock_subscriber]

                        mock_record = MagicMock()
                        mock_record.success = True
                        mock_send.return_value = mock_record

                        response = test_client.post(
                            "/api/cartographer-status/notify",
                            json={"event_type": "down", "affected_services": ["health", "metrics"]},
                        )

                        assert response.status_code == 200

    def test_notify_invalid_event_type(self, test_client):
        """Should return 400 for invalid event type"""
        response = test_client.post(
            "/api/cartographer-status/notify", json={"event_type": "invalid"}
        )

        assert response.status_code == 400

    def test_notify_no_subscribers(self, test_client):
        """Should handle no subscribers"""
        with patch("app.routers.cartographer_status.cartographer_status_service") as mock_service:
            mock_service.get_subscribers_for_event.return_value = []

            response = test_client.post(
                "/api/cartographer-status/notify", json={"event_type": "up"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["subscribers_notified"] == 0

    def test_notify_no_services_configured(self, test_client):
        """Should return error when no notification services configured"""
        with patch("app.routers.cartographer_status.cartographer_status_service") as mock_service:
            with patch("app.routers.cartographer_status.is_email_configured", return_value=False):
                with patch(
                    "app.routers.cartographer_status.is_discord_configured", return_value=False
                ):
                    mock_subscriber = MagicMock()
                    mock_subscriber.user_id = "user-123"
                    mock_subscriber.email_enabled = True
                    mock_subscriber.discord_enabled = False

                    mock_service.get_subscribers_for_event.return_value = [mock_subscriber]

                    response = test_client.post(
                        "/api/cartographer-status/notify", json={"event_type": "up"}
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is False


class TestTestDiscordEndpoint:
    """Tests for test Discord endpoint"""

    def test_test_discord_not_configured(self, test_client):
        """Should return 503 when Discord not configured"""
        with patch("app.routers.cartographer_status.is_discord_configured", return_value=False):
            response = test_client.post(
                "/api/cartographer-status/test/discord",
                headers={"X-User-Id": "user-123"},
                json={"channel_id": "123456789"},
            )

            assert response.status_code == 503

    def test_test_discord_no_target(self, test_client):
        """Should return 400 when no channel or user ID provided"""
        with patch("app.routers.cartographer_status.is_discord_configured", return_value=True):
            response = test_client.post(
                "/api/cartographer-status/test/discord", headers={"X-User-Id": "user-123"}, json={}
            )

            assert response.status_code == 400

    def test_test_discord_channel_success(self, test_client):
        """Should send test notification to channel"""
        with patch("app.routers.cartographer_status.is_discord_configured", return_value=True):
            with patch("app.routers.cartographer_status.discord_service") as mock_ds:
                mock_ds.send_test_notification = AsyncMock(return_value={"success": True})

                response = test_client.post(
                    "/api/cartographer-status/test/discord",
                    headers={"X-User-Id": "user-123"},
                    json={"channel_id": "123456789"},
                )

                assert response.status_code == 200
                assert response.json()["success"] is True

    def test_test_discord_dm_success(self, test_client):
        """Should send test notification via DM"""
        with patch("app.routers.cartographer_status.is_discord_configured", return_value=True):
            with patch("app.routers.cartographer_status.discord_service") as mock_ds:
                mock_ds.send_test_notification = AsyncMock(return_value={"success": True})

                response = test_client.post(
                    "/api/cartographer-status/test/discord",
                    headers={"X-User-Id": "user-123"},
                    json={"user_id": "discord-user-123"},
                )

                assert response.status_code == 200

    def test_test_discord_failure(self, test_client):
        """Should handle Discord send failure"""
        with patch("app.routers.cartographer_status.is_discord_configured", return_value=True):
            with patch("app.routers.cartographer_status.discord_service") as mock_ds:
                mock_ds.send_test_notification = AsyncMock(
                    return_value={"success": False, "error": "Failed to send"}
                )

                response = test_client.post(
                    "/api/cartographer-status/test/discord",
                    headers={"X-User-Id": "user-123"},
                    json={"channel_id": "123456789"},
                )

                assert response.status_code == 500
