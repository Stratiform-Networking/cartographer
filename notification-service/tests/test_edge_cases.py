"""
Edge case tests to boost coverage to 95%+.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import json


class TestNotificationManagerEdgeCases:
    """Edge case tests for NotificationManager"""
    
    def test_load_preferences_empty_file(self):
        """Should handle empty preferences file"""
        from app.services.notification_manager import NotificationManager
        
        with patch('app.services.notification_manager.PREFERENCES_FILE') as mock_file:
            mock_file.exists.return_value = True
            with patch('builtins.open', mock_open(read_data="{}")):
                manager = NotificationManager()
        
        # Empty preferences is valid
        assert isinstance(manager._preferences, dict)
    
    def test_load_preferences_no_file(self):
        """Should handle missing preferences file"""
        from app.services.notification_manager import NotificationManager
        
        with patch('app.services.notification_manager.PREFERENCES_FILE') as mock_file:
            mock_file.exists.return_value = False
            with patch('app.services.notification_manager.HISTORY_FILE') as mock_history:
                mock_history.exists.return_value = False
                with patch('app.services.notification_manager.SCHEDULED_FILE') as mock_sched:
                    mock_sched.exists.return_value = False
                    with patch('app.services.notification_manager.SILENCED_DEVICES_FILE') as mock_silenced:
                        mock_silenced.exists.return_value = False
                        manager = NotificationManager()
        
        assert manager._preferences == {}
    
    def test_load_history_no_file(self):
        """Should handle missing history file"""
        from app.services.notification_manager import NotificationManager
        
        with patch('app.services.notification_manager.PREFERENCES_FILE') as mock_prefs:
            mock_prefs.exists.return_value = False
            with patch('app.services.notification_manager.HISTORY_FILE') as mock_file:
                mock_file.exists.return_value = False
                with patch('app.services.notification_manager.SCHEDULED_FILE') as mock_sched:
                    mock_sched.exists.return_value = False
                    with patch('app.services.notification_manager.SILENCED_DEVICES_FILE') as mock_silenced:
                        mock_silenced.exists.return_value = False
                        manager = NotificationManager()
        
        # History is a deque, check it's empty
        assert len(manager._history) == 0
    
    def test_silenced_devices_operations(self):
        """Test silenced devices operations"""
        from app.services.notification_manager import NotificationManager
        
        with patch('app.services.notification_manager.PREFERENCES_FILE') as mock_prefs:
            mock_prefs.exists.return_value = False
            with patch('app.services.notification_manager.HISTORY_FILE') as mock_history:
                mock_history.exists.return_value = False
                with patch('app.services.notification_manager.SCHEDULED_FILE') as mock_sched:
                    mock_sched.exists.return_value = False
                    with patch('app.services.notification_manager.SILENCED_DEVICES_FILE') as mock_silenced:
                        mock_silenced.exists.return_value = False
                        manager = NotificationManager()
        
        # Test silence/unsilence
        with patch.object(manager, '_save_silenced_devices'):
            manager.silence_device("192.168.1.1")
            assert manager.is_device_silenced("192.168.1.1")
            
            manager.unsilence_device("192.168.1.1")
            assert not manager.is_device_silenced("192.168.1.1")
    
    def test_set_silenced_devices(self):
        """Test setting silenced devices list"""
        from app.services.notification_manager import NotificationManager
        
        with patch('app.services.notification_manager.PREFERENCES_FILE') as mock_prefs:
            mock_prefs.exists.return_value = False
            with patch('app.services.notification_manager.HISTORY_FILE') as mock_history:
                mock_history.exists.return_value = False
                with patch('app.services.notification_manager.SCHEDULED_FILE') as mock_sched:
                    mock_sched.exists.return_value = False
                    with patch('app.services.notification_manager.SILENCED_DEVICES_FILE') as mock_silenced:
                        mock_silenced.exists.return_value = False
                        manager = NotificationManager()
        
        with patch.object(manager, '_save_silenced_devices'):
            manager.set_silenced_devices(["192.168.1.1", "192.168.1.2"])
        
        # Use set comparison since order isn't guaranteed
        assert set(manager.get_silenced_devices()) == {"192.168.1.1", "192.168.1.2"}
    
    def test_get_preferences(self):
        """Should get user preferences"""
        from app.services.notification_manager import NotificationManager
        from app.models import NotificationPreferences
        
        with patch('app.services.notification_manager.PREFERENCES_FILE') as mock_file:
            mock_file.exists.return_value = False
            with patch('app.services.notification_manager.HISTORY_FILE') as mock_history:
                mock_history.exists.return_value = False
                with patch('app.services.notification_manager.SCHEDULED_FILE') as mock_sched:
                    mock_sched.exists.return_value = False
                    with patch('app.services.notification_manager.SILENCED_DEVICES_FILE') as mock_silenced:
                        mock_silenced.exists.return_value = False
                        manager = NotificationManager()
        
        prefs = manager.get_preferences("user_123")
        
        assert prefs.user_id == "user_123"
    
    def test_update_preferences(self):
        """Should update user preferences"""
        from app.services.notification_manager import NotificationManager
        from app.models import NotificationPreferencesUpdate
        
        with patch('app.services.notification_manager.PREFERENCES_FILE') as mock_file:
            mock_file.exists.return_value = False
            with patch('app.services.notification_manager.HISTORY_FILE') as mock_history:
                mock_history.exists.return_value = False
                with patch('app.services.notification_manager.SCHEDULED_FILE') as mock_sched:
                    mock_sched.exists.return_value = False
                    with patch('app.services.notification_manager.SILENCED_DEVICES_FILE') as mock_silenced:
                        mock_silenced.exists.return_value = False
                        manager = NotificationManager()
        
        update = NotificationPreferencesUpdate(quiet_hours_start="22:00")
        
        with patch.object(manager, '_save_preferences'):
            result = manager.update_preferences("user_123", update)
        
        assert result.quiet_hours_start == "22:00"
    
    def test_delete_preferences(self):
        """Should delete user preferences"""
        from app.services.notification_manager import NotificationManager
        from app.models import NotificationPreferences
        
        with patch('app.services.notification_manager.PREFERENCES_FILE') as mock_file:
            mock_file.exists.return_value = False
            with patch('app.services.notification_manager.HISTORY_FILE') as mock_history:
                mock_history.exists.return_value = False
                with patch('app.services.notification_manager.SCHEDULED_FILE') as mock_sched:
                    mock_sched.exists.return_value = False
                    with patch('app.services.notification_manager.SILENCED_DEVICES_FILE') as mock_silenced:
                        mock_silenced.exists.return_value = False
                        manager = NotificationManager()
        
        manager._preferences["user_123"] = NotificationPreferences(user_id="user_123")
        
        with patch.object(manager, '_save_preferences'):
            result = manager.delete_preferences("user_123")
        
        assert result is True
        assert "user_123" not in manager._preferences
    
    def test_scheduled_broadcast_operations(self):
        """Test scheduled broadcast operations"""
        from app.services.notification_manager import NotificationManager
        from app.models import NotificationType, NotificationPriority
        
        with patch('app.services.notification_manager.PREFERENCES_FILE') as mock_file:
            mock_file.exists.return_value = False
            with patch('app.services.notification_manager.HISTORY_FILE') as mock_history:
                mock_history.exists.return_value = False
                with patch('app.services.notification_manager.SCHEDULED_FILE') as mock_sched:
                    mock_sched.exists.return_value = False
                    with patch('app.services.notification_manager.SILENCED_DEVICES_FILE') as mock_silenced:
                        mock_silenced.exists.return_value = False
                        manager = NotificationManager()
        
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        
        with patch.object(manager, '_save_scheduled_broadcasts'):
            broadcast = manager.create_scheduled_broadcast(
                title="Test",
                message="Test message",
                scheduled_at=future_time,
                created_by="admin"
            )
        
        assert broadcast.title == "Test"
        
        # Get all broadcasts
        result = manager.get_scheduled_broadcasts()
        assert result.total_count == 1
        
        # Get specific broadcast
        fetched = manager.get_scheduled_broadcast(broadcast.id)
        assert fetched.id == broadcast.id
    
    def test_cancel_scheduled_broadcast(self):
        """Should cancel scheduled broadcast"""
        from app.services.notification_manager import NotificationManager
        from app.models import ScheduledBroadcast, ScheduledBroadcastStatus
        
        with patch('app.services.notification_manager.PREFERENCES_FILE') as mock_file:
            mock_file.exists.return_value = False
            with patch('app.services.notification_manager.HISTORY_FILE') as mock_history:
                mock_history.exists.return_value = False
                with patch('app.services.notification_manager.SCHEDULED_FILE') as mock_sched:
                    mock_sched.exists.return_value = False
                    with patch('app.services.notification_manager.SILENCED_DEVICES_FILE') as mock_silenced:
                        mock_silenced.exists.return_value = False
                        manager = NotificationManager()
        
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        
        with patch.object(manager, '_save_scheduled_broadcasts'):
            broadcast = manager.create_scheduled_broadcast(
                title="Test",
                message="Test",
                scheduled_at=future_time,
                created_by="admin"
            )
            
            result = manager.cancel_scheduled_broadcast(broadcast.id)
        
        assert result is True
    
    def test_get_stats(self):
        """Should calculate stats"""
        from app.services.notification_manager import NotificationManager
        
        with patch('app.services.notification_manager.PREFERENCES_FILE') as mock_file:
            mock_file.exists.return_value = False
            with patch('app.services.notification_manager.HISTORY_FILE') as mock_history:
                mock_history.exists.return_value = False
                with patch('app.services.notification_manager.SCHEDULED_FILE') as mock_sched:
                    mock_sched.exists.return_value = False
                    with patch('app.services.notification_manager.SILENCED_DEVICES_FILE') as mock_silenced:
                        mock_silenced.exists.return_value = False
                        manager = NotificationManager()
        
        result = manager.get_stats()
        
        assert result.total_sent_24h >= 0


class TestDiscordServiceEdgeCases:
    """Edge case tests for Discord service"""
    
    async def test_discord_get_guilds_connected(self):
        """Should return guilds when connected"""
        from app.services.discord_service import DiscordNotificationService
        
        service = DiscordNotificationService()
        service._client = MagicMock()
        service._ready = asyncio.Event()
        service._ready.set()
        
        mock_guild = MagicMock()
        mock_guild.id = 123
        mock_guild.name = "Test Guild"
        mock_guild.icon = None
        service._client.guilds = [mock_guild]
        
        guilds = await service.get_guilds()
        
        assert len(guilds) == 1
        assert guilds[0].name == "Test Guild"
    
    async def test_discord_get_channels_guild_not_found(self):
        """Should return empty list when guild not found"""
        from app.services.discord_service import DiscordNotificationService
        
        service = DiscordNotificationService()
        service._client = MagicMock()
        service._ready = asyncio.Event()
        service._ready.set()
        
        service._client.get_guild = MagicMock(return_value=None)
        
        channels = await service.get_channels("123")
        
        assert channels == []
    
    def test_discord_bot_info_is_connected_false(self):
        """Should return is_connected=False when not connected"""
        from app.services.discord_service import DiscordNotificationService
        
        service = DiscordNotificationService()
        
        info = service.get_bot_info()
        
        assert info.is_connected is False


class TestAnomalyDetectorEdgeCases:
    """Edge case tests for AnomalyDetector"""
    
    def test_latency_stats_update(self):
        """Should update latency stats correctly"""
        from app.services.anomaly_detector import LatencyStats
        
        stats = LatencyStats()
        stats.update(10.0)
        stats.update(20.0)
        stats.update(30.0)
        
        assert stats.count == 3
        assert stats.mean == 20.0
        assert stats.min_value == 10.0
        assert stats.max_value == 30.0
    
    def test_latency_stats_variance(self):
        """Should calculate variance correctly"""
        from app.services.anomaly_detector import LatencyStats
        
        stats = LatencyStats()
        
        # With single value, variance should be 0
        stats.update(10.0)
        assert stats.variance == 0.0
        
        # With multiple values, should have variance
        stats.update(20.0)
        assert stats.variance > 0
    
    def test_latency_stats_to_from_dict(self):
        """Should serialize and deserialize correctly"""
        from app.services.anomaly_detector import LatencyStats
        
        stats = LatencyStats()
        stats.update(10.0)
        stats.update(20.0)
        
        data = stats.to_dict()
        restored = LatencyStats.from_dict(data)
        
        assert restored.count == stats.count
        assert restored.mean == stats.mean
    
    def test_device_stats_update_check(self):
        """Should update device stats correctly"""
        from app.services.anomaly_detector import DeviceStats
        
        stats = DeviceStats(device_ip="192.168.1.1")
        now = datetime.now()
        
        stats.update_check(True, latency_ms=10.0, packet_loss=0.0, check_time=now)
        assert stats.total_checks == 1
        assert stats.successful_checks == 1
        assert stats.consecutive_failures == 0
        
        stats.update_check(False, latency_ms=None, packet_loss=None, check_time=now)
        assert stats.total_checks == 2
        assert stats.successful_checks == 1
        assert stats.consecutive_failures == 1
    
    def test_device_stats_availability(self):
        """Should calculate availability correctly"""
        from app.services.anomaly_detector import DeviceStats
        
        stats = DeviceStats(device_ip="192.168.1.1")
        now = datetime.now()
        
        # No checks yet
        assert stats.availability == 0.0
        
        # Add successful checks
        stats.update_check(True, latency_ms=10.0, packet_loss=0.0, check_time=now)
        stats.update_check(True, latency_ms=10.0, packet_loss=0.0, check_time=now)
        stats.update_check(False, latency_ms=None, packet_loss=None, check_time=now)
        
        assert stats.availability == pytest.approx(66.67, rel=0.1)
    
    def test_train_device(self):
        """Should train on device metrics"""
        from app.services.anomaly_detector import AnomalyDetector
        
        with patch('app.services.anomaly_detector.BASELINES_FILE') as mock_file:
            mock_file.exists.return_value = False
            mock_file.parent.mkdir = MagicMock()
            with patch('app.services.anomaly_detector.MODEL_STATE_FILE') as mock_state:
                mock_state.exists.return_value = False
                with patch('app.services.anomaly_detector.DATA_DIR') as mock_dir:
                    mock_dir.exists.return_value = True
                    detector = AnomalyDetector()
        
        with patch.object(detector, '_save_state'):
            detector.train(
                device_ip="192.168.1.1",
                success=True,
                latency_ms=10.0
            )
        
        assert "192.168.1.1" in detector._device_stats
    
    def test_get_device_baseline(self):
        """Should return device baseline"""
        from app.services.anomaly_detector import AnomalyDetector, DeviceStats
        
        with patch('app.services.anomaly_detector.BASELINES_FILE') as mock_file:
            mock_file.exists.return_value = False
            with patch('app.services.anomaly_detector.MODEL_STATE_FILE') as mock_state:
                mock_state.exists.return_value = False
                with patch('app.services.anomaly_detector.DATA_DIR') as mock_dir:
                    mock_dir.exists.return_value = True
                    detector = AnomalyDetector()
        
        # Add some device stats
        stats = DeviceStats(device_ip="192.168.1.1")
        now = datetime.now()
        stats.update_check(True, latency_ms=10.0, packet_loss=0.0, check_time=now)
        stats.update_check(True, latency_ms=20.0, packet_loss=0.0, check_time=now)
        detector._device_stats["192.168.1.1"] = stats
        
        baseline = detector.get_device_baseline("192.168.1.1")
        
        assert baseline is not None
        assert baseline.device_ip == "192.168.1.1"
    
    def test_get_model_status(self):
        """Should return model status"""
        from app.services.anomaly_detector import AnomalyDetector
        
        with patch('app.services.anomaly_detector.BASELINES_FILE') as mock_file:
            mock_file.exists.return_value = False
            with patch('app.services.anomaly_detector.MODEL_STATE_FILE') as mock_state:
                mock_state.exists.return_value = False
                with patch('app.services.anomaly_detector.DATA_DIR') as mock_dir:
                    mock_dir.exists.return_value = True
                    detector = AnomalyDetector()
        
        status = detector.get_model_status()
        
        assert status.model_version is not None
        assert status.devices_tracked >= 0


class TestVersionCheckerEdgeCases:
    """Edge case tests for VersionChecker"""
    
    def test_compare_versions_major(self):
        """Should detect major version difference"""
        from app.services.version_checker import compare_versions
        
        has_update, update_type = compare_versions("1.0.0", "2.0.0")
        
        assert has_update is True
        assert update_type == "major"
    
    def test_compare_versions_minor(self):
        """Should detect minor version difference"""
        from app.services.version_checker import compare_versions
        
        has_update, update_type = compare_versions("1.0.0", "1.1.0")
        
        assert has_update is True
        assert update_type == "minor"
    
    def test_compare_versions_patch(self):
        """Should detect patch version difference"""
        from app.services.version_checker import compare_versions
        
        has_update, update_type = compare_versions("1.0.0", "1.0.1")
        
        assert has_update is True
        assert update_type == "patch"
    
    def test_compare_versions_equal(self):
        """Should detect equal versions"""
        from app.services.version_checker import compare_versions
        
        has_update, update_type = compare_versions("1.0.0", "1.0.0")
        
        assert has_update is False
        assert update_type is None
    
    def test_get_update_priority(self):
        """Should return appropriate priority for update type"""
        from app.services.version_checker import get_update_priority
        from app.models import NotificationPriority
        
        assert get_update_priority("major") == NotificationPriority.HIGH
        assert get_update_priority("minor") == NotificationPriority.MEDIUM
        assert get_update_priority("patch") == NotificationPriority.LOW
    
    def test_get_update_title(self):
        """Should return appropriate title for update type"""
        from app.services.version_checker import get_update_title
        
        title = get_update_title("major", "2.0.0")
        
        assert "2.0.0" in title
    
    def test_get_update_message(self):
        """Should return appropriate message for update type"""
        from app.services.version_checker import get_update_message
        
        message = get_update_message("major", "1.0.0", "2.0.0")
        
        assert "1.0.0" in message
        assert "2.0.0" in message
    
    async def test_checker_loop_basic(self):
        """Should run checker loop"""
        from app.services.version_checker import VersionChecker
        
        checker = VersionChecker()
        
        call_count = 0
        
        async def mock_sleep(*args):
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                raise asyncio.CancelledError()
        
        with patch.object(checker, '_check_for_updates', AsyncMock()):
            with patch('asyncio.sleep', side_effect=mock_sleep):
                try:
                    await checker._checker_loop()
                except asyncio.CancelledError:
                    pass


class TestEmailServiceEdgeCases:
    """Edge case tests for email service"""
    
    def test_build_html_all_fields(self):
        """Should build HTML with all fields"""
        from app.services.email_service import _build_notification_email_html
        from app.models import NetworkEvent, NotificationType, NotificationPriority
        
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            title="Test Device Offline",
            message="Router is offline",
            priority=NotificationPriority.HIGH,
            device_name="Router",
            device_ip="192.168.1.1",
            previous_state="online",
            current_state="offline"
        )
        
        html = _build_notification_email_html(event)
        
        assert "Router" in html
        assert "192.168.1.1" in html
    
    def test_build_text_all_fields(self):
        """Should build text with all fields"""
        from app.services.email_service import _build_notification_email_text
        from app.models import NetworkEvent, NotificationType, NotificationPriority
        
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            title="Test Device Offline",
            message="Router is offline",
            priority=NotificationPriority.HIGH,
            device_name="Router",
            device_ip="192.168.1.1"
        )
        
        text = _build_notification_email_text(event)
        
        assert "Router" in text
        assert "192.168.1.1" in text


class TestMainEdgeCases:
    """Edge case tests for main module"""
    
    def test_get_service_state_with_file(self):
        """Should load service state from file"""
        from app.main import _get_service_state
        
        state_data = {"clean_shutdown": True, "last_shutdown": "2024-01-01T00:00:00"}
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open()):
                with patch('json.load', return_value=state_data):
                    state = _get_service_state()
        
        assert state["clean_shutdown"] is True
    
    async def test_send_cartographer_down_with_details(self):
        """Should include details in down notification"""
        from app.main import _send_cartographer_down_notification
        
        with patch('app.main.notification_manager') as mock_nm:
            mock_nm.broadcast_notification = AsyncMock(return_value={})
            
            await _send_cartographer_down_notification()
            
            mock_nm.broadcast_notification.assert_called_once()


class TestModelsEdgeCases:
    """Edge case tests for models"""
    
    def test_network_event_minimal(self):
        """Should create NetworkEvent with minimal fields"""
        from app.models import NetworkEvent, NotificationType
        
        event = NetworkEvent(
            event_type=NotificationType.SYSTEM_STATUS,
            title="Test",
            message="Test message"
        )
        
        assert event.event_type == NotificationType.SYSTEM_STATUS
    
    def test_scheduled_broadcast_with_all_fields(self):
        """Should create ScheduledBroadcast with all fields"""
        from app.models import ScheduledBroadcast, ScheduledBroadcastStatus, NotificationType, NotificationPriority
        
        broadcast = ScheduledBroadcast(
            id=str(uuid4()),
            title="Test",
            message="Test message",
            scheduled_at=datetime.now(timezone.utc),
            status=ScheduledBroadcastStatus.PENDING,
            created_by="admin",
            event_type=NotificationType.SYSTEM_STATUS,
            priority=NotificationPriority.HIGH
        )
        
        assert broadcast.event_type == NotificationType.SYSTEM_STATUS
        assert broadcast.priority == NotificationPriority.HIGH

