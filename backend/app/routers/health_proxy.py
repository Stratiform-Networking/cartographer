"""
Proxy router for health service requests.
Forwards /api/health/* requests to the health microservice.

Performance optimizations:
- Uses shared HTTP client pool with connection reuse
- Circuit breaker prevents cascade failures
- Connections are pre-warmed on startup
"""
from fastapi import APIRouter, HTTPException, Request, Query, Depends
from fastapi.responses import JSONResponse
from typing import Optional

from ..dependencies import (
    AuthenticatedUser,
    require_auth,
    require_write_access
)
from ..services.http_client import http_pool

router = APIRouter(prefix="/health", tags=["health"])


async def proxy_request(method: str, path: str, params: dict = None, json_body: dict = None, timeout: float = 30.0):
    """Forward a request to the health service using the shared client pool"""
    return await http_pool.request(
        service_name="health",
        method=method,
        path=f"/api/health{path}",
        params=params,
        json_body=json_body,
        timeout=timeout
            )


@router.get("/check/{ip}")
async def check_device(
    ip: str,
    include_ports: bool = Query(False),
    include_dns: bool = Query(True),
    user: AuthenticatedUser = Depends(require_auth)
):
    """Proxy health check for a single device. Requires authentication."""
    return await proxy_request(
        "GET",
        f"/check/{ip}",
        params={"include_ports": include_ports, "include_dns": include_dns}
    )


