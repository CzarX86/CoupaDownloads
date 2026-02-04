"""
Stub CSV Handler for experimental CoupaDownloads.

This is a temporary implementation until the full CSVHandler is implemented.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, ClassVar
from datetime import datetime
import logging

# Import the working ExcelProcessor
try:
    from ..lib.excel_processor import ExcelProcessor
    EXCEL_PROCESSOR_AVAILABLE = True
except ImportError:
    EXCEL_PROCESSOR_AVAILABLE = False
    ExcelProcessor = None  # Define it as None for type checking
    logging.warning("ExcelProcessor not available, CSV updates will be disabled")


class WriteQueue:
    """Stub WriteQueue implementation."""
    
    def __init__(self, csv_handler):
        self.csv_handler = csv_handler
    
    def start_writer_thread(self):
        pass
    
    def stop_writer_thread(self, timeout=15.0):
        pass


class CSVHandler:
    """CSV Handler implementation using ExcelProcessor."""

    _last_backup_path: ClassVar[Optional[Path]] = None

    def __init__(self, csv_path: Path, backup_dir: Optional[Path] = None):
        self.csv_path = csv_path
        self.backup_dir = backup_dir or (csv_path.parent / "backups")
        self.logger = logging.getLogger(__name__)
        
        if not EXCEL_PROCESSOR_AVAILABLE:
            self.logger.error("ExcelProcessor not available - CSV updates disabled")

    @classmethod
    def create_handler(
        cls,
        csv_path: Path,
        enable_incremental_updates: bool = True,
        backup_dir: Optional[Path] = None,
    ) -> Tuple["CSVHandler", "WriteQueue", str]:
        """Factory helper to match CSVManager expectations."""
        handler = cls(csv_path, backup_dir=backup_dir)
        session_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        if enable_incremental_updates:
            try:
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
            # Copy the file if it exists
            if self.csv_path.exists():
                import shutil
                shutil.copy2(self.csv_path, backup_path)
                return backup_path
        return self.csv_path
    
    def update_record(self, po_number: str, updates: Dict[str, Any]) -> bool:
        """Update a record using ExcelProcessor.update_po_status."""
        if not EXCEL_PROCESSOR_AVAILABLE:
            self.logger.warning(f"ExcelProcessor not available - skipping CSV update for PO {po_number}")
            return False
            
        try:
            self.logger.debug(f"Updating CSV record for PO: {po_number}, updates: {updates}")
            
            # Extract the fields that ExcelProcessor.update_po_status expects
            status = updates.get('STATUS', 'FAILED')
            supplier = updates.get('SUPPLIER', '')
            attachments_found = updates.get('ATTACHMENTS_FOUND', 0)
            attachments_downloaded = updates.get('ATTACHMENTS_DOWNLOADED', 0)
            error_message = updates.get('ERROR_MESSAGE', '')
            download_folder = updates.get('DOWNLOAD_FOLDER', '')
            coupa_url = updates.get('COUPA_URL', '')
            
            # Handle attachment names - can be string or list
            attachment_names = updates.get('AttachmentName', [])
            if isinstance(attachment_names, list):
                attachment_names = ', '.join(str(name) for name in attachment_names if name)
            
            # Call the working ExcelProcessor.update_po_status
            if EXCEL_PROCESSOR_AVAILABLE and ExcelProcessor is not None:
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
            
            self.logger.debug(f"Successfully updated CSV record for PO: {po_number}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update CSV record for PO {po_number}: {e}")
            return False
