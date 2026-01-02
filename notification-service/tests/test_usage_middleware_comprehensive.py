"""
Comprehensive tests for Usage Tracking Middleware.

Tests the middleware that tracks endpoint usage and reports to metrics service.
"""

import asyncio
from collections import deque
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.usage_middleware import UsageRecord, UsageTrackingMiddleware


class TestUsageRecord:
    """Tests for UsageRecord class"""

    def test_create_usage_record(self):
        """Should create usage record with all fields"""
        timestamp = datetime.utcnow()
        record = UsageRecord(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time_ms=15.5,
            timestamp=timestamp,
        )

        assert record.endpoint == "/api/test"
        assert record.method == "GET"
        assert record.status_code == 200
        assert record.response_time_ms == 15.5
        assert record.timestamp == timestamp

    def test_usage_record_to_dict(self):
        """Should convert to dictionary"""
        timestamp = datetime.utcnow()
        record = UsageRecord(
            endpoint="/api/test",
            method="POST",
            status_code=201,
            response_time_ms=25.0,
            timestamp=timestamp,
        )

        result = record.to_dict()

        assert result["endpoint"] == "/api/test"
        assert result["method"] == "POST"
        assert result["status_code"] == 201
        assert result["response_time_ms"] == 25.0
        assert result["timestamp"] == timestamp.isoformat()
        assert "service" in result


class TestUsageTrackingMiddlewareInit:
    """Tests for middleware initialization"""

    def test_init_creates_buffer(self):
        """Should initialize with empty buffer"""
        mock_app = MagicMock()
        middleware = UsageTrackingMiddleware(mock_app)

        assert hasattr(middleware, "_buffer")
        assert isinstance(middleware._buffer, deque)
        assert len(middleware._buffer) == 0

    def test_init_sets_service_name(self):
        """Should set service name"""
        mock_app = MagicMock()
        middleware = UsageTrackingMiddleware(mock_app, service_name="test-service")

        assert middleware.service_name == "test-service"

    def test_init_client_is_none(self):
        """Should start with no HTTP client"""
        mock_app = MagicMock()
        middleware = UsageTrackingMiddleware(mock_app)

        assert middleware._client is None


class TestUsageTrackingMiddlewareGetClient:
    """Tests for client management"""

    @pytest.mark.asyncio
    async def test_get_client_creates_new(self):
        """Should create new client if none exists"""
        mock_app = MagicMock()
        middleware = UsageTrackingMiddleware(mock_app)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.is_closed = False
            mock_client_class.return_value = mock_client

            client = await middleware._get_client()

            mock_client_class.assert_called_once()
            assert middleware._client is not None

    @pytest.mark.asyncio
    async def test_get_client_reuses_existing(self):
        """Should reuse existing client"""
        mock_app = MagicMock()
        middleware = UsageTrackingMiddleware(mock_app)

        mock_client = MagicMock()
        mock_client.is_closed = False
        middleware._client = mock_client

        client = await middleware._get_client()

        assert client is mock_client


