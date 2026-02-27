"""
Unit tests for assistant user settings helpers.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import user_settings


@pytest.fixture(autouse=True)
def clear_user_settings_cache():
    """Isolate in-memory settings cache across tests."""
    user_settings._settings_cache.clear()
    yield
    user_settings._settings_cache.clear()


def test_empty_settings_shape():
    result = user_settings._empty_settings()
    assert set(result.keys()) == {"openai", "anthropic", "gemini"}
    assert result["openai"] == {"api_key": None, "model": None}


def test_normalize_settings_handles_invalid_payload():
    assert user_settings._normalize_settings("not-a-dict") == user_settings._empty_settings()


def test_normalize_settings_trims_and_filters_values():
    result = user_settings._normalize_settings(
        {
            "openai": {"api_key": "  sk-openai  ", "model": "  gpt-4o-mini  "},
            "anthropic": {"api_key": "", "model": "   "},
            "gemini": {"api_key": 123, "model": None},
            "other": {"api_key": "ignored", "model": "ignored"},
        }
    )

    assert result["openai"] == {"api_key": "sk-openai", "model": "gpt-4o-mini"}
    assert result["anthropic"] == {"api_key": None, "model": None}
    assert result["gemini"] == {"api_key": None, "model": None}


def test_normalize_settings_skips_non_dict_provider_payload():
    result = user_settings._normalize_settings({"openai": ["not-a-dict"]})
    assert result["openai"] == {"api_key": None, "model": None}


@pytest.mark.asyncio
async def test_fetch_user_settings_without_auth_service_url():
    with patch.object(user_settings.settings, "auth_service_url", ""):
        result = await user_settings._fetch_user_settings("user-1")
    assert result == user_settings._empty_settings()


@pytest.mark.asyncio
async def test_fetch_user_settings_handles_request_error():
    with patch.object(user_settings.settings, "auth_service_url", "http://auth-service"):
        with patch("app.services.user_settings.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = RuntimeError("network error")
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await user_settings._fetch_user_settings("user-1")

    assert result == user_settings._empty_settings()


@pytest.mark.asyncio
async def test_fetch_user_settings_handles_non_200_response():
    with patch.object(user_settings.settings, "auth_service_url", "http://auth-service"):
        with patch("app.services.user_settings.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock(status_code=503)
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await user_settings._fetch_user_settings("user-1")

    assert result == user_settings._empty_settings()


@pytest.mark.asyncio
async def test_fetch_user_settings_successfully_normalizes_payload():
    payload = {
        "openai": {"api_key": " sk-key ", "model": " gpt-model "},
        "anthropic": {"api_key": "  ", "model": "claude-3-5"},
    }
    with patch.object(user_settings.settings, "auth_service_url", "http://auth-service"):
        with patch("app.services.user_settings.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock(status_code=200)
            mock_response.json.return_value = payload
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await user_settings._fetch_user_settings("user-1")

    assert result["openai"] == {"api_key": "sk-key", "model": "gpt-model"}
    assert result["anthropic"] == {"api_key": None, "model": "claude-3-5"}
    assert result["gemini"] == {"api_key": None, "model": None}


@pytest.mark.asyncio
async def test_get_user_assistant_settings_uses_cache_and_refresh():
    cached_value = {"openai": {"api_key": "k1", "model": "m1"}}
    refreshed_value = {"openai": {"api_key": "k2", "model": "m2"}}

    with patch(
        "app.services.user_settings._fetch_user_settings",
        new=AsyncMock(side_effect=[cached_value, refreshed_value]),
    ) as mock_fetch:
        first = await user_settings.get_user_assistant_settings("user-1")
        second = await user_settings.get_user_assistant_settings("user-1")
        refreshed = await user_settings.get_user_assistant_settings("user-1", refresh=True)

    assert first == cached_value
    assert second == cached_value
    assert refreshed == refreshed_value
    assert mock_fetch.await_count == 2


@pytest.mark.asyncio
async def test_get_user_assistant_settings_double_check_after_lock():
    cached_value = {"openai": {"api_key": "k1", "model": "m1"}}

    with patch(
        "app.services.user_settings._fetch_user_settings",
        new=AsyncMock(return_value={"openai": {"api_key": "unexpected", "model": "unexpected"}}),
    ) as mock_fetch:
        await user_settings._cache_lock.acquire()
        try:
            task = asyncio.create_task(user_settings.get_user_assistant_settings("user-2"))
            await asyncio.sleep(0)
            user_settings._settings_cache["user-2"] = (cached_value, datetime.utcnow())
        finally:
            user_settings._cache_lock.release()

        result = await task

    assert result == cached_value
    mock_fetch.assert_not_awaited()


def test_provider_has_user_key():
    settings_by_provider = {
        "openai": {"api_key": "sk-openai"},
        "anthropic": {"api_key": ""},
        "gemini": {"api_key": 123},
    }

    assert user_settings.provider_has_user_key(settings_by_provider, "openai") is True
    assert user_settings.provider_has_user_key(settings_by_provider, "anthropic") is False
    assert user_settings.provider_has_user_key(settings_by_provider, "gemini") is False
    assert user_settings.provider_has_user_key(settings_by_provider, "missing") is False
