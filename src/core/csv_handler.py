from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, ClassVar
from datetime import datetime
import logging
import os

# Import the working ExcelProcessor
try:
    from ..lib.excel_processor import ExcelProcessor
    EXCEL_PROCESSOR_AVAILABLE = True
except ImportError:
    EXCEL_PROCESSOR_AVAILABLE = False
    ExcelProcessor = None
    logging.warning("ExcelProcessor not available, CSV updates will be disabled")

# Import SQLiteHandler
try:
    from .sqlite_handler import SQLiteHandler
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False
    SQLiteHandler = None


class WriteQueue:
    """Stub WriteQueue implementation."""
    
    def __init__(self, csv_handler):
        self.csv_handler = csv_handler
    
    def start_writer_thread(self):
        pass
    
    def stop_writer_thread(self, timeout=15.0):
        pass


class CSVHandler:
    """CSV Handler implementation using ExcelProcessor (Legacy) or SQLite (New)."""

    _last_backup_path: ClassVar[Optional[Path]] = None

    def __init__(self, csv_path: Path, backup_dir: Optional[Path] = None, sqlite_db_path: Optional[str] = None):
        self.csv_path = csv_path
        self.backup_dir = backup_dir or (csv_path.parent / "backups")
        self.sqlite_db_path = sqlite_db_path
        self.logger = logging.getLogger(__name__)
        
        # Initialize SQLite handler if path provided
        self.sqlite_handler = None
        if sqlite_db_path and SQLITE_AVAILABLE:
            try:
                self.sqlite_handler = SQLiteHandler(sqlite_db_path)
                self.logger.debug(f"🚀 SQLite persistence enabled for CSVHandler: {sqlite_db_path}")
            except Exception as e:
                self.logger.error(f"⚠️ Failed to initialize SQLite in CSVHandler: {e}")

        if not EXCEL_PROCESSOR_AVAILABLE and not self.sqlite_handler:
            self.logger.error("No persistence engine available (ExcelProcessor and SQLite failed)")

    def is_initialized(self) -> bool:
        """Check if any persistence engine is initialized."""
        return (EXCEL_PROCESSOR_AVAILABLE and ExcelProcessor is not None) or self.sqlite_handler is not None

    @classmethod
    def create_handler(
        cls,
        csv_path: Path,
        enable_incremental_updates: bool = True,
        backup_dir: Optional[Path] = None,
        sqlite_db_path: Optional[str] = None
    ) -> Tuple["CSVHandler", "WriteQueue", str]:
        """Factory helper to match CSVManager expectations."""
        handler = cls(csv_path, backup_dir=backup_dir, sqlite_db_path=sqlite_db_path)
        session_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        if enable_incremental_updates:
            try:
                # Session backup is still useful as a 'original state' snapshot
                backup_path = handler.create_session_backup(session_id)
                cls._last_backup_path = backup_path
            except Exception:
                cls._last_backup_path = None
        write_queue = WriteQueue(handler)
        return handler, write_queue, session_id

    @staticmethod
    def get_backup_path(csv_path: Path, backup_dir: Optional[Path] = None) -> Path:
        """Return the most recent backup path when available."""
        if CSVHandler._last_backup_path:
            return CSVHandler._last_backup_path
        backup_root = backup_dir or (csv_path.parent / "backups")
        backup_root.mkdir(parents=True, exist_ok=True)
        session_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        return backup_root / f"backup_{session_id}.csv"
    
    def create_session_backup(self, session_id: str) -> Path:
        """Create a backup - stub implementation."""
        if self.backup_dir:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = self.backup_dir / f"backup_{session_id}.csv"
            if self.csv_path.exists():
                import shutil
                shutil.copy2(self.csv_path, backup_path)
                return backup_path
        return self.csv_path
    
    def update_record(self, po_number: str, updates: Dict[str, Any]) -> bool:
        """Update a record (prefers SQLite, falls back to ExcelProcessor)."""
        success = False
        
        # 1. High Performance: SQLite
        if self.sqlite_handler:
            try:
                success = self.sqlite_handler.update_record(po_number, updates)
                if success:
                    self.logger.debug(f"Successfully updated SQLite record for PO: {po_number}")
                    # If SQLite succeeded, we might NOT want to call ExcelProcessor (the bottleneck)
                    # during the parallel phase.
                    return True
            except Exception as e:
                self.logger.error(f"SQLite update failed for {po_number}: {e}")

        # 2. Legacy / Low Performance: ExcelProcessor
        if EXCEL_PROCESSOR_AVAILABLE and ExcelProcessor is not None:
            try:
                self.logger.debug(f"Updating Legacy CSV record for PO: {po_number}")
                
                status = updates.get('STATUS', 'FAILED')
                supplier = updates.get('SUPPLIER', '')
                attachments_found = updates.get('ATTACHMENTS_FOUND', 0)
                attachments_downloaded = updates.get('ATTACHMENTS_DOWNLOADED', 0)
                error_message = updates.get('ERROR_MESSAGE', '')
                download_folder = updates.get('DOWNLOAD_FOLDER', '')
                coupa_url = updates.get('COUPA_URL', '')
                
                attachment_names = updates.get('AttachmentName', [])
                if isinstance(attachment_names, list):
                    attachment_names = ', '.join(str(name) for name in attachment_names if name)
                
                ExcelProcessor.update_po_status(
                    po_number=po_number,
                    status=status,
                    supplier=supplier,
                    attachments_found=attachments_found,
                    attachments_downloaded=attachments_downloaded,
                    error_message=error_message,
                    download_folder=download_folder,
                    coupa_url=coupa_url,
                    attachment_names=attachment_names
                )
                success = True
                self.logger.debug(f"Successfully updated Legacy CSV for PO: {po_number}")
            except Exception as e:
                self.logger.error(f"Legacy CSV update failed for PO {po_number}: {e}")
        
        return success
