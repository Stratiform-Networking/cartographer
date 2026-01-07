"""
Health service proxy.

Handles HTTP requests to the health microservice.
"""

import httpx

from ..config import get_settings


async def health_service_request(
    method: str,
    path: str,
    json_body: dict | None = None,
    timeout: float = 30.0,
) -> httpx.Response:
    """Make a request to the health service.

    Args:
        method: HTTP method (GET, POST, etc.)
        path: Path relative to /api/health
        json_body: Optional JSON body for POST requests
        timeout: Request timeout in seconds

    Returns:
        httpx.Response from the health service

    Raises:
        httpx.ConnectError: If health service is unavailable
        httpx.TimeoutException: If request times out
        ValueError: If method is not supported
    """
    settings = get_settings()
    url = f"{settings.health_service_url}/api/health{path}"

    async with httpx.AsyncClient(timeout=timeout) as client:
        if method == "GET":
            response = await client.get(url)
        elif method == "POST":
            response = await client.post(url, json=json_body)
        else:
            raise ValueError(f"Unsupported method: {method}")

        return response


async def register_devices(
    ips: list[str], network_id: str | None = None, timeout: float = 10.0
) -> httpx.Response:
    """Register devices with the health service for monitoring.

    Args:
        ips: List of IP addresses to register
        network_id: Network ID (UUID string) these devices belong to
        timeout: Request timeout in seconds

    Returns:
        Response from health service
    """
    body = {"ips": ips, "network_id": network_id or "embed"}
    return await health_service_request(
        "POST", "/monitoring/devices", json_body=body, timeout=timeout
    )


async def trigger_health_check(timeout: float = 30.0) -> httpx.Response:
    """Trigger an immediate health check.

    Args:
        timeout: Request timeout in seconds

    Returns:
        Response from health service
    """
    return await health_service_request("POST", "/monitoring/check-now", timeout=timeout)


async def get_cached_metrics(timeout: float = 10.0) -> dict:
    """Get cached health metrics for all monitored devices.

    Args:
        timeout: Request timeout in seconds

    Returns:
        Dict of ip -> metrics

    Raises:
        httpx.ConnectError: If health service is unavailable
        httpx.HTTPStatusError: If request fails
    """
    response = await health_service_request("GET", "/cached", timeout=timeout)
    response.raise_for_status()
    return response.json()
