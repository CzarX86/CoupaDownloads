from typing import Optional, Dict, Any, List
from pathlib import Path
import pandas as pd
import os
from datetime import datetime

from .core.csv_handler import CSVHandler, WriteQueue
from .core.sqlite_handler import SQLiteHandler


class CSVManager:
    """Manager for persistence operations, supporting both CSV and SQLite."""

    def __init__(self):
        self._csv_handler: Optional[CSVHandler] = None
        self._csv_write_queue: Optional[WriteQueue] = None
        self._csv_session_id: Optional[str] = None
        self._sqlite_handler: Optional[SQLiteHandler] = None
        self._sqlite_db_path: Optional[str] = None

    @property
    def csv_handler(self) -> Optional[CSVHandler]:
        """Get the CSV handler instance."""
        return self._csv_handler

    @csv_handler.setter
    def csv_handler(self, value: Optional[CSVHandler]) -> None:
        """Set the CSV handler instance."""
        self._csv_handler = value

    @property
    def sqlite_handler(self) -> Optional[SQLiteHandler]:
        """Get the SQLite handler instance."""
        return self._sqlite_handler

    @property
    def sqlite_db_path(self) -> Optional[str]:
        """Get the SQLite database path."""
        return self._sqlite_db_path

    def initialize_csv_handler(self, csv_input_path: Path) -> Optional[str]:
        """Initialize CSV handler if input is CSV."""
        if csv_input_path.suffix.lower() == '.csv' and not self.csv_handler:
            try:
                # 1. Prepare SQLite session DB path
                session_id = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_dir = csv_input_path.parent / "backups"
                backup_dir.mkdir(parents=True, exist_ok=True)
                db_path = backup_dir / f"session_{session_id}.db"
                self._sqlite_db_path = str(db_path)

                # 2. Initialize Handler (which now handles its own SQLite sub-handler)
                self.csv_handler, self._csv_write_queue, self._csv_session_id = CSVHandler.create_handler(
                    csv_input_path, 
                    enable_incremental_updates=True,
                    sqlite_db_path=self._sqlite_db_path
                )
                
                # 3. Store reference to the sqlite_handler for main-process operations (like seeding)
                self._sqlite_handler = self.csv_handler.sqlite_handler
                
                print(f"🛡️ CSV backup created at: {CSVHandler.get_backup_path(csv_input_path)}")
                print(f"🚀 SQLite persistence enabled: {self._sqlite_db_path}")
                
                return self._csv_session_id
            except Exception as e:
                print(f"⚠️ Failed to initialize CSV/SQLite handler: {e}")
                import traceback
                traceback.print_exc()
                return None
        return None

    def initialize_sqlite_handler(self, db_path: str):
        """Initialize SQLite handler."""
        self._sqlite_db_path = db_path
        self._sqlite_handler = SQLiteHandler(db_path)

    def seed_sqlite(self, df: pd.DataFrame):
        """Seed SQLite with initial data."""
        if self._sqlite_handler:
            self._sqlite_handler.seed_from_dataframe(df)

    def shutdown_csv_handler(self):
        """Shutdown handlers and export SQLite data back to CSV."""
        db_path_to_clean = self._sqlite_db_path
        
        if self._sqlite_handler and self.csv_handler:
            self._export_sqlite_to_file()

        if self._csv_write_queue:
            self._csv_write_queue.stop_writer_thread(timeout=15.0)
            self._csv_write_queue = None
        
        # Close SQLite handler if it has a close method (it currently doesn't do much, but good practice)
        if self._sqlite_handler:
            self._sqlite_handler.close()
            
        self.csv_handler = None
        self._sqlite_handler = None
        self._sqlite_db_path = None
        
        # Cleanup temporary SQLite files
        if db_path_to_clean and os.path.exists(db_path_to_clean):
            try:
                # Give a small buffer for OS to release file handles if needed
                import time
                time.sleep(0.5)
                
                os.remove(db_path_to_clean)
                print(f"🧹 Cleaned up temporary SQLite session: {os.path.basename(db_path_to_clean)}")
                
                # Also cleanup sidecar files if they exist (WAL mode)
                for suffix in ['-wal', '-shm']:
                    sidecar = f"{db_path_to_clean}{suffix}"
                    if os.path.exists(sidecar):
                        os.remove(sidecar)
            except Exception as e:
                print(f"⚠️ Failed to cleanup temporary SQLite files: {e}")

    def _export_sqlite_to_file(self):
        """Internal helper to export SQLite results back to CSV/Excel."""
        if not self._sqlite_handler or not self.csv_handler:
            return

        try:
            results_df = self._sqlite_handler.get_all_results_df()
            if results_df.empty:
                print("ℹ️ No results in SQLite to export.")
                return

            if not hasattr(self.csv_handler, 'csv_path') or not self.csv_handler.csv_path:
                print("⚠️ CSV handler has no path for export.")
                return

            file_path = self.csv_handler.csv_path
            if not file_path.exists():
                print(f"⚠️ File path {file_path} does not exist for export.")
                return

            print(f"💾 Merging {len(results_df)} records from SQLite back to {file_path.name}...")
            
            # Read original file using ExcelProcessor logic to maintain compatibility
            from .lib.excel_processor import ExcelProcessor
            processor = ExcelProcessor()
            _, ext = os.path.splitext(str(file_path).lower())
            
            # We need to know the original structure to merge correctly
            if ext == '.csv':
                df, sep, enc = processor._read_csv_auto(str(file_path))
            else:
                # Excel: read specific sheet
                xl = pd.ExcelFile(file_path)
                sheet_name = 'PO_Data' if 'PO_Data' in xl.sheet_names else xl.sheet_names[0]
                df = pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')

            # Find the actual PO_NUMBER column
            po_col = processor._find_column(df, 'PO_NUMBER')
            if not po_col:
                print("❌ Could not find PO_NUMBER column in the original file. Export aborted.")
                return

            # Clean keys for matching
            df[po_col] = df[po_col].astype(str).str.strip()
            results_df['po_number'] = results_df['po_number'].astype(str).str.strip()
            
            # Only update records that were actually processed (not PENDING)
            to_update = results_df[results_df['STATUS'] != 'PENDING'].copy()
            
            if not to_update.empty:
                print(f"   📝 Updating {len(to_update)} processed records...")
                df.set_index(po_col, inplace=True)
                to_update.set_index('po_number', inplace=True)
                
                # Columns to sync back
                sync_map = {
                    'STATUS': 'STATUS',
                    'SUPPLIER': 'SUPPLIER',
                    'ATTACHMENTS_FOUND': 'ATTACHMENTS_FOUND',
                    'ATTACHMENTS_DOWNLOADED': 'ATTACHMENTS_DOWNLOADED',
                    'AttachmentName': 'AttachmentName',
                    'LAST_PROCESSED': 'LAST_PROCESSED',
                    'ERROR_MESSAGE': 'ERROR_MESSAGE',
                    'DOWNLOAD_FOLDER': 'DOWNLOAD_FOLDER',
                    'COUPA_URL': 'COUPA_URL'
                }
                
                for sqlite_col, standard_name in sync_map.items():
                    target_col = processor._find_column(df, standard_name)
                    if target_col and sqlite_col in to_update.columns:
                        # Ensure we don't overwrite with empty values if SQLite has better data
                        # but SQLite should have the most recent data
                        df.update(to_update[[sqlite_col]].rename(columns={sqlite_col: target_col}))
                
                df.reset_index(inplace=True)
                
                # Save back to disk
                if ext == '.csv':
                    df.to_csv(file_path, index=False, sep=sep, encoding=enc)
                else:
                    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                print(f"✅ Final export completed successfully to {file_path}")
            else:
                print("ℹ️ No processed records to export (all still PENDING).")
                
        except Exception as e:
            print(f"❌ Export failed: {e}")
            import traceback
            traceback.print_exc()

    def update_record(self, po_number: str, updates: Dict[str, Any]) -> bool:
        """Update a record (prefer SQLite if available)."""
        success = False
        if self._sqlite_handler:
            success = self._sqlite_handler.update_record(po_number, updates)
        
        # Fallback to CSV if SQLite is not used or purely for incremental safety
        if self.csv_handler:
            success = self.csv_handler.update_record(po_number, updates) or success
            
        return success

    def is_initialized(self) -> bool:
        """Check if any persistence handler is initialized."""
        return self.csv_handler is not None or self._sqlite_handler is not None