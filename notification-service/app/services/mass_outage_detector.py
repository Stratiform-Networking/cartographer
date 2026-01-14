"""
Mass outage and recovery detection service.

Detects when multiple devices go offline or come back online within a short time
window and aggregates notifications to prevent spam during network-wide events.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..models import NetworkEvent, NotificationPriority, NotificationType

logger = logging.getLogger(__name__)


@dataclass
class PendingDeviceEvent:
    """A pending device event waiting to be dispatched or aggregated."""

    device_ip: str
    device_name: str | None
    timestamp: datetime
    original_event: NetworkEvent


@dataclass
class NetworkEventBuffer:
    """Buffer for pending device events in a network."""

    pending_events: dict[str, PendingDeviceEvent] = field(default_factory=dict)
    # Timestamp when threshold was first reached (for grace period before flushing)
    threshold_reached_at: datetime | None = None


class MassOutageDetector:
    """
    Detects mass device outages/recoveries and aggregates notifications.

    When multiple devices go offline or come back online within a short time window,
    this service aggregates them into a single notification instead of sending
    individual notifications for each device.
    """

    # Configuration
    # Collection window: how long to wait for concurrent events before dispatching
    # This should be short - just enough to catch health checks arriving in the same batch
    OFFLINE_COLLECTION_WINDOW_SECONDS = 5  # Wait up to 5s to collect offline events
    ONLINE_COLLECTION_WINDOW_SECONDS = 3  # Shorter window for recovery (users want fast feedback)
    MIN_DEVICES_FOR_MASS_EVENT = 3  # Minimum devices to trigger aggregation
    # Grace period after threshold reached before flushing (catch concurrent arrivals)
    THRESHOLD_GRACE_PERIOD_SECONDS = 1  # 1 second is enough for concurrent requests

    def __init__(self):
        # Per-network buffers for offline events: network_id -> NetworkEventBuffer
        self._offline_buffers: dict[str, NetworkEventBuffer] = {}
        # Per-network buffers for online events: network_id -> NetworkEventBuffer
        self._online_buffers: dict[str, NetworkEventBuffer] = {}

    def _get_offline_buffer(self, network_id: str) -> NetworkEventBuffer:
        """Get or create offline buffer for a network."""
        if network_id not in self._offline_buffers:
            self._offline_buffers[network_id] = NetworkEventBuffer()
        return self._offline_buffers[network_id]

    def _get_online_buffer(self, network_id: str) -> NetworkEventBuffer:
        """Get or create online buffer for a network."""
        if network_id not in self._online_buffers:
            self._online_buffers[network_id] = NetworkEventBuffer()
        return self._online_buffers[network_id]

    def _cleanup_expired_events(
        self, buffer: NetworkEventBuffer, network_id: str, event_type: str, window_seconds: int
    ) -> list[NetworkEvent]:
        """
        Remove events older than the aggregation window from a buffer.

        Returns list of expired events that should be dispatched individually.
        """
        now = datetime.utcnow()

        # Use <= to ensure events at exactly the cutoff time are expired
        cutoff = now - timedelta(seconds=window_seconds)

        expired_events = []
        expired_ips = []

        for device_ip, pending in buffer.pending_events.items():
            if pending.timestamp <= cutoff:
                expired_ips.append(device_ip)
                expired_events.append(pending.original_event)

        for device_ip in expired_ips:
            del buffer.pending_events[device_ip]
            logger.debug(
                f"[Network {network_id}] Expired pending {event_type} event for {device_ip}"
            )

        return expired_events

    # ==================== Offline (Outage) Methods ====================

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
        buffer = self._get_offline_buffer(network_id)

        # Don't duplicate events for the same device
        if device_ip in buffer.pending_events:
            logger.debug(
                f"[Network {network_id}] Device {device_ip} already has pending offline event"
            )
            return

        pending = PendingDeviceEvent(
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

    def remove_offline_device(self, network_id: str, device_ip: str) -> NetworkEvent | None:
        """
        Remove a device from the pending offline buffer.

        Returns the original event if it was pending, None otherwise.
        Also resets threshold tracking if we drop below threshold.
        """
        buffer = self._get_offline_buffer(network_id)

        if device_ip in buffer.pending_events:
            pending = buffer.pending_events.pop(device_ip)
            logger.info(
                f"[Network {network_id}] Removed {device_ip} from pending offline events "
                f"({len(buffer.pending_events)} remaining)"
            )

            # If we drop below threshold, reset threshold tracking
            # Remaining events will be dispatched individually when they expire
            if len(buffer.pending_events) < self.MIN_DEVICES_FOR_MASS_EVENT:
                if buffer.threshold_reached_at is not None:
                    logger.info(
                        f"[Network {network_id}] Dropped below mass outage threshold, "
                        f"remaining {len(buffer.pending_events)} devices will be dispatched individually"
                    )
                    buffer.threshold_reached_at = None

            return pending.original_event

        return None

    # Alias for backwards compatibility
    def remove_device(self, network_id: str, device_ip: str) -> NetworkEvent | None:
        """Alias for remove_offline_device for backwards compatibility."""
        return self.remove_offline_device(network_id, device_ip)

    def should_aggregate(self, network_id: str) -> bool:
        """
        Check if there are enough pending offline events to trigger mass outage aggregation.

        Returns True if the number of pending events >= MIN_DEVICES_FOR_MASS_EVENT.
        Also tracks when threshold was first reached for grace period handling.
        """
        buffer = self._get_offline_buffer(network_id)
        count = len(buffer.pending_events)
        should = count >= self.MIN_DEVICES_FOR_MASS_EVENT

        if should and buffer.threshold_reached_at is None:
            # First time reaching threshold - record timestamp
            buffer.threshold_reached_at = datetime.utcnow()
            logger.info(
                f"[Network {network_id}] Mass outage threshold reached: "
                f"{count} devices offline (threshold: {self.MIN_DEVICES_FOR_MASS_EVENT})"
            )

        return should

    def is_ready_to_flush_offline(self, network_id: str) -> bool:
        """
        Check if the offline buffer is ready to be flushed as a mass event.

        Returns True if threshold was reached AND grace period has passed.
        This allows concurrent arrivals to be captured before flushing.
        """
        buffer = self._get_offline_buffer(network_id)
        if buffer.threshold_reached_at is None:
            return False

        elapsed = (datetime.utcnow() - buffer.threshold_reached_at).total_seconds()
        return elapsed >= self.THRESHOLD_GRACE_PERIOD_SECONDS

    def get_pending_count(self, network_id: str) -> int:
        """Get the number of pending offline events for a network."""
        buffer = self._get_offline_buffer(network_id)
        return len(buffer.pending_events)

    def flush_and_create_mass_outage_event(self, network_id: str) -> NetworkEvent | None:
        """
        Create a mass outage event from all pending offline events and clear the buffer.

        Returns a single aggregated NetworkEvent if there are pending events,
        None if the buffer is empty.
        """
        buffer = self._get_offline_buffer(network_id)

        if not buffer.pending_events:
            return None

        # Collect all pending events
        pending_list = list(buffer.pending_events.values())

        # Sort by timestamp
        pending_list.sort(key=lambda p: p.timestamp)

        # Build affected devices list as "Name | IP" strings
        affected_devices = []
        for pending in pending_list:
            name = pending.device_name or pending.device_ip
            affected_devices.append(f"{name} | {pending.device_ip}")

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
                f"We found {len(pending_list)} devices went offline. "
                f"Check your network configurations and we will notify you when they have been detected again.\n\n"
                f"Affected devices: {device_list_str}"
            ),
            details={
                "affected_devices": affected_devices,
                "total_affected": len(pending_list),
                "first_detected": first_detected.isoformat(),
                "last_detected": last_detected.isoformat(),
                "detection_window_seconds": self.OFFLINE_COLLECTION_WINDOW_SECONDS,
            },
        )

        # Clear the buffer and reset threshold tracking
        buffer.pending_events.clear()
        buffer.threshold_reached_at = None

        logger.info(
            f"[Network {network_id}] Created mass outage event for {len(affected_devices)} devices"
        )

        return event

    def get_expired_events(self, network_id: str) -> list[NetworkEvent]:
        """
        Get and remove expired offline events that should be dispatched individually.

        Call this periodically to dispatch individual notifications for devices
        that went offline but didn't reach the mass outage threshold.
        """
        buffer = self._get_offline_buffer(network_id)
        return self._cleanup_expired_events(
            buffer, network_id, "offline", self.OFFLINE_COLLECTION_WINDOW_SECONDS
        )

    def get_all_pending_events(self, network_id: str) -> list[NetworkEvent]:
        """
        Get all pending offline events without removing them.

        Useful for debugging or status checks.
        """
        buffer = self._get_offline_buffer(network_id)
        return [p.original_event for p in buffer.pending_events.values()]

    def flush_all_pending_events(self, network_id: str) -> list[NetworkEvent]:
        """
        Remove and return all pending offline events for a network.

        Useful when you want to dispatch all pending events individually
        (e.g., when the aggregation window expires without reaching threshold).
        """
        buffer = self._get_offline_buffer(network_id)
        events = [p.original_event for p in buffer.pending_events.values()]
        buffer.pending_events.clear()

        if events:
            logger.info(f"[Network {network_id}] Flushed {len(events)} pending offline events")

        return events

    # ==================== Online (Recovery) Methods ====================

    def record_online_event(
        self,
        network_id: str,
        device_ip: str,
        device_name: str | None,
        event: NetworkEvent,
    ) -> None:
        """
        Record a device online event for potential aggregation.

        Args:
            network_id: The network this device belongs to
            device_ip: IP address of the device coming online
            device_name: Name of the device (optional)
            event: The original NetworkEvent for this device coming online
        """
        buffer = self._get_online_buffer(network_id)

        # Don't duplicate events for the same device
        if device_ip in buffer.pending_events:
            logger.debug(
                f"[Network {network_id}] Device {device_ip} already has pending online event"
            )
            return

        pending = PendingDeviceEvent(
            device_ip=device_ip,
            device_name=device_name,
            timestamp=datetime.utcnow(),
            original_event=event,
        )

        buffer.pending_events[device_ip] = pending

        logger.info(
            f"[Network {network_id}] Recorded online event for {device_ip} "
            f"({len(buffer.pending_events)} devices now pending recovery)"
        )

    def remove_online_device(self, network_id: str, device_ip: str) -> NetworkEvent | None:
        """
        Remove a device from the pending online buffer.

        Returns the original event if it was pending, None otherwise.
        Also resets threshold tracking if we drop below threshold.
        """
        buffer = self._get_online_buffer(network_id)

        if device_ip in buffer.pending_events:
            pending = buffer.pending_events.pop(device_ip)
            logger.info(
                f"[Network {network_id}] Removed {device_ip} from pending online events "
                f"({len(buffer.pending_events)} remaining)"
            )

            # If we drop below threshold, reset threshold tracking
            if len(buffer.pending_events) < self.MIN_DEVICES_FOR_MASS_EVENT:
                if buffer.threshold_reached_at is not None:
                    logger.info(
                        f"[Network {network_id}] Dropped below mass recovery threshold, "
                        f"remaining {len(buffer.pending_events)} devices will be dispatched individually"
                    )
                    buffer.threshold_reached_at = None

            return pending.original_event

        return None

    def should_aggregate_online(self, network_id: str) -> bool:
        """
        Check if there are enough pending online events to trigger mass recovery aggregation.

        Returns True if the number of pending events >= MIN_DEVICES_FOR_MASS_EVENT.
        Also tracks when threshold was first reached for grace period handling.
        """
        buffer = self._get_online_buffer(network_id)
        count = len(buffer.pending_events)
        should = count >= self.MIN_DEVICES_FOR_MASS_EVENT

        if should and buffer.threshold_reached_at is None:
            # First time reaching threshold - record timestamp
            buffer.threshold_reached_at = datetime.utcnow()
            logger.info(
                f"[Network {network_id}] Mass recovery threshold reached: "
                f"{count} devices online (threshold: {self.MIN_DEVICES_FOR_MASS_EVENT})"
            )

        return should

    def is_ready_to_flush_online(self, network_id: str) -> bool:
        """
        Check if the online buffer is ready to be flushed as a mass event.

        Returns True if threshold was reached AND grace period has passed.
        This allows concurrent arrivals to be captured before flushing.
        """
        buffer = self._get_online_buffer(network_id)
        if buffer.threshold_reached_at is None:
            return False

        elapsed = (datetime.utcnow() - buffer.threshold_reached_at).total_seconds()
        return elapsed >= self.THRESHOLD_GRACE_PERIOD_SECONDS

    def get_pending_online_count(self, network_id: str) -> int:
        """Get the number of pending online events for a network."""
        buffer = self._get_online_buffer(network_id)
        return len(buffer.pending_events)

    def flush_and_create_mass_recovery_event(self, network_id: str) -> NetworkEvent | None:
        """
        Create a mass recovery event from all pending online events and clear the buffer.

        Returns a single aggregated NetworkEvent if there are pending events,
        None if the buffer is empty.
        """
        buffer = self._get_online_buffer(network_id)

        if not buffer.pending_events:
            return None

        # Collect all pending events
        pending_list = list(buffer.pending_events.values())

        # Sort by timestamp
        pending_list.sort(key=lambda p: p.timestamp)

        # Build recovered devices list as "Name | IP" strings
        recovered_devices = []
        for pending in pending_list:
            name = pending.device_name or pending.device_ip
            recovered_devices.append(f"{name} | {pending.device_ip}")

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
            event_type=NotificationType.MASS_RECOVERY,
            priority=NotificationPriority.LOW,
            network_id=network_id,
            title="Mass Device Recovery Detected",
            message=(
                f"{len(pending_list)} devices came back online. "
                f"Network connectivity appears to be restored.\n\n"
                f"Recovered devices: {device_list_str}"
            ),
            details={
                "recovered_devices": recovered_devices,
                "total_recovered": len(pending_list),
                "first_detected": first_detected.isoformat(),
                "last_detected": last_detected.isoformat(),
                "detection_window_seconds": self.ONLINE_COLLECTION_WINDOW_SECONDS,
            },
        )

        # Clear the buffer and reset threshold tracking
        buffer.pending_events.clear()
        buffer.threshold_reached_at = None

        logger.info(
            f"[Network {network_id}] Created mass recovery event for {len(recovered_devices)} devices"
        )

        return event

    def get_expired_online_events(self, network_id: str) -> list[NetworkEvent]:
        """
        Get and remove expired online events that should be dispatched individually.

        Call this periodically to dispatch individual notifications for devices
        that came online but didn't reach the mass recovery threshold.
        """
        buffer = self._get_online_buffer(network_id)
        return self._cleanup_expired_events(
            buffer, network_id, "online", self.ONLINE_COLLECTION_WINDOW_SECONDS
        )

    def get_all_pending_online_events(self, network_id: str) -> list[NetworkEvent]:
        """
        Get all pending online events without removing them.

        Useful for debugging or status checks.
        """
        buffer = self._get_online_buffer(network_id)
        return [p.original_event for p in buffer.pending_events.values()]

    def flush_all_pending_online_events(self, network_id: str) -> list[NetworkEvent]:
        """
        Remove and return all pending online events for a network.

        Useful when you want to dispatch all pending events individually
        (e.g., when the aggregation window expires without reaching threshold).
        """
        buffer = self._get_online_buffer(network_id)
        events = [p.original_event for p in buffer.pending_events.values()]
        buffer.pending_events.clear()

        if events:
            logger.info(f"[Network {network_id}] Flushed {len(events)} pending online events")

        return events


# Singleton instance
mass_outage_detector = MassOutageDetector()
