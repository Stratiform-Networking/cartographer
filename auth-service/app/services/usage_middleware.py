"""
Usage Tracking Middleware

Automatically tracks endpoint usage statistics and reports them
to the metrics service for aggregation.
"""

import asyncio
import logging
import time
from collections import deque
from datetime import datetime

import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..config import settings

logger = logging.getLogger(__name__)

try:
    import posthog
except Exception:  # pragma: no cover - only exercised when dependency is absent
    posthog = None

_POSTHOG_INITIALIZED = False

# Constants
SERVICE_NAME = "auth-service"
EXCLUDED_PATHS = {"/healthz", "/ready", "/", "/docs", "/openapi.json", "/redoc"}


def _initialize_posthog(posthog_api_key: str, posthog_host: str, posthog_enabled: bool) -> bool:
    """Initialize the PostHog client once per process."""
    global _POSTHOG_INITIALIZED

    if _POSTHOG_INITIALIZED:
        return True

    if not posthog_enabled or not posthog_api_key or posthog is None:
        return False

    try:
        posthog.api_key = posthog_api_key
        posthog.host = posthog_host
        _POSTHOG_INITIALIZED = True
        return True
    except Exception as exc:
        logger.debug(f"Failed to initialize PostHog: {exc}")
        return False


def _capture_posthog_api_event(
    service_name: str,
    path: str,
    method: str,
    status_code: int,
    response_time_ms: float,
    posthog_api_key: str,
    posthog_host: str,
    posthog_enabled: bool,
) -> None:
    """Send a backend API usage event to PostHog."""
    if not _initialize_posthog(posthog_api_key, posthog_host, posthog_enabled):
        return

    try:
        posthog.capture(
            distinct_id=f"service:{service_name}",
            event="api_request",
            properties={
                "service": service_name,
                "path": path,
                "method": method,
                "status_code": status_code,
                "response_time_ms": round(response_time_ms, 2),
            },
        )
    except Exception as exc:
        logger.debug(f"Failed to capture PostHog event: {exc}")


class UsageRecord:
    """Simple record class for usage data."""

    __slots__ = ["endpoint", "method", "status_code", "response_time_ms", "timestamp"]

    def __init__(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: float,
        timestamp: datetime,
    ):
        self.endpoint = endpoint
        self.method = method
        self.status_code = status_code
        self.response_time_ms = response_time_ms
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        return {
            "endpoint": self.endpoint,
            "method": self.method,
            "service": SERVICE_NAME,
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

    def __init__(self, app, service_name: str = SERVICE_NAME):
        super().__init__(app)
        self.service_name = service_name
        self._buffer: deque[UsageRecord] = deque(maxlen=1000)  # Limit buffer size
        self._client: httpx.AsyncClient | None = None
        self._flush_task: asyncio.Task | None = None
        self._running = False

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=settings.metrics_service_url,
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
                await asyncio.sleep(settings.usage_batch_interval_seconds)
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
        while self._buffer and len(records_to_send) < settings.usage_batch_size:
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
                for record_dict in reversed(records_to_send):
                    record = UsageRecord(
                        endpoint=record_dict["endpoint"],
                        method=record_dict["method"],
                        status_code=record_dict["status_code"],
                        response_time_ms=record_dict["response_time_ms"],
                        timestamp=datetime.fromisoformat(record_dict["timestamp"]),
                    )
                    self._buffer.appendleft(record)
        except Exception as e:
            logger.debug(f"Failed to report usage to metrics service: {e}")
            # Put records back on failure
            for record_dict in reversed(records_to_send):
                record = UsageRecord(
                    endpoint=record_dict["endpoint"],
                    method=record_dict["method"],
                    status_code=record_dict["status_code"],
                    response_time_ms=record_dict["response_time_ms"],
                    timestamp=datetime.fromisoformat(record_dict["timestamp"]),
                )
                self._buffer.appendleft(record)

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and track usage."""
        # Start flush task on first request
        if not self._running:
            asyncio.create_task(self._start_flush_task())

        # Skip excluded paths
        path = request.url.path
        if path in EXCLUDED_PATHS or path.startswith("/docs") or path.startswith("/openapi"):
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
            status_code=response.status_code,
            response_time_ms=response_time_ms,
            timestamp=datetime.utcnow(),
        )

        # Add to buffer (non-blocking)
        self._buffer.append(record)
        _capture_posthog_api_event(
            service_name=self.service_name,
            path=path,
            method=request.method,
            status_code=response.status_code,
            response_time_ms=response_time_ms,
            posthog_api_key=settings.posthog_api_key,
            posthog_host=settings.posthog_host,
            posthog_enabled=settings.posthog_enabled,
        )

        # Trigger immediate flush if buffer is getting full
        if len(self._buffer) >= settings.usage_batch_size:
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
