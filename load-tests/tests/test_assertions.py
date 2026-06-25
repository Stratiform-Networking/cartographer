from common.assertions import expect_status


class DummyResponse:
    def __init__(self, status_code=200, text="ok"):
        self.status_code = status_code
        self.text = text
        self.success_called = False
        self.failure_message = None

    def success(self):
        self.success_called = True

    def failure(self, message):
        self.failure_message = message


def test_expect_status_success():
    response = DummyResponse(status_code=200)
    assert expect_status(response, [200], "ctx") is True
    assert response.success_called is True
    assert response.failure_message is None


def test_expect_status_failure():
    response = DummyResponse(status_code=503, text="boom")
    assert expect_status(response, [200], "ctx") is False
    assert response.success_called is False
    assert "expected status in [200]" in response.failure_message
    assert "503" in response.failure_message

