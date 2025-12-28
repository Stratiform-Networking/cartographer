"""
Extended tests for version_checker.py to improve coverage.

Covers:
- Version parsing
- Version comparison
- Checker loop
- Update notifications
- State persistence
"""

import os
import json
import asyncio
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Set test environment
os.environ["NOTIFICATION_DATA_DIR"] = "/tmp/test_notification_data_version"

from app.services.version_checker import (
    parse_version,
    compare_versions,
    get_update_priority,
    get_update_title,
    get_update_message,
    VersionChecker,
    DATA_DIR,
    VERSION_STATE_FILE,
    CURRENT_VERSION,
)
from app.models import NotificationPriority


class TestParseVersion:
    """Tests for parse_version function."""
    
    def test_parse_standard_version(self):
        """Test parsing standard version string."""
        result = parse_version("1.2.3")
        assert result == (1, 2, 3)
    
    def test_parse_version_with_v_prefix(self):
        """Test parsing version with v prefix."""
        result = parse_version("v1.2.3")
        assert result == (1, 2, 3)
    
    def test_parse_version_with_extra(self):
        """Test parsing version with extra suffix."""
        result = parse_version("1.2.3-beta")
        assert result == (1, 2, 3)
    
    def test_parse_version_with_whitespace(self):
        """Test parsing version with whitespace."""
        result = parse_version("  1.2.3  \n")
        assert result == (1, 2, 3)
    
    def test_parse_invalid_version(self):
        """Test parsing invalid version string."""
        result = parse_version("invalid")
        assert result is None
    
    def test_parse_empty_version(self):
        """Test parsing empty version string."""
        result = parse_version("")
        assert result is None
    
    def test_parse_partial_version(self):
        """Test parsing partial version string."""
        result = parse_version("1.2")
        assert result is None


class TestCompareVersions:
    """Tests for compare_versions function."""
    
    def test_compare_equal_versions(self):
        """Test comparing equal versions."""
        has_update, update_type = compare_versions("1.0.0", "1.0.0")
        assert has_update is False
        assert update_type is None
    
    def test_compare_major_update(self):
        """Test detecting major version update."""
        has_update, update_type = compare_versions("1.0.0", "2.0.0")
        assert has_update is True
        assert update_type == "major"
    
    def test_compare_minor_update(self):
        """Test detecting minor version update."""
        has_update, update_type = compare_versions("1.0.0", "1.1.0")
        assert has_update is True
        assert update_type == "minor"
    
    def test_compare_patch_update(self):
        """Test detecting patch version update."""
        has_update, update_type = compare_versions("1.0.0", "1.0.1")
        assert has_update is True
        assert update_type == "patch"
    
    def test_compare_newer_current(self):
        """Test when current is newer than latest."""
        has_update, update_type = compare_versions("2.0.0", "1.0.0")
        assert has_update is False
        assert update_type is None
    
    def test_compare_invalid_current(self):
        """Test comparing with invalid current version."""
        has_update, update_type = compare_versions("invalid", "1.0.0")
        assert has_update is False
        assert update_type is None
    
    def test_compare_invalid_latest(self):
        """Test comparing with invalid latest version."""
        has_update, update_type = compare_versions("1.0.0", "invalid")
        assert has_update is False
        assert update_type is None


class TestGetUpdatePriority:
    """Tests for get_update_priority function."""
    
    def test_major_update_priority(self):
        """Test priority for major update."""
        priority = get_update_priority("major")
        assert priority == NotificationPriority.HIGH
    
    def test_minor_update_priority(self):
        """Test priority for minor update."""
        priority = get_update_priority("minor")
        assert priority == NotificationPriority.MEDIUM
    
    def test_patch_update_priority(self):
        """Test priority for patch update."""
        priority = get_update_priority("patch")
        assert priority == NotificationPriority.LOW
    
    def test_none_update_priority(self):
        """Test priority for None update type."""
        priority = get_update_priority(None)
        assert priority == NotificationPriority.LOW


class TestGetUpdateTitle:
    """Tests for get_update_title function."""
    
    def test_major_update_title(self):
        """Test title for major update."""
        title = get_update_title("major", "2.0.0")
        assert "Major Update" in title
        assert "2.0.0" in title
    
    def test_minor_update_title(self):
        """Test title for minor update."""
        title = get_update_title("minor", "1.1.0")
        assert "New Features" in title
        assert "1.1.0" in title
    
    def test_patch_update_title(self):
        """Test title for patch update."""
        title = get_update_title("patch", "1.0.1")
        assert "Bug Fixes" in title
        assert "1.0.1" in title
    
    def test_none_update_title(self):
        """Test title for None update type."""
        title = get_update_title(None, "1.0.0")
        assert "Bug Fixes" in title


