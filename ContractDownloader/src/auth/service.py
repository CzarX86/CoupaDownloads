from __future__ import annotations

import asyncio
from typing import Callable, Mapping

from src.auth.browser import BrowserCatalog, BrowserKind, BrowserLogin, BrowserProfileManager, SeleniumBrowserLauncher
from src.auth.cookie_store import CookieStore, CookieStoreError
from src.auth.models import AuthState, SessionCheck
from src.auth.session_validator import SessionValidator


class AuthService:
    """Single authentication policy shared by GUI and CLI entry points."""

    def __init__(
        self,
        *,
        store: CookieStore | None = None,
        validator: SessionValidator | None = None,
        catalog: type[BrowserCatalog] = BrowserCatalog,
        profiles: BrowserProfileManager | None = None,
        browser_login: BrowserLogin | None = None,
    ):
        self.store = store or CookieStore()
        self.validator = validator or SessionValidator()
        self.catalog = catalog
        self.profiles = profiles or BrowserProfileManager()
        self.browser_login = browser_login or BrowserLogin(SeleniumBrowserLauncher())
        self._cookies: dict[str, str] | None = None

    @property
    def cookies(self) -> dict[str, str] | None:
        return dict(self._cookies) if self._cookies else None

    def set_cookies(self, cookies: Mapping[str, str] | None) -> None:
        self._cookies = {str(key): str(value) for key, value in (cookies or {}).items() if value is not None} or None

    async def check(self) -> SessionCheck:
        """Load and validate the cache, preserving it during outages."""
        cached = self.store.load()
        result = await self.validator.validate(cached)
        if result.state in {AuthState.VALID, AuthState.UNAVAILABLE} and result.has_cached_session:
            self.set_cookies(result.cookies)
            return result
        self.set_cookies(None)
        return result

    async def ensure_session(
        self,
        *,
        interactive: bool,
        browser_preference: str | None = None,
        status_callback: Callable[[str, str], None] | None = None,
        fresh: bool = False,
        headless: bool = False,
    ) -> SessionCheck:
        """Return a usable session or optionally perform visible login.

        GUI callers pass ``interactive=True``. The GUI-launched CLI worker
        passes ``interactive=False`` so an expired session produces a clear
        authentication-required result instead of opening an untracked second
        browser. Direct CLI use can opt into the interactive path.
        """
        current = await self.check()
        if not fresh and (current.state is AuthState.VALID or (current.state is AuthState.UNAVAILABLE and current.has_cached_session)):
            return current
        if not interactive:
            return current
        return await self.authenticate(
            browser_preference=browser_preference,
            status_callback=status_callback,
            fresh=fresh,
            headless=headless,
            _skip_cache_check=True,
        )

    async def authenticate(
        self,
        *,
        browser_preference: str | None = None,
        status_callback: Callable[[str, str], None] | None = None,
        fresh: bool = False,
        headless: bool = False,
        _skip_cache_check: bool = False,
    ) -> SessionCheck:
        """Capture a fresh session through an app-owned Edge/Chrome profile."""
        if not fresh and not _skip_cache_check:
            # Check the shared cache before resolving a browser. A valid
            # session should not require a browser installation or a second
            # Coupa request after the caller already checked it.
            current = await self.check()
            if current.state is AuthState.VALID:
                if status_callback:
                    status_callback("success", "Cached Coupa session is valid.")
                return current

        installation = self.catalog.select(browser_preference)
        if fresh:
            # Reset only the selected app-owned profile. Personal profiles are
            # never discovered, opened, or deleted by this service.
            self.store.clear()
            self.profiles.clear(installation.kind)

        profile_dir = self.profiles.ensure(installation.kind)
        cookies = self.browser_login.capture(
            installation,
            profile_dir,
            headless=headless,
            status_callback=status_callback,
        )
        validation = await self.validator.validate(cookies)
        if validation.state is AuthState.EXPIRED:
            raise RuntimeError("Coupa rejected the captured session. Complete the sign-in and try again.")

        try:
            self.store.save(cookies)
        except CookieStoreError:
            raise
        self.set_cookies(cookies)

        if validation.state is AuthState.UNAVAILABLE:
            result = SessionCheck(
                AuthState.UNAVAILABLE,
                "Sign-in completed; Coupa session validation is temporarily unavailable. The cached session will be tried during the run.",
                cookies,
                "capture",
            )
            if status_callback:
                status_callback("success", result.message)
            return result

        result = SessionCheck(AuthState.VALID, "Coupa session captured and validated.", cookies, "capture")
        if status_callback:
            status_callback("success", result.message)
        return result

    def reset(self) -> dict[str, object]:
        """Clear cache and only profiles owned by the application."""
        result: dict[str, object] = {"success": True, "removed": []}
        try:
            cache_result = self.store.clear()
            result["removed"] = list(cache_result.get("removed", []))
        except CookieStoreError as exc:
            return {"success": False, "error": str(exc)}

        try:
            profiles = self.profiles.clear()
            result["removed"] = [*result["removed"], *profiles]  # type: ignore[list-item]
        except RuntimeError as exc:
            # The cache is already cleared safely; report the profile issue so
            # the user can close only the app-owned sign-in browser and retry.
            result["success"] = False
            result["error"] = str(exc)
        self.set_cookies(None)
        return result

    def browser_options(self, preference: str | None = None) -> dict[str, object]:
        options = dict(self.catalog.as_settings(preference))
        profile_info = getattr(self.profiles, "info", None)
        if profile_info:
            options["profiles"] = {
                kind.value: profile_info(kind)
                for kind in BrowserKind
            }
        else:
            options["profiles"] = {}
        return options


def run_async(coro):
    """Run a service coroutine from the synchronous pywebview/CLI bridge."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # pywebview API methods are synchronous, but this fallback keeps the
    # service usable from an embedding loop without nesting asyncio.run().
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
