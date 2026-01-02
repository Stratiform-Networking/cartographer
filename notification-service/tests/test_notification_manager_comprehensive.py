"""
Comprehensive tests for NotificationManager service to achieve 80%+ coverage.
"""

import asyncio
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import (
    DiscordConfig,
    EmailConfig,
    GlobalUserPreferences,
    GlobalUserPreferencesUpdate,
    NetworkEvent,
    NotificationChannel,
    NotificationPreferences,
    NotificationPreferencesUpdate,
    NotificationPriority,
    NotificationRecord,
    NotificationType,
    ScheduledBroadcast,
    ScheduledBroadcastStatus,
    ScheduledBroadcastUpdate,
    TestNotificationRequest,
)


class TestPersistenceLoad:
    """Tests for loading persisted data"""

    def test_load_preferences_with_datetime_parsing(self, notification_manager_instance, tmp_path):
        """Should parse datetime strings when loading preferences"""
        prefs_file = tmp_path / "prefs.json"
        prefs_file.write_text(
            json.dumps(
                {
                    "test-network": {
                        "network_id": "test-network",
                        "created_at": "2024-01-15T10:00:00Z",
                        "updated_at": "2024-01-15T11:00:00Z",
                        "enabled": True,
                    }
                }
            )
        )

        with patch("app.services.notification_manager.PREFERENCES_FILE", prefs_file):
            notification_manager_instance._preferences.clear()
            notification_manager_instance._load_preferences()

        assert "test-network" in notification_manager_instance._preferences
        prefs = notification_manager_instance._preferences["test-network"]
        assert isinstance(prefs.created_at, datetime)

    def test_load_preferences_skips_old_user_format(self, notification_manager_instance, tmp_path):
        """Should skip old user_id based preferences"""
        prefs_file = tmp_path / "prefs.json"
        prefs_file.write_text(
            json.dumps({"old-user-id": {"user_id": "old-user-id", "enabled": True}})
        )

        with patch("app.services.notification_manager.PREFERENCES_FILE", prefs_file):
            notification_manager_instance._preferences.clear()
            notification_manager_instance._load_preferences()

        assert "old-user-id" not in notification_manager_instance._preferences

    def test_load_preferences_handles_validation_error(
        self, notification_manager_instance, tmp_path
    ):
        """Should handle validation errors gracefully"""
        prefs_file = tmp_path / "prefs.json"
        prefs_file.write_text(
            json.dumps(
                {
                    "test-network": {
                        "network_id": "test-network",
                        "enabled": "invalid_boolean",  # Should be bool
                    }
                }
            )
        )

        with patch("app.services.notification_manager.PREFERENCES_FILE", prefs_file):
            with patch("app.services.notification_manager.logger.warning") as mock_warn:
                notification_manager_instance._preferences.clear()
                notification_manager_instance._load_preferences()
                mock_warn.assert_called()

    def test_load_history_with_migration(self, notification_manager_instance, tmp_path):
        """Should migrate old user_id based records"""
        history_file = tmp_path / "history.json"
        history_file.write_text(
            json.dumps(
                [
                    {
                        "notification_id": "n1",
                        "event_id": "e1",
                        "user_id": "old-user",  # Old format
                        "channel": "email",
                        "success": True,
                        "title": "Test",
                        "message": "Test",
                        "priority": "high",
                    }
                ]
            )
        )

        with patch("app.services.notification_manager.HISTORY_FILE", history_file):
            notification_manager_instance._history.clear()
            notification_manager_instance._load_history()

        assert len(notification_manager_instance._history) == 1
        assert notification_manager_instance._history[0].network_id is None

    def test_load_history_converts_integer_network_id(
        self, notification_manager_instance, tmp_path
    ):
        """Should convert integer network_id to string or None"""
        history_file = tmp_path / "history.json"
        history_file.write_text(
            json.dumps(
                [
                    {
                        "notification_id": "n1",
                        "event_id": "e1",
                        "network_id": 0,  # Old integer format
                        "channel": "email",
                        "success": True,
                        "title": "Test",
                        "message": "Test",
                        "priority": "high",
                    }
                ]
            )
        )

        with patch("app.services.notification_manager.HISTORY_FILE", history_file):
            notification_manager_instance._history.clear()
            notification_manager_instance._load_history()

        assert len(notification_manager_instance._history) == 1
        assert notification_manager_instance._history[0].network_id is None

    def test_load_scheduled_broadcasts_with_datetime(self, notification_manager_instance, tmp_path):
        """Should parse datetime fields in scheduled broadcasts"""
        scheduled_file = tmp_path / "scheduled.json"
        scheduled_file.write_text(
            json.dumps(
                {
                    "broadcast-1": {
                        "id": "broadcast-1",
                        "title": "Test",
                        "message": "Test message",
                        "network_id": "test-network",
                        "scheduled_at": "2024-01-15T10:00:00Z",
                        "created_at": "2024-01-14T10:00:00Z",
                        "created_by": "admin",
                    }
                }
            )
        )

        with patch("app.services.notification_manager.SCHEDULED_FILE", scheduled_file):
            notification_manager_instance._scheduled_broadcasts.clear()
            notification_manager_instance._load_scheduled_broadcasts()

        assert "broadcast-1" in notification_manager_instance._scheduled_broadcasts
        broadcast = notification_manager_instance._scheduled_broadcasts["broadcast-1"]
        assert isinstance(broadcast.scheduled_at, datetime)

    def test_load_scheduled_broadcasts_skips_without_network_id(
        self, notification_manager_instance, tmp_path
    ):
        """Should skip old broadcasts without network_id"""
        scheduled_file = tmp_path / "scheduled.json"
        scheduled_file.write_text(
            json.dumps(
                {
                    "old-broadcast": {
                        "id": "old-broadcast",
                        "title": "Old",
                        "message": "Old message",
                        "scheduled_at": "2024-01-15T10:00:00Z",
                        "created_by": "admin",
                        # Missing network_id
                    }
                }
            )
        )

        with patch("app.services.notification_manager.SCHEDULED_FILE", scheduled_file):
            with patch("app.services.notification_manager.logger.warning") as mock_warn:
                with patch.object(notification_manager_instance, "_save_scheduled_broadcasts"):
                    notification_manager_instance._scheduled_broadcasts.clear()
                    notification_manager_instance._load_scheduled_broadcasts()
                    mock_warn.assert_called()

        assert "old-broadcast" not in notification_manager_instance._scheduled_broadcasts

    def test_load_global_preferences(self, notification_manager_instance, tmp_path):
        """Should load global preferences correctly"""
        global_prefs_file = tmp_path / "global_prefs.json"
        global_prefs_file.write_text(
            json.dumps(
                {
                    "user-1": {
                        "user_id": "user-1",
                        "email_address": "user1@test.com",
                        "cartographer_up_enabled": True,
                        "cartographer_down_enabled": False,
                        "created_at": "2024-01-15T10:00:00Z",
                    }
                }
            )
        )

        with patch("app.services.notification_manager.GLOBAL_PREFERENCES_FILE", global_prefs_file):
            notification_manager_instance._global_preferences.clear()
            notification_manager_instance._load_global_preferences()

        assert "user-1" in notification_manager_instance._global_preferences
        prefs = notification_manager_instance._global_preferences["user-1"]
        assert prefs.cartographer_up_enabled is True
        assert prefs.cartographer_down_enabled is False


