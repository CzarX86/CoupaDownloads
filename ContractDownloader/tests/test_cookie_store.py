import json

from src.auth.cookie_store import CookieStore


def test_cookie_store_round_trips_json_and_sqlite(tmp_path):
    store = CookieStore(tmp_path / "cookies.json", tmp_path / "auth_cache.db")
    cookies = {"_coupa_session": "session", "other": "value"}

    store.save(cookies)

    assert store.load() == cookies
    assert (tmp_path / "cookies.json").exists()
    assert (tmp_path / "auth_cache.db").exists()


def test_cookie_store_prefers_session_cookie_in_legacy_json(tmp_path):
    cookie_file = tmp_path / "cookies.json"
    cookie_file.write_text(json.dumps({"_coupa_session": "legacy", "other": "value"}), encoding="utf-8")
    store = CookieStore(cookie_file, tmp_path / "missing.db")

    assert store.load() == {"_coupa_session": "legacy", "other": "value"}


def test_cookie_store_uses_newest_atomic_json_after_database_write_failure(tmp_path):
    cookie_file = tmp_path / "cookies.json"
    store = CookieStore(cookie_file, tmp_path / "auth_cache.db")
    store.save({"_coupa_session": "old", "other": "value"})
    cookie_file.write_text(json.dumps({"_coupa_session": "new", "other": "value"}), encoding="utf-8")

    assert store.load() == {"_coupa_session": "new", "other": "value"}


def test_cookie_store_rejects_missing_session_cookie(tmp_path):
    store = CookieStore(tmp_path / "cookies.json", tmp_path / "auth_cache.db")

    try:
        store.save({"other": "value"})
    except RuntimeError as exc:
        assert "_coupa_session" in str(exc)
    else:
        raise AssertionError("Expected missing-session error")
