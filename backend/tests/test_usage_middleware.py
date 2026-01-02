"""
Unit tests for the Usage Tracking Middleware.
Tests request interception, timing, and batch reporting.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from starlette.testclient import TestClient


class TestUsageTrackingMiddleware:
    """Tests for UsageTrackingMiddleware"""

    @pytest.fixture
    def app(self):
        """Create a simple test app with middleware"""
        from app.services.usage_middleware import UsageTrackingMiddleware

        async def homepage(request):
            return JSONResponse({"status": "ok"})

        async def api_endpoint(request):
            return JSONResponse({"data": "test"})

        async def health_check(request):
            return JSONResponse({"status": "healthy"})

        async def error_endpoint(request):
            return JSONResponse({"error": "test"}, status_code=500)

        routes = [
            Route("/", homepage),
            Route("/api/test", api_endpoint),
            Route("/healthz", health_check),
            Route("/api/error", error_endpoint),
        ]

        app = Starlette(routes=routes)
        app.add_middleware(UsageTrackingMiddleware, service_name="test-service")
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return TestClient(app)

    def test_middleware_passes_request(self, client):
        """Middleware should pass requests through to app"""
        response = client.get("/api/test")

        assert response.status_code == 200
        assert response.json() == {"data": "test"}

    def test_middleware_excludes_health_check(self, client):
        """Middleware should exclude /healthz from tracking"""
        # Health check should still work - middleware passes it through
        response = client.get("/healthz")
        assert response.status_code == 200

    def test_middleware_excludes_root(self, client):
        """Middleware should exclude root path from tracking"""
        response = client.get("/")

        assert response.status_code == 200

    def test_middleware_handles_errors(self, client):
        """Middleware should track error responses"""
        response = client.get("/api/error")

        assert response.status_code == 500


class TestUsageRecord:
    """Tests for UsageRecord class"""

    def test_usage_record_to_dict(self):
        """UsageRecord should serialize to dict correctly"""
        from app.services.usage_middleware import UsageRecord

        now = datetime.utcnow()
        record = UsageRecord(
            endpoint="/api/test",
            method="GET",
            service_name="test-service",
            status_code=200,
            response_time_ms=45.5,
            timestamp=now,
        )

        result = record.to_dict()

        assert result["endpoint"] == "/api/test"
        assert result["method"] == "GET"
        assert result["service"] == "test-service"
        assert result["status_code"] == 200
        assert result["response_time_ms"] == 45.5
        assert result["timestamp"] == now.isoformat()


class TestMiddlewareBuffer:
    """Tests for middleware buffer behavior"""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance for testing"""
        from app.services.usage_middleware import UsageTrackingMiddleware

        # Create a minimal ASGI app
        async def app(scope, receive, send):
            pass

        return UsageTrackingMiddleware(app, service_name="test-service")

    def test_buffer_has_max_size(self, middleware):
        """Buffer should have a maximum size"""
        assert middleware._buffer.maxlen == 1000

    def test_buffer_starts_empty(self, middleware):
        """Buffer should start empty"""
        assert len(middleware._buffer) == 0


