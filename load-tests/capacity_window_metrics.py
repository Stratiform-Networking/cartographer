"""Rolling-window metrics for capacity discovery."""

from __future__ import annotations

import threading
import time
from collections import deque
from math import ceil
from typing import Deque, Dict, Optional, Tuple


class RollingWindowMetrics:
    """Thread-safe collector for recent request metrics."""

    def __init__(self) -> None:
        self._records: Deque[Tuple[float, float, bool]] = deque()
        self._lock = threading.Lock()

    def reset(self) -> None:
        with self._lock:
            self._records.clear()

    def add(self, response_time_ms: float, is_failure: bool, timestamp: Optional[float] = None) -> None:
        ts = timestamp if timestamp is not None else time.time()
        with self._lock:
            self._records.append((ts, float(response_time_ms), bool(is_failure)))

    def snapshot(self, window_seconds: int) -> Dict[str, float]:
        now = time.time()
        cutoff = now - window_seconds
        with self._lock:
            while self._records and self._records[0][0] < cutoff:
                self._records.popleft()

            sample_size = len(self._records)
            if sample_size == 0:
                return {
                    "sample_size": 0,
                    "p95_ms": 0.0,
                    "error_rate": 0.0,
                }

            response_times = sorted(record[1] for record in self._records)
            failures = sum(1 for record in self._records if record[2])
            # nearest-rank percentile
            p95_idx = max(0, min(sample_size - 1, ceil(0.95 * sample_size) - 1))
            p95_ms = response_times[p95_idx]
            error_rate = failures / sample_size

            return {
                "sample_size": sample_size,
                "p95_ms": p95_ms,
                "error_rate": error_rate,
            }


rolling_window_metrics = RollingWindowMetrics()

