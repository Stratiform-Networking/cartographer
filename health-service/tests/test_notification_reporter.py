"""
Unit tests for notification_reporter service.
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.notification_reporter import (
    _load_network_states,
    _previous_states,
    _save_network_states,
    clear_state_tracking,
    report_health_check,
    report_health_checks_batch,
    sync_devices_with_notification_service,
)


class TestReportHealthCheck:
    """Tests for report_health_check function"""

    def setup_method(self):
        """Clear state before each test"""
        clear_state_tracking()

    async def test_report_success(self):
        """Should report successfully"""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = ""

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await report_health_check(
                device_ip="192.168.1.1",
                success=True,
                network_id="network-uuid-1",  # Required for actual reporting
                latency_ms=25.0,
                packet_loss=0.0,
                device_name="router",
            )

            assert result is True
            mock_client.post.assert_called_once()

    async def test_report_with_previous_state(self):
        """Should include previous state when available"""
        mock_response = AsyncMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            # First call establishes state (needs network_id to actually POST)
            await report_health_check(
                device_ip="192.168.1.1", success=True, network_id="network-uuid-1"
            )

            # Second call should include previous state
            await report_health_check(
                device_ip="192.168.1.1", success=False, network_id="network-uuid-1"
            )

            # Check that second call had previous_state
            call_args = mock_client.post.call_args_list[1]
            params = call_args.kwargs.get("params", {})
            assert params.get("previous_state") == "online"

    async def test_report_non_200_response(self):
        """Should return False for non-200 response"""
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.text = "Internal error"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await report_health_check(
                device_ip="192.168.1.1", success=True, network_id="network-uuid-1"
            )

            assert result is False

    async def test_report_connect_error(self):
        """Should handle connection error"""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await report_health_check(
                device_ip="192.168.1.1", success=True, network_id="network-uuid-1"
            )

            assert result is False

    async def test_report_generic_exception(self):
        """Should handle generic exception"""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=Exception("Unknown error"))

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await report_health_check(
                device_ip="192.168.1.1", success=True, network_id="network-uuid-1"
            )

            assert result is False

    async def test_report_with_optional_params(self):
        """Should send only provided optional params"""
        mock_response = AsyncMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            await report_health_check(
                device_ip="192.168.1.1",
                success=True,
                network_id="network-uuid-1",  # Required for actual reporting
                latency_ms=25.0,
                # Not providing packet_loss or device_name
            )

            call_args = mock_client.post.call_args
            params = call_args.kwargs.get("params", {})

            assert "latency_ms" in params
            assert "packet_loss" not in params
            assert "device_name" not in params

    async def test_report_without_network_id(self):
        """Should return False without network_id (skips reporting)"""
        # No mock needed since it should return early
        result = await report_health_check(
            device_ip="192.168.1.1",
            success=True,
            # No network_id
        )

        assert result is False


class TestReportHealthChecksBatch:
    """Tests for report_health_checks_batch function"""

    def setup_method(self):
        """Clear state before each test"""
        clear_state_tracking()

    async def test_batch_report_all_success(self):
        """Should report all checks in batch (mocking at report_health_check level)"""
        # Mock report_health_check to return True for all calls
        with patch(
            "app.services.notification_reporter.report_health_check", new_callable=AsyncMock
        ) as mock_report:
            mock_report.return_value = True

            results = {
                "192.168.1.1": (True, 25.0, 0.0, "device1"),
                "192.168.1.2": (True, 30.0, 0.0, "device2"),
                "192.168.1.3": (False, None, 1.0, "device3"),
            }

            # Note: report_health_checks_batch calls report_health_check
            # but doesn't pass network_id, so we mock at that level
            count = await report_health_checks_batch(results)

            assert count == 3
            assert mock_report.call_count == 3

    async def test_batch_report_some_failures(self):
        """Should count successful reports"""
        call_count = 0

        async def mock_report(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Second call fails
            return call_count != 2

        with patch(
            "app.services.notification_reporter.report_health_check", side_effect=mock_report
        ):
            results = {
                "192.168.1.1": (True, 25.0, 0.0, "device1"),
                "192.168.1.2": (True, 30.0, 0.0, "device2"),
                "192.168.1.3": (True, 20.0, 0.0, "device3"),
            }

            count = await report_health_checks_batch(results)

            assert count == 2  # 1 failed

    async def test_batch_without_network_id_returns_zero(self):
        """Should return 0 when no network_id is passed (current behavior)"""
        # Don't mock - just verify actual behavior
        results = {
            "192.168.1.1": (True, 25.0, 0.0, "device1"),
            "192.168.1.2": (True, 30.0, 0.0, "device2"),
        }

        count = await report_health_checks_batch(results)

        # Without network_id, report_health_check returns False for all
        assert count == 0


class TestClearStateTracking:
    """Tests for clear_state_tracking function"""

    async def test_clear_state(self):
        """Should clear all tracked states"""
        # First establish some state
        mock_response = AsyncMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            # Need network_id to actually execute the code that sets _previous_states
            await report_health_check(
                device_ip="192.168.1.1", success=True, network_id="network-uuid-1"
            )

        # Clear state
        clear_state_tracking()

        # Import and check the global state
        from app.services.notification_reporter import _previous_states

        assert len(_previous_states) == 0


class TestStatePersistenceHelpers:
    """Tests for state load/save helpers"""

    def test_load_network_states_success(self, tmp_path, monkeypatch):
        """Should load state file when it exists"""
        state_dir = tmp_path / "states"
        state_dir.mkdir()
        state_file = state_dir / "net-1.json"
        state_file.write_text('{"192.168.1.1": "online"}')

        monkeypatch.setattr("app.services.notification_reporter._STATE_DIR", state_dir)

        states = _load_network_states("net-1")

        assert states == {"192.168.1.1": "online"}
        clear_state_tracking()

    def test_load_network_states_handles_error(self, tmp_path, monkeypatch):
        """Should return empty dict on read error"""
        state_dir = tmp_path / "states"
        state_dir.mkdir()
        state_file = state_dir / "net-1.json"
        state_file.write_text('{"192.168.1.1": "online"}')
        monkeypatch.setattr("app.services.notification_reporter._STATE_DIR", state_dir)

        def boom(*args, **kwargs):
            raise OSError("nope")

        monkeypatch.setattr("builtins.open", boom)

        states = _load_network_states("net-1")

        assert states == {}
        clear_state_tracking()

    def test_save_network_states_handles_error(self, tmp_path, monkeypatch):
        """Should swallow errors when saving states"""
        state_dir = tmp_path / "states"
        monkeypatch.setattr("app.services.notification_reporter._STATE_DIR", state_dir)
        _previous_states["net-1"] = {"192.168.1.1": "online"}

        def boom(*args, **kwargs):
            raise OSError("nope")

        monkeypatch.setattr("builtins.open", boom)

        _save_network_states("net-1")
        clear_state_tracking()

    def test_clear_state_tracking_removes_file(self, tmp_path, monkeypatch):
        """Should remove state file when clearing a specific network"""
        state_dir = tmp_path / "states"
        state_dir.mkdir()
        state_file = state_dir / "net-1.json"
        state_file.write_text('{"192.168.1.1": "online"}')

        monkeypatch.setattr("app.services.notification_reporter._STATE_DIR", state_dir)
        _previous_states["net-1"] = {"192.168.1.1": "online"}

        clear_state_tracking("net-1")

        assert not state_file.exists()
        assert "net-1" not in _previous_states


class TestSyncDevicesWithNotificationService:
    """Tests for sync_devices_with_notification_service function"""

    async def test_sync_devices_success(self):
        """Should sync devices successfully with network_id"""
        mock_response = AsyncMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await sync_devices_with_notification_service(
                ["192.168.1.1", "192.168.1.2", "192.168.1.3"], network_id=42
            )

            assert result is True
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args.kwargs.get("json") == ["192.168.1.1", "192.168.1.2", "192.168.1.3"]
            assert call_args.kwargs.get("params") == {"network_id": 42}

    async def test_sync_devices_without_network_id(self):
        """Should return False without network_id"""
        result = await sync_devices_with_notification_service(["192.168.1.1", "192.168.1.2"])
        assert result is False

    async def test_sync_devices_non_200_response(self):
        """Should return False for non-200 response"""
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.text = "Internal error"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await sync_devices_with_notification_service(["192.168.1.1"], network_id=42)

            assert result is False

    async def test_sync_devices_connect_error(self):
        """Should handle connection error"""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await sync_devices_with_notification_service(["192.168.1.1"], network_id=42)

            assert result is False

    async def test_sync_devices_generic_exception(self):
        """Should handle generic exception"""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=Exception("Unknown error"))

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await sync_devices_with_notification_service(["192.168.1.1"], network_id=42)

            assert result is False

    async def test_sync_empty_devices_list(self):
        """Should sync empty devices list (clearing all devices for a network)"""
        mock_response = AsyncMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await sync_devices_with_notification_service([], network_id=42)

            assert result is True
            call_args = mock_client.post.call_args
            assert call_args.kwargs.get("json") == []
            assert call_args.kwargs.get("params") == {"network_id": 42}
