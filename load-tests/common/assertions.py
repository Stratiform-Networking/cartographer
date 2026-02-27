"""Assertion helpers for Locust responses."""

from __future__ import annotations

from typing import Iterable


def expect_status(response, allowed_codes: Iterable[int], context: str) -> bool:
    """
    Mark a Locust catch_response block as success/failure based on status code.

    Returns True when the response status is expected, else False.
    """
    allowed = set(allowed_codes)
    if response.status_code in allowed:
        response.success()
        return True

    body = ""
    try:
        body = (response.text or "")[:200]
    except Exception:
        body = "<unavailable>"

    response.failure(
        f"{context}: expected status in {sorted(allowed)} but got {response.status_code}. "
        f"body={body}"
    )
    return False

