from types import SimpleNamespace

from src.workers.verifiers.auth_verifier import AuthVerifier


class _Response:
    def __init__(self, url: str, status_code: int = 200):
        self.url = url
        self.status_code = status_code


def _config() -> SimpleNamespace:
    return SimpleNamespace(auth_check_url="https://example.test/check", auth_check_timeout=1.0)


def _profile(tmp_path):
    return SimpleNamespace(profile_path=tmp_path / "profile")


def test_auth_verifier_soft_mode_treats_redirect_as_warning(monkeypatch, tmp_path):
    monkeypatch.delenv("COUPA_AUTH_CHECK_STRICT", raising=False)
    monkeypatch.setattr(
        "src.workers.verifiers.auth_verifier.requests.get",
        lambda *_args, **_kwargs: _Response("https://tenant.example/sessions/new", 200),
    )

    verifier = AuthVerifier(_config())
    result = verifier.verify(_profile(tmp_path))

    assert result.success is True
    assert result.details.get("warning") == "session_redirect_detected_without_browser_context"


def test_auth_verifier_strict_mode_fails_on_redirect(monkeypatch, tmp_path):
    monkeypatch.setenv("COUPA_AUTH_CHECK_STRICT", "1")
    monkeypatch.setattr(
        "src.workers.verifiers.auth_verifier.requests.get",
        lambda *_args, **_kwargs: _Response("https://tenant.example/sessions/new", 200),
    )

    verifier = AuthVerifier(_config())
    result = verifier.verify(_profile(tmp_path))

    assert result.success is False
    assert "session redirect detected" in (result.error_message or "")
