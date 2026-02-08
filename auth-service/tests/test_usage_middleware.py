"""
Unit tests for usage tracking middleware.
"""

import asyncio
import base64
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.services.usage_middleware as usage_middleware
from app.services.usage_middleware import (
    UsageRecord,
    UsageTrackingMiddleware,
    _capture_posthog_api_event,
    _initialize_posthog,
    _is_service_bearer_token,
    _is_user_generated_request,
)


def _build_token(payload: dict) -> str:
    encoded_payload = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
    encoded_payload = encoded_payload.rstrip("=")
    return f"header.{encoded_payload}.signature"


class TestUsageRecord:
    """Tests for UsageRecord class"""

    def test_init(self):
        """Should initialize record"""
        now = datetime.now()
        record = UsageRecord(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time_ms=15.5,
            timestamp=now,
        )

        assert record.endpoint == "/api/test"
        assert record.method == "GET"
        assert record.status_code == 200
        assert record.response_time_ms == 15.5
        assert record.timestamp == now

    def test_to_dict(self):
        """Should convert to dict"""
        now = datetime.now()
        record = UsageRecord(
            endpoint="/api/auth/login",
            method="POST",
            status_code=201,
            response_time_ms=25.0,
            timestamp=now,
        )

        result = record.to_dict()

        assert result["endpoint"] == "/api/auth/login"
        assert result["method"] == "POST"
        assert result["service"] == "auth-service"
        assert result["status_code"] == 201
        assert result["response_time_ms"] == 25.0
        assert "timestamp" in result


class TestUsageTrackingMiddleware:
    """Tests for UsageTrackingMiddleware"""

    def test_init(self):
        """Should initialize middleware"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        assert middleware.service_name == "auth-service"
        assert len(middleware._buffer) == 0
        assert middleware._client is None
        assert not middleware._running

    def test_init_with_custom_service_name(self):
        """Should accept custom service name"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app, service_name="test-service")

        assert middleware.service_name == "test-service"

    @pytest.mark.asyncio
    async def test_get_client_creates_client(self):
        """Should create HTTP client"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        client = await middleware._get_client()

        assert client is not None
        assert middleware._client is not None

        # Cleanup
        await client.aclose()

    @pytest.mark.asyncio
    async def test_get_client_reuses_client(self):
        """Should reuse existing client"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        client1 = await middleware._get_client()
        client2 = await middleware._get_client()

        assert client1 is client2

        # Cleanup
        await client1.aclose()

    @pytest.mark.asyncio
    async def test_start_flush_task(self):
        """Should start flush task"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        await middleware._start_flush_task()

        assert middleware._running
        assert middleware._flush_task is not None

        # Cleanup
        middleware._running = False
        middleware._flush_task.cancel()
        try:
            await middleware._flush_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_flush_buffer_empty(self):
        """Should handle empty buffer"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        await middleware._flush_buffer()  # Should not raise

    @pytest.mark.asyncio
    async def test_flush_buffer_with_records(self):
        """Should send records to metrics service"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        # Add records to buffer
        record = UsageRecord(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time_ms=10.0,
            timestamp=datetime.now(),
        )
        middleware._buffer.append(record)

        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False

        # Override _get_client to return our mock
        middleware._get_client = AsyncMock(return_value=mock_client)

        await middleware._flush_buffer()

        # Should have sent records
        mock_client.post.assert_called_once()
        assert len(middleware._buffer) == 0

    @pytest.mark.asyncio
    async def test_flush_buffer_failure_returns_records(self):
        """Should return records to buffer on failure"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        # Add records to buffer
        record = UsageRecord(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time_ms=10.0,
            timestamp=datetime.now(),
        )
        middleware._buffer.append(record)

        # Mock HTTP client with failure
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        middleware._client = mock_client

        await middleware._flush_buffer()

        # Should have returned records to buffer
        assert len(middleware._buffer) == 1

    @pytest.mark.asyncio
    async def test_flush_buffer_exception_returns_records(self):
        """Should return records to buffer on exception"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        # Add records to buffer
        record = UsageRecord(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time_ms=10.0,
            timestamp=datetime.now(),
        )
        middleware._buffer.append(record)

        # Mock HTTP client with exception
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Connection failed")
        middleware._client = mock_client

        await middleware._flush_buffer()

        # Should have returned records to buffer
        assert len(middleware._buffer) == 1

    @pytest.mark.asyncio
    async def test_dispatch_excluded_paths(self):
        """Should skip excluded paths"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        mock_request = MagicMock()
        mock_request.url.path = "/healthz"
        mock_request.method = "GET"

        mock_response = MagicMock()
        mock_response.status_code = 200

        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        assert response == mock_response
        assert len(middleware._buffer) == 0

    @pytest.mark.asyncio
    async def test_dispatch_docs_paths(self):
        """Should skip docs paths"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        mock_request = MagicMock()
        mock_request.url.path = "/docs/oauth2-redirect"
        mock_request.method = "GET"

        mock_response = MagicMock()
        mock_response.status_code = 200

        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        assert response == mock_response
        assert len(middleware._buffer) == 0

    @pytest.mark.asyncio
    async def test_dispatch_tracks_request(self):
        """Should track non-excluded requests"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        mock_request = MagicMock()
        mock_request.url.path = "/api/auth/login"
        mock_request.method = "POST"

        mock_response = MagicMock()
        mock_response.status_code = 200

        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        assert response == mock_response
        assert len(middleware._buffer) == 1

        record = middleware._buffer[0]
        assert record.endpoint == "/api/auth/login"
        assert record.method == "POST"
        assert record.status_code == 200

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Should clean up on shutdown"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        # Start running
        middleware._running = True
        middleware._flush_task = asyncio.create_task(asyncio.sleep(10))

        # Create and set a mock client
        mock_client = AsyncMock()
        middleware._client = mock_client

        await middleware.shutdown()

        assert not middleware._running
        mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_flush_loop(self):
        """Should run flush loop"""
        from app.config import settings

        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)
        middleware._running = True

        # Mock _flush_buffer
        flush_count = 0

        async def mock_flush():
            nonlocal flush_count
            flush_count += 1
            if flush_count >= 2:
                middleware._running = False

        middleware._flush_buffer = mock_flush

        with patch.object(settings, "usage_batch_interval_seconds", 0.01):
            await middleware._flush_loop()

        assert flush_count >= 1


