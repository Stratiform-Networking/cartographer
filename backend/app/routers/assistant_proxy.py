"""
Proxy router for assistant service requests.
Forwards /api/assistant/* requests to the assistant microservice.

Performance optimizations:
- Uses shared HTTP client pool with connection reuse
- Circuit breaker prevents cascade failures
- Connections are pre-warmed on startup
"""
import os
import httpx
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional

from ..dependencies import (
    AuthenticatedUser,
    require_auth,
)
from ..services.http_client import http_pool

router = APIRouter(prefix="/assistant", tags=["assistant"])

# Assistant service URL - still needed for streaming endpoint (different connection handling)
ASSISTANT_SERVICE_URL = os.environ.get("ASSISTANT_SERVICE_URL", "http://localhost:8004")


async def proxy_request(method: str, path: str, params: dict = None, json_body: dict = None, timeout: float = 60.0):
    """Forward a request to the assistant service using the shared client pool"""
    return await http_pool.request(
        service_name="assistant",
        method=method,
        path=f"/api/assistant{path}",
        params=params,
        json_body=json_body,
        timeout=timeout
            )


# ==================== Configuration Endpoints ====================

@router.get("/config")
async def get_config(user: AuthenticatedUser = Depends(require_auth)):
    """Get assistant configuration. Requires authentication."""
    return await proxy_request("GET", "/config")


@router.get("/providers")
async def list_providers(user: AuthenticatedUser = Depends(require_auth)):
    """List available AI providers. Requires authentication."""
    return await proxy_request("GET", "/providers")


@router.get("/models/{provider}")
async def list_models(provider: str, user: AuthenticatedUser = Depends(require_auth)):
    """List models for a provider. Requires authentication."""
    return await proxy_request("GET", f"/models/{provider}")


# ==================== Context Endpoints ====================

@router.get("/context")
async def get_context(
    network_id: Optional[str] = None,
    user: AuthenticatedUser = Depends(require_auth)
):
    """Get network context summary. Requires authentication.
    
    Args:
        network_id: Optional network ID (UUID) for multi-tenant mode.
    """
    params = {}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_request("GET", "/context", params=params if params else None)


@router.post("/context/refresh")
async def refresh_context(
    network_id: Optional[str] = None,
    user: AuthenticatedUser = Depends(require_auth)
):
    """Refresh cached network context. Requires authentication.
    
    Args:
        network_id: Optional network ID (UUID) for multi-tenant mode.
    """
    params = {}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_request("POST", "/context/refresh", params=params if params else None)


@router.get("/context/debug")
async def get_context_debug(
    network_id: Optional[str] = None,
    user: AuthenticatedUser = Depends(require_auth)
):
    """Debug: Get full context string sent to AI. Requires authentication.
    
    Args:
        network_id: Optional network ID (UUID) for multi-tenant mode.
    """
    params = {}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_request("GET", "/context/debug", params=params if params else None)


@router.get("/context/raw")
async def get_context_raw(
    network_id: Optional[str] = None,
    user: AuthenticatedUser = Depends(require_auth)
):
    """Debug: Get raw snapshot data from metrics. Requires authentication.
    
    Args:
        network_id: Optional network ID (UUID) for multi-tenant mode.
    """
    params = {}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_request("GET", "/context/raw", params=params if params else None)


@router.get("/context/status")
async def get_context_status(user: AuthenticatedUser = Depends(require_auth)):
    """Get context service status (loading/ready state). Requires authentication."""
    return await proxy_request("GET", "/context/status")


# ==================== Chat Endpoints ====================

@router.post("/chat")
async def chat(request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """Non-streaming chat. Requires authentication."""
    body = await request.json()
    return await proxy_request("POST", "/chat", json_body=body, timeout=120.0)


@router.post("/chat/stream")
async def chat_stream(request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """
    Streaming chat endpoint - proxies SSE from assistant service.
    Requires authentication.
    """
    body = await request.json()
    url = f"{ASSISTANT_SERVICE_URL}/api/assistant/chat/stream"
    
    async def stream_proxy():
        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                async with client.stream("POST", url, json=body) as response:
                    async for chunk in response.aiter_bytes():
                        yield chunk
            except httpx.ConnectError:
                yield b'data: {"type": "error", "error": "Assistant service unavailable"}\n\n'
            except httpx.TimeoutException:
                yield b'data: {"type": "error", "error": "Assistant service timeout"}\n\n'
            except Exception as e:
                yield f'data: {{"type": "error", "error": "{str(e)}"}}\n\n'.encode()
    
    return StreamingResponse(
        stream_proxy(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