class TestPersistenceSave:
    """Tests for saving persisted data"""

    def test_save_preferences_error_handling(self, notification_manager_instance, tmp_path):
        """Should handle save errors gracefully"""
        # Create a read-only directory
        read_only_dir = tmp_path / "readonly"
        read_only_dir.mkdir()

        notification_manager_instance._preferences["test"] = NotificationPreferences(
            network_id="test"
        )

        with patch(
            "app.services.notification_manager.settings.notification_data_dir", str(read_only_dir)
        ):
            with patch(
                "app.services.notification_manager.PREFERENCES_FILE",
                read_only_dir / "readonly_dir" / "prefs.json",
            ):
                with patch("app.services.notification_manager.logger.error") as mock_error:
                    # Force an error by making directory creation fail
                    with patch("pathlib.Path.mkdir", side_effect=PermissionError("Access denied")):
                        notification_manager_instance._save_preferences()
                        mock_error.assert_called()

    def test_save_history_error_handling(self, notification_manager_instance, tmp_path):
        """Should handle history save errors gracefully"""
        notification_manager_instance._history.append(
            NotificationRecord(
                notification_id="1",
                event_id="1",
                network_id="test",
                channel=NotificationChannel.EMAIL,
                success=True,
                title="Test",
                message="Test",
                priority=NotificationPriority.HIGH,
            )
        )

        with patch(
            "app.services.notification_manager.settings.notification_data_dir", str(tmp_path)
        ):
            with patch("builtins.open", side_effect=IOError("Write failed")):
                with patch("app.services.notification_manager.logger.error") as mock_error:
                    notification_manager_instance._save_history()
                    mock_error.assert_called()

    def test_save_scheduled_broadcasts_error_handling(
        self, notification_manager_instance, tmp_path
    ):
        """Should handle scheduled broadcast save errors"""
        notification_manager_instance._scheduled_broadcasts["test-id"] = ScheduledBroadcast(
            id="test-id",
            title="Test",
            message="Test",
            network_id="test-network",
            scheduled_at=datetime.utcnow(),
            created_by="admin",
        )

        with patch(
            "app.services.notification_manager.settings.notification_data_dir", str(tmp_path)
        ):
            with patch("builtins.open", side_effect=IOError("Write failed")):
                with patch("app.services.notification_manager.logger.error") as mock_error:
                    notification_manager_instance._save_scheduled_broadcasts()
                    mock_error.assert_called()

    def test_save_silenced_devices_error_handling(self, notification_manager_instance, tmp_path):
        """Should handle silenced devices save errors"""
        notification_manager_instance._silenced_devices.add("192.168.1.1")

        with patch(
            "app.services.notification_manager.settings.notification_data_dir", str(tmp_path)
        ):
            with patch("builtins.open", side_effect=IOError("Write failed")):
                with patch("app.services.notification_manager.logger.error") as mock_error:
                    notification_manager_instance._save_silenced_devices()
                    mock_error.assert_called()

    def test_save_global_preferences_error_handling(self, notification_manager_instance, tmp_path):
        """Should handle global preferences save errors"""
        notification_manager_instance._global_preferences["user1"] = GlobalUserPreferences(
            user_id="user1"
        )

        with patch(
            "app.services.notification_manager.settings.notification_data_dir", str(tmp_path)
        ):
            with patch("builtins.open", side_effect=IOError("Write failed")):
                with patch("app.services.notification_manager.logger.error") as mock_error:
                    notification_manager_instance._save_global_preferences()
                    mock_error.assert_called()


