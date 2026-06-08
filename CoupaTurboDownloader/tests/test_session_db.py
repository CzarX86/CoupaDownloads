import os
import sqlite3
import pytest
from src.db.session_db import SessionDB, PODownload


@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_session.db"
    db = SessionDB(str(db_path))
    yield db
    db.close()


def test_db_initialization(tmp_path):
    db_path = tmp_path / "init_test.db"
    db = SessionDB(str(db_path))
    cursor = db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}
    assert "sessions" in tables
    assert "po_downloads" in tables
    db.close()


def test_create_session(temp_db):
    session_id = temp_db.create_session("input_test.xlsx")
    assert session_id is not None
    session = temp_db.get_session(session_id)
    assert session["id"] == session_id
    assert session["input_file"] == "input_test.xlsx"
    assert session["execution_type"] == "PROD"
    assert session["status"] == "PENDING"


def test_create_session_with_test_execution_type(temp_db):
    session_id = temp_db.create_session("input_test.xlsx", execution_type="TEST")
    session = temp_db.get_session(session_id)
    assert session["execution_type"] == "TEST"


def test_add_and_update_po(temp_db):
    session_id = temp_db.create_session("input_test.xlsx")

    po = PODownload(session_id=session_id, po_number="PO-123", company_code="COMP-A", status="PENDING")
    temp_db.add_po(po)
    temp_db.update_po_status(session_id, "PO-123", "SUCCESS", "/downloads/COMP-A/PO-123", 3, None)

    retrieved = temp_db.get_po(session_id, "PO-123")
    assert retrieved["status"] == "SUCCESS"
    assert retrieved["download_folder"] == "/downloads/COMP-A/PO-123"
    assert retrieved["attachment_count"] == 3


def test_add_po_with_attachment_count(temp_db):
    session_id = temp_db.create_session("input.xlsx")
    po = PODownload(session_id=session_id, po_number="PO-1", company_code="CC", attachment_count=5)
    temp_db.add_po(po)

    retrieved = temp_db.get_po(session_id, "PO-1")
    assert retrieved["attachment_count"] == 5


def test_update_po_status_default_args(temp_db):
    """Backward compat: update_po_status works with only required args."""
    session_id = temp_db.create_session("input.xlsx")
    temp_db.add_po(PODownload(session_id=session_id, po_number="PO-X", company_code="CC"))

    temp_db.update_po_status(session_id, "PO-X", "ERROR")
    retrieved = temp_db.get_po(session_id, "PO-X")
    assert retrieved["status"] == "ERROR"


def test_circuit_breaker_stats(temp_db):
    session_id = temp_db.create_session("input.xlsx")

    for i in range(10):
        temp_db.add_po(PODownload(
            session_id=session_id, po_number=f"PO-{i}", company_code="COMP-A", status="PENDING"
        ))

    temp_db.update_po_status(session_id, "PO-0", "ERROR")
    temp_db.update_po_status(session_id, "PO-1", "ERROR")

    stats = temp_db.get_company_stats(session_id, "COMP-A")
    assert stats["total"] == 10
    assert stats["processed"] == 2
    assert stats["errors"] == 2
    assert stats["success"] == 0
    assert stats["processed"] / stats["total"] >= 0.15
    assert stats["errors"] == stats["processed"]


def test_suspend_company_code(temp_db):
    session_id = temp_db.create_session("input.xlsx")
    for i in range(5):
        temp_db.add_po(PODownload(session_id=session_id, po_number=f"PO-{i}", company_code="COMP-X", status="PENDING"))

    temp_db.suspend_company_code(session_id, "COMP-X")

    for i in range(5):
        po = temp_db.get_po(session_id, f"PO-{i}")
        assert po["status"] == "SKIPPED_VERIFICATION_REQUIRED"


def test_migration_adds_attachment_count(tmp_path):
    """Existing DB without attachment_count column gets migrated."""
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute('''
        CREATE TABLE IF NOT EXISTS po_downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            po_number TEXT NOT NULL,
            company_code TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            download_folder TEXT,
            error_message TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(session_id, po_number)
        )
    ''')
    conn.commit()
    conn.close()

    db = SessionDB(str(db_path))
    cursor = db.conn.cursor()
    columns = {row[1] for row in cursor.execute("PRAGMA table_info(po_downloads)")}
    assert "attachment_count" in columns

    session_id = db.create_session("test.xlsx")
    db.add_po(PODownload(session_id=session_id, po_number="PO-1", company_code="CC", attachment_count=2))
    assert db.get_po(session_id, "PO-1")["attachment_count"] == 2
    db.close()


def test_migration_adds_execution_type_to_sessions(tmp_path):
    db_path = tmp_path / "legacy_sessions.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            input_file TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute("INSERT INTO sessions (input_file, status) VALUES ('legacy_input.xlsx', 'PENDING')")
    conn.commit()
    conn.close()

    db = SessionDB(str(db_path))
    cursor = db.conn.cursor()
    columns = {row[1] for row in cursor.execute("PRAGMA table_info(sessions)")}
    assert "execution_type" in columns

    row = cursor.execute("SELECT execution_type FROM sessions WHERE input_file = 'legacy_input.xlsx'").fetchone()
    assert row is not None
    assert row["execution_type"] == "PROD"

    new_session = db.create_session("fresh_test.xlsx", execution_type="TEST")
    assert db.get_session(new_session)["execution_type"] == "TEST"
    db.close()
