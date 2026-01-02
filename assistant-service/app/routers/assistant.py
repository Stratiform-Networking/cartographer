"""
Assistant Router

API endpoints for the AI assistant, including streaming chat.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any

import httpx
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..config import settings
from ..dependencies import AuthenticatedUser, require_auth, require_auth_with_rate_limit
from ..models import (
    AssistantConfig,
    ChatRequest,
    ChatResponse,
    ModelProvider,
    NetworkContextSummary,
    ProviderStatus,
)
from ..providers import (
    AnthropicProvider,
    BaseProvider,
    GeminiProvider,
    OllamaProvider,
    OpenAIProvider,
    ProviderConfig,
)
from ..providers.base import ChatMessage as ProviderChatMessage
from ..services.metrics_context import metrics_context_service
from ..services.rate_limit import get_rate_limit_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["assistant"])


# ==================== Redis Cache ====================

_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis | None:
    """Get Redis client (cached)"""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = await aioredis.from_url(
                settings.redis_url,
                db=settings.redis_db,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2.0,
            )
            await _redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Caching disabled.")
            _redis_client = None
    return _redis_client


# ==================== Model List Cache ====================


class ModelCache:
    """Cache for provider model lists to avoid repeated API calls"""

    def __init__(self, ttl_seconds: int = 300):  # 5 minute cache
        self._cache: dict[str, tuple[list[str], datetime]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)
        self._lock = asyncio.Lock()

    async def get_models(
        self, provider: ModelProvider, provider_instance: BaseProvider
    ) -> list[str]:
        """Get models for a provider, using cache if available"""
        cache_key = provider.value
        now = datetime.utcnow()

        # Check cache
        if cache_key in self._cache:
            models, cached_at = self._cache[cache_key]
            if now - cached_at < self._ttl:
                return models

        # Fetch fresh models
        async with self._lock:
            # Double-check after acquiring lock
            if cache_key in self._cache:
                models, cached_at = self._cache[cache_key]
                if now - cached_at < self._ttl:
                    return models

            # Fetch from API - let exceptions propagate
            models = await provider_instance.list_models()
            self._cache[cache_key] = (models, now)
            logger.info(f"Cached {len(models)} models for {provider.value}")
            return models

    def invalidate(self, provider: ModelProvider | None = None):
        """Invalidate cache for a specific provider or all providers"""
        if provider:
            self._cache.pop(provider.value, None)
        else:
            self._cache.clear()


# Global model cache
model_cache = ModelCache()


# System prompt for the assistant
SYSTEM_PROMPT_TEMPLATE = """You are Cartographer Assistant, an AI helper for the Cartographer network mapping and monitoring application.

Your role is to:
- Help users understand their network topology and device status
- Answer questions about network health, connectivity, and performance
- Provide troubleshooting guidance for network issues
- Explain networking concepts when asked
- Suggest optimizations based on the network data

Guidelines:
- Be concise but thorough in your responses
- When referring to specific devices, use their names and IP addresses
- If you notice any unhealthy or degraded devices, proactively mention them if relevant
- For troubleshooting, provide step-by-step guidance
- If you don't have enough information to answer, say so and suggest what data would help

