import os
import pytest
import pandas as pd
from unittest.mock import MagicMock, AsyncMock, patch
from src.db.session_db import SessionDB
from src.gui.api import AppAPI

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_gui.db"
    db = SessionDB(str(db_path))
    yield db
    db.close()

@pytest.fixture
def dummy_excel(tmp_path):
    file_path = tmp_path / "po_input.xlsx"
    df = pd.DataFrame({
        'PO Number': ['PO-100', 'PO-101', 'PO-102'],
        'legal entity': ['COMP-A', 'COMP-B', 'COMP-A'],
        'Other Col': ['x', 'y', 'z']
    })
    df.to_excel(file_path, index=False)
    return str(file_path)

def test_import_file_excel(temp_db, dummy_excel):
    api = AppAPI(temp_db, "/tmp/downloads")
    result = api.import_file(dummy_excel)
    
    assert result['success'] is True
    assert result['session_id'] is not None
    assert result['total_pos'] == 3

    session = temp_db.get_session(result['session_id'])
    assert session['execution_type'] == 'PROD'
    
    # Verify POs are stored in DB
    stats = temp_db.get_company_stats(result['session_id'], "COMP-A")
    assert stats['total'] == 2

def test_get_session_history(temp_db):
    api = AppAPI(temp_db, "/tmp/downloads")
    
    # Create two sessions directly
    s1 = temp_db.create_session("file1.xlsx")
    s2 = temp_db.create_session("file2.xlsx")
    
    history = api.get_session_history()
    assert len(history) == 2
    assert history[0]['input_file'] == "file2.xlsx" # Should be reverse chronological
    assert history[1]['input_file'] == "file1.xlsx"
    assert history[0]['execution_type'] == "PROD"

def test_confirm_and_retry_company(temp_db):
    api = AppAPI(temp_db, "/tmp/downloads")
    session_id = temp_db.create_session("file.xlsx")
    
    from src.db.session_db import PODownload
    temp_db.add_po(PODownload(session_id, "PO-1", "COMP-A", "SKIPPED_VERIFICATION_REQUIRED"))
    temp_db.add_po(PODownload(session_id, "PO-2", "COMP-A", "SUCCESS"))
    
    result = api.confirm_and_retry_company(session_id, "COMP-A")
    assert result['success'] is True
    
    # PO-1 should be PENDING again
    po1 = temp_db.get_po(session_id, "PO-1")
    assert po1['status'] == "PENDING"
    
    # PO-2 should remain SUCCESS
    po2 = temp_db.get_po(session_id, "PO-2")
    assert po2['status'] == "SUCCESS"


def test_authentication_exposes_progress_states_without_blocking(temp_db, monkeypatch):
    import asyncio
    import time
    from src.main import TurboAPI

    async def fake_authenticate(*, load_from_file=True, fresh=False, status_callback=None):
        status_callback("starting", "Opening Edge and loading Coupa…")
        await asyncio.sleep(0.08)
        status_callback("user_action_required", "Complete the Coupa sign-in in the Edge window.")
        await asyncio.sleep(0.08)
        status_callback("validating", "Sign-in detected; validating the Coupa session…")
        return {"_coupa_session": "session-value"}

    monkeypatch.setattr("src.main.get_coupa_cookies", fake_authenticate)
    api = TurboAPI(temp_db, "/tmp/downloads")

    started = api.authenticate()
    assert started == {"success": True, "started": True}

    states = []
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        status = api.get_authentication_status()
        states.append(status["state"])
        if status["state"] == "success":
            break
        time.sleep(0.01)

    assert states[-1] == "success"
    assert api._cookies == {"_coupa_session": "session-value"}


def test_relative_download_path_is_resolved_under_user_home(temp_db, monkeypatch, tmp_path):
    monkeypatch.setattr("src.gui.api.Path.home", lambda: tmp_path)
    api = AppAPI(temp_db, "Downloads/CoupaAttachments")

    assert api.default_download_dir == str(tmp_path / "Downloads" / "CoupaAttachments")


def test_edge_driver_version_components_can_be_compared():
    from src.gui.api import AppAPI

    assert AppAPI._version_components("Microsoft Edge 140.0.3485.54") == (140, 0, 3485, 54)
    assert AppAPI._version_components("MSEdgeDriver 140.0.3485.54")[:3] == (140, 0, 3485)


