import asyncio
import json
import os
import sqlite3
import sys
import threading
import time
from typing import Dict, Optional

import httpx
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait

COUPA_URL = "https://unilever.coupahost.com"
COOKIE_FILE = os.path.join(os.path.dirname(__file__), "..", "..", ".cookies.json")
AUTH_DB = os.path.expanduser("~/.coupa_turbo/auth_cache.db")


def _init_auth_db() -> None:
    os.makedirs(os.path.dirname(AUTH_DB), exist_ok=True)
    conn = sqlite3.connect(AUTH_DB)
    try:
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


def load_cached_cookies() -> Optional[Dict[str, str]]:
    cached_db = load_cached_cookies_db()
    cached_file: Optional[Dict[str, str]] = None

    if os.path.exists(COOKIE_FILE):
        try:
            with open(COOKIE_FILE, encoding="utf-8") as f:
                saved = json.load(f)
            cached_file = {k: v for k, v in saved.items() if not k.startswith("_")}
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


async def validate_cookies(cookies: Dict[str, str]) -> bool:
    """Validate by hitting a lightweight authenticated endpoint (PO list page).
    If the final URL stays on coupahost.com and is NOT a login/oauth redirect, cookies are valid.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
        ),
    }
    try:
        async with httpx.AsyncClient(
            cookies=cookies, headers=headers, follow_redirects=True, timeout=10.0
        ) as client:
            resp = await client.get(f"{COUPA_URL}/order_headers")
            final_url = str(resp.url).lower()
            if resp.status_code == 200 and "coupahost.com" in final_url:
                if not any(word in final_url for word in ("/login", "/oauth", "/sso", "/authorization", "openid", "pingfederate")):
                    return True
            return False
    except Exception:
        return False


async def get_coupa_cookies(headless: bool = False, load_from_file: bool = True) -> Dict[str, str]:
    """
    Obtain Coupa session cookies via Selenium Edge.

    Opens Edge to Coupa homepage (redirects to login). User completes manual
    login including SSO/OAuth flow. System validates cookies by navigating to
    a PO page, then extracts and caches them.
    """
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

    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Edge(options=options)

    def _safe_current_url_lower() -> str:
        try:
            value = driver.current_url
            return (value or "").lower()
        except Exception:
            return ""

    try:
        driver.get(COUPA_URL)

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
                on_auth = any(
                    word in current
                    for word in ("/login", "/oauth", "/sso", "/authorization", "openid")
                )
                if on_coupa and not on_auth:
                    print("[AUTH] Login detectado (via ENTER)!")
                    break
                else:
                    print("[AUTH] Login ainda nao detectado. Continuando espera passiva...")

            time.sleep(1)
            current = _safe_current_url_lower()
            if not current:
                if time.time() - started_wait > 900:
                    raise TimeoutError("Falha ao ler URL atual do browser durante autenticacao")
                continue
            on_coupa = "unilever.coupahost.com" in current
            on_auth = any(
                word in current
                for word in ("/login", "/oauth", "/sso", "/authorization", "openid")
            )
            if on_coupa and not on_auth:
                break

        print("[AUTH] Login detectado! Navegando para o Coupa para capturar cookies de sessao...")
        # Navigate explicitly to Coupa domain to ensure we capture Coupa session cookies
        # (not just SSO/OAuth domain cookies)
        driver.get(COUPA_URL + "/order_headers")
        time.sleep(4)

        # Verify we actually landed on an authenticated Coupa page
        final_url = _safe_current_url_lower()
        if any(word in final_url for word in ("/login", "/oauth", "/sso", "/authorization", "openid", "pingfederate")):
            print("[AUTH] Ainda em pagina de auth apos navegar. Aguardando mais 5s...")
            time.sleep(5)
            final_url = _safe_current_url_lower()

        cookies_list = driver.get_cookies()
        cookies = {c["name"]: c["value"] for c in cookies_list}
        shown_url = _safe_current_url_lower() or "(url indisponivel)"
        print(f"[AUTH] {len(cookies)} cookies capturados do dominio: {shown_url[:80]}")

        cookie_data = {**cookies, "_expires_at": time.time() + 28800, "_saved_at": time.time()}  # 8h TTL
        os.makedirs(os.path.dirname(COOKIE_FILE), exist_ok=True)
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            json.dump(cookie_data, f)
        save_cached_cookies_db(cookies)

        print(f"[AUTH] Cookies extraidos e cacheados (validade: 8h). Total: {len(cookies)} cookies.")
        print(f"[AUTH] Chaves: {list(cookies.keys())}\n")
        return cookies

    finally:
        driver.quit()
