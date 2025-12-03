"""
Proxy router for assistant service requests.
Forwards /api/assistant/* requests to the assistant microservice.
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

router = APIRouter(prefix="/assistant", tags=["assistant"])

# Assistant service URL - defaults to localhost:8004 for host network mode
ASSISTANT_SERVICE_URL = os.environ.get("ASSISTANT_SERVICE_URL", "http://localhost:8004")


async def proxy_request(method: str, path: str, params: dict = None, json_body: dict = None, timeout: float = 60.0):
    """Forward a request to the assistant service"""
    url = f"{ASSISTANT_SERVICE_URL}/api/assistant{path}"
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            if method == "GET":
                response = await client.get(url, params=params)
            elif method == "POST":
                response = await client.post(url, params=params, json=json_body)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")
            
            return JSONResponse(
                content=response.json(),
                status_code=response.status_code
            )
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail="Assistant service unavailable"
            )
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Assistant service timeout"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Assistant service error: {str(e)}"
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
async def get_context(user: AuthenticatedUser = Depends(require_auth)):
    """Get network context summary. Requires authentication."""
    return await proxy_request("GET", "/context")


@router.post("/context/refresh")
async def refresh_context(user: AuthenticatedUser = Depends(require_auth)):
    """Refresh cached network context. Requires authentication."""
    return await proxy_request("POST", "/context/refresh")


@router.get("/context/debug")
async def get_context_debug(user: AuthenticatedUser = Depends(require_auth)):
    """Debug: Get full context string sent to AI. Requires authentication."""
    return await proxy_request("GET", "/context/debug")


@router.get("/context/raw")
async def get_context_raw(user: AuthenticatedUser = Depends(require_auth)):
    """Debug: Get raw snapshot data from metrics. Requires authentication."""
    return await proxy_request("GET", "/context/raw")


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
