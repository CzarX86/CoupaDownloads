import json
import plistlib
import signal
from types import SimpleNamespace

import pytest

from src.auth.browser import (
    BrowserCatalog,
    BrowserInstallation,
    BrowserKind,
    BrowserLogin,
    BrowserProfileManager,
    build_browser_options,
    open_browser_profile_setup,
)


def test_browser_catalog_uses_os_default_in_auto_mode(monkeypatch):
    available = [
        BrowserInstallation(BrowserKind.CHROME, "Google Chrome", "/chrome"),
        BrowserInstallation(BrowserKind.EDGE, "Microsoft Edge", "/edge"),
    ]
    monkeypatch.setattr(BrowserCatalog, "detect", classmethod(lambda cls: available))
    monkeypatch.setattr(
        BrowserCatalog,
        "system_default_kind",
        classmethod(lambda cls: BrowserKind.CHROME),
    )

    assert BrowserCatalog.select("auto").kind is BrowserKind.CHROME
    assert BrowserCatalog.select("chrome").kind is BrowserKind.CHROME


def test_browser_catalog_falls_back_to_edge_when_os_default_is_unsupported(monkeypatch):
    available = [
        BrowserInstallation(BrowserKind.CHROME, "Google Chrome", "/chrome"),
        BrowserInstallation(BrowserKind.EDGE, "Microsoft Edge", "/edge"),
    ]
    monkeypatch.setattr(BrowserCatalog, "detect", classmethod(lambda cls: available))
    monkeypatch.setattr(BrowserCatalog, "system_default_kind", classmethod(lambda cls: None))

    assert BrowserCatalog.select("auto").kind is BrowserKind.EDGE


def test_macos_default_browser_parser_maps_chrome(monkeypatch):
    payload = plistlib.dumps({
        "LSHandlers": [{
            "LSHandlerURLScheme": "http",
            "LSHandlerRoleAll": "com.google.Chrome",
        }],
    })
    monkeypatch.setattr("src.auth.browser.sys.platform", "darwin")
    monkeypatch.setattr(
        "src.auth.browser.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=payload),
    )

    assert BrowserCatalog.system_default_kind() is BrowserKind.CHROME


def test_browser_catalog_rejects_unavailable_explicit_browser(monkeypatch):
    monkeypatch.setattr(
        BrowserCatalog,
        "detect",
        classmethod(lambda cls: [BrowserInstallation(BrowserKind.EDGE, "Microsoft Edge", "/edge")]),
    )

    try:
        BrowserCatalog.select("chrome")
    except RuntimeError as exc:
        assert "Google Chrome" in str(exc)
    else:
        raise AssertionError("Expected an unavailable-browser error")


def test_browser_profile_manager_removes_stale_chromium_locks(tmp_path):
    profile = tmp_path / "edge"
    profile.mkdir()
    (profile / "SingletonLock").symlink_to("Dead-Machine-999999")
    (profile / "SingletonCookie").symlink_to("dead-cookie")
    manager = BrowserProfileManager(tmp_path / "browser_profiles")
    manager.root.mkdir(parents=True, exist_ok=True)
    manager.path_for = lambda kind: profile
    assert manager.ensure(BrowserKind.EDGE) == profile
    assert not (profile / "SingletonLock").exists()


def test_browser_profile_manager_recovers_orphaned_webdriver_on_macos(monkeypatch, tmp_path):
    manager = BrowserProfileManager(tmp_path / "browser_profiles")
    profile = manager.path_for(BrowserKind.EDGE)
    profile.mkdir(parents=True)
    (profile / "SingletonLock").symlink_to("Test-Mac-4242")
    process_info = {
        4242: (5000, f"/Applications/Microsoft Edge --test-type=webdriver --user-data-dir={profile}"),
        5000: (1, "/cache/selenium/msedgedriver --port=12345"),
    }
    terminated = set()

    def fake_kill(pid, sig):
        if sig == 0:
            if pid in terminated:
                raise ProcessLookupError
            return
        assert sig == signal.SIGTERM
        terminated.add(pid)

    monkeypatch.setattr("src.auth.browser.sys.platform", "darwin")
    monkeypatch.setattr(BrowserProfileManager, "_process_info", staticmethod(process_info.get))
    monkeypatch.setattr("src.auth.browser.os.kill", fake_kill)

    assert manager.ensure(BrowserKind.EDGE) == profile
    assert terminated == {4242, 5000}
    assert not (profile / "SingletonLock").exists()


