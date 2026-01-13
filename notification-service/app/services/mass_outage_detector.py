"""
Mass outage detection service.

Detects when multiple devices go offline within a short time window and
aggregates notifications to prevent spam during network-wide outages.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..models import NetworkEvent, NotificationPriority, NotificationType

logger = logging.getLogger(__name__)


@dataclass
class PendingOfflineEvent:
    """A pending offline event waiting to be dispatched or aggregated."""

    device_ip: str
    device_name: str | None
    timestamp: datetime
    original_event: NetworkEvent


@dataclass
class NetworkOutageBuffer:
    """Buffer for pending offline events in a network."""

    pending_events: dict[str, PendingOfflineEvent] = field(default_factory=dict)
    last_cleanup: datetime = field(default_factory=datetime.utcnow)


class MassOutageDetector:
    """
    Detects mass device outages and aggregates notifications.

    When multiple devices go offline within a short time window, this service
    aggregates them into a single "mass outage" notification instead of sending
    individual notifications for each device.
    """

    # Configuration
    AGGREGATION_WINDOW_SECONDS = 60  # Time window to detect mass outage
    MIN_DEVICES_FOR_MASS_OUTAGE = 3  # Minimum devices to trigger aggregation
    CLEANUP_INTERVAL_SECONDS = 30  # How often to clean up expired events

    def __init__(self):
        # Per-network buffers: network_id -> NetworkOutageBuffer
        self._buffers: dict[str, NetworkOutageBuffer] = {}

    def _get_buffer(self, network_id: str) -> NetworkOutageBuffer:
        """Get or create buffer for a network."""
        if network_id not in self._buffers:
            self._buffers[network_id] = NetworkOutageBuffer()
        return self._buffers[network_id]

    def _cleanup_expired_events(self, network_id: str) -> list[NetworkEvent]:
        """
        Remove events older than the aggregation window.

        Returns list of expired events that should be dispatched individually.
        """
        buffer = self._get_buffer(network_id)
        now = datetime.utcnow()

        # Only cleanup periodically to avoid performance overhead
        if (now - buffer.last_cleanup).total_seconds() < self.CLEANUP_INTERVAL_SECONDS:
            return []

        buffer.last_cleanup = now
        cutoff = now - timedelta(seconds=self.AGGREGATION_WINDOW_SECONDS)

        expired_events = []
        expired_ips = []

        for device_ip, pending in buffer.pending_events.items():
            if pending.timestamp < cutoff:
                expired_ips.append(device_ip)
                expired_events.append(pending.original_event)

        for device_ip in expired_ips:
            del buffer.pending_events[device_ip]
            logger.debug(f"[Network {network_id}] Expired pending offline event for {device_ip}")

        return expired_events

    def record_offline_event(
        self,
        network_id: str,
        device_ip: str,
        device_name: str | None,
        event: NetworkEvent,
    ) -> None:
        """
        Record a device offline event for potential aggregation.

        Args:
            network_id: The network this device belongs to
            device_ip: IP address of the offline device
            device_name: Name of the device (optional)
            event: The original NetworkEvent for this device going offline
        """
        buffer = self._get_buffer(network_id)

        # Don't duplicate events for the same device
        if device_ip in buffer.pending_events:
            logger.debug(
                f"[Network {network_id}] Device {device_ip} already has pending offline event"
            )
            return

        pending = PendingOfflineEvent(
            device_ip=device_ip,
            device_name=device_name,
            timestamp=datetime.utcnow(),
            original_event=event,
        )

        buffer.pending_events[device_ip] = pending

        logger.info(
            f"[Network {network_id}] Recorded offline event for {device_ip} "
            f"({len(buffer.pending_events)} devices now pending)"
        )

    def remove_device(self, network_id: str, device_ip: str) -> NetworkEvent | None:
        """
        Remove a device from the pending buffer (e.g., when it comes back online).

        Returns the original event if it was pending, None otherwise.
        """
        buffer = self._get_buffer(network_id)

        if device_ip in buffer.pending_events:
            pending = buffer.pending_events.pop(device_ip)
            logger.info(
                f"[Network {network_id}] Removed {device_ip} from pending offline events "
                f"({len(buffer.pending_events)} remaining)"
            )
            return pending.original_event

        return None

    def should_aggregate(self, network_id: str) -> bool:
        """
        Check if there are enough pending offline events to trigger mass outage aggregation.

        Returns True if the number of pending events >= MIN_DEVICES_FOR_MASS_OUTAGE
        """
        buffer = self._get_buffer(network_id)
        count = len(buffer.pending_events)
        should = count >= self.MIN_DEVICES_FOR_MASS_OUTAGE

        if should:
            logger.info(
                f"[Network {network_id}] Mass outage threshold reached: "
                f"{count} devices offline (threshold: {self.MIN_DEVICES_FOR_MASS_OUTAGE})"
            )

        return should

    def get_pending_count(self, network_id: str) -> int:
        """Get the number of pending offline events for a network."""
        buffer = self._get_buffer(network_id)
        return len(buffer.pending_events)

    def flush_and_create_mass_outage_event(self, network_id: str) -> NetworkEvent | None:
        """
        Create a mass outage event from all pending offline events and clear the buffer.

        Returns a single aggregated NetworkEvent if there are pending events,
        None if the buffer is empty.
        """
        buffer = self._get_buffer(network_id)

        if not buffer.pending_events:
            return None

        # Collect all pending events
        pending_list = list(buffer.pending_events.values())

        # Sort by timestamp
        pending_list.sort(key=lambda p: p.timestamp)

        # Build affected devices list
        affected_devices = []
        for pending in pending_list:
            affected_devices.append(
                {
                    "ip": pending.device_ip,
                    "name": pending.device_name or pending.device_ip,
                    "timestamp": pending.timestamp.isoformat(),
                }
            )

        # Get time range
        first_detected = pending_list[0].timestamp
        last_detected = pending_list[-1].timestamp

        # Build device list for message
        device_names = [p.device_name or p.device_ip for p in pending_list]
        if len(device_names) <= 5:
            device_list_str = ", ".join(device_names)
        else:
            device_list_str = f"{', '.join(device_names[:5])}, and {len(device_names) - 5} more"

        # Create aggregated event
        event = NetworkEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            event_type=NotificationType.MASS_OUTAGE,
            priority=NotificationPriority.HIGH,
            network_id=network_id,
            title="Mass Device Outage Detected",
            message=(
                f"{len(pending_list)} devices went offline within {self.AGGREGATION_WINDOW_SECONDS} seconds. "
                f"This may indicate a network-wide issue.\n\n"
                f"Affected devices: {device_list_str}"
            ),
            details={
                "affected_devices": affected_devices,
                "total_affected": len(pending_list),
                "first_detected": first_detected.isoformat(),
                "last_detected": last_detected.isoformat(),
                "detection_window_seconds": self.AGGREGATION_WINDOW_SECONDS,
            },
        )

        # Clear the buffer
        buffer.pending_events.clear()

        logger.info(
            f"[Network {network_id}] Created mass outage event for {len(affected_devices)} devices"
        )

        return event

    def get_expired_events(self, network_id: str) -> list[NetworkEvent]:
        """
        Get and remove expired events that should be dispatched individually.

        Call this periodically to dispatch individual notifications for devices
        that went offline but didn't reach the mass outage threshold.
        """
        return self._cleanup_expired_events(network_id)

    def get_all_pending_events(self, network_id: str) -> list[NetworkEvent]:
        """
        Get all pending events without removing them.

        Useful for debugging or status checks.
        """
        buffer = self._get_buffer(network_id)
        return [p.original_event for p in buffer.pending_events.values()]

    def flush_all_pending_events(self, network_id: str) -> list[NetworkEvent]:
        """
        Remove and return all pending events for a network.

        Useful when you want to dispatch all pending events individually
        (e.g., when the aggregation window expires without reaching threshold).
        """
        buffer = self._get_buffer(network_id)
        events = [p.original_event for p in buffer.pending_events.values()]
        buffer.pending_events.clear()

        if events:
            logger.info(f"[Network {network_id}] Flushed {len(events)} pending offline events")

        return events


# Singleton instance
mass_outage_detector = MassOutageDetector()
