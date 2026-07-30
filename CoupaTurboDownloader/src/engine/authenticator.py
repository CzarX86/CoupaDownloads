import asyncio
import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.edge.options import Options

from src.engine.tls import system_ssl_context

COUPA_URL = "https://unilever.coupahost.com"
WORK_PROFILE_TOKENS = ("work", "trabalho", "business", "empresa", "corporate", "profissional")
# Authentication state belongs to the user's persistent application data, not
# the install directory (which can be replaced by updates or PyInstaller).
COOKIE_FILE = os.path.expanduser("~/.coupa_turbo/cookies.json")
AUTH_DB = os.path.expanduser("~/.coupa_turbo/auth_cache.db")
EDGE_AUTH_PROFILE_DIR = Path.home() / ".coupa_turbo" / "edge_auth_profile"


def _init_auth_db() -> None:
    os.makedirs(os.path.dirname(AUTH_DB), exist_ok=True)
    conn = sqlite3.connect(AUTH_DB)
    try:
        try:
            os.chmod(AUTH_DB, 0o600)
        except OSError:
            pass
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_cache (
                key TEXT PRIMARY KEY,
                cookies_json TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_cached_cookies_db(cookies: Dict[str, str]) -> None:
    _init_auth_db()
    conn = sqlite3.connect(AUTH_DB)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO auth_cache (key, cookies_json, updated_at)
            VALUES ('coupa', ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                cookies_json = excluded.cookies_json,
                updated_at = excluded.updated_at
            """,
            (json.dumps(cookies), int(time.time())),
        )
        conn.commit()
    finally:
        conn.close()


def load_cached_cookies_db() -> Optional[Dict[str, str]]:
    if not os.path.exists(AUTH_DB):
        return None
    conn = sqlite3.connect(AUTH_DB)
    try:
        cur = conn.cursor()
        row = cur.execute(
            "SELECT cookies_json FROM auth_cache WHERE key = 'coupa'"
        ).fetchone()
        if not row:
            return None
        data = json.loads(row[0])
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items() if v is not None}
        return None
    except Exception:
        return None
    finally:
        conn.close()


def clear_cached_authentication(*, remove_app_profile: bool = False) -> Dict[str, Any]:
    """Clear Coupa cookies and optionally the app-owned Edge profile.

    The user's normal Edge Work profile is never removed. Removing the
    dedicated app profile is refused while Edge is running to avoid corrupting
    Chromium's locked files.
    """
    if remove_app_profile and _edge_is_running():
        return {
            "success": False,
            "error": "Close all Microsoft Edge windows before resetting the Coupa sign-in state.",
        }

    removed = []
    try:
        Path(COOKIE_FILE).unlink(missing_ok=True)
        removed.append("cookies")
    except OSError as exc:
        return {"success": False, "error": f"Could not clear cached cookies: {exc}"}

    try:
        if Path(AUTH_DB).exists():
            conn = sqlite3.connect(AUTH_DB)
            try:
                conn.execute("DELETE FROM auth_cache WHERE key = 'coupa'")
                conn.commit()
            finally:
                conn.close()
            removed.append("auth_cache")
    except sqlite3.Error as exc:
        return {"success": False, "error": f"Could not clear authentication database: {exc}"}

    if remove_app_profile and EDGE_AUTH_PROFILE_DIR.exists():
        try:
            shutil.rmtree(EDGE_AUTH_PROFILE_DIR)
            removed.append("app_edge_profile")
        except OSError as exc:
            return {"success": False, "error": f"Could not reset the app Edge profile: {exc}"}

    return {"success": True, "removed": removed}


def load_cached_cookies() -> Optional[Dict[str, str]]:
    cached_db = load_cached_cookies_db()
    cached_file: Optional[Dict[str, str]] = None

    if os.path.exists(COOKIE_FILE):
        try:
            with open(COOKIE_FILE, encoding="utf-8") as f:
                saved = json.load(f)
            # Keep every cookie name, including underscore-prefixed session
            # cookies, so JSON remains a usable fallback to SQLite.
            cached_file = {str(k): str(v) for k, v in saved.items() if v is not None}
        except (json.JSONDecodeError, KeyError):
            cached_file = None

    def has_session_cookie(cookies: Optional[Dict[str, str]]) -> bool:
        return bool(cookies and cookies.get("_coupa_session"))

    if has_session_cookie(cached_db):
        return cached_db
    if has_session_cookie(cached_file):
        return cached_file
    if cached_db:
        return cached_db
    return cached_file


async def validate_cookies_detailed(cookies: Dict[str, str]) -> tuple[bool, str]:
    """Validate cached cookies and distinguish expiry from a temporary outage."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
        ),
    }
    try:
        async with httpx.AsyncClient(
            cookies=cookies,
            headers=headers,
            follow_redirects=True,
            timeout=10.0,
            verify=system_ssl_context(),
        ) as client:
            resp = await client.get(f"{COUPA_URL}/order_headers")
            final_url = str(resp.url).lower()
            auth_redirect = any(
                word in final_url
                for word in ("/login", "/oauth", "/sso", "/authorization", "openid", "pingfederate")
            )
            if resp.status_code == 200 and "coupahost.com" in final_url and not auth_redirect:
                return True, "valid"
            if resp.status_code in {401, 403} or auth_redirect:
                return False, "expired"
            if resp.status_code >= 500:
                return False, "unavailable"
            return False, "expired"
    except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError):
        return False, "unavailable"
    except Exception:
        return False, "unavailable"


