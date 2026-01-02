"""
Unit tests for version checker service.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import settings
from app.models import NotificationPriority
from app.services.version_checker import (
    VersionChecker,
    compare_versions,
    get_update_message,
    get_update_priority,
    get_update_title,
    parse_version,
    version_checker,
)


class TestVersionParsing:
    """Tests for version parsing"""

    def test_parse_version_valid(self):
        """Should parse valid version"""
        result = parse_version("1.2.3")
        assert result == (1, 2, 3)

    def test_parse_version_with_v_prefix(self):
        """Should parse version with v prefix"""
        result = parse_version("v1.2.3")
        assert result == (1, 2, 3)

    def test_parse_version_invalid(self):
        """Should return None for invalid version"""
        result = parse_version("not-a-version")
        assert result is None

    def test_parse_version_empty(self):
        """Should return None for empty string"""
        result = parse_version("")
        assert result is None


class TestVersionComparison:
    """Tests for version comparison"""

    def test_compare_major_update(self):
        """Should detect major update"""
        has_update, update_type = compare_versions("1.0.0", "2.0.0")
        assert has_update is True
        assert update_type == "major"

    def test_compare_minor_update(self):
        """Should detect minor update"""
        has_update, update_type = compare_versions("1.0.0", "1.1.0")
        assert has_update is True
        assert update_type == "minor"

    def test_compare_patch_update(self):
        """Should detect patch update"""
        has_update, update_type = compare_versions("1.0.0", "1.0.1")
        assert has_update is True
        assert update_type == "patch"

    def test_compare_no_update(self):
        """Should detect no update"""
        has_update, update_type = compare_versions("1.0.0", "1.0.0")
        assert has_update is False
        assert update_type is None

    def test_compare_older_version(self):
        """Should detect older version as no update"""
        has_update, update_type = compare_versions("2.0.0", "1.0.0")
        assert has_update is False

    def test_compare_invalid_version(self):
        """Should handle invalid versions"""
        has_update, update_type = compare_versions("invalid", "1.0.0")
        assert has_update is False
        assert update_type is None


class TestUpdateHelpers:
    """Tests for update helper functions"""

    def test_get_update_priority_major(self):
        """Should return HIGH for major update"""
        priority = get_update_priority("major")
        assert priority == NotificationPriority.HIGH

    def test_get_update_priority_minor(self):
        """Should return MEDIUM for minor update"""
        priority = get_update_priority("minor")
        assert priority == NotificationPriority.MEDIUM

    def test_get_update_priority_patch(self):
        """Should return LOW for patch update"""
        priority = get_update_priority("patch")
        assert priority == NotificationPriority.LOW

    def test_get_update_title_major(self):
        """Should return major update title"""
        title = get_update_title("major", "2.0.0")
        assert "Major Update" in title
        assert "2.0.0" in title

    def test_get_update_title_minor(self):
        """Should return minor update title"""
        title = get_update_title("minor", "1.1.0")
        assert "New Features" in title

    def test_get_update_title_patch(self):
        """Should return patch update title"""
        title = get_update_title("patch", "1.0.1")
        assert "Bug Fixes" in title

    def test_get_update_message_major(self):
        """Should return major update message"""
        message = get_update_message("major", "1.0.0", "2.0.0")
        assert "major release" in message.lower()
        assert "1.0.0" in message
        assert "2.0.0" in message


class TestVersionChecker:
    """Tests for VersionChecker class"""

    def test_init(self, version_checker_instance):
        """Should initialize correctly"""
        assert version_checker_instance._checker_task is None
        assert version_checker_instance._last_notified_version is None

    async def test_start(self, version_checker_instance):
        """Should start checker"""
        with patch.object(version_checker_instance, "_checker_loop", AsyncMock()):
            await version_checker_instance.start()

        assert version_checker_instance._checker_task is not None
        assert version_checker_instance._http_client is not None

        # Cleanup
        await version_checker_instance.stop()

    async def test_start_already_running(self, version_checker_instance):
        """Should not start if already running"""
        version_checker_instance._checker_task = MagicMock()

        await version_checker_instance.start()

        # Should not have created new task

    async def test_stop(self, version_checker_instance):
        """Should stop checker"""
        import asyncio

        # Create an actual cancelled task to mock
        async def dummy_task():
            await asyncio.sleep(1000)

        # Create a real task
        task = asyncio.create_task(dummy_task())
        version_checker_instance._checker_task = task

        mock_http = AsyncMock()
        mock_http.aclose = AsyncMock()
        version_checker_instance._http_client = mock_http

        await version_checker_instance.stop()

        assert version_checker_instance._checker_task is None
        assert version_checker_instance._http_client is None

    async def test_fetch_latest_version_no_client(self, version_checker_instance):
        """Should return None when no client"""
        result = await version_checker_instance._fetch_latest_version()
        assert result is None

    async def test_fetch_latest_version_success(self, version_checker_instance):
        """Should fetch version from GitHub"""
        mock_response = MagicMock()
        mock_response.text = "1.2.3"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        version_checker_instance._http_client = mock_client

        result = await version_checker_instance._fetch_latest_version()

        assert result == "1.2.3"

    async def test_fetch_latest_version_error(self, version_checker_instance):
        """Should return None on error"""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Network error"))
        version_checker_instance._http_client = mock_client

        result = await version_checker_instance._fetch_latest_version()

        assert result is None

    async def test_check_now_no_version(self, version_checker_instance):
        """Should return error when version fetch fails"""
        with patch.object(
            version_checker_instance, "_fetch_latest_version", AsyncMock(return_value=None)
        ):
            result = await version_checker_instance.check_now()

        assert result["success"] is False

    async def test_check_now_no_update(self, version_checker_instance):
        """Should indicate no update available"""
        with patch.object(
            version_checker_instance, "_fetch_latest_version", AsyncMock(return_value="0.1.0")
        ):
            with patch("app.services.version_checker.settings.cartographer_version", "0.1.0"):
                result = await version_checker_instance.check_now()

        assert result["success"] is True
        assert result["has_update"] is False

    async def test_check_now_has_update(self, version_checker_instance):
        """Should indicate update available"""
        with patch.object(
            version_checker_instance, "_fetch_latest_version", AsyncMock(return_value="2.0.0")
        ):
            with patch("app.services.version_checker.settings.cartographer_version", "1.0.0"):
                result = await version_checker_instance.check_now()

        assert result["success"] is True
        assert result["has_update"] is True
        assert result["update_type"] == "major"

    def test_get_status(self, version_checker_instance):
        """Should return status"""
        status = version_checker_instance.get_status()

        assert "current_version" in status
        assert "is_running" in status

    def test_get_status_is_running(self, version_checker_instance):
        """Should indicate running status"""
        mock_task = MagicMock()
        mock_task.done.return_value = False
        version_checker_instance._checker_task = mock_task

        status = version_checker_instance.get_status()

        assert status["is_running"] is True


class TestVersionCheckerPersistence:
    """Tests for version checker state persistence"""

    def test_load_state_no_file(self, version_checker_instance):
        """Should handle missing state file"""
        with patch("pathlib.Path.exists", return_value=False):
            version_checker_instance._load_state()

        # Should not raise

    def test_save_state(self, version_checker_instance):
        """Should save state"""
        version_checker_instance._last_notified_version = "1.0.0"
        version_checker_instance._last_check_time = datetime.utcnow()

        with patch("pathlib.Path.mkdir"):
            with patch("builtins.open", MagicMock()):
                with patch("json.dump") as mock_dump:
                    version_checker_instance._save_state()

        # Should have called json.dump
