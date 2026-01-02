"""
Per-network isolated anomaly detector manager.
Each network has its own ML model and device statistics.
"""

import json
import logging
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path

from ..config import settings
from ..models import (
    DeviceBaseline,
    MLModelStatus,
    NetworkEvent,
    NotificationPriority,
    NotificationType,
)
from .anomaly_detector import (
    LATENCY_ZSCORE_THRESHOLD,
    MIN_SAMPLES_FOR_BASELINE,
    PACKET_LOSS_THRESHOLD,
    UNEXPECTED_OFFLINE_THRESHOLD,
    AnomalyDetectionResult,
    AnomalyType,
    DeviceStats,
)

logger = logging.getLogger(__name__)

# Persistence
NETWORK_ANOMALY_DIR = settings.data_dir / "network_anomaly_detectors"


class NetworkAnomalyDetector:
    """
    Isolated anomaly detector for a specific network.
    Each network has completely separate ML models and device statistics.
    """

    MODEL_VERSION = "1.0.0"

    def __init__(self, network_id: str, load_state: bool = True):
        self.network_id = network_id
        # Key device stats by device_ip (scoped to this network)
        self._device_stats: dict[str, DeviceStats] = {}
        self._anomalies_detected: int = 0
        self._false_positives: int = 0
        self._last_training: datetime | None = None
        self._notified_offline: set = set()  # device_ips
        self._anomaly_timestamps: deque = deque(maxlen=10000)
        self._current_devices: set = set()  # device_ips

        # Load persisted state if requested
        if load_state:
            self._load_state()

    def _get_state_file(self) -> Path:
        """Get the state file path for this network"""
        return NETWORK_ANOMALY_DIR / f"network_{self.network_id}.json"

    def _save_state(self):
        """Save detector state to disk"""
        try:
            NETWORK_ANOMALY_DIR.mkdir(parents=True, exist_ok=True)

            state = {
                "version": self.MODEL_VERSION,
                "network_id": self.network_id,
                "devices": {ip: stats.to_dict() for ip, stats in self._device_stats.items()},
                "anomalies_detected": self._anomalies_detected,
                "false_positives": self._false_positives,
                "last_training": self._last_training.isoformat() if self._last_training else None,
                "notified_offline": list(self._notified_offline),
                "anomaly_timestamps": [ts.isoformat() for ts in self._anomaly_timestamps],
                "current_devices": list(self._current_devices),
            }

            with open(self._get_state_file(), "w") as f:
                json.dump(state, f, indent=2)

            logger.debug(
                f"Saved anomaly detector state for network {self.network_id} with {len(self._device_stats)} devices"
            )
        except Exception as e:
            logger.error(
                f"Failed to save anomaly detector state for network {self.network_id}: {e}"
            )

    def _load_state(self):
        """Load detector state from disk"""
        try:
            state_file = self._get_state_file()
            if not state_file.exists():
                logger.debug(f"No existing anomaly detector state for network {self.network_id}")
                return

            with open(state_file, "r") as f:
                state = json.load(f)

            # Check version compatibility
            if state.get("version") != self.MODEL_VERSION:
                logger.warning(
                    f"Model version mismatch for network {self.network_id}, starting fresh"
                )
                return

            self._device_stats = {
                ip: DeviceStats.from_dict(data) for ip, data in state.get("devices", {}).items()
            }
            self._anomalies_detected = state.get("anomalies_detected", 0)
            self._false_positives = state.get("false_positives", 0)
            self._last_training = (
                datetime.fromisoformat(state["last_training"])
                if state.get("last_training")
                else None
            )
            self._notified_offline = set(state.get("notified_offline", []))
            self._current_devices = set(state.get("current_devices", []))

            # Load anomaly timestamps (filter to keep only last 24h on load)
            cutoff = datetime.utcnow() - timedelta(days=1)
            self._anomaly_timestamps = deque(
                (
                    datetime.fromisoformat(ts)
                    for ts in state.get("anomaly_timestamps", [])
                    if datetime.fromisoformat(ts) > cutoff
                ),
                maxlen=10000,
            )

            logger.info(
                f"Loaded anomaly detector state for network {self.network_id}: "
                f"{len(self._device_stats)} devices, {len(self._anomaly_timestamps)} anomalies in 24h, "
                f"{len(self._notified_offline)} pending online notifications"
            )
        except Exception as e:
            logger.error(
                f"Failed to load anomaly detector state for network {self.network_id}: {e}"
            )

    def save(self):
        """Public method to save state - call on shutdown"""
        self._save_state()
        logger.info(f"Saved anomaly detector for network {self.network_id}")

    def train(
        self,
        device_ip: str,
        success: bool,
        latency_ms: float | None = None,
        packet_loss: float | None = None,
        device_name: str | None = None,
        check_time: datetime | None = None,
    ):
        """Train the model with a new data point for this network"""
        if check_time is None:
            check_time = datetime.utcnow()

        if device_ip not in self._device_stats:
            self._device_stats[device_ip] = DeviceStats(
                device_ip=device_ip,
                device_name=device_name,
            )

        stats = self._device_stats[device_ip]
        if device_name:
            stats.device_name = device_name

        stats.update_check(success, latency_ms, packet_loss, check_time)
        self._last_training = check_time
        self._current_devices.add(device_ip)

        # Periodically save state (every 10 updates for new devices, 50 for established)
        save_interval = 10 if stats.total_checks < 100 else 50
        if stats.total_checks % save_interval == 0:
            self._save_state()

    def detect_anomaly(
        self,
        device_ip: str,
        success: bool,
        latency_ms: float | None = None,
        packet_loss: float | None = None,
        check_time: datetime | None = None,
    ) -> AnomalyDetectionResult:
        """Detect anomalies for a device in this network"""

        if check_time is None:
            check_time = datetime.utcnow()

        stats = self._device_stats.get(device_ip)

        if not stats or stats.total_checks < MIN_SAMPLES_FOR_BASELINE:
            return AnomalyDetectionResult(
                is_anomaly=False,
                anomaly_score=0.0,
                reason="Insufficient data for anomaly detection",
                confidence=0.0,
            )

        # Check for stable offline device
        if not success and stats.is_stable_offline():
            return AnomalyDetectionResult(
                is_anomaly=False,
                anomaly_score=0.0,
                reason="Device is in stable offline state (learned baseline behavior)",
                confidence=min(stats.total_checks / 100.0, 1.0),
            )

        contributing_factors = []
        max_anomaly_score = 0.0
        detected_type = None

        # Check for unexpected offline
        if not success:
            expected_state, confidence = stats.get_expected_state_for_time(check_time)

            if (
                expected_state == "online"
                and stats.availability >= UNEXPECTED_OFFLINE_THRESHOLD * 100
            ):
                score = min(stats.availability / 100.0, 0.95)

                if stats.consecutive_failures > 1:
                    score = min(score + (stats.consecutive_failures * 0.1), 0.99)

                if score > max_anomaly_score:
                    max_anomaly_score = score
                    detected_type = AnomalyType.UNEXPECTED_OFFLINE

                contributing_factors.append(
                    f"Device typically has {stats.availability:.1f}% availability but is now offline"
                )

        # Check for latency anomaly
        if latency_ms is not None and stats.latency_stats.count >= MIN_SAMPLES_FOR_BASELINE:
            mean = stats.latency_stats.mean
            std_dev = stats.latency_stats.std_dev

            if std_dev > 0:
                z_score = abs(latency_ms - mean) / std_dev

                if z_score > LATENCY_ZSCORE_THRESHOLD:
                    score = min(z_score / 10.0, 0.9)

                    if score > max_anomaly_score:
                        max_anomaly_score = score
                        detected_type = AnomalyType.UNUSUAL_LATENCY_SPIKE

                    contributing_factors.append(
                        f"Latency {latency_ms:.1f}ms is {z_score:.1f} std devs from normal ({mean:.1f}ms)"
                    )

        # Check for packet loss anomaly
        if packet_loss is not None and packet_loss > PACKET_LOSS_THRESHOLD:
            normal_loss = stats.packet_loss_stats.mean if stats.packet_loss_stats.count > 0 else 0

            if packet_loss > normal_loss * 2 or packet_loss > 0.2:
                score = min(packet_loss * 2, 0.8)

                if score > max_anomaly_score:
                    max_anomaly_score = score
                    detected_type = AnomalyType.UNUSUAL_PACKET_LOSS

                contributing_factors.append(
                    f"Packet loss {packet_loss*100:.1f}% is higher than normal ({normal_loss*100:.1f}%)"
                )

        # Check for time-based anomaly
        hour_avail = stats.get_hourly_availability(check_time.hour)
        if hour_avail is not None and stats.total_checks >= 30:  # Lowered from 50
            if not success and hour_avail > 80:  # Lowered from 95
                score = min(hour_avail / 100.0, 0.7)

                if score > max_anomaly_score:
                    max_anomaly_score = score
                    detected_type = AnomalyType.TIME_BASED_ANOMALY

                contributing_factors.append(
                    f"Device is {hour_avail:.1f}% available at this hour but is currently offline"
                )

        # Lowered threshold from 0.5 to 0.3 for more sensitive detection
        is_anomaly = max_anomaly_score >= 0.3

        if is_anomaly:
            self._anomalies_detected += 1
            self._anomaly_timestamps.append(datetime.utcnow())
            logger.info(
                f"[Network {self.network_id}] Anomaly detected for {device_ip}: "
                f"type={detected_type}, score={max_anomaly_score:.2f}, factors={contributing_factors}"
            )
            # Save state when anomaly is detected (important event)
            self._save_state()

        confidence = min(stats.total_checks / 100.0, 1.0)

        if detected_type:
            reason = f"Detected {detected_type.value.replace('_', ' ')}"
        elif contributing_factors:
            reason = "Multiple factors indicate potential issue"
        else:
            reason = "No anomaly detected"

        return AnomalyDetectionResult(
            is_anomaly=is_anomaly,
            anomaly_score=max_anomaly_score,
            anomaly_type=detected_type,
            reason=reason,
            contributing_factors=contributing_factors,
            expected_value=(
                stats.latency_stats.mean
                if detected_type == AnomalyType.UNUSUAL_LATENCY_SPIKE
                else None
            ),
            actual_value=latency_ms if detected_type == AnomalyType.UNUSUAL_LATENCY_SPIKE else None,
            confidence=confidence,
        )

    def create_network_event(
        self,
        device_ip: str,
        success: bool,
        latency_ms: float | None = None,
        packet_loss: float | None = None,
        device_name: str | None = None,
        previous_state: str | None = None,
    ) -> NetworkEvent | None:
        """
        Create a network event if notification-worthy.

        Uses ML-based anomaly detection combined with state tracking to determine
        when to send notifications.
        """
        check_time = datetime.utcnow()

        # Train first
        self.train(device_ip, success, latency_ms, packet_loss, device_name, check_time)

        # Detect anomalies
        result = self.detect_anomaly(device_ip, success, latency_ms, packet_loss, check_time)

        stats = self._device_stats.get(device_ip)
        current_state = "online" if success else "offline"

        should_notify = False
        event_type = NotificationType.DEVICE_OFFLINE
        priority = NotificationPriority.MEDIUM
        title = ""
        message = ""

        # Determine effective previous state if not provided
        effective_previous_state = previous_state
        if effective_previous_state is None and stats:
            # Infer previous state from consecutive counters
            # Stats were just updated by train(), so we need to check:
            # - If consecutive_successes > 1 (multiple successes), device was online
            # - If consecutive_failures > 1 (multiple failures), device was offline
            # - For first transition, check history
            if stats.consecutive_successes > 1:
                effective_previous_state = "online"
            elif stats.consecutive_failures > 1:
                effective_previous_state = "offline"
            elif stats.consecutive_successes == 1 and stats.failed_checks >= 3:
                # First success after failures - recovery
                if not stats.is_stable_offline():
                    effective_previous_state = "offline"
            elif stats.consecutive_failures == 1 and stats.successful_checks >= 3:
                # First failure after successes - outage
                if not stats.is_stable_online():
                    effective_previous_state = "online"

        # Check for stable offline device (don't notify if this is normal behavior)
        is_stable_offline_device = stats and stats.is_stable_offline()

        # Determine if this is a genuine state transition
        state_changed = effective_previous_state and effective_previous_state != current_state

        # Check for genuine offline transition (first failure after being online)
        just_went_offline = (
            not success
            and stats
            and stats.consecutive_failures == 1
            and stats.successful_checks >= 3
            and not stats.is_stable_online()  # Stable online devices with occasional failures shouldn't alert
        )

        if not success:
            # Device is offline
            if device_ip in self._notified_offline:
                # Already sent an offline notification for this device - don't send another
                logger.debug(
                    f"[Network {self.network_id}] Skipping duplicate offline notification for {device_ip} "
                    f"(already notified)"
                )
                should_notify = False
            elif is_stable_offline_device:
                # This device is normally offline - don't notify
                logger.debug(
                    f"[Network {self.network_id}] Skipping notification for stable offline device {device_ip} "
                    f"(availability: {stats.availability:.1f}%)"
                )
                should_notify = False
            elif (
                state_changed
                or just_went_offline
                or effective_previous_state == "online"
                or result.is_anomaly
            ):
                # Device just went offline - send notification
                should_notify = True
                event_type = NotificationType.DEVICE_OFFLINE
                priority = (
                    NotificationPriority.HIGH if result.is_anomaly else NotificationPriority.MEDIUM
                )

                if result.is_anomaly:
                    title = f"Device Offline: {device_name or device_ip} (Unexpected)"
                    message = (
                        f"The device at {device_ip} has gone offline unexpectedly. {result.reason}"
                    )
                else:
                    title = f"Device Offline: {device_name or device_ip}"
                    message = f"The device at {device_ip} is no longer responding."

                # Track that we sent an offline notification - prevents duplicate notifications
                self._notified_offline.add(device_ip)
                # Save state immediately to persist offline tracking across restarts
                self._save_state()

                logger.info(
                    f"[Network {self.network_id}] Device {device_ip} went offline - creating notification "
                    f"(is_anomaly={result.is_anomaly}, score={result.anomaly_score:.2f})"
                )

                # Add context for multiple failures
                if stats and stats.consecutive_failures >= 3:
                    priority = NotificationPriority.HIGH
                    message += f" ({stats.consecutive_failures} consecutive failures)"

        elif success:
            # Device is online
            # Only send "back online" notification if we previously sent an offline notification
            # This ensures we don't spam users with online notifications for devices that were
            # never reported as offline
            if device_ip in self._notified_offline:
                # We sent an offline notification - now send the recovery notification
                should_notify = True
                event_type = NotificationType.DEVICE_ONLINE
                priority = NotificationPriority.LOW
                title = f"Device Online: {device_name or device_ip}"
                message = f"The device at {device_ip} is now responding."

                # Remove from tracking
                self._notified_offline.discard(device_ip)
                # Save state immediately to persist tracking changes across restarts
                self._save_state()

                logger.info(
                    f"[Network {self.network_id}] Device {device_ip} came back online - creating notification"
                )

            # Check for degraded performance (high latency or packet loss)
            if result.is_anomaly:
                if result.anomaly_type == AnomalyType.UNUSUAL_LATENCY_SPIKE:
                    should_notify = True
                    event_type = NotificationType.HIGH_LATENCY
                    priority = NotificationPriority.MEDIUM
                    title = f"High Latency: {device_name or device_ip}"
                    message = f"Unusual latency detected on {device_ip}: {latency_ms:.1f}ms (normally {stats.latency_stats.mean:.1f}ms)"
                    logger.info(
                        f"[Network {self.network_id}] High latency anomaly detected for {device_ip}"
                    )

                elif result.anomaly_type == AnomalyType.UNUSUAL_PACKET_LOSS:
                    should_notify = True
                    event_type = NotificationType.PACKET_LOSS
                    priority = NotificationPriority.MEDIUM
                    title = f"Packet Loss: {device_name or device_ip}"
                    message = f"High packet loss detected on {device_ip}: {packet_loss*100:.1f}%"
                    logger.info(
                        f"[Network {self.network_id}] Packet loss anomaly detected for {device_ip}"
                    )

        if not should_notify:
            logger.debug(
                f"[Network {self.network_id}] No notification for {device_ip}: success={success}, "
                f"effective_previous_state={effective_previous_state}, is_anomaly={result.is_anomaly}"
            )
            return None

        import uuid

        return NetworkEvent(
            event_id=str(uuid.uuid4()),
            timestamp=check_time,
            event_type=event_type,
            priority=priority,
            device_ip=device_ip,
            device_name=device_name,
            title=title,
            message=message,
            previous_state=previous_state,
            current_state=current_state,
            anomaly_score=result.anomaly_score if result.is_anomaly else None,
            is_predicted_anomaly=result.is_anomaly,
            ml_model_version="1.0.0",
            details={
                "latency_ms": latency_ms,
                "packet_loss_percent": packet_loss * 100 if packet_loss else None,
                "contributing_factors": result.contributing_factors,
            },
        )

    def get_device_baseline(self, device_ip: str) -> DeviceBaseline | None:
        """Get the learned baseline for a device in this network"""
        stats = self._device_stats.get(device_ip)
        if not stats:
            return None

        hourly_avail = {}
        for hour, (succ, total) in stats.hourly_patterns.items():
            if total > 0:
                hourly_avail[hour] = (succ / total) * 100

        daily_avail = {}
        for dow, (succ, total) in stats.daily_patterns.items():
            if total > 0:
                daily_avail[dow] = (succ / total) * 100

        return DeviceBaseline(
            device_ip=device_ip,
            device_name=stats.device_name,
            avg_latency_ms=stats.latency_stats.mean if stats.latency_stats.count > 0 else None,
            latency_std_dev=stats.latency_stats.std_dev if stats.latency_stats.count > 1 else None,
            avg_packet_loss=(
                stats.packet_loss_stats.mean if stats.packet_loss_stats.count > 0 else None
            ),
            check_count=stats.total_checks,
            online_count=stats.successful_checks,
            offline_count=stats.failed_checks,
            hourly_availability=hourly_avail,
            daily_availability=daily_avail,
            is_stable_offline=stats.is_stable_offline(),
            is_stable_online=stats.is_stable_online(),
            state_transitions=stats.state_transitions,
            first_seen=stats.first_seen,
            last_updated=stats.last_updated,
            model_version="1.0.0",
            samples_count=stats.total_checks,
        )

    def get_model_status(self) -> MLModelStatus:
        """Get current status of the ML model for this network"""
        cutoff = datetime.utcnow() - timedelta(days=1)
        anomalies_24h = sum(1 for ts in self._anomaly_timestamps if ts > cutoff)

        has_data = len(self._device_stats) > 0 and self._last_training is not None

        return MLModelStatus(
            model_version="1.0.0",
            last_training=self._last_training,
            samples_count=sum(s.total_checks for s in self._device_stats.values()),
            devices_tracked=(
                len(self._current_devices) if self._current_devices else len(self._device_stats)
            ),
            anomalies_detected_total=self._anomalies_detected,
            anomalies_detected_24h=anomalies_24h,
            # Deprecated: kept for backward compatibility
            is_trained=has_data,
            # Model is always online learning once it has data
            is_online_learning=has_data,
            # Status reflects continuous learning nature
            training_status="online_learning" if has_data else "initializing",
        )

    def sync_current_devices(self, device_ips: list):
        """Sync the list of devices currently in this network"""
        self._current_devices = set(device_ips)


