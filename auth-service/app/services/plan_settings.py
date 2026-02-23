"""Centralized per-user plan settings sourced from subscription tier configs."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db_models import UserPlanSettings

logger = logging.getLogger(__name__)

DEFAULT_PLAN_ID = "free"

_FALLBACK_PLAN_LIMITS: dict[str, dict[str, int]] = {
    "free": {
        "owned_networks_limit": 1,
        "assistant_daily_chat_messages_limit": 5,
        "automatic_full_scan_min_interval_seconds": 7200,
    },
    "pro": {
        "owned_networks_limit": 3,
        "assistant_daily_chat_messages_limit": 50,
        "automatic_full_scan_min_interval_seconds": 60,
    },
    "proplus": {
        "owned_networks_limit": 20,
        "assistant_daily_chat_messages_limit": -1,
        "automatic_full_scan_min_interval_seconds": 30,
    },
    "enterprise": {
        "owned_networks_limit": -1,
        "assistant_daily_chat_messages_limit": -1,
        "automatic_full_scan_min_interval_seconds": 30,
    },
}


def _normalize_plan_id(plan_id: str | None) -> str:
    normalized = (plan_id or DEFAULT_PLAN_ID).strip().lower()
    return normalized or DEFAULT_PLAN_ID


def _tier_config_dir() -> Path:
    repo_root = Path(__file__).resolve().parents[4]
    return repo_root / "cartographer-cloud" / "backend" / "config" / "subscription_tiers"


@lru_cache(maxsize=1)
def _load_all_plan_limits() -> dict[str, dict[str, int]]:
    limits_by_plan = dict(_FALLBACK_PLAN_LIMITS)
    config_dir = _tier_config_dir()

    if not config_dir.exists():
        logger.warning(
            "Subscription tier config directory not found at %s; using fallback plan limits",
            config_dir,
        )
        return limits_by_plan

    try:
        import yaml
    except Exception as exc:  # pragma: no cover - fallback path
        logger.warning("PyYAML unavailable (%s); using fallback plan limits", exc)
        return limits_by_plan

    for path in sorted(config_dir.glob("*.yaml")):
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
        except Exception as exc:
            logger.warning("Failed to load subscription tier config %s: %s", path, exc)
            continue

        tier_id = _normalize_plan_id(data.get("tier_id"))
        tier_limits = (data.get("limits") or {}) if isinstance(data, dict) else {}

        try:
            limits_by_plan[tier_id] = {
                "owned_networks_limit": int(tier_limits["owned_networks_limit"]),
                "assistant_daily_chat_messages_limit": int(
                    tier_limits["assistant_daily_chat_messages_limit"]
                ),
                "automatic_full_scan_min_interval_seconds": int(
                    tier_limits["automatic_full_scan_min_interval_seconds"]
                ),
            }
        except Exception as exc:
            logger.warning(
                "Tier config %s missing supported limits; keeping fallback/defaults for %s (%s)",
                path,
                tier_id,
                exc,
            )

    return limits_by_plan


def resolve_plan_limits(plan_id: str | None) -> tuple[str, dict[str, int]]:
    """Resolve supported plan values for a tier ID, defaulting to free."""
    normalized_plan_id = _normalize_plan_id(plan_id)
    all_limits = _load_all_plan_limits()
    if normalized_plan_id not in all_limits:
        logger.warning("Unknown plan_id=%s, defaulting to %s", normalized_plan_id, DEFAULT_PLAN_ID)
        normalized_plan_id = DEFAULT_PLAN_ID
    return normalized_plan_id, all_limits[normalized_plan_id]


async def get_user_plan_settings(
    db: AsyncSession, user_id: str, create_if_missing: bool = True
) -> UserPlanSettings | None:
    """Get a user's plan settings, optionally creating a default free-tier row."""
    result = await db.execute(select(UserPlanSettings).where(UserPlanSettings.user_id == user_id))
    row = result.scalar_one_or_none()
    if row is not None or not create_if_missing:
        return row

    return await apply_plan_to_user(db, user_id=user_id, plan_id=DEFAULT_PLAN_ID, commit=True)


async def apply_plan_to_user(
    db: AsyncSession,
    user_id: str,
    plan_id: str | None,
    *,
    commit: bool = True,
) -> UserPlanSettings:
    """
    Upsert a user's plan-derived settings from the subscription tier configs.

    Args:
        db: Async session
        user_id: Local auth-service user ID
        plan_id: Requested plan ID (defaults to free)
        commit: Commit changes immediately (set False when composing in a larger tx)
    """
    normalized_plan_id, limits = resolve_plan_limits(plan_id)

    result = await db.execute(select(UserPlanSettings).where(UserPlanSettings.user_id == user_id))
    row = result.scalar_one_or_none()

    if row is None:
        row = UserPlanSettings(user_id=user_id)
        db.add(row)

    row.plan_id = normalized_plan_id
    row.owned_networks_limit = limits["owned_networks_limit"]
    row.assistant_daily_chat_messages_limit = limits["assistant_daily_chat_messages_limit"]
    row.automatic_full_scan_min_interval_seconds = limits[
        "automatic_full_scan_min_interval_seconds"
    ]

    if commit:
        await db.commit()
        await db.refresh(row)
    else:
        await db.flush()

    return row
