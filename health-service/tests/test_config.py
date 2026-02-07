"""
Tests for health service configuration.
"""

import pytest


def test_cors_wildcard_rejected_in_production(monkeypatch):
    """Should raise if CORS wildcard is set in production."""
    from app.config import Settings

    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("CORS_ORIGINS", "*")

    with pytest.raises(ValueError, match="CORS wildcard"):
        Settings()
