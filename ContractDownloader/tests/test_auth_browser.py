import json
import plistlib
from types import SimpleNamespace

from src.auth.browser import (
    BrowserCatalog,
    BrowserInstallation,
    BrowserKind,
    BrowserLogin,
    BrowserProfileManager,
    build_browser_options,
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
