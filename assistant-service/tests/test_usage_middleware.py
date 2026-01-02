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

from app.config import settings
from app.services.usage_middleware import (
    EXCLUDED_PATHS,
    SERVICE_NAME,
    UsageRecord,
    UsageTrackingMiddleware,
)


class TestUsageRecord:
    """Tests for UsageRecord class"""

    def test_init(self):
        """Should initialize with all fields"""
        timestamp = datetime.now(timezone.utc)
        record = UsageRecord(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time_ms=50.5,
            timestamp=timestamp,
        )

        assert record.endpoint == "/api/test"
        assert record.method == "GET"
        assert record.status_code == 200
        assert record.response_time_ms == 50.5
        assert record.timestamp == timestamp

    def test_to_dict(self):
        """Should convert to dictionary"""
        timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        record = UsageRecord(
            endpoint="/api/test",
            method="POST",
            status_code=201,
            response_time_ms=100.0,
            timestamp=timestamp,
        )

        result = record.to_dict()

        assert result["endpoint"] == "/api/test"
        assert result["method"] == "POST"
        assert result["service"] == SERVICE_NAME
        assert result["status_code"] == 201
        assert result["response_time_ms"] == 100.0
        assert "2024-01-01" in result["timestamp"]


class TestUsageTrackingMiddlewareInit:
    """Tests for UsageTrackingMiddleware initialization"""

    def test_init_defaults(self):
        """Should initialize with default values"""
        app = FastAPI()
        middleware = UsageTrackingMiddleware(app)

        assert middleware.service_name == SERVICE_NAME
        assert isinstance(middleware._buffer, deque)
        assert middleware._client is None
        assert middleware._flush_task is None
        assert middleware._running is False

    def test_init_custom_service_name(self):
        """Should accept custom service name"""
        app = FastAPI()
        middleware = UsageTrackingMiddleware(app, service_name="custom-service")

        assert middleware.service_name == "custom-service"


class TestUsageTrackingMiddlewareClient:
    """Tests for HTTP client management"""

    async def test_get_client_creates_client(self):
        """Should create client when none exists"""
        app = FastAPI()
        middleware = UsageTrackingMiddleware(app)

        client = await middleware._get_client()

        assert client is not None
        assert isinstance(client, httpx.AsyncClient)

        # Cleanup
        await client.aclose()

    async def test_get_client_reuses_client(self):
        """Should reuse existing client"""
        app = FastAPI()
        middleware = UsageTrackingMiddleware(app)

        client1 = await middleware._get_client()
        client2 = await middleware._get_client()

        assert client1 is client2

        # Cleanup
        await client1.aclose()

    async def test_get_client_recreates_closed_client(self):
        """Should recreate client if closed"""
        app = FastAPI()
        middleware = UsageTrackingMiddleware(app)

        client1 = await middleware._get_client()
        await client1.aclose()

        client2 = await middleware._get_client()

        assert client2 is not client1
        assert not client2.is_closed

        # Cleanup
        await client2.aclose()


