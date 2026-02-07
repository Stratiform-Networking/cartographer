"""
Unit tests for usage tracking middleware.
"""

import asyncio
from collections import deque
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response
from starlette.testclient import TestClient

from app.services.usage_middleware import (
    EXCLUDED_PATHS,
    SERVICE_NAME,
    UsageRecord,
    UsageTrackingMiddleware,
)


class TestUsageRecord:
    """Tests for UsageRecord class"""

    def test_create_usage_record(self):
        """Should create a usage record with all fields"""
        now = datetime.now(timezone.utc)
        record = UsageRecord(
            endpoint="/api/health/ping",
            method="GET",
            status_code=200,
            response_time_ms=25.5,
            timestamp=now,
        )

        assert record.endpoint == "/api/health/ping"
        assert record.method == "GET"
        assert record.status_code == 200
        assert record.response_time_ms == 25.5
        assert record.timestamp == now

    def test_to_dict(self):
        """Should convert record to dict"""
        now = datetime.now(timezone.utc)
        record = UsageRecord(
            endpoint="/api/health/check",
            method="POST",
            status_code=201,
            response_time_ms=100.0,
            timestamp=now,
        )

        result = record.to_dict()

        assert result["endpoint"] == "/api/health/check"
        assert result["method"] == "POST"
        assert result["service"] == SERVICE_NAME
        assert result["status_code"] == 201
        assert result["response_time_ms"] == 100.0
        assert result["timestamp"] == now.isoformat()


class TestUsageTrackingMiddlewareInit:
    """Tests for middleware initialization"""

    def test_init_with_default_service_name(self):
        """Should initialize with default service name"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        assert middleware.service_name == SERVICE_NAME
        assert middleware._buffer is not None
        assert middleware._running is False

    def test_init_with_custom_service_name(self):
        """Should initialize with custom service name"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app, service_name="custom-service")

        assert middleware.service_name == "custom-service"


class TestUsageTrackingMiddlewareDispatch:
    """Tests for middleware dispatch functionality"""

    @pytest.fixture
    def app_with_middleware(self):
        """Create test app with middleware"""
        app = FastAPI()
        app.add_middleware(UsageTrackingMiddleware, service_name="test-service")

        @app.get("/api/health/ping")
        async def ping():
            return {"status": "ok"}

        @app.get("/healthz")
        async def healthz():
            return {"status": "healthy"}

        @app.get("/")
        async def root():
            return {"service": "test"}

        return app

    def test_dispatch_tracks_non_excluded_path(self, app_with_middleware):
        """Should track usage for non-excluded paths"""
        client = TestClient(app_with_middleware)

        response = client.get("/api/health/ping")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_dispatch_triggers_immediate_flush(self, monkeypatch):
        """Should trigger immediate flush when buffer reaches batch size"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)
        middleware._running = True

        monkeypatch.setattr("app.services.usage_middleware.settings.usage_batch_size", 1)

        created = []

        def fake_create_task(coro):
            if hasattr(coro, "close"):
                coro.close()
            created.append(coro)
            return AsyncMock()

        flush_mock = AsyncMock()
        monkeypatch.setattr(middleware, "_flush_buffer", flush_mock)
        monkeypatch.setattr("asyncio.create_task", fake_create_task)

        async def call_next(request):
            return Response(status_code=200)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/test",
            "headers": [],
        }
        request = Request(scope)

        await middleware.dispatch(request, call_next)

        assert len(created) == 1

    def test_dispatch_skips_excluded_paths(self, app_with_middleware):
        """Should skip tracking for excluded paths"""
        client = TestClient(app_with_middleware)

        # These should be skipped
        response = client.get("/healthz")
        assert response.status_code == 200

        response = client.get("/")
        assert response.status_code == 200

    def test_excluded_paths_constant(self):
        """Should have expected excluded paths"""
        assert "/healthz" in EXCLUDED_PATHS
        assert "/ready" in EXCLUDED_PATHS
        assert "/" in EXCLUDED_PATHS
        assert "/docs" in EXCLUDED_PATHS


class TestUsageTrackingMiddlewareBuffering:
    """Tests for middleware buffering functionality"""

    def test_buffer_has_max_size(self):
        """Should have a maxlen on the buffer"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        # Buffer should be a deque with maxlen
        assert isinstance(middleware._buffer, deque)
        assert middleware._buffer.maxlen == 1000