def test_browser_profile_manager_registers_dedicated_profile(tmp_path):
    manager = BrowserProfileManager(tmp_path / "browser_profiles")
    path = manager.ensure(BrowserKind.CHROME)

    manifest = json.loads((tmp_path / "browser_profiles.json").read_text(encoding="utf-8"))
    assert manifest["profiles"]["chrome"]["path"] == str(path)
    assert manager.info(BrowserKind.CHROME)["registered"] is True
    assert manager.info(BrowserKind.CHROME)["exists"] is True

    removed = manager.clear(BrowserKind.CHROME)
    assert removed == [path.name]
    assert not path.exists()
    assert not (tmp_path / "browser_profiles.json").exists()


def test_browser_login_detects_authenticated_second_window(tmp_path):
    class SwitchTo:
        def __init__(self, driver):
            self.driver = driver

        def window(self, handle):
            self.driver.active = handle

    class MultiWindowDriver:
        def __init__(self):
            self.active = "main"
            self.windows = {
                "main": {"url": "edge://newtab", "cookies": {}},
                "coupa": {
                    "url": "https://unilever.coupahost.com/order_headers",
                    "cookies": {"_coupa_session": "session-from-second-window"},
                },
            }
            self.switch_to = SwitchTo(self)

        @property
        def window_handles(self):
            return list(self.windows)

        @property
        def current_url(self):
            return self.windows[self.active]["url"]

        def get(self, url):
            self.windows[self.active]["url"] = url

        def get_cookie(self, name):
            value = self.windows[self.active]["cookies"].get(name)
            return {"name": name, "value": value} if value else None

        def get_cookies(self):
            return [
                {"name": name, "value": value}
                for name, value in self.windows[self.active]["cookies"].items()
            ]

        def quit(self):
            return None

    driver = MultiWindowDriver()

    class Launcher:
        def launch(self, *args, **kwargs):
            return driver

    login = BrowserLogin(Launcher(), poll_interval=0.001, wait_timeout=0.2, final_navigation_timeout=0.2)
    login._profile_has_browser_account = lambda profile_dir: True
    installation = BrowserInstallation(BrowserKind.EDGE, "Microsoft Edge", "/edge")
    statuses = []

    cookies = login.capture(installation, tmp_path / "profile", status_callback=lambda state, message: statuses.append((state, message)))

    assert cookies["_coupa_session"] == "session-from-second-window"
    assert any("Multiple browser windows" in message for _, message in statuses)


def test_browser_options_use_an_app_owned_profile(tmp_path):
    installation = BrowserInstallation(BrowserKind.CHROME, "Google Chrome", "/chrome")
    options = build_browser_options(installation, tmp_path / "profile")

    arguments = set(options.arguments)
    assert f"--user-data-dir={tmp_path / 'profile'}" in arguments
    assert "--no-first-run" in arguments
    assert options.binary_location == "/chrome"


