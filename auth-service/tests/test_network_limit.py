"""Unit tests for network limit service logic."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.services import network_limit as network_limit_service


def _mock_db_with_user_limit(user_limit):
    """Create a DB mock that returns a single UserLimit lookup result."""
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user_limit
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


class TestIsRoleExempt:
    def test_is_role_exempt_is_case_insensitive(self):
        with patch.object(
            network_limit_service.settings,
            "network_limit_exempt_roles",
            "owner,admin",
        ):
            assert network_limit_service.is_role_exempt("AdMiN") is True
            assert network_limit_service.is_role_exempt("member") is False


class TestGetUserNetworkLimit:
    async def test_creates_unlimited_record_for_exempt_user_without_existing_limit(self):
        db = _mock_db_with_user_limit(None)

        with (
            patch.object(network_limit_service.settings, "network_limit_per_user", 2),
            patch.object(
                network_limit_service.settings, "network_limit_exempt_roles", "owner,admin"
            ),
        ):
            limit = await network_limit_service.get_user_network_limit(db, "user-1", "admin")

        assert limit == network_limit_service.UNLIMITED_LIMIT
        assert db.add.called
        created = db.add.call_args.args[0]
        assert created.user_id == "user-1"
        assert created.network_limit == network_limit_service.UNLIMITED_LIMIT
        assert created.is_role_exempt is True
        db.commit.assert_awaited_once()

    async def test_returns_default_for_non_exempt_user_without_existing_limit(self):
        db = _mock_db_with_user_limit(None)

        with (
            patch.object(network_limit_service.settings, "network_limit_per_user", 3),
            patch.object(
                network_limit_service.settings, "network_limit_exempt_roles", "owner,admin"
            ),
        ):
            limit = await network_limit_service.get_user_network_limit(db, "user-2", "member")

        assert limit == 3
        db.add.assert_not_called()
        db.commit.assert_not_called()

    async def test_switches_existing_user_to_exempt_when_role_becomes_exempt(self):
        existing = SimpleNamespace(network_limit=1, is_role_exempt=False)
        db = _mock_db_with_user_limit(existing)

        with patch.object(
            network_limit_service.settings, "network_limit_exempt_roles", "owner,admin"
        ):
            limit = await network_limit_service.get_user_network_limit(db, "user-3", "owner")

        assert limit == network_limit_service.UNLIMITED_LIMIT
        assert existing.network_limit == network_limit_service.UNLIMITED_LIMIT
        assert existing.is_role_exempt is True
        db.commit.assert_awaited_once()

    async def test_switches_existing_user_off_exempt_when_role_loses_exemption(self):
        existing = SimpleNamespace(
            network_limit=network_limit_service.UNLIMITED_LIMIT, is_role_exempt=True
        )
        db = _mock_db_with_user_limit(existing)

        with (
            patch.object(network_limit_service.settings, "network_limit_per_user", 4),
            patch.object(
                network_limit_service.settings, "network_limit_exempt_roles", "owner,admin"
            ),
        ):
            limit = await network_limit_service.get_user_network_limit(db, "user-4", "member")

        assert limit == 4
        assert existing.network_limit is None
        assert existing.is_role_exempt is False
        db.commit.assert_awaited_once()

    async def test_prefers_custom_limit_when_present(self):
        existing = SimpleNamespace(network_limit=7, is_role_exempt=False)
        db = _mock_db_with_user_limit(existing)

        with (
            patch.object(network_limit_service.settings, "network_limit_per_user", 2),
            patch.object(
                network_limit_service.settings, "network_limit_exempt_roles", "owner,admin"
            ),
        ):
            limit = await network_limit_service.get_user_network_limit(db, "user-5", "member")

        assert limit == 7
        db.commit.assert_not_called()

    async def test_falls_back_to_default_when_custom_limit_is_none(self):
        existing = SimpleNamespace(network_limit=None, is_role_exempt=False)
        db = _mock_db_with_user_limit(existing)

        with (
            patch.object(network_limit_service.settings, "network_limit_per_user", 6),
            patch.object(
                network_limit_service.settings, "network_limit_exempt_roles", "owner,admin"
            ),
        ):
            limit = await network_limit_service.get_user_network_limit(db, "user-6", "member")

        assert limit == 6
        db.commit.assert_not_called()

    async def test_handles_integrity_error_when_exempt_record_created_concurrently(self):
        existing = SimpleNamespace(
            network_limit=network_limit_service.UNLIMITED_LIMIT, is_role_exempt=True
        )
        first_result = MagicMock()
        first_result.scalar_one_or_none.return_value = None
        second_result = MagicMock()
        second_result.scalar_one_or_none.return_value = existing

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[first_result, second_result])
        db.add = MagicMock()
        db.commit = AsyncMock(side_effect=[IntegrityError("insert", {}, Exception("duplicate"))])
        db.rollback = AsyncMock()

        with patch.object(
            network_limit_service.settings, "network_limit_exempt_roles", "owner,admin"
        ):
            limit = await network_limit_service.get_user_network_limit(db, "user-race", "admin")

        assert limit == network_limit_service.UNLIMITED_LIMIT
        db.rollback.assert_awaited_once()


class TestNetworkCountAndStatus:
    async def test_get_network_count_returns_zero_for_null_scalar(self):
        db = AsyncMock()
        result = MagicMock()
        result.scalar.return_value = None
        db.execute = AsyncMock(return_value=result)

        count = await network_limit_service.get_network_count(db, "user-1")

        assert count == 0

    async def test_get_network_limit_status_for_exempt_user(self):
        with (
            patch(
                "app.services.network_limit.get_user_network_limit",
                new=AsyncMock(return_value=network_limit_service.UNLIMITED_LIMIT),
            ),
            patch(
                "app.services.network_limit.get_network_count",
                new=AsyncMock(return_value=9),
            ),
        ):
            status = await network_limit_service.get_network_limit_status(
                AsyncMock(), "user-1", "admin"
            )

        assert status == {
            "used": 9,
            "limit": -1,
            "remaining": -1,
            "is_exempt": True,
            "message": None,
        }

    async def test_get_network_limit_status_sets_limit_reached_message(self):
        with (
            patch(
                "app.services.network_limit.get_user_network_limit", new=AsyncMock(return_value=2)
            ),
            patch("app.services.network_limit.get_network_count", new=AsyncMock(return_value=2)),
            patch.object(
                network_limit_service.settings,
                "network_limit_message",
                "You can only have {limit} networks.",
            ),
        ):
            status = await network_limit_service.get_network_limit_status(
                AsyncMock(), "user-2", "member"
            )

        assert status["used"] == 2
        assert status["limit"] == 2
        assert status["remaining"] == 0
        assert status["is_exempt"] is False
        assert status["message"] == "You can only have 2 networks."


class TestCheckNetworkLimit:
    async def test_check_network_limit_allows_unlimited_user(self):
        with (
            patch(
                "app.services.network_limit.get_user_network_limit",
                new=AsyncMock(return_value=network_limit_service.UNLIMITED_LIMIT),
            ),
            patch("app.services.network_limit.get_network_count", new=AsyncMock()) as mock_count,
        ):
            await network_limit_service.check_network_limit(AsyncMock(), "user-1", "admin")

        mock_count.assert_not_called()

    async def test_check_network_limit_raises_when_limit_reached(self):
        with (
            patch(
                "app.services.network_limit.get_user_network_limit", new=AsyncMock(return_value=2)
            ),
            patch("app.services.network_limit.get_network_count", new=AsyncMock(return_value=2)),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await network_limit_service.check_network_limit(AsyncMock(), "user-2", "member")

        assert exc_info.value.status_code == 403
        assert "maximum of 2" in exc_info.value.detail

    async def test_check_network_limit_allows_when_under_limit(self):
        with (
            patch(
                "app.services.network_limit.get_user_network_limit", new=AsyncMock(return_value=3)
            ),
            patch("app.services.network_limit.get_network_count", new=AsyncMock(return_value=2)),
        ):
            await network_limit_service.check_network_limit(AsyncMock(), "user-3", "member")


class TestSetUserNetworkLimit:
    async def test_set_user_network_limit_creates_record_for_new_user(self):
        db = _mock_db_with_user_limit(None)

        response = await network_limit_service.set_user_network_limit(db, "user-1", 5)

        assert db.add.called
        created = db.add.call_args.args[0]
        assert created.user_id == "user-1"
        assert created.network_limit == 5
        assert created.is_role_exempt is False
        db.commit.assert_awaited_once()
        assert response == {"user_id": "user-1", "network_limit": 5, "is_role_exempt": False}

    async def test_set_user_network_limit_updates_existing_user_and_clears_role_exempt(self):
        existing = SimpleNamespace(
            network_limit=network_limit_service.UNLIMITED_LIMIT, is_role_exempt=True
        )
        db = _mock_db_with_user_limit(existing)

        response = await network_limit_service.set_user_network_limit(db, "user-2", None)

        assert existing.network_limit is None
        assert existing.is_role_exempt is False
        db.add.assert_not_called()
        db.commit.assert_awaited_once()
        assert response == {"user_id": "user-2", "network_limit": None, "is_role_exempt": False}

    async def test_set_user_network_limit_handles_concurrent_create(self):
        existing = SimpleNamespace(network_limit=1, is_role_exempt=True)
        first_result = MagicMock()
        first_result.scalar_one_or_none.return_value = None
        second_result = MagicMock()
        second_result.scalar_one_or_none.return_value = existing

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[first_result, second_result])
        db.add = MagicMock()
        db.commit = AsyncMock(
            side_effect=[IntegrityError("insert", {}, Exception("duplicate")), None]
        )
        db.rollback = AsyncMock()

        response = await network_limit_service.set_user_network_limit(db, "user-race", 5)

        assert existing.network_limit == 5
        assert existing.is_role_exempt is False
        db.rollback.assert_awaited_once()
        assert db.commit.await_count == 2
        assert response == {"user_id": "user-race", "network_limit": 5, "is_role_exempt": False}