@router.post("/check/batch")
async def check_batch(request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """Proxy batch health check. Requires authentication."""
    body = await request.json()
    return await proxy_request("POST", "/check/batch", json_body=body)


@router.get("/cached/{ip}")
async def get_cached(ip: str, user: AuthenticatedUser = Depends(require_auth)):
    """Proxy get cached metrics. Requires authentication."""
    return await proxy_request("GET", f"/cached/{ip}")


@router.get("/cached")
async def get_all_cached(user: AuthenticatedUser = Depends(require_auth)):
    """Proxy get all cached metrics. Requires authentication."""
    return await proxy_request("GET", "/cached")


@router.delete("/cache")
async def clear_cache(user: AuthenticatedUser = Depends(require_write_access)):
    """Proxy clear cache. Requires write access."""
    return await proxy_request("DELETE", "/cache")


@router.get("/ping/{ip}")
async def ping(ip: str, count: int = Query(3, ge=1, le=10), user: AuthenticatedUser = Depends(require_auth)):
    """Proxy quick ping. Requires authentication."""
    return await proxy_request("GET", f"/ping/{ip}", params={"count": count})


@router.get("/ports/{ip}")
async def scan_ports(ip: str, user: AuthenticatedUser = Depends(require_auth)):
    """Proxy port scan. Requires authentication."""
    return await proxy_request("GET", f"/ports/{ip}")


@router.get("/dns/{ip}")
async def check_dns(ip: str, user: AuthenticatedUser = Depends(require_auth)):
    """Proxy DNS check. Requires authentication."""
    return await proxy_request("GET", f"/dns/{ip}")


# ==================== Monitoring Endpoints ====================

@router.post("/monitoring/devices")
async def register_devices(request: Request, user: AuthenticatedUser = Depends(require_write_access)):
    """
    Proxy register devices for monitoring. Requires write access.
    
    Expects JSON body with:
    - ips: List[str] - Device IP addresses
    - network_id: str - The network UUID these devices belong to (required)
    """
    body = await request.json()
    # Validate network_id is present
    if "network_id" not in body:
        raise HTTPException(status_code=400, detail="network_id is required")
    return await proxy_request("POST", "/monitoring/devices", json_body=body)


@router.get("/monitoring/devices")
async def get_monitored_devices(user: AuthenticatedUser = Depends(require_auth)):
    """Proxy get monitored devices. Requires authentication."""
    return await proxy_request("GET", "/monitoring/devices")


@router.delete("/monitoring/devices")
async def clear_monitored_devices(user: AuthenticatedUser = Depends(require_write_access)):
    """Proxy clear monitored devices. Requires write access."""
    return await proxy_request("DELETE", "/monitoring/devices")


@router.get("/monitoring/config")
async def get_monitoring_config(user: AuthenticatedUser = Depends(require_auth)):
    """Proxy get monitoring config. Requires authentication."""
    return await proxy_request("GET", "/monitoring/config")


@router.post("/monitoring/config")
async def set_monitoring_config(request: Request, user: AuthenticatedUser = Depends(require_write_access)):
    """Proxy set monitoring config. Requires write access."""
    body = await request.json()
    return await proxy_request("POST", "/monitoring/config", json_body=body)


@router.get("/monitoring/status")
async def get_monitoring_status(user: AuthenticatedUser = Depends(require_auth)):
    """Proxy get monitoring status. Requires authentication."""
    return await proxy_request("GET", "/monitoring/status")


@router.post("/monitoring/start")
async def start_monitoring(user: AuthenticatedUser = Depends(require_write_access)):
    """Proxy start monitoring. Requires write access."""
    return await proxy_request("POST", "/monitoring/start")


@router.post("/monitoring/stop")
async def stop_monitoring(user: AuthenticatedUser = Depends(require_write_access)):
    """Proxy stop monitoring. Requires write access."""
    return await proxy_request("POST", "/monitoring/stop")


@router.post("/monitoring/check-now")
async def trigger_check(user: AuthenticatedUser = Depends(require_write_access)):
    """Proxy trigger immediate check. Requires write access."""
    return await proxy_request("POST", "/monitoring/check-now")


# ==================== Gateway Test IP Endpoints ====================

# Note: Specific route must come before parameterized routes
@router.get("/gateway/test-ips/all")
async def get_all_gateway_test_ips(user: AuthenticatedUser = Depends(require_auth)):
    """Proxy get all gateway test IP configurations. Requires authentication."""
    return await proxy_request("GET", "/gateway/test-ips/all")


@router.post("/gateway/{gateway_ip}/test-ips")
async def set_gateway_test_ips(gateway_ip: str, request: Request, user: AuthenticatedUser = Depends(require_write_access)):
    """Proxy set test IPs for a gateway. Requires write access."""
    body = await request.json()
    return await proxy_request("POST", f"/gateway/{gateway_ip}/test-ips", json_body=body)


@router.get("/gateway/{gateway_ip}/test-ips")
async def get_gateway_test_ips(gateway_ip: str, user: AuthenticatedUser = Depends(require_auth)):
    """Proxy get test IPs for a gateway. Requires authentication."""
    return await proxy_request("GET", f"/gateway/{gateway_ip}/test-ips")


@router.delete("/gateway/{gateway_ip}/test-ips")
async def remove_gateway_test_ips(gateway_ip: str, user: AuthenticatedUser = Depends(require_write_access)):
    """Proxy remove test IPs for a gateway. Requires write access."""
    return await proxy_request("DELETE", f"/gateway/{gateway_ip}/test-ips")


@router.get("/gateway/{gateway_ip}/test-ips/check")
async def check_gateway_test_ips(gateway_ip: str, user: AuthenticatedUser = Depends(require_auth)):
    """Proxy check test IPs for a gateway. Requires authentication."""
    return await proxy_request("GET", f"/gateway/{gateway_ip}/test-ips/check")


@router.get("/gateway/{gateway_ip}/test-ips/cached")
async def get_cached_test_ip_metrics(gateway_ip: str, user: AuthenticatedUser = Depends(require_auth)):
    """Proxy get cached test IP metrics for a gateway. Requires authentication."""
    return await proxy_request("GET", f"/gateway/{gateway_ip}/test-ips/cached")


# ==================== Speed Test Endpoints ====================

@router.post("/speedtest")
async def run_speed_test(user: AuthenticatedUser = Depends(require_write_access)):
    """Proxy run speed test - can take 30-60 seconds. Requires write access."""
    return await proxy_request("POST", "/speedtest", timeout=120.0)  # 2 minute timeout for speed test


@router.get("/speedtest/all")
async def get_all_speed_tests(user: AuthenticatedUser = Depends(require_auth)):
    """Proxy get all stored speed test results. Requires authentication."""
    return await proxy_request("GET", "/speedtest/all")


@router.get("/gateway/{gateway_ip}/speedtest")
async def get_gateway_speed_test(gateway_ip: str, user: AuthenticatedUser = Depends(require_auth)):
    """Proxy get last speed test result for a gateway. Requires authentication."""
    return await proxy_request("GET", f"/gateway/{gateway_ip}/speedtest")


@router.post("/gateway/{gateway_ip}/speedtest")
async def run_gateway_speed_test(gateway_ip: str, user: AuthenticatedUser = Depends(require_write_access)):
    """Proxy run speed test for a specific gateway - can take 30-60 seconds. Requires write access."""
    return await proxy_request("POST", f"/gateway/{gateway_ip}/speedtest", timeout=120.0)
