"""
Usage Tracking Middleware

Automatically tracks endpoint usage statistics and reports them
to the metrics service for aggregation.
"""

import asyncio
import logging
import time
from collections import deque
from collections.abc import Callable
from datetime import datetime

import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..config import get_settings

logger = logging.getLogger(__name__)

# Excluded paths and prefixes (not configurable - these are internal)
EXCLUDED_PATHS = {"/healthz", "/ready", "/", "/docs", "/openapi.json", "/redoc", "/favicon.png"}
EXCLUDED_PREFIXES = ("/docs", "/openapi", "/assets", "/api/metrics/usage")


class UsageRecord:
    """Simple record class for usage data."""

    __slots__ = [
        "endpoint",
        "method",
        "service_name",
        "status_code",
        "response_time_ms",
        "timestamp",
    ]

    def __init__(
        self,
        endpoint: str,
        method: str,
        service_name: str,
        status_code: int,
        response_time_ms: float,
        timestamp: datetime,
    ):
        self.endpoint = endpoint
        self.method = method
        self.service_name = service_name
        self.status_code = status_code
        self.response_time_ms = response_time_ms
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        return {
            "endpoint": self.endpoint,
            "method": self.method,
            "service": self.service_name,
            "status_code": self.status_code,
            "response_time_ms": self.response_time_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class UsageTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that tracks endpoint usage and reports to metrics service.

    Features:
    - Non-blocking: Uses background tasks for reporting
    - Batching: Accumulates records and sends in batches
    - Resilient: Continues operating even if metrics service is unavailable
    """

    def __init__(self, app, service_name: str = "backend"):
        super().__init__(app)
        self.service_name = service_name
        self._settings = get_settings()
        self._buffer: deque[UsageRecord] = deque(maxlen=1000)
        self._client: httpx.AsyncClient | None = None
        self._flush_task: asyncio.Task | None = None
        self._running = False

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._settings.metrics_service_url,
                timeout=5.0,
            )
        return self._client

    async def _start_flush_task(self):
        """Start the background flush task if not running."""
        if not self._running:
            self._running = True
            self._flush_task = asyncio.create_task(self._flush_loop())

    async def _flush_loop(self):
        """Background loop that periodically flushes the buffer."""
        while self._running:
            try:
                await asyncio.sleep(self._settings.usage_batch_interval_seconds)
                await self._flush_buffer()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Flush loop error: {e}")

    async def _flush_buffer(self):
        """Send accumulated records to metrics service."""
        if not self._buffer:
            return

        # Collect records to send
        records_to_send: list[dict] = []
        while self._buffer and len(records_to_send) < self._settings.usage_batch_size:
            records_to_send.append(self._buffer.popleft().to_dict())

        if not records_to_send:
            return

        try:
            client = await self._get_client()
            response = await client.post(
                "/api/metrics/usage/record/batch",
                json={"records": records_to_send},
            )

            if response.status_code != 200:
                logger.debug(f"Failed to report usage: {response.status_code}")
                # Put records back in buffer on failure (at the front)
                self._restore_records(records_to_send)
        except Exception as e:
            logger.debug(f"Failed to report usage to metrics service: {e}")
            # Put records back on failure
            self._restore_records(records_to_send)

    def _restore_records(self, records_to_send: list[dict]) -> None:
        """Restore records to buffer after a failed send attempt."""
        for record_dict in reversed(records_to_send):
            record = UsageRecord(
                endpoint=record_dict["endpoint"],
                method=record_dict["method"],
                service_name=record_dict["service"],
                status_code=record_dict["status_code"],
                response_time_ms=record_dict["response_time_ms"],
                timestamp=datetime.fromisoformat(record_dict["timestamp"]),
            )
            self._buffer.appendleft(record)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track usage."""
        # Start flush task on first request
        if not self._running:
            asyncio.create_task(self._start_flush_task())

        # Skip excluded paths
        path = request.url.path
        if path in EXCLUDED_PATHS:
            return await call_next(request)

        # Skip excluded prefixes
        for prefix in EXCLUDED_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # Track timing
        start_time = time.perf_counter()

        # Process request
        response = await call_next(request)

        # Calculate response time
        response_time_ms = (time.perf_counter() - start_time) * 1000

        # Create usage record
        record = UsageRecord(
            endpoint=path,
            method=request.method,
            service_name=self.service_name,
            status_code=response.status_code,
            response_time_ms=response_time_ms,
            timestamp=datetime.utcnow(),
        )

        # Add to buffer (non-blocking)
        self._buffer.append(record)

        # Trigger immediate flush if buffer is getting full
        if len(self._buffer) >= self._settings.usage_batch_size:
            asyncio.create_task(self._flush_buffer())

        return response

    async def shutdown(self):
        """Clean shutdown - flush remaining records."""
        self._running = False

        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Final flush
        while self._buffer:
            await self._flush_buffer()

        if self._client:
            await self._client.aclose()
