"""
Tests for Cartographer Status Service and Router.

This module tests the CartographerStatusService which manages subscriptions
for Cartographer Up/Down notifications, separate from network-scoped notifications.
"""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestCartographerStatusService:
    """Tests for CartographerStatusService"""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create temporary data directory"""
        with patch.dict(os.environ, {"NOTIFICATION_DATA_DIR": str(tmp_path)}):
            yield tmp_path

    @pytest.fixture
    def status_service(self, temp_data_dir):
        """Create a CartographerStatusService instance"""
        with patch(
            "app.services.cartographer_status.SUBSCRIPTIONS_FILE", temp_data_dir / "subs.json"
        ):
            from app.services.cartographer_status import CartographerStatusService

            with patch.object(CartographerStatusService, "_migrate_from_global_preferences"):
                return CartographerStatusService()

    def test_create_subscription(self, status_service):
        """Should create new subscription"""
        sub = status_service.create_or_update_subscription(
            user_id="user-123",
            email_address="test@example.com",
            cartographer_up_enabled=True,
            cartographer_down_enabled=True,
        )

        assert sub.user_id == "user-123"
        assert sub.email_address == "test@example.com"
        assert sub.cartographer_up_enabled is True

    def test_create_subscription_requires_email(self, status_service):
        """Should require email for new subscription"""
        with pytest.raises(ValueError, match="email_address is required"):
            status_service.create_or_update_subscription(
                user_id="user-123",
            )

    def test_update_subscription(self, status_service):
        """Should update existing subscription"""
        status_service.create_or_update_subscription(
            user_id="user-123",
            email_address="old@example.com",
        )

        sub = status_service.create_or_update_subscription(
            user_id="user-123",
            email_address="new@example.com",
            cartographer_up_enabled=False,
        )

        assert sub.email_address == "new@example.com"
        assert sub.cartographer_up_enabled is False

    def test_get_subscription(self, status_service):
        """Should get subscription by user ID"""
        status_service.create_or_update_subscription(
            user_id="user-123",
            email_address="test@example.com",
        )

        sub = status_service.get_subscription("user-123")

        assert sub is not None
        assert sub.user_id == "user-123"

    def test_get_subscription_not_found(self, status_service):
        """Should return None for unknown user"""
        sub = status_service.get_subscription("unknown-user")
        assert sub is None

    def test_delete_subscription(self, status_service):
        """Should delete subscription"""
        status_service.create_or_update_subscription(
            user_id="user-123",
            email_address="test@example.com",
        )

        result = status_service.delete_subscription("user-123")

        assert result is True
        assert status_service.get_subscription("user-123") is None

    def test_delete_subscription_not_found(self, status_service):
        """Should return False when deleting non-existent subscription"""
        result = status_service.delete_subscription("unknown-user")
        assert result is False

    def test_get_all_subscriptions(self, status_service):
        """Should return all subscriptions"""
        status_service.create_or_update_subscription(
            user_id="user-1",
            email_address="user1@example.com",
        )
        status_service.create_or_update_subscription(
            user_id="user-2",
            email_address="user2@example.com",
        )

        all_subs = status_service.get_all_subscriptions()

        assert len(all_subs) == 2


class TestCartographerStatusSubscribers:
    """Tests for subscriber filtering in CartographerStatusService"""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        yield tmp_path

    @pytest.fixture
    def status_service(self, temp_data_dir):
        with patch(
            "app.services.cartographer_status.SUBSCRIPTIONS_FILE", temp_data_dir / "subs.json"
        ):
            from app.services.cartographer_status import CartographerStatusService

            with patch.object(CartographerStatusService, "_migrate_from_global_preferences"):
                return CartographerStatusService()

    def test_get_subscribers_for_cartographer_up(self, status_service):
        """Should get subscribers for CARTOGRAPHER_UP event"""
        from app.models import NotificationType

        status_service.create_or_update_subscription(
            user_id="user-1",
            email_address="user1@example.com",
            cartographer_up_enabled=True,
            email_enabled=True,
        )
        status_service.create_or_update_subscription(
            user_id="user-2",
            email_address="user2@example.com",
            cartographer_up_enabled=False,
            email_enabled=True,
        )

        subs = status_service.get_subscribers_for_event(NotificationType.CARTOGRAPHER_UP)

        assert len(subs) == 1
        assert subs[0].user_id == "user-1"

    def test_get_subscribers_for_cartographer_down(self, status_service):
        """Should get subscribers for CARTOGRAPHER_DOWN event"""
        from app.models import NotificationType

        status_service.create_or_update_subscription(
            user_id="user-1",
            email_address="user1@example.com",
            cartographer_down_enabled=True,
            email_enabled=True,
        )

        subs = status_service.get_subscribers_for_event(NotificationType.CARTOGRAPHER_DOWN)

        assert len(subs) == 1

    def test_get_subscribers_for_other_event(self, status_service):
        """Should return empty for non-cartographer events"""
        from app.models import NotificationType

        status_service.create_or_update_subscription(
            user_id="user-1",
            email_address="user1@example.com",
            email_enabled=True,
        )

        subs = status_service.get_subscribers_for_event(NotificationType.DEVICE_OFFLINE)

        assert len(subs) == 0


class TestCartographerStatusSubscriptionModel:
    """Tests for CartographerStatusSubscription model"""

    def test_subscription_to_dict_and_from_dict(self):
        """Should serialize and deserialize subscription"""
        from app.services.cartographer_status import CartographerStatusSubscription

        sub = CartographerStatusSubscription(
            user_id="user-123",
            email_address="test@example.com",
            cartographer_up_enabled=True,
            discord_enabled=True,
            discord_user_id="discord-123",
        )

        data = sub.to_dict()
        restored = CartographerStatusSubscription.from_dict(data)

        assert restored.user_id == "user-123"
        assert restored.email_address == "test@example.com"
        assert restored.discord_user_id == "discord-123"

    def test_subscription_defaults(self):
        """Should have correct defaults"""
        from app.services.cartographer_status import CartographerStatusSubscription

        sub = CartographerStatusSubscription(
            user_id="user-123",
            email_address="test@example.com",
        )

        assert sub.cartographer_up_enabled is True
        assert sub.cartographer_down_enabled is True
        assert sub.email_enabled is False
        assert sub.discord_enabled is False

    def test_subscription_with_all_fields(self):
        """Should create subscription with all fields"""
        from app.services.cartographer_status import CartographerStatusSubscription

        sub = CartographerStatusSubscription(
            user_id="user-123",
            email_address="test@example.com",
            cartographer_up_enabled=True,
            cartographer_down_enabled=True,
            email_enabled=True,
            discord_enabled=True,
            discord_delivery_method="dm",
            discord_guild_id="guild-123",
            discord_channel_id="channel-123",
            discord_user_id="discord-123",
            minimum_priority="high",
            quiet_hours_enabled=True,
            quiet_hours_start="22:00",
            quiet_hours_end="08:00",
            timezone="America/New_York",
        )

        assert sub.discord_user_id == "discord-123"
        assert sub.timezone == "America/New_York"


class TestCartographerStatusRouter:
    """Tests for Cartographer status router endpoints"""

    @pytest.fixture
    def test_client(self):
        from fastapi.testclient import TestClient

        from app.main import app

        return TestClient(app)

    def test_get_subscription_not_found(self, test_client):
        """Should return default subscription when not subscribed"""
        with patch("app.routers.cartographer_status.cartographer_status_service") as mock_svc:
            mock_svc.get_subscription.return_value = None

            response = test_client.get(
                "/api/cartographer-status/subscription", headers={"X-User-Id": "user-123"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["subscribed"] is False

    def test_get_subscription_found(self, test_client):
        """Should return subscription when exists"""
        with patch("app.routers.cartographer_status.cartographer_status_service") as mock_svc:
            from app.services.cartographer_status import CartographerStatusSubscription

            mock_sub = CartographerStatusSubscription(
                user_id="user-123",
                email_address="test@example.com",
            )
            mock_svc.get_subscription.return_value = mock_sub

            response = test_client.get(
                "/api/cartographer-status/subscription", headers={"X-User-Id": "user-123"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["subscribed"] is True

    def test_delete_subscription_not_found(self, test_client):
        """Should return 404 when subscription not found"""
        with patch("app.routers.cartographer_status.cartographer_status_service") as mock_svc:
            mock_svc.delete_subscription.return_value = False

            response = test_client.delete(
                "/api/cartographer-status/subscription", headers={"X-User-Id": "user-123"}
            )

            assert response.status_code == 404

    def test_delete_subscription_success(self, test_client):
        """Should delete subscription successfully"""
        with patch("app.routers.cartographer_status.cartographer_status_service") as mock_svc:
            mock_svc.delete_subscription.return_value = True

            response = test_client.delete(
                "/api/cartographer-status/subscription", headers={"X-User-Id": "user-123"}
            )

            assert response.status_code == 200
            assert response.json()["success"] is True

    def test_create_subscription_no_email_service(self, test_client):
        """Should fail when email not configured"""
        with patch("app.routers.cartographer_status.is_email_configured") as mock_email:
            mock_email.return_value = False

            response = test_client.post(
                "/api/cartographer-status/subscription",
                headers={"X-User-Id": "user-123"},
                json={"email_address": "test@example.com"},
            )

            assert response.status_code == 503

    def test_create_subscription_success(self, test_client):
        """Should create subscription successfully"""
        with patch("app.routers.cartographer_status.is_email_configured") as mock_email:
            mock_email.return_value = True

            with patch("app.routers.cartographer_status.cartographer_status_service") as mock_svc:
                from app.services.cartographer_status import CartographerStatusSubscription

                mock_sub = CartographerStatusSubscription(
                    user_id="user-123",
                    email_address="test@example.com",
                )
                mock_svc.create_or_update_subscription.return_value = mock_sub

                response = test_client.post(
                    "/api/cartographer-status/subscription",
                    headers={"X-User-Id": "user-123"},
                    json={"email_address": "test@example.com"},
                )

                assert response.status_code == 200


class TestCartographerStatusNotify:
    """Tests for cartographer status notify endpoint"""

    @pytest.fixture
    def test_client(self):
        from fastapi.testclient import TestClient

        from app.main import app

        return TestClient(app)

    def test_notify_invalid_event_type(self, test_client):
        """Should reject invalid event type"""
        response = test_client.post(
            "/api/cartographer-status/notify", json={"event_type": "invalid"}
        )

        assert response.status_code == 400

    def test_notify_up_event(self, test_client):
        """Should handle up event"""
        with patch("app.routers.cartographer_status.cartographer_status_service") as mock_svc:
            mock_svc.get_subscribers_for_event.return_value = []

            response = test_client.post(
                "/api/cartographer-status/notify", json={"event_type": "up"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["subscribers_notified"] == 0

    def test_notify_down_event(self, test_client):
        """Should handle down event"""
        with patch("app.routers.cartographer_status.cartographer_status_service") as mock_svc:
            mock_svc.get_subscribers_for_event.return_value = []

            response = test_client.post(
                "/api/cartographer-status/notify",
                json={
                    "event_type": "down",
                    "message": "Service is down",
                    "affected_services": ["api", "web"],
                },
            )

            assert response.status_code == 200

    def test_notify_with_email_subscriber(self, test_client):
        """Should send email to subscriber"""
        with patch("app.routers.cartographer_status.cartographer_status_service") as mock_svc:
            from app.services.cartographer_status import CartographerStatusSubscription

            mock_sub = CartographerStatusSubscription(
                user_id="user-123",
                email_address="test@example.com",
                email_enabled=True,
                cartographer_up_enabled=True,
            )
            mock_svc.get_subscribers_for_event.return_value = [mock_sub]

            with patch("app.routers.cartographer_status.is_email_configured") as mock_email_cfg:
                mock_email_cfg.return_value = True

                with patch(
                    "app.routers.cartographer_status.is_discord_configured"
                ) as mock_discord_cfg:
                    mock_discord_cfg.return_value = False

                    with patch(
                        "app.routers.cartographer_status.send_notification_email"
                    ) as mock_send:
                        mock_record = MagicMock()
                        mock_record.success = True
                        mock_send.return_value = mock_record

                        response = test_client.post(
                            "/api/cartographer-status/notify", json={"event_type": "up"}
                        )

                        assert response.status_code == 200
                        data = response.json()
                        assert data["subscribers_notified"] == 1

    def test_notify_with_no_services_configured(self, test_client):
        """Should handle subscribers with no notification services"""
        with patch("app.routers.cartographer_status.cartographer_status_service") as mock_svc:
            from app.services.cartographer_status import CartographerStatusSubscription

            mock_sub = CartographerStatusSubscription(
                user_id="user-123",
                email_address="test@example.com",
                email_enabled=True,
            )
            mock_svc.get_subscribers_for_event.return_value = [mock_sub]

            with patch("app.routers.cartographer_status.is_email_configured") as mock_email:
                mock_email.return_value = False
                with patch("app.routers.cartographer_status.is_discord_configured") as mock_discord:
                    mock_discord.return_value = False

                    response = test_client.post(
                        "/api/cartographer-status/notify", json={"event_type": "up"}
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is False


class TestCartographerStatusTestDiscord:
    """Tests for test discord endpoint"""

    @pytest.fixture
    def test_client(self):
        from fastapi.testclient import TestClient

        from app.main import app

        return TestClient(app)

    def test_test_discord_no_config(self, test_client):
        """Should fail when Discord not configured"""
        with patch("app.routers.cartographer_status.is_discord_configured") as mock_discord:
            mock_discord.return_value = False

            response = test_client.post(
                "/api/cartographer-status/test/discord", headers={"X-User-Id": "user-123"}, json={}
            )

            assert response.status_code in [400, 503]

    def test_test_discord_no_target(self, test_client):
        """Should fail when no channel or user specified"""
        with patch("app.routers.cartographer_status.is_discord_configured") as mock_discord:
            mock_discord.return_value = True

            response = test_client.post(
                "/api/cartographer-status/test/discord", headers={"X-User-Id": "user-123"}, json={}
            )

            assert response.status_code == 400

    def test_test_discord_with_channel(self, test_client):
        """Should test Discord with channel ID"""
        with patch("app.routers.cartographer_status.is_discord_configured") as mock_cfg:
            mock_cfg.return_value = True

            with patch("app.routers.cartographer_status.discord_service") as mock_svc:
                mock_svc.send_test_notification = AsyncMock(return_value={"success": True})

                response = test_client.post(
                    "/api/cartographer-status/test/discord",
                    headers={"X-User-Id": "user-123"},
                    json={"channel_id": "channel-123"},
                )

                assert response.status_code == 200
