"""
Unit tests for the metrics-service Usage Tracking Middleware.
Tests request interception, timing, buffer management, and local recording.
"""

import asyncio
from collections import deque
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import settings
from app.models import EndpointUsageRecord
from app.services.usage_middleware import (
    EXCLUDED_PATHS,
    SERVICE_NAME,
    USAGE_PATHS,
    UsageRecord,
    UsageTrackingMiddleware,
)


class TestUsageRecord:
    """Tests for UsageRecord class"""

    def test_usage_record_creation(self):
        """Should create usage record with all fields"""
        now = datetime.utcnow()
        record = UsageRecord(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time_ms=45.5,
            timestamp=now,
        )

        assert record.endpoint == "/api/test"
        assert record.method == "GET"
        assert record.status_code == 200
        assert record.response_time_ms == 45.5
        assert record.timestamp == now

    def test_usage_record_uses_slots(self):
        """Should use __slots__ for memory efficiency"""
        assert hasattr(UsageRecord, "__slots__")
        assert "endpoint" in UsageRecord.__slots__
        assert "method" in UsageRecord.__slots__
        assert "status_code" in UsageRecord.__slots__


class TestUsageTrackingMiddlewareInit:
    """Tests for middleware initialization"""

    def test_middleware_init_defaults(self):
        """Should initialize with default values"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        assert middleware.service_name == SERVICE_NAME
        assert isinstance(middleware._buffer, deque)
        assert middleware._buffer.maxlen == 1000
        assert middleware._flush_task is None
        assert middleware._running is False
        assert middleware._usage_tracker is None

    def test_middleware_init_custom_service_name(self):
        """Should accept custom service name"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app, service_name="custom-service")

        assert middleware.service_name == "custom-service"


class TestGetUsageTracker:
    """Tests for lazy loading of usage tracker"""

    def test_get_usage_tracker_lazy_loads(self):
        """Should lazy load usage tracker on first access"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        assert middleware._usage_tracker is None

        # Get tracker
        tracker = middleware._get_usage_tracker()

        assert tracker is not None
        assert middleware._usage_tracker is not None

    def test_get_usage_tracker_returns_same_instance(self):
        """Should return same instance on subsequent calls"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        tracker1 = middleware._get_usage_tracker()
        tracker2 = middleware._get_usage_tracker()

        assert tracker1 is tracker2


class TestStartFlushTask:
    """Tests for _start_flush_task method"""

    async def test_start_flush_task_sets_running(self):
        """Should set running flag and create task"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        assert middleware._running is False

        # Start the task but cancel immediately
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

    async def test_start_flush_task_no_op_if_running(self):
        """Should not start new task if already running"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)
        middleware._running = True
        original_task = middleware._flush_task

        await middleware._start_flush_task()

        # Should not have created a new task
        assert middleware._flush_task == original_task


class TestFlushLoop:
    """Tests for _flush_loop method"""

    async def test_flush_loop_calls_flush_buffer(self):
        """Should call _flush_buffer periodically"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)
        middleware._running = True

        with patch.object(middleware, "_flush_buffer", new_callable=AsyncMock) as mock_flush:
            # Run one iteration
            task = asyncio.create_task(middleware._flush_loop())
            await asyncio.sleep(0.1)
            middleware._running = False
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def test_flush_loop_handles_cancelled_error(self):
        """Should handle CancelledError gracefully"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)
        middleware._running = True

        task = asyncio.create_task(middleware._flush_loop())
        await asyncio.sleep(0.05)
        task.cancel()

        # Should not raise
        try:
            await task
        except asyncio.CancelledError:
            pass


