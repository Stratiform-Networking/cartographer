"""
Extended tests for notifications router to improve coverage.

Covers:
- Health check processing
- Service status endpoints
- Scheduled broadcasts management
- Version checking endpoints
- Global preferences endpoints
"""

import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Set test environment
os.environ["NOTIFICATION_DATA_DIR"] = "/tmp/test_notification_data_router"
os.environ["RESEND_API_KEY"] = ""
os.environ["DISCORD_BOT_TOKEN"] = ""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models import (
    NetworkEvent,
    NotificationPriority,
    NotificationType,
    ScheduledBroadcastStatus,
)
from app.routers.notifications import router


@pytest.fixture
def test_app():
    """Create test FastAPI app with router."""
    app = FastAPI()
    app.include_router(router, prefix="/api/notifications")
    return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


class TestServiceStatusEndpoint:
    """Tests for service status endpoint."""

    def test_get_service_status(self, client):
        """Test getting service status."""
        with (
            patch("app.routers.notifications.is_email_configured", return_value=True),
            patch("app.routers.notifications.is_discord_configured", return_value=True),
            patch("app.routers.notifications.discord_service") as mock_discord,
            patch("app.routers.notifications.anomaly_detector") as mock_anomaly,
            patch("app.routers.notifications.version_checker") as mock_version,
        ):

            mock_discord._client = MagicMock()
            mock_discord._ready.is_set.return_value = True
            mock_anomaly.get_model_status.return_value = MagicMock(
                model_dump=lambda: {"status": "ok"}
            )
            mock_version.get_status.return_value = {"current_version": "0.1.0"}

            response = client.get("/api/notifications/status")

            assert response.status_code == 200
            data = response.json()
            assert "email_configured" in data
            assert "discord_configured" in data


class TestDiscordEndpoints:
    """Tests for Discord endpoints."""

    def test_get_discord_info(self, client):
        """Test getting Discord bot info."""
        from app.models import DiscordBotInfo

        with patch("app.routers.notifications.discord_service") as mock_discord:
            mock_discord.get_bot_info.return_value = DiscordBotInfo(
                is_connected=True,
                bot_name="Test Bot",
                bot_id="123456789",
                invite_url="https://discord.com/invite/test",
            )

            response = client.get("/api/notifications/discord/info")

            assert response.status_code == 200

    def test_get_discord_guilds_not_configured(self, client):
        """Test getting guilds when Discord not configured."""
        with patch("app.routers.notifications.is_discord_configured", return_value=False):
            response = client.get("/api/notifications/discord/guilds")

            assert response.status_code == 503

    def test_get_discord_guilds_configured(self, client):
        """Test getting guilds when Discord is configured."""
        with (
            patch("app.routers.notifications.is_discord_configured", return_value=True),
            patch("app.routers.notifications.discord_service") as mock_discord,
        ):

            mock_discord.get_guilds = AsyncMock(return_value=[])

            response = client.get("/api/notifications/discord/guilds")

            assert response.status_code == 200

    def test_get_discord_channels_not_configured(self, client):
        """Test getting channels when Discord not configured."""
        with patch("app.routers.notifications.is_discord_configured", return_value=False):
            response = client.get("/api/notifications/discord/guilds/123/channels")

            assert response.status_code == 503

    def test_get_discord_channels_configured(self, client):
        """Test getting channels when Discord is configured."""
        with (
            patch("app.routers.notifications.is_discord_configured", return_value=True),
            patch("app.routers.notifications.discord_service") as mock_discord,
        ):

            mock_discord.get_channels = AsyncMock(return_value=[])

            response = client.get("/api/notifications/discord/guilds/123/channels")

            assert response.status_code == 200

    def test_get_discord_invite_url(self, client):
        """Test getting invite URL."""
        with patch(
            "app.routers.notifications.get_bot_invite_url",
            return_value="https://discord.com/invite/test",
        ):
            response = client.get("/api/notifications/discord/invite-url")

            assert response.status_code == 200
            assert "invite_url" in response.json()

    def test_get_discord_invite_url_not_configured(self, client):
        """Test getting invite URL when not configured."""
        with patch("app.routers.notifications.get_bot_invite_url", return_value=None):
            response = client.get("/api/notifications/discord/invite-url")

            assert response.status_code == 503