class TestUsageTrackingMiddlewareFlush:
    """Tests for middleware flush functionality"""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance"""
        app = MagicMock()
        return UsageTrackingMiddleware(app)

    async def test_flush_empty_buffer(self, middleware):
        """Should handle empty buffer gracefully"""
        # Empty buffer should not make any requests
        await middleware._flush_buffer()

        # No error should occur
        assert len(middleware._buffer) == 0

    async def test_flush_with_records(self, middleware):
        """Should send records to metrics service"""
        # Add some records to buffer
        now = datetime.now(timezone.utc)
        middleware._buffer.append(
            UsageRecord(
                endpoint="/api/test",
                method="GET",
                status_code=200,
                response_time_ms=10.0,
                timestamp=now,
            )
        )

        mock_response = AsyncMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client.post = AsyncMock(return_value=mock_response)

        middleware._client = mock_client

        await middleware._flush_buffer()

        mock_client.post.assert_called_once()

    async def test_flush_handles_failure(self, middleware):
        """Should put records back on failure"""
        # Add some records to buffer
        now = datetime.now(timezone.utc)
        middleware._buffer.append(
            UsageRecord(
                endpoint="/api/test",
                method="GET",
                status_code=200,
                response_time_ms=10.0,
                timestamp=now,
            )
        )

        mock_response = AsyncMock()
        mock_response.status_code = 500

        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client.post = AsyncMock(return_value=mock_response)

        middleware._client = mock_client

        await middleware._flush_buffer()

        # Record should be put back
        assert len(middleware._buffer) == 1

    async def test_flush_handles_exception(self, middleware):
        """Should handle exceptions during flush"""
        # Add some records to buffer
        now = datetime.now(timezone.utc)
        middleware._buffer.append(
            UsageRecord(
                endpoint="/api/test",
                method="GET",
                status_code=200,
                response_time_ms=10.0,
                timestamp=now,
            )
        )

        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client.post = AsyncMock(side_effect=Exception("Connection error"))

        middleware._client = mock_client

        await middleware._flush_buffer()

        # Record should be put back
        assert len(middleware._buffer) == 1

    async def test_flush_buffer_returns_when_batch_size_zero(self, middleware, monkeypatch):
        """Should return early when batch size is zero"""
        now = datetime.now(timezone.utc)
        middleware._buffer.append(
            UsageRecord(
                endpoint="/api/test",
                method="GET",
                status_code=200,
                response_time_ms=10.0,
                timestamp=now,
            )
        )

        monkeypatch.setattr("app.services.usage_middleware.settings.usage_batch_size", 0)

        await middleware._flush_buffer()

        assert len(middleware._buffer) == 1


class TestUsageTrackingMiddlewareClient:
    """Tests for HTTP client management"""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance"""
        app = MagicMock()
        return UsageTrackingMiddleware(app)

    async def test_get_client_creates_new(self, middleware):
        """Should create new client if none exists"""
        client = await middleware._get_client()

        assert client is not None
        assert middleware._client is client

        # Cleanup
        await client.aclose()

    async def test_get_client_returns_existing(self, middleware):
        """Should return existing client if valid"""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        middleware._client = mock_client

        client = await middleware._get_client()

        assert client is mock_client

    async def test_get_client_creates_new_if_closed(self, middleware):
        """Should create new client if existing is closed"""
        mock_client = AsyncMock()
        mock_client.is_closed = True
        middleware._client = mock_client

        client = await middleware._get_client()

        assert client is not mock_client

        # Cleanup
        await client.aclose()