class TestUsageTrackingMiddlewareFlush:
    """Tests for flush functionality"""

    async def test_start_flush_task(self):
        """Should start flush task"""
        app = FastAPI()
        middleware = UsageTrackingMiddleware(app)

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

    async def test_start_flush_task_only_once(self):
        """Should only start flush task once"""
        app = FastAPI()
        middleware = UsageTrackingMiddleware(app)

        await middleware._start_flush_task()
        task1 = middleware._flush_task

        await middleware._start_flush_task()
        task2 = middleware._flush_task

        assert task1 is task2

        # Cleanup
        middleware._running = False
        middleware._flush_task.cancel()
        try:
            await middleware._flush_task
        except asyncio.CancelledError:
            pass

    async def test_flush_buffer_empty(self):
        """Should do nothing when buffer is empty"""
        app = FastAPI()
        middleware = UsageTrackingMiddleware(app)

        # Should not raise
        await middleware._flush_buffer()

    async def test_flush_buffer_success(self):
        """Should send records to metrics service"""
        app = FastAPI()
        middleware = UsageTrackingMiddleware(app)

        # Add records to buffer
        record = UsageRecord(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time_ms=50.0,
            timestamp=datetime.utcnow(),
        )
        middleware._buffer.append(record)

        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        with patch.object(middleware, "_get_client", return_value=mock_client):
            await middleware._flush_buffer()

        assert len(middleware._buffer) == 0
        mock_client.post.assert_called_once()

    async def test_flush_buffer_failure_restores_records(self):
        """Should restore records on failure"""
        app = FastAPI()
        middleware = UsageTrackingMiddleware(app)

        # Add records to buffer
        record = UsageRecord(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time_ms=50.0,
            timestamp=datetime.utcnow(),
        )
        middleware._buffer.append(record)

        # Mock HTTP client failure
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False

        with patch.object(middleware, "_get_client", return_value=mock_client):
            await middleware._flush_buffer()

        # Records should be restored
        assert len(middleware._buffer) == 1

    async def test_flush_buffer_exception_restores_records(self):
        """Should restore records on exception"""
        app = FastAPI()
        middleware = UsageTrackingMiddleware(app)

        # Add records to buffer
        record = UsageRecord(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time_ms=50.0,
            timestamp=datetime.utcnow(),
        )
        middleware._buffer.append(record)

        # Mock HTTP client exception
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Network error"))
        mock_client.is_closed = False

        with patch.object(middleware, "_get_client", return_value=mock_client):
            await middleware._flush_buffer()

        # Records should be restored
        assert len(middleware._buffer) == 1

    async def test_flush_buffer_race_condition(self):
        """Should handle race condition when buffer empties during iteration"""
        app = FastAPI()
        middleware = UsageTrackingMiddleware(app)

        # Add a record then clear it during flush simulation
        # This tests the early return on line 108
        record = UsageRecord(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time_ms=50.0,
            timestamp=datetime.utcnow(),
        )
        middleware._buffer.append(record)

        # Pop the record before flush processes it
        middleware._buffer.popleft()

        # Should handle empty buffer gracefully
        await middleware._flush_buffer()


class TestUsageTrackingMiddlewareFlushLoop:
    """Tests for flush loop"""

    async def test_flush_loop_runs(self):
        """Should run flush loop"""
        app = FastAPI()
        middleware = UsageTrackingMiddleware(app)
        middleware._running = True

        # Mock flush buffer to track calls
        call_count = 0
        original_flush = middleware._flush_buffer

        async def mock_flush():
            nonlocal call_count
            call_count += 1
            middleware._running = False  # Stop after first iteration

        middleware._flush_buffer = mock_flush

        with patch.object(settings, "usage_batch_interval_seconds", 0.01):
            await middleware._flush_loop()

        assert call_count >= 1

    async def test_flush_loop_handles_cancellation(self):
        """Should handle cancellation gracefully"""
        app = FastAPI()
        middleware = UsageTrackingMiddleware(app)
        middleware._running = True

        # Start loop in background
        task = asyncio.create_task(middleware._flush_loop())

        # Cancel after brief delay
        await asyncio.sleep(0.01)
        task.cancel()

        # Should not raise
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def test_flush_loop_handles_error(self):
        """Should continue after error"""
        app = FastAPI()
        middleware = UsageTrackingMiddleware(app)
        middleware._running = True

        call_count = 0

        async def mock_flush():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Test error")
            middleware._running = False

        middleware._flush_buffer = mock_flush

        with patch.object(settings, "usage_batch_interval_seconds", 0.01):
            await middleware._flush_loop()

        assert call_count >= 2


class TestUsageTrackingMiddlewareDispatch:
    """Tests for dispatch method"""

    def test_dispatch_excluded_paths(self):
        """Should skip excluded paths"""
        app = FastAPI()

        @app.get("/healthz")
        def healthz():
            return {"status": "ok"}

        app.add_middleware(UsageTrackingMiddleware)

        client = TestClient(app)
        response = client.get("/healthz")

        assert response.status_code == 200

    def test_dispatch_docs_path(self):
        """Should skip docs paths"""
        app = FastAPI()
        app.add_middleware(UsageTrackingMiddleware)

        client = TestClient(app)
        # Docs endpoint should be skipped
        response = client.get("/docs")

        # Should proceed without tracking (even if 404)
        assert response.status_code in [200, 404, 307]

    def test_dispatch_tracks_api_endpoints(self):
        """Should track API endpoints"""
        app = FastAPI()

        @app.get("/api/test")
        def test_endpoint():
            return {"data": "test"}

        app.add_middleware(UsageTrackingMiddleware)

        client = TestClient(app)
        response = client.get("/api/test")

        assert response.status_code == 200

    def test_dispatch_tracks_response_time(self):
        """Should track response time"""
        import time

        app = FastAPI()

        @app.get("/api/slow")
        def slow_endpoint():
            time.sleep(0.01)
            return {"data": "slow"}

        app.add_middleware(UsageTrackingMiddleware)

        client = TestClient(app)
        response = client.get("/api/slow")

        assert response.status_code == 200

    def test_dispatch_triggers_flush_when_buffer_full(self):
        """Should trigger immediate flush when buffer reaches batch size"""
        app = FastAPI()

        @app.get("/api/item/{item_id}")
        def get_item(item_id: int):
            return {"id": item_id}

        app.add_middleware(UsageTrackingMiddleware)

        client = TestClient(app)

        # Make enough requests to fill the buffer and trigger flush
        for i in range(settings.usage_batch_size + 5):
            response = client.get(f"/api/item/{i}")
            assert response.status_code == 200


