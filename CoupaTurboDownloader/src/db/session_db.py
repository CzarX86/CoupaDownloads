import hashlib
import shutil
import sqlite3
import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, List

@dataclass
class PODownload:
    session_id: int
    po_number: str
    company_code: str
    status: str = "PENDING"
    output_subdir: Optional[str] = None
    download_folder: Optional[str] = None
    attachment_count: Optional[int] = 0
    error_message: Optional[str] = None

class SessionDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                input_file TEXT NOT NULL,
                execution_type TEXT DEFAULT 'PROD',
                concurrency INTEGER DEFAULT 4,
                duration_seconds REAL,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS retry_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                po_number TEXT,
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                status_before TEXT,
                status_after TEXT,
                error_message TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS po_downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                po_number TEXT NOT NULL,
                company_code TEXT NOT NULL,
                output_subdir TEXT,
                status TEXT DEFAULT 'PENDING',
                download_folder TEXT,
                attachment_count INTEGER DEFAULT 0,
                error_message TEXT,
                remarks TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id),
                UNIQUE(session_id, po_number)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS retry_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                original_po_number TEXT NOT NULL,
                edited_po_number TEXT NOT NULL,
                staging_dir TEXT NOT NULL,
                status TEXT DEFAULT 'RUNNING',
                error_message TEXT,
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
        ''')

        self._migrate()

        self.conn.commit()

    def _migrate(self):
        """Add columns that may be missing from existing databases."""
        cursor = self.conn.cursor()
        sessions_existing = {row[1] for row in cursor.execute("PRAGMA table_info(sessions)")}
        if "execution_type" not in sessions_existing:
            cursor.execute(
                "ALTER TABLE sessions ADD COLUMN execution_type TEXT DEFAULT 'PROD'"
            )
        for column, definition in {
            "concurrency": "INTEGER DEFAULT 4",
            "duration_seconds": "REAL",
            "input_file_path": "TEXT",
            "input_file_blob": "BLOB",
            "input_file_sha256": "TEXT",
            "input_file_size": "INTEGER",
        }.items():
            if column not in sessions_existing:
                cursor.execute(f"ALTER TABLE sessions ADD COLUMN {column} {definition}")

        existing = {row[1] for row in cursor.execute("PRAGMA table_info(po_downloads)")}

        if "remarks" not in existing:
            cursor.execute("ALTER TABLE po_downloads ADD COLUMN remarks TEXT")
        if "attachment_count" not in existing:
            cursor.execute(
                "ALTER TABLE po_downloads ADD COLUMN attachment_count INTEGER DEFAULT 0"
            )
        if "output_subdir" not in existing:
            cursor.execute(
                "ALTER TABLE po_downloads ADD COLUMN output_subdir TEXT"
            )

    def create_session(self, input_file: str, execution_type: str = "PROD") -> int:
        normalized_type = (execution_type or "PROD").strip().upper()
        if normalized_type not in {"PROD", "TEST"}:
            normalized_type = "PROD"

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO sessions (input_file, execution_type, status)
            VALUES (?, ?, 'PENDING')
        ''', (input_file, normalized_type))
        self.conn.commit()
        return cursor.lastrowid

    def archive_session_input(self, session_id: int, source_path: str, archive_path: str) -> str:
        source = Path(source_path).expanduser().resolve()
        archive = Path(archive_path).expanduser().resolve()
        data = source.read_bytes()
        archive.parent.mkdir(parents=True, exist_ok=True)
        if source != archive:
            shutil.copy2(source, archive)
        digest = hashlib.sha256(data).hexdigest()
        self.conn.execute(
            """
            UPDATE sessions
            SET input_file = ?, input_file_path = ?, input_file_blob = ?,
                input_file_sha256 = ?, input_file_size = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (source.name, str(archive), data, digest, len(data), session_id),
        )
        self.conn.commit()
        return str(archive)

    def clone_session_input(self, source_session_id: int, target_session_id: int, archive_path: str) -> Optional[str]:
        row = self.conn.execute(
            "SELECT input_file, input_file_path, input_file_blob, input_file_sha256, input_file_size FROM sessions WHERE id = ?",
            (source_session_id,),
        ).fetchone()
        if not row:
            return None
        source_path = Path(row["input_file_path"]) if row["input_file_path"] else None
        data = row["input_file_blob"]
        if data is None and source_path and source_path.exists():
            data = source_path.read_bytes()
        if data is None:
            return None
        archive = Path(archive_path).expanduser().resolve()
        archive.parent.mkdir(parents=True, exist_ok=True)
        archive.write_bytes(data)
        digest = row["input_file_sha256"] or hashlib.sha256(data).hexdigest()
        self.conn.execute(
            """
            UPDATE sessions
            SET input_file = ?, input_file_path = ?, input_file_blob = ?,
                input_file_sha256 = ?, input_file_size = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (row["input_file"] or archive.name, str(archive), data, digest, len(data), target_session_id),
        )
        self.conn.commit()
        return str(archive)

    def get_session_execution_type(self, session_id: int) -> str:
        session = self.get_session(session_id)
        if not session:
            return "PROD"
        value = str(session.get("execution_type") or "PROD").strip().upper()
        return value if value in {"PROD", "TEST"} else "PROD"

    def get_session(self, session_id: int) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM sessions WHERE id = ?', (session_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def add_po(self, po: PODownload):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO po_downloads (session_id, po_number, company_code, output_subdir, status, download_folder, attachment_count, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            po.session_id,
            po.po_number,
            po.company_code,
            po.output_subdir,
            po.status,
            po.download_folder,
            po.attachment_count or 0,
            po.error_message,
        ))
        self.conn.commit()

    def update_po_status(self, session_id: int, po_number: str, status: str, download_folder: Optional[str] = None, attachment_count: Optional[int] = None, error_message: Optional[str] = None):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE po_downloads
            SET status = ?, download_folder = COALESCE(?, download_folder),
                attachment_count = COALESCE(?, attachment_count),
                error_message = ?, updated_at = strftime('%Y-%m-%d %H:%M:%f', 'now')
            WHERE session_id = ? AND po_number = ?
        ''', (status, download_folder, attachment_count, error_message, session_id, po_number))
        self.conn.commit()

    def get_po(self, session_id: int, po_number: str) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM po_downloads WHERE session_id = ? AND po_number = ?', (session_id, po_number))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_company_stats(self, session_id: int, company_code: str) -> Dict[str, int]:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status != 'PENDING' THEN 1 ELSE 0 END) as processed,
                SUM(CASE WHEN status = 'ERROR' THEN 1 ELSE 0 END) as errors,
                SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as success
            FROM po_downloads 
            WHERE session_id = ? AND company_code = ?
        ''', (session_id, company_code))
        
        row = cursor.fetchone()
        return {
            'total': row['total'] or 0,
            'processed': row['processed'] or 0,
            'errors': row['errors'] or 0,
            'success': row['success'] or 0
        }
        
    def suspend_company_code(self, session_id: int, company_code: str):
        """Marks pending POs of a company code as SKIPPED_VERIFICATION_REQUIRED"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE po_downloads 
            SET status = 'SKIPPED_VERIFICATION_REQUIRED', updated_at = strftime('%Y-%m-%d %H:%M:%f', 'now')
            WHERE session_id = ? AND company_code = ? AND status = 'PENDING'
        ''', (session_id, company_code))
        self.conn.commit()

    def close(self):
        self.conn.close()
