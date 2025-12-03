"""
Assistant Router

API endpoints for the AI assistant, including streaming chat.
"""

import os
import json
import logging
import asyncio
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..models import (
    ModelProvider,
    ChatRequest,
    ChatResponse,
    ProviderStatus,
    AssistantConfig,
    NetworkContextSummary,
)
from ..providers import (
    BaseProvider,
    ProviderConfig,
    OpenAIProvider,
    AnthropicProvider,
    GeminiProvider,
    OllamaProvider,
)
from ..providers.base import ChatMessage as ProviderChatMessage
from ..services.metrics_context import metrics_context_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["assistant"])


# ==================== Model List Cache ====================

class ModelCache:
    """Cache for provider model lists to avoid repeated API calls"""
    
    def __init__(self, ttl_seconds: int = 300):  # 5 minute cache
        self._cache: Dict[str, Tuple[List[str], datetime]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)
        self._lock = asyncio.Lock()
    
    async def get_models(self, provider: ModelProvider, provider_instance: BaseProvider) -> List[str]:
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
    
    def invalidate(self, provider: Optional[ModelProvider] = None):
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


def get_provider(provider_type: ModelProvider, config: Optional[ProviderConfig] = None) -> BaseProvider:
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
async def get_config():
    """Get assistant configuration and provider status"""
    providers_status = []
    
    # Fetch all provider statuses concurrently
    async def get_provider_status(provider_type: ModelProvider) -> ProviderStatus:
        try:
            provider = get_provider(provider_type)
            available = await provider.is_available()
            
            if available:
                models = await model_cache.get_models(provider_type, provider)
            else:
                models = []
            
            return ProviderStatus(
                provider=provider_type,
                available=available,
                configured=available,
                default_model=provider.default_model,
                available_models=models,
            )
        except Exception as e:
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
    
    return AssistantConfig(
        providers=list(providers_status),
        default_provider=default,
        network_context_enabled=True,
    )


@router.get("/providers")
async def list_providers():
    """List all providers and their availability"""
    result = []
    
    for provider_type in ModelProvider:
        try:
            provider = get_provider(provider_type)
            available = await provider.is_available()
            
            result.append({
                "provider": provider_type.value,
                "available": available,
                "default_model": provider.default_model,
            })
        except Exception as e:
            result.append({
                "provider": provider_type.value,
                "available": False,
                "error": str(e),
            })
    
    return {"providers": result}


@router.get("/models/{provider}")
async def list_models(provider: ModelProvider, refresh: bool = False):
    """List available models for a specific provider
    
    Args:
        provider: The AI provider to list models for
        refresh: If true, bypass cache and fetch fresh model list
    """
    try:
        prov = get_provider(provider)
        
        if not await prov.is_available():
            raise HTTPException(
                status_code=503,
                detail=f"Provider {provider.value} is not configured or available"
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
async def refresh_all_models():
    """Refresh model lists for all providers"""
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
async def get_network_context():
    """Get the current network context that would be provided to the assistant"""
    _, summary = await metrics_context_service.build_context_string()
    
    return NetworkContextSummary(
        total_nodes=summary.get("total_nodes", 0),
        healthy_nodes=summary.get("healthy_nodes", 0),
        unhealthy_nodes=summary.get("unhealthy_nodes", 0),
        gateway_count=summary.get("gateway_count", 0),
        snapshot_timestamp=summary.get("snapshot_timestamp"),
        context_tokens_estimate=summary.get("context_tokens_estimate", 0),
    )


@router.post("/context/refresh")
async def refresh_context():
    """Clear cached context and fetch fresh data"""
    metrics_context_service.clear_cache()
    _, summary = await metrics_context_service.build_context_string()
    
    return {
        "success": True,
        "message": "Context refreshed",
        "summary": summary,
    }


# ==================== Chat Endpoints ====================

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Non-streaming chat endpoint"""
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
                status_code=503,
                detail=f"Provider {request.provider.value} is not configured"
            )
        
        # Build system prompt with network context
        if request.include_network_context:
            context, _ = await metrics_context_service.build_context_string()
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
async def chat_stream(request: ChatRequest):
    """
    Streaming chat endpoint.
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
                status_code=503,
                detail=f"Provider {request.provider.value} is not configured"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    async def generate():
        try:
            # Build system prompt with network context
            if request.include_network_context:
                context, summary = await metrics_context_service.build_context_string()
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