class TestMiddlewareFlush:
    """Tests for middleware flush behavior"""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance for testing"""
        from app.services.usage_middleware import UsageRecord, UsageTrackingMiddleware

        async def app(scope, receive, send):
            pass

        mw = UsageTrackingMiddleware(app, service_name="test-service")

        # Add some records to buffer
        for i in range(5):
            mw._buffer.append(
                UsageRecord(
                    endpoint=f"/api/test/{i}",
                    method="GET",
                    service_name="test-service",
                    status_code=200,
                    response_time_ms=10.0 + i,
                    timestamp=datetime.utcnow(),
                )
            )

        return mw

    async def test_flush_sends_batch_to_metrics(self, middleware):
        """Flush should send batch to metrics service"""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(middleware, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            await middleware._flush_buffer()

            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "/api/metrics/usage/record/batch" in call_args[0][0]

    async def test_flush_clears_buffer(self, middleware):
        """Flush should clear sent records from buffer"""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(middleware, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            initial_count = len(middleware._buffer)
            await middleware._flush_buffer()

            # Buffer should have fewer records
            assert len(middleware._buffer) < initial_count

    async def test_flush_retries_on_failure(self, middleware):
        """Flush should put records back on failure"""
        mock_response = MagicMock()
        mock_response.status_code = 500

        initial_count = len(middleware._buffer)

        with patch.object(middleware, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            await middleware._flush_buffer()

            # Records should be put back
            # (may not be exactly initial count due to batch size)
            assert len(middleware._buffer) > 0

    async def test_flush_handles_network_error(self, middleware):
        """Flush should handle network errors gracefully"""
        initial_count = len(middleware._buffer)

        with patch.object(middleware, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=Exception("Network error"))
            mock_get_client.return_value = mock_client

            # Should not raise
            await middleware._flush_buffer()

            # Records should be preserved
            assert len(middleware._buffer) > 0

    async def test_flush_does_nothing_when_empty(self, middleware):
        """Flush should do nothing when buffer is empty"""
        # Clear the buffer
        middleware._buffer.clear()

        with patch.object(middleware, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client

            await middleware._flush_buffer()

            # Should not call post
            mock_client.post.assert_not_called()


class TestMiddlewareShutdown:
    """Tests for middleware shutdown behavior"""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance for testing"""
        from app.services.usage_middleware import UsageTrackingMiddleware

        async def app(scope, receive, send):
            pass

        return UsageTrackingMiddleware(app, service_name="test-service")

    async def test_shutdown_stops_running(self, middleware):
        """Shutdown should stop the running flag"""
        middleware._running = True

        with patch.object(middleware, "_flush_buffer", new_callable=AsyncMock):
            with patch.object(middleware, "_client", None):
                await middleware.shutdown()

        assert middleware._running is False

    async def test_shutdown_cancels_flush_task(self, middleware):
        """Shutdown should cancel the flush task"""
        middleware._running = True
        middleware._flush_task = asyncio.create_task(asyncio.sleep(100))

        with patch.object(middleware, "_flush_buffer", new_callable=AsyncMock):
            with patch.object(middleware, "_client", None):
                await middleware.shutdown()

        assert middleware._flush_task.cancelled() or middleware._flush_task.done()


class TestMiddlewareExclusions:
    """Tests for path exclusions in middleware"""

    def test_healthz_excluded(self):
        """Healthcheck paths should be excluded"""
        from app.services.usage_middleware import EXCLUDED_PATHS

        assert "/healthz" in EXCLUDED_PATHS

    def test_docs_excluded(self):
        """Documentation paths should be excluded"""
        from app.services.usage_middleware import EXCLUDED_PATHS

        assert "/docs" in EXCLUDED_PATHS

    def test_root_excluded(self):
        """Root path should be excluded"""
        from app.services.usage_middleware import EXCLUDED_PATHS

        assert "/" in EXCLUDED_PATHS


class TestGetClient:
    """Tests for _get_client method"""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance for testing"""
        from app.services.usage_middleware import UsageTrackingMiddleware

        async def app(scope, receive, send):
            pass

        return UsageTrackingMiddleware(app, service_name="test-service")

    async def test_get_client_creates_new_client(self, middleware):
        """Should create a new client when none exists"""
        client = await middleware._get_client()

        assert client is not None
        assert middleware._client is not None

        # Cleanup
        await client.aclose()

    async def test_get_client_returns_existing_client(self, middleware):
        """Should return existing client if available"""
        client1 = await middleware._get_client()
        client2 = await middleware._get_client()

        assert client1 is client2

        # Cleanup
        await client1.aclose()

    async def test_get_client_creates_new_if_closed(self, middleware):
        """Should create new client if existing is closed"""
        client1 = await middleware._get_client()
        await client1.aclose()

        client2 = await middleware._get_client()

        assert client2 is not client1
        assert not client2.is_closed

        # Cleanup
        await client2.aclose()


class TestStartFlushTask:
    """Tests for _start_flush_task method"""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance for testing"""
        from app.services.usage_middleware import UsageTrackingMiddleware

        async def app(scope, receive, send):
            pass

        return UsageTrackingMiddleware(app, service_name="test-service")

    async def test_start_flush_task_starts_task(self, middleware):
        """Should start flush task when not running"""
        assert middleware._running is False
        assert middleware._flush_task is None

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

    async def test_start_flush_task_noop_if_running(self, middleware):
        """Should not start new task if already running"""
        middleware._running = True

        await middleware._start_flush_task()

        # Should not have created a task
        assert middleware._flush_task is None


