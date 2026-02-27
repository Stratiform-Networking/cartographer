"""
Shared test fixtures for auth service unit tests.
"""

import os
from unittest.mock import AsyncMock

import pytest

# Set test environment before imports - use SQLite for testing
os.environ["AUTH_DATA_DIR"] = "/tmp/test-auth-data"
os.environ["JWT_SECRET"] = "test-secret-key-for-testing"
os.environ["JWT_EXPIRATION_HOURS"] = "24"
os.environ["ASSISTANT_KEYS_ENCRYPTION_KEY"] = "test-assistant-key-encryption-secret"
os.environ["RESEND_API_KEY"] = ""  # Disable email in tests
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"  # Use SQLite for tests


@pytest.fixture(autouse=True)
def clear_rate_limit():
    """Clear rate limiting state before each test to prevent cross-test 429s."""
    from app.rate_limit import _request_log

    _request_log.clear()
    yield
    _request_log.clear()


@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    return AsyncMock()
