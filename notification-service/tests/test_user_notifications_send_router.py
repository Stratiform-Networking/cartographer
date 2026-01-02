"""
Tests for User Notifications Send Router endpoints.

Tests the API endpoints for sending notifications to network users.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.models import NotificationChannel, NotificationPriority


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


class TestSendNetworkNotification:
    """Tests for send network notification endpoint"""

    def test_send_network_notification_success(self, test_client):
        """Should send notification to network users"""
        with patch(
            "app.routers.user_notifications_send.notification_dispatch_service"
        ) as mock_dispatch:
            with patch("app.routers.user_notifications_send.get_db") as mock_get_db:
                mock_record = MagicMock()
                mock_record.success = True

                mock_dispatch.send_to_network_users = AsyncMock(
                    return_value={
                        "user-1": [mock_record],
                        "user-2": [mock_record],
                    }
                )

                mock_db = AsyncMock()

                async def mock_db_gen():
                    yield mock_db

                mock_get_db.return_value = mock_db_gen()

                response = test_client.post(
                    "/api/networks/network-uuid/notifications/send",
                    json={
                        "user_ids": ["user-1", "user-2"],
                        "type": "device_offline",
                        "priority": "high",
                        "title": "Test Alert",
                        "message": "This is a test notification",
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["users_notified"] == 2

    def test_send_network_notification_invalid_type(self, test_client):
        """Should return 400 for invalid notification type"""
        with patch("app.routers.user_notifications_send.get_db") as mock_get_db:
            mock_db = AsyncMock()

            async def mock_db_gen():
                yield mock_db

            mock_get_db.return_value = mock_db_gen()

            response = test_client.post(
                "/api/networks/network-uuid/notifications/send",
                json={
                    "user_ids": ["user-1"],
                    "type": "invalid_type",
                    "priority": "high",
                    "title": "Test",
                    "message": "Test",
                },
            )

            assert response.status_code == 400

    def test_send_network_notification_invalid_priority(self, test_client):
        """Should return 400 for invalid priority"""
        with patch("app.routers.user_notifications_send.get_db") as mock_get_db:
            mock_db = AsyncMock()

            async def mock_db_gen():
                yield mock_db

            mock_get_db.return_value = mock_db_gen()

            response = test_client.post(
                "/api/networks/network-uuid/notifications/send",
                json={
                    "user_ids": ["user-1"],
                    "type": "device_offline",
                    "priority": "invalid_priority",
                    "title": "Test",
                    "message": "Test",
                },
            )

            assert response.status_code == 400

    def test_send_network_notification_scheduled(self, test_client):
        """Should handle scheduled notifications"""
        with patch(
            "app.routers.user_notifications_send.notification_dispatch_service"
        ) as mock_dispatch:
            with patch("app.routers.user_notifications_send.get_db") as mock_get_db:
                mock_record = MagicMock()
                mock_record.success = True

                mock_dispatch.send_to_network_users = AsyncMock(
                    return_value={
                        "user-1": [mock_record],
                    }
                )

                mock_db = AsyncMock()

                async def mock_db_gen():
                    yield mock_db

                mock_get_db.return_value = mock_db_gen()

                future_time = (datetime.now(timezone.utc).isoformat()).replace("+00:00", "Z")

                response = test_client.post(
                    "/api/networks/network-uuid/notifications/send",
                    json={
                        "user_ids": ["user-1"],
                        "type": "scheduled_maintenance",
                        "priority": "medium",
                        "title": "Scheduled Maintenance",
                        "message": "System maintenance scheduled",
                        "scheduled_at": future_time,
                    },
                )

                assert response.status_code == 200

    def test_send_network_notification_invalid_scheduled_at(self, test_client):
        """Should return 400 for invalid scheduled_at format"""
        with patch("app.routers.user_notifications_send.get_db") as mock_get_db:
            mock_db = AsyncMock()

            async def mock_db_gen():
                yield mock_db

            mock_get_db.return_value = mock_db_gen()

            response = test_client.post(
                "/api/networks/network-uuid/notifications/send",
                json={
                    "user_ids": ["user-1"],
                    "type": "device_offline",
                    "priority": "high",
                    "title": "Test",
                    "message": "Test",
                    "scheduled_at": "invalid-date-format",
                },
            )

            assert response.status_code == 400

    def test_send_network_notification_no_users(self, test_client):
        """Should handle empty user list"""
        with patch(
            "app.routers.user_notifications_send.notification_dispatch_service"
        ) as mock_dispatch:
            with patch("app.routers.user_notifications_send.get_db") as mock_get_db:
                mock_dispatch.send_to_network_users = AsyncMock(return_value={})

                mock_db = AsyncMock()

                async def mock_db_gen():
                    yield mock_db

                mock_get_db.return_value = mock_db_gen()

                response = test_client.post(
                    "/api/networks/network-uuid/notifications/send",
                    json={
                        "user_ids": [],
                        "type": "device_offline",
                        "priority": "high",
                        "title": "Test",
                        "message": "Test",
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["users_notified"] == 0

    def test_send_network_notification_partial_success(self, test_client):
        """Should handle partial success (some users notified)"""
        with patch(
            "app.routers.user_notifications_send.notification_dispatch_service"
        ) as mock_dispatch:
            with patch("app.routers.user_notifications_send.get_db") as mock_get_db:
                success_record = MagicMock()
                success_record.success = True

                fail_record = MagicMock()
                fail_record.success = False

                mock_dispatch.send_to_network_users = AsyncMock(
                    return_value={
                        "user-1": [success_record],
                        "user-2": [fail_record],
                        "user-3": [success_record],
                    }
                )

                mock_db = AsyncMock()

                async def mock_db_gen():
                    yield mock_db

                mock_get_db.return_value = mock_db_gen()

                response = test_client.post(
                    "/api/networks/network-uuid/notifications/send",
                    json={
                        "user_ids": ["user-1", "user-2", "user-3"],
                        "type": "device_offline",
                        "priority": "high",
                        "title": "Test",
                        "message": "Test",
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["users_notified"] == 2  # 2 successful


class TestSendNetworkNotificationRequestModel:
    """Tests for SendNetworkNotificationRequest model"""

    def test_request_model_validation(self):
        """Should validate request model fields"""
        from app.routers.user_notifications_send import SendNetworkNotificationRequest

        request = SendNetworkNotificationRequest(
            user_ids=["user-1", "user-2"],
            type="device_offline",
            priority="high",
            title="Test Alert",
            message="This is a test",
        )

        assert len(request.user_ids) == 2
        assert request.type == "device_offline"
        assert request.priority == "high"

    def test_request_model_with_scheduled_at(self):
        """Should accept scheduled_at field"""
        from app.routers.user_notifications_send import SendNetworkNotificationRequest

        request = SendNetworkNotificationRequest(
            user_ids=["user-1"],
            type="scheduled_maintenance",
            priority="medium",
            title="Maintenance",
            message="Scheduled",
            scheduled_at="2024-12-31T23:59:59Z",
        )

        assert request.scheduled_at == "2024-12-31T23:59:59Z"

    def test_request_model_optional_scheduled_at(self):
        """Should allow None for scheduled_at"""
        from app.routers.user_notifications_send import SendNetworkNotificationRequest

        request = SendNetworkNotificationRequest(
            user_ids=["user-1"],
            type="device_offline",
            priority="high",
            title="Alert",
            message="Message",
        )

        assert request.scheduled_at is None
