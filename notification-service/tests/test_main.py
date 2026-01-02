"""
Unit tests for the main FastAPI application.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app, create_app


class TestCreateApp:
    """Tests for create_app factory"""

    def test_creates_fastapi_app(self):
        """Should create a FastAPI application"""
        with patch("app.main.lifespan"):
            test_app = create_app()

            assert test_app is not None
            assert test_app.title == "Cartographer Notification Service"
            assert test_app.version == "0.1.0"

    def test_includes_notifications_router(self):
        """Should include notifications router"""
        with patch("app.main.lifespan"):
            test_app = create_app()

            routes = [r.path for r in test_app.routes]

            assert any("/api/notifications" in str(r) for r in routes)


class TestRootEndpoint:
    """Tests for root endpoint"""

    def test_root_returns_service_info(self):
        """Should return service information"""
        with patch("app.main.lifespan"):
            test_app = create_app()
            client = TestClient(test_app)

            response = client.get("/")

            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "Cartographer Notification Service"
            assert data["status"] == "running"


class TestHealthzEndpoint:
    """Tests for healthz endpoint"""

    def test_healthz_returns_healthy(self):
        """Should return healthy status"""
        with patch("app.main.lifespan"):
            test_app = create_app()
            client = TestClient(test_app)

            response = client.get("/healthz")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"


class TestCORS:
    """Tests for CORS middleware"""

    def test_cors_middleware_present(self):
        """Should have CORS middleware"""
        with patch("app.main.lifespan"):
            with patch.dict("os.environ", {"CORS_ORIGINS": "http://localhost:3000"}):
                test_app = create_app()

                middlewares = [m.cls.__name__ for m in test_app.user_middleware]
                assert "CORSMiddleware" in middlewares


class TestServiceState:
    """Tests for service state management"""

    def test_get_service_state_no_file(self):
        """Should return default state when no file"""
        from app.main import _get_service_state

        with patch("pathlib.Path.exists", return_value=False):
            state = _get_service_state()

        assert state["clean_shutdown"] is False

    def test_get_service_state_invalid_json(self):
        """Should handle invalid JSON"""
        from app.main import _get_service_state

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", MagicMock()):
                with patch("json.load", side_effect=Exception("Invalid JSON")):
                    state = _get_service_state()

        assert state["clean_shutdown"] is False

    def test_save_service_state(self):
        """Should save service state"""
        from app.main import _save_service_state

        with patch("pathlib.Path.mkdir"):
            with patch("builtins.open", MagicMock()):
                with patch("json.dump") as mock_dump:
                    _save_service_state(True)

        # Should have called json.dump


class TestLifespanEvents:
    """Tests for lifespan events"""

    async def test_lifespan_startup(self):
        """Should handle startup"""
        from fastapi import FastAPI

        from app.main import lifespan

        test_app = FastAPI()

        with patch("app.main._get_service_state", return_value={"clean_shutdown": True}):
            with patch("app.main._save_service_state"):
                with patch("app.main.settings.discord_bot_token", ""):
                    with patch("app.main.notification_manager") as mock_nm:
                        mock_nm.start_scheduler = AsyncMock()
                        mock_nm.stop_scheduler = AsyncMock()
                        mock_nm.broadcast_notification = AsyncMock(return_value={})

                        with patch("app.main.version_checker") as mock_vc:
                            mock_vc.start = AsyncMock()
                            mock_vc.stop = AsyncMock()

                            with patch("app.main.anomaly_detector") as mock_ad:
                                mock_ad.save = MagicMock()

                                with patch("app.main.discord_service") as mock_ds:
                                    mock_ds._running = False

                                    with patch(
                                        "app.main._send_cartographer_up_notification", AsyncMock()
                                    ):
                                        with patch(
                                            "app.main._send_cartographer_down_notification",
                                            AsyncMock(),
                                        ):
                                            with patch("app.main.SERVICE_STATE_FILE") as mock_path:
                                                mock_path.exists.return_value = False

                                                async with lifespan(test_app):
                                                    pass

    async def test_lifespan_shutdown(self):
        """Should handle shutdown"""
        from fastapi import FastAPI

        from app.main import lifespan

        test_app = FastAPI()

        with patch("app.main._get_service_state", return_value={"clean_shutdown": True}):
            with patch("app.main._save_service_state"):
                with patch("app.main.settings.discord_bot_token", ""):
                    with patch("app.main.notification_manager") as mock_nm:
                        mock_nm.start_scheduler = AsyncMock()
                        mock_nm.stop_scheduler = AsyncMock()
                        mock_nm.broadcast_notification = AsyncMock(return_value={})

                        with patch("app.main.version_checker") as mock_vc:
                            mock_vc.start = AsyncMock()
                            mock_vc.stop = AsyncMock()

                            with patch("app.main.anomaly_detector") as mock_ad:
                                mock_ad.save = MagicMock()

                                with patch("app.main.discord_service") as mock_ds:
                                    mock_ds._running = False

                                    with patch(
                                        "app.main._send_cartographer_up_notification", AsyncMock()
                                    ):
                                        with patch(
                                            "app.main._send_cartographer_down_notification",
                                            AsyncMock(),
                                        ):
                                            with patch("app.main.SERVICE_STATE_FILE") as mock_path:
                                                mock_path.exists.return_value = False

                                                async with lifespan(test_app):
                                                    pass


class TestNotificationFunctions:
    """Tests for notification helper functions"""

    async def test_send_cartographer_up_notification(self):
        """Should send cartographer up notification"""
        from app.main import _send_cartographer_up_notification

        with patch("app.main.cartographer_status_service") as mock_css:
            with patch("app.services.email_service.is_email_configured", return_value=True):
                with patch(
                    "app.services.email_service.send_notification_email", new_callable=AsyncMock
                ) as mock_send:
                    mock_css.get_subscribers_for_event.return_value = []

                    await _send_cartographer_up_notification({"clean_shutdown": True})

        mock_css.get_subscribers_for_event.assert_called_once()

    async def test_send_cartographer_up_notification_with_downtime(self):
        """Should include downtime in notification"""
        from datetime import datetime, timedelta

        from app.main import _send_cartographer_up_notification

        past_time = (datetime.utcnow() - timedelta(minutes=30)).isoformat()

        with patch("app.main.cartographer_status_service") as mock_css:
            with patch("app.services.email_service.is_email_configured", return_value=True):
                with patch(
                    "app.services.email_service.send_notification_email", new_callable=AsyncMock
                ) as mock_send:
                    mock_css.get_subscribers_for_event.return_value = []

                    await _send_cartographer_up_notification(
                        {"clean_shutdown": True, "last_shutdown": past_time}
                    )

        mock_css.get_subscribers_for_event.assert_called_once()

    async def test_send_cartographer_down_notification(self):
        """Should send cartographer down notification"""
        from app.main import _send_cartographer_down_notification

        with patch("app.main.cartographer_status_service") as mock_css:
            with patch("app.services.email_service.is_email_configured", return_value=True):
                with patch(
                    "app.services.email_service.send_notification_email", new_callable=AsyncMock
                ) as mock_send:
                    mock_css.get_subscribers_for_event.return_value = []

                    await _send_cartographer_down_notification()

        mock_css.get_subscribers_for_event.assert_called_once()

    async def test_send_notification_error_handling(self):
        """Should handle errors gracefully"""
        from app.main import _send_cartographer_up_notification

        with patch("app.main.cartographer_status_service") as mock_css:
            mock_css.get_subscribers_for_event.side_effect = Exception("Error")

            # Should not raise
            await _send_cartographer_up_notification({})


class TestGlobalAppInstance:
    """Tests for global app instance"""

    def test_global_app_exists(self):
        """Should have a global app instance"""
        assert app is not None
        assert app.title == "Cartographer Notification Service"
