import sqlite3
import datetime
from dataclasses import dataclass
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
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id),
                UNIQUE(session_id, po_number)
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

        existing = {row[1] for row in cursor.execute("PRAGMA table_info(po_downloads)")}

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
                error_message = ?, updated_at = CURRENT_TIMESTAMP
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
            SET status = 'SKIPPED_VERIFICATION_REQUIRED', updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ? AND company_code = ? AND status = 'PENDING'
        ''', (session_id, company_code))
        self.conn.commit()

    def close(self):
        self.conn.close()
