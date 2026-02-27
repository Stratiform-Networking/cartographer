"""
Proxy router for assistant service requests.
Forwards /api/assistant/* requests to the assistant microservice.

Performance optimizations:
- Uses shared HTTP client pool with connection reuse
- Circuit breaker prevents cascade failures
- Connections are pre-warmed on startup
- Redis caching for config and providers (reduces backend load)
"""

import json

from fastapi import APIRouter, Depends, Request

from ..config import get_settings
from ..dependencies import AuthenticatedUser, require_auth
from ..services.cache_service import CacheService, get_cache
from ..services.proxy_service import extract_auth_headers, proxy_assistant_request
from ..services.streaming_service import proxy_streaming_request

settings = get_settings()
router = APIRouter(prefix="/assistant", tags=["assistant"])


# ==================== Configuration Endpoints ====================


@router.get("/config")
async def get_config(
    request: Request,
    refresh: bool = False,
    user: AuthenticatedUser = Depends(require_auth),
    cache: CacheService = Depends(get_cache),
):
    """Get assistant configuration. Requires authentication. Cached for 5 minutes."""
    cache_key = f"assistant:config:{user.user_id}"

    async def fetch_config():
        params = {"refresh": "true"} if refresh else None
        response = await proxy_assistant_request("GET", "/config", request, params=params)
        if hasattr(response, "body"):
            return json.loads(response.body)
        return response

    if refresh:
        return await fetch_config()

    return await cache.get_or_compute(cache_key, fetch_config, ttl=300)


@router.get("/providers")
async def list_providers(
    request: Request,
    refresh: bool = False,
    user: AuthenticatedUser = Depends(require_auth),
    cache: CacheService = Depends(get_cache),
):
    """List available AI providers. Requires authentication. Cached for 5 minutes."""
    cache_key = f"assistant:providers:{user.user_id}"

    async def fetch_providers():
        params = {"refresh": "true"} if refresh else None
        response = await proxy_assistant_request("GET", "/providers", request, params=params)
        if hasattr(response, "body"):
            return json.loads(response.body)
        return response

    if refresh:
        return await fetch_providers()

    return await cache.get_or_compute(cache_key, fetch_providers, ttl=300)


@router.get("/models/{provider}")
async def list_models(
    request: Request, provider: str, user: AuthenticatedUser = Depends(require_auth)
):
    """List models for a provider. Requires authentication."""
    return await proxy_assistant_request("GET", f"/models/{provider}", request)


# ==================== Context Endpoints ====================


@router.get("/context")
async def get_context(
    request: Request, network_id: str | None = None, user: AuthenticatedUser = Depends(require_auth)
):
    """Get network context summary. Requires authentication.

    Args:
        network_id: Optional network ID (UUID) for multi-tenant mode.
    """
    params = {}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_assistant_request(
        "GET", "/context", request, params=params if params else None
    )


@router.post("/context/refresh")
async def refresh_context(
    request: Request, network_id: str | None = None, user: AuthenticatedUser = Depends(require_auth)
):
    """Refresh cached network context. Requires authentication.

    Args:
        network_id: Optional network ID (UUID) for multi-tenant mode.
    """
    params = {}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_assistant_request(
        "POST", "/context/refresh", request, params=params if params else None
    )


@router.get("/context/debug")
async def get_context_debug(
    request: Request, network_id: str | None = None, user: AuthenticatedUser = Depends(require_auth)
):
    """Debug: Get full context string sent to AI. Requires authentication.

    Args:
        network_id: Optional network ID (UUID) for multi-tenant mode.
    """
    params = {}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_assistant_request(
        "GET", "/context/debug", request, params=params if params else None
    )


@router.get("/context/raw")
async def get_context_raw(
    request: Request, network_id: str | None = None, user: AuthenticatedUser = Depends(require_auth)
):
    """Debug: Get raw snapshot data from metrics. Requires authentication.

    Args:
        network_id: Optional network ID (UUID) for multi-tenant mode.
    """
    params = {}
    if network_id is not None:
        params["network_id"] = network_id
    return await proxy_assistant_request(
        "GET", "/context/raw", request, params=params if params else None
    )


@router.get("/context/status")
async def get_context_status(request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """Get context service status (loading/ready state). Requires authentication."""
    return await proxy_assistant_request("GET", "/context/status", request)


# ==================== Chat Endpoints ====================


@router.get("/chat/limit")
async def get_chat_limit(
    request: Request,
    provider: str | None = None,
    user: AuthenticatedUser = Depends(require_auth),
):
    """Get current chat rate limit status. Requires authentication."""
    params = {"provider": provider} if provider else None
    return await proxy_assistant_request("GET", "/chat/limit", request, params=params)


@router.post("/chat")
async def chat(request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """Non-streaming chat. Requires authentication."""
    body = await request.json()
    return await proxy_assistant_request("POST", "/chat", request, json_body=body, timeout=120.0)


@router.post("/chat/stream")
async def chat_stream(request: Request, user: AuthenticatedUser = Depends(require_auth)):
    """
    Streaming chat endpoint - proxies SSE from assistant service.
    Requires authentication.
    """
    body = await request.json()
    url = f"{settings.assistant_service_url}/api/assistant/chat/stream"

    return await proxy_streaming_request(
        url=url,
        method="POST",
        json_body=body,
        headers=extract_auth_headers(request),
        timeout=300.0,
    )