class TestFlushBuffer:
    """Tests for _flush_buffer method"""

    async def test_flush_buffer_empty_returns_early(self):
        """Should return early when buffer is empty"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        # Should not raise
        await middleware._flush_buffer()

    async def test_flush_buffer_processes_records(self):
        """Should process records from buffer"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        # Add records to buffer
        now = datetime.utcnow()
        for i in range(3):
            middleware._buffer.append(
                UsageRecord(
                    endpoint=f"/api/test/{i}",
                    method="GET",
                    status_code=200,
                    response_time_ms=10.0,
                    timestamp=now,
                )
            )

        mock_tracker = AsyncMock()
        mock_tracker.record_usage = AsyncMock(return_value=True)

        with patch.object(middleware, "_get_usage_tracker", return_value=mock_tracker):
            await middleware._flush_buffer()

            assert mock_tracker.record_usage.call_count == 3

    async def test_flush_buffer_handles_exception(self):
        """Should handle exceptions gracefully"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        # Add a record
        middleware._buffer.append(
            UsageRecord(
                endpoint="/api/test",
                method="GET",
                status_code=200,
                response_time_ms=10.0,
                timestamp=datetime.utcnow(),
            )
        )

        mock_tracker = AsyncMock()
        mock_tracker.record_usage = AsyncMock(side_effect=Exception("Error"))

        with patch.object(middleware, "_get_usage_tracker", return_value=mock_tracker):
            # Should not raise
            await middleware._flush_buffer()

    async def test_flush_buffer_respects_batch_size(self):
        """Should process at most settings.usage_batch_size records per flush"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        # Add more records than batch size
        now = datetime.utcnow()
        for i in range(settings.usage_batch_size + 5):
            middleware._buffer.append(
                UsageRecord(
                    endpoint=f"/api/test/{i}",
                    method="GET",
                    status_code=200,
                    response_time_ms=10.0,
                    timestamp=now,
                )
            )

        mock_tracker = AsyncMock()
        mock_tracker.record_usage = AsyncMock(return_value=True)

        with patch.object(middleware, "_get_usage_tracker", return_value=mock_tracker):
            await middleware._flush_buffer()

            # Should have processed settings.usage_batch_size records
            assert mock_tracker.record_usage.call_count == settings.usage_batch_size
            # Should have remaining records in buffer
            assert len(middleware._buffer) == 5


