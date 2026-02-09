"""
SQLite Handler for CoupaDownloads.

Provides a high-performance, concurrent-safe persistence layer using SQLite.
Replaces synchronous CSV full-file rewrites to eliminate lock contention bottlenecks.
"""

import sqlite3
import os
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import logging

class SQLiteHandler:
    """
    Handles persistence of PO processing state in a SQLite database.
    Supports concurrent updates from multiple worker processes using WAL mode.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._initialize_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a connection with WAL mode and proper timeout for concurrency."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _initialize_database(self):
        """Creates the schema if it doesn't exist, with retries for concurrency."""
        import time
        max_retries = 5
        for attempt in range(max_retries):
            try:
                with self._get_connection() as conn:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS po_tasks (
                            po_number TEXT PRIMARY KEY,
                            STATUS TEXT DEFAULT 'PENDING',
                            SUPPLIER TEXT DEFAULT '',
                            ATTACHMENTS_FOUND INTEGER DEFAULT 0,
                            ATTACHMENTS_DOWNLOADED INTEGER DEFAULT 0,
                            AttachmentName TEXT DEFAULT '',
                            LAST_PROCESSED TEXT DEFAULT '',
                            ERROR_MESSAGE TEXT DEFAULT '',
                            DOWNLOAD_FOLDER TEXT DEFAULT '',
                            COUPA_URL TEXT DEFAULT ''
                        )
                    """)
                    # Create an index on status for faster reporting
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON po_tasks(STATUS)")
                    conn.commit()
                self.logger.debug(f"💾 SQLite database initialized at {self.db_path}")
                return # Success
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))
                    continue
                self.logger.error(f"❌ Failed to initialize SQLite database: {e}")
                raise
            except Exception as e:
                self.logger.error(f"❌ Failed to initialize SQLite database: {e}")
                raise

    def seed_from_dataframe(self, df: pd.DataFrame, po_col: str = 'PO_NUMBER'):
        """
        Populate the database with initial PO numbers from the input file.
        Existing records remain untouched.
        """
        # Find the column case-insensitively
        actual_col = None
        for col in df.columns:
            if str(col).strip().upper() == po_col.upper():
                actual_col = col
                break
        
        if actual_col is None:
            self.logger.warning(f"Column {po_col} not found in dataframe columns: {list(df.columns)}. Seeding aborted.")
            return

        po_list = df[actual_col].astype(str).str.strip().tolist()
        
        try:
            with self._get_connection() as conn:
                # Use INSERT OR IGNORE to avoid duplicates if re-seeding
                conn.executemany(
                    "INSERT OR IGNORE INTO po_tasks (po_number) VALUES (?)",
                    [(po,) for po in po_list if po]
                )
                conn.commit()
            self.logger.debug(f"🌱 Seeded {len(po_list)} POs into SQLite")
        except Exception as e:
            self.logger.error(f"❌ Failed to seed SQLite: {e}")

    def update_record(self, po_number: str, updates: Dict[str, Any]) -> bool:
        """
        Update a record in the database.
        Args:
            po_number: The PO number (key)
            updates: Dictionary of column names and values
        """
        if not updates:
            return True

        # Map keys to match schema columns if necessary
        # This preserves compatibility with the previous CSVHandler/ExcelProcessor API
        column_map = {
            'STATUS': 'STATUS',
            'SUPPLIER': 'SUPPLIER',
            'ATTACHMENTS_FOUND': 'ATTACHMENTS_FOUND',
            'ATTACHMENTS_DOWNLOADED': 'ATTACHMENTS_DOWNLOADED',
            'AttachmentName': 'AttachmentName',
            'ERROR_MESSAGE': 'ERROR_MESSAGE',
            'DOWNLOAD_FOLDER': 'DOWNLOAD_FOLDER',
            'COUPA_URL': 'COUPA_URL'
        }

        sql_parts = []
        params = []
        
        for key, value in updates.items():
            col = column_map.get(key)
            if col:
                sql_parts.append(f"{col} = ?")
                params.append(value)

        # Always update LAST_PROCESSED
        sql_parts.append("LAST_PROCESSED = ?")
        params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        params.append(str(po_number).strip())
        
        query = f"UPDATE po_tasks SET {', '.join(sql_parts)} WHERE po_number = ?"

        try:
            with self._get_connection() as conn:
                cursor = conn.execute(query, params)
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"❌ SQLite update failed for {po_number}: {e}")
            return False

    def get_all_results_df(self) -> pd.DataFrame:
        """Retrieve all results as a pandas DataFrame for final export."""
        try:
            with self._get_connection() as conn:
                return pd.read_sql_query("SELECT * FROM po_tasks", conn)
        except Exception as e:
            self.logger.error(f"❌ Failed to retrieve results from SQLite: {e}")
            return pd.DataFrame()

    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics."""
        try:
            with self._get_connection() as conn:
                res = conn.execute("SELECT STATUS, COUNT(*) as count FROM po_tasks GROUP BY STATUS").fetchall()
                return {row['STATUS']: row['count'] for row in res}
        except Exception as e:
            self.logger.error(f"❌ Failed to get SQLite stats: {e}")
            return {}

    def close(self):
        """Perform any final cleanup if needed."""
        # SQLite connections are context-managed here, so no persistent conn to close
        pass