class TestGlobalPreferencesMigration:
    """Tests for global preferences migration"""

    def test_migrate_users_to_global_preferences(self, notification_manager_instance):
        """Should migrate network owners to global preferences"""
        # Clear any existing state
        notification_manager_instance._preferences.clear()
        notification_manager_instance._global_preferences.clear()

        # Setup network with owner and email
        notification_manager_instance._preferences["network-1"] = NotificationPreferences(
            network_id="network-1",
            owner_user_id="owner-user-1",
            email=EmailConfig(enabled=True, email_address="owner@test.com"),
        )

        with patch.object(notification_manager_instance, "_save_global_preferences"):
            notification_manager_instance._migrate_users_to_global_preferences()

        assert "owner-user-1" in notification_manager_instance._global_preferences
        migrated = notification_manager_instance._global_preferences["owner-user-1"]
        assert migrated.email_address == "owner@test.com"
        assert migrated.cartographer_up_enabled is True
        assert migrated.cartographer_down_enabled is True

    def test_migrate_skips_without_owner(self, notification_manager_instance):
        """Should skip networks without owner_user_id"""
        # Clear any existing state
        notification_manager_instance._preferences.clear()
        notification_manager_instance._global_preferences.clear()

        notification_manager_instance._preferences["network-1"] = NotificationPreferences(
            network_id="network-1",
            owner_user_id=None,
            email=EmailConfig(enabled=True, email_address="test@test.com"),
        )

        with patch.object(notification_manager_instance, "_save_global_preferences"):
            notification_manager_instance._migrate_users_to_global_preferences()

        assert len(notification_manager_instance._global_preferences) == 0

    def test_migrate_skips_without_email(self, notification_manager_instance):
        """Should skip networks without email address"""
        # Clear any existing state
        notification_manager_instance._preferences.clear()
        notification_manager_instance._global_preferences.clear()

        notification_manager_instance._preferences["network-1"] = NotificationPreferences(
            network_id="network-1",
            owner_user_id="owner-1",
            email=EmailConfig(enabled=False),  # No email configured
        )

        with patch.object(notification_manager_instance, "_save_global_preferences"):
            notification_manager_instance._migrate_users_to_global_preferences()

        assert "owner-1" not in notification_manager_instance._global_preferences

    def test_migrate_skips_existing_users(self, notification_manager_instance):
        """Should skip users who already have global preferences"""
        # Clear any existing state
        notification_manager_instance._preferences.clear()
        notification_manager_instance._global_preferences.clear()

        notification_manager_instance._preferences["network-1"] = NotificationPreferences(
            network_id="network-1",
            owner_user_id="existing-user",
            email=EmailConfig(enabled=True, email_address="owner@test.com"),
        )
        notification_manager_instance._global_preferences["existing-user"] = GlobalUserPreferences(
            user_id="existing-user", email_address="existing@test.com"
        )

        original_email = notification_manager_instance._global_preferences[
            "existing-user"
        ].email_address

        with patch.object(notification_manager_instance, "_save_global_preferences"):
            notification_manager_instance._migrate_users_to_global_preferences()

        # Should not be overwritten
        assert (
            notification_manager_instance._global_preferences["existing-user"].email_address
            == original_email
        )


