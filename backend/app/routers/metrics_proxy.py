"""
Proxy router for metrics service requests.
Forwards /api/metrics/* requests to the metrics microservice.

Performance optimizations:
- Uses shared HTTP client pool with connection reuse
- Circuit breaker prevents cascade failures
- Connections are pre-warmed on startup
- Redis caching for config, snapshots, and summaries
"""

from fastapi import APIRouter, Depends, Request, WebSocket

from ..config import get_settings
from ..dependencies import AuthenticatedUser, require_auth, require_write_access
from ..services.cache_service import CacheService, get_cache
from ..services.proxy_service import proxy_metrics_request
from ..services.websocket_proxy_service import build_ws_url, proxy_websocket

settings = get_settings()
router = APIRouter(prefix="/metrics", tags=["metrics"])


# ==================== Snapshot Endpoints ====================


@router.get("/snapshot")
async def get_snapshot(
    network_id: str | None = None, user: AuthenticatedUser = Depends(require_auth)
):
    """Proxy get current snapshot. Requires authentication.

    Args:
        network_id: Optional network ID for multi-tenant mode.
    """
    params = {}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_metrics_request("GET", "/snapshot", params=params if params else None)


@router.post("/snapshot/generate")
async def generate_snapshot(
    network_id: str | None = None, user: AuthenticatedUser = Depends(require_write_access)
):
    """Proxy generate new snapshot. Requires write access.

    Args:
        network_id: Optional network ID for multi-tenant mode.
    """
    params = {}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_metrics_request(
        "POST", "/snapshot/generate", params=params if params else None
    )


@router.post("/snapshot/publish")
async def publish_snapshot(
    network_id: str | None = None, user: AuthenticatedUser = Depends(require_write_access)
):
    """Proxy publish snapshot to Redis. Requires write access.

    Args:
        network_id: Optional network ID for multi-tenant mode.
    """
    params = {}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_metrics_request(
        "POST", "/snapshot/publish", params=params if params else None
    )


@router.get("/snapshot/cached")
async def get_cached_snapshot(user: AuthenticatedUser = Depends(require_auth)):
    """Proxy get cached snapshot from Redis. Requires authentication."""
    return await proxy_metrics_request("GET", "/snapshot/cached")


# ==================== Configuration Endpoints ====================


@router.get("/config")
async def get_config(
    user: AuthenticatedUser = Depends(require_auth),
    cache: CacheService = Depends(get_cache),
):
    """Proxy get metrics config. Requires authentication. Cached for 5 minutes."""
    cache_key = "metrics:config"
    
    async def fetch_config():
        response = await proxy_metrics_request("GET", "/config")
        if hasattr(response, "body"):
            import json
            return json.loads(response.body)
        return response
    
    return await cache.get_or_compute(cache_key, fetch_config, ttl=300)


@router.post("/config")
async def update_config(request: Request, user: AuthenticatedUser = Depends(require_write_access)):
    """Proxy update metrics config. Requires write access."""
    body = await request.json()
    return await proxy_metrics_request("POST", "/config", json_body=body)


# ==================== Summary & Data Endpoints ====================


@router.get("/summary")
async def get_summary(
    network_id: str | None = None,
    user: AuthenticatedUser = Depends(require_auth),
    cache: CacheService = Depends(get_cache),
):
    """
    Proxy get network summary. Requires authentication.
    
    Cached for 15 seconds per network - lighter weight than full snapshot.
    
    Args:
        network_id: Optional network ID for multi-tenant mode.
    """
    cache_key = cache.make_key("metrics", "summary", network_id or "default")
    
    async def fetch_summary():
        params = {}
        if network_id is not None:
            params["network_id"] = network_id
        response = await proxy_metrics_request("GET", "/summary", params=params if params else None)
        if hasattr(response, "body"):
            import json
            return json.loads(response.body)
        return response
    
    return await cache.get_or_compute(cache_key, fetch_summary, ttl=15)


@router.get("/nodes/{node_id}")
async def get_node_metrics(
    node_id: str, network_id: str | None = None, user: AuthenticatedUser = Depends(require_auth)
):
    """Proxy get specific node metrics. Requires authentication.

    Args:
        node_id: The node ID to get metrics for.
        network_id: Optional network ID for multi-tenant mode.
    """
    params = {}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_metrics_request(
        "GET", f"/nodes/{node_id}", params=params if params else None
    )


