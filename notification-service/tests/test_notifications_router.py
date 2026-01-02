"""
Unit tests for the notifications router endpoints.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.models import (
    DeviceBaseline,
    DiscordBotInfo,
    DiscordChannel,
    DiscordChannelsResponse,
    DiscordGuild,
    DiscordGuildsResponse,
    MLModelStatus,
    NetworkEvent,
    NotificationChannel,
    NotificationPreferences,
    NotificationPriority,
    NotificationRecord,
    NotificationType,
    ScheduledBroadcast,
    ScheduledBroadcastCreate,
    ScheduledBroadcastStatus,
)


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


class TestPreferencesEndpoints:
    """Tests for preferences endpoints"""

    def test_get_preferences(self, test_client):
        """Should return network preferences"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            default_prefs = NotificationPreferences(
                network_id="network_uuid_123",
            )
            mock_nm.get_preferences.return_value = default_prefs

            response = test_client.get(
                "/api/notifications/networks/network_uuid_123/preferences",
                headers={"X-User-Id": "user_123"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["network_id"] == "network_uuid_123"

    def test_update_preferences(self, test_client):
        """Should update preferences"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            updated_prefs = NotificationPreferences(
                network_id="network_uuid_123",
            )
            mock_nm.update_preferences.return_value = updated_prefs

            response = test_client.put(
                "/api/notifications/networks/network_uuid_123/preferences",
                headers={"X-User-Id": "user_123"},
                json={"enabled": True},
            )

            assert response.status_code == 200

    def test_delete_preferences(self, test_client):
        """Should delete preferences"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            mock_nm.delete_preferences.return_value = True

            response = test_client.delete(
                "/api/notifications/networks/network_uuid_123/preferences",
                headers={"X-User-Id": "user_123"},
            )

            assert response.status_code == 200


class TestServiceStatusEndpoints:
    """Tests for service status endpoints"""

    def test_get_status(self, test_client):
        """Should return service status"""
        with patch("app.routers.notifications.is_email_configured", return_value=True):
            with patch("app.routers.notifications.is_discord_configured", return_value=True):
                with patch("app.routers.notifications.discord_service") as mock_ds:
                    mock_ds._client = MagicMock()
                    mock_ds._ready = MagicMock()
                    mock_ds._ready.is_set.return_value = True

                    with patch("app.routers.notifications.anomaly_detector") as mock_ad:
                        mock_ad.get_model_status.return_value = MLModelStatus(
                            model_version="1.0",
                            devices_tracked=10,
                            samples_count=1000,
                            is_trained=True,
                            is_online_learning=True,
                            training_status="online_learning",
                        )

                        with patch("app.routers.notifications.version_checker") as mock_vc:
                            mock_vc.get_status.return_value = {
                                "current_version": "1.0.0",
                                "update_available": False,
                            }

                            response = test_client.get("/api/notifications/status")

        assert response.status_code == 200


class TestDiscordEndpoints:
    """Tests for Discord endpoints"""

    def test_get_discord_info(self, test_client):
        """Should return Discord info"""
        with patch("app.routers.notifications.discord_service") as mock_ds:
            mock_ds.get_bot_info.return_value = DiscordBotInfo(
                connected=True, username="TestBot", discriminator="1234"
            )

            response = test_client.get("/api/notifications/discord/info")

            assert response.status_code == 200

    def test_get_discord_guilds_not_configured(self, test_client):
        """Should return 503 when not configured"""
        with patch("app.routers.notifications.is_discord_configured", return_value=False):
            response = test_client.get("/api/notifications/discord/guilds")

            assert response.status_code == 503

    def test_get_discord_guilds(self, test_client):
        """Should return Discord guilds"""
        with patch("app.routers.notifications.is_discord_configured", return_value=True):
            with patch("app.routers.notifications.discord_service") as mock_ds:
                mock_ds.get_guilds = AsyncMock(
                    return_value=[DiscordGuild(id="123", name="Test Guild", icon=None)]
                )

                response = test_client.get("/api/notifications/discord/guilds")

                assert response.status_code == 200

    def test_get_discord_channels_not_configured(self, test_client):
        """Should return 503 when not configured"""
        with patch("app.routers.notifications.is_discord_configured", return_value=False):
            response = test_client.get("/api/notifications/discord/guilds/123/channels")

            assert response.status_code == 503

    def test_get_discord_channels(self, test_client):
        """Should return Discord channels"""
        with patch("app.routers.notifications.is_discord_configured", return_value=True):
            with patch("app.routers.notifications.discord_service") as mock_ds:
                mock_ds.get_channels = AsyncMock(
                    return_value=[DiscordChannel(id="456", name="general", type="text")]
                )

                response = test_client.get("/api/notifications/discord/guilds/123/channels")

                assert response.status_code == 200

    def test_get_discord_invite_url_not_configured(self, test_client):
        """Should return 503 when no client ID"""
        with patch("app.routers.notifications.get_bot_invite_url", return_value=None):
            response = test_client.get("/api/notifications/discord/invite-url")

            assert response.status_code == 503

    def test_get_discord_invite_url(self, test_client):
        """Should return bot invite URL"""
        with patch(
            "app.routers.notifications.get_bot_invite_url",
            return_value="https://discord.com/invite",
        ):
            response = test_client.get("/api/notifications/discord/invite-url")

            assert response.status_code == 200


class TestTestNotificationEndpoints:
    """Tests for test notification endpoints"""

    def test_send_test_notification(self, test_client):
        """Should send test notification"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            from app.models import TestNotificationResponse

            mock_nm.send_test_notification = AsyncMock(
                return_value=TestNotificationResponse(
                    success=True, channel=NotificationChannel.DISCORD, message="Test sent"
                )
            )

            response = test_client.post(
                "/api/notifications/networks/network_uuid_123/test",
                headers={"X-User-Id": "user_123"},
                json={"channel": "discord"},
            )

            assert response.status_code == 200


class TestHistoryEndpoints:
    """Tests for history endpoints"""

    def test_get_history(self, test_client):
        """Should return notification history"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            from app.models import NotificationHistoryResponse

            mock_nm.get_history.return_value = NotificationHistoryResponse(
                notifications=[], total_count=0, page=1, per_page=50
            )

            response = test_client.get(
                "/api/notifications/networks/network_uuid_123/history",
                headers={"X-User-Id": "user_123"},
            )

            assert response.status_code == 200

    def test_get_stats(self, test_client):
        """Should return notification stats"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            from app.models import NotificationStatsResponse

            mock_nm.get_stats.return_value = NotificationStatsResponse(
                total_sent_24h=100,
                total_sent_7d=500,
                by_channel={"discord": 80, "email": 20},
                by_type={},
                success_rate=0.95,
                anomalies_detected_24h=2,
            )

            response = test_client.get(
                "/api/notifications/networks/network_uuid_123/stats",
                headers={"X-User-Id": "user_123"},
            )

            assert response.status_code == 200


class TestMLAnomalyEndpoints:
    """Tests for ML anomaly detection endpoints"""

    def test_get_ml_status(self, test_client):
        """Should return ML model status"""
        with patch("app.routers.notifications.anomaly_detector") as mock_ad:
            mock_ad.get_model_status.return_value = MLModelStatus(
                model_version="1.0",
                devices_tracked=10,
                samples_count=1000,
                is_trained=True,
                is_online_learning=True,
                training_status="online_learning",
            )

            response = test_client.get("/api/notifications/ml/status")

            assert response.status_code == 200

    def test_get_device_baseline(self, test_client):
        """Should return device baseline"""
        with patch("app.routers.notifications.network_anomaly_detector_manager") as mock_nadm:
            mock_detector = MagicMock()
            mock_detector.get_device_baseline.return_value = DeviceBaseline(
                device_ip="192.168.1.1",
                mean_latency=10.5,
                std_latency=2.3,
                availability=0.99,
                sample_count=100,
            )
            mock_nadm.get_detector.return_value = mock_detector

            response = test_client.get(
                "/api/notifications/ml/baseline/192.168.1.1?network_id=network_uuid_123"
            )

            assert response.status_code == 200

    def test_get_device_baseline_not_found(self, test_client):
        """Should return 404 for unknown device"""
        with patch("app.routers.notifications.network_anomaly_detector_manager") as mock_nadm:
            mock_detector = MagicMock()
            mock_detector.get_device_baseline.return_value = None
            mock_nadm.get_detector.return_value = mock_detector

            response = test_client.get(
                "/api/notifications/ml/baseline/192.168.1.1?network_id=network_uuid_123"
            )

            assert response.status_code == 404

    def test_reset_device_baseline(self, test_client):
        """Should reset device baseline"""
        with patch("app.routers.notifications.network_anomaly_detector_manager") as mock_nadm:
            mock_detector = MagicMock()
            mock_nadm.get_detector.return_value = mock_detector

            response = test_client.delete(
                "/api/notifications/ml/baseline/192.168.1.1?network_id=network_uuid_123"
            )

            assert response.status_code == 200

    def test_reset_all_baselines(self, test_client):
        """Should reset all baselines"""
        with patch("app.routers.notifications.anomaly_detector") as mock_ad:
            mock_ad.reset_all.return_value = None

            response = test_client.delete("/api/notifications/ml/reset")

            assert response.status_code == 200

    def test_mark_false_positive(self, test_client):
        """Should mark event as false positive"""
        with patch("app.routers.notifications.anomaly_detector") as mock_ad:
            mock_ad.mark_false_positive.return_value = None

            response = test_client.post(
                "/api/notifications/ml/feedback/false-positive", params={"event_id": "event_123"}
            )

            assert response.status_code == 200

    def test_sync_current_devices(self, test_client):
        """Should sync current devices for ML tracking"""
        with patch("app.routers.notifications.network_anomaly_detector_manager") as mock_nadm:
            mock_detector = MagicMock()
            mock_detector.sync_current_devices.return_value = None
            mock_nadm.get_detector.return_value = mock_detector

            device_ips = ["192.168.1.1", "192.168.1.2", "192.168.1.3"]
            response = test_client.post(
                "/api/notifications/ml/sync-devices?network_id=network_uuid_123", json=device_ips
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["devices_synced"] == 3
            mock_detector.sync_current_devices.assert_called_once_with(device_ips)


class TestHealthCheckProcessing:
    """Tests for health check processing endpoints"""

    def test_process_health_check(self, test_client):
        """Should process health checks"""
        with patch("app.routers.notifications.network_anomaly_detector_manager") as mock_nadm:
            mock_nadm.process_health_check.return_value = None

            response = test_client.post(
                "/api/notifications/process-health-check",
                params={
                    "device_ip": "192.168.1.1",
                    "success": True,
                    "latency_ms": 10.5,
                    "network_id": "network_uuid_123",
                },
            )

            assert response.status_code == 200


class TestManualNotificationEndpoints:
    """Tests for manual notification endpoints"""

    def test_send_manual_notification_broadcast(self, test_client):
        """Should broadcast notification"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            mock_nm.broadcast_notification = AsyncMock(return_value={"user1": True})

            event_data = {
                "event_type": "device_offline",
                "priority": "medium",
                "title": "Test",
                "message": "Test message",
            }

            response = test_client.post("/api/notifications/send-notification", json=event_data)

            assert response.status_code == 200

    def test_send_manual_notification_to_network(self, test_client):
        """Should send notification to a network"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            record = NotificationRecord(
                notification_id=str(uuid4()),
                event_id=str(uuid4()),
                network_id="network_uuid_123",
                channel=NotificationChannel.DISCORD,
                timestamp=datetime.now(timezone.utc),
                success=True,
                title="Test",
                message="Test message",
                priority=NotificationPriority.MEDIUM,
            )
            mock_nm.send_notification_to_network = AsyncMock(return_value=[record])

            event_data = {
                "event_type": "device_offline",
                "priority": "medium",
                "title": "Test",
                "message": "Test message",
            }

            response = test_client.post(
                "/api/notifications/networks/network_uuid_123/send-notification", json=event_data
            )

            assert response.status_code == 200


class TestScheduledBroadcastEndpoints:
    """Tests for scheduled broadcast endpoints"""

    def test_get_scheduled_broadcasts(self, test_client):
        """Should list scheduled broadcasts"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            from app.models import ScheduledBroadcastResponse

            mock_nm.get_scheduled_broadcasts.return_value = ScheduledBroadcastResponse(
                broadcasts=[], total_count=0
            )

            response = test_client.get("/api/notifications/scheduled")

            assert response.status_code == 200

    def test_create_scheduled_broadcast(self, test_client):
        """Should create scheduled broadcast"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            broadcast_id = str(uuid4())
            future_time = datetime.now(timezone.utc) + timedelta(hours=1)

            broadcast = ScheduledBroadcast(
                id=broadcast_id,
                title="Test Broadcast",
                message="Test message",
                scheduled_at=future_time,
                status=ScheduledBroadcastStatus.PENDING,
                created_by="admin",
                network_id="network_uuid_123",
            )
            mock_nm.create_scheduled_broadcast.return_value = broadcast

            response = test_client.post(
                "/api/notifications/scheduled",
                headers={"X-Username": "admin"},
                json={
                    "title": "Test Broadcast",
                    "message": "Test message",
                    "scheduled_at": future_time.isoformat(),
                    "network_id": "network_uuid_123",
                },
            )

            assert response.status_code == 200

    def test_create_scheduled_broadcast_past_time(self, test_client):
        """Should reject past scheduled time"""
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)

        response = test_client.post(
            "/api/notifications/scheduled",
            headers={"X-Username": "admin"},
            json={
                "title": "Test Broadcast",
                "message": "Test message",
                "scheduled_at": past_time.isoformat(),
                "network_id": "network_uuid_123",
            },
        )

        assert response.status_code == 400

    def test_get_scheduled_broadcast(self, test_client):
        """Should get specific broadcast"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            broadcast_id = str(uuid4())
            broadcast = ScheduledBroadcast(
                id=broadcast_id,
                title="Test",
                message="Test",
                scheduled_at=datetime.now(timezone.utc) + timedelta(hours=1),
                status=ScheduledBroadcastStatus.PENDING,
                created_by="admin",
                network_id="network_uuid_123",
            )
            mock_nm.get_scheduled_broadcast.return_value = broadcast

            response = test_client.get(f"/api/notifications/scheduled/{broadcast_id}")

            assert response.status_code == 200

    def test_get_scheduled_broadcast_not_found(self, test_client):
        """Should return 404 for unknown broadcast"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            mock_nm.get_scheduled_broadcast.return_value = None

            response = test_client.get(f"/api/notifications/scheduled/{uuid4()}")

            assert response.status_code == 404

    def test_cancel_scheduled_broadcast(self, test_client):
        """Should cancel scheduled broadcast"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            mock_nm.cancel_scheduled_broadcast.return_value = True

            response = test_client.post(f"/api/notifications/scheduled/{uuid4()}/cancel")

            assert response.status_code == 200

    def test_cancel_scheduled_broadcast_not_found(self, test_client):
        """Should return 400 when canceling unknown/sent broadcast"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            mock_nm.cancel_scheduled_broadcast.return_value = False

            response = test_client.post(f"/api/notifications/scheduled/{uuid4()}/cancel")

            assert response.status_code == 400

    def test_delete_scheduled_broadcast(self, test_client):
        """Should delete scheduled broadcast"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            mock_nm.delete_scheduled_broadcast.return_value = True

            response = test_client.delete(f"/api/notifications/scheduled/{uuid4()}")

            assert response.status_code == 200

    def test_delete_scheduled_broadcast_not_found(self, test_client):
        """Should return 400 when deleting pending broadcast"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            mock_nm.delete_scheduled_broadcast.return_value = False

            response = test_client.delete(f"/api/notifications/scheduled/{uuid4()}")

            assert response.status_code == 400


class TestSilencedDevicesEndpoints:
    """Tests for silenced devices endpoints"""

    def test_get_silenced_devices(self, test_client):
        """Should return silenced devices"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            mock_nm.get_silenced_devices.return_value = ["192.168.1.1", "192.168.1.2"]

            response = test_client.get("/api/notifications/silenced-devices")

            assert response.status_code == 200
            assert len(response.json()["devices"]) == 2

    def test_silence_device(self, test_client):
        """Should silence a device"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            mock_nm.silence_device.return_value = True

            response = test_client.post("/api/notifications/silenced-devices/192.168.1.1")

            assert response.status_code == 200

    def test_unsilence_device(self, test_client):
        """Should unsilence a device"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            mock_nm.unsilence_device.return_value = True

            response = test_client.delete("/api/notifications/silenced-devices/192.168.1.1")

            assert response.status_code == 200

    def test_set_silenced_devices(self, test_client):
        """Should set silenced devices list"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            mock_nm.set_silenced_devices.return_value = None

            response = test_client.post("/api/notifications/silenced-devices", json=["192.168.1.1"])

            assert response.status_code == 200

    def test_check_device_silenced(self, test_client):
        """Should check if device is silenced"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            mock_nm.is_device_silenced.return_value = True

            response = test_client.get("/api/notifications/silenced-devices/192.168.1.1")

            assert response.status_code == 200
            assert response.json()["silenced"] is True


class TestServiceStatusNotifications:
    """Tests for Cartographer service status notification endpoints"""

    def test_notify_cartographer_up(self, test_client):
        """Should send cartographer up notification"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            mock_nm.broadcast_notification = AsyncMock(return_value={"user1": True})

            response = test_client.post("/api/notifications/service-status/up")

            assert response.status_code == 200

    def test_notify_cartographer_up_with_downtime(self, test_client):
        """Should include downtime in notification"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            mock_nm.broadcast_notification = AsyncMock(return_value={"user1": True})

            response = test_client.post(
                "/api/notifications/service-status/up", params={"downtime_minutes": 30}
            )

            assert response.status_code == 200

    def test_notify_cartographer_down(self, test_client):
        """Should send cartographer down notification"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            mock_nm.broadcast_notification = AsyncMock(return_value={"user1": True})

            response = test_client.post("/api/notifications/service-status/down")

            assert response.status_code == 200

    def test_notify_cartographer_down_with_services(self, test_client):
        """Should include affected services in notification"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            mock_nm.broadcast_notification = AsyncMock(return_value={"user1": True})

            response = test_client.post(
                "/api/notifications/service-status/down",
                params={"affected_services": ["health", "metrics"]},
            )

            assert response.status_code == 200


class TestSendNetworkNotificationEndpoint:
    """Tests for send network notification endpoint"""

    def test_send_network_notification_with_user_ids(self, test_client):
        """Should send notification to specific users"""
        with patch("app.routers.notifications.notification_manager") as mock_nm:
            mock_record = NotificationRecord(
                notification_id="n1",
                event_id="e1",
                channel=NotificationChannel.EMAIL,
                success=True,
                title="T",
                message="M",
                priority=NotificationPriority.HIGH,
            )
            mock_nm.send_notification_to_network_members = AsyncMock(
                return_value={"user1": [mock_record], "user2": [mock_record]}
            )

            response = test_client.post(
                "/api/notifications/networks/test-network/send-notification",
                json={
                    "event_type": "device_offline",
                    "title": "Test",
                    "message": "Test message",
                    "priority": "high",
                    "user_ids": ["user1", "user2"],
                },
            )

            assert response.status_code == 200
            assert response.json()["success"] is True


class TestVersionCheckEndpoints:
    """Tests for version check endpoints"""

    def test_get_version_status(self, test_client):
        """Should return version check status"""
        with patch("app.routers.notifications.version_checker") as mock_vc:
            mock_vc.get_status.return_value = {
                "current_version": "1.0.0",
                "latest_version": "1.1.0",
                "update_available": True,
                "last_check": datetime.now(timezone.utc).isoformat(),
            }

            response = test_client.get("/api/notifications/version")

            assert response.status_code == 200

    def test_check_for_updates(self, test_client):
        """Should trigger version check"""
        with patch("app.routers.notifications.version_checker") as mock_vc:
            mock_vc.check_now = AsyncMock(
                return_value={
                    "success": True,
                    "has_update": False,
                    "current_version": "1.0.0",
                    "latest_version": "1.0.0",
                }
            )

            response = test_client.post("/api/notifications/version/check")

            assert response.status_code == 200

    def test_send_version_notification_no_update(self, test_client):
        """Should handle no update available"""
        with patch("app.routers.notifications.version_checker") as mock_vc:
            mock_vc.check_now = AsyncMock(
                return_value={
                    "success": True,
                    "has_update": False,
                    "current_version": "1.0.0",
                    "latest_version": "1.0.0",
                }
            )

            response = test_client.post("/api/notifications/version/notify")

            assert response.status_code == 200
            # success indicates the check was successful, has_update indicates if there's an update
            assert response.json()["success"] is True
            assert response.json()["has_update"] is False

    def test_send_version_notification_check_failed(self, test_client):
        """Should handle check failure"""
        with patch("app.routers.notifications.version_checker") as mock_vc:
            mock_vc.check_now = AsyncMock(return_value={"success": False, "error": "Network error"})

            response = test_client.post("/api/notifications/version/notify")

            assert response.status_code == 200
            assert response.json()["success"] is False

    def test_send_version_notification_with_update(self, test_client):
        """Should send version notification when update available"""
        with patch("app.routers.notifications.version_checker") as mock_vc:
            mock_vc.check_now = AsyncMock(
                return_value={
                    "success": True,
                    "has_update": True,
                    "current_version": "1.0.0",
                    "latest_version": "1.1.0",
                    "update_type": "minor",
                }
            )

            with patch("app.routers.notifications.notification_manager") as mock_nm:
                mock_nm.broadcast_notification = AsyncMock(return_value={"user1": True})

                response = test_client.post("/api/notifications/version/notify")

                assert response.status_code == 200
                assert response.json()["success"] is True
