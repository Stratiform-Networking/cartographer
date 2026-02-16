"""
Usage Tracking Middleware for Metrics Service

Tracks endpoint usage statistics locally without making external HTTP calls
since this is the metrics service itself that handles usage data.
"""

import asyncio
import base64
import json
import logging
import time
from collections import deque
from collections.abc import Callable
from datetime import datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..config import settings
from ..models import EndpointUsageRecord

logger = logging.getLogger(__name__)

try:
    import posthog
except Exception:  # pragma: no cover - only exercised when dependency is absent
    posthog = None

_POSTHOG_INITIALIZED = False

# Configuration
SERVICE_NAME = "metrics-service"
EXCLUDED_PATHS = {"/healthz", "/ready", "/", "/docs", "/openapi.json", "/redoc"}
# Also exclude usage endpoints to prevent infinite loops
USAGE_PATHS = {"/api/metrics/usage/record", "/api/metrics/usage/record/batch"}
INTERNAL_HEADER_KEYS = ("x-service-name", "x-request-signature", "x-request-timestamp")


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


def _is_service_bearer_token(authorization: str | None) -> bool:
    """Best-effort check for service-to-service bearer tokens without signature verification."""
    if not authorization:
        return False

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return False

    token_parts = parts[1].split(".")
    if len(token_parts) < 2:
        return False

    try:
        payload_segment = token_parts[1]
        padding = "=" * (-len(payload_segment) % 4)
        payload_json = base64.urlsafe_b64decode((payload_segment + padding).encode("utf-8"))
        payload = json.loads(payload_json.decode("utf-8"))
    except Exception:
        return False

    return payload.get("service") is True or str(payload.get("type", "")).lower() == "service"


def _is_user_generated_request(request: Request) -> bool:
    """Classify request origin for analytics filtering."""
    headers = request.headers

    for header_key in INTERNAL_HEADER_KEYS:
        if headers.get(header_key):
            return False

    if _is_service_bearer_token(headers.get("authorization")):
        return False

    user_agent = (headers.get("user-agent") or "").lower()
    if user_agent.startswith("kube-probe/") or user_agent.startswith("prometheus/"):
        return False

    return True


def _capture_posthog_api_event(
    service_name: str,
    path: str,
    method: str,
    status_code: int,
    response_time_ms: float,
    is_user_generated: bool,
    error_type: str | None,
    posthog_api_key: str,
    posthog_host: str,
    posthog_enabled: bool,
) -> None:
    """Send a backend API usage event to PostHog."""
    if not is_user_generated and status_code < 500:
        return

    if not _initialize_posthog(posthog_api_key, posthog_host, posthog_enabled):
        return

    properties = {
        "service": service_name,
        "path": path,
        "method": method,
        "status_code": status_code,
        "response_time_ms": round(response_time_ms, 2),
        "request_source": "user" if is_user_generated else "server",
    }
    if error_type:
        properties["error_type"] = error_type

    try:
        posthog.capture(
            distinct_id=f"service:{service_name}",
            event="api_request",
            properties=properties,
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


class UsageTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that tracks endpoint usage for the metrics service itself.

    Records directly to the usage tracker without HTTP calls to avoid
    circular dependencies.
    """

    def __init__(self, app, service_name: str = SERVICE_NAME):
        super().__init__(app)
        self.service_name = service_name
        self._buffer: deque[UsageRecord] = deque(maxlen=1000)
        self._flush_task: asyncio.Task | None = None
        self._running = False
        self._usage_tracker = None  # Lazy load to avoid circular import

    def _get_usage_tracker(self):
        """Lazy load usage tracker to avoid circular imports."""
        if self._usage_tracker is None:
            from .usage_tracker import usage_tracker

            self._usage_tracker = usage_tracker
        return self._usage_tracker

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
        """Process accumulated records directly."""
        if not self._buffer:
            return

        tracker = self._get_usage_tracker()

        # Collect records to process
        records_to_process: list[UsageRecord] = []
        while self._buffer and len(records_to_process) < settings.usage_batch_size:
            records_to_process.append(self._buffer.popleft())

        if not records_to_process:
            return

        try:
            for record in records_to_process:
                usage_record = EndpointUsageRecord(
                    endpoint=record.endpoint,
                    method=record.method,
                    service=self.service_name,
                    status_code=record.status_code,
                    response_time_ms=record.response_time_ms,
                    timestamp=record.timestamp,
                )
                await tracker.record_usage(usage_record)
        except Exception as e:
            logger.debug(f"Failed to record metrics service usage: {e}")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track usage."""
        # Start flush task on first request
        if not self._running:
            asyncio.create_task(self._start_flush_task())

        # Skip excluded paths and usage endpoints (prevent infinite loop)
        path = request.url.path
        if (
            path in EXCLUDED_PATHS
            or path in USAGE_PATHS
            or path.startswith("/docs")
            or path.startswith("/openapi")
            or path.startswith("/api/metrics/usage")
        ):
            return await call_next(request)

        # Track timing
        start_time = time.perf_counter()
        is_user_generated = _is_user_generated_request(request)

        # Process request
        try:
            response = await call_next(request)
        except Exception as exc:
            response_time_ms = (time.perf_counter() - start_time) * 1000
            _capture_posthog_api_event(
                service_name=self.service_name,
                path=path,
                method=request.method,
                status_code=500,
                response_time_ms=response_time_ms,
                is_user_generated=is_user_generated,
                error_type=exc.__class__.__name__,
                posthog_api_key=settings.posthog_api_key,
                posthog_host=settings.posthog_host,
                posthog_enabled=settings.posthog_enabled,
            )
            raise

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
            is_user_generated=is_user_generated,
            error_type=None,
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
