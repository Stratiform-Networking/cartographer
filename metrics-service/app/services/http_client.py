"""
Shared HTTP client for the metrics service.

Maintains a single persistent HTTP client with connection pooling
for efficient communication with backend and health services.
"""

import logging

import httpx

logger = logging.getLogger(__name__)

# Check if HTTP/2 support is available
try:
    import h2  # noqa: F401

    HTTP2_AVAILABLE = True
except ImportError:
    HTTP2_AVAILABLE = False
    logger.debug("h2 package not installed - HTTP/2 disabled for metrics service")


class ServiceHttpClient:
    """
    Singleton HTTP client with connection pooling for microservice communication.

    Features:
    - Connection reuse across requests
    - HTTP/2 support when available
    - Configurable timeouts
    - Clean shutdown
    """

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def initialize(self):
        """Initialize the HTTP client with connection pooling."""
        if self._client is None:
            # Configure connection pool limits
            limits = httpx.Limits(
                max_keepalive_connections=20,
                max_connections=50,
                keepalive_expiry=30.0,
            )
            timeout = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)
            self._client = httpx.AsyncClient(
                limits=limits,
                timeout=timeout,
                http2=HTTP2_AVAILABLE,
            )
            protocol = "HTTP/2" if HTTP2_AVAILABLE else "HTTP/1.1"
            logger.info(f"Metrics service HTTP client initialized ({protocol})")

    async def close(self):
        """Close the HTTP client gracefully."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("Metrics service HTTP client closed")

    async def get(self, url: str, timeout: float = 10.0, **kwargs) -> httpx.Response:
        """Make a GET request using the shared client."""
        if not self._client:
            await self.initialize()
        return await self._client.get(url, timeout=timeout, **kwargs)

    async def post(self, url: str, timeout: float = 10.0, **kwargs) -> httpx.Response:
        """Make a POST request using the shared client."""
        if not self._client:
            await self.initialize()
        return await self._client.post(url, timeout=timeout, **kwargs)


# Singleton instance
http_client = ServiceHttpClient()
