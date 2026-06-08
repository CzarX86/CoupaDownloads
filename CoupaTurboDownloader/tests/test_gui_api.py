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