class TestMLEndpoints:
    """Tests for ML/anomaly detection endpoints."""

    def test_get_device_baseline_not_found(self, client):
        """Test getting non-existent device baseline."""
        with patch("app.routers.notifications.network_anomaly_detector_manager") as mock_manager:
            mock_detector = MagicMock()
            mock_detector.get_device_baseline.return_value = None
            mock_manager.get_detector.return_value = mock_detector

            response = client.get(
                "/api/notifications/ml/baseline/192.168.1.1?network_id=test-network"
            )

            assert response.status_code == 404

    def test_mark_false_positive(self, client):
        """Test marking event as false positive."""
        with patch("app.routers.notifications.anomaly_detector") as mock_detector:
            response = client.post(
                "/api/notifications/ml/feedback/false-positive?event_id=test-event"
            )

            assert response.status_code == 200
            mock_detector.mark_false_positive.assert_called_once()

    def test_reset_device_baseline(self, client):
        """Test resetting device baseline."""
        with patch("app.routers.notifications.network_anomaly_detector_manager") as mock_manager:
            mock_detector = MagicMock()
            mock_manager.get_detector.return_value = mock_detector

            response = client.delete(
                "/api/notifications/ml/baseline/192.168.1.1?network_id=test-network"
            )

            assert response.status_code == 200

    def test_reset_all_ml_data(self, client):
        """Test resetting all ML data."""
        with patch("app.routers.notifications.anomaly_detector") as mock_detector:
            response = client.delete("/api/notifications/ml/reset")

            assert response.status_code == 200
            mock_detector.reset_all.assert_called_once()

    def test_reset_network_ml_data(self, client):
        """Test resetting per-network ML data."""
        with patch("app.routers.notifications.network_anomaly_detector_manager") as mock_manager:
            mock_detector = MagicMock()
            mock_manager.get_detector.return_value = mock_detector

            response = client.delete("/api/notifications/ml/reset?network_id=test-network")

            assert response.status_code == 200

    def test_sync_devices(self, client):
        """Test syncing devices for ML tracking."""
        with patch("app.routers.notifications.network_anomaly_detector_manager") as mock_manager:
            mock_detector = MagicMock()
            mock_manager.get_detector.return_value = mock_detector

            response = client.post(
                "/api/notifications/ml/sync-devices?network_id=test-network",
                json=["192.168.1.1", "192.168.1.2"],
            )

            assert response.status_code == 200
            data = response.json()
            assert data["devices_synced"] == 2


