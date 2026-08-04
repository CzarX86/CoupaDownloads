from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Mapping


class CookieStoreError(RuntimeError):
    """Raised when the local session cache cannot be persisted."""


class CookieStore:
    """Persistent local cookie cache with legacy JSON/SQLite compatibility.

    The two existing formats are intentionally kept during the migration. The
    The atomic ``cookies.json`` snapshot is preferred when it contains the
    Coupa session cookie, while SQLite remains a fallback for installations
    created by older releases or interrupted writes. No expiration is inferred
    locally; Coupa remains authoritative.
    """

    def __init__(self, cookie_file: str | os.PathLike[str] | None = None, db_path: str | os.PathLike[str] | None = None):
        root = Path.home() / ".contract_downloader"
        self.cookie_file = Path(cookie_file).expanduser() if cookie_file else root / "cookies.json"
        self.db_path = Path(db_path).expanduser() if db_path else root / "auth_cache.db"

    @property
    def root(self) -> Path:
        return self.cookie_file.parent

    @staticmethod
    def _normalise(value: object) -> dict[str, str] | None:
        if not isinstance(value, Mapping):
            return None
        cookies = {str(key): str(item) for key, item in value.items() if item is not None}
        return cookies or None

    @staticmethod
    def _has_session(cookies: Mapping[str, str] | None) -> bool:
        return bool(cookies and cookies.get("_coupa_session"))

    def _ensure_root(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.root, 0o700)
        except OSError:
            pass

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.db_path.parent, 0o700)
        except OSError:
            pass
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_cache (
                    key TEXT PRIMARY KEY,
                    cookies_json TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                """
            )
            conn.commit()
        try:
            os.chmod(self.db_path, 0o600)
        except OSError:
            pass

    def _load_db(self) -> dict[str, str] | None:
        if not self.db_path.exists():
            return None
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT cookies_json FROM auth_cache WHERE key = 'coupa'"
                ).fetchone()
            if not row:
                return None
            return self._normalise(json.loads(row[0]))
        except (OSError, sqlite3.Error, TypeError, ValueError, json.JSONDecodeError):
            return None

    def _load_json(self) -> dict[str, str] | None:
        if not self.cookie_file.exists():
            return None
        try:
            return self._normalise(json.loads(self.cookie_file.read_text(encoding="utf-8")))
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return None

    def load(self) -> dict[str, str] | None:
        database = self._load_db()
        legacy = self._load_json()
        # The JSON snapshot is written atomically before SQLite. Prefer it when
        # both copies contain a session: after a crash or locked SQLite file it
        # can contain the newest successful login while the DB still has the
        # previous cookie set. SQLite remains the fallback for older installs
        # where the JSON file is absent or incomplete.
        if self._has_session(legacy):
            return legacy
        if self._has_session(database):
            return database
        return database or legacy

    def save(self, cookies: Mapping[str, str]) -> None:
        normalised = self._normalise(cookies)
        if not self._has_session(normalised):
            raise CookieStoreError("Cannot cache a Coupa session without _coupa_session.")

        self._ensure_root()
        payload = json.dumps(normalised, separators=(",", ":"))
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.cookie_file.parent,
                prefix=f".{self.cookie_file.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary_path = Path(handle.name)
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.chmod(temporary_path, 0o600)
            except OSError:
                pass
            os.replace(temporary_path, self.cookie_file)
            temporary_path = None

            self._init_db()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO auth_cache (key, cookies_json, updated_at)
                    VALUES ('coupa', ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        cookies_json = excluded.cookies_json,
                        updated_at = excluded.updated_at
                    """,
                    (payload, int(time.time())),
                )
                conn.commit()
        except (OSError, sqlite3.Error) as exc:
            raise CookieStoreError(f"Could not persist the Coupa session: {exc}") from exc
        finally:
            if temporary_path:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def clear(self) -> dict[str, object]:
        removed: list[str] = []
        try:
            self.cookie_file.unlink(missing_ok=True)
            removed.append("cookies")
        except OSError as exc:
            raise CookieStoreError(f"Could not clear cached cookies: {exc}") from exc

        if self.db_path.exists():
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("DELETE FROM auth_cache WHERE key = 'coupa'")
                    conn.commit()
                removed.append("auth_cache")
            except sqlite3.Error as exc:
                raise CookieStoreError(f"Could not clear authentication database: {exc}") from exc
        return {"success": True, "removed": removed}
