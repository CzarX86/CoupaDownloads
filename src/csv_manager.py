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
        self._input_csv_path: Optional[Path] = None
        self._output_copy_path: Optional[Path] = None

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
                from .lib.config import Config
                # 1. Prepare SQLite session DB path
                session_id = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_dir = csv_input_path.parent / "backups"
                backup_dir.mkdir(parents=True, exist_ok=True)
                db_path = backup_dir / f"session_{session_id}.db"
                self._sqlite_db_path = str(db_path)
                self._input_csv_path = csv_input_path
                self._output_copy_path = self._build_output_copy_path(csv_input_path)

                # 2. Initialize Handler (which now handles its own SQLite sub-handler)
                self.csv_handler, self._csv_write_queue, self._csv_session_id = CSVHandler.create_handler(
                    csv_input_path, 
                    enable_incremental_updates=True,
                    enable_legacy_updates=not getattr(Config, "SQLITE_ONLY_PERSISTENCE", True),
                    sqlite_db_path=self._sqlite_db_path
                )
                
                # 3. Store reference to the sqlite_handler for main-process operations (like seeding)
                self._sqlite_handler = self.csv_handler.sqlite_handler
                
                print(f"🛡️ CSV backup created at: {CSVHandler.get_backup_path(csv_input_path)}")
                print(f"🚀 SQLite persistence enabled: {self._sqlite_db_path}")
                if getattr(Config, "SQLITE_ONLY_PERSISTENCE", True):
                    print("🧠 SQLite-only persistence enabled: CSV will be updated only after completion.")
                if self._output_copy_path:
                    print(f"🧾 Output copy will be generated at: {self._output_copy_path}")
                
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

    def _build_output_copy_path(self, input_path: Path) -> Path:
        """Build output copy path for final export, keeping input file untouched."""
        from .lib.config import Config
        suffix = getattr(Config, "CSV_OUTPUT_SUFFIX", "_processed")
        include_ts = bool(getattr(Config, "CSV_OUTPUT_INCLUDE_TIMESTAMP", True))
        output_dir = getattr(Config, "CSV_OUTPUT_DIR", None)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S") if include_ts else ""
        ts_part = f"_{timestamp}" if timestamp else ""
        out_dir = Path(output_dir).expanduser() if output_dir else input_path.parent
        filename = f"{input_path.stem}{suffix}{ts_part}{input_path.suffix}"
        return out_dir / filename

    def seed_sqlite(self, df: pd.DataFrame):
        """Seed SQLite with initial data."""
        if self._sqlite_handler:
            self._sqlite_handler.seed_from_dataframe(df)

    def shutdown_csv_handler(self, cleanup_sqlite: bool = True):
        """Shutdown handlers. Does NOT auto-export to CSV anymore.
        
        The final report is now generated on-demand via ``generate_final_report``.
        
        Args:
            cleanup_sqlite: If True (default), close and remove the temporary
                SQLite files. Set to False if the caller still needs the data
                (e.g. to generate the final report).
        """
        db_path_to_clean = self._sqlite_db_path

        if self._csv_write_queue:
            self._csv_write_queue.stop_writer_thread(timeout=15.0)
            self._csv_write_queue = None

        if cleanup_sqlite:
            # Close SQLite handler
            if self._sqlite_handler:
                self._sqlite_handler.close()

            self.csv_handler = None
            self._sqlite_handler = None
            self._sqlite_db_path = None

            # Cleanup temporary SQLite files
            if db_path_to_clean and os.path.exists(db_path_to_clean):
                try:
                    import time
                    time.sleep(0.5)

                    os.remove(db_path_to_clean)
                    print(f"🧹 Cleaned up temporary SQLite session: {os.path.basename(db_path_to_clean)}")

                    for suffix in ['-wal', '-shm']:
                        sidecar = f"{db_path_to_clean}{suffix}"
                        if os.path.exists(sidecar):
                            os.remove(sidecar)
                except Exception as e:
                    print(f"⚠️ Failed to cleanup temporary SQLite files: {e}")

    def generate_final_report(self, download_root: Optional[Path] = None) -> Optional[Path]:
        """Generate a final Excel report with processing results.

        Merges the SQLite data with the original input file and saves an
        ``.xlsx`` report to *download_root* (the timestamped directory where
        attachments were saved during this run).

        Args:
            download_root: Directory where the report will be saved.
                Falls back to the input file's directory if not provided.

        Returns:
            Path to the generated report, or ``None`` on failure.
        """
        if not self._sqlite_handler:
            print("⚠️ No SQLite data available to generate report.")
            return None

        try:
            results_df = self._sqlite_handler.get_all_results_df()
            if results_df.empty:
                print("ℹ️ No results to include in the report.")
                return None

            # Determine input path for reading the original structure
            input_path: Optional[Path] = None
            if self.csv_handler and hasattr(self.csv_handler, 'csv_path'):
                input_path = self.csv_handler.csv_path
            elif self._input_csv_path:
                input_path = self._input_csv_path

            if not input_path or not input_path.exists():
                print("⚠️ Original input file not found. Generating standalone report.")
                return self._generate_standalone_report(results_df, download_root)

            # Determine output directory and filename
            report_dir = download_root or input_path.parent
            report_dir = Path(report_dir)
            report_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            report_name = f"CoupaDownloads_Report_{timestamp}.xlsx"
            report_path = report_dir / report_name

            # Read original input file
            from .lib.excel_processor import ExcelProcessor
            processor = ExcelProcessor()
            _, ext = os.path.splitext(str(input_path).lower())

            if ext == '.csv':
                df, _sep, _enc = processor._read_csv_auto(str(input_path))
            else:
                xl = pd.ExcelFile(input_path)
                sheet_name = 'PO_Data' if 'PO_Data' in xl.sheet_names else xl.sheet_names[0]
                df = pd.read_excel(input_path, sheet_name=sheet_name, engine='openpyxl')

            po_col = processor._find_column(df, 'PO_NUMBER')
            if not po_col:
                print("❌ Could not find PO_NUMBER column. Generating standalone report.")
                return self._generate_standalone_report(results_df, download_root)

            # Clean keys for matching
            df[po_col] = df[po_col].astype(str).str.strip()
            results_df['po_number'] = results_df['po_number'].astype(str).str.strip()

            # Convert all columns to object dtype to avoid StringDtype assignment
            # errors when mixing str/int values during the merge.
            df = df.astype(object)

            to_update = results_df[results_df['STATUS'] != 'PENDING'].copy()

            if not to_update.empty:
                print(f"   📝 Merging {len(to_update)} processed records into report...")
                df.set_index(po_col, inplace=True)
                to_update.set_index('po_number', inplace=True)

                sync_map = {
                    'STATUS': 'STATUS',
                    'SUPPLIER': 'SUPPLIER',
                    'ATTACHMENTS_FOUND': 'ATTACHMENTS_FOUND',
                    'ATTACHMENTS_DOWNLOADED': 'ATTACHMENTS_DOWNLOADED',
                    'AttachmentName': 'AttachmentName',
                    'LAST_PROCESSED': 'LAST_PROCESSED',
                    'ERROR_MESSAGE': 'ERROR_MESSAGE',
                    'DOWNLOAD_FOLDER': 'DOWNLOAD_FOLDER',
                    'COUPA_URL': 'COUPA_URL',
                }

                for sqlite_col, standard_name in sync_map.items():
                    target_col = processor._find_column(df, standard_name)
                    if target_col and sqlite_col in to_update.columns:
                        source_data = to_update[sqlite_col].copy()

                        if target_col in [
                            'STATUS', 'SUPPLIER', 'AttachmentName',
                            'ERROR_MESSAGE', 'DOWNLOAD_FOLDER', 'COUPA_URL',
                            'LAST_PROCESSED',
                        ]:
                            source_data = source_data.fillna('').astype(str)
                        elif target_col in ['ATTACHMENTS_FOUND', 'ATTACHMENTS_DOWNLOADED']:
                            source_data = pd.to_numeric(source_data, errors='coerce').fillna(0).astype(int)

                        chunk = source_data[~source_data.index.duplicated(keep='first')]
                        df.loc[df.index.isin(chunk.index), target_col] = chunk

                df.reset_index(inplace=True)

            # Always save as .xlsx for the report
            with pd.ExcelWriter(report_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Report', index=False)

            print(f"✅ Final report saved to: {report_path}")
            return report_path

        except Exception as e:
            print(f"❌ Report generation failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _generate_standalone_report(self, results_df: pd.DataFrame, download_root: Optional[Path] = None) -> Optional[Path]:
        """Fallback: generate report purely from SQLite data without merging."""
        try:
            report_dir = Path(download_root) if download_root else Path.cwd()
            report_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            report_path = report_dir / f"CoupaDownloads_Report_{timestamp}.xlsx"

            to_export = results_df[results_df['STATUS'] != 'PENDING'].copy()
            if to_export.empty:
                print("ℹ️ No processed records to export.")
                return None

            with pd.ExcelWriter(report_path, engine='openpyxl') as writer:
                to_export.to_excel(writer, sheet_name='Report', index=False)

            print(f"✅ Standalone report saved to: {report_path}")
            return report_path
        except Exception as e:
            print(f"❌ Standalone report generation failed: {e}")
            return None

    def has_results(self) -> bool:
        """Check if there are any processed results available for a report."""
        if not self._sqlite_handler:
            return False
        try:
            results_df = self._sqlite_handler.get_all_results_df()
            if results_df.empty:
                return False
            return bool((results_df['STATUS'] != 'PENDING').any())
        except Exception:
            return False

    def update_record(self, po_number: str, updates: Dict[str, Any]) -> bool:
        """Update a record in SQLite only (no CSV write-back during processing)."""
        if self._sqlite_handler:
            return self._sqlite_handler.update_record(po_number, updates)
        return False

    def is_initialized(self) -> bool:
        """Check if any persistence handler is initialized."""
        return self.csv_handler is not None or self._sqlite_handler is not None