class TestScheduledBroadcastManagement:
    """Tests for scheduled broadcast management"""

    def test_mark_broadcast_seen(self, notification_manager_instance):
        """Should mark broadcast as seen"""
        broadcast = ScheduledBroadcast(
            id="test-id",
            title="Test",
            message="Test",
            network_id="test-network",
            scheduled_at=datetime.utcnow() - timedelta(hours=1),
            created_by="admin",
            status=ScheduledBroadcastStatus.SENT,
        )
        notification_manager_instance._scheduled_broadcasts["test-id"] = broadcast

        with patch.object(notification_manager_instance, "_save_scheduled_broadcasts"):
            result = notification_manager_instance.mark_broadcast_seen("test-id")

        assert result is not None
        assert result.seen_at is not None

    def test_mark_broadcast_seen_not_found(self, notification_manager_instance):
        """Should return None for non-existent broadcast"""
        result = notification_manager_instance.mark_broadcast_seen("nonexistent")
        assert result is None

    def test_mark_broadcast_seen_pending(self, notification_manager_instance):
        """Should not mark pending broadcast as seen"""
        broadcast = ScheduledBroadcast(
            id="test-id",
            title="Test",
            message="Test",
            network_id="test-network",
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
            created_by="admin",
            status=ScheduledBroadcastStatus.PENDING,
        )
        notification_manager_instance._scheduled_broadcasts["test-id"] = broadcast

        result = notification_manager_instance.mark_broadcast_seen("test-id")

        assert result is not None
        assert result.seen_at is None

    def test_update_scheduled_broadcast(self, notification_manager_instance):
        """Should update scheduled broadcast"""
        broadcast = ScheduledBroadcast(
            id="test-id",
            title="Original Title",
            message="Original Message",
            network_id="test-network",
            scheduled_at=datetime.utcnow() + timedelta(hours=1),
            created_by="admin",
        )
        notification_manager_instance._scheduled_broadcasts["test-id"] = broadcast

        update = ScheduledBroadcastUpdate(title="New Title", message="New Message")

        with patch.object(notification_manager_instance, "_save_scheduled_broadcasts"):
            result = notification_manager_instance.update_scheduled_broadcast("test-id", update)

        assert result is not None
        assert result.title == "New Title"
        assert result.message == "New Message"

    def test_update_scheduled_broadcast_not_found(self, notification_manager_instance):
        """Should return None for non-existent broadcast"""
        update = ScheduledBroadcastUpdate(title="New Title")
        result = notification_manager_instance.update_scheduled_broadcast("nonexistent", update)
        assert result is None

    def test_update_scheduled_broadcast_not_pending(self, notification_manager_instance):
        """Should not update non-pending broadcast"""
        broadcast = ScheduledBroadcast(
            id="test-id",
            title="Original",
            message="Original",
            network_id="test-network",
            scheduled_at=datetime.utcnow(),
            created_by="admin",
            status=ScheduledBroadcastStatus.SENT,
        )
        notification_manager_instance._scheduled_broadcasts["test-id"] = broadcast

        update = ScheduledBroadcastUpdate(title="New Title")
        result = notification_manager_instance.update_scheduled_broadcast("test-id", update)

        assert result is None

    def test_get_scheduled_broadcasts_filters_dismissed(self, notification_manager_instance):
        """Should filter out seen broadcasts after timeout"""
        now = datetime.utcnow()

        # Create sent broadcast that was seen recently
        recent = ScheduledBroadcast(
            id="recent",
            title="Recent",
            message="Test",
            network_id="test-network",
            scheduled_at=now - timedelta(hours=1),
            created_by="admin",
            status=ScheduledBroadcastStatus.SENT,
            seen_at=now - timedelta(seconds=2),  # Seen 2 seconds ago
        )

        # Create sent broadcast that was seen long ago (dismissed)
        dismissed = ScheduledBroadcast(
            id="dismissed",
            title="Dismissed",
            message="Test",
            network_id="test-network",
            scheduled_at=now - timedelta(hours=2),
            created_by="admin",
            status=ScheduledBroadcastStatus.SENT,
            seen_at=now - timedelta(seconds=10),  # Seen 10 seconds ago (dismissed)
        )

        notification_manager_instance._scheduled_broadcasts["recent"] = recent
        notification_manager_instance._scheduled_broadcasts["dismissed"] = dismissed

        result = notification_manager_instance.get_scheduled_broadcasts(include_completed=True)

        # Only recent should be included
        broadcast_ids = [b.id for b in result.broadcasts]
        assert "recent" in broadcast_ids
        assert "dismissed" not in broadcast_ids