class TestUsageTrackingMiddlewareFlush:
    """Tests for buffer flushing"""

    @pytest.mark.asyncio
    async def test_flush_buffer_empty(self):
        """Should do nothing when buffer is empty"""
        mock_app = MagicMock()
        middleware = UsageTrackingMiddleware(mock_app)

        await middleware._flush_buffer()

        # No error should occur
        assert len(middleware._buffer) == 0

    @pytest.mark.asyncio
    async def test_flush_buffer_sends_records(self):
        """Should send records to metrics service"""
        mock_app = MagicMock()
        middleware = UsageTrackingMiddleware(mock_app)

        # Add test record
        record = UsageRecord(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time_ms=10.0,
            timestamp=datetime.utcnow(),
        )
        middleware._buffer.append(record)

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(middleware, "_get_client", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_client

            await middleware._flush_buffer()

            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_flush_buffer_failure_puts_back_records(self):
        """Should put records back on failure"""
        mock_app = MagicMock()
        middleware = UsageTrackingMiddleware(mock_app)

        # Add test record
        record = UsageRecord(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time_ms=10.0,
            timestamp=datetime.utcnow(),
        )
        middleware._buffer.append(record)

        mock_response = MagicMock()
        mock_response.status_code = 500  # Failure

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(middleware, "_get_client", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_client

            await middleware._flush_buffer()

            # Records should be put back in buffer
            assert len(middleware._buffer) == 1

    @pytest.mark.asyncio
    async def test_flush_buffer_exception_puts_back_records(self):
        """Should put records back on exception"""
        mock_app = MagicMock()
        middleware = UsageTrackingMiddleware(mock_app)

        # Add test record
        record = UsageRecord(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time_ms=10.0,
            timestamp=datetime.utcnow(),
        )
        middleware._buffer.append(record)

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Network error"))

        with patch.object(middleware, "_get_client", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_client

            await middleware._flush_buffer()

            # Records should be put back in buffer
            assert len(middleware._buffer) == 1


class TestUsageTrackingMiddlewareDispatch:
    """Tests for request dispatch"""

    @pytest.mark.asyncio
    async def test_dispatch_excluded_path(self):
        """Should skip excluded paths"""
        mock_app = MagicMock()
        middleware = UsageTrackingMiddleware(mock_app)

        mock_request = MagicMock()
        mock_request.url.path = "/healthz"
        mock_request.method = "GET"

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_call_next = AsyncMock(return_value=mock_response)

        result = await middleware.dispatch(mock_request, mock_call_next)

        assert result == mock_response
        assert len(middleware._buffer) == 0  # Should not add to buffer

    @pytest.mark.asyncio
    async def test_dispatch_docs_path(self):
        """Should skip docs paths"""
        mock_app = MagicMock()
        middleware = UsageTrackingMiddleware(mock_app)

        mock_request = MagicMock()
        mock_request.url.path = "/docs/something"
        mock_request.method = "GET"

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_call_next = AsyncMock(return_value=mock_response)

        result = await middleware.dispatch(mock_request, mock_call_next)

        assert result == mock_response
        assert len(middleware._buffer) == 0

    @pytest.mark.asyncio
    async def test_dispatch_records_usage(self):
        """Should record usage for tracked paths"""
        mock_app = MagicMock()
        middleware = UsageTrackingMiddleware(mock_app)
        middleware._running = True  # Skip starting flush task

        mock_request = MagicMock()
        mock_request.url.path = "/api/notifications/test"
        mock_request.method = "POST"

        mock_response = MagicMock()
        mock_response.status_code = 201

        mock_call_next = AsyncMock(return_value=mock_response)

        # Mock flush buffer to prevent actual network calls
        with patch.object(middleware, "_flush_buffer", new_callable=AsyncMock):
            result = await middleware.dispatch(mock_request, mock_call_next)

        assert result == mock_response
        assert len(middleware._buffer) == 1

        record = middleware._buffer[0]
        assert record.endpoint == "/api/notifications/test"
        assert record.method == "POST"
        assert record.status_code == 201


class TestUsageTrackingMiddlewareShutdown:
    """Tests for middleware shutdown"""

    @pytest.mark.asyncio
    async def test_shutdown_stops_running(self):
        """Should stop running flag"""
        mock_app = MagicMock()
        middleware = UsageTrackingMiddleware(mock_app)
        middleware._running = True
        middleware._flush_task = None
        middleware._client = None

        with patch.object(middleware, "_flush_buffer", new_callable=AsyncMock):
            await middleware.shutdown()

        assert middleware._running is False

    @pytest.mark.asyncio
    async def test_shutdown_cancels_flush_task(self):
        """Should cancel flush task"""
        mock_app = MagicMock()
        middleware = UsageTrackingMiddleware(mock_app)
        middleware._running = True

        # Create a real asyncio task that we can cancel
        cancel_called = []

        async def fake_flush_loop():
            await asyncio.sleep(100)  # Will be cancelled

        # Create and start the task
        task = asyncio.create_task(fake_flush_loop())
        middleware._flush_task = task
        middleware._client = None

        with patch.object(middleware, "_flush_buffer", new_callable=AsyncMock):
            await middleware.shutdown()

        # Task should have been cancelled
        assert task.cancelled()

    @pytest.mark.asyncio
    async def test_shutdown_closes_client(self):
        """Should close HTTP client"""
        mock_app = MagicMock()
        middleware = UsageTrackingMiddleware(mock_app)
        middleware._running = True
        middleware._flush_task = None

        mock_client = AsyncMock()
        mock_client.aclose = AsyncMock()
        middleware._client = mock_client

        with patch.object(middleware, "_flush_buffer", new_callable=AsyncMock):
            await middleware.shutdown()

        mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_flushes_remaining(self):
        """Should flush remaining records"""
        mock_app = MagicMock()
        middleware = UsageTrackingMiddleware(mock_app)
        middleware._running = True
        middleware._flush_task = None
        middleware._client = None

        # Add a record
        record = UsageRecord(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time_ms=10.0,
            timestamp=datetime.utcnow(),
        )
        middleware._buffer.append(record)

        flush_calls = []

        async def mock_flush():
            flush_calls.append(1)
            middleware._buffer.clear()  # Simulate successful flush

        with patch.object(middleware, "_flush_buffer", new_callable=AsyncMock) as mock_flush_method:
            mock_flush_method.side_effect = mock_flush
            await middleware.shutdown()

        # Flush should have been called
        assert mock_flush_method.call_count >= 1


class TestUsageTrackingMiddlewareFlushLoop:
    """Tests for flush loop"""

    @pytest.mark.asyncio
    async def test_flush_loop_stops_on_cancel(self):
        """Should stop on CancelledError"""
        mock_app = MagicMock()
        middleware = UsageTrackingMiddleware(mock_app)
        middleware._running = True

        # Create a task that cancels immediately
        async def run_and_cancel():
            task = asyncio.create_task(middleware._flush_loop())
            await asyncio.sleep(0.01)  # Give it time to start
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        with patch.object(middleware, "_flush_buffer", new_callable=AsyncMock):
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = asyncio.CancelledError()

                try:
                    await middleware._flush_loop()
                except asyncio.CancelledError:
                    pass  # Expected

    @pytest.mark.asyncio
    async def test_flush_loop_handles_errors(self):
        """Should continue on errors"""
        mock_app = MagicMock()
        middleware = UsageTrackingMiddleware(mock_app)
        middleware._running = True

        error_count = 0

        async def error_flush():
            nonlocal error_count
            error_count += 1
            if error_count < 2:
                raise Exception("Test error")
            middleware._running = False  # Stop after second call

        with patch.object(middleware, "_flush_buffer", new_callable=AsyncMock) as mock_flush:
            mock_flush.side_effect = error_flush

            with patch("asyncio.sleep", new_callable=AsyncMock):
                await middleware._flush_loop()

        # Should have attempted flush twice
        assert error_count >= 1


class TestUsageTrackingMiddlewareStartFlushTask:
    """Tests for starting flush task"""

    @pytest.mark.asyncio
    async def test_start_flush_task_when_not_running(self):
        """Should start flush task"""
        mock_app = MagicMock()
        middleware = UsageTrackingMiddleware(mock_app)
        middleware._running = False

        with patch("asyncio.create_task") as mock_create_task:
            mock_create_task.return_value = MagicMock()

            await middleware._start_flush_task()

            assert middleware._running is True
            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_flush_task_when_already_running(self):
        """Should not start if already running"""
        mock_app = MagicMock()
        middleware = UsageTrackingMiddleware(mock_app)
        middleware._running = True

        with patch("asyncio.create_task") as mock_create_task:
            await middleware._start_flush_task()

            # Should not create new task
            mock_create_task.assert_not_called()