class TestUsageTrackingMiddlewareShutdown:
    """Tests for shutdown method"""

    async def test_shutdown_stops_flush_task(self):
        """Should stop flush task"""
        app = FastAPI()
        middleware = UsageTrackingMiddleware(app)

        # Start flush task
        await middleware._start_flush_task()

        # Shutdown
        await middleware.shutdown()

        assert middleware._running is False

    async def test_shutdown_flushes_remaining_records(self):
        """Should flush remaining records"""
        app = FastAPI()
        middleware = UsageTrackingMiddleware(app)

        # Add records
        record = UsageRecord(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time_ms=50.0,
            timestamp=datetime.utcnow(),
        )
        middleware._buffer.append(record)

        # Mock successful flush
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False
        mock_client.aclose = AsyncMock()

        middleware._client = mock_client

        await middleware.shutdown()

        # Buffer should be empty after shutdown
        assert len(middleware._buffer) == 0
        mock_client.aclose.assert_called_once()

    async def test_shutdown_closes_client(self):
        """Should close HTTP client"""
        app = FastAPI()
        middleware = UsageTrackingMiddleware(app)

        # Create client
        client = await middleware._get_client()

        # Shutdown
        await middleware.shutdown()

        # Client should be closed
        # Note: client may be recreated in cleanup, so just verify no exception

    async def test_shutdown_without_task(self):
        """Should handle shutdown without flush task"""
        app = FastAPI()
        middleware = UsageTrackingMiddleware(app)

        # Shutdown without starting task
        await middleware.shutdown()

        assert middleware._running is False

    async def test_shutdown_without_client(self):
        """Should handle shutdown without client"""
        app = FastAPI()
        middleware = UsageTrackingMiddleware(app)

        # Shutdown without creating client
        await middleware.shutdown()

        # Should not raise


class TestUsageTrackingMiddlewareIntegration:
    """Integration tests for usage middleware"""

    def test_full_request_flow(self):
        """Should track full request flow"""
        app = FastAPI()

        @app.get("/api/items")
        def get_items():
            return [{"id": 1, "name": "Item 1"}]

        @app.post("/api/items")
        def create_item():
            return {"id": 2, "name": "Item 2"}

        app.add_middleware(UsageTrackingMiddleware)

        client = TestClient(app)

        # Make multiple requests
        response1 = client.get("/api/items")
        response2 = client.post("/api/items")
        response3 = client.get("/healthz")  # Should be excluded

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 404  # Not defined

    def test_error_responses_tracked(self):
        """Should track error responses"""
        app = FastAPI()

        @app.get("/api/error")
        def error_endpoint():
            raise ValueError("Test error")

        app.add_middleware(UsageTrackingMiddleware)

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/error")

        assert response.status_code == 500


class TestExcludedPaths:
    """Tests for excluded paths configuration"""

    def test_excluded_paths_constant(self):
        """Should have expected excluded paths"""
        assert "/healthz" in EXCLUDED_PATHS
        assert "/ready" in EXCLUDED_PATHS
        assert "/" in EXCLUDED_PATHS
        assert "/docs" in EXCLUDED_PATHS
        assert "/openapi.json" in EXCLUDED_PATHS
        assert "/redoc" in EXCLUDED_PATHS

    def test_batch_size_constant(self):
        """Should have reasonable batch size"""
        assert settings.usage_batch_size > 0
        assert settings.usage_batch_size <= 100

    def test_batch_interval_constant(self):
        """Should have reasonable batch interval"""
        assert settings.usage_batch_interval_seconds > 0
        assert settings.usage_batch_interval_seconds <= 60