@pytest.mark.parametrize(
    "kind",
    [
        BrowserKind.EDGE,
        BrowserKind.CHROME,
    ],
)
def test_profile_setup_opens_natively_outside_webdriver(monkeypatch, tmp_path, kind):
    captured = {}
    process = SimpleNamespace()

    def fake_popen(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return process

    monkeypatch.setattr("src.auth.browser.subprocess.Popen", fake_popen)
    monkeypatch.setattr("src.auth.browser.sys.platform", "darwin")
    app_name = "Microsoft Edge" if kind is BrowserKind.EDGE else "Google Chrome"
    executable = tmp_path / f"{app_name}.app" / "Contents" / "MacOS" / app_name

    result = open_browser_profile_setup(
        BrowserInstallation(kind, kind.value, str(executable)),
        tmp_path / "profile",
    )

    assert result is process
    assert captured["command"][:4] == ["open", "-n", "-a", str(executable.parents[2])]
    assert f"--user-data-dir={tmp_path / 'profile'}" in captured["command"]
    assert not any("coupahost.com" in argument for argument in captured["command"])


class ProfileOnboardingDriver:
    def __init__(self, *, auth_after_cookie_checks=None):
        self.current_url = ""
        self.visited = []
        self.cookie_checks = 0
        self.auth_after_cookie_checks = auth_after_cookie_checks
        self.switch_to = SimpleNamespace(window=lambda handle: None)

    @property
    def window_handles(self):
        return ["main"]

    def get(self, url):
        self.current_url = url
        self.visited.append(url)

    def get_cookie(self, name):
        self.cookie_checks += 1
        sso_ready = (
            self.cookie_checks >= self.auth_after_cookie_checks
            if self.auth_after_cookie_checks
            else bool(self.visited)
        )
        if sso_ready and name == "_coupa_session":
            return {"name": name, "value": "session"}
        return None

    def get_cookies(self):
        return [{"name": "_coupa_session", "value": "session"}]

    def quit(self):
        return None


class ProfileSetupProcess:
    def __init__(self):
        self.terminated = False

    def poll(self):
        return 0 if self.terminated else None

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        return 0

    def kill(self):
        self.terminated = True


def browser_login(driver, *, wait_timeout, setup_calls=None, events=None):
    flow = events if events is not None else []

    def launch_driver(*args, **kwargs):
        flow.append("webdriver")
        return driver

    launcher = SimpleNamespace(launch=launch_driver)
    calls = setup_calls if setup_calls is not None else []

    def open_setup(installation, profile_dir):
        flow.append("profile_setup")
        calls.append((installation.kind, profile_dir))
        return ProfileSetupProcess()

    return BrowserLogin(
        launcher,
        poll_interval=0.001,
        wait_timeout=wait_timeout,
        profile_setup_launcher=open_setup,
    )


@pytest.mark.parametrize(
    ("kind", "name"),
    [
        (BrowserKind.EDGE, "Microsoft Edge"),
        (BrowserKind.CHROME, "Google Chrome"),
    ],
)
def test_browser_login_onboards_work_account_then_opens_coupa(tmp_path, kind, name):
    driver = ProfileOnboardingDriver()
    setup_calls = []
    events = []
    login = browser_login(driver, wait_timeout=0.2, setup_calls=setup_calls, events=events)
    account_checks = iter([False, True, True])
    login._profile_has_browser_account = lambda profile_dir: next(account_checks)
    statuses = []

    login.capture(
        BrowserInstallation(kind, name, f"/{kind.value}"),
        tmp_path / "profile",
        status_callback=lambda state, message: statuses.append((state, message)),
    )

    assert driver.visited[:2] == [
        "https://unilever.coupahost.com/order_headers",
        "https://unilever.coupahost.com/order_headers",
    ]
    assert setup_calls == [(kind, tmp_path / "profile")]
    assert events[:2] == ["profile_setup", "webdriver"]
    assert any(f"dedicated {name} profile" in message for _, message in statuses)
    assert any("opening Coupa with SSO" in message for _, message in statuses)


def test_chrome_account_onboarding_falls_back_to_coupa_login(tmp_path):
    driver = ProfileOnboardingDriver()
    login = browser_login(driver, wait_timeout=0)
    login._profile_has_browser_account = lambda profile_dir: False
    statuses = []

    cookies = login.capture(
        BrowserInstallation(BrowserKind.CHROME, "Google Chrome", "/chrome"),
        tmp_path / "profile",
        status_callback=lambda state, message: statuses.append((state, message)),
    )

    assert cookies["_coupa_session"] == "session"
    assert any("profile setup was not completed" in message for _, message in statuses)


def test_edge_account_onboarding_never_falls_back_to_coupa_login(tmp_path):
    driver = ProfileOnboardingDriver()
    login = browser_login(driver, wait_timeout=0)
    login._profile_has_browser_account = lambda profile_dir: False

    with pytest.raises(TimeoutError, match="dedicated Edge profile"):
        login.capture(
            BrowserInstallation(BrowserKind.EDGE, "Microsoft Edge", "/edge"),
            tmp_path / "profile",
        )

    assert driver.visited == []


def test_existing_profile_sso_skips_profile_onboarding(tmp_path):
    driver = ProfileOnboardingDriver(auth_after_cookie_checks=2)
    setup_calls = []
    login = browser_login(driver, wait_timeout=0.1, setup_calls=setup_calls)
    login._profile_has_browser_account = lambda profile_dir: True

    login.capture(
        BrowserInstallation(BrowserKind.CHROME, "Google Chrome", "/chrome"),
        tmp_path / "profile",
    )

    assert driver.visited == ["https://unilever.coupahost.com/order_headers"] * 2
    assert setup_calls == []