class NetworkAnomalyDetectorManager:
    """
    Manages per-network anomaly detectors.
    Each network has an isolated ML model.
    """

    def __init__(self):
        self._detectors: dict[str, NetworkAnomalyDetector] = {}
        # Load existing detectors from disk on startup
        self._load_all()

    def _load_all(self):
        """Load all existing network detectors from disk"""
        try:
            if not NETWORK_ANOMALY_DIR.exists():
                logger.debug("No existing network anomaly detector data directory")
                return

            # Find all network state files
            for state_file in NETWORK_ANOMALY_DIR.glob("network_*.json"):
                try:
                    # Extract network_id from filename
                    filename = state_file.stem  # e.g., "network_<uuid>"
                    network_id = filename.split("_", 1)[1]  # UUID string

                    # Load the detector (it will load its own state)
                    detector = NetworkAnomalyDetector(network_id, load_state=True)
                    self._detectors[network_id] = detector

                    logger.info(f"Loaded anomaly detector for network {network_id}")
                except Exception as e:
                    logger.error(f"Failed to load detector from {state_file}: {e}")

            logger.info(f"Loaded {len(self._detectors)} network anomaly detectors from disk")
        except Exception as e:
            logger.error(f"Failed to load network anomaly detectors: {e}")

    def save_all(self):
        """Save all network detectors to disk"""
        for network_id, detector in self._detectors.items():
            try:
                detector.save()
            except Exception as e:
                logger.error(f"Failed to save detector for network {network_id}: {e}")

        logger.info(f"Saved {len(self._detectors)} network anomaly detectors to disk")

    def get_detector(self, network_id: str) -> NetworkAnomalyDetector:
        """Get or create anomaly detector for a network"""
        if network_id not in self._detectors:
            self._detectors[network_id] = NetworkAnomalyDetector(network_id)
            logger.info(f"Created new anomaly detector for network {network_id}")

        return self._detectors[network_id]

    def get_stats(self, network_id: str) -> MLModelStatus:
        """Get ML model status for a network"""
        detector = self.get_detector(network_id)
        return detector.get_model_status()

    def process_health_check(
        self,
        network_id: str,
        device_ip: str,
        success: bool,
        latency_ms: float | None = None,
        packet_loss: float | None = None,
        device_name: str | None = None,
        previous_state: str | None = None,
    ) -> NetworkEvent | None:
        """Process a health check and return event if notification-worthy"""
        detector = self.get_detector(network_id)
        return detector.create_network_event(
            device_ip=device_ip,
            success=success,
            latency_ms=latency_ms,
            packet_loss=packet_loss,
            device_name=device_name,
            previous_state=previous_state,
        )


# Singleton instance
network_anomaly_detector_manager = NetworkAnomalyDetectorManager()