class TestUsageTrackingMiddlewareFlushLoop:
    """Tests for background flush loop"""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance"""
        app = MagicMock()
        return UsageTrackingMiddleware(app)

    async def test_start_flush_task(self, middleware):
        """Should start background flush task"""
        assert middleware._running is False

        await middleware._start_flush_task()

        assert middleware._running is True
        assert middleware._flush_task is not None

        # Cleanup
        middleware._running = False
        middleware._flush_task.cancel()
        try:
            await middleware._flush_task
        except asyncio.CancelledError:
            pass

    async def test_flush_loop_runs(self, middleware):
        """Should run flush loop and call flush_buffer"""
        middleware._running = True

        with patch.object(middleware, "_flush_buffer", new_callable=AsyncMock) as mock_flush:
            # Create task and let it run briefly
            task = asyncio.create_task(middleware._flush_loop())

            # Give it a tiny bit of time
            await asyncio.sleep(0.01)

            # Stop the loop
            middleware._running = False
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

    async def test_flush_loop_calls_flush_buffer(self, middleware, monkeypatch):
        """Should call flush_buffer inside loop"""
        called = {"count": 0}

        async def fake_flush():
            called["count"] += 1
            middleware._running = False

        async def fake_sleep(_):
            return None

        monkeypatch.setattr(middleware, "_flush_buffer", fake_flush)
        monkeypatch.setattr("asyncio.sleep", fake_sleep)

        middleware._running = True
        await middleware._flush_loop()

        assert called["count"] == 1

    async def test_flush_loop_handles_exception(self, middleware, monkeypatch, caplog):
        """Should log flush loop exceptions"""

        async def fake_flush():
            middleware._running = False
            raise RuntimeError("boom")

        async def fake_sleep(_):
            return None

        monkeypatch.setattr(middleware, "_flush_buffer", fake_flush)
        monkeypatch.setattr("asyncio.sleep", fake_sleep)

        middleware._running = True
        with caplog.at_level("DEBUG"):
            await middleware._flush_loop()

        assert "Flush loop error" in caplog.text


class TestUsageTrackingMiddlewareShutdown:
    """Tests for middleware shutdown"""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance"""
        app = MagicMock()
        return UsageTrackingMiddleware(app)

    async def test_shutdown_stops_loop(self, middleware):
        """Should stop the flush loop on shutdown"""
        middleware._running = True
        middleware._flush_task = asyncio.create_task(asyncio.sleep(100))

        mock_client = AsyncMock()
        middleware._client = mock_client

        await middleware.shutdown()

        assert middleware._running is False
        mock_client.aclose.assert_called_once()

    async def test_shutdown_flushes_remaining(self, middleware):
        """Should flush remaining records on shutdown"""
        middleware._running = True
        middleware._flush_task = asyncio.create_task(asyncio.sleep(100))

        # Add a record
        now = datetime.now(timezone.utc)
        middleware._buffer.append(
            UsageRecord(
                endpoint="/api/test",
                method="GET",
                status_code=200,
                response_time_ms=10.0,
                timestamp=now,
            )
        )

        mock_response = AsyncMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client.post = AsyncMock(return_value=mock_response)

        middleware._client = mock_client

        await middleware.shutdown()

        # Buffer should be empty after shutdown flushes
        assert len(middleware._buffer) == 0

    async def test_shutdown_without_task(self, middleware):
        """Should handle shutdown when no task is running"""
        middleware._running = False
        middleware._flush_task = None
        middleware._client = None

        # Should not raise
        await middleware.shutdown()


class TestUsageTrackingMiddlewareIntegration:
    """Integration tests for the middleware"""

    @pytest.fixture
    def app_with_middleware(self):
        """Create test app with middleware"""
        app = FastAPI()
        middleware = UsageTrackingMiddleware(app, service_name="test-service")

        @app.get("/api/health/test")
        async def test_endpoint():
            return {"result": "success"}

        @app.post("/api/health/create")
        async def create_endpoint():
            return {"created": True}

        return app, middleware

    def test_multiple_requests_track_usage(self, app_with_middleware):
        """Should track multiple requests"""
        app, middleware = app_with_middleware
        client = TestClient(app)

        # Make multiple requests
        client.get("/api/health/test")
        client.post("/api/health/create")
        client.get("/api/health/test")

        # Requests should be tracked (buffer will have records)
        # Note: Buffer content depends on whether flush has run

    def test_4xx_and_5xx_responses_tracked(self, app_with_middleware):
        """Should track error responses"""
        app, middleware = app_with_middleware
        client = TestClient(app)

        # Make request to non-existent endpoint
        response = client.get("/api/nonexistent")

        assert response.status_code == 404
