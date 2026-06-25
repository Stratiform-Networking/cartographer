import pytest
from locust.exception import StopUser

from common.auth import login_with_locust_client


class DummyResponse:
    def __init__(self, status_code=200, payload=None, text="ok"):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text
        self.success_called = False
        self.failure_message = None

    def json(self):
        return self._payload

    def success(self):
        self.success_called = True

    def failure(self, message):
        self.failure_message = message


class DummyContextManager:
    def __init__(self, response):
        self.response = response

    def __enter__(self):
        return self.response

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, json, name, catch_response):
        self.calls.append({"url": url, "json": json, "name": name, "catch_response": catch_response})
        return DummyContextManager(self.response)


def test_login_with_locust_client_success():
    response = DummyResponse(
        status_code=200,
        payload={"access_token": "token-123", "user": {"id": "u1", "username": "alice"}},
    )
    client = DummyClient(response)

    result = login_with_locust_client(
        client,
        "alice",
        "secret",
        auth_host="http://localhost:8002",
    )

    assert result.access_token == "token-123"
    assert result.user_id == "u1"
    assert result.username == "alice"
    assert response.success_called is True
    assert client.calls[0]["url"] == "http://localhost:8002/api/auth/login"
    assert client.calls[0]["name"] == "/api/auth/login"


def test_login_with_locust_client_raises_stop_user_on_401():
    response = DummyResponse(status_code=401, payload={"detail": "invalid credentials"})
    client = DummyClient(response)

    with pytest.raises(StopUser):
        login_with_locust_client(client, "alice", "wrong", auth_host="http://localhost:8002")

    assert response.failure_message is not None


def test_login_with_locust_client_raises_stop_user_when_token_missing():
    response = DummyResponse(status_code=200, payload={"user": {"id": "u1"}})
    client = DummyClient(response)

    with pytest.raises(StopUser):
        login_with_locust_client(client, "alice", "secret", auth_host="http://localhost:8002")

    assert response.failure_message is not None
    assert "access_token" in response.failure_message

