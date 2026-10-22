import time

from capacity_discovery_shape import CapacityDiscoveryShape
from capacity_window_metrics import rolling_window_metrics


def _new_shape(monkeypatch, **env):
    for key, value in env.items():
        monkeypatch.setenv(key, str(value))
    shape = CapacityDiscoveryShape()
    shape.runner = object()
    return shape


def test_stop_when_rolling_p95_exceeds_threshold(monkeypatch):
    rolling_window_metrics.reset()
    shape = _new_shape(
        monkeypatch,
        RAMP_WINDOW_SECONDS=60,
        RAMP_MIN_SAMPLES=5,
        RAMP_P95_THRESHOLD=200,
        RAMP_ERROR_THRESHOLD=0.5,
    )

    now = time.time()
    for rt in [100, 120, 130, 220, 260]:
        rolling_window_metrics.add(rt, is_failure=False, timestamp=now)

    assert shape._should_stop_based_on_metrics() is True
    assert "Rolling p95" in shape.stop_reason


def test_stop_when_rolling_error_rate_exceeds_threshold(monkeypatch):
    rolling_window_metrics.reset()
    shape = _new_shape(
        monkeypatch,
        RAMP_WINDOW_SECONDS=60,
        RAMP_MIN_SAMPLES=5,
        RAMP_P95_THRESHOLD=1000,
        RAMP_ERROR_THRESHOLD=0.2,
    )

    now = time.time()
    for idx in range(10):
        rolling_window_metrics.add(80 + idx, is_failure=(idx < 3), timestamp=now)

    assert shape._should_stop_based_on_metrics() is True
    assert "Rolling error rate" in shape.stop_reason


def test_uses_rolling_window_not_cumulative_totals(monkeypatch):
    rolling_window_metrics.reset()
    shape = _new_shape(
        monkeypatch,
        RAMP_WINDOW_SECONDS=30,
        RAMP_MIN_SAMPLES=5,
        RAMP_P95_THRESHOLD=200,
        RAMP_ERROR_THRESHOLD=0.5,
    )

    old_timestamp = time.time() - 120
    recent_timestamp = time.time()

    # Old good requests should be excluded by rolling window cutoff.
    for _ in range(100):
        rolling_window_metrics.add(20, is_failure=False, timestamp=old_timestamp)

    # Recent slow requests should trigger p95 threshold in-window.
    for rt in [210, 220, 230, 240, 250]:
        rolling_window_metrics.add(rt, is_failure=False, timestamp=recent_timestamp)

    assert shape._should_stop_based_on_metrics() is True
    assert "Rolling p95" in shape.stop_reason