{network_context}
"""


def get_provider(
    provider_type: ModelProvider, config: ProviderConfig | None = None
) -> BaseProvider:
    """Get the appropriate provider instance"""
    if config is None:
        config = ProviderConfig()

    providers = {
        ModelProvider.OPENAI: OpenAIProvider,
        ModelProvider.ANTHROPIC: AnthropicProvider,
        ModelProvider.GEMINI: GeminiProvider,
        ModelProvider.OLLAMA: OllamaProvider,
    }

    provider_class = providers.get(provider_type)
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider_type}")

    return provider_class(config)


# ==================== Configuration Endpoints ====================


@router.get("/config", response_model=AssistantConfig)
async def get_config(user: AuthenticatedUser = Depends(require_auth)):
    """
    Get assistant configuration and provider status. Requires authentication.

    Implements caching with 5-minute TTL to avoid repeated provider checks.
    """
    cache_key = "assistant:config"
    redis = await get_redis()

    # Try cache first
    if redis:
        try:
            cached = await redis.get(cache_key)
            if cached:
                logger.debug(f"Cache HIT: {cache_key}")
                cached_data = json.loads(cached)
                # Convert back to AssistantConfig model
                return AssistantConfig(**cached_data)
        except Exception as e:
            logger.warning(f"Cache read error: {e}")

    # Cache miss - compute result
    providers_status = []

    # Fetch all provider statuses concurrently
    async def get_provider_status(provider_type: ModelProvider) -> ProviderStatus:
        try:
            provider = get_provider(provider_type)
            available = await provider.is_available()

            if not available:
                return ProviderStatus(
                    provider=provider_type,
                    available=False,
                    configured=False,
                    default_model=provider.default_model,
                )

            # Try to get models, but don't fail the whole provider if this fails
            models = []
            error_msg = None
            try:
                models = await model_cache.get_models(provider_type, provider)
            except Exception as e:
                logger.warning(f"Failed to list models for {provider_type.value}: {e}")
                error_msg = f"Could not list models: {str(e)}"
                # Use default model as fallback
                models = [provider.default_model]

            return ProviderStatus(
                provider=provider_type,
                available=True,
                configured=True,
                default_model=provider.default_model,
                available_models=models,
                error=error_msg,
            )
        except Exception as e:
            logger.error(f"Error checking provider {provider_type.value}: {e}")
            return ProviderStatus(
                provider=provider_type,
                available=False,
                configured=False,
                default_model="",
                error=str(e),
            )

    # Run all provider checks concurrently
    tasks = [get_provider_status(pt) for pt in ModelProvider]
    providers_status = await asyncio.gather(*tasks)

    # Determine default provider (first available)
    default = ModelProvider.OPENAI
    for status in providers_status:
        if status.available:
            default = status.provider
            break

    result = AssistantConfig(
        providers=list(providers_status),
        default_provider=default,
        network_context_enabled=True,
    )

    # Cache the result (best effort)
    if redis:
        try:
            # Convert Pydantic model to dict for JSON serialization
            await redis.setex(
                cache_key, settings.cache_ttl_providers, json.dumps(result.model_dump())
            )
            logger.debug(f"Cache SET: {cache_key} (TTL: {settings.cache_ttl_providers}s)")
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    return result


@router.get("/providers")
async def list_providers(user: AuthenticatedUser = Depends(require_auth)):
    """
    List all providers and their availability. Requires authentication.

    Implements caching with 5-minute TTL to avoid repeated provider checks.
    """
    cache_key = "providers:list"
    redis = await get_redis()

    # Try cache first
    if redis:
        try:
            cached = await redis.get(cache_key)
            if cached:
                logger.debug(f"Cache HIT: {cache_key}")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache read error: {e}")

    # Cache miss - compute result
    result = []

    for provider_type in ModelProvider:
        try:
            provider = get_provider(provider_type)
            available = await provider.is_available()

            result.append(
                {
                    "provider": provider_type.value,
                    "available": available,
                    "default_model": provider.default_model,
                }
            )
        except Exception as e:
            result.append(
                {
                    "provider": provider_type.value,
                    "available": False,
                    "error": str(e),
                }
            )

    response = {"providers": result}

    # Cache the result (best effort)
    if redis:
        try:
            await redis.setex(cache_key, settings.cache_ttl_providers, json.dumps(response))
            logger.debug(f"Cache SET: {cache_key} (TTL: {settings.cache_ttl_providers}s)")
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    return response


@router.get("/models/{provider}")
async def list_models(
    provider: ModelProvider, refresh: bool = False, user: AuthenticatedUser = Depends(require_auth)
):
    """List available models for a specific provider. Requires authentication.

    Args:
        provider: The AI provider to list models for
        refresh: If true, bypass cache and fetch fresh model list
    """
    try:
        prov = get_provider(provider)

        if not await prov.is_available():
            raise HTTPException(
                status_code=503, detail=f"Provider {provider.value} is not configured or available"
            )

        if refresh:
            model_cache.invalidate(provider)

        models = await model_cache.get_models(provider, prov)
        return {
            "provider": provider.value,
            "models": models,
            "default": prov.default_model,
            "cached": not refresh,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/refresh")
async def refresh_all_models(user: AuthenticatedUser = Depends(require_auth)):
    """Refresh model lists for all providers. Requires authentication."""
    model_cache.invalidate()

    results = {}
    for provider_type in ModelProvider:
        try:
            prov = get_provider(provider_type)
            if await prov.is_available():
                models = await model_cache.get_models(provider_type, prov)
                results[provider_type.value] = {
                    "success": True,
                    "count": len(models),
                    "models": models,
                }
            else:
                results[provider_type.value] = {
                    "success": False,
                    "error": "Provider not available",
                }
        except Exception as e:
            results[provider_type.value] = {
                "success": False,
                "error": str(e),
            }

    return {"refreshed": True, "providers": results}


# ==================== Context Endpoints ====================


@router.get("/context", response_model=NetworkContextSummary)
async def get_network_context(
    network_id: str | None = Query(None, description="Network ID for multi-tenant mode"),
    user: AuthenticatedUser = Depends(require_auth),
):
    """Get the current network context that would be provided to the assistant. Requires authentication.

    Args:
        network_id: Optional network ID for multi-tenant mode. If not provided,
                   uses legacy single-network mode.
    """
    _, summary = await metrics_context_service.build_context_string(network_id=network_id)

    return NetworkContextSummary(
        total_nodes=summary.get("total_nodes", 0),
        healthy_nodes=summary.get("healthy_nodes", 0),
        unhealthy_nodes=summary.get("unhealthy_nodes", 0),
        gateway_count=summary.get("gateway_count", 0),
        snapshot_timestamp=summary.get("snapshot_timestamp"),
        context_tokens_estimate=summary.get("context_tokens_estimate", 0),
    )


@router.post("/context/refresh")
async def refresh_context(
    network_id: str | None = Query(None, description="Network ID for multi-tenant mode"),
    user: AuthenticatedUser = Depends(require_auth),
):
    """Clear cached context and fetch fresh data from the metrics service. Requires authentication.

    This triggers the metrics service to regenerate its snapshot with
    the latest data (including recent speed test results, health checks, etc.)
    before building the context string.

    Args:
        network_id: Optional network ID for multi-tenant mode.
    """
    metrics_context_service.clear_cache()
    # Use force_refresh=True to tell the metrics service to regenerate its snapshot
    _, summary = await metrics_context_service.build_context_string(
        force_refresh=True, network_id=network_id
    )

    return {
        "success": True,
        "message": "Context refreshed",
        "summary": summary,
    }


@router.get("/context/status")
async def get_context_status(user: AuthenticatedUser = Depends(require_auth)):
    """Get the current status of the context service. Requires authentication."""
    status = metrics_context_service.get_status()

    # Add additional info
    status["loading"] = not status["snapshot_available"]
    status["ready"] = status["snapshot_available"]

    return status


@router.get("/context/debug")
async def get_context_debug(
    network_id: str | None = Query(None, description="Network ID for multi-tenant mode"),
    user: AuthenticatedUser = Depends(require_auth),
):
    """Debug endpoint to see the full context string being sent to AI. Requires authentication.

    Args:
        network_id: Optional network ID for multi-tenant mode.
    """
    metrics_context_service.clear_cache()  # Force fresh data
    context_string, summary = await metrics_context_service.build_context_string(
        network_id=network_id
    )

    return {
        "context_string": context_string,
        "summary": summary,
        "context_length": len(context_string),
    }


@router.get("/context/raw")
async def get_context_raw(
    network_id: str | None = Query(None, description="Network ID for multi-tenant mode"),
    user: AuthenticatedUser = Depends(require_auth),
):
    """Debug endpoint to see raw snapshot data from metrics service. Requires authentication.

    Args:
        network_id: Optional network ID for multi-tenant mode.
    """
    # First, let's get the raw snapshot from metrics service
    snapshot = await metrics_context_service.fetch_network_snapshot(network_id=network_id)

    # Also try to get the layout directly to compare
    layout_data = None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            params: dict[str, Any] = {}
            if network_id is not None:
                params["network_id"] = network_id
            response = await client.get(
                f"{settings.metrics_service_url}/api/metrics/debug/layout", params=params
            )
            if response.status_code == 200:
                layout_data = response.json()
    except Exception as e:
        layout_data = {"error": str(e)}

    if not snapshot:
        return {
            "error": "Failed to fetch snapshot from metrics service",
            "layout_debug": layout_data,
        }

    # Extract key data for debugging
    nodes = snapshot.get("nodes", {})
    gateways = snapshot.get("gateways", [])

    # Get detailed node info
    node_details = []
    for node_id, node in nodes.items():
        node_details.append(
            {
                "id": node_id,
                "name": node.get("name"),
                "ip": node.get("ip"),
                "role": node.get("role"),
                "notes": node.get("notes"),
                "has_isp_info": node.get("isp_info") is not None,
            }
        )

    # Get gateway details
    gateway_details = []
    for gw in gateways:
        gw_detail = {
            "gateway_ip": gw.get("gateway_ip"),
            "test_ips": [],
            "has_speed_test": gw.get("last_speed_test") is not None,
            "speed_test": None,
        }
        # Include speed test details if available
        speed_test = gw.get("last_speed_test")
        if speed_test:
            gw_detail["speed_test"] = {
                "success": speed_test.get("success"),
                "download_mbps": speed_test.get("download_mbps"),
                "upload_mbps": speed_test.get("upload_mbps"),
                "ping_ms": speed_test.get("ping_ms"),
                "client_isp": speed_test.get("client_isp"),
                "server_sponsor": speed_test.get("server_sponsor"),
                "server_location": speed_test.get("server_location"),
                "timestamp": (
                    str(speed_test.get("timestamp")) if speed_test.get("timestamp") else None
                ),
            }
        for tip in gw.get("test_ips", []):
            gw_detail["test_ips"].append(
                {
                    "ip": tip.get("ip"),
                    "label": tip.get("label"),
                    "status": tip.get("status"),
                    "status_type": str(type(tip.get("status"))),
                }
            )
        gateway_details.append(gw_detail)

    # Filter to count only actual devices (exclude groups, matching frontend)
    device_count = sum(
        1 for node_id, node in nodes.items() if node.get("role", "").lower() != "group"
    )

    return {
        "snapshot_available": True,
        "total_nodes": device_count,
        "total_tree_nodes": len(nodes),
        "total_gateways": len(gateways),
        "nodes": node_details,
        "gateways": gateway_details,
        "layout_debug": layout_data,
    }


# ==================== Chat Endpoints ====================

# Create a rate-limited auth dependency for chat endpoints
require_chat_auth = require_auth_with_rate_limit(settings.assistant_chat_limit_per_day, "chat")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, user: AuthenticatedUser = Depends(require_chat_auth)):
    """Non-streaming chat endpoint. Requires authentication and is rate-limited."""
    # Get provider
    provider_config = ProviderConfig(
        model=request.model,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )

    try:
        provider = get_provider(request.provider, provider_config)

        if not await provider.is_available():
            raise HTTPException(
                status_code=503, detail=f"Provider {request.provider.value} is not configured"
            )

        # Build system prompt with network context
        if request.include_network_context:
            context, _ = await metrics_context_service.build_context_string(
                network_id=request.network_id
            )
            system_prompt = SYSTEM_PROMPT_TEMPLATE.format(network_context=context)
        else:
            system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
                network_context="(Network context not included in this request)"
            )

        # Convert conversation history
        messages = [
            ProviderChatMessage(role=msg.role.value, content=msg.content)
            for msg in request.conversation_history
        ]

        # Add current message
        messages.append(ProviderChatMessage(role="user", content=request.message))

        # Get response
        response_text = await provider.chat(messages, system_prompt)

        return ChatResponse(
            message=response_text,
            provider=request.provider,
            model=request.model or provider.default_model,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, user: AuthenticatedUser = Depends(require_chat_auth)):
    """
    Streaming chat endpoint. Requires authentication and is rate-limited.
    Returns Server-Sent Events (SSE) with response chunks.
    """
    # Get provider
    provider_config = ProviderConfig(
        model=request.model,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )

    try:
        provider = get_provider(request.provider, provider_config)

        if not await provider.is_available():
            raise HTTPException(
                status_code=503, detail=f"Provider {request.provider.value} is not configured"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    async def generate():
        try:
            # Build system prompt with network context
            if request.include_network_context:
                context, summary = await metrics_context_service.build_context_string(
                    network_id=request.network_id
                )
                system_prompt = SYSTEM_PROMPT_TEMPLATE.format(network_context=context)

                # Send context summary first
                yield f"data: {json.dumps({'type': 'context', 'summary': summary})}\n\n"
            else:
                system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
                    network_context="(Network context not included in this request)"
                )

            # Convert conversation history
            messages = [
                ProviderChatMessage(role=msg.role.value, content=msg.content)
                for msg in request.conversation_history
            ]

            # Add current message
            messages.append(ProviderChatMessage(role="user", content=request.message))

            # Stream response
            async for chunk in provider.stream_chat(messages, system_prompt):
                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"

            # Send done signal
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# ==================== Rate Limit Status ====================


@router.get("/chat/limit")
async def get_chat_limit_status(user: AuthenticatedUser = Depends(require_auth)):
    """
    Get the current chat rate limit status for the authenticated user.
    Returns usage count, limit, remaining, time until reset, and exempt status.

    Users with roles in ASSISTANT_RATE_LIMIT_EXEMPT_ROLES have unlimited access.
    """
    status = await get_rate_limit_status(
        user.user_id, "chat", settings.assistant_chat_limit_per_day, user_role=user.role.value
    )

    # If user is exempt, they have unlimited access
    if status.get("is_exempt"):
        return {
            "used": status["used"],
            "limit": status["limit"],
            "remaining": status["remaining"],
            "resets_in_seconds": status["resets_in_seconds"],
            "is_limited": False,
            "is_exempt": True,
        }

    return {
        "used": status["used"],
        "limit": status["limit"],
        "remaining": status["remaining"],
        "resets_in_seconds": status["resets_in_seconds"],
        "is_limited": status["remaining"] <= 0,
        "is_exempt": False,
    }