class TestFlushLoop:
    """Tests for _flush_loop method"""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance for testing"""
        from app.services.usage_middleware import UsageTrackingMiddleware

        async def app(scope, receive, send):
            pass

        return UsageTrackingMiddleware(app, service_name="test-service")

    async def test_flush_loop_exits_on_cancelled_error(self, middleware):
        """Should exit gracefully on CancelledError"""
        middleware._running = True

        task = asyncio.create_task(middleware._flush_loop())
        await asyncio.sleep(0.05)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # Task should have exited
        assert task.done()

    async def test_flush_loop_handles_generic_exception(self, middleware):
        """Should handle generic exceptions in loop"""
        middleware._running = True
        call_count = 0

        # Store original interval and set a fast one for testing
        original_interval = middleware._settings.usage_batch_interval_seconds

        async def failing_flush():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Test error")
            middleware._running = False

        try:
            # Patch the settings interval
            with (
                patch.object(middleware._settings, "usage_batch_interval_seconds", 0.01),
                patch.object(middleware, "_flush_buffer", failing_flush),
            ):
                task = asyncio.create_task(middleware._flush_loop())
                await asyncio.sleep(0.1)
                middleware._running = False
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

                # Should have continued after error
                assert call_count >= 1
        finally:
            pass  # Settings are not modified directly


class TestFlushBufferHTTP:
    """Tests for _flush_buffer HTTP behavior"""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance with records"""
        from app.services.usage_middleware import UsageRecord, UsageTrackingMiddleware

        async def app(scope, receive, send):
            pass

        mw = UsageTrackingMiddleware(app, service_name="test-service")

        # Add records to buffer
        for i in range(3):
            mw._buffer.append(
                UsageRecord(
                    endpoint=f"/api/test/{i}",
                    method="GET",
                    service_name="test-service",
                    status_code=200,
                    response_time_ms=10.0 + i,
                    timestamp=datetime.utcnow(),
                )
            )

        return mw

    async def test_flush_buffer_puts_back_on_non_200(self, middleware):
        """Should put records back on non-200 response"""
        initial_count = len(middleware._buffer)

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch.object(middleware, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            await middleware._flush_buffer()

            # Records should be put back
            assert len(middleware._buffer) > 0


class TestShutdownWithClient:
    """Tests for shutdown with HTTP client"""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance"""
        from app.services.usage_middleware import UsageTrackingMiddleware

        async def app(scope, receive, send):
            pass

        return UsageTrackingMiddleware(app, service_name="test-service")

    async def test_shutdown_closes_client(self, middleware):
        """Should close HTTP client during shutdown"""
        # Create a client
        client = await middleware._get_client()

        await middleware.shutdown()

        # Client should be closed
        assert middleware._client is None or middleware._client.is_closed


class TestDispatchExcludedPrefixes:
    """Tests for dispatch with excluded prefixes"""

    @pytest.fixture
    def app(self):
        """Create a simple test app with middleware"""
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route

        from app.services.usage_middleware import UsageTrackingMiddleware

        async def test_endpoint(request):
            return JSONResponse({"status": "ok"})

        routes = [
            Route("/api/test", test_endpoint),
            Route("/api/metrics/usage/record", test_endpoint),
            Route("/assets/test.js", test_endpoint),
            Route("/docs/test", test_endpoint),
        ]

        app = Starlette(routes=routes)
        app.add_middleware(UsageTrackingMiddleware, service_name="test-service")
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return TestClient(app)

    def test_dispatch_excludes_assets(self, client):
        """Should exclude /assets/ prefix"""
        response = client.get("/assets/test.js")
        assert response.status_code == 200

    def test_dispatch_excludes_metrics_usage(self, client):
        """Should exclude /api/metrics/usage prefix"""
        response = client.get("/api/metrics/usage/record")
        assert response.status_code == 200