class TestSchedulerTask:
    """Tests for the scheduler task"""

    @pytest.mark.asyncio
    async def test_send_scheduled_broadcast_no_users(self, notification_manager_instance):
        """Should handle case with no users"""
        broadcast = ScheduledBroadcast(
            id="test-broadcast",
            title="Test",
            message="Test message",
            network_id="test-network",
            scheduled_at=datetime.utcnow(),
            created_by="admin",
        )
        notification_manager_instance._scheduled_broadcasts["test-broadcast"] = broadcast

        with patch.object(
            notification_manager_instance,
            "_get_network_member_user_ids",
            new_callable=AsyncMock,
            return_value=[],
        ):
            with patch.object(notification_manager_instance, "_save_scheduled_broadcasts"):
                await notification_manager_instance._send_scheduled_broadcast("test-broadcast")

        assert (
            notification_manager_instance._scheduled_broadcasts["test-broadcast"].status
            == ScheduledBroadcastStatus.FAILED
        )


class TestNotificationSending:
    """Tests for notification sending methods"""

    @pytest.mark.asyncio
    async def test_send_notification_to_network_email_not_configured(
        self, notification_manager_instance
    ):
        """Should record error when email service not configured"""
        notification_manager_instance._preferences["test-network"] = NotificationPreferences(
            network_id="test-network",
            enabled=True,
            email=EmailConfig(enabled=True, email_address="test@test.com"),
        )

        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            title="Test",
            message="Test",
            priority=NotificationPriority.HIGH,
        )

        with patch("app.services.notification_manager.is_email_configured", return_value=False):
            with patch.object(notification_manager_instance, "_save_history"):
                records = await notification_manager_instance.send_notification_to_network(
                    "test-network", event, force=True
                )

        assert len(records) == 1
        assert records[0].success is False
        assert "not configured" in records[0].error_message.lower()

    @pytest.mark.asyncio
    async def test_send_notification_to_network_with_discord(self, notification_manager_instance):
        """Should send Discord notification"""
        notification_manager_instance._preferences["test-network"] = NotificationPreferences(
            network_id="test-network",
            enabled=True,
            discord=DiscordConfig(enabled=True, discord_user_id="123456789"),
        )

        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            title="Test",
            message="Test",
            priority=NotificationPriority.HIGH,
        )

        mock_record = NotificationRecord(
            notification_id="test",
            event_id="test",
            network_id="test-network",
            channel=NotificationChannel.DISCORD,
            success=True,
            title="Test",
            message="Test",
            priority=NotificationPriority.HIGH,
        )

        with patch(
            "app.services.notification_manager.send_discord_notification",
            new_callable=AsyncMock,
            return_value=mock_record,
        ):
            with patch.object(notification_manager_instance, "_save_history"):
                records = await notification_manager_instance.send_notification_to_network(
                    "test-network", event, force=True
                )

        assert len(records) == 1
        assert records[0].success is True
        assert records[0].channel == NotificationChannel.DISCORD

    @pytest.mark.asyncio
    async def test_send_notification_to_network_members(self, notification_manager_instance):
        """Should send to all network members"""
        notification_manager_instance._preferences["test-network"] = NotificationPreferences(
            network_id="test-network",
            enabled=True,
            email=EmailConfig(enabled=True, email_address="test@test.com"),
        )

        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            title="Test",
            message="Test",
            priority=NotificationPriority.HIGH,
        )

        mock_record = NotificationRecord(
            notification_id="test",
            event_id="test",
            network_id="test-network",
            channel=NotificationChannel.EMAIL,
            success=True,
            title="Test",
            message="Test",
            priority=NotificationPriority.HIGH,
        )

        with patch("app.services.notification_manager.is_email_configured", return_value=True):
            with patch(
                "app.services.notification_manager.send_notification_email",
                new_callable=AsyncMock,
                return_value=mock_record,
            ):
                with patch.object(notification_manager_instance, "_save_history"):
                    results = (
                        await notification_manager_instance.send_notification_to_network_members(
                            "test-network", ["user1", "user2"], event, force=True
                        )
                    )

        assert "user1" in results
        assert "user2" in results
        assert all(r[0].success for r in results.values())

    @pytest.mark.asyncio
    async def test_send_notification_to_network_members_email_exception(
        self, notification_manager_instance
    ):
        """Should handle email send exception"""
        notification_manager_instance._preferences["test-network"] = NotificationPreferences(
            network_id="test-network",
            enabled=True,
            email=EmailConfig(enabled=True, email_address="test@test.com"),
        )

        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            title="Test",
            message="Test",
            priority=NotificationPriority.HIGH,
        )

        with patch("app.services.notification_manager.is_email_configured", return_value=True):
            with patch(
                "app.services.notification_manager.send_notification_email",
                new_callable=AsyncMock,
                side_effect=Exception("Send failed"),
            ):
                with patch.object(notification_manager_instance, "_save_history"):
                    results = (
                        await notification_manager_instance.send_notification_to_network_members(
                            "test-network", ["user1"], event, force=True
                        )
                    )

        assert "user1" in results
        assert results["user1"][0].success is False

    @pytest.mark.asyncio
    async def test_send_notification_to_network_members_discord_exception(
        self, notification_manager_instance
    ):
        """Should handle Discord send exception"""
        notification_manager_instance._preferences["test-network"] = NotificationPreferences(
            network_id="test-network",
            enabled=True,
            discord=DiscordConfig(enabled=True, discord_user_id="123456789"),
        )

        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            title="Test",
            message="Test",
            priority=NotificationPriority.HIGH,
        )

        with patch(
            "app.services.notification_manager.send_discord_notification",
            new_callable=AsyncMock,
            side_effect=Exception("Discord failed"),
        ):
            with patch.object(notification_manager_instance, "_save_history"):
                results = await notification_manager_instance.send_notification_to_network_members(
                    "test-network", ["user1"], event, force=True
                )

        assert "user1" in results
        assert results["user1"][0].success is False
        assert results["user1"][0].channel == NotificationChannel.DISCORD