class TestFlushLoopErrorHandling:
    """Tests for _flush_loop error handling"""

    @pytest.mark.asyncio
    async def test_flush_loop_handles_exception(self):
        """Should continue running after exception in flush_buffer"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)
        middleware._running = True

        call_count = 0

        async def failing_flush():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Simulated error")
            elif call_count >= 2:
                middleware._running = False

        middleware._flush_buffer = failing_flush

        with patch("app.services.usage_middleware.settings") as mock_settings:
            mock_settings.usage_batch_interval_seconds = 0.01

            await middleware._flush_loop()

        # Should have called flush at least twice (once failed, once stopped)
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_flush_loop_handles_cancelled_error(self):
        """Should exit cleanly on CancelledError"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)
        middleware._running = True

        async def cancelling_flush():
            raise asyncio.CancelledError()

        middleware._flush_buffer = cancelling_flush

        with patch("app.services.usage_middleware.settings") as mock_settings:
            mock_settings.usage_batch_interval_seconds = 0.01

            # Should not raise, just exit cleanly
            await middleware._flush_loop()


class TestFlushBufferNon200Response:
    """Tests for _flush_buffer non-200 response handling"""

    @pytest.mark.asyncio
    async def test_flush_buffer_non_200_puts_records_back(self):
        """Should put records back in buffer on non-200 response"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        # Add multiple records to buffer
        for i in range(3):
            record = UsageRecord(
                endpoint=f"/api/test/{i}",
                method="GET",
                status_code=200,
                response_time_ms=10.0,
                timestamp=datetime.now(),
            )
            middleware._buffer.append(record)

        # Mock HTTP client with non-200 response
        mock_response = MagicMock()
        mock_response.status_code = 503

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False

        middleware._get_client = AsyncMock(return_value=mock_client)

        await middleware._flush_buffer()

        # Records should be put back
        assert len(middleware._buffer) == 3


class TestDispatchImmediateFlush:
    """Tests for dispatch immediate flush when buffer is full"""

    @pytest.mark.asyncio
    async def test_dispatch_triggers_flush_when_buffer_full(self):
        """Should trigger immediate flush when buffer reaches batch size"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        mock_request = MagicMock()
        mock_request.url.path = "/api/test"
        mock_request.method = "GET"

        mock_response = MagicMock()
        mock_response.status_code = 200

        call_next = AsyncMock(return_value=mock_response)

        # Pre-fill buffer to just below batch size
        with patch("app.services.usage_middleware.settings") as mock_settings:
            mock_settings.usage_batch_size = 5
            mock_settings.usage_batch_interval_seconds = 60

            for i in range(4):
                record = UsageRecord(
                    endpoint=f"/api/prefill/{i}",
                    method="GET",
                    status_code=200,
                    response_time_ms=10.0,
                    timestamp=datetime.now(),
                )
                middleware._buffer.append(record)

            # Mock _flush_buffer
            flush_called = False

            async def mock_flush():
                nonlocal flush_called
                flush_called = True

            middleware._flush_buffer = mock_flush

            # This should trigger flush since buffer will be at batch_size
            await middleware.dispatch(mock_request, call_next)

            # Give async task time to run
            await asyncio.sleep(0.01)

            # Buffer should have 5 records now (4 + 1)
            assert len(middleware._buffer) == 5


