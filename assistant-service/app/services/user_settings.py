"""
Helpers for resolving per-user assistant BYOK settings from auth-service.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

_PROVIDERS = ("openai", "anthropic", "gemini")
_TTL = timedelta(seconds=60)
_settings_cache: dict[str, tuple[dict[str, dict[str, str | None]], datetime]] = {}
_cache_lock = asyncio.Lock()


def _empty_settings() -> dict[str, dict[str, str | None]]:
    """Build an empty provider settings object."""
    return {provider: {"api_key": None, "model": None} for provider in _PROVIDERS}


def _normalize_settings(payload: dict) -> dict[str, dict[str, str | None]]:
    """Normalize auth-service payload into expected provider settings shape."""
    normalized = _empty_settings()
    if not isinstance(payload, dict):
        return normalized

    for provider in _PROVIDERS:
        raw_provider = payload.get(provider, {})
        if not isinstance(raw_provider, dict):
            continue

        api_key = raw_provider.get("api_key")
        if isinstance(api_key, str):
            api_key = api_key.strip() or None
        else:
            api_key = None

        model = raw_provider.get("model")
        if isinstance(model, str):
            model = model.strip() or None
        else:
            model = None

        normalized[provider] = {"api_key": api_key, "model": model}

    return normalized


async def _fetch_user_settings(user_id: str) -> dict[str, dict[str, str | None]]:
    """
    Fetch raw per-user assistant settings from auth-service internal API.

    Returns empty settings if unavailable.
    """
    if not settings.auth_service_url:
        return _empty_settings()

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.auth_service_url}/api/auth/internal/users/{user_id}/assistant-settings"
            )
    except Exception as exc:
        logger.debug("Failed to fetch assistant settings for user %s: %s", user_id, exc)
        return _empty_settings()

    if response.status_code != 200:
        return _empty_settings()

    return _normalize_settings(response.json())


async def get_user_assistant_settings(
    user_id: str, *, refresh: bool = False
) -> dict[str, dict[str, str | None]]:
    """Get per-user assistant settings with a short in-memory cache."""
    now = datetime.utcnow()

    if not refresh:
        cached = _settings_cache.get(user_id)
        if cached:
            value, cached_at = cached
            if now - cached_at < _TTL:
                return value

    async with _cache_lock:
        if not refresh:
            cached = _settings_cache.get(user_id)
            if cached:
                value, cached_at = cached
                if now - cached_at < _TTL:
                    return value

        fetched = await _fetch_user_settings(user_id)
        _settings_cache[user_id] = (fetched, now)
        return fetched


def provider_has_user_key(
    settings_by_provider: dict[str, dict[str, str | None]], provider: str
) -> bool:
    """Check if provider settings include a non-empty API key."""
    provider_settings = settings_by_provider.get(provider, {})
    api_key = provider_settings.get("api_key")
    return bool(api_key and isinstance(api_key, str))