class TestBroadcastNotification:
    """Tests for broadcast_notification method"""

    @pytest.mark.asyncio
    async def test_broadcast_to_all_networks(self, notification_manager_instance):
        """Should broadcast to all networks with notifications enabled"""
        notification_manager_instance._preferences["network-1"] = NotificationPreferences(
            network_id="network-1",
            enabled=True,
            email=EmailConfig(enabled=True, email_address="net1@test.com"),
        )
        notification_manager_instance._preferences["network-2"] = NotificationPreferences(
            network_id="network-2",
            enabled=True,
            email=EmailConfig(enabled=True, email_address="net2@test.com"),
        )

        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            title="Broadcast Test",
            message="Test message",
        )

        mock_record = NotificationRecord(
            notification_id="test",
            event_id="test",
            network_id="",
            channel=NotificationChannel.EMAIL,
            success=True,
            title="Test",
            message="Test",
            priority=NotificationPriority.HIGH,
        )

        with patch("app.services.notification_manager.is_email_configured", return_value=True):
            with patch(
                "app.services.notification_manager.send_notification_email",
                new_callable=AsyncMock,
                return_value=mock_record,
            ):
                with patch.object(notification_manager_instance, "_save_history"):
                    results = await notification_manager_instance.broadcast_notification(event)

        assert len(results) == 2


