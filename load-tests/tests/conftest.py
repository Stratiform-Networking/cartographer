"""Pytest configuration for load-test helper tests."""

import sys
import types
from pathlib import Path

LOAD_TESTS_DIR = Path(__file__).resolve().parents[1]
if str(LOAD_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(LOAD_TESTS_DIR))

# Provide a lightweight locust stub for unit tests.
# Real locust imports can fail under some local Python/gevent combos and these
# tests only need StopUser and LoadTestShape behavior.
if "locust" not in sys.modules:
    locust_module = types.ModuleType("locust")
    exception_module = types.ModuleType("locust.exception")

    class StopUser(Exception):
        pass

    class LoadTestShape:
        runner = None

        @property
        def run_time(self):
            return None

    exception_module.StopUser = StopUser
    locust_module.LoadTestShape = LoadTestShape
    locust_module.exception = exception_module

    sys.modules["locust"] = locust_module
    sys.modules["locust.exception"] = exception_module
