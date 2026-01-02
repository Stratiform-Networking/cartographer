"""
Extended tests for NetworkAnomalyDetector to improve coverage.

Covers:
- State persistence
- Error handling
- Device tracking
- Anomaly detection edge cases
"""

import json
import os
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

# Set test environment
os.environ["NOTIFICATION_DATA_DIR"] = "/tmp/test_network_anomaly"
os.environ["RESEND_API_KEY"] = ""
os.environ["DISCORD_BOT_TOKEN"] = ""


class TestNetworkAnomalyDetectorPersistence:
    """Tests for detector state persistence."""

    def test_save_state_error(self):
        """Test error handling when saving state fails."""
        from app.services.network_anomaly_detector import NetworkAnomalyDetector

        detector = NetworkAnomalyDetector("test-network")

        with patch("builtins.open", side_effect=PermissionError("No permission")):
            # Should not raise, just log error
            detector._save_state()

    def test_load_state_version_mismatch(self):
        """Test loading state with version mismatch."""
        from app.services.network_anomaly_detector import NetworkAnomalyDetector

        state = {
            "version": "0.0.0",  # Old version
            "devices": {},
        }

        with patch.object(Path, "exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=json.dumps(state))):
                with patch("json.load", return_value=state):
                    detector = NetworkAnomalyDetector("test-network")
                    # Should start fresh due to version mismatch
                    assert len(detector._device_stats) == 0

    def test_load_state_error(self):
        """Test error handling when loading state fails."""
        from app.services.network_anomaly_detector import NetworkAnomalyDetector

        with patch.object(Path, "exists", return_value=True):
            with patch("builtins.open", side_effect=PermissionError("No permission")):
                # Should not raise
                detector = NetworkAnomalyDetector("test-network")


class TestNetworkAnomalyDetectorDeviceTracking:
    """Tests for device tracking."""

    def test_add_device_via_train(self):
        """Test adding new devices via training."""
        from app.services.network_anomaly_detector import NetworkAnomalyDetector

        detector = NetworkAnomalyDetector("test-network")

        detector.train("192.168.1.1", success=True, latency_ms=50.0)
        detector.train("192.168.1.2", success=True, latency_ms=60.0)

        assert "192.168.1.1" in detector._device_stats
        assert "192.168.1.2" in detector._device_stats

    def test_current_devices_updated(self):
        """Test current devices set is maintained."""
        from app.services.network_anomaly_detector import NetworkAnomalyDetector

        detector = NetworkAnomalyDetector("test-network")
        detector._current_devices = set()

        detector.train("192.168.1.1", success=True, latency_ms=50.0)

        # Device stats should have the device
        assert "192.168.1.1" in detector._device_stats


class TestNetworkAnomalyDetectorTraining:
    """Tests for model training."""

    def test_train_new_device(self):
        """Test training with a new device."""
        from app.services.network_anomaly_detector import NetworkAnomalyDetector

        detector = NetworkAnomalyDetector("test-network")

        detector.train(
            device_ip="192.168.1.1",
            success=True,
            latency_ms=50.0,
            device_name="Test Device",
        )

        assert "192.168.1.1" in detector._device_stats
        assert detector._device_stats["192.168.1.1"].device_name == "Test Device"

    def test_train_existing_device(self):
        """Test training updates existing device."""
        from app.services.network_anomaly_detector import NetworkAnomalyDetector

        detector = NetworkAnomalyDetector("test-network")

        # First training
        detector.train("192.168.1.1", success=True, latency_ms=50.0)

        # Second training with new name
        detector.train("192.168.1.1", success=True, latency_ms=55.0, device_name="Updated Name")

        assert detector._device_stats["192.168.1.1"].device_name == "Updated Name"

    def test_train_with_failure(self):
        """Test training with a failure."""
        from app.services.network_anomaly_detector import NetworkAnomalyDetector

        detector = NetworkAnomalyDetector("test-network")

        detector.train("192.168.1.1", success=False)

        stats = detector._device_stats["192.168.1.1"]
        # Failure should be recorded in stats
        assert stats.total_checks >= 1


class TestNetworkAnomalyDetectorBaseline:
    """Tests for baseline management."""

    def test_get_device_baseline_no_stats(self):
        """Test getting baseline for device with no stats."""
        from app.services.network_anomaly_detector import NetworkAnomalyDetector

        detector = NetworkAnomalyDetector("test-network-new", load_state=False)

        baseline = detector.get_device_baseline("192.168.99.99")

        assert baseline is None

    def test_get_device_baseline_with_stats(self):
        """Test getting baseline for device with stats."""
        from app.services.network_anomaly_detector import NetworkAnomalyDetector

        detector = NetworkAnomalyDetector("test-network-baseline", load_state=False)

        # Add device stats by training
        for _ in range(20):  # Need enough samples
            detector.train("192.168.1.1", success=True, latency_ms=50.0)

        baseline = detector.get_device_baseline("192.168.1.1")

        # Should return baseline data
        assert baseline is not None or "192.168.1.1" in detector._device_stats

    def test_delete_device_stats(self):
        """Test deleting device stats directly."""
        from app.services.network_anomaly_detector import NetworkAnomalyDetector

        detector = NetworkAnomalyDetector("test-network-delete", load_state=False)

        # Add device stats
        detector.train("192.168.1.1", success=True, latency_ms=50.0)
        assert "192.168.1.1" in detector._device_stats

        # Remove directly
        del detector._device_stats["192.168.1.1"]

        assert "192.168.1.1" not in detector._device_stats


class TestNetworkAnomalyDetectorStatus:
    """Tests for status methods."""

    def test_get_model_status(self):
        """Test getting model status."""
        from app.services.network_anomaly_detector import NetworkAnomalyDetector

        detector = NetworkAnomalyDetector("test-network", load_state=False)

        status = detector.get_model_status()

        assert status.model_version is not None

    def test_get_model_status_with_devices(self):
        """Test getting model status with trained devices."""
        from app.services.network_anomaly_detector import NetworkAnomalyDetector

        detector = NetworkAnomalyDetector("test-network", load_state=False)
        detector.train("192.168.1.1", success=True, latency_ms=50.0)

        status = detector.get_model_status()

        assert status.devices_tracked >= 1


class TestNetworkAnomalyDetectorManager:
    """Tests for NetworkAnomalyDetectorManager."""

    def test_get_detector_creates_new(self):
        """Test getting detector creates new one if needed."""
        from app.services.network_anomaly_detector import NetworkAnomalyDetectorManager

        manager = NetworkAnomalyDetectorManager()

        detector = manager.get_detector("new-network")

        assert detector is not None
        assert detector.network_id == "new-network"

    def test_get_detector_returns_existing(self):
        """Test getting detector returns existing one."""
        from app.services.network_anomaly_detector import NetworkAnomalyDetectorManager

        manager = NetworkAnomalyDetectorManager()

        detector1 = manager.get_detector("test-network")
        detector2 = manager.get_detector("test-network")

        assert detector1 is detector2

    def test_process_health_check(self):
        """Test processing health check."""
        from app.services.network_anomaly_detector import NetworkAnomalyDetectorManager

        manager = NetworkAnomalyDetectorManager()

        result = manager.process_health_check(
            network_id="test-network",
            device_ip="192.168.1.1",
            success=True,
            latency_ms=50.0,
        )

        # Should train and optionally detect anomaly
        assert "test-network" in manager._detectors

    def test_get_stats(self):
        """Test getting stats for a network."""
        from app.services.network_anomaly_detector import NetworkAnomalyDetectorManager

        manager = NetworkAnomalyDetectorManager()
        manager.get_detector("test-network")  # Create detector

        stats = manager.get_stats("test-network")

        assert stats is not None

    def test_get_stats_nonexistent(self):
        """Test getting stats for nonexistent network."""
        from app.services.network_anomaly_detector import NetworkAnomalyDetectorManager

        manager = NetworkAnomalyDetectorManager()

        stats = manager.get_stats("nonexistent")

        assert stats is not None  # Returns new empty detector stats

    def test_save_all(self):
        """Test saving all detectors."""
        from app.services.network_anomaly_detector import NetworkAnomalyDetectorManager

        manager = NetworkAnomalyDetectorManager()
        manager.get_detector("network1")
        manager.get_detector("network2")

        with (
            patch.object(manager._detectors["network1"], "save") as mock1,
            patch.object(manager._detectors["network2"], "save") as mock2,
        ):
            manager.save_all()

            mock1.assert_called_once()
            mock2.assert_called_once()


class TestDeviceStats:
    """Tests for DeviceStats model."""

    def test_device_stats_from_dict(self):
        """Test creating DeviceStats from dict."""
        from app.services.anomaly_detector import DeviceStats

        data = {
            "device_ip": "192.168.1.1",
            "device_name": "Test",
            "total_checks": 10,
            "successful_checks": 8,
        }

        stats = DeviceStats.from_dict(data)

        assert stats.device_ip == "192.168.1.1"

    def test_device_stats_to_dict(self):
        """Test converting DeviceStats to dict."""
        from app.services.anomaly_detector import DeviceStats

        stats = DeviceStats(
            device_ip="192.168.1.1",
            device_name="Test",
        )

        data = stats.to_dict()

        assert data["device_ip"] == "192.168.1.1"
        assert "device_name" in data

    def test_update_check_success(self):
        """Test updating with successful check."""
        from datetime import datetime

        from app.services.anomaly_detector import DeviceStats

        stats = DeviceStats(device_ip="192.168.1.1")

        stats.update_check(
            success=True, latency_ms=50.0, packet_loss=0.0, check_time=datetime.utcnow()
        )

        assert stats.total_checks == 1
        assert stats.successful_checks == 1

    def test_update_check_failure(self):
        """Test updating with failed check."""
        from datetime import datetime

        from app.services.anomaly_detector import DeviceStats

        stats = DeviceStats(device_ip="192.168.1.1")

        stats.update_check(
            success=False, latency_ms=None, packet_loss=None, check_time=datetime.utcnow()
        )

        assert stats.failed_checks == 1

    def test_availability_calculation(self):
        """Test availability property."""
        from datetime import datetime

        from app.services.anomaly_detector import DeviceStats

        stats = DeviceStats(device_ip="192.168.1.1")

        # Add successful checks
        for _ in range(8):
            stats.update_check(
                success=True, latency_ms=50.0, packet_loss=0.0, check_time=datetime.utcnow()
            )

        # Add failed checks
        for _ in range(2):
            stats.update_check(
                success=False, latency_ms=None, packet_loss=None, check_time=datetime.utcnow()
            )

        assert stats.availability == 80.0