async def validate_cookies(cookies: Dict[str, str]) -> bool:
    """Backward-compatible boolean validation for callers that only need validity."""
    valid, _reason = await validate_cookies_detailed(cookies)
    return valid


def _edge_user_data_dir() -> Optional[Path]:
    configured = os.environ.get("COUPA_EDGE_USER_DATA_DIR", "").strip()
    candidates = [Path(configured).expanduser()] if configured else []
    if sys.platform == "darwin":
        candidates.append(Path.home() / "Library" / "Application Support" / "Microsoft Edge")
    elif os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            candidates.append(Path(local_app_data) / "Microsoft" / "Edge" / "User Data")
    else:
        candidates.append(Path.home() / ".config" / "microsoft-edge")
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def _edge_profile_directory(user_data_dir: Path) -> str:
    """Prefer a work profile without inspecting or hardcoding an email address."""
    configured = os.environ.get("COUPA_EDGE_PROFILE_DIRECTORY", "").strip()
    if configured and (user_data_dir / configured).is_dir():
        return configured

    candidates: list[tuple[int, str]] = []
    try:
        info_cache = json.loads(
            (user_data_dir / "Local State").read_text(encoding="utf-8")
        ).get("profile", {}).get("info_cache", {})
    except (OSError, ValueError, AttributeError):
        info_cache = {}

    for directory, info in info_cache.items():
        profile_path = user_data_dir / directory
        if not profile_path.is_dir() or not isinstance(info, dict):
            continue
        name = " ".join(str(info.get(key, "")) for key in ("name", "shortcut_name")).lower()
        hosted_domain = str(info.get("hosted_domain", "")).strip().lower()
        score = 10 if hosted_domain else 0
        if any(token in name for token in WORK_PROFILE_TOKENS):
            score += 5
        if info.get("is_consented_primary_account"):
            score += 1

        # Edge doesn't always expose hosted_domain in Local State. Entra work
        # profiles can still be recognized through non-sensitive account type
        # and tenant metadata in Preferences; email values are never read.
        try:
            preferences = json.loads((profile_path / "Preferences").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            preferences = {}
        if preferences.get("profile", {}).get("is_relative_to_aad"):
            score += 10
        for account in preferences.get("account_info", []):
            if not isinstance(account, dict):
                continue
            if str(account.get("edge_account_tenant_id", "")).strip():
                score += 15
                break
            account_type = str(account.get("edge_account_type", "")).strip().lower()
            if account_type not in {"", "0", "none"}:
                score += 8
                break
        candidates.append((score, directory))

    if candidates:
        candidates.sort(key=lambda item: (-item[0], item[1] != "Default", item[1]))
        return candidates[0][1]
    return "Default"


def _edge_options(
    headless: bool,
    user_data_dir: Optional[Path],
    profile_directory: str = "Default",
) -> Options:
    options = Options()
    options.page_load_strategy = "eager"
    if headless:
        options.add_argument("--headless=new")
    if user_data_dir:
        options.add_argument(f"--user-data-dir={user_data_dir}")
        options.add_argument(f"--profile-directory={profile_directory}")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    return options


def _edge_is_running() -> bool:
    """Avoid waiting for WebDriver to fail against an already locked profile."""
    try:
        if os.name == "nt":
            output = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq msedge.exe"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            ).stdout.lower()
            return "msedge.exe" in output
        output = subprocess.run(
            ["ps", "-ax", "-o", "command="],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        ).stdout.lower()
        return "microsoft edge" in output or "/msedge" in output
    except (OSError, subprocess.SubprocessError):
        return False


def _start_edge_with_profile(headless: bool, prefer_existing: bool = True) -> Any:
    """Prefer the user's Edge profile and fall back when it is locked.

    Edge locks its user-data directory while running. If that happens, a
    separate persistent Coupa profile lets the user keep Edge open without
    attempting to attach to or modify the running browser process.
    """
    profile_dir = _edge_user_data_dir() if prefer_existing and not headless else None
    if profile_dir and not _edge_is_running():
        try:
            profile_name = _edge_profile_directory(profile_dir)
            print(f"[AUTH] Usando o perfil existente do Edge: {profile_dir}/{profile_name}")
            return webdriver.Edge(options=_edge_options(headless, profile_dir, profile_name))
        except WebDriverException as exc:
            print(f"[AUTH] Perfil existente indisponível; usando perfil Coupa separado: {exc}")
    elif profile_dir:
        print("[AUTH] Edge já está aberto; usando perfil Coupa separado para evitar conflito.")

    EDGE_AUTH_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[AUTH] Usando perfil persistente do app: {EDGE_AUTH_PROFILE_DIR}")
    return webdriver.Edge(options=_edge_options(headless, EDGE_AUTH_PROFILE_DIR))


def _close_auth_driver(driver: Any) -> None:
    driver.quit()


async def get_coupa_cookies(
    headless: bool = False,
    load_from_file: bool = True,
    fresh: bool = False,
) -> Dict[str, str]:
    """
    Obtain Coupa session cookies via Selenium Edge.

    Opens Edge to Coupa homepage (redirects to login). User completes manual
    login including SSO/OAuth flow. System validates cookies by navigating to
    a PO page, then extracts and caches them.
    """
    if fresh:
        cleared = clear_cached_authentication(remove_app_profile=True)
        if not cleared.get("success"):
            raise RuntimeError(str(cleared.get("error") or "Could not reset authentication state."))
        load_from_file = False

    if load_from_file:
        cached = load_cached_cookies()
        if cached and await validate_cookies(cached):
            return cached

    print("\n" + "=" * 60)
    print("  AUTENTICACAO NECESSARIA")
    print("  Edge sera aberto. Faca login no Coupa.")
    print("  O sistema detectara automaticamente e continuara.")
    print("  Pressione ENTER para forcar verificacao imediata.")
    print("=" * 60 + "\n")

    driver = _start_edge_with_profile(headless, prefer_existing=True)

    def _safe_current_url_lower() -> str:
        try:
            value = driver.current_url
            return (value or "").lower()
        except Exception:
            return ""

    def _is_auth_redirect(url: str) -> bool:
        return any(
            word in url
            for word in ("/login", "/oauth", "/sso", "/authorization", "openid", "pingfederate")
        )

    def _has_coupa_session_cookie() -> bool:
        try:
            return bool(driver.get_cookie("_coupa_session"))
        except Exception:
            return False

    def _is_authenticated_url(url: str) -> bool:
        return (
            "unilever.coupahost.com" in url
            and not _is_auth_redirect(url)
            and _has_coupa_session_cookie()
        )

    try:
        login_url = COUPA_URL + "/order_headers"
        try:
            driver.get(login_url)
        except WebDriverException as exc:
            raise RuntimeError(f"Could not open Coupa in the existing Edge profile: {exc}") from exc

        print("[AUTH] Aguardando login (detecao passiva, ENTER para forcar verificacao)...")

        enter_event = threading.Event()

        def _listen_for_enter() -> None:
            while True:
                try:
                    input()
                    enter_event.set()
                except (EOFError, OSError):
                    break

        input_thread = threading.Thread(target=_listen_for_enter, daemon=True)
        input_thread.start()

        started_wait = time.time()
        while True:
            if enter_event.is_set():
                enter_event.clear()
                current = _safe_current_url_lower()
                on_coupa = "unilever.coupahost.com" in current
                on_auth = _is_auth_redirect(current)
                if on_coupa and not on_auth and _has_coupa_session_cookie():
                    print("[AUTH] Login detectado (via ENTER)!")
                    break
                else:
                    print("[AUTH] Login ainda nao detectado. Continuando espera passiva...")

            time.sleep(0.25)
            current = _safe_current_url_lower()
            if not current:
                if time.time() - started_wait > 900:
                    raise TimeoutError("Falha ao ler URL atual do browser durante autenticacao")
                continue
            on_coupa = "unilever.coupahost.com" in current
            on_auth = _is_auth_redirect(current)
            if on_coupa and not on_auth and _has_coupa_session_cookie():
                break

        print("[AUTH] Login detectado! Navegando para o Coupa para capturar cookies de sessao...")
        # Navigate explicitly to Coupa domain to ensure we capture Coupa session cookies
        # (not just SSO/OAuth domain cookies)
        driver.get(COUPA_URL + "/order_headers")

        # Wait only until the authenticated Coupa URL is visible. Avoid the
        # previous fixed 4s + 5s delays after SSO redirects.
        deadline = time.time() + 15
        final_url = _safe_current_url_lower()
        while time.time() < deadline and not _is_authenticated_url(final_url):
            time.sleep(0.25)
            final_url = _safe_current_url_lower()

        cookies_list = driver.get_cookies()
        cookies = {c["name"]: c["value"] for c in cookies_list}
        shown_url = _safe_current_url_lower() or "(url indisponivel)"
        print(f"[AUTH] {len(cookies)} cookies capturados do dominio: {shown_url[:80]}")
        if not cookies.get("_coupa_session"):
            raise RuntimeError("O login foi concluido, mas o cookie de sessao do Coupa nao foi encontrado.")
        valid, reason = await validate_cookies_detailed(cookies)
        if not valid and reason == "expired":
            raise RuntimeError("O Coupa rejeitou a sessao capturada. Conclua o login e tente novamente.")

        # Persist only the cookie values. There is deliberately no local TTL;
        # validity is decided by Coupa when the cached session is validated.
        os.makedirs(os.path.dirname(COOKIE_FILE), exist_ok=True)
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            json.dump(cookies, f)
        try:
            os.chmod(COOKIE_FILE, 0o600)
        except OSError:
            pass
        save_cached_cookies_db(cookies)

        print(f"[AUTH] Cookies extraidos e cacheados sem expiracao artificial. Total: {len(cookies)} cookies.")
        print(f"[AUTH] Chaves: {list(cookies.keys())}\n")
        return cookies

    finally:
        _close_auth_driver(driver)
