"""
Unit tests for MassOutageDetector service.
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app.models import NetworkEvent, NotificationPriority, NotificationType
from app.services.mass_outage_detector import (
    MassOutageDetector,
    NetworkEventBuffer,
    PendingDeviceEvent,
)


def create_test_event(
    device_ip: str,
    device_name: str | None = None,
    network_id: str = "test-network-id",
    event_type: NotificationType = NotificationType.DEVICE_OFFLINE,
) -> NetworkEvent:
    """Create a test NetworkEvent for a device state change."""
    if event_type == NotificationType.DEVICE_OFFLINE:
        title = f"Device Offline: {device_name or device_ip}"
        message = f"The device at {device_ip} is no longer responding."
        priority = NotificationPriority.HIGH
    else:
        title = f"Device Online: {device_name or device_ip}"
        message = f"The device at {device_ip} is now responding."
        priority = NotificationPriority.LOW

    return NetworkEvent(
        event_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow(),
        event_type=event_type,
        priority=priority,
        network_id=network_id,
        device_ip=device_ip,
        device_name=device_name,
        title=title,
        message=message,
    )


def create_online_event(
    device_ip: str,
    device_name: str | None = None,
    network_id: str = "test-network-id",
) -> NetworkEvent:
    """Create a test NetworkEvent for a device coming online."""
    return create_test_event(device_ip, device_name, network_id, NotificationType.DEVICE_ONLINE)


class TestMassOutageDetector:
    """Tests for MassOutageDetector class"""

    def test_record_offline_event(self):
        """Should record an offline event for a device."""
        detector = MassOutageDetector()
        network_id = "network-1"
        device_ip = "192.168.1.1"
        event = create_test_event(device_ip, "Router", network_id)

        detector.record_offline_event(network_id, device_ip, "Router", event)

        assert detector.get_pending_count(network_id) == 1
        pending = detector.get_all_pending_events(network_id)
        assert len(pending) == 1
        assert pending[0].device_ip == device_ip

    def test_record_offline_event_no_duplicate(self):
        """Should not duplicate events for the same device."""
        detector = MassOutageDetector()
        network_id = "network-1"
        device_ip = "192.168.1.1"
        event1 = create_test_event(device_ip, "Router", network_id)
        event2 = create_test_event(device_ip, "Router", network_id)

        detector.record_offline_event(network_id, device_ip, "Router", event1)
        detector.record_offline_event(network_id, device_ip, "Router", event2)

        assert detector.get_pending_count(network_id) == 1

    def test_should_aggregate_below_threshold(self):
        """Should not aggregate when below threshold."""
        detector = MassOutageDetector()
        network_id = "network-1"

        # Add 2 devices (below threshold of 3)
        for i in range(2):
            ip = f"192.168.1.{i+1}"
            event = create_test_event(ip, f"Device{i+1}", network_id)
            detector.record_offline_event(network_id, ip, f"Device{i+1}", event)

        assert detector.should_aggregate(network_id) is False

    def test_should_aggregate_at_threshold(self):
        """Should aggregate when at or above threshold."""
        detector = MassOutageDetector()
        network_id = "network-1"

        # Add 3 devices (at threshold)
        for i in range(3):
            ip = f"192.168.1.{i+1}"
            event = create_test_event(ip, f"Device{i+1}", network_id)
            detector.record_offline_event(network_id, ip, f"Device{i+1}", event)

        assert detector.should_aggregate(network_id) is True

    def test_should_aggregate_above_threshold(self):
        """Should aggregate when above threshold."""
        detector = MassOutageDetector()
        network_id = "network-1"

        # Add 5 devices (above threshold)
        for i in range(5):
            ip = f"192.168.1.{i+1}"
            event = create_test_event(ip, f"Device{i+1}", network_id)
            detector.record_offline_event(network_id, ip, f"Device{i+1}", event)

        assert detector.should_aggregate(network_id) is True

    def test_flush_and_create_mass_outage_event(self):
        """Should create aggregated mass outage event."""
        detector = MassOutageDetector()
        network_id = "network-1"

        # Add 5 devices
        device_names = ["Router", "Switch", "Server1", "Server2", "NAS"]
        for i, name in enumerate(device_names):
            ip = f"192.168.1.{i+1}"
            event = create_test_event(ip, name, network_id)
            detector.record_offline_event(network_id, ip, name, event)

        # Create mass outage event
        mass_event = detector.flush_and_create_mass_outage_event(network_id)

        assert mass_event is not None
        assert mass_event.event_type == NotificationType.MASS_OUTAGE
        assert mass_event.priority == NotificationPriority.HIGH
        assert mass_event.network_id == network_id
        assert "Mass Device Outage" in mass_event.title
        assert "5 devices" in mass_event.message
        assert mass_event.details["total_affected"] == 5
        assert len(mass_event.details["affected_devices"]) == 5

        # Buffer should be cleared
        assert detector.get_pending_count(network_id) == 0

    def test_flush_empty_buffer(self):
        """Should return None for empty buffer."""
        detector = MassOutageDetector()
        network_id = "network-1"

        mass_event = detector.flush_and_create_mass_outage_event(network_id)

        assert mass_event is None

    def test_remove_device(self):
        """Should remove device from pending events."""
        detector = MassOutageDetector()
        network_id = "network-1"
        device_ip = "192.168.1.1"
        event = create_test_event(device_ip, "Router", network_id)

        detector.record_offline_event(network_id, device_ip, "Router", event)
        assert detector.get_pending_count(network_id) == 1

        removed = detector.remove_device(network_id, device_ip)

        assert removed is not None
        assert removed.device_ip == device_ip
        assert detector.get_pending_count(network_id) == 0

    def test_remove_nonexistent_device(self):
        """Should return None when removing nonexistent device."""
        detector = MassOutageDetector()
        network_id = "network-1"

        removed = detector.remove_device(network_id, "192.168.1.99")

        assert removed is None

    def test_network_isolation(self):
        """Should isolate events by network."""
        detector = MassOutageDetector()
        network_1 = "network-1"
        network_2 = "network-2"

        # Add 3 devices to network 1
        for i in range(3):
            ip = f"192.168.1.{i+1}"
            event = create_test_event(ip, f"Device{i+1}", network_1)
            detector.record_offline_event(network_1, ip, f"Device{i+1}", event)

        # Add 1 device to network 2
        event = create_test_event("10.0.0.1", "Server", network_2)
        detector.record_offline_event(network_2, "10.0.0.1", "Server", event)

        assert detector.get_pending_count(network_1) == 3
        assert detector.get_pending_count(network_2) == 1
        assert detector.should_aggregate(network_1) is True
        assert detector.should_aggregate(network_2) is False

    def test_flush_all_pending_events(self):
        """Should return all pending events and clear buffer."""
        detector = MassOutageDetector()
        network_id = "network-1"

        # Add 2 devices (below threshold)
        for i in range(2):
            ip = f"192.168.1.{i+1}"
            event = create_test_event(ip, f"Device{i+1}", network_id)
            detector.record_offline_event(network_id, ip, f"Device{i+1}", event)

        events = detector.flush_all_pending_events(network_id)

        assert len(events) == 2
        assert detector.get_pending_count(network_id) == 0

    def test_mass_outage_event_device_list_formatting(self):
        """Should format device list correctly in message."""
        detector = MassOutageDetector()
        network_id = "network-1"

        # Add 3 devices
        device_names = ["Router", "Switch", "Server"]
        for i, name in enumerate(device_names):
            ip = f"192.168.1.{i+1}"
            event = create_test_event(ip, name, network_id)
            detector.record_offline_event(network_id, ip, name, event)

        mass_event = detector.flush_and_create_mass_outage_event(network_id)

        # All 3 names should be listed
        assert "Router" in mass_event.message
        assert "Switch" in mass_event.message
        assert "Server" in mass_event.message

    def test_mass_outage_event_truncates_long_list(self):
        """Should truncate device list if more than 5 devices."""
        detector = MassOutageDetector()
        network_id = "network-1"

        # Add 10 devices
        for i in range(10):
            ip = f"192.168.1.{i+1}"
            name = f"Device{i+1}"
            event = create_test_event(ip, name, network_id)
            detector.record_offline_event(network_id, ip, name, event)

        mass_event = detector.flush_and_create_mass_outage_event(network_id)

        # Should show first 5 and "and X more"
        assert "Device1" in mass_event.message
        assert "Device5" in mass_event.message
        assert "and 5 more" in mass_event.message
        # Device10 should not be in message (truncated)
        assert "Device10" not in mass_event.message

    def test_affected_devices_details(self):
        """Should include all device details in the event as 'Name | IP' strings."""
        detector = MassOutageDetector()
        network_id = "network-1"

        # Add devices
        devices = [
            ("192.168.1.1", "Router"),
            ("192.168.1.2", "Switch"),
            ("192.168.1.3", None),  # No name
        ]
        for ip, name in devices:
            event = create_test_event(ip, name, network_id)
            detector.record_offline_event(network_id, ip, name, event)

        mass_event = detector.flush_and_create_mass_outage_event(network_id)
        affected = mass_event.details["affected_devices"]

        assert len(affected) == 3
        # Check format is "Name | IP" strings
        assert "Router | 192.168.1.1" in affected
        assert "Switch | 192.168.1.2" in affected
        assert "192.168.1.3 | 192.168.1.3" in affected  # Falls back to IP when no name


class TestPendingDeviceEvent:
    """Tests for PendingDeviceEvent dataclass"""

    def test_creation(self):
        """Should create pending event correctly."""
        event = create_test_event("192.168.1.1", "Router")
        pending = PendingDeviceEvent(
            device_ip="192.168.1.1",
            device_name="Router",
            timestamp=datetime.utcnow(),
            original_event=event,
        )

        assert pending.device_ip == "192.168.1.1"
        assert pending.device_name == "Router"
        assert pending.original_event is event


class TestNetworkEventBuffer:
    """Tests for NetworkEventBuffer dataclass"""

    def test_default_creation(self):
        """Should create buffer with empty events."""
        buffer = NetworkEventBuffer()

        assert len(buffer.pending_events) == 0


class TestMassOutageDetectorExpiry:
    """Tests for event expiry in MassOutageDetector"""

    def test_get_expired_events_cleans_old(self):
        """Should return and remove expired events."""
        detector = MassOutageDetector()
        network_id = "network-1"

        # Add an event
        ip = "192.168.1.1"
        event = create_test_event(ip, "Router", network_id)
        detector.record_offline_event(network_id, ip, "Router", event)

        # Manually set the timestamp to be old (past aggregation window)
        buffer = detector._get_offline_buffer(network_id)
        buffer.pending_events[ip].timestamp = datetime.utcnow() - timedelta(
            seconds=detector.OFFLINE_COLLECTION_WINDOW_SECONDS + 10
        )

        expired = detector.get_expired_events(network_id)

        assert len(expired) == 1
        assert expired[0].device_ip == ip
        assert detector.get_pending_count(network_id) == 0

    def test_get_expired_events_keeps_recent(self):
        """Should not expire recent events."""
        detector = MassOutageDetector()
        network_id = "network-1"

        # Add a recent event
        ip = "192.168.1.1"
        event = create_test_event(ip, "Router", network_id)
        detector.record_offline_event(network_id, ip, "Router", event)

        expired = detector.get_expired_events(network_id)

        assert len(expired) == 0
        assert detector.get_pending_count(network_id) == 1


class TestMassOutageIntegration:
    """Integration tests for mass outage detection flow"""

    def test_gradual_failures_not_aggregated(self):
        """Devices failing slowly should not trigger mass outage."""
        detector = MassOutageDetector()
        network_id = "network-1"

        # Add first device
        event1 = create_test_event("192.168.1.1", "Device1", network_id)
        detector.record_offline_event(network_id, "192.168.1.1", "Device1", event1)

        # Manually age the event past the window
        buffer = detector._get_offline_buffer(network_id)
        buffer.pending_events["192.168.1.1"].timestamp = datetime.utcnow() - timedelta(
            seconds=detector.OFFLINE_COLLECTION_WINDOW_SECONDS + 10
        )

        # Add second device (now only 1 device in window)
        event2 = create_test_event("192.168.1.2", "Device2", network_id)
        detector.record_offline_event(network_id, "192.168.1.2", "Device2", event2)

        # Clean up expired events - the old one should be removed
        detector.get_expired_events(network_id)

        # After cleanup, only recent device remains
        assert detector.get_pending_count(network_id) == 1
        assert detector.should_aggregate(network_id) is False

    def test_recovery_during_aggregation(self):
        """Device recovering should be removed from pending."""
        detector = MassOutageDetector()
        network_id = "network-1"

        # Add 3 devices
        for i in range(3):
            ip = f"192.168.1.{i+1}"
            event = create_test_event(ip, f"Device{i+1}", network_id)
            detector.record_offline_event(network_id, ip, f"Device{i+1}", event)

        # Device 2 comes back online
        detector.remove_device(network_id, "192.168.1.2")

        # Now only 2 devices pending - below threshold
        assert detector.get_pending_count(network_id) == 2
        assert detector.should_aggregate(network_id) is False


class TestMassRecoveryDetector:
    """Tests for mass recovery (online) detection"""

    def test_record_online_event(self):
        """Should record an online event for a device."""
        detector = MassOutageDetector()
        network_id = "network-1"
        device_ip = "192.168.1.1"
        event = create_online_event(device_ip, "Router", network_id)

        detector.record_online_event(network_id, device_ip, "Router", event)

        assert detector.get_pending_online_count(network_id) == 1

    def test_record_online_event_no_duplicate(self):
        """Should not duplicate events for the same device."""
        detector = MassOutageDetector()
        network_id = "network-1"
        device_ip = "192.168.1.1"
        event1 = create_online_event(device_ip, "Router", network_id)
        event2 = create_online_event(device_ip, "Router", network_id)

        detector.record_online_event(network_id, device_ip, "Router", event1)
        detector.record_online_event(network_id, device_ip, "Router", event2)

        assert detector.get_pending_online_count(network_id) == 1

    def test_should_aggregate_online_below_threshold(self):
        """Should not aggregate online events when below threshold."""
        detector = MassOutageDetector()
        network_id = "network-1"

        # Add 2 devices (below threshold of 3)
        for i in range(2):
            ip = f"192.168.1.{i+1}"
            event = create_online_event(ip, f"Device{i+1}", network_id)
            detector.record_online_event(network_id, ip, f"Device{i+1}", event)

        assert detector.should_aggregate_online(network_id) is False

    def test_should_aggregate_online_at_threshold(self):
        """Should aggregate online events when at or above threshold."""
        detector = MassOutageDetector()
        network_id = "network-1"

        # Add 3 devices (at threshold)
        for i in range(3):
            ip = f"192.168.1.{i+1}"
            event = create_online_event(ip, f"Device{i+1}", network_id)
            detector.record_online_event(network_id, ip, f"Device{i+1}", event)

        assert detector.should_aggregate_online(network_id) is True

    def test_flush_and_create_mass_recovery_event(self):
        """Should create aggregated mass recovery event."""
        detector = MassOutageDetector()
        network_id = "network-1"

        # Add 5 devices
        device_names = ["Router", "Switch", "Server1", "Server2", "NAS"]
        for i, name in enumerate(device_names):
            ip = f"192.168.1.{i+1}"
            event = create_online_event(ip, name, network_id)
            detector.record_online_event(network_id, ip, name, event)

        # Create mass recovery event
        mass_event = detector.flush_and_create_mass_recovery_event(network_id)

        assert mass_event is not None
        assert mass_event.event_type == NotificationType.MASS_RECOVERY
        assert mass_event.priority == NotificationPriority.LOW
        assert mass_event.network_id == network_id
        assert "Mass Device Recovery" in mass_event.title
        assert "5 devices" in mass_event.message
        assert mass_event.details["total_recovered"] == 5
        assert len(mass_event.details["recovered_devices"]) == 5

        # Buffer should be cleared
        assert detector.get_pending_online_count(network_id) == 0

    def test_flush_empty_online_buffer(self):
        """Should return None for empty online buffer."""
        detector = MassOutageDetector()
        network_id = "network-1"

        mass_event = detector.flush_and_create_mass_recovery_event(network_id)

        assert mass_event is None

    def test_remove_online_device(self):
        """Should remove device from pending online events."""
        detector = MassOutageDetector()
        network_id = "network-1"
        device_ip = "192.168.1.1"
        event = create_online_event(device_ip, "Router", network_id)

        detector.record_online_event(network_id, device_ip, "Router", event)
        assert detector.get_pending_online_count(network_id) == 1

        removed = detector.remove_online_device(network_id, device_ip)

        assert removed is not None
        assert removed.device_ip == device_ip
        assert detector.get_pending_online_count(network_id) == 0

    def test_get_expired_online_events(self):
        """Should return and remove expired online events."""
        detector = MassOutageDetector()
        network_id = "network-1"

        # Add an event
        ip = "192.168.1.1"
        event = create_online_event(ip, "Router", network_id)
        detector.record_online_event(network_id, ip, "Router", event)

        # Manually set the timestamp to be old (past online aggregation window)
        buffer = detector._get_online_buffer(network_id)
        buffer.pending_events[ip].timestamp = datetime.utcnow() - timedelta(
            seconds=detector.ONLINE_COLLECTION_WINDOW_SECONDS + 10
        )

        expired = detector.get_expired_online_events(network_id)

        assert len(expired) == 1
        assert expired[0].device_ip == ip
        assert detector.get_pending_online_count(network_id) == 0

    def test_online_offline_buffers_independent(self):
        """Online and offline buffers should be independent."""
        detector = MassOutageDetector()
        network_id = "network-1"

        # Add offline events
        for i in range(3):
            ip = f"192.168.1.{i+1}"
            event = create_test_event(ip, f"Device{i+1}", network_id)
            detector.record_offline_event(network_id, ip, f"Device{i+1}", event)

        # Add online events
        for i in range(2):
            ip = f"10.0.0.{i+1}"
            event = create_online_event(ip, f"Server{i+1}", network_id)
            detector.record_online_event(network_id, ip, f"Server{i+1}", event)

        assert detector.get_pending_count(network_id) == 3
        assert detector.get_pending_online_count(network_id) == 2
        assert detector.should_aggregate(network_id) is True
        assert detector.should_aggregate_online(network_id) is False