class TestTestNotifications:
    """Tests for test notification functionality"""

    @pytest.mark.asyncio
    async def test_send_test_email_success(self, notification_manager_instance):
        """Should send test email successfully"""
        notification_manager_instance._preferences["test-network"] = NotificationPreferences(
            network_id="test-network",
            email=EmailConfig(enabled=True, email_address="test@test.com"),
        )

        request = TestNotificationRequest(channel=NotificationChannel.EMAIL)

        with patch("app.services.notification_manager.is_email_configured", return_value=True):
            with patch(
                "app.services.notification_manager.send_test_email",
                new_callable=AsyncMock,
                return_value={"success": True},
            ):
                result = await notification_manager_instance.send_test_notification(
                    "test-network", request
                )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_send_test_email_service_not_configured(self, notification_manager_instance):
        """Should fail when email service not configured"""
        notification_manager_instance._preferences["test-network"] = NotificationPreferences(
            network_id="test-network",
            email=EmailConfig(enabled=True, email_address="test@test.com"),
        )

        request = TestNotificationRequest(channel=NotificationChannel.EMAIL)

        with patch("app.services.notification_manager.is_email_configured", return_value=False):
            result = await notification_manager_instance.send_test_notification(
                "test-network", request
            )

        assert result.success is False

    @pytest.mark.asyncio
    async def test_send_test_discord_success(self, notification_manager_instance):
        """Should send test Discord successfully"""
        notification_manager_instance._preferences["test-network"] = NotificationPreferences(
            network_id="test-network",
            discord=DiscordConfig(enabled=True, discord_user_id="123456789"),
        )

        request = TestNotificationRequest(channel=NotificationChannel.DISCORD)

        with patch("app.services.notification_manager.is_discord_configured", return_value=True):
            with patch(
                "app.services.notification_manager.send_test_discord",
                new_callable=AsyncMock,
                return_value={"success": True},
            ):
                result = await notification_manager_instance.send_test_notification(
                    "test-network", request
                )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_send_test_discord_service_not_configured(self, notification_manager_instance):
        """Should fail when Discord service not configured"""
        notification_manager_instance._preferences["test-network"] = NotificationPreferences(
            network_id="test-network",
            discord=DiscordConfig(enabled=True, discord_user_id="123456789"),
        )

        request = TestNotificationRequest(channel=NotificationChannel.DISCORD)

        with patch("app.services.notification_manager.is_discord_configured", return_value=False):
            result = await notification_manager_instance.send_test_notification(
                "test-network", request
            )

        assert result.success is False


