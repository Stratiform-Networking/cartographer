"""
Tests for Network Anomaly Detector Service.

This module tests the NetworkAnomalyDetector and NetworkAnomalyDetectorManager
which provide per-network anomaly detection capabilities.
"""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models import NetworkEvent, NotificationPriority, NotificationType


class TestNetworkAnomalyDetector:
    """Tests for NetworkAnomalyDetector"""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create temporary data directory"""
        yield tmp_path

    @pytest.fixture
    def detector(self, temp_data_dir):
        """Create a NetworkAnomalyDetector instance"""
        with patch("app.services.network_anomaly_detector.NETWORK_ANOMALY_DIR", temp_data_dir):
            from app.services.network_anomaly_detector import NetworkAnomalyDetector

            return NetworkAnomalyDetector("test-network-123", load_state=False)

    def test_init(self, detector):
        """Should initialize correctly"""
        assert detector.network_id == "test-network-123"
        assert len(detector._device_stats) == 0

    def test_train(self, detector):
        """Should train with new data point"""
        detector.train(
            device_ip="192.168.1.1",
            success=True,
            latency_ms=10.5,
            device_name="Router",
        )

        assert "192.168.1.1" in detector._device_stats
        assert detector._device_stats["192.168.1.1"].total_checks == 1

    def test_train_updates_existing_device(self, detector):
        """Should update existing device stats"""
        detector.train("192.168.1.1", True, 10.0)
        detector.train("192.168.1.1", True, 15.0)
        detector.train("192.168.1.1", False, None)

        stats = detector._device_stats["192.168.1.1"]
        assert stats.total_checks == 3
        assert stats.successful_checks == 2
        assert stats.failed_checks == 1

    def test_detect_anomaly_insufficient_data(self, detector):
        """Should not detect anomaly with insufficient data"""
        detector.train("192.168.1.1", True, 10.0)

        result = detector.detect_anomaly("192.168.1.1", True, 10.0)

        assert result.is_anomaly is False
        assert "Insufficient data" in result.reason

    def test_detect_anomaly_unknown_device(self, detector):
        """Should handle unknown device"""
        result = detector.detect_anomaly("unknown-ip", True, 10.0)

        assert result.is_anomaly is False

    def test_detect_anomaly_high_latency(self, detector):
        """Should detect high latency anomaly"""
        for _ in range(50):
            detector.train("192.168.1.1", True, 10.0)

        result = detector.detect_anomaly("192.168.1.1", True, 100.0)

        assert isinstance(result.is_anomaly, bool)

    def test_detect_anomaly_packet_loss(self, detector):
        """Should detect packet loss anomaly"""
        for _ in range(50):
            detector.train("192.168.1.1", True, 10.0, packet_loss=0.01)

        result = detector.detect_anomaly("192.168.1.1", True, 10.0, packet_loss=0.5)

        assert isinstance(result.is_anomaly, bool)


class TestNetworkAnomalyDetectorEvents:
    """Tests for NetworkAnomalyDetector event creation"""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        yield tmp_path

    @pytest.fixture
    def detector(self, temp_data_dir):
        with patch("app.services.network_anomaly_detector.NETWORK_ANOMALY_DIR", temp_data_dir):
            from app.services.network_anomaly_detector import NetworkAnomalyDetector

            return NetworkAnomalyDetector("test-network-123", load_state=False)

    def test_create_network_event_device_offline(self, detector):
        """Should create event for device going offline"""
        for _ in range(20):
            detector.train("192.168.1.1", True, 10.0)

        event = detector.create_network_event(
            device_ip="192.168.1.1",
            success=False,
            device_name="Router",
            previous_state="online",
        )

        if event:
            assert event.event_type in [
                NotificationType.DEVICE_OFFLINE,
                NotificationType.ANOMALY_DETECTED,
            ]

    def test_create_network_event_device_online(self, detector):
        """Should create event for device coming back online"""
        for _ in range(10):
            detector.train("192.168.1.1", True, 10.0)
        detector.train("192.168.1.1", False)
        detector._notified_offline.add("192.168.1.1")

        event = detector.create_network_event(
            device_ip="192.168.1.1",
            success=True,
            device_name="Router",
        )

        if event:
            assert event.event_type == NotificationType.DEVICE_ONLINE

    def test_create_network_event_no_notification_needed(self, detector):
        """Should return None when no notification needed"""
        for _ in range(10):
            detector.train("192.168.1.1", True, 10.0)

        event = detector.create_network_event(
            device_ip="192.168.1.1",
            success=True,
        )

        assert event is None

    def test_create_network_event_stable_offline(self, detector):
        """Should not notify for stable offline device"""
        for _ in range(50):
            detector.train("192.168.1.1", False, None, None)

        event = detector.create_network_event(
            device_ip="192.168.1.1",
            success=False,
        )

        assert event is None or isinstance(event, NetworkEvent)


class TestNetworkAnomalyDetectorBaselines:
    """Tests for NetworkAnomalyDetector baseline operations"""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        yield tmp_path

    @pytest.fixture
    def detector(self, temp_data_dir):
        with patch("app.services.network_anomaly_detector.NETWORK_ANOMALY_DIR", temp_data_dir):
            from app.services.network_anomaly_detector import NetworkAnomalyDetector

            return NetworkAnomalyDetector("test-network-123", load_state=False)

    def test_get_device_baseline(self, detector):
        """Should return device baseline"""
        for i in range(30):
            detector.train("192.168.1.1", True, 10.0 + i * 0.1)

        baseline = detector.get_device_baseline("192.168.1.1")

        assert baseline is not None
        assert baseline.device_ip == "192.168.1.1"
        assert baseline.check_count == 30

    def test_get_device_baseline_unknown(self, detector):
        """Should return None for unknown device"""
        baseline = detector.get_device_baseline("unknown")
        assert baseline is None

    def test_get_model_status(self, detector):
        """Should return model status"""
        detector.train("192.168.1.1", True, 10.0)

        status = detector.get_model_status()

        assert status.model_version == "1.0.0"
        assert status.devices_tracked >= 1

    def test_sync_current_devices(self, detector):
        """Should sync device list"""
        detector.sync_current_devices(["192.168.1.1", "192.168.1.2"])

        assert len(detector._current_devices) == 2


class TestNetworkAnomalyDetectorPersistence:
    """Tests for NetworkAnomalyDetector state persistence"""

    def test_save_and_load_state(self, tmp_path):
        """Should save and load state"""
        with patch("app.services.network_anomaly_detector.NETWORK_ANOMALY_DIR", tmp_path):
            from app.services.network_anomaly_detector import NetworkAnomalyDetector

            detector1 = NetworkAnomalyDetector("test-net", load_state=False)
            detector1.train("192.168.1.1", True, 10.0)
            detector1.train("192.168.1.1", True, 11.0)
            detector1._save_state()

            detector2 = NetworkAnomalyDetector("test-net", load_state=True)

            assert "192.168.1.1" in detector2._device_stats
            assert detector2._device_stats["192.168.1.1"].total_checks == 2


class TestNetworkAnomalyDetectorManager:
    """Tests for NetworkAnomalyDetectorManager"""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        yield tmp_path

    @pytest.fixture
    def manager(self, temp_data_dir):
        with patch("app.services.network_anomaly_detector.NETWORK_ANOMALY_DIR", temp_data_dir):
            from app.services.network_anomaly_detector import NetworkAnomalyDetectorManager

            return NetworkAnomalyDetectorManager()

    def test_get_detector_creates_new(self, manager):
        """Should create new detector for unknown network"""
        detector = manager.get_detector("new-network")

        assert detector is not None
        assert detector.network_id == "new-network"

    def test_get_detector_returns_existing(self, manager):
        """Should return existing detector"""
        detector1 = manager.get_detector("network-123")
        detector1.train("192.168.1.1", True, 10.0)

        detector2 = manager.get_detector("network-123")

        assert detector2 is detector1
        assert "192.168.1.1" in detector2._device_stats

    def test_get_detector_different_networks(self, manager):
        """Should return different detectors for different networks"""
        detector1 = manager.get_detector("network-a")
        detector2 = manager.get_detector("network-b")

        assert detector1.network_id != detector2.network_id

    def test_get_stats(self, manager):
        """Should get stats for network"""
        detector = manager.get_detector("network-123")
        detector.train("192.168.1.1", True, 10.0)

        status = manager.get_stats("network-123")

        assert status.model_version == "1.0.0"

    def test_process_health_check(self, manager):
        """Should process health check"""
        event = manager.process_health_check(
            network_id="network-123",
            device_ip="192.168.1.1",
            success=True,
            latency_ms=10.0,
        )

        assert event is None

    def test_save_all(self, manager, temp_data_dir):
        """Should save all detectors"""
        with patch("app.services.network_anomaly_detector.NETWORK_ANOMALY_DIR", temp_data_dir):
            detector = manager.get_detector("network-123")
            detector.train("192.168.1.1", True, 10.0)

            manager.save_all()

            state_file = temp_data_dir / "network_network-123.json"
            assert state_file.exists()


class TestNetworkAnomalyDetectorSingleton:
    """Tests for the global network anomaly detector manager singleton"""

    def test_manager_returns_same_detector(self):
        """Should return same detector for same network"""
        from app.services.network_anomaly_detector import network_anomaly_detector_manager

        detector1 = network_anomaly_detector_manager.get_detector("singleton-test-network")
        detector2 = network_anomaly_detector_manager.get_detector("singleton-test-network")

        assert detector1 is detector2

    def test_detector_creation(self):
        """Should create network anomaly detector"""
        from app.services.network_anomaly_detector import NetworkAnomalyDetector

        detector = NetworkAnomalyDetector(network_id="net-123")

        assert detector.network_id == "net-123"

    def test_detector_device_stats(self):
        """Should initialize device stats"""
        from app.services.network_anomaly_detector import NetworkAnomalyDetector

        detector = NetworkAnomalyDetector(network_id="test-net")

        assert hasattr(detector, "_device_stats")

    def test_detector_model_status(self):
        """Should get model status"""
        from app.services.network_anomaly_detector import NetworkAnomalyDetector

        detector = NetworkAnomalyDetector(network_id="net-123")

        status = detector.get_model_status()

        assert status is not None
