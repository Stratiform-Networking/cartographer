"""
Unit tests for AnomalyDetector service.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.services.anomaly_detector import (
    AnomalyDetector,
    DeviceStats,
    LatencyStats,
    MIN_SAMPLES_FOR_BASELINE,
)
from app.models import (
    NotificationType,
    NotificationPriority,
    AnomalyType,
)


class TestLatencyStats:
    """Tests for LatencyStats class"""
    
    def test_update(self):
        """Should update stats correctly"""
        stats = LatencyStats()
        stats.update(10.0)
        stats.update(20.0)
        stats.update(30.0)
        
        assert stats.count == 3
        assert stats.mean == 20.0
        assert stats.min_value == 10.0
        assert stats.max_value == 30.0
    
    def test_variance_single_sample(self):
        """Should return 0 variance for single sample"""
        stats = LatencyStats()
        stats.update(10.0)
        
        assert stats.variance == 0.0
    
    def test_std_dev(self):
        """Should calculate standard deviation"""
        stats = LatencyStats()
        for val in [10, 20, 30, 40, 50]:
            stats.update(float(val))
        
        assert stats.std_dev > 0
    
    def test_to_dict(self):
        """Should serialize to dict"""
        stats = LatencyStats()
        stats.update(10.0)
        
        d = stats.to_dict()
        
        assert "count" in d
        assert "mean" in d
    
    def test_from_dict(self):
        """Should deserialize from dict"""
        stats = LatencyStats.from_dict({
            "count": 5,
            "mean": 25.0,
            "m2": 100.0,
            "min_value": 10.0,
            "max_value": 40.0
        })
        
        assert stats.count == 5
        assert stats.mean == 25.0


class TestDeviceStats:
    """Tests for DeviceStats class"""
    
    def test_update_check_success(self):
        """Should update stats on successful check"""
        stats = DeviceStats(device_ip="192.168.1.1")
        check_time = datetime.utcnow()
        
        stats.update_check(True, 25.0, 0.0, check_time)
        
        assert stats.total_checks == 1
        assert stats.successful_checks == 1
        assert stats.consecutive_successes == 1
    
    def test_update_check_failure(self):
        """Should update stats on failed check"""
        stats = DeviceStats(device_ip="192.168.1.1")
        check_time = datetime.utcnow()
        
        stats.update_check(False, None, None, check_time)
        
        assert stats.total_checks == 1
        assert stats.failed_checks == 1
        assert stats.consecutive_failures == 1
    
    def test_availability(self):
        """Should calculate availability"""
        stats = DeviceStats(device_ip="192.168.1.1")
        stats.total_checks = 100
        stats.successful_checks = 90
        
        assert stats.availability == 90.0
    
    def test_availability_no_checks(self):
        """Should return 0 with no checks"""
        stats = DeviceStats(device_ip="192.168.1.1")
        
        assert stats.availability == 0.0
    
    def test_state_transitions(self):
        """Should track state transitions"""
        stats = DeviceStats(device_ip="192.168.1.1")
        now = datetime.utcnow()
        
        stats.update_check(True, 25.0, 0.0, now)
        stats.update_check(False, None, None, now)
        stats.update_check(True, 25.0, 0.0, now)
        
        assert stats.state_transitions == 2
    
    def test_is_stable_state(self):
        """Should detect stable state"""
        stats = DeviceStats(device_ip="192.168.1.1")
        stats.total_checks = 50
        stats.state_transitions = 2  # Low transition ratio
        
        assert stats.is_stable_state(min_samples=20) is True
    
    def test_is_stable_offline(self):
        """Should detect stable offline device"""
        stats = DeviceStats(device_ip="192.168.1.1")
        stats.total_checks = 50
        stats.successful_checks = 5
        stats.failed_checks = 45
        stats.state_transitions = 1
        
        assert stats.is_stable_offline() is True
    
    def test_is_stable_online(self):
        """Should detect stable online device"""
        stats = DeviceStats(device_ip="192.168.1.1")
        stats.total_checks = 50
        stats.successful_checks = 48
        stats.failed_checks = 2
        stats.state_transitions = 1
        
        assert stats.is_stable_online() is True
    
    def test_get_expected_state(self):
        """Should predict expected state"""
        stats = DeviceStats(device_ip="192.168.1.1")
        stats.total_checks = 100
        stats.successful_checks = 90
        stats.hourly_patterns[10] = (45, 50)  # 90% at 10am
        
        state, confidence = stats.get_expected_state_for_time(
            datetime(2024, 1, 1, 10, 0)
        )
        
        assert state == "online"
    
    def test_to_dict(self):
        """Should serialize to dict"""
        stats = DeviceStats(device_ip="192.168.1.1", device_name="Test")
        
        d = stats.to_dict()
        
        assert d["device_ip"] == "192.168.1.1"
        assert d["device_name"] == "Test"
    
    def test_from_dict(self):
        """Should deserialize from dict"""
        stats = DeviceStats.from_dict({
            "device_ip": "192.168.1.1",
            "device_name": "Test",
            "total_checks": 100,
            "successful_checks": 90,
            "failed_checks": 10,
            "latency_stats": {"count": 0, "mean": 0, "m2": 0, "max_value": 0},
            "packet_loss_stats": {"count": 0, "mean": 0, "m2": 0, "max_value": 0},
            "hourly_patterns": {},
            "daily_patterns": {},
        })
        
        assert stats.device_ip == "192.168.1.1"
        assert stats.total_checks == 100


class TestAnomalyDetector:
    """Tests for AnomalyDetector class"""
    
    def test_train_new_device(self, anomaly_detector_instance):
        """Should train on new device"""
        with patch.object(anomaly_detector_instance, '_save_state'):
            anomaly_detector_instance.train(
                "192.168.1.100",
                success=True,
                latency_ms=25.0,
                device_name="Test Device"
            )
        
        assert "192.168.1.100" in anomaly_detector_instance._device_stats
    
    def test_train_updates_stats(self, anomaly_detector_instance):
        """Should update device stats"""
        with patch.object(anomaly_detector_instance, '_save_state'):
            for _ in range(10):
                anomaly_detector_instance.train(
                    "192.168.1.100",
                    success=True,
                    latency_ms=25.0
                )
        
        stats = anomaly_detector_instance._device_stats["192.168.1.100"]
        assert stats.total_checks == 10
    
    def test_detect_anomaly_insufficient_data(self, anomaly_detector_instance):
        """Should not detect anomaly with insufficient data"""
        result = anomaly_detector_instance.detect_anomaly(
            "192.168.1.100",
            success=False
        )
        
        assert result.is_anomaly is False
        assert result.confidence == 0.0
    
    def test_detect_anomaly_stable_offline(self, anomaly_detector_instance, sample_device_stats):
        """Should not flag stable offline device as anomaly"""
        sample_device_stats.total_checks = 100
        sample_device_stats.successful_checks = 5
        sample_device_stats.failed_checks = 95
        sample_device_stats.state_transitions = 2
        
        anomaly_detector_instance._device_stats["192.168.1.100"] = sample_device_stats
        
        result = anomaly_detector_instance.detect_anomaly(
            "192.168.1.100",
            success=False
        )
        
        assert result.is_anomaly is False
    
    def test_detect_anomaly_unexpected_offline(self, anomaly_detector_instance, sample_device_stats):
        """Should detect unexpected offline"""
        sample_device_stats.total_checks = 100
        sample_device_stats.successful_checks = 95
        sample_device_stats.failed_checks = 5
        sample_device_stats.state_transitions = 20  # Not stable
        
        anomaly_detector_instance._device_stats["192.168.1.100"] = sample_device_stats
        
        result = anomaly_detector_instance.detect_anomaly(
            "192.168.1.100",
            success=False
        )
        
        assert result.is_anomaly is True
        assert result.anomaly_type == AnomalyType.UNEXPECTED_OFFLINE
    
    def test_detect_anomaly_latency_spike(self, anomaly_detector_instance, sample_device_stats):
        """Should detect latency spike"""
        sample_device_stats.latency_stats.count = 100
        sample_device_stats.latency_stats.mean = 25.0
        sample_device_stats.latency_stats.m2 = 500.0  # std_dev ~ 2.25
        
        anomaly_detector_instance._device_stats["192.168.1.100"] = sample_device_stats
        
        result = anomaly_detector_instance.detect_anomaly(
            "192.168.1.100",
            success=True,
            latency_ms=100.0  # Way above normal
        )
        
        assert result.is_anomaly is True
        assert result.anomaly_type == AnomalyType.UNUSUAL_LATENCY_SPIKE
    
    def test_detect_anomaly_packet_loss(self, anomaly_detector_instance, sample_device_stats):
        """Should detect packet loss"""
        anomaly_detector_instance._device_stats["192.168.1.100"] = sample_device_stats
        
        result = anomaly_detector_instance.detect_anomaly(
            "192.168.1.100",
            success=True,
            packet_loss=0.25  # 25% packet loss
        )
        
        assert result.is_anomaly is True
        assert result.anomaly_type == AnomalyType.UNUSUAL_PACKET_LOSS
    
    def test_create_network_event_device_offline(self, anomaly_detector_instance):
        """Should create event when device goes offline"""
        # Build up history
        with patch.object(anomaly_detector_instance, '_save_state'):
            for _ in range(20):
                anomaly_detector_instance.train(
                    "192.168.1.100",
                    success=True,
                    latency_ms=25.0,
                    device_name="Test Device"
                )
        
        # Now device goes offline
        with patch.object(anomaly_detector_instance, '_save_state'):
            event = anomaly_detector_instance.create_network_event(
                "192.168.1.100",
                success=False,
                device_name="Test Device",
                previous_state="online"
            )
        
        assert event is not None
        assert event.event_type == NotificationType.DEVICE_OFFLINE
    
    def test_create_network_event_device_online(self, anomaly_detector_instance):
        """Should create event when device comes back online"""
        # Set up device that was offline
        anomaly_detector_instance._notified_offline.add("192.168.1.100")
        
        with patch.object(anomaly_detector_instance, '_save_state'):
            for _ in range(5):
                anomaly_detector_instance.train(
                    "192.168.1.100",
                    success=False,
                    device_name="Test Device"
                )
        
        # Now device comes online
        with patch.object(anomaly_detector_instance, '_save_state'):
            event = anomaly_detector_instance.create_network_event(
                "192.168.1.100",
                success=True,
                device_name="Test Device",
                previous_state="offline"
            )
        
        assert event is not None
        assert event.event_type == NotificationType.DEVICE_ONLINE
    
    def test_get_device_baseline(self, anomaly_detector_instance, sample_device_stats):
        """Should return device baseline"""
        anomaly_detector_instance._device_stats["192.168.1.100"] = sample_device_stats
        
        baseline = anomaly_detector_instance.get_device_baseline("192.168.1.100")
        
        assert baseline is not None
        assert baseline.device_ip == "192.168.1.100"
    
    def test_get_device_baseline_not_found(self, anomaly_detector_instance):
        """Should return None for unknown device"""
        baseline = anomaly_detector_instance.get_device_baseline("192.168.1.999")
        
        assert baseline is None
    
    def test_get_model_status(self, anomaly_detector_instance, sample_device_stats):
        """Should return model status"""
        anomaly_detector_instance._device_stats["192.168.1.100"] = sample_device_stats
        anomaly_detector_instance._last_training = datetime.utcnow()
        
        status = anomaly_detector_instance.get_model_status()
        
        assert status.devices_tracked == 1
        assert status.is_trained is True
    
    def test_mark_false_positive(self, anomaly_detector_instance):
        """Should mark false positive"""
        anomaly_detector_instance.mark_false_positive("event-123")
        
        assert anomaly_detector_instance._false_positives == 1
    
    def test_reset_device(self, anomaly_detector_instance, sample_device_stats):
        """Should reset device data"""
        anomaly_detector_instance._device_stats["192.168.1.100"] = sample_device_stats
        
        with patch.object(anomaly_detector_instance, '_save_state'):
            anomaly_detector_instance.reset_device("192.168.1.100")
        
        assert "192.168.1.100" not in anomaly_detector_instance._device_stats
    
    def test_reset_all(self, anomaly_detector_instance, sample_device_stats):
        """Should reset all data"""
        anomaly_detector_instance._device_stats["192.168.1.100"] = sample_device_stats
        anomaly_detector_instance._anomalies_detected = 10
        
        with patch.object(anomaly_detector_instance, '_save_state'):
            anomaly_detector_instance.reset_all()
        
        assert len(anomaly_detector_instance._device_stats) == 0
        assert anomaly_detector_instance._anomalies_detected == 0
    
    def test_save_public(self, anomaly_detector_instance):
        """Should have public save method"""
        with patch.object(anomaly_detector_instance, '_save_state') as mock_save:
            anomaly_detector_instance.save()
        
        mock_save.assert_called_once()

