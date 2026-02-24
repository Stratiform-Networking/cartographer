"""Unit tests for centralized user plan settings service."""

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.services.plan_settings as plan_settings


@pytest.fixture(autouse=True)
def clear_plan_limits_cache():
    plan_settings._load_all_plan_limits.cache_clear()
    yield
    plan_settings._load_all_plan_limits.cache_clear()


def _result(value):
    return SimpleNamespace(scalar_one_or_none=lambda: value)


class TestPlanConfigLoading:
    def test_normalize_plan_id_defaults_and_lowercases(self):
        assert plan_settings._normalize_plan_id(None) == "free"
        assert plan_settings._normalize_plan_id("  ProPlus ") == "proplus"
        assert plan_settings._normalize_plan_id("   ") == "free"

    def test_tier_config_dir_points_to_subscription_tiers(self):
        path = plan_settings._tier_config_dir()
        assert str(path).endswith("cartographer-cloud/backend/config/subscription_tiers")

    def test_load_all_plan_limits_uses_fallback_when_directory_missing(self):
        missing = Path("/tmp/definitely-missing-subscription-tier-dir")
        with patch.object(plan_settings, "_tier_config_dir", return_value=missing):
            loaded = plan_settings._load_all_plan_limits()

        assert loaded["free"]["owned_networks_limit"] == 1
        assert loaded["pro"]["assistant_daily_chat_messages_limit"] == 50

    def test_load_all_plan_limits_reads_yaml_and_skips_bad_files(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            (tmp_path / "pro.yaml").write_text(
                "\n".join(
                    [
                        "tier_id: pro",
                        "limits:",
                        "  owned_networks_limit: 7",
                        "  assistant_daily_chat_messages_limit: 123",
                        "  automatic_full_scan_min_interval_seconds: 42",
                        "  health_poll_interval_seconds: 9",
                    ]
                ),
                encoding="utf-8",
            )
            (tmp_path / "broken.yaml").write_text("limits: [", encoding="utf-8")
            (tmp_path / "partial.yaml").write_text(
                "\n".join(
                    [
                        "tier_id: enterprise",
                        "limits:",
                        "  owned_networks_limit: -1",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.object(plan_settings, "_tier_config_dir", return_value=tmp_path):
                loaded = plan_settings._load_all_plan_limits()

        assert loaded["pro"]["owned_networks_limit"] == 7
        assert loaded["pro"]["assistant_daily_chat_messages_limit"] == 123
        assert loaded["pro"]["automatic_full_scan_min_interval_seconds"] == 42
        assert loaded["pro"]["health_poll_interval_seconds"] == 9
        # Partial file should not overwrite fallback/defaults for enterprise
        assert loaded["enterprise"]["assistant_daily_chat_messages_limit"] == -1

    def test_resolve_plan_limits_unknown_plan_defaults_to_free(self):
        with patch.object(
            plan_settings,
            "_load_all_plan_limits",
            return_value={
                "free": {
                    "owned_networks_limit": 1,
                    "assistant_daily_chat_messages_limit": 5,
                    "automatic_full_scan_min_interval_seconds": 7200,
                    "health_poll_interval_seconds": 60,
                }
            },
        ):
            plan_id, limits = plan_settings.resolve_plan_limits("unknown-plan")

        assert plan_id == "free"
        assert limits["owned_networks_limit"] == 1


@pytest.mark.asyncio
class TestPlanSettingsPersistence:
    async def test_get_user_plan_settings_returns_existing_row(self):
        row = plan_settings.UserPlanSettings(user_id="user-1")
        db = MagicMock()
        db.execute = AsyncMock(return_value=_result(row))

        result = await plan_settings.get_user_plan_settings(db, "user-1", create_if_missing=True)

        assert result is row

    async def test_get_user_plan_settings_returns_none_when_missing_and_no_create(self):
        db = MagicMock()
        db.execute = AsyncMock(return_value=_result(None))

        result = await plan_settings.get_user_plan_settings(db, "user-1", create_if_missing=False)

        assert result is None

    async def test_get_user_plan_settings_creates_row_when_missing(self):
        db = MagicMock()
        db.execute = AsyncMock(return_value=_result(None))
        created = plan_settings.UserPlanSettings(user_id="user-1")

        with patch.object(
            plan_settings, "apply_plan_to_user", AsyncMock(return_value=created)
        ) as mock_apply:
            result = await plan_settings.get_user_plan_settings(
                db, "user-1", create_if_missing=True
            )

        assert result is created
        mock_apply.assert_awaited_once_with(
            db, user_id="user-1", plan_id=plan_settings.DEFAULT_PLAN_ID, commit=True
        )

    async def test_apply_plan_to_user_creates_and_commits(self):
        db = MagicMock()
        db.add = MagicMock()
        db.execute = AsyncMock(return_value=_result(None))
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.flush = AsyncMock()

        limits = {
            "owned_networks_limit": 3,
            "assistant_daily_chat_messages_limit": 50,
            "automatic_full_scan_min_interval_seconds": 60,
            "health_poll_interval_seconds": 30,
        }
        with patch.object(plan_settings, "resolve_plan_limits", return_value=("pro", limits)):
            row = await plan_settings.apply_plan_to_user(db, "user-1", "pro", commit=True)

        assert row.plan_id == "pro"
        assert row.owned_networks_limit == 3
        db.add.assert_called_once()
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once_with(row)
        db.flush.assert_not_awaited()

    async def test_apply_plan_to_user_updates_existing_and_flushes(self):
        existing = plan_settings.UserPlanSettings(user_id="user-2")
        db = MagicMock()
        db.add = MagicMock()
        db.execute = AsyncMock(return_value=_result(existing))
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.flush = AsyncMock()

        limits = {
            "owned_networks_limit": 20,
            "assistant_daily_chat_messages_limit": -1,
            "automatic_full_scan_min_interval_seconds": 30,
            "health_poll_interval_seconds": 5,
        }
        with patch.object(plan_settings, "resolve_plan_limits", return_value=("proplus", limits)):
            row = await plan_settings.apply_plan_to_user(db, "user-2", "proplus", commit=False)

        assert row is existing
        assert row.plan_id == "proplus"
        assert row.assistant_daily_chat_messages_limit == -1
        db.add.assert_not_called()
        db.flush.assert_awaited_once()
        db.commit.assert_not_awaited()
        db.refresh.assert_not_awaited()

    async def test_initialize_default_plan_settings_skips_non_async_session(self):
        db = MagicMock()

        result = await plan_settings.initialize_default_plan_settings_for_new_user(db, "user-1")

        assert result is None

    async def test_initialize_default_plan_settings_adds_row_and_flushes_for_async_session(self):
        class FakeAsyncSession:
            def __init__(self):
                self.add = MagicMock()
                self.flush = AsyncMock()
                self.commit = AsyncMock()
                self.refresh = AsyncMock()

        db = FakeAsyncSession()
        limits = {
            "owned_networks_limit": 1,
            "assistant_daily_chat_messages_limit": 5,
            "automatic_full_scan_min_interval_seconds": 7200,
            "health_poll_interval_seconds": 60,
        }

        with (
            patch.object(plan_settings, "AsyncSession", FakeAsyncSession),
            patch.object(plan_settings, "resolve_plan_limits", return_value=("free", limits)),
        ):
            row = await plan_settings.initialize_default_plan_settings_for_new_user(
                db, "user-3", commit=False
            )

        assert row is not None
        assert row.user_id == "user-3"
        db.add.assert_called_once()
        db.flush.assert_awaited_once()
        db.commit.assert_not_awaited()
        db.refresh.assert_not_awaited()

    async def test_initialize_default_plan_settings_can_commit(self):
        class FakeAsyncSession:
            def __init__(self):
                self.add = MagicMock()
                self.flush = AsyncMock()
                self.commit = AsyncMock()
                self.refresh = AsyncMock()

        db = FakeAsyncSession()
        limits = {
            "owned_networks_limit": 1,
            "assistant_daily_chat_messages_limit": 5,
            "automatic_full_scan_min_interval_seconds": 7200,
            "health_poll_interval_seconds": 60,
        }

        with (
            patch.object(plan_settings, "AsyncSession", FakeAsyncSession),
            patch.object(plan_settings, "resolve_plan_limits", return_value=("free", limits)),
        ):
            row = await plan_settings.initialize_default_plan_settings_for_new_user(
                db, "user-4", commit=True
            )

        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once_with(row)
