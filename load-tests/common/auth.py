"""Authentication helpers for load tests."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from locust.exception import StopUser

from common.assertions import expect_status

DEFAULT_AUTH_HOST = "http://localhost:8002"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"


@dataclass(frozen=True)
class AuthResult:
    access_token: str
    user_id: Optional[str]
    username: Optional[str]


def get_auth_host() -> str:
    return os.getenv("LOADTEST_AUTH_HOST", DEFAULT_AUTH_HOST).rstrip("/")


def get_auth_username() -> str:
    return os.getenv("LOADTEST_USERNAME", DEFAULT_USERNAME)


def get_auth_password() -> str:
    return os.getenv("LOADTEST_PASSWORD", DEFAULT_PASSWORD)


def login_with_locust_client(
    client,
    username: str,
    password: str,
    *,
    auth_host: Optional[str] = None,
) -> AuthResult:
    """
    Authenticate against auth service and return an access token payload.

    Raises StopUser on any authentication failure.
    """
    base = (auth_host or get_auth_host()).rstrip("/")
    login_url = f"{base}/api/auth/login"

    with client.post(
        login_url,
        json={"username": username, "password": password},
        name="/api/auth/login",
        catch_response=True,
    ) as response:
        if not expect_status(response, [200], "Authentication failed"):
            raise StopUser("Authentication failed")

        try:
            payload = response.json()
        except Exception as exc:
            response.failure(f"Authentication response was not valid JSON: {exc}")
            raise StopUser("Authentication response was not valid JSON") from exc

        token = payload.get("access_token")
        if not token:
            response.failure("Authentication response did not contain access_token")
            raise StopUser("Missing access token in authentication response")

        user_data = payload.get("user", {}) if isinstance(payload, dict) else {}
        user_id = user_data.get("id") if isinstance(user_data, dict) else None
        resolved_username = (
            user_data.get("username") if isinstance(user_data, dict) else None
        )
        return AuthResult(
            access_token=token,
            user_id=user_id,
            username=resolved_username,
        )

