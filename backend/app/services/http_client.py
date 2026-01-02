"""
Shared HTTP client pool with connection reuse, circuit breaker, and warm-up support.

This module addresses several performance issues identified in load testing:
1. Connection pooling - Reuses connections instead of creating new ones per request
2. Circuit breaker - Fails fast when downstream services are unavailable
3. Warm-up - Pre-establishes connections on startup to avoid cold start latency
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum

import httpx
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from ..config import get_settings

logger = logging.getLogger(__name__)

# Check if HTTP/2 support is available
try:
    import h2  # noqa: F401

    HTTP2_AVAILABLE = True
except ImportError:
    HTTP2_AVAILABLE = False
    logger.warning(
        "h2 package not installed - HTTP/2 disabled. Install with: pip install httpx[http2]"
    )


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation - requests flow through
    OPEN = "open"  # Circuit tripped - requests fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreaker:
    """
    Simple circuit breaker implementation.

    - CLOSED: Requests pass through normally
    - OPEN: Requests fail immediately (fail fast)
    - HALF_OPEN: Allow one test request to check if service recovered
    """

    failure_threshold: int = 5  # Failures before opening circuit
    recovery_timeout: float = 30.0  # Seconds before trying half-open
    half_open_max_calls: int = 1  # Test calls in half-open state

    state: CircuitState = field(default=CircuitState.CLOSED)
    failure_count: int = field(default=0)
    last_failure_time: float = field(default=0.0)
    half_open_calls: int = field(default=0)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def can_execute(self) -> bool:
        """Check if request should be allowed through"""
        async with self._lock:
            if self.state == CircuitState.CLOSED:
                return True

            if self.state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
                    return True
                return False

            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls < self.half_open_max_calls:
                    self.half_open_calls += 1
                    return True
                return False

            return False

    async def record_success(self):
        """Record a successful request"""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                # Service recovered - close circuit
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker CLOSED - service recovered")
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0

    async def record_failure(self):
        """Record a failed request"""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                # Recovery failed - reopen circuit
                self.state = CircuitState.OPEN
                logger.warning("Circuit breaker OPEN - recovery attempt failed")
            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitState.OPEN
                    logger.warning(f"Circuit breaker OPEN after {self.failure_count} failures")


@dataclass
class ServiceClient:
    """HTTP client wrapper for a specific service with circuit breaker"""

    name: str
    base_url: str
    client: httpx.AsyncClient | None = None
    circuit_breaker: CircuitBreaker = field(default_factory=CircuitBreaker)

    async def initialize(self):
        """Initialize the HTTP client with connection pooling"""
        if self.client is None:
            # Configure connection pool limits
            limits = httpx.Limits(
                max_keepalive_connections=20, max_connections=100, keepalive_expiry=30.0
            )
            timeout = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                limits=limits,
                timeout=timeout,
                http2=HTTP2_AVAILABLE,  # Enable HTTP/2 if h2 package is available
            )
            protocol = "HTTP/2" if HTTP2_AVAILABLE else "HTTP/1.1"
            logger.info(f"Initialized HTTP client for {self.name} -> {self.base_url} ({protocol})")

    async def close(self):
        """Close the HTTP client"""
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.info(f"Closed HTTP client for {self.name}")

    async def warm_up(self) -> bool:
        """
        Warm up the connection by making a test request.
        Returns True if warm-up succeeded.
        """
        if not self.client:
            await self.initialize()

        try:
            # Try common health endpoints
            for path in ["/health", "/healthz", "/api/health", "/"]:
                try:
                    response = await self.client.get(path, timeout=5.0)
                    if response.status_code < 500:
                        logger.info(f"Warm-up succeeded for {self.name} via {path}")
                        return True
                except Exception:
                    continue

            logger.warning(f"Warm-up failed for {self.name} - no healthy endpoint found")
            return False
        except Exception as e:
            logger.warning(f"Warm-up failed for {self.name}: {e}")
            return False


class HTTPClientPool:
    """
    Centralized HTTP client pool for all microservices.

    Features:
    - Connection pooling with keepalive
    - Circuit breaker per service
    - Startup warm-up
    - Graceful shutdown
    """

    def __init__(self):
        self._services: dict[str, ServiceClient] = {}
        self._initialized = False

    def register_service(self, name: str, url: str) -> ServiceClient:
        """Register a service with the client pool"""
        if name not in self._services:
            self._services[name] = ServiceClient(name=name, base_url=url)
            logger.debug(f"Registered service: {name} -> {url}")
        return self._services[name]

    async def initialize_all(self):
        """Initialize all registered service clients"""
        if self._initialized:
            return

        logger.info(f"Initializing {len(self._services)} HTTP clients...")

        for service in self._services.values():
            await service.initialize()

        self._initialized = True
        logger.info("HTTP client pool initialized")

    async def warm_up_all(self) -> dict[str, bool]:
        """
        Warm up connections to all services.
        Returns dict of service_name -> success status.
        """
        results = {}

        logger.info("Starting connection warm-up...")

        # Warm up in parallel
        async def warm_up_service(service: ServiceClient):
            return service.name, await service.warm_up()

        tasks = [warm_up_service(svc) for svc in self._services.values()]
        warm_up_results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in warm_up_results:
            if isinstance(result, tuple):
                name, success = result
                results[name] = success
            else:
                logger.error(f"Warm-up error: {result}")

        successful = sum(1 for v in results.values() if v)
        logger.info(f"Warm-up complete: {successful}/{len(results)} services ready")

        return results

    async def close_all(self):
        """Close all HTTP clients gracefully"""
        logger.info("Closing HTTP client pool...")

        for service in self._services.values():
            await service.close()

        self._initialized = False
        logger.info("HTTP client pool closed")

    def get_service(self, name: str) -> ServiceClient | None:
        """Get a service client by name"""
        return self._services.get(name)

    async def request(
        self,
        service_name: str,
        method: str,
        path: str,
        params: dict | None = None,
        json_body: dict | None = None,
        headers: dict | None = None,
        timeout: float | None = None,
    ) -> JSONResponse:
        """
        Make a request to a service with circuit breaker protection.

        Args:
            service_name: Registered service name
            method: HTTP method (GET, POST, etc.)
            path: Request path (relative to service base URL)
            params: Query parameters
            json_body: JSON request body
            headers: Additional headers
            timeout: Override default timeout

        Returns:
            JSONResponse with the service response

        Raises:
            HTTPException on errors
        """
        service = self._services.get(service_name)
        if not service:
            raise HTTPException(status_code=500, detail=f"Unknown service: {service_name}")

        if not service.client:
            await service.initialize()

        # Check circuit breaker
        if not await service.circuit_breaker.can_execute():
            raise HTTPException(
                status_code=503,
                detail=f"{service_name} service temporarily unavailable (circuit open)",
            )

        try:
            # Build request kwargs
            kwargs: dict = {}
            if params:
                kwargs["params"] = params
            if json_body is not None:
                kwargs["json"] = json_body
            if headers:
                kwargs["headers"] = headers
            if timeout:
                kwargs["timeout"] = timeout

            # Make the request
            response = await service.client.request(method, path, **kwargs)

            # Record success
            await service.circuit_breaker.record_success()

            # Parse and return response
            try:
                content = response.json()
            except Exception:
                content = {"detail": response.text or "Empty response"}

            return JSONResponse(content=content, status_code=response.status_code)

        except httpx.ConnectError as e:
            await service.circuit_breaker.record_failure()
            logger.error(f"Connection error to {service_name}: {e}")
            raise HTTPException(status_code=503, detail=f"{service_name} service unavailable")
        except httpx.TimeoutException as e:
            await service.circuit_breaker.record_failure()
            logger.error(f"Timeout connecting to {service_name}: {e}")
            raise HTTPException(status_code=504, detail=f"{service_name} service timeout")
        except HTTPException:
            raise
        except Exception as e:
            await service.circuit_breaker.record_failure()
            logger.error(f"Error calling {service_name}: {e}")
            raise HTTPException(status_code=500, detail=f"{service_name} service error: {str(e)}")


# Global singleton instance
http_pool = HTTPClientPool()


def get_service_urls() -> dict[str, str]:
    """Get service URLs from settings."""
    settings = get_settings()
    return {
        "health": settings.health_service_url,
        "auth": settings.auth_service_url,
        "metrics": settings.metrics_service_url,
        "assistant": settings.assistant_service_url,
        "notification": settings.notification_service_url,
    }


def register_all_services(pool: HTTPClientPool | None = None):
    """Register all microservices with the HTTP client pool.

    Args:
        pool: Optional pool instance. Defaults to global http_pool.
    """
    target_pool = pool or http_pool
    service_urls = get_service_urls()
    for name, url in service_urls.items():
        target_pool.register_service(name, url)


@asynccontextmanager
async def lifespan_http_pool():
    """
    Async context manager for FastAPI lifespan.
    Handles registration, initialization and cleanup of the HTTP client pool.
    """
    # Register services at startup (not on module import)
    register_all_services()

    # Initialize clients
    await http_pool.initialize_all()
    await http_pool.warm_up_all()

    yield

    # Shutdown
    await http_pool.close_all()