@router.get("/connections")
async def get_connections(
    network_id: str | None = None, user: AuthenticatedUser = Depends(require_auth)
):
    """Proxy get all connections. Requires authentication.

    Args:
        network_id: Optional network ID for multi-tenant mode.
    """
    params = {}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_metrics_request("GET", "/connections", params=params if params else None)


@router.get("/gateways")
async def get_gateways(
    network_id: str | None = None, user: AuthenticatedUser = Depends(require_auth)
):
    """Proxy get gateway ISP info. Requires authentication.

    Args:
        network_id: Optional network ID for multi-tenant mode.
    """
    params = {}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_metrics_request("GET", "/gateways", params=params if params else None)


# ==================== Debug Endpoints ====================


@router.get("/debug/layout")
async def debug_layout(
    network_id: str | None = None, user: AuthenticatedUser = Depends(require_auth)
):
    """Debug: Get raw layout data to verify notes are saved. Requires authentication.

    Args:
        network_id: Optional network ID for multi-tenant mode.
    """
    params = {}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_metrics_request("GET", "/debug/layout", params=params if params else None)


# ==================== Speed Test Endpoint ====================


@router.post("/speed-test")
async def trigger_speed_test(
    request: Request, user: AuthenticatedUser = Depends(require_write_access)
):
    """Proxy trigger speed test - can take 30-60 seconds. Requires write access."""
    body = await request.json()
    return await proxy_metrics_request("POST", "/speed-test", json_body=body, timeout=120.0)


# ==================== Redis Status Endpoints ====================


@router.get("/redis/status")
async def get_redis_status(user: AuthenticatedUser = Depends(require_auth)):
    """Proxy get Redis status. Requires authentication."""
    return await proxy_metrics_request("GET", "/redis/status")


@router.post("/redis/reconnect")
async def reconnect_redis(user: AuthenticatedUser = Depends(require_write_access)):
    """Proxy reconnect to Redis. Requires write access."""
    return await proxy_metrics_request("POST", "/redis/reconnect")


# ==================== WebSocket Proxy ====================

# ==================== Usage Statistics Endpoints ====================


@router.post("/usage/record")
async def record_usage(request: Request):
    """Proxy record usage event. No auth required - called by internal services."""
    body = await request.json()
    return await proxy_metrics_request("POST", "/usage/record", json_body=body)


@router.post("/usage/record/batch")
async def record_usage_batch(request: Request):
    """Proxy record batch usage events. No auth required - called by internal services."""
    body = await request.json()
    return await proxy_metrics_request("POST", "/usage/record/batch", json_body=body)


@router.get("/usage/stats")
async def get_usage_stats(
    service: str | None = None,
    user: AuthenticatedUser = Depends(require_auth),
    cache: CacheService = Depends(get_cache),
):
    """Proxy get usage stats. Requires authentication. Cached for 30 seconds."""
    cache_key = cache.make_key("metrics", "usage", "stats", service or "all")
    
    async def fetch_stats():
        params = {}
        if service:
            params["service"] = service
        response = await proxy_metrics_request("GET", "/usage/stats", params=params if params else None)
        if hasattr(response, "body"):
            import json
            return json.loads(response.body)
        return response
    
    return await cache.get_or_compute(cache_key, fetch_stats, ttl=30)


@router.delete("/usage/stats")
async def reset_usage_stats(
    service: str | None = None, user: AuthenticatedUser = Depends(require_write_access)
):
    """Proxy reset usage stats. Requires write access."""
    params = {}
    if service:
        params["service"] = service
    return await proxy_metrics_request("DELETE", "/usage/stats", params=params if params else None)


# ==================== WebSocket Proxy ====================


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Proxy WebSocket connection to metrics service.
    Note: This is a simple proxy - for production, consider direct connection to metrics service.
    """
    ws_url = build_ws_url(settings.metrics_service_url, "/api/metrics/ws")
    await proxy_websocket(websocket, ws_url)


# Alias for backwards compatibility with tests
websocket_proxy = websocket_endpoint
