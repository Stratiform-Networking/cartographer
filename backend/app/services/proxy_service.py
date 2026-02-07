"""
Shared proxy service for forwarding requests to microservices.

This service provides a unified interface for all proxy routers to forward
requests to their respective downstream microservices using the shared
HTTP client pool.

Features:
- Consistent interface across all proxy routers
- Auth header extraction and forwarding
- Configurable path prefixes per service
- Service-specific timeout defaults
"""

from typing import Any

from fastapi import Request

from ..dependencies.token_extractor import resolve_authorization_header
from .http_client import http_pool

# Service path prefixes - defines the API path structure for each service
SERVICE_PATH_PREFIXES: dict[str, str] = {
    "auth": "/api/auth",
    "health": "/api/health",
    "metrics": "/api/metrics",
    "assistant": "/api/assistant",
    "notification": "/api/notifications",
}

# Default timeouts per service (seconds)
SERVICE_TIMEOUTS: dict[str, float] = {
    "auth": 30.0,
    "health": 30.0,
    "metrics": 30.0,
    "assistant": 60.0,
    "notification": 30.0,
}


def extract_auth_headers(request: Request) -> dict[str, str]:
    """
    Extract authorization header from request for forwarding to downstream services.

    Args:
        request: The incoming FastAPI request

    Returns:
        Dictionary with Authorization header if present, empty dict otherwise
    """
    headers: dict[str, str] = {}
    auth_header = resolve_authorization_header(request)
    if auth_header:
        headers["Authorization"] = auth_header
    return headers


async def proxy_request(
    service_name: str,
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float | None = None,
    use_prefix: bool = True,
    custom_prefix: str | None = None,
) -> Any:
    """
    Forward a request to a downstream microservice using the shared HTTP client pool.

    This is the unified proxy function used by all proxy routers. It handles:
    - Path prefix construction based on service
    - Default timeouts per service
    - Request forwarding via the shared client pool with circuit breaker

    Args:
        service_name: Name of the target service (auth, health, metrics, assistant, notification)
        method: HTTP method (GET, POST, PUT, PATCH, DELETE)
        path: The path to append after the service prefix (e.g., "/users" becomes "/api/auth/users")
        params: Query parameters to include
        json_body: JSON body for POST/PUT/PATCH requests
        headers: Additional headers to forward (e.g., Authorization, X-User-Id)
        timeout: Request timeout in seconds (uses service default if not specified)
        use_prefix: Whether to prepend the service path prefix (default True)
        custom_prefix: Override the service path prefix with a custom one

    Returns:
        The response from the downstream service (typically dict or list)

    Raises:
        HTTPException: If the downstream service returns an error
    """
    # Determine the full path
    if custom_prefix is not None:
        full_path = f"{custom_prefix}{path}"
    elif use_prefix:
        prefix = SERVICE_PATH_PREFIXES.get(service_name, f"/api/{service_name}")
        full_path = f"{prefix}{path}"
    else:
        full_path = path

    # Use service-specific default timeout if not specified
    if timeout is None:
        timeout = SERVICE_TIMEOUTS.get(service_name, 30.0)

    return await http_pool.request(
        service_name=service_name,
        method=method,
        path=full_path,
        params=params,
        json_body=json_body,
        headers=headers,
        timeout=timeout,
    )


# Convenience functions for common patterns


async def proxy_auth_request(
    method: str,
    path: str,
    request: Request,
    body: dict[str, Any] | None = None,
) -> Any:
    """
    Proxy a request to the auth service, forwarding the Authorization header.

    Args:
        method: HTTP method
        path: Path after /api/auth (e.g., "/users" -> "/api/auth/users")
        request: The incoming FastAPI request (for extracting auth headers)
        body: Optional JSON body for POST/PUT/PATCH

    Returns:
        Response from auth service
    """
    headers = extract_auth_headers(request)
    headers["Content-Type"] = "application/json"

    return await proxy_request(
        service_name="auth",
        method=method,
        path=path,
        json_body=body,
        headers=headers,
    )


async def proxy_health_request(
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> Any:
    """
    Proxy a request to the health service.

    Args:
        method: HTTP method
        path: Path after /api/health (e.g., "/check/192.168.1.1")
        params: Query parameters
        json_body: Optional JSON body
        timeout: Request timeout (default 30s)

    Returns:
        Response from health service
    """
    return await proxy_request(
        service_name="health",
        method=method,
        path=path,
        params=params,
        json_body=json_body,
        timeout=timeout,
    )


async def proxy_metrics_request(
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> Any:
    """
    Proxy a request to the metrics service.

    Args:
        method: HTTP method
        path: Path after /api/metrics (e.g., "/snapshot")
        params: Query parameters
        json_body: Optional JSON body
        timeout: Request timeout (default 30s)

    Returns:
        Response from metrics service
    """
    return await proxy_request(
        service_name="metrics",
        method=method,
        path=path,
        params=params,
        json_body=json_body,
        timeout=timeout,
    )


async def proxy_assistant_request(
    method: str,
    path: str,
    request: Request,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> Any:
    """
    Proxy a request to the assistant service, forwarding the Authorization header.

    Args:
        method: HTTP method
        path: Path after /api/assistant (e.g., "/chat")
        request: The incoming FastAPI request (for extracting auth headers)
        params: Query parameters
        json_body: Optional JSON body
        timeout: Request timeout (default 60s for AI operations)

    Returns:
        Response from assistant service
    """
    headers = extract_auth_headers(request)

    return await proxy_request(
        service_name="assistant",
        method=method,
        path=path,
        params=params,
        json_body=json_body,
        headers=headers,
        timeout=timeout,
    )


async def proxy_notification_request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
    use_user_path: bool = False,
) -> Any:
    """
    Proxy a request to the notification service.

    Args:
        method: HTTP method
        path: Path after prefix (e.g., "/preferences")
        params: Query parameters
        json_body: Optional JSON body
        headers: Additional headers (e.g., X-User-Id)
        timeout: Request timeout (default 30s)
        use_user_path: If True, use /api prefix instead of /api/notifications

    Returns:
        Response from notification service
    """
    if use_user_path:
        # Use direct API path (not /api/notifications prefix)
        custom_prefix = "/api"
    else:
        custom_prefix = None

    return await proxy_request(
        service_name="notification",
        method=method,
        path=path,
        params=params,
        json_body=json_body,
        headers=headers,
        timeout=timeout,
        custom_prefix=custom_prefix,
    )


async def proxy_cartographer_status_request(
    method: str,
    path: str,
    json_body: dict[str, Any] | None = None,
    user_id: str | None = None,
    user_email: str | None = None,
) -> Any:
    """
    Proxy a request to the Cartographer status service (notification service).

    This uses a different path prefix (/api/cartographer-status) than the
    main notification service endpoints.

    Args:
        method: HTTP method
        path: Path after /api/cartographer-status (e.g., "/subscription")
        json_body: Optional JSON body
        user_id: User ID to include in X-User-Id header
        user_email: User email to include in X-User-Email header

    Returns:
        Response from notification service
    """
    headers: dict[str, str] = {}
    if user_id:
        headers["X-User-Id"] = user_id
    if user_email:
        headers["X-User-Email"] = user_email

    return await proxy_request(
        service_name="notification",
        method=method,
        path=path,
        json_body=json_body,
        headers=headers if headers else None,
        custom_prefix="/api/cartographer-status",
    )