class TestShouldNotifyAdvanced:
    """Advanced tests for _should_notify method"""

    def test_should_notify_quiet_hours_bypass(self, notification_manager_instance):
        """Should bypass quiet hours for high priority"""
        # Mock current time to be in quiet hours
        mock_time = datetime(2024, 1, 15, 3, 0, 0)

        prefs = NotificationPreferences(
            network_id="test-network",
            enabled=True,
            email=EmailConfig(enabled=True, email_address="test@test.com"),
            quiet_hours_enabled=True,
            quiet_hours_start="22:00",
            quiet_hours_end="07:00",
            quiet_hours_bypass_priority=NotificationPriority.HIGH,
            notification_type_priorities={
                NotificationType.DEVICE_OFFLINE: NotificationPriority.CRITICAL
            },
        )

        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE, title="Test", message="Test"
        )

        with patch("app.services.notification_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_time
            mock_datetime.utcnow.return_value = mock_time

            should, reason = notification_manager_instance._should_notify(prefs, event)

        # CRITICAL priority should bypass quiet hours
        assert should is True

    def test_should_notify_quiet_hours_blocked(self, notification_manager_instance):
        """Should block low priority during quiet hours"""
        mock_time = datetime(2024, 1, 15, 3, 0, 0)

        prefs = NotificationPreferences(
            network_id="test-network",
            enabled=True,
            email=EmailConfig(enabled=True, email_address="test@test.com"),
            quiet_hours_enabled=True,
            quiet_hours_start="22:00",
            quiet_hours_end="07:00",
            quiet_hours_bypass_priority=NotificationPriority.CRITICAL,
            notification_type_priorities={
                NotificationType.DEVICE_OFFLINE: NotificationPriority.HIGH
            },
        )

        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE, title="Test", message="Test"
        )

        with patch("app.services.notification_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_time
            mock_datetime.utcnow.return_value = mock_time

            should, reason = notification_manager_instance._should_notify(prefs, event)

        # HIGH priority should NOT bypass CRITICAL-only bypass
        assert should is False
        assert "quiet hours" in reason.lower()


class TestHistoryAndStatsAdvanced:
    """Advanced tests for history and statistics"""

    def test_get_history_all_networks(self, notification_manager_instance):
        """Should return history for all networks when no filter"""
        notification_manager_instance._history.clear()

        notification_manager_instance._history.append(
            NotificationRecord(
                notification_id="1",
                event_id="1",
                network_id="network-1",
                channel=NotificationChannel.EMAIL,
                success=True,
                title="Test 1",
                message="Test",
                priority=NotificationPriority.HIGH,
            )
        )
        notification_manager_instance._history.append(
            NotificationRecord(
                notification_id="2",
                event_id="2",
                network_id="network-2",
                channel=NotificationChannel.DISCORD,
                success=True,
                title="Test 2",
                message="Test",
                priority=NotificationPriority.HIGH,
            )
        )

        result = notification_manager_instance.get_history()

        assert result.total_count >= 2

    def test_get_stats_with_failures(self, notification_manager_instance):
        """Should correctly count stats"""
        now = datetime.utcnow()
        notification_manager_instance._history.clear()

        notification_manager_instance._history.append(
            NotificationRecord(
                notification_id="1",
                event_id="1",
                network_id="test",
                channel=NotificationChannel.EMAIL,
                success=True,
                title="Test",
                message="Test",
                priority=NotificationPriority.HIGH,
                timestamp=now,
            )
        )
        notification_manager_instance._history.append(
            NotificationRecord(
                notification_id="2",
                event_id="2",
                network_id="test",
                channel=NotificationChannel.EMAIL,
                success=False,
                title="Test",
                message="Test",
                priority=NotificationPriority.HIGH,
                timestamp=now,
                error_message="Failed",
            )
        )

        stats = notification_manager_instance.get_stats(network_id="test")

        # Check that stats has the expected attributes
        assert stats.total_sent_24h >= 0
        assert stats.total_sent_7d >= 0
