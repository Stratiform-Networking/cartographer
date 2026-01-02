"""
Anomaly detection service using machine learning.

Passively trains on network metrics to detect anomalous behavior patterns.
Uses statistical methods and simple ML techniques suitable for real-time detection.
"""

import json
import logging
import math
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta

from ..config import settings
from ..models import (
    AnomalyDetectionResult,
    AnomalyType,
    DeviceBaseline,
    MLModelStatus,
    NetworkEvent,
    NotificationPriority,
    NotificationType,
)

logger = logging.getLogger(__name__)

# Persistence
BASELINES_FILE = settings.data_dir / "device_baselines.json"
MODEL_STATE_FILE = settings.data_dir / "ml_model_state.json"

# Detection thresholds
LATENCY_ZSCORE_THRESHOLD = 3.0  # Standard deviations from mean
PACKET_LOSS_THRESHOLD = 0.1  # 10% packet loss is concerning
UNEXPECTED_OFFLINE_THRESHOLD = 0.9  # If device is usually online 90%+ of time
MIN_SAMPLES_FOR_BASELINE = 5  # Minimum samples before making predictions
STABLE_STATE_MIN_SAMPLES = 15  # Minimum samples to consider a device in stable state
STABLE_STATE_TRANSITION_RATIO = 0.1  # Max ratio of state transitions to be considered stable
STABLE_OFFLINE_AVAILABILITY_THRESHOLD = (
    20.0  # Below this % availability, device is considered "normally offline"
)
STABLE_ONLINE_AVAILABILITY_THRESHOLD = (
    80.0  # Above this % availability, device is considered "normally online"
)


@dataclass
class LatencyStats:
    """Rolling statistics for latency measurements"""

    count: int = 0
    mean: float = 0.0
    m2: float = 0.0  # For Welford's algorithm
    min_value: float = float("inf")
    max_value: float = 0.0

    def update(self, value: float):
        """Update stats with new value using Welford's online algorithm"""
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        delta2 = value - self.mean
        self.m2 += delta * delta2
        self.min_value = min(self.min_value, value)
        self.max_value = max(self.max_value, value)

    @property
    def variance(self) -> float:
        if self.count < 2:
            return 0.0
        return self.m2 / (self.count - 1)

    @property
    def std_dev(self) -> float:
        return math.sqrt(self.variance) if self.variance > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "count": self.count,
            "mean": self.mean,
            "m2": self.m2,
            "min_value": self.min_value if self.min_value != float("inf") else None,
            "max_value": self.max_value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LatencyStats":
        stats = cls()
        stats.count = data.get("count", 0)
        stats.mean = data.get("mean", 0.0)
        stats.m2 = data.get("m2", 0.0)
        stats.min_value = (
            data.get("min_value") if data.get("min_value") is not None else float("inf")
        )
        stats.max_value = data.get("max_value", 0.0)
        return stats