def test_window_uses_85_percent_width_and_is_centered():
    from src.main import calculate_window_geometry

    geometry = calculate_window_geometry(1512, 982)

    assert geometry == {"width": 1285, "height": 820, "x": 114, "y": 81}


def test_macos_coupa_url_uses_configured_default_handler(temp_db, monkeypatch):
    from src.main import TurboAPI

    monkeypatch.setattr("src.main.sys.platform", "darwin")
    api = TurboAPI(temp_db, "/tmp/downloads")
    url = "https://unilever.coupahost.com/order_headers/17105916"
    with patch("src.main.subprocess.run") as run:
        result = api.open_external_url(url)

    assert result["success"] is True
    run.assert_called_once_with(
        ["/usr/bin/open", url],
        check=True,
        timeout=10,
    )


def test_open_coupa_po_strips_prefix_and_uses_default_browser(temp_db):
    from src.main import TurboAPI

    api = TurboAPI(temp_db, "/tmp/downloads")
    with patch.object(api, "open_external_url", return_value={"success": True}) as open_browser:
        result = api.open_coupa_po("PO17138914")

    assert result["success"] is True
    open_browser.assert_called_once_with("https://unilever.coupahost.com/order_headers/17138914")


def test_font_scale_setting_is_validated_and_persisted(temp_db, monkeypatch, tmp_path):
    monkeypatch.setattr("src.gui.api.Path.home", lambda: tmp_path)
    api = AppAPI(temp_db, "Downloads/CoupaAttachments")

    result = api.set_app_settings({
        "download_root": "Downloads/CoupaAttachments",
        "font_scale": 1.2,
    })

    assert result["success"] is True
    assert result["settings"]["font_scale"] == 1.2
    assert AppAPI(temp_db, "Downloads/CoupaAttachments").get_app_settings()["font_scale"] == 1.2

    clamped = api.set_app_settings({
        "download_root": "Downloads/CoupaAttachments",
        "font_scale": 9,
    })
    assert clamped["settings"]["font_scale"] == 1.3


def test_reset_new_run_deletes_only_app_generated_template(temp_db, monkeypatch, tmp_path):
    monkeypatch.setattr("src.gui.api.Path.home", lambda: tmp_path)
    template_dir = tmp_path / "Documents" / "Contract Downloader" / "templates"
    template_dir.mkdir(parents=True)
    generated = template_dir / "input_template_20260729-213140.xlsx"
    generated.write_bytes(b"template")
    external = tmp_path / "input.xlsx"
    external.write_bytes(b"original")
    api = AppAPI(temp_db, "Downloads/CoupaAttachments")

    deleted = api.reset_new_run(str(generated))
    preserved = api.reset_new_run(str(external))

    assert deleted == {"success": True, "deleted": True, "path": str(generated)}
    assert not generated.exists()
    assert preserved == {"success": True, "deleted": False, "preserved": True}
    assert external.exists()


def test_python_portable_disables_startup_update_checks_by_default(temp_db, monkeypatch, tmp_path):
    monkeypatch.setenv("COUPA_PYTHON_PORTABLE", "1")
    monkeypatch.setattr("src.gui.api.Path.home", lambda: tmp_path)

    settings = AppAPI(temp_db, "Downloads/CoupaAttachments").get_app_settings()

    assert settings["python_portable"] is True
    assert settings["auto_updates"] is False


def test_import_file_csv_hierarchy_output_subdir(temp_db, tmp_path):
    csv_path = tmp_path / "hierarchy.csv"
    csv_path.write_text(
        "PO_NUMBER;SUPPLIER;<|>;Year;Quarter;Management Unit L1 Name\n"
        "PO9001;Manpowergroup Inc.;;2026;Q12026;Yellow Wood\n",
        encoding="utf-8",
    )

    api = AppAPI(temp_db, "/tmp/downloads")
    result = api.import_file(str(csv_path))

    assert result["success"] is True
    session_id = result["session_id"]

    cur = temp_db.conn.cursor()
    row = cur.execute(
        "SELECT output_subdir FROM po_downloads WHERE session_id = ? AND po_number = ?",
        (session_id, "PO9001"),
    ).fetchone()
    assert row is not None
    assert row["output_subdir"] == "2026/Q12026/Yellow_Wood"