class TestHealthCheckProcessing:
    """Tests for health check processing endpoint."""

    def test_process_health_check_no_event(self, client):
        """Test processing health check that doesn't create event."""
        with patch("app.routers.notifications.network_anomaly_detector_manager") as mock_manager:
            mock_manager.process_health_check.return_value = None

            response = client.post(
                "/api/notifications/process-health-check",
                params={
                    "device_ip": "192.168.1.1",
                    "success": True,
                    "network_id": "test-network",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["event_created"] is False


class TestSendNotificationEndpoints:
    """Tests for notification sending endpoints."""

    def test_send_network_notification_with_user_ids(self, client):
        """Test sending network notification with user IDs."""
        with patch("app.routers.notifications.notification_manager") as mock_manager:
            mock_manager.send_notification_to_network_members = AsyncMock(
                return_value={"user1": [MagicMock(success=True)]}
            )

            response = client.post(
                "/api/notifications/networks/test-network/send-notification",
                json={
                    "event_type": "device_offline",
                    "priority": "high",
                    "title": "Test",
                    "message": "Test message",
                    "user_ids": ["user1"],
                },
            )

            assert response.status_code == 200

    def test_send_network_notification_network_level(self, client):
        """Test sending network-level notification."""
        with patch("app.routers.notifications.notification_manager") as mock_manager:
            mock_manager.send_notification_to_network = AsyncMock(
                return_value=[MagicMock(success=True, model_dump=lambda: {"success": True})]
            )

            response = client.post(
                "/api/notifications/networks/test-network/send-notification",
                json={
                    "event_type": "device_offline",
                    "priority": "high",
                    "title": "Test",
                    "message": "Test message",
                },
            )

            assert response.status_code == 200

    def test_send_manual_notification_deprecated(self, client):
        """Test deprecated manual notification with user_id."""
        response = client.post(
            "/api/notifications/send-notification?user_id=test-user",
            json={
                "event_type": "device_offline",
                "priority": "high",
                "title": "Test",
                "message": "Test message",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "deprecated" in data["error"]

    def test_send_manual_notification_broadcast(self, client):
        """Test manual notification broadcast."""
        with patch("app.routers.notifications.notification_manager") as mock_manager:
            mock_manager.broadcast_notification = AsyncMock(return_value={})

            response = client.post(
                "/api/notifications/send-notification",
                json={
                    "event_type": "device_offline",
                    "priority": "high",
                    "title": "Test",
                    "message": "Test message",
                },
            )

            assert response.status_code == 200


class TestScheduledBroadcastEndpoints:
    """Tests for scheduled broadcast endpoints."""

    def test_get_scheduled_broadcasts(self, client):
        """Test getting scheduled broadcasts."""
        with patch("app.routers.notifications.notification_manager") as mock_manager:
            mock_manager.get_scheduled_broadcasts.return_value = MagicMock(
                broadcasts=[],
                total_count=0,
            )

            response = client.get("/api/notifications/scheduled")

            assert response.status_code == 200

    def test_create_scheduled_broadcast_past_time(self, client):
        """Test creating scheduled broadcast with past time."""
        past_time = datetime.utcnow() - timedelta(hours=1)

        response = client.post(
            "/api/notifications/scheduled",
            json={
                "title": "Test",
                "message": "Test message",
                "scheduled_at": past_time.isoformat(),
                "network_id": "test-network",
            },
            headers={"X-Username": "testuser"},
        )

        assert response.status_code == 400

    def test_get_scheduled_broadcast_not_found(self, client):
        """Test getting non-existent scheduled broadcast."""
        with patch("app.routers.notifications.notification_manager") as mock_manager:
            mock_manager.get_scheduled_broadcast.return_value = None

            response = client.get("/api/notifications/scheduled/nonexistent")

            assert response.status_code == 404

    def test_update_scheduled_broadcast_past_time(self, client):
        """Test updating scheduled broadcast with past time."""
        past_time = datetime.utcnow() - timedelta(hours=1)

        response = client.patch(
            "/api/notifications/scheduled/test-id",
            json={
                "scheduled_at": past_time.isoformat(),
            },
        )

        assert response.status_code == 400

    def test_update_scheduled_broadcast_not_found(self, client):
        """Test updating non-existent scheduled broadcast."""
        with patch("app.routers.notifications.notification_manager") as mock_manager:
            mock_manager.update_scheduled_broadcast.return_value = None

            response = client.patch(
                "/api/notifications/scheduled/nonexistent", json={"title": "Updated"}
            )

            assert response.status_code == 400

    def test_cancel_scheduled_broadcast(self, client):
        """Test cancelling scheduled broadcast."""
        with patch("app.routers.notifications.notification_manager") as mock_manager:
            mock_manager.cancel_scheduled_broadcast.return_value = True

            response = client.post("/api/notifications/scheduled/test-id/cancel")

            assert response.status_code == 200

    def test_cancel_scheduled_broadcast_failed(self, client):
        """Test cancelling broadcast that can't be cancelled."""
        with patch("app.routers.notifications.notification_manager") as mock_manager:
            mock_manager.cancel_scheduled_broadcast.return_value = False

            response = client.post("/api/notifications/scheduled/test-id/cancel")

            assert response.status_code == 400

    def test_delete_scheduled_broadcast(self, client):
        """Test deleting scheduled broadcast."""
        with patch("app.routers.notifications.notification_manager") as mock_manager:
            mock_manager.delete_scheduled_broadcast.return_value = True

            response = client.delete("/api/notifications/scheduled/test-id")

            assert response.status_code == 200

    def test_delete_scheduled_broadcast_failed(self, client):
        """Test deleting broadcast that can't be deleted."""
        with patch("app.routers.notifications.notification_manager") as mock_manager:
            mock_manager.delete_scheduled_broadcast.return_value = False

            response = client.delete("/api/notifications/scheduled/test-id")

            assert response.status_code == 400

    def test_mark_broadcast_seen(self, client):
        """Test marking broadcast as seen."""
        with patch("app.routers.notifications.notification_manager") as mock_manager:
            mock_manager.mark_broadcast_seen.return_value = MagicMock(
                seen_at=datetime.utcnow(),
            )

            response = client.post("/api/notifications/scheduled/test-id/seen")

            assert response.status_code == 200

    def test_mark_broadcast_seen_not_found(self, client):
        """Test marking non-existent broadcast as seen."""
        with patch("app.routers.notifications.notification_manager") as mock_manager:
            mock_manager.mark_broadcast_seen.return_value = None

            response = client.post("/api/notifications/scheduled/nonexistent/seen")

            assert response.status_code == 404


class TestSilencedDevicesEndpoints:
    """Tests for silenced devices endpoints."""

    def test_get_silenced_devices(self, client):
        """Test getting silenced devices."""
        with patch("app.routers.notifications.notification_manager") as mock_manager:
            mock_manager.get_silenced_devices.return_value = ["192.168.1.1"]

            response = client.get("/api/notifications/silenced-devices")

            assert response.status_code == 200
            data = response.json()
            assert "192.168.1.1" in data["devices"]

    def test_set_silenced_devices(self, client):
        """Test setting silenced devices."""
        with patch("app.routers.notifications.notification_manager") as mock_manager:
            response = client.post(
                "/api/notifications/silenced-devices", json=["192.168.1.1", "192.168.1.2"]
            )

            assert response.status_code == 200
            mock_manager.set_silenced_devices.assert_called_once()

    def test_silence_device(self, client):
        """Test silencing a device."""
        with patch("app.routers.notifications.notification_manager") as mock_manager:
            mock_manager.silence_device.return_value = True

            response = client.post("/api/notifications/silenced-devices/192.168.1.1")

            assert response.status_code == 200

    def test_unsilence_device(self, client):
        """Test unsilencing a device."""
        with patch("app.routers.notifications.notification_manager") as mock_manager:
            mock_manager.unsilence_device.return_value = True

            response = client.delete("/api/notifications/silenced-devices/192.168.1.1")

            assert response.status_code == 200

    def test_check_device_silenced(self, client):
        """Test checking if device is silenced."""
        with patch("app.routers.notifications.notification_manager") as mock_manager:
            mock_manager.is_device_silenced.return_value = True

            response = client.get("/api/notifications/silenced-devices/192.168.1.1")

            assert response.status_code == 200
            data = response.json()
            assert data["silenced"] is True


class TestGlobalPreferencesEndpoints:
    """Tests for global preferences endpoints."""

    def test_update_global_preferences(self, client):
        """Test updating global preferences."""
        with patch("app.routers.notifications.notification_manager") as mock_manager:
            mock_manager.update_global_preferences.return_value = MagicMock(
                user_id="test-user",
                email_address="test@example.com",
            )

            response = client.put(
                "/api/notifications/global/preferences",
                json={"email_address": "test@example.com"},
                headers={"X-User-Id": "test-user"},
            )

            assert response.status_code == 200


class TestVersionEndpoints:
    """Tests for version checking endpoints."""

    def test_get_version_status(self, client):
        """Test getting version status."""
        with patch("app.routers.notifications.version_checker") as mock_checker:
            mock_checker.get_status.return_value = {
                "current_version": "0.1.0",
                "is_running": True,
            }

            response = client.get("/api/notifications/version")

            assert response.status_code == 200

    def test_check_for_updates(self, client):
        """Test checking for updates."""
        with patch("app.routers.notifications.version_checker") as mock_checker:
            mock_checker.check_now = AsyncMock(
                return_value={
                    "success": True,
                    "has_update": False,
                }
            )

            response = client.post("/api/notifications/version/check")

            assert response.status_code == 200

    def test_send_version_notification(self, client):
        """Test sending version notification."""
        with patch("app.routers.notifications.version_checker") as mock_checker:
            mock_checker.check_now = AsyncMock(
                return_value={
                    "success": True,
                    "notification_sent": True,
                }
            )

            response = client.post("/api/notifications/version/notify")

            assert response.status_code == 200


class TestServiceStatusNotificationEndpoints:
    """Tests for service status notification endpoints."""

    def test_notify_cartographer_up_not_configured(self, client):
        """Test up notification when email not configured."""
        with patch("app.routers.notifications.is_email_configured", return_value=False):
            response = client.post("/api/notifications/service-status/up")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False

    def test_notify_cartographer_down_not_configured(self, client):
        """Test down notification when email not configured."""
        with patch("app.routers.notifications.is_email_configured", return_value=False):
            response = client.post("/api/notifications/service-status/down")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