@dataclass
class DeviceStats:
    """Comprehensive statistics for a device"""

    device_ip: str
    device_name: str | None = None

    # Check statistics
    total_checks: int = 0
    successful_checks: int = 0
    failed_checks: int = 0

    # Latency statistics (using Welford's algorithm for online computation)
    latency_stats: LatencyStats = field(default_factory=LatencyStats)

    # Packet loss statistics
    packet_loss_stats: LatencyStats = field(default_factory=LatencyStats)

    # Time-based patterns (hour -> success rate)
    hourly_patterns: dict[int, tuple[int, int]] = field(
        default_factory=dict
    )  # hour -> (success, total)

    # Day of week patterns
    daily_patterns: dict[int, tuple[int, int]] = field(
        default_factory=dict
    )  # dow -> (success, total)

    # Recent state tracking
    last_state: str | None = None
    last_check_time: datetime | None = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0

    # State transition tracking
    state_transitions: int = 0

    # Timestamps
    first_seen: datetime | None = None
    last_updated: datetime | None = None

    def update_check(
        self,
        success: bool,
        latency_ms: float | None,
        packet_loss: float | None,
        check_time: datetime,
    ):
        """Update statistics with a new health check result"""
        self.total_checks += 1

        if self.first_seen is None:
            self.first_seen = check_time
        self.last_updated = check_time

        # Update success/failure counts
        if success:
            self.successful_checks += 1
            self.consecutive_successes += 1
            self.consecutive_failures = 0
        else:
            self.failed_checks += 1
            self.consecutive_failures += 1
            self.consecutive_successes = 0

        # Update latency stats
        if latency_ms is not None and latency_ms > 0:
            self.latency_stats.update(latency_ms)

        # Update packet loss stats
        if packet_loss is not None:
            self.packet_loss_stats.update(packet_loss)

        # Update time-based patterns
        hour = check_time.hour
        if hour not in self.hourly_patterns:
            self.hourly_patterns[hour] = (0, 0)
        succ, total = self.hourly_patterns[hour]
        self.hourly_patterns[hour] = (succ + (1 if success else 0), total + 1)

        dow = check_time.weekday()
        if dow not in self.daily_patterns:
            self.daily_patterns[dow] = (0, 0)
        succ, total = self.daily_patterns[dow]
        self.daily_patterns[dow] = (succ + (1 if success else 0), total + 1)

        # Track state transitions
        current_state = "online" if success else "offline"
        if self.last_state and self.last_state != current_state:
            self.state_transitions += 1
        self.last_state = current_state
        self.last_check_time = check_time

    @property
    def availability(self) -> float:
        """Overall availability percentage"""
        if self.total_checks == 0:
            return 0.0
        return (self.successful_checks / self.total_checks) * 100

    def get_hourly_availability(self, hour: int) -> float | None:
        """Get availability for a specific hour"""
        if hour not in self.hourly_patterns:
            return None
        succ, total = self.hourly_patterns[hour]
        if total == 0:
            return None
        return (succ / total) * 100

    def get_expected_state_for_time(self, dt: datetime) -> tuple[str, float]:
        """Predict expected state for a given time based on patterns"""
        hour = dt.hour
        hour_avail = self.get_hourly_availability(hour)

        if hour_avail is None:
            # Fall back to overall availability
            return ("online" if self.availability >= 50 else "offline", 0.5)

        confidence = min(self.hourly_patterns.get(hour, (0, 0))[1] / 10.0, 1.0)
        expected = "online" if hour_avail >= 50 else "offline"

        return (expected, confidence)

    def is_stable_state(
        self,
        min_samples: int = STABLE_STATE_MIN_SAMPLES,
        transition_ratio: float = STABLE_STATE_TRANSITION_RATIO,
    ) -> bool:
        """
        Check if the device is in a stable state (consistently online or offline).

        A device is considered stable if:
        - It has enough samples
        - The ratio of state transitions to total checks is low
        """
        if self.total_checks < min_samples:
            return False

        # Calculate transition ratio (state changes per check)
        if self.total_checks <= 1:
            return False

        actual_transition_ratio = self.state_transitions / (self.total_checks - 1)
        return actual_transition_ratio <= transition_ratio

    def is_stable_offline(
        self,
        min_samples: int = STABLE_STATE_MIN_SAMPLES,
        transition_ratio: float = STABLE_STATE_TRANSITION_RATIO,
        availability_threshold: float = STABLE_OFFLINE_AVAILABILITY_THRESHOLD,
    ) -> bool:
        """
        Check if device is consistently offline (this is its normal state).

        Returns True if device:
        - Has enough samples
        - Has very low availability (mostly offline)
        - Has few state transitions (stable behavior)
        """
        if not self.is_stable_state(min_samples, transition_ratio):
            return False

        return self.availability < availability_threshold

    def is_stable_online(
        self,
        min_samples: int = STABLE_STATE_MIN_SAMPLES,
        transition_ratio: float = STABLE_STATE_TRANSITION_RATIO,
        availability_threshold: float = STABLE_ONLINE_AVAILABILITY_THRESHOLD,
    ) -> bool:
        """
        Check if device is consistently online (this is its normal state).

        Returns True if device:
        - Has enough samples
        - Has very high availability (mostly online)
        - Has few state transitions (stable behavior)
        """
        if not self.is_stable_state(min_samples, transition_ratio):
            return False

        return self.availability > availability_threshold

    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            "device_ip": self.device_ip,
            "device_name": self.device_name,
            "total_checks": self.total_checks,
            "successful_checks": self.successful_checks,
            "failed_checks": self.failed_checks,
            "latency_stats": self.latency_stats.to_dict(),
            "packet_loss_stats": self.packet_loss_stats.to_dict(),
            "hourly_patterns": {str(k): v for k, v in self.hourly_patterns.items()},
            "daily_patterns": {str(k): v for k, v in self.daily_patterns.items()},
            "last_state": self.last_state,
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "state_transitions": self.state_transitions,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DeviceStats":
        """Deserialize from dictionary"""
        stats = cls(
            device_ip=data["device_ip"],
            device_name=data.get("device_name"),
        )
        stats.total_checks = data.get("total_checks", 0)
        stats.successful_checks = data.get("successful_checks", 0)
        stats.failed_checks = data.get("failed_checks", 0)

        if "latency_stats" in data:
            stats.latency_stats = LatencyStats.from_dict(data["latency_stats"])
        if "packet_loss_stats" in data:
            stats.packet_loss_stats = LatencyStats.from_dict(data["packet_loss_stats"])

        stats.hourly_patterns = {
            int(k): tuple(v) for k, v in data.get("hourly_patterns", {}).items()
        }
        stats.daily_patterns = {int(k): tuple(v) for k, v in data.get("daily_patterns", {}).items()}

        stats.last_state = data.get("last_state")
        stats.last_check_time = (
            datetime.fromisoformat(data["last_check_time"]) if data.get("last_check_time") else None
        )
        stats.consecutive_failures = data.get("consecutive_failures", 0)
        stats.consecutive_successes = data.get("consecutive_successes", 0)
        stats.state_transitions = data.get("state_transitions", 0)
        stats.first_seen = (
            datetime.fromisoformat(data["first_seen"]) if data.get("first_seen") else None
        )
        stats.last_updated = (
            datetime.fromisoformat(data["last_updated"]) if data.get("last_updated") else None
        )

        return stats


