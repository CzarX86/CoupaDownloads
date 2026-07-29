import json

from src.engine import authenticator


def _profile(root, directory, *, name, tenant_id="", account_type=0):
    path = root / directory
    path.mkdir(parents=True)
    preferences = {
        "profile": {"name": name},
        "account_info": [
            {
                "edge_account_tenant_id": tenant_id,
                "edge_account_type": account_type,
            }
        ],
    }
    (path / "Preferences").write_text(json.dumps(preferences), encoding="utf-8")


def test_edge_profile_detection_prefers_entra_work_profile_without_email(tmp_path):
    _profile(tmp_path, "Default", name="Personal", account_type=1)
    _profile(tmp_path, "Profile 1", name="Profile 2", tenant_id="tenant-id", account_type=2)
    local_state = {
        "profile": {
            "info_cache": {
                "Default": {"name": "Personal", "is_consented_primary_account": True},
                "Profile 1": {"name": "Profile 2", "is_consented_primary_account": True},
            }
        }
    }
    (tmp_path / "Local State").write_text(json.dumps(local_state), encoding="utf-8")

    assert authenticator._edge_profile_directory(tmp_path) == "Profile 1"


def test_cookie_json_fallback_keeps_underscore_session_cookie(tmp_path, monkeypatch):
    cookie_file = tmp_path / "cookies.json"
    cookie_file.write_text(
        json.dumps({"_coupa_session": "session-value", "other": "value"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(authenticator, "COOKIE_FILE", str(cookie_file))
    monkeypatch.setattr(authenticator, "AUTH_DB", str(tmp_path / "missing.db"))

    assert authenticator.load_cached_cookies() == {
        "_coupa_session": "session-value",
        "other": "value",
    }