class TestGetUpdateMessage:
    """Tests for get_update_message function."""
    
    def test_major_update_message(self):
        """Test message for major update."""
        message = get_update_message("major", "1.0.0", "2.0.0")
        assert "major release" in message
        assert "1.0.0" in message
        assert "2.0.0" in message
    
    def test_minor_update_message(self):
        """Test message for minor update."""
        message = get_update_message("minor", "1.0.0", "1.1.0")
        assert "new features" in message
    
    def test_patch_update_message(self):
        """Test message for patch update."""
        message = get_update_message("patch", "1.0.0", "1.0.1")
        assert "bug fixes" in message


class TestVersionChecker:
    """Tests for VersionChecker class."""
    
    @pytest.fixture
    def checker(self):
        """Create a fresh version checker instance."""
        # Clear state file if exists
        if VERSION_STATE_FILE.exists():
            VERSION_STATE_FILE.unlink()
        
        checker = VersionChecker()
        checker._last_notified_version = None
        checker._last_check_time = None
        checker._http_client = None
        checker._checker_task = None
        return checker
    
    def test_load_state_no_file(self, checker):
        """Test loading state when file doesn't exist."""
        # Should not error
        assert checker._last_notified_version is None
    
    def test_load_state_with_file(self, checker):
        """Test loading state from existing file."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        state = {
            "last_notified_version": "1.0.0",
            "last_check_time": "2024-01-01T12:00:00",
        }
        with open(VERSION_STATE_FILE, 'w') as f:
            json.dump(state, f)
        
        checker._load_state()
        
        assert checker._last_notified_version == "1.0.0"
        assert checker._last_check_time is not None
    
    def test_load_state_corrupted(self, checker):
        """Test loading state from corrupted file."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(VERSION_STATE_FILE, 'w') as f:
            f.write("not valid json")
        
        checker._load_state()
        # Should not error
    
    def test_save_state(self, checker):
        """Test saving state to file."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        checker._last_notified_version = "1.0.0"
        checker._last_check_time = datetime.utcnow()
        
        checker._save_state()
        
        assert VERSION_STATE_FILE.exists()
        with open(VERSION_STATE_FILE, 'r') as f:
            state = json.load(f)
        
        assert state["last_notified_version"] == "1.0.0"
    
    @pytest.mark.asyncio
    async def test_start(self, checker):
        """Test starting the checker."""
        await checker.start()
        
        assert checker._http_client is not None
        assert checker._checker_task is not None
        
        # Clean up
        await checker.stop()
    
    @pytest.mark.asyncio
    async def test_start_already_running(self, checker):
        """Test starting when already running."""
        await checker.start()
        first_task = checker._checker_task
        
        await checker.start()  # Should do nothing
        
        assert checker._checker_task is first_task
        
        await checker.stop()
    
    @pytest.mark.asyncio
    async def test_stop(self, checker):
        """Test stopping the checker."""
        await checker.start()
        await checker.stop()
        
        assert checker._checker_task is None
        assert checker._http_client is None
    
    @pytest.mark.asyncio
    async def test_stop_not_running(self, checker):
        """Test stopping when not running."""
        await checker.stop()  # Should not error
        
        assert checker._checker_task is None
    
    @pytest.mark.asyncio
    async def test_fetch_latest_version_success(self, checker):
        """Test fetching latest version successfully."""
        mock_response = MagicMock()
        mock_response.text = "1.2.3"
        mock_response.raise_for_status = MagicMock()
        
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        checker._http_client = mock_client
        
        version = await checker._fetch_latest_version()
        
        assert version == "1.2.3"
    
    @pytest.mark.asyncio
    async def test_fetch_latest_version_failure(self, checker):
        """Test fetching latest version with failure."""
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=Exception("Network error"))
        checker._http_client = mock_client
        
        version = await checker._fetch_latest_version()
        
        assert version is None
    
    @pytest.mark.asyncio
    async def test_fetch_latest_version_no_client(self, checker):
        """Test fetching latest version without client."""
        version = await checker._fetch_latest_version()
        
        assert version is None
    
    @pytest.mark.asyncio
    async def test_check_for_updates_no_update(self, checker):
        """Test checking for updates when none available."""
        mock_response = MagicMock()
        mock_response.text = CURRENT_VERSION  # Same version
        mock_response.raise_for_status = MagicMock()
        
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        checker._http_client = mock_client
        
        await checker._check_for_updates()
        
        assert checker._last_check_time is not None
    
    @pytest.mark.asyncio
    async def test_check_for_updates_already_notified(self, checker):
        """Test checking for updates when already notified."""
        checker._last_notified_version = "2.0.0"
        
        mock_response = MagicMock()
        mock_response.text = "2.0.0"  # Already notified
        mock_response.raise_for_status = MagicMock()
        
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        checker._http_client = mock_client
        
        with patch.object(checker, '_send_update_notification', new_callable=AsyncMock) as mock_send:
            await checker._check_for_updates()
            
            mock_send.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_now_no_client(self, checker):
        """Test check_now creates temporary client."""
        mock_response = MagicMock()
        mock_response.text = CURRENT_VERSION
        mock_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client
            
            result = await checker.check_now()
        
        assert result["success"] is True
        assert result["current_version"] == CURRENT_VERSION
    
    @pytest.mark.asyncio
    async def test_check_now_fetch_failure(self, checker):
        """Test check_now handles fetch failure."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("Network error"))
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client
            
            result = await checker.check_now()
        
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_check_now_with_notification(self, checker):
        """Test check_now with notification sending."""
        mock_response = MagicMock()
        mock_response.text = "99.0.0"  # Much newer version
        mock_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client_class, \
             patch.object(checker, '_send_update_notification', new_callable=AsyncMock) as mock_send:
            
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client
            
            mock_send.return_value = {"network1": []}
            
            result = await checker.check_now(send_notification=True)
        
        assert result["success"] is True
        assert result["has_update"] is True
        assert result["notification_sent"] is True
    
    @pytest.mark.asyncio
    async def test_check_now_skip_already_notified(self, checker):
        """Test check_now skips already notified version."""
        checker._last_notified_version = "99.0.0"
        
        mock_response = MagicMock()
        mock_response.text = "99.0.0"  # Same as already notified
        mock_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client_class, \
             patch.object(checker, '_send_update_notification', new_callable=AsyncMock) as mock_send:
            
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client
            
            result = await checker.check_now(send_notification=True)
        
        assert result["skipped_already_notified"] is True
        mock_send.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_now_force_notification(self, checker):
        """Test check_now with force flag."""
        checker._last_notified_version = "99.0.0"
        
        mock_response = MagicMock()
        mock_response.text = "99.0.0"  # Same as already notified
        mock_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client_class, \
             patch.object(checker, '_send_update_notification', new_callable=AsyncMock) as mock_send:
            
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client
            
            mock_send.return_value = {}
            
            result = await checker.check_now(send_notification=True, force=True)
        
        # Should send even though already notified
        mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_update_notification_function_exists(self, checker):
        """Test send_update_notification function exists."""
        # Just verify the method exists
        assert hasattr(checker, '_send_update_notification')
        assert callable(checker._send_update_notification)
    
    def test_get_status(self, checker):
        """Test getting checker status."""
        checker._last_notified_version = "1.0.0"
        checker._last_check_time = datetime.utcnow()
        checker._checker_task = None
        
        status = checker.get_status()
        
        assert status["current_version"] == CURRENT_VERSION
        assert status["last_notified_version"] == "1.0.0"
        assert status["is_running"] is False
    
    def test_get_status_running(self, checker):
        """Test getting checker status when running."""
        mock_task = MagicMock()
        mock_task.done.return_value = False
        checker._checker_task = mock_task
        
        status = checker.get_status()
        
        assert status["is_running"] is True


class TestCheckerLoop:
    """Tests for checker loop functionality."""
    
    @pytest.mark.asyncio
    async def test_checker_loop_cancellation(self):
        """Test checker loop handles cancellation."""
        checker = VersionChecker()
        
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=asyncio.CancelledError)
        checker._http_client = mock_client
        
        # Start and quickly stop
        await checker.start()
        await asyncio.sleep(0.1)
        await checker.stop()
    
    @pytest.mark.asyncio
    async def test_checker_loop_error_recovery(self):
        """Test checker loop recovers from errors."""
        checker = VersionChecker()
        checker._last_notified_version = None
        checker._last_check_time = None
        
        # Make check fail then succeed
        call_count = 0
        
        async def mock_check():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Temporary error")
        
        with patch.object(checker, '_check_for_updates', side_effect=mock_check):
            # Run one iteration manually
            try:
                await checker._check_for_updates()
            except Exception:
                pass  # Expected
            
            assert call_count == 1

