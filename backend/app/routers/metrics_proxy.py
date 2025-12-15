"""
Proxy router for metrics service requests.
Forwards /api/metrics/* requests to the metrics microservice.

Performance optimizations:
- Uses shared HTTP client pool with connection reuse
- Circuit breaker prevents cascade failures
- Connections are pre-warmed on startup
"""
import os
import httpx
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import JSONResponse
from typing import Optional

from ..dependencies import (
    AuthenticatedUser,
    require_auth,
    require_write_access
)
from ..services.http_client import http_pool

router = APIRouter(prefix="/metrics", tags=["metrics"])

# Metrics service URL - still needed for WebSocket proxy (different protocol)
METRICS_SERVICE_URL = os.environ.get("METRICS_SERVICE_URL", "http://localhost:8003")


async def proxy_request(method: str, path: str, params: dict = None, json_body: dict = None, timeout: float = 30.0):
    """Forward a request to the metrics service using the shared client pool"""
    return await http_pool.request(
        service_name="metrics",
        method=method,
        path=f"/api/metrics{path}",
        params=params,
        json_body=json_body,
        timeout=timeout
            )


# ==================== Snapshot Endpoints ====================

@router.get("/snapshot")
async def get_snapshot(
    network_id: Optional[str] = None,
    user: AuthenticatedUser = Depends(require_auth)
):
    """Proxy get current snapshot. Requires authentication.
    
    Args:
        network_id: Optional network ID for multi-tenant mode.
    """
    params = {}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_request("GET", "/snapshot", params=params if params else None)


@router.post("/snapshot/generate")
async def generate_snapshot(
    network_id: Optional[str] = None,
    user: AuthenticatedUser = Depends(require_write_access)
):
    """Proxy generate new snapshot. Requires write access.
    
    Args:
        network_id: Optional network ID for multi-tenant mode.
    """
    params = {}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_request("POST", "/snapshot/generate", params=params if params else None)


@router.post("/snapshot/publish")
async def publish_snapshot(
    network_id: Optional[str] = None,
    user: AuthenticatedUser = Depends(require_write_access)
):
    """Proxy publish snapshot to Redis. Requires write access.
    
    Args:
        network_id: Optional network ID for multi-tenant mode.
    """
    params = {}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_request("POST", "/snapshot/publish", params=params if params else None)


@router.get("/snapshot/cached")
async def get_cached_snapshot(user: AuthenticatedUser = Depends(require_auth)):
    """Proxy get cached snapshot from Redis. Requires authentication."""
    return await proxy_request("GET", "/snapshot/cached")


# ==================== Configuration Endpoints ====================

@router.get("/config")
async def get_config(user: AuthenticatedUser = Depends(require_auth)):
    """Proxy get metrics config. Requires authentication."""
    return await proxy_request("GET", "/config")


@router.post("/config")
async def update_config(request: Request, user: AuthenticatedUser = Depends(require_write_access)):
    """Proxy update metrics config. Requires write access."""
    body = await request.json()
    return await proxy_request("POST", "/config", json_body=body)


# ==================== Summary & Data Endpoints ====================

@router.get("/summary")
async def get_summary(
    network_id: Optional[str] = None,
    user: AuthenticatedUser = Depends(require_auth)
):
    """Proxy get network summary. Requires authentication.
    
    Args:
        network_id: Optional network ID for multi-tenant mode.
    """
    params = {}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_request("GET", "/summary", params=params if params else None)


@router.get("/nodes/{node_id}")
async def get_node_metrics(
    node_id: str,
    network_id: Optional[str] = None,
    user: AuthenticatedUser = Depends(require_auth)
):
    """Proxy get specific node metrics. Requires authentication.
    
    Args:
        node_id: The node ID to get metrics for.
        network_id: Optional network ID for multi-tenant mode.
    """
    params = {}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_request("GET", f"/nodes/{node_id}", params=params if params else None)


@router.get("/connections")
async def get_connections(
    network_id: Optional[str] = None,
    user: AuthenticatedUser = Depends(require_auth)
):
    """Proxy get all connections. Requires authentication.
    
    Args:
        network_id: Optional network ID for multi-tenant mode.
    """
    params = {}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_request("GET", "/connections", params=params if params else None)


