import asyncio

import httpx

from src.auth.models import AuthState
from src.auth.session_validator import SessionValidator


class FakeResponse:
    def __init__(self, status_code, url):
        self.status_code = status_code
        self.url = url


class FakeClient:
    response = None
    error = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.cookies = kwargs.get("cookies") or httpx.Cookies()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url):
        if self.error:
            raise self.error
        return self.response


def test_validator_rejects_missing_session_without_http(monkeypatch):
    called = False

    def unexpected_client(**kwargs):
        nonlocal called
        called = True
        return FakeClient(**kwargs)

    monkeypatch.setattr("src.auth.session_validator.httpx.AsyncClient", unexpected_client)
    result = asyncio.run(SessionValidator().validate({"other": "value"}))

    assert result.state is AuthState.MISSING
    assert called is False


def test_validator_distinguishes_expired_redirect(monkeypatch):
    FakeClient.response = FakeResponse(200, "https://unilever.coupahost.com/login")
    FakeClient.error = None
    monkeypatch.setattr("src.auth.session_validator.httpx.AsyncClient", FakeClient)

    result = asyncio.run(SessionValidator().validate({"_coupa_session": "session"}))

    assert result.state is AuthState.EXPIRED


def test_validator_preserves_cache_when_network_is_unavailable(monkeypatch):
    FakeClient.error = httpx.NetworkError("offline")
    monkeypatch.setattr("src.auth.session_validator.httpx.AsyncClient", FakeClient)

    result = asyncio.run(SessionValidator().validate({"_coupa_session": "session"}))

    assert result.state is AuthState.UNAVAILABLE
    assert result.has_cached_session


def test_validator_retries_transient_network_failure(monkeypatch):
    class RetryingClient(FakeClient):
        calls = 0

        async def get(self, url):
            type(self).calls += 1
            if self.calls == 1:
                raise httpx.NetworkError("temporary offline")
            return FakeResponse(200, "https://unilever.coupahost.com/order_headers")

    monkeypatch.setattr("src.auth.session_validator.httpx.AsyncClient", RetryingClient)

    result = asyncio.run(SessionValidator(attempts=2).validate({"_coupa_session": "session"}))

    assert result.state is AuthState.VALID
    assert RetryingClient.calls == 2


def test_validator_returns_cookie_refreshed_by_coupa(monkeypatch):
    class RefreshingClient(FakeClient):
        instance = None

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            type(self).instance = self

        async def get(self, url):
            current = next(iter(self.cookies.jar))
            self.cookies.set("_coupa_session", "refreshed", domain=current.domain, path="/")
            return FakeResponse(200, "https://unilever.coupahost.com/order_headers")

    monkeypatch.setattr("src.auth.session_validator.httpx.AsyncClient", RefreshingClient)

    result = asyncio.run(SessionValidator().validate({"_coupa_session": "cached"}))

    assert result.state is AuthState.VALID
    assert result.cookies["_coupa_session"] == "refreshed"
    assert [cookie.value for cookie in RefreshingClient.instance.cookies.jar] == ["refreshed"]