class AnomalyDetector:
    """
    Machine learning-based anomaly detector for network devices.

    Uses statistical methods and learned baselines to detect:
    - Unexpected device offline events
    - Unusual latency spikes
    - Abnormal packet loss
    - Pattern deviations from historical behavior
    """

    MODEL_VERSION = "1.0.0"

    def __init__(self):
        self._device_stats: dict[str, DeviceStats] = {}
        self._anomalies_detected: int = 0
        self._false_positives: int = 0
        self._last_training: datetime | None = None
        # Track devices we've sent offline notifications for
        # so we can send online notifications when they recover
        self._notified_offline: set = set()
        # Track anomaly timestamps for 24h count (max 10000 to prevent unbounded growth)
        self._anomaly_timestamps: deque = deque(maxlen=10000)
        # Track current devices in the network (for accurate device count reporting)
        self._current_devices: set = set()

        # Load persisted state
        self._load_state()

    def _save_state(self):
        """Save model state to disk"""
        try:
            settings.data_dir.mkdir(parents=True, exist_ok=True)

            state = {
                "version": self.MODEL_VERSION,
                "devices": {ip: stats.to_dict() for ip, stats in self._device_stats.items()},
                "anomalies_detected": self._anomalies_detected,
                "false_positives": self._false_positives,
                "last_training": self._last_training.isoformat() if self._last_training else None,
                "notified_offline": list(
                    self._notified_offline
                ),  # Track devices with pending online notifications
                "anomaly_timestamps": [ts.isoformat() for ts in self._anomaly_timestamps],
                "current_devices": list(
                    self._current_devices
                ),  # Track devices currently in network
            }

            with open(MODEL_STATE_FILE, "w") as f:
                json.dump(state, f, indent=2)

            logger.debug(f"Saved anomaly detector state with {len(self._device_stats)} devices")
        except Exception as e:
            logger.error(f"Failed to save anomaly detector state: {e}")

    def _load_state(self):
        """Load model state from disk"""
        try:
            if not MODEL_STATE_FILE.exists():
                logger.debug("No existing anomaly detector state found")
                return

            with open(MODEL_STATE_FILE, "r") as f:
                state = json.load(f)

            # Check version compatibility
            if state.get("version") != self.MODEL_VERSION:
                logger.warning(f"Model version mismatch, starting fresh")
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
                f"Loaded anomaly detector state with {len(self._device_stats)} devices, {len(self._current_devices)} current devices, {len(self._notified_offline)} pending online notifications"
            )
        except Exception as e:
            logger.error(f"Failed to load anomaly detector state: {e}")

    def train(
        self,
        device_ip: str,
        success: bool,
        latency_ms: float | None = None,
        packet_loss: float | None = None,
        device_name: str | None = None,
        check_time: datetime | None = None,
    ):
        """
        Train the model with a new data point.
        Called passively after each health check.
        """
        if check_time is None:
            check_time = datetime.utcnow()

        # Get or create device stats
        if device_ip not in self._device_stats:
            self._device_stats[device_ip] = DeviceStats(
                device_ip=device_ip,
                device_name=device_name,
            )

        stats = self._device_stats[device_ip]
        if device_name:
            stats.device_name = device_name

        # Update statistics
        stats.update_check(success, latency_ms, packet_loss, check_time)

        self._last_training = check_time

        # Periodically save state (every 50 updates or every 10 for new devices)
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
        """
        Analyze a health check result for anomalies.

        Returns an AnomalyDetectionResult with:
        - is_anomaly: Whether this is an anomaly
        - anomaly_score: 0.0 to 1.0 indicating severity
        - anomaly_type: What kind of anomaly was detected
        - explanation: Human-readable explanation
        """
        if check_time is None:
            check_time = datetime.utcnow()

        stats = self._device_stats.get(device_ip)

        # Not enough data to make predictions
        if not stats or stats.total_checks < MIN_SAMPLES_FOR_BASELINE:
            return AnomalyDetectionResult(
                is_anomaly=False,
                anomaly_score=0.0,
                reason="Insufficient data for anomaly detection",
                confidence=0.0,
            )

        # Check for stable offline device - this is the device's normal behavior
        # Don't flag consistently offline devices as anomalies
        if not success and stats.is_stable_offline():
            logger.debug(
                f"Device {device_ip} is in stable offline state "
                f"(availability: {stats.availability:.1f}%, "
                f"transitions: {stats.state_transitions}/{stats.total_checks}, "
                f"samples: {stats.total_checks})"
            )
            return AnomalyDetectionResult(
                is_anomaly=False,
                anomaly_score=0.0,
                reason="Device is in stable offline state (learned baseline behavior)",
                confidence=min(stats.total_checks / 100.0, 1.0),
            )

        contributing_factors = []
        max_anomaly_score = 0.0
        detected_type = None

        # 1. Check for unexpected offline
        if not success:
            expected_state, confidence = stats.get_expected_state_for_time(check_time)

            if (
                expected_state == "online"
                and stats.availability >= UNEXPECTED_OFFLINE_THRESHOLD * 100
            ):
                # Device is usually online but now offline
                score = min(stats.availability / 100.0, 0.95)

                # Increase score if multiple consecutive failures
                if stats.consecutive_failures > 1:
                    score = min(score + (stats.consecutive_failures * 0.1), 0.99)

                if score > max_anomaly_score:
                    max_anomaly_score = score
                    detected_type = AnomalyType.UNEXPECTED_OFFLINE

                contributing_factors.append(
                    f"Device typically has {stats.availability:.1f}% availability but is now offline"
                )

                if stats.consecutive_failures > 1:
                    contributing_factors.append(
                        f"Device has been offline for {stats.consecutive_failures} consecutive checks"
                    )

        # 2. Check for latency anomaly
        if latency_ms is not None and stats.latency_stats.count >= MIN_SAMPLES_FOR_BASELINE:
            mean = stats.latency_stats.mean
            std_dev = stats.latency_stats.std_dev

            if std_dev > 0:
                z_score = abs(latency_ms - mean) / std_dev

                if z_score > LATENCY_ZSCORE_THRESHOLD:
                    score = min(z_score / 10.0, 0.9)  # Scale z-score to 0-0.9

                    if score > max_anomaly_score:
                        max_anomaly_score = score
                        detected_type = AnomalyType.UNUSUAL_LATENCY_SPIKE

                    contributing_factors.append(
                        f"Latency {latency_ms:.1f}ms is {z_score:.1f} std devs from normal ({mean:.1f}ms)"
                    )

        # 3. Check for packet loss anomaly
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

        # 4. Check for time-based anomaly
        hour_avail = stats.get_hourly_availability(check_time.hour)
        if hour_avail is not None and stats.total_checks >= 50:
            # Check if current state deviates significantly from hourly pattern
            if not success and hour_avail > 95:
                score = min(hour_avail / 100.0, 0.7)

                if score > max_anomaly_score:
                    max_anomaly_score = score
                    detected_type = AnomalyType.TIME_BASED_ANOMALY

                contributing_factors.append(
                    f"Device is {hour_avail:.1f}% available at this hour but is currently offline"
                )

        # Build result
        is_anomaly = max_anomaly_score >= 0.5

        if is_anomaly:
            self._anomalies_detected += 1
            self._anomaly_timestamps.append(datetime.utcnow())
            # Save state when anomaly is detected (important event)
            self._save_state()

        # Calculate confidence based on sample size
        confidence = min(stats.total_checks / 100.0, 1.0)

        # Build reason
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
        Analyze a health check and create a NetworkEvent if notification-worthy.

        Returns None if no notification should be sent.
        """
        check_time = datetime.utcnow()

        # First train with the new data
        self.train(device_ip, success, latency_ms, packet_loss, device_name, check_time)

        # Then detect anomalies
        result = self.detect_anomaly(device_ip, success, latency_ms, packet_loss, check_time)

        stats = self._device_stats.get(device_ip)
        current_state = "online" if success else "offline"

        # Determine if we should create an event
        should_notify = False
        event_type = NotificationType.DEVICE_OFFLINE
        priority = NotificationPriority.MEDIUM
        title = ""
        message = ""

        # Use provided previous_state, or fall back to internal state tracking
        # This handles cases where the health service restarted and lost state
        effective_previous_state = previous_state
        if effective_previous_state is None and stats:
            # The stats.last_state was updated by train() above to the current state,
            # but we can infer the previous state from consecutive counters
            #
            # IMPORTANT: We require multiple consecutive checks (>1) to infer state
            # to avoid false positives from fluke/transient network results.
            # A single success among failures (or vice versa) is not enough evidence.
            if stats.consecutive_successes > 1:
                effective_previous_state = "online"
            elif stats.consecutive_failures > 1:
                effective_previous_state = "offline"
            # For single-check transitions, we need stronger evidence:
            # - The device must have significant history in the opposite state
            # - AND not be a "stable" device (which would indicate fluky behavior)
            elif stats.consecutive_successes == 1 and stats.failed_checks >= 3:
                # First success after multiple failures - likely a real recovery
                # But only if device isn't "stable offline" (which would mean this is a fluke)
                if not stats.is_stable_offline():
                    effective_previous_state = "offline"
            elif stats.consecutive_failures == 1 and stats.successful_checks >= 3:
                # First failure after multiple successes - likely a real outage
                # But only if device isn't "stable online" with occasional fluky failures
                if not stats.is_stable_online():
                    effective_previous_state = "online"

        # Check if device was in a non-online state (offline or degraded)
        # We only consider it "was not online" if we have explicit evidence
        device_was_not_online = effective_previous_state in ("offline", "degraded")

        # Check if device was online before (for offline detection)
        device_was_online = effective_previous_state == "online"

        # Check for state change
        state_changed = effective_previous_state and effective_previous_state != current_state

        # Check if this is a genuine transition to offline (not a fluke failure)
        # Requires: first failure after MULTIPLE successes, and device isn't "stable online"
        # (stable online devices with occasional failures shouldn't trigger notifications)
        just_went_offline = (
            not success
            and stats
            and stats.consecutive_failures == 1
            and stats.successful_checks >= 3  # Require history of being online
            and not stats.is_stable_online()  # Don't notify for stable devices with fluky failures
        )

        # Check if device is in a stable offline state (this is its normal behavior)
        is_stable_offline_device = stats and stats.is_stable_offline()

        if not success:
            # Device is offline
            if is_stable_offline_device:
                # This device is normally offline - don't notify
                logger.debug(
                    f"Skipping notification for stable offline device {device_ip} "
                    f"(availability: {stats.availability:.1f}%)"
                )
                should_notify = False
            elif state_changed or just_went_offline or device_was_online:
                # Device went offline - send DEVICE_OFFLINE notification
                # This triggers when:
                # - state_changed: explicit state change detected
                # - just_went_offline: first failure after successes (internal detection)
                # - device_was_online: we know it was online before
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

                # Track that we sent an offline notification - we'll send online when it recovers
                self._notified_offline.add(device_ip)
                self._save_state()  # Persist immediately so we don't lose tracking on restart

                logger.info(
                    f"Device {device_ip} went offline - creating DEVICE_OFFLINE notification "
                    f"(previous_state={previous_state}, effective_previous_state={effective_previous_state}, "
                    f"state_changed={state_changed}, just_went_offline={just_went_offline}, "
                    f"is_anomaly={result.is_anomaly})"
                )

                # Increase priority if multiple failures
                if stats and stats.consecutive_failures >= 3:
                    priority = NotificationPriority.HIGH
                    message += f" ({stats.consecutive_failures} consecutive failures)"

        elif success and (
            # PRIMARY: We sent an offline notification for this device - send online when it recovers
            device_ip in self._notified_offline
            or
            # FALLBACK: Device came back online from any non-online state (offline, degraded)
            device_was_not_online
            or
            # FALLBACK: This is a genuine recovery: first success after MULTIPLE failures
            # AND device isn't "stable offline" (which would indicate a fluke success)
            (
                stats
                and stats.consecutive_successes == 1
                and stats.failed_checks >= 3
                and not stats.is_stable_offline()
            )
        ):
            # Device came back online from offline/degraded state
            should_notify = True
            event_type = NotificationType.DEVICE_ONLINE
            priority = NotificationPriority.LOW
            title = f"Device Online: {device_name or device_ip}"

            if effective_previous_state == "degraded":
                message = f"The device at {device_ip} has recovered from degraded state and is now fully online."
            else:
                message = f"The device at {device_ip} is now responding."

            # Check if we had sent an offline notification (before removing from tracking)
            had_offline_notification = device_ip in self._notified_offline

            # Remove from tracking - we're sending the online notification now
            if had_offline_notification:
                self._notified_offline.discard(device_ip)
                self._save_state()  # Persist immediately

            logger.info(
                f"Device {device_ip} came back online - creating DEVICE_ONLINE notification "
                f"(previous_state={previous_state}, effective_previous_state={effective_previous_state}, "
                f"had_offline_notification={had_offline_notification}, "
                f"consecutive_successes={stats.consecutive_successes if stats else 'N/A'}, "
                f"failed_checks={stats.failed_checks if stats else 'N/A'})"
            )

            # Add recovery context if we have failure history
            if stats and stats.failed_checks > 0:
                if stats.consecutive_failures == 0 and stats.failed_checks > 0:
                    message += " Device has recovered."

        # Check for degraded performance
        if success and result.is_anomaly:
            if result.anomaly_type == AnomalyType.UNUSUAL_LATENCY_SPIKE:
                should_notify = True
                event_type = NotificationType.HIGH_LATENCY
                priority = NotificationPriority.MEDIUM
                title = f"High Latency: {device_name or device_ip}"
                message = f"Unusual latency detected on {device_ip}: {latency_ms:.1f}ms (normally {stats.latency_stats.mean:.1f}ms)"

            elif result.anomaly_type == AnomalyType.UNUSUAL_PACKET_LOSS:
                should_notify = True
                event_type = NotificationType.PACKET_LOSS
                priority = NotificationPriority.MEDIUM
                title = f"Packet Loss: {device_name or device_ip}"
                message = f"High packet loss detected on {device_ip}: {packet_loss*100:.1f}%"

        if not should_notify:
            logger.debug(
                f"No notification for {device_ip}: success={success}, "
                f"previous_state={previous_state}, effective_previous_state={effective_previous_state}, "
                f"current_state={current_state}, is_anomaly={result.is_anomaly}"
            )
            return None

        logger.info(f"Creating {event_type.value} notification for {device_ip}: {title}")

        # Create the event
        import uuid

        event = NetworkEvent(
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
            ml_model_version=self.MODEL_VERSION,
            details={
                "latency_ms": latency_ms,
                "packet_loss_percent": packet_loss * 100 if packet_loss else None,
                "contributing_factors": result.contributing_factors,
            },
        )

        return event

    def get_device_baseline(self, device_ip: str) -> DeviceBaseline | None:
        """Get the learned baseline for a device"""
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
            model_version=self.MODEL_VERSION,
            samples_count=stats.total_checks,
        )

    def get_model_status(self) -> MLModelStatus:
        """Get current status of the ML model"""
        # Count anomalies in past 24 hours
        cutoff = datetime.utcnow() - timedelta(days=1)
        anomalies_24h = sum(1 for ts in self._anomaly_timestamps if ts > cutoff)

        # Count only devices currently in the network
        # If current_devices hasn't been synced yet, fall back to tracked stats
        if self._current_devices:
            devices_tracked = len(self._current_devices)
        else:
            devices_tracked = len(self._device_stats)

        has_data = len(self._device_stats) > 0 and self._last_training is not None

        return MLModelStatus(
            model_version=self.MODEL_VERSION,
            last_training=self._last_training,
            samples_count=sum(s.total_checks for s in self._device_stats.values()),
            devices_tracked=devices_tracked,
            anomalies_detected_total=self._anomalies_detected,
            anomalies_detected_24h=anomalies_24h,
            # Deprecated: kept for backward compatibility
            is_trained=has_data,
            # Model is always online learning once it has data
            is_online_learning=has_data,
            # Status reflects continuous learning nature
            training_status="online_learning" if has_data else "initializing",
        )

    def mark_false_positive(self, event_id: str):
        """Mark an anomaly as a false positive (for feedback learning)"""
        self._false_positives += 1
        logger.info(f"Marked event {event_id} as false positive")
        # In a more advanced implementation, this would adjust model weights

    def reset_device(self, device_ip: str):
        """Reset learned data for a specific device"""
        if device_ip in self._device_stats:
            del self._device_stats[device_ip]
            self._save_state()
            logger.info(f"Reset learned data for device {device_ip}")

    def reset_all(self):
        """Reset all learned data"""
        self._device_stats.clear()
        self._anomalies_detected = 0
        self._false_positives = 0
        self._last_training = None
        self._anomaly_timestamps.clear()
        self._current_devices.clear()
        self._save_state()
        logger.info("Reset all anomaly detection data")

    def sync_current_devices(self, device_ips: list[str]):
        """
        Sync the list of devices currently in the network.

        This ensures the ML model status only reports tracking devices
        that are actually present in the network. Historical data for
        removed devices is retained for potential future use.
        """
        self._current_devices = set(device_ips)
        self._save_state()
        logger.info(f"Synced {len(self._current_devices)} current devices for ML tracking")

    def get_current_devices_count(self) -> int:
        """Get the count of devices currently being tracked in the network"""
        return len(self._current_devices) if self._current_devices else len(self._device_stats)

    def save(self):
        """Public method to save state - call on shutdown"""
        self._save_state()
        logger.info(
            f"Saved anomaly detector state with {len(self._device_stats)} devices and {sum(s.total_checks for s in self._device_stats.values())} total samples"
        )


# Singleton instance
anomaly_detector = AnomalyDetector()
