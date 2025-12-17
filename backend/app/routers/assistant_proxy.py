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


def get_auth_headers(request: Request) -> dict:
    """Extract authorization header from request to forward to assistant service"""
    headers = {}
    auth_header = request.headers.get("Authorization")
    if auth_header:
        headers["Authorization"] = auth_header
    return headers

router = APIRouter(prefix="/assistant", tags=["assistant"])

# Assistant service URL - still needed for streaming endpoint (different connection handling)
ASSISTANT_SERVICE_URL = os.environ.get("ASSISTANT_SERVICE_URL", "http://localhost:8004")


async def proxy_request(
    method: str,
    path: str,
    params: dict = None,
    json_body: dict = None,
    headers: dict = None,
    timeout: float = 60.0
):
    """Forward a request to the assistant service using the shared client pool"""
    return await http_pool.request(
        service_name="assistant",
        method=method,
        path=f"/api/assistant{path}",
        params=params,
        json_body=json_body,
        headers=headers,
        timeout=timeout
    )


# ==================== Configuration Endpoints ====================

@router.get("/config")
async def get_config(request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """Get assistant configuration. Requires authentication."""
    return await proxy_request("GET", "/config", headers=get_auth_headers(request))


@router.get("/providers")
async def list_providers(request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """List available AI providers. Requires authentication."""
    return await proxy_request("GET", "/providers", headers=get_auth_headers(request))


@router.get("/models/{provider}")
async def list_models(request: Request, provider: str, user: AuthenticatedUser = Depends(require_auth)):
    """List models for a provider. Requires authentication."""
    return await proxy_request("GET", f"/models/{provider}", headers=get_auth_headers(request))


# ==================== Context Endpoints ====================

@router.get("/context")
async def get_context(
    request: Request,
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
    return await proxy_request("GET", "/context", params=params if params else None, headers=get_auth_headers(request))


@router.post("/context/refresh")
async def refresh_context(
    request: Request,
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
    return await proxy_request("POST", "/context/refresh", params=params if params else None, headers=get_auth_headers(request))


@router.get("/context/debug")
async def get_context_debug(
    request: Request,
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
    return await proxy_request("GET", "/context/debug", params=params if params else None, headers=get_auth_headers(request))


@router.get("/context/raw")
async def get_context_raw(
    request: Request,
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
    return await proxy_request("GET", "/context/raw", params=params if params else None, headers=get_auth_headers(request))


@router.get("/context/status")
async def get_context_status(request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """Get context service status (loading/ready state). Requires authentication."""
    return await proxy_request("GET", "/context/status", headers=get_auth_headers(request))


# ==================== Chat Endpoints ====================

@router.get("/chat/limit")
async def get_chat_limit(request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """Get current chat rate limit status. Requires authentication."""
    return await proxy_request("GET", "/chat/limit", headers=get_auth_headers(request))


@router.post("/chat")
async def chat(request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """Non-streaming chat. Requires authentication."""
    body = await request.json()
    return await proxy_request("POST", "/chat", json_body=body, headers=get_auth_headers(request), timeout=120.0)


@router.post("/chat/stream")
async def chat_stream(request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """
    Streaming chat endpoint - proxies SSE from assistant service.
    Requires authentication.
    """
    body = await request.json()
    url = f"{ASSISTANT_SERVICE_URL}/api/assistant/chat/stream"
    auth_headers = get_auth_headers(request)
    
    # Create client WITHOUT context manager - we need it to stay open for streaming
    client = httpx.AsyncClient(timeout=300.0)
    
    try:
        response = await client.send(
            client.build_request("POST", url, json=body, headers=auth_headers),
            stream=True
        )
        
        # Check for error status codes BEFORE streaming
        if response.status_code == 429:
            # Rate limit exceeded - return proper error response
            try:
                error_body = await response.aread()
                import json as json_lib
                error_data = json_lib.loads(error_body)
                detail = error_data.get("detail", "Daily chat limit exceeded. Please try again tomorrow.")
            except Exception:
                detail = "Daily chat limit exceeded. Please try again tomorrow."
            
            await response.aclose()
            await client.aclose()
            raise HTTPException(
                status_code=429,
                detail=detail,
                headers={"Retry-After": response.headers.get("Retry-After", "86400")}
            )
        
        if response.status_code == 401:
            await response.aclose()
            await client.aclose()
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        if response.status_code >= 400:
            try:
                error_body = await response.aread()
                import json as json_lib
                error_data = json_lib.loads(error_body)
                detail = error_data.get("detail", f"Assistant service error: {response.status_code}")
            except Exception:
                detail = f"Assistant service error: {response.status_code}"
            await response.aclose()
            await client.aclose()
            raise HTTPException(status_code=response.status_code, detail=detail)
        
        # Stream successful response - client and response stay open
        async def stream_response():
            try:
                async for chunk in response.aiter_bytes():
                    yield chunk
            except Exception as e:
                yield f'data: {{"type": "error", "error": "{str(e)}"}}\n\n'.encode()
            finally:
                await response.aclose()
                await client.aclose()
        
        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
        
    except HTTPException:
        raise
    except httpx.ConnectError:
        await client.aclose()
        raise HTTPException(status_code=503, detail="Assistant service unavailable")
    except httpx.TimeoutException:
        await client.aclose()
        raise HTTPException(status_code=504, detail="Assistant service timeout")
    except Exception as e:
        await client.aclose()
        raise HTTPException(status_code=500, detail=str(e))
