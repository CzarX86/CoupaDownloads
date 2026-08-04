import asyncio

from src.auth.browser import BrowserInstallation, BrowserKind
from src.auth.models import AuthState, SessionCheck
from src.auth.service import AuthService


class FakeStore:
    def __init__(self, cookies=None):
        self.cookies = cookies
        self.saved = None
        self.cleared = False

    def load(self):
        return self.cookies

    def save(self, cookies):
        self.saved = dict(cookies)
        self.cookies = dict(cookies)

    def clear(self):
        self.cleared = True
        self.cookies = None
        return {"success": True, "removed": ["cookies"]}


class FakeValidator:
    def __init__(self, states):
        self.states = iter(states)

    async def validate(self, cookies):
        state = next(self.states)
        return SessionCheck(state, state.value, cookies or {}, "cache")


class FakeCatalog:
    installation = BrowserInstallation(BrowserKind.EDGE, "Microsoft Edge", "/edge")

    @classmethod
    def select(cls, preference=None):
        return cls.installation

    @classmethod
    def as_settings(cls, preference=None):
        return {"available": [{"id": "edge", "name": "Microsoft Edge", "path": "/edge"}], "selected": "edge"}


class FakeProfiles:
    def __init__(self, tmp_path):
        self.path = tmp_path / "edge-profile"
        self.cleared = []

    def ensure(self, kind):
        self.path.mkdir()
        return self.path

    def clear(self, kind=None):
        self.cleared.append(kind)
        return ["edge-profile"]

    def path_for(self, kind):
        return self.path


class FakeLogin:
    def __init__(self):
        self.calls = 0

    def capture(self, installation, profile_dir, **kwargs):
        self.calls += 1
        return {"_coupa_session": "new-session"}


def test_worker_mode_keeps_cached_session_when_validation_is_unavailable(tmp_path):
    store = FakeStore({"_coupa_session": "cached"})
    login = FakeLogin()
    service = AuthService(
        store=store,
        validator=FakeValidator([AuthState.UNAVAILABLE]),
        catalog=FakeCatalog,
        profiles=FakeProfiles(tmp_path),
        browser_login=login,
    )

    result = asyncio.run(service.ensure_session(interactive=False))

    assert result.state is AuthState.UNAVAILABLE
    assert result.has_cached_session
    assert result.cookies["_coupa_session"] == "cached"
    assert login.calls == 0


def test_validated_session_refresh_is_persisted(tmp_path):
    class RefreshingValidator:
        async def validate(self, cookies):
            return SessionCheck(
                AuthState.VALID,
                "valid",
                {"_coupa_session": "refreshed"},
                "cache",
            )

    store = FakeStore({"_coupa_session": "cached"})
    service = AuthService(
        store=store,
        validator=RefreshingValidator(),
        catalog=FakeCatalog,
        profiles=FakeProfiles(tmp_path),
        browser_login=FakeLogin(),
    )

    result = asyncio.run(service.check())

    assert result.state is AuthState.VALID
    assert store.saved == {"_coupa_session": "refreshed"}


def test_interactive_mode_reauthenticates_after_expiry(tmp_path):
    store = FakeStore({"_coupa_session": "expired"})
    login = FakeLogin()
    service = AuthService(
        store=store,
        validator=FakeValidator([AuthState.EXPIRED, AuthState.VALID]),
        catalog=FakeCatalog,
        profiles=FakeProfiles(tmp_path),
        browser_login=login,
    )

    result = asyncio.run(service.ensure_session(interactive=True))

    assert result.state is AuthState.VALID
    assert result.cookies["_coupa_session"] == "new-session"
    assert login.calls == 1
    assert store.saved == {"_coupa_session": "new-session"}


def test_reset_only_delegates_to_cache_and_app_profiles(tmp_path):
    store = FakeStore({"_coupa_session": "cached"})
    profiles = FakeProfiles(tmp_path)
    service = AuthService(
        store=store,
        validator=FakeValidator([]),
        catalog=FakeCatalog,
        profiles=profiles,
        browser_login=FakeLogin(),
    )

    result = service.reset()

    assert result["success"] is True
    assert store.cleared is True
    assert profiles.cleared == [None]
    assert service.cookies is None
