from __future__ import annotations

import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Iterable

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions

from src.auth.session_validator import AUTH_REDIRECT_MARKERS, COUPA_URL


class BrowserKind(StrEnum):
    EDGE = "edge"
    CHROME = "chrome"


@dataclass(frozen=True, slots=True)
class BrowserInstallation:
    kind: BrowserKind
    name: str
    executable: str


class BrowserCatalog:
    """Detect supported browsers and the OS default without reading profiles."""

    _DISPLAY_NAMES = {
        BrowserKind.EDGE: "Microsoft Edge",
        BrowserKind.CHROME: "Google Chrome",
    }

    @classmethod
    def _candidates(cls) -> dict[BrowserKind, list[str]]:
        if os.name == "nt":
            local = os.environ.get("LOCALAPPDATA", "")
            program_files = os.environ.get("PROGRAMFILES", r"C:\\Program Files")
            program_files_x86 = os.environ.get("PROGRAMFILES(X86)", r"C:\\Program Files (x86)")
            return {
                BrowserKind.EDGE: [
                    os.path.join(local, "Microsoft", "Edge", "Application", "msedge.exe"),
                    os.path.join(program_files_x86, "Microsoft", "Edge", "Application", "msedge.exe"),
                    os.path.join(program_files, "Microsoft", "Edge", "Application", "msedge.exe"),
                ],
                BrowserKind.CHROME: [
                    os.path.join(local, "Google", "Chrome", "Application", "chrome.exe"),
                    os.path.join(program_files_x86, "Google", "Chrome", "Application", "chrome.exe"),
                    os.path.join(program_files, "Google", "Chrome", "Application", "chrome.exe"),
                ],
            }
        if sys.platform == "darwin":
            return {
                BrowserKind.EDGE: [
                    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                    str(Path.home() / "Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
                ],
                BrowserKind.CHROME: [
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    str(Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                ],
            }
        return {
            BrowserKind.EDGE: ["/usr/bin/microsoft-edge", "/usr/bin/microsoft-edge-stable"],
            BrowserKind.CHROME: ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium"],
        }

    @classmethod
    def detect(cls) -> list[BrowserInstallation]:
        detected: list[BrowserInstallation] = []
        for kind, candidates in cls._candidates().items():
            paths: Iterable[str | None] = [
                shutil.which("msedge") if kind is BrowserKind.EDGE else shutil.which("google-chrome"),
                shutil.which("microsoft-edge") if kind is BrowserKind.EDGE else shutil.which("chrome"),
                *candidates,
            ]
            selected = next(
                (
                    str(Path(path).expanduser())
                    for path in paths
                    if path and Path(path).expanduser().is_file()
                ),
                None,
            )
            if selected:
                detected.append(BrowserInstallation(kind, cls._DISPLAY_NAMES[kind], selected))
        return detected

    @staticmethod
    def _kind_from_identifier(identifier: object) -> BrowserKind | None:
        value = str(identifier or "").lower()
        if "edge" in value or "microsoft.edgemac" in value:
            return BrowserKind.EDGE
        if "chrome" in value or "googlechromes" in value or "chromium" in value:
            return BrowserKind.CHROME
        return None

    @classmethod
    def _macos_default_kind(cls) -> BrowserKind | None:
        try:
            result = subprocess.run(
                [
                    "defaults",
                    "export",
                    "com.apple.LaunchServices/com.apple.launchservices.secure",
                    "-",
                ],
                capture_output=True,
                check=False,
                timeout=4,
            )
            if result.returncode != 0 or not result.stdout:
                return None
            payload = plistlib.loads(result.stdout)
            handlers = payload.get("LSHandlers", []) if isinstance(payload, dict) else []
            if not isinstance(handlers, list):
                return None
            for scheme in ("http", "https"):
                for handler in handlers:
                    if not isinstance(handler, dict):
                        continue
                    if str(handler.get("LSHandlerURLScheme", "")).lower() != scheme:
                        continue
                    for key in ("LSHandlerRoleAll", "LSHandlerRoleViewer", "LSHandlerRoleEditor"):
                        kind = cls._kind_from_identifier(handler.get(key))
                        if kind:
                            return kind
            for handler in handlers:
                if not isinstance(handler, dict):
                    continue
                if handler.get("LSHandlerContentType") != "com.apple.default-app.web-browser":
                    continue
                for key in ("LSHandlerRoleAll", "LSHandlerRoleViewer", "LSHandlerRoleEditor"):
                    kind = cls._kind_from_identifier(handler.get(key))
                    if kind:
                        return kind
        except (OSError, subprocess.SubprocessError, plistlib.InvalidFileException, TypeError, ValueError):
            return None
        return None

    @classmethod
    def _windows_default_kind(cls) -> BrowserKind | None:
        try:
            import winreg

            for scheme in ("http", "https"):
                key_path = (
                    "Software\\Microsoft\\Windows\\Shell\\Associations\\UrlAssociations\\"
                    f"{scheme}\\UserChoice"
                )
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                    prog_id, _ = winreg.QueryValueEx(key, "ProgId")
                kind = cls._kind_from_identifier(prog_id)
                if kind:
                    return kind
        except (ImportError, OSError):
            return None
        return None

    @classmethod
    def _linux_default_kind(cls) -> BrowserKind | None:
        try:
            result = subprocess.run(
                ["xdg-settings", "get", "default-url-scheme-handler", "http"],
                capture_output=True,
                text=True,
                check=False,
                timeout=4,
            )
            if result.returncode == 0:
                return cls._kind_from_identifier(result.stdout.strip())
        except (OSError, subprocess.SubprocessError):
            pass
        return None

    @classmethod
    def system_default_kind(cls) -> BrowserKind | None:
        """Return the supported browser selected by the operating system."""
        if sys.platform == "darwin":
            return cls._macos_default_kind()
        if sys.platform.startswith("win"):
            return cls._windows_default_kind()
        if sys.platform.startswith("linux"):
            return cls._linux_default_kind()
        return None

    @classmethod
    def select(cls, preference: str | None = None) -> BrowserInstallation:
        available = cls.detect()
        if not available:
            raise RuntimeError("Microsoft Edge or Google Chrome is required for Coupa sign-in.")
        requested = str(preference or os.environ.get("COUPA_AUTH_BROWSER", "auto")).strip().lower()
        if requested in {"edge", "msedge", "microsoft-edge"}:
            selected = next((item for item in available if item.kind is BrowserKind.EDGE), None)
            if selected:
                return selected
            raise RuntimeError("Microsoft Edge was selected for Coupa sign-in but was not found.")
        if requested in {"chrome", "google-chrome"}:
            selected = next((item for item in available if item.kind is BrowserKind.CHROME), None)
            if selected:
                return selected
            raise RuntimeError("Google Chrome was selected for Coupa sign-in but was not found.")

        system_default = cls.system_default_kind()
        if system_default:
            selected = next((item for item in available if item.kind is system_default), None)
            if selected:
                return selected

        # If the OS default is unsupported (for example Safari), choose a
        # deterministic supported fallback without changing the OS setting.
        return next(
            (
                item
                for kind in (BrowserKind.EDGE, BrowserKind.CHROME)
                for item in available
                if item.kind is kind
            ),
            available[0],
        )

    @classmethod
    def as_settings(cls, preference: str | None = None) -> dict[str, Any]:
        available = cls.detect()
        system_default = cls.system_default_kind()
        selected = None
        try:
            selected = cls.select(preference).kind.value
        except RuntimeError:
            pass
        requested = str(preference or os.environ.get("COUPA_AUTH_BROWSER", "auto")).strip().lower()
        source = "settings" if requested not in {"", "auto"} else (
            "system_default" if system_default and any(item.kind is system_default for item in available) else "fallback"
        )
        return {
            "available": [
                {"id": item.kind.value, "name": item.name, "path": item.executable}
                for item in available
            ],
            "selected": selected,
            "system_default": system_default.value if system_default else None,
            "system_default_name": cls._DISPLAY_NAMES.get(system_default) if system_default else None,
            "selection_source": source,
        }


class BrowserProfileManager:
    """Own and register only profiles created for app authentication."""

    def __init__(self, root: str | os.PathLike[str] | None = None):
        self.root = Path(root).expanduser() if root else Path.home() / ".contract_downloader" / "browser_profiles"
        self.legacy_edge_profile = self.root.parent / "edge_auth_profile"
        self.manifest_path = self.root.parent / "browser_profiles.json"

    @staticmethod
    def _timestamp() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def _read_manifest(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            profiles = payload.get("profiles", {}) if isinstance(payload, dict) else {}
            return {"profiles": profiles} if isinstance(profiles, dict) else {"profiles": {}}
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return {"profiles": {}}

    def _write_manifest(self, payload: dict[str, Any]) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.manifest_path.with_name(f".{self.manifest_path.name}.tmp")
        try:
            temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.manifest_path)
            os.chmod(self.manifest_path, 0o600)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise RuntimeError(f"Could not register the app-owned browser profile: {exc}") from exc

    def path_for(self, kind: BrowserKind) -> Path:
        # New profiles live under browser_profiles/<browser>. Reuse the legacy
        # Edge location when it already exists so upgrades do not force a new
        # sign-in. Neither path is a user's normal browser profile.
        canonical = self.root / kind.value
        if kind is BrowserKind.EDGE and self.legacy_edge_profile.exists() and not canonical.exists():
            return self.legacy_edge_profile
        return canonical

    def ensure(self, kind: BrowserKind) -> Path:
        path = self.path_for(kind)
        path.mkdir(parents=True, exist_ok=True)
        if self.is_locked(path) and not self.clear_stale_lock(path):
            raise RuntimeError(f"Close the Contract Downloader sign-in browser before retrying {kind.value} sign-in.")
        try:
            os.chmod(self.root.parent, 0o700)
            os.chmod(self.root, 0o700)
            os.chmod(path, 0o700)
        except OSError:
            pass
        manifest = self._read_manifest()
        previous = manifest["profiles"].get(kind.value, {})
        manifest["profiles"][kind.value] = {
            "kind": kind.value,
            "path": str(path),
            "created_at": previous.get("created_at") or self._timestamp(),
            "last_used_at": self._timestamp(),
        }
        self._write_manifest(manifest)
        return path

    def info(self, kind: BrowserKind) -> dict[str, Any]:
        record = self._read_manifest()["profiles"].get(kind.value, {})
        path = self.path_for(kind)
        return {
            "id": kind.value,
            "path": str(path),
            "exists": path.exists(),
            "registered": bool(record),
            "created_at": record.get("created_at"),
            "last_used_at": record.get("last_used_at"),
        }

    @staticmethod
    def _lock_owner_alive(path: Path) -> bool:
        lock = path / "SingletonLock"
        if not lock.is_symlink():
            return False
        try:
            target = os.readlink(lock)
        except OSError:
            return False
        match = re.search(r"-(\d+)$", target)
        if not match:
            return False
        try:
            os.kill(int(match.group(1)), 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False
        return True

    @classmethod
    def clear_stale_lock(cls, path: Path) -> bool:
        """Remove orphaned Chromium lock markers from an app-owned profile."""
        if cls._lock_owner_alive(path):
            return False
        removed = False
        for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
            marker = path / name
            if marker.is_symlink() or marker.exists():
                try:
                    marker.unlink()
                    removed = True
                except OSError:
                    return False
        return removed

    @classmethod
    def is_locked(cls, path: Path) -> bool:
        # Chromium creates one of these markers for a live user-data root. We
        # inspect only the app-owned profile, never the user's personal profile.
        if cls._lock_owner_alive(path):
            return True
        return any((path / name).is_symlink() or (path / name).exists() for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"))

    def clear(self, kind: BrowserKind | None = None) -> list[str]:
        kinds = [kind] if kind else list(BrowserKind)
        manifest = self._read_manifest()
        targets: list[tuple[BrowserKind, Path]] = []
        for item in kinds:
            selected = self.path_for(item)
            targets.append((item, selected))
            if item is BrowserKind.EDGE and self.legacy_edge_profile != selected and self.legacy_edge_profile.exists():
                targets.append((item, self.legacy_edge_profile))

        removed: list[str] = []
        for item, path in targets:
            if path.exists():
                if self.is_locked(path) and not self.clear_stale_lock(path):
                    raise RuntimeError(f"Close the Contract Downloader sign-in browser before resetting {path.name}.")
                try:
                    shutil.rmtree(path)
                except OSError as exc:
                    raise RuntimeError(f"Could not reset the app-owned browser profile: {exc}") from exc
                removed.append(path.name)
            manifest["profiles"].pop(item.value, None)
        if manifest["profiles"]:
            self._write_manifest(manifest)
        else:
            try:
                self.manifest_path.unlink(missing_ok=True)
            except OSError as exc:
                raise RuntimeError(f"Could not clear the browser profile registry: {exc}") from exc
        return removed


def build_browser_options(
    installation: BrowserInstallation,
    profile_dir: Path,
    *,
    headless: bool = False,
) -> EdgeOptions | ChromeOptions:
    options: EdgeOptions | ChromeOptions
    if installation.kind is BrowserKind.EDGE:
        options = EdgeOptions()
    else:
        options = ChromeOptions()
    options.page_load_strategy = "eager"
    options.binary_location = installation.executable
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    if headless:
        options.add_argument("--headless=new")
    # These flags only reduce Selenium's automation banner. They do not bypass
    # Coupa authentication or inject credentials.
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    return options


class SeleniumBrowserLauncher:
    def launch(self, installation: BrowserInstallation, profile_dir: Path, *, headless: bool = False) -> Any:
        options = build_browser_options(installation, profile_dir, headless=headless)
        try:
            if installation.kind is BrowserKind.EDGE:
                return webdriver.Edge(options=options)
            return webdriver.Chrome(options=options)
        except WebDriverException as exc:
            raise RuntimeError(f"Could not start {installation.name} for Coupa sign-in: {exc}") from exc


class BrowserLogin:
    """Perform the visible, user-driven login and return Coupa cookies."""

    def __init__(
        self,
        launcher: SeleniumBrowserLauncher | None = None,
        *,
        base_url: str = COUPA_URL,
        poll_interval: float = 0.25,
        wait_timeout: float = 900.0,
        final_navigation_timeout: float = 15.0,
    ):
        self.launcher = launcher or SeleniumBrowserLauncher()
        self.base_url = base_url.rstrip("/")
        self.poll_interval = poll_interval
        self.wait_timeout = wait_timeout
        self.final_navigation_timeout = final_navigation_timeout

    @staticmethod
    def _report(callback: Callable[[str, str], None] | None, state: str, message: str) -> None:
        if callback:
            callback(state, message)

    @staticmethod
    def _auth_redirect(url: str) -> bool:
        lowered = url.lower()
        return any(marker in lowered for marker in AUTH_REDIRECT_MARKERS)

    @staticmethod
    def _url(driver: Any) -> str:
        try:
            return str(driver.current_url or "").lower()
        except Exception:
            return ""

    @staticmethod
    def _has_session_cookie(driver: Any) -> bool:
        try:
            cookie = driver.get_cookie("_coupa_session")
            return bool(cookie and cookie.get("value"))
        except Exception:
            return False

    @staticmethod
    def _window_handles(driver: Any) -> list[str]:
        try:
            return [str(handle) for handle in driver.window_handles]
        except Exception:
            return []

    def _authenticated_window(self, driver: Any) -> str | None:
        """Find a logged-in window, including SSO-created tabs/windows.

        Edge/Chrome may leave an initial new-tab window open while an SSO
        redirect completes in another window. Selenium's ``current_url`` only
        describes the active handle, so checking one handle can miss a valid
        login indefinitely.
        """
        for handle in self._window_handles(driver):
            try:
                driver.switch_to.window(handle)
                if self._is_authenticated(driver):
                    return handle
            except WebDriverException:
                continue
        return None

    @staticmethod
    def _cookies(driver: Any) -> dict[str, str]:
        try:
            return {
                str(cookie.get("name")): str(cookie.get("value"))
                for cookie in driver.get_cookies()
                if cookie.get("name") and cookie.get("value") is not None
            }
        except WebDriverException:
            return {}

    def _is_authenticated(self, driver: Any, url: str | None = None) -> bool:
        current = url if url is not None else self._url(driver)
        return (
            "unilever.coupahost.com" in current
            and not self._auth_redirect(current)
            and self._has_session_cookie(driver)
        )

    def capture(
        self,
        installation: BrowserInstallation,
        profile_dir: Path,
        *,
        headless: bool = False,
        status_callback: Callable[[str, str], None] | None = None,
    ) -> dict[str, str]:
        self._report(
            status_callback,
            "starting",
            f"Opening {installation.name} with the Contract Downloader profile…",
        )
        driver = self.launcher.launch(installation, profile_dir, headless=headless)
        try:
            login_url = f"{self.base_url}/order_headers"
            try:
                driver.get(login_url)
            except WebDriverException as exc:
                raise RuntimeError(f"Could not open Coupa in {installation.name}: {exc}") from exc
            handles = self._window_handles(driver)
            if len(handles) > 1:
                self._report(
                    status_callback,
                    "checking",
                    "Multiple browser windows detected; checking the Coupa session in each one…",
                )

            authenticated_handle = self._authenticated_window(driver)
            if authenticated_handle:
                self._report(status_callback, "checking", "Coupa is open; checking the current session…")
            else:
                self._report(
                    status_callback,
                    "user_action_required",
                    f"Complete the Coupa sign-in in {installation.name}.",
                )

            deadline = time.monotonic() + self.wait_timeout
            while not authenticated_handle:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Timed out waiting for the Coupa sign-in to complete.")
                time.sleep(self.poll_interval)
                authenticated_handle = self._authenticated_window(driver)

            self._report(status_callback, "validating", "Sign-in detected; validating the Coupa session…")
            try:
                driver.switch_to.window(authenticated_handle)
                driver.get(login_url)
            except WebDriverException as exc:
                raise RuntimeError(f"Could not validate the Coupa session in {installation.name}: {exc}") from exc

            deadline = time.monotonic() + self.final_navigation_timeout
            authenticated_handle = self._authenticated_window(driver)
            while time.monotonic() < deadline and not authenticated_handle:
                time.sleep(self.poll_interval)
                authenticated_handle = self._authenticated_window(driver)

            if not authenticated_handle:
                raise RuntimeError("The Coupa sign-in completed, but the authenticated Coupa window was not found.")
            driver.switch_to.window(authenticated_handle)
            cookies = self._cookies(driver)
            if not cookies.get("_coupa_session"):
                raise RuntimeError("The Coupa sign-in completed, but no Coupa session cookie was found.")
            return cookies
        finally:
            try:
                driver.quit()
            except Exception:
                pass
