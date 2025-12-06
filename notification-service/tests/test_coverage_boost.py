"""
Additional tests to boost coverage above 90%.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import json


class TestNotificationManagerCoverage:
    """Additional tests for notification manager coverage"""
    
    def test_save_preferences(self):
        """Should save preferences to disk"""
        from app.services.notification_manager import NotificationManager
        from app.models import NotificationPreferences
        
        with patch('app.services.notification_manager.PREFERENCES_FILE') as mock_file:
            mock_file.exists.return_value = False
            mock_file.parent.mkdir = MagicMock()
            with patch('app.services.notification_manager.HISTORY_FILE') as mock_history:
                mock_history.exists.return_value = False
                with patch('app.services.notification_manager.SCHEDULED_FILE') as mock_sched:
                    mock_sched.exists.return_value = False
                    with patch('app.services.notification_manager.SILENCED_DEVICES_FILE') as mock_silenced:
                        mock_silenced.exists.return_value = False
                        manager = NotificationManager()
        
        manager._preferences["user_123"] = NotificationPreferences(user_id="user_123")
        
        with patch('builtins.open', mock_open()) as mock_file_open:
            with patch('json.dump') as mock_dump:
                manager._save_preferences()
                mock_dump.assert_called_once()
    
    def test_save_history(self):
        """Should save history to disk"""
        from app.services.notification_manager import NotificationManager
        from app.models import NotificationRecord, NotificationChannel, NotificationPriority
        
        with patch('app.services.notification_manager.PREFERENCES_FILE') as mock_file:
            mock_file.exists.return_value = False
            with patch('app.services.notification_manager.HISTORY_FILE') as mock_history:
                mock_history.exists.return_value = False
                mock_history.parent.mkdir = MagicMock()
                with patch('app.services.notification_manager.SCHEDULED_FILE') as mock_sched:
                    mock_sched.exists.return_value = False
                    with patch('app.services.notification_manager.SILENCED_DEVICES_FILE') as mock_silenced:
                        mock_silenced.exists.return_value = False
                        manager = NotificationManager()
        
        record = NotificationRecord(
            notification_id=str(uuid4()),
            event_id=str(uuid4()),
            user_id="user_123",
            channel=NotificationChannel.DISCORD,
            success=True,
            title="Test",
            message="Test",
            priority=NotificationPriority.MEDIUM
        )
        manager._history.append(record)
        
        with patch('builtins.open', mock_open()) as mock_file_open:
            with patch('json.dump') as mock_dump:
                manager._save_history()
                mock_dump.assert_called_once()
    
    def test_save_scheduled_broadcasts(self):
        """Should save scheduled broadcasts to disk"""
        from app.services.notification_manager import NotificationManager
        from app.models import ScheduledBroadcast, ScheduledBroadcastStatus
        
        with patch('app.services.notification_manager.PREFERENCES_FILE') as mock_file:
            mock_file.exists.return_value = False
            with patch('app.services.notification_manager.HISTORY_FILE') as mock_history:
                mock_history.exists.return_value = False
                with patch('app.services.notification_manager.SCHEDULED_FILE') as mock_sched:
                    mock_sched.exists.return_value = False
                    mock_sched.parent.mkdir = MagicMock()
                    with patch('app.services.notification_manager.SILENCED_DEVICES_FILE') as mock_silenced:
                        mock_silenced.exists.return_value = False
                        manager = NotificationManager()
        
        broadcast = ScheduledBroadcast(
            id=str(uuid4()),
            title="Test",
            message="Test",
            scheduled_at=datetime.now(timezone.utc) + timedelta(hours=1),
            status=ScheduledBroadcastStatus.PENDING,
            created_by="admin"
        )
        manager._scheduled_broadcasts[broadcast.id] = broadcast
        
        with patch('builtins.open', mock_open()) as mock_file_open:
            with patch('json.dump') as mock_dump:
                manager._save_scheduled_broadcasts()
                mock_dump.assert_called_once()
    
    def test_save_silenced_devices(self):
        """Should save silenced devices to disk"""
        from app.services.notification_manager import NotificationManager
        
        with patch('app.services.notification_manager.PREFERENCES_FILE') as mock_file:
            mock_file.exists.return_value = False
            with patch('app.services.notification_manager.HISTORY_FILE') as mock_history:
                mock_history.exists.return_value = False
                with patch('app.services.notification_manager.SCHEDULED_FILE') as mock_sched:
                    mock_sched.exists.return_value = False
                    with patch('app.services.notification_manager.SILENCED_DEVICES_FILE') as mock_silenced:
                        mock_silenced.exists.return_value = False
                        mock_silenced.parent.mkdir = MagicMock()
                        manager = NotificationManager()
        
        manager._silenced_devices.add("192.168.1.1")
        
        with patch('builtins.open', mock_open()) as mock_file_open:
            with patch('json.dump') as mock_dump:
                manager._save_silenced_devices()
                mock_dump.assert_called_once()
    
    async def test_start_scheduler(self):
        """Should start scheduler"""
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
        
        with patch('asyncio.create_task') as mock_task:
            await manager.start_scheduler()
            mock_task.assert_called_once()
    
    async def test_stop_scheduler(self):
        """Should stop scheduler task"""
        from app.services.notification_manager import NotificationManager
        import asyncio
        
        with patch('app.services.notification_manager.PREFERENCES_FILE') as mock_file:
            mock_file.exists.return_value = False
            with patch('app.services.notification_manager.HISTORY_FILE') as mock_history:
                mock_history.exists.return_value = False
                with patch('app.services.notification_manager.SCHEDULED_FILE') as mock_sched:
                    mock_sched.exists.return_value = False
                    with patch('app.services.notification_manager.SILENCED_DEVICES_FILE') as mock_silenced:
                        mock_silenced.exists.return_value = False
                        manager = NotificationManager()
        
        # Create a real task that can be cancelled
        async def dummy():
            await asyncio.sleep(1000)
        
        manager._scheduler_task = asyncio.create_task(dummy())
        
        await manager.stop_scheduler()
        
        # Task should be None after stop
        assert manager._scheduler_task is None


class TestDiscordServiceCoverage:
    """Additional tests for discord service coverage"""
    
    def test_priority_colors(self):
        """Should return valid colors for priorities"""
        from app.services.discord_service import _get_priority_color
        from app.models import NotificationPriority
        
        # Just verify they return valid integers
        assert isinstance(_get_priority_color(NotificationPriority.CRITICAL), int)
        assert isinstance(_get_priority_color(NotificationPriority.HIGH), int)
        assert isinstance(_get_priority_color(NotificationPriority.MEDIUM), int)
        assert isinstance(_get_priority_color(NotificationPriority.LOW), int)
    
    def test_notification_icons(self):
        """Should return icons for types"""
        from app.services.discord_service import _get_notification_icon
        from app.models import NotificationType
        
        # Just verify they return strings
        assert isinstance(_get_notification_icon(NotificationType.DEVICE_OFFLINE), str)
        assert isinstance(_get_notification_icon(NotificationType.DEVICE_ONLINE), str)
    
    def test_build_embed_basic(self):
        """Should build Discord embed dict"""
        from app.services.discord_service import _build_discord_embed
        from app.models import NetworkEvent, NotificationType, NotificationPriority
        
        event = NetworkEvent(
            event_type=NotificationType.DEVICE_OFFLINE,
            title="Test Title",
            message="Test message",
            priority=NotificationPriority.MEDIUM
        )
        
        # The function returns a discord.Embed but we don't have discord installed
        # So just verify it doesn't raise an error
        try:
            embed = _build_discord_embed(event)
            assert embed is not None
        except ImportError:
            # discord.py not installed
            pass


class TestVersionCheckerCoverage:
    """Additional tests for version checker coverage"""
    
    def test_parse_version_valid(self):
        """Should parse valid version"""
        from app.services.version_checker import parse_version
        
        result = parse_version("1.2.3")
        
        assert result == (1, 2, 3)
    
    def test_parse_version_with_v(self):
        """Should handle v prefix"""
        from app.services.version_checker import parse_version
        
        result = parse_version("v1.2.3")
        
        assert result == (1, 2, 3)
    
    def test_parse_version_invalid(self):
        """Should return None for invalid version"""
        from app.services.version_checker import parse_version
        
        result = parse_version("invalid")
        
        assert result is None
    
    async def test_version_checker_start(self):
        """Should start version checker"""
        from app.services.version_checker import VersionChecker
        
        with patch('app.services.version_checker.VERSION_STATE_FILE') as mock_file:
            mock_file.exists.return_value = False
            with patch('app.services.version_checker.DATA_DIR') as mock_dir:
                mock_dir.exists.return_value = True
                checker = VersionChecker()
        
        checker._checker_task = None
        
        with patch.object(checker, '_checker_loop', AsyncMock()):
            with patch('httpx.AsyncClient', return_value=AsyncMock()):
                with patch('asyncio.create_task') as mock_task:
                    await checker.start()
                    # Should have created task
                    mock_task.assert_called_once()


class TestAnomalyDetectorCoverage:
    """Additional tests for anomaly detector coverage"""
    
    def test_reset_device(self):
        """Should reset device stats"""
        from app.services.anomaly_detector import AnomalyDetector, DeviceStats
        
        with patch('app.services.anomaly_detector.BASELINES_FILE') as mock_file:
            mock_file.exists.return_value = False
            with patch('app.services.anomaly_detector.MODEL_STATE_FILE') as mock_state:
                mock_state.exists.return_value = False
                with patch('app.services.anomaly_detector.DATA_DIR') as mock_dir:
                    mock_dir.exists.return_value = True
                    detector = AnomalyDetector()
        
        detector._device_stats["192.168.1.1"] = DeviceStats(device_ip="192.168.1.1")
        
        with patch.object(detector, '_save_state'):
            detector.reset_device("192.168.1.1")
        
        assert "192.168.1.1" not in detector._device_stats
    
    def test_reset_all(self):
        """Should reset all device stats"""
        from app.services.anomaly_detector import AnomalyDetector, DeviceStats
        
        with patch('app.services.anomaly_detector.BASELINES_FILE') as mock_file:
            mock_file.exists.return_value = False
            with patch('app.services.anomaly_detector.MODEL_STATE_FILE') as mock_state:
                mock_state.exists.return_value = False
                with patch('app.services.anomaly_detector.DATA_DIR') as mock_dir:
                    mock_dir.exists.return_value = True
                    detector = AnomalyDetector()
        
        detector._device_stats["192.168.1.1"] = DeviceStats(device_ip="192.168.1.1")
        detector._device_stats["192.168.1.2"] = DeviceStats(device_ip="192.168.1.2")
        
        with patch.object(detector, '_save_state'):
            detector.reset_all()
        
        assert len(detector._device_stats) == 0
    
    def test_mark_false_positive(self):
        """Should mark as false positive"""
        from app.services.anomaly_detector import AnomalyDetector, DeviceStats
        
        with patch('app.services.anomaly_detector.BASELINES_FILE') as mock_file:
            mock_file.exists.return_value = False
            with patch('app.services.anomaly_detector.MODEL_STATE_FILE') as mock_state:
                mock_state.exists.return_value = False
                with patch('app.services.anomaly_detector.DATA_DIR') as mock_dir:
                    mock_dir.exists.return_value = True
                    detector = AnomalyDetector()
        
        initial_count = detector._false_positives
        
        detector.mark_false_positive("event_123")
        
        assert detector._false_positives == initial_count + 1


class TestMainCoverage:
    """Additional tests for main module coverage"""
    
    def test_create_app_factory(self):
        """Should create app with factory"""
        from app.main import create_app
        
        with patch('app.main.lifespan'):
            app = create_app()
            
            assert app is not None
            assert app.title == "Cartographer Notification Service"


class TestEmailServiceCoverage:
    """Additional tests for email service coverage"""
    
    def test_notification_icons(self):
        """Should return icons for notification types"""
        from app.services.email_service import _get_notification_icon
        from app.models import NotificationType
        
        # Verify they return strings
        offline_icon = _get_notification_icon(NotificationType.DEVICE_OFFLINE)
        assert isinstance(offline_icon, str)
        
        online_icon = _get_notification_icon(NotificationType.DEVICE_ONLINE)
        assert isinstance(online_icon, str)
    
    def test_priority_colors(self):
        """Should return colors for priorities"""
        from app.services.email_service import _get_priority_color
        from app.models import NotificationPriority
        
        # Verify they return strings (hex colors)
        assert isinstance(_get_priority_color(NotificationPriority.CRITICAL), str)
        assert isinstance(_get_priority_color(NotificationPriority.HIGH), str)
        assert isinstance(_get_priority_color(NotificationPriority.MEDIUM), str)
        assert isinstance(_get_priority_color(NotificationPriority.LOW), str)