@router.get("/gateways")
async def get_gateways(
    network_id: Optional[str] = None,
    user: AuthenticatedUser = Depends(require_auth)
):
    """Proxy get gateway ISP info. Requires authentication.
    
    Args:
        network_id: Optional network ID for multi-tenant mode.
    """
    params = {}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_request("GET", "/gateways", params=params if params else None)


# ==================== Debug Endpoints ====================

@router.get("/debug/layout")
async def debug_layout(
    network_id: Optional[str] = None,
    user: AuthenticatedUser = Depends(require_auth)
):
    """Debug: Get raw layout data to verify notes are saved. Requires authentication.
    
    Args:
        network_id: Optional network ID for multi-tenant mode.
    """
    params = {}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_request("GET", "/debug/layout", params=params if params else None)


# ==================== Speed Test Endpoint ====================

@router.post("/speed-test")
async def trigger_speed_test(request: Request, user: AuthenticatedUser = Depends(require_write_access)):
    """Proxy trigger speed test - can take 30-60 seconds. Requires write access."""
    body = await request.json()
    return await proxy_request("POST", "/speed-test", json_body=body, timeout=120.0)


# ==================== Redis Status Endpoints ====================

@router.get("/redis/status")
async def get_redis_status(user: AuthenticatedUser = Depends(require_auth)):
    """Proxy get Redis status. Requires authentication."""
    return await proxy_request("GET", "/redis/status")


@router.post("/redis/reconnect")
async def reconnect_redis(user: AuthenticatedUser = Depends(require_write_access)):
    """Proxy reconnect to Redis. Requires write access."""
    return await proxy_request("POST", "/redis/reconnect")


# ==================== WebSocket Proxy ====================

# ==================== Usage Statistics Endpoints ====================

@router.post("/usage/record")
async def record_usage(request: Request):
    """Proxy record usage event. No auth required - called by internal services."""
    body = await request.json()
    return await proxy_request("POST", "/usage/record", json_body=body)


@router.post("/usage/record/batch")
async def record_usage_batch(request: Request):
    """Proxy record batch usage events. No auth required - called by internal services."""
    body = await request.json()
    return await proxy_request("POST", "/usage/record/batch", json_body=body)


@router.get("/usage/stats")
async def get_usage_stats(service: Optional[str] = None, user: AuthenticatedUser = Depends(require_auth)):
    """Proxy get usage stats. Requires authentication."""
    params = {}
    if service:
        params["service"] = service
    return await proxy_request("GET", "/usage/stats", params=params if params else None)


@router.delete("/usage/stats")
async def reset_usage_stats(service: Optional[str] = None, user: AuthenticatedUser = Depends(require_write_access)):
    """Proxy reset usage stats. Requires write access."""
    params = {}
    if service:
        params["service"] = service
    return await proxy_request("DELETE", "/usage/stats", params=params if params else None)


# ==================== WebSocket Proxy ====================

@router.websocket("/ws")
async def websocket_proxy(websocket: WebSocket):
    """
    Proxy WebSocket connection to metrics service.
    Note: This is a simple proxy - for production, consider direct connection to metrics service.
    """
    await websocket.accept()
    
    try:
        # Connect to upstream metrics service WebSocket
        async with httpx.AsyncClient() as client:
            ws_url = f"{METRICS_SERVICE_URL.replace('http', 'ws')}/api/metrics/ws"
            
            # For now, just forward messages between client and service
            # A full implementation would use websockets library for proper proxying
            import asyncio
            import websockets
            
            async with websockets.connect(ws_url) as upstream_ws:
                async def forward_to_client():
                    try:
                        async for message in upstream_ws:
                            await websocket.send_text(message)
                    except Exception:
                        pass
                
                async def forward_to_upstream():
                    try:
                        while True:
                            data = await websocket.receive_text()
                            await upstream_ws.send(data)
                    except Exception:
                        pass
                
                # Run both forwarding tasks concurrently
                await asyncio.gather(
                    forward_to_client(),
                    forward_to_upstream(),
                    return_exceptions=True
                )
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        # If websocket proxy fails, close gracefully
        try:
            await websocket.close()
        except Exception:
            pass