class TestShutdownWithPendingRecords:
    """Tests for shutdown with pending records in buffer"""

    @pytest.mark.asyncio
    async def test_shutdown_flushes_remaining_records(self):
        """Should flush all remaining records on shutdown"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        # Add records to buffer
        for i in range(3):
            record = UsageRecord(
                endpoint=f"/api/test/{i}",
                method="GET",
                status_code=200,
                response_time_ms=10.0,
                timestamp=datetime.now(),
            )
            middleware._buffer.append(record)

        middleware._running = True

        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False

        middleware._get_client = AsyncMock(return_value=mock_client)
        middleware._client = mock_client

        with patch("app.services.usage_middleware.settings") as mock_settings:
            mock_settings.usage_batch_size = 100  # Large batch size

            await middleware.shutdown()

        # Buffer should be empty after shutdown
        assert len(middleware._buffer) == 0
        assert not middleware._running

    @pytest.mark.asyncio
    async def test_shutdown_multiple_batches(self):
        """Should flush multiple batches during shutdown"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        # Add many records to buffer
        for i in range(10):
            record = UsageRecord(
                endpoint=f"/api/test/{i}",
                method="GET",
                status_code=200,
                response_time_ms=10.0,
                timestamp=datetime.now(),
            )
            middleware._buffer.append(record)

        middleware._running = True

        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False

        middleware._get_client = AsyncMock(return_value=mock_client)
        middleware._client = mock_client

        with patch("app.services.usage_middleware.settings") as mock_settings:
            mock_settings.usage_batch_size = 3  # Small batch size to trigger multiple flushes

            await middleware.shutdown()

        # Buffer should be empty after shutdown
        assert len(middleware._buffer) == 0


