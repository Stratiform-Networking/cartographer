"""
Shared test fixtures for auth service unit tests.
"""
import os
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock

# Set test environment before imports - use SQLite for testing
os.environ["AUTH_DATA_DIR"] = "/tmp/test-auth-data"
os.environ["JWT_SECRET"] = "test-secret-key-for-testing"
os.environ["JWT_EXPIRATION_HOURS"] = "24"
os.environ["RESEND_API_KEY"] = ""  # Disable email in tests
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"  # Use SQLite for tests


@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    return AsyncMock()