class TestDispatch:
    """Tests for dispatch method"""

    async def test_dispatch_skips_excluded_paths(self):
        """Should skip tracking for excluded paths"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        for path in EXCLUDED_PATHS:
            mock_request = MagicMock()
            mock_request.url.path = path
            mock_request.method = "GET"

            mock_call_next = AsyncMock(return_value=MagicMock(status_code=200))

            response = await middleware.dispatch(mock_request, mock_call_next)

            # Should have called next handler
            mock_call_next.assert_called_once()
            # Should not have added to buffer
            assert len(middleware._buffer) == 0

    async def test_dispatch_skips_usage_paths(self):
        """Should skip tracking for usage paths"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        for path in USAGE_PATHS:
            mock_request = MagicMock()
            mock_request.url.path = path
            mock_request.method = "POST"

            mock_call_next = AsyncMock(return_value=MagicMock(status_code=200))

            response = await middleware.dispatch(mock_request, mock_call_next)

            mock_call_next.assert_called_once()
            assert len(middleware._buffer) == 0

    async def test_dispatch_skips_docs_prefix(self):
        """Should skip tracking for /docs/* paths"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        mock_request = MagicMock()
        mock_request.url.path = "/docs/swagger"
        mock_request.method = "GET"

        mock_call_next = AsyncMock(return_value=MagicMock(status_code=200))

        response = await middleware.dispatch(mock_request, mock_call_next)

        mock_call_next.assert_called_once()
        assert len(middleware._buffer) == 0

    async def test_dispatch_skips_openapi_prefix(self):
        """Should skip tracking for /openapi/* paths"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        mock_request = MagicMock()
        mock_request.url.path = "/openapi.json"
        mock_request.method = "GET"

        mock_call_next = AsyncMock(return_value=MagicMock(status_code=200))

        response = await middleware.dispatch(mock_request, mock_call_next)

        mock_call_next.assert_called_once()
        assert len(middleware._buffer) == 0

    async def test_dispatch_skips_usage_api_prefix(self):
        """Should skip tracking for /api/metrics/usage/* paths"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)

        mock_request = MagicMock()
        mock_request.url.path = "/api/metrics/usage/stats"
        mock_request.method = "GET"

        mock_call_next = AsyncMock(return_value=MagicMock(status_code=200))

        response = await middleware.dispatch(mock_request, mock_call_next)

        mock_call_next.assert_called_once()
        assert len(middleware._buffer) == 0

    async def test_dispatch_tracks_api_path(self):
        """Should track non-excluded API paths"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)
        middleware._running = True  # Prevent task creation

        mock_request = MagicMock()
        mock_request.url.path = "/api/metrics/snapshot"
        mock_request.method = "GET"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, mock_call_next)

        mock_call_next.assert_called_once()
        assert len(middleware._buffer) == 1

        record = middleware._buffer[0]
        assert record.endpoint == "/api/metrics/snapshot"
        assert record.method == "GET"
        assert record.status_code == 200

    async def test_dispatch_records_response_time(self):
        """Should record response time"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)
        middleware._running = True

        mock_request = MagicMock()
        mock_request.url.path = "/api/test"
        mock_request.method = "POST"

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, mock_call_next)

        record = middleware._buffer[0]
        assert record.response_time_ms >= 0
        assert record.timestamp is not None

    async def test_dispatch_triggers_flush_when_buffer_full(self):
        """Should trigger flush when buffer reaches settings.usage_batch_size"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)
        middleware._running = True

        # Pre-fill buffer to just below threshold
        now = datetime.utcnow()
        for i in range(settings.usage_batch_size - 1):
            middleware._buffer.append(
                UsageRecord(
                    endpoint=f"/api/existing/{i}",
                    method="GET",
                    status_code=200,
                    response_time_ms=10.0,
                    timestamp=now,
                )
            )

        mock_request = MagicMock()
        mock_request.url.path = "/api/test"
        mock_request.method = "GET"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_call_next = AsyncMock(return_value=mock_response)

        with patch("asyncio.create_task") as mock_create_task:
            response = await middleware.dispatch(mock_request, mock_call_next)

            # Should have triggered flush
            mock_create_task.assert_called()


class TestShutdown:
    """Tests for shutdown method"""

    async def test_shutdown_sets_running_false(self):
        """Should set running flag to False"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)
        middleware._running = True

        await middleware.shutdown()

        assert middleware._running is False

    async def test_shutdown_cancels_flush_task(self):
        """Should cancel the flush task"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)
        middleware._running = True

        # Create a dummy task
        async def dummy_task():
            await asyncio.sleep(100)

        middleware._flush_task = asyncio.create_task(dummy_task())

        await middleware.shutdown()

        assert middleware._flush_task.cancelled() or middleware._flush_task.done()

    async def test_shutdown_flushes_remaining_records(self):
        """Should flush remaining records during shutdown"""
        app = MagicMock()
        middleware = UsageTrackingMiddleware(app)
        middleware._running = True

        # Add some records
        now = datetime.utcnow()
        for i in range(3):
            middleware._buffer.append(
                UsageRecord(
                    endpoint=f"/api/test/{i}",
                    method="GET",
                    status_code=200,
                    response_time_ms=10.0,
                    timestamp=now,
                )
            )

        mock_tracker = AsyncMock()
        mock_tracker.record_usage = AsyncMock(return_value=True)

        with patch.object(middleware, "_get_usage_tracker", return_value=mock_tracker):
            await middleware.shutdown()

            # All records should have been flushed
            assert len(middleware._buffer) == 0


class TestExcludedPaths:
    """Tests for excluded paths configuration"""

    def test_healthz_in_excluded_paths(self):
        """healthz should be excluded"""
        assert "/healthz" in EXCLUDED_PATHS

    def test_ready_in_excluded_paths(self):
        """ready should be excluded"""
        assert "/ready" in EXCLUDED_PATHS

    def test_root_in_excluded_paths(self):
        """root should be excluded"""
        assert "/" in EXCLUDED_PATHS

    def test_docs_in_excluded_paths(self):
        """docs should be excluded"""
        assert "/docs" in EXCLUDED_PATHS

    def test_usage_record_in_usage_paths(self):
        """usage record endpoint should be in usage paths"""
        assert "/api/metrics/usage/record" in USAGE_PATHS

    def test_usage_batch_in_usage_paths(self):
        """usage batch endpoint should be in usage paths"""
        assert "/api/metrics/usage/record/batch" in USAGE_PATHS