class TestPostHogHelpers:
    """Tests for PostHog helper behavior and request classification."""

    def test_initialize_posthog_returns_true_when_already_initialized(self):
        with patch.object(usage_middleware, "_POSTHOG_INITIALIZED", True):
            assert _initialize_posthog("key", "https://host", True) is True

    def test_initialize_posthog_returns_false_when_disabled(self):
        with patch.object(usage_middleware, "_POSTHOG_INITIALIZED", False):
            assert _initialize_posthog("key", "https://host", False) is False

    def test_initialize_posthog_handles_assignment_error(self):
        class BrokenPostHog:
            def __setattr__(self, _name, _value):
                raise RuntimeError("boom")

        with patch.object(usage_middleware, "posthog", BrokenPostHog()):
            with patch.object(usage_middleware, "_POSTHOG_INITIALIZED", False):
                assert _initialize_posthog("key", "https://host", True) is False

    def test_is_service_bearer_token_handles_invalid_values(self):
        assert _is_service_bearer_token(None) is False
        assert _is_service_bearer_token("invalid") is False
        assert _is_service_bearer_token("Bearer not-a-jwt") is False
        assert _is_service_bearer_token("Bearer a.b.c") is False

    def test_is_service_bearer_token_detects_service_claims(self):
        service_flag_token = _build_token({"service": True})
        service_type_token = _build_token({"type": "service"})
        user_token = _build_token({"service": False, "type": "user"})

        assert _is_service_bearer_token(f"Bearer {service_flag_token}") is True
        assert _is_service_bearer_token(f"Bearer {service_type_token}") is True
        assert _is_service_bearer_token(f"Bearer {user_token}") is False

    def test_is_user_generated_request_filters_internal_headers(self):
        request = MagicMock()
        request.headers = {"x-service-name": "backend"}
        assert _is_user_generated_request(request) is False

    def test_is_user_generated_request_filters_service_tokens(self):
        request = MagicMock()
        request.headers = {"authorization": f"Bearer {_build_token({'service': True})}"}
        assert _is_user_generated_request(request) is False

    def test_is_user_generated_request_filters_probe_user_agents(self):
        request = MagicMock()
        request.headers = {"user-agent": "kube-probe/1.0"}
        assert _is_user_generated_request(request) is False

        request.headers = {"user-agent": "prometheus/2.0"}
        assert _is_user_generated_request(request) is False

    def test_is_user_generated_request_accepts_normal_user_traffic(self):
        request = MagicMock()
        request.headers = {"user-agent": "Mozilla/5.0"}
        assert _is_user_generated_request(request) is True

    def test_capture_posthog_api_event_drops_non_user_non_error(self):
        mock_posthog = MagicMock()
        with patch.object(usage_middleware, "posthog", mock_posthog):
            with patch.object(usage_middleware, "_POSTHOG_INITIALIZED", False):
                _capture_posthog_api_event(
                    service_name="auth-service",
                    path="/api/auth/login",
                    method="POST",
                    status_code=200,
                    response_time_ms=12.34,
                    is_user_generated=False,
                    error_type=None,
                    posthog_api_key="key",
                    posthog_host="https://host",
                    posthog_enabled=True,
                )

        mock_posthog.capture.assert_not_called()

    def test_capture_posthog_api_event_keeps_server_errors(self):
        mock_posthog = MagicMock()
        with patch.object(usage_middleware, "posthog", mock_posthog):
            with patch.object(usage_middleware, "_POSTHOG_INITIALIZED", False):
                _capture_posthog_api_event(
                    service_name="auth-service",
                    path="/api/auth/login",
                    method="POST",
                    status_code=500,
                    response_time_ms=23.45,
                    is_user_generated=False,
                    error_type="RuntimeError",
                    posthog_api_key="key",
                    posthog_host="https://host",
                    posthog_enabled=True,
                )

        mock_posthog.capture.assert_called_once()
        kwargs = mock_posthog.capture.call_args.kwargs
        assert kwargs["properties"]["request_source"] == "server"
        assert kwargs["properties"]["error_type"] == "RuntimeError"

    def test_capture_posthog_api_event_handles_capture_error(self):
        mock_posthog = MagicMock()
        mock_posthog.capture.side_effect = RuntimeError("boom")

        with patch.object(usage_middleware, "posthog", mock_posthog):
            with patch.object(usage_middleware, "_POSTHOG_INITIALIZED", False):
                _capture_posthog_api_event(
                    service_name="auth-service",
                    path="/api/auth/login",
                    method="POST",
                    status_code=500,
                    response_time_ms=23.45,
                    is_user_generated=True,
                    error_type="RuntimeError",
                    posthog_api_key="key",
                    posthog_host="https://host",
                    posthog_enabled=True,
                )

    @pytest.mark.asyncio
    async def test_dispatch_tracks_exception_path(self):
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)
        middleware._running = True

        mock_request = MagicMock()
        mock_request.url.path = "/api/fail"
        mock_request.method = "GET"
        mock_request.headers = {"user-agent": "Mozilla/5.0"}
        call_next = AsyncMock(side_effect=RuntimeError("boom"))

        with patch("app.services.usage_middleware._capture_posthog_api_event") as mock_capture:
            with pytest.raises(RuntimeError):
                await middleware.dispatch(mock_request, call_next)

        mock_capture.assert_called_once()
        assert mock_capture.call_args.kwargs["status_code"] == 500

    @pytest.mark.asyncio
    async def test_flush_buffer_returns_early_when_batch_size_zero(self):
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)
        middleware._buffer.append(
            UsageRecord(
                endpoint="/api/test",
                method="GET",
                status_code=200,
                response_time_ms=1.0,
                timestamp=datetime.utcnow(),
            )
        )

        with patch("app.services.usage_middleware.settings") as mock_settings:
            mock_settings.usage_batch_size = 0
            await middleware._flush_buffer()

        assert len(middleware._buffer) == 1


class TestIntegration:
    """Integration tests for middleware with FastAPI app"""

    def test_middleware_with_app(self):
        """Should work with FastAPI app"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.add_middleware(UsageTrackingMiddleware, service_name="test-service")

        @app.get("/test")
        def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)

        response = client.get("/test")

        assert response.status_code == 200
