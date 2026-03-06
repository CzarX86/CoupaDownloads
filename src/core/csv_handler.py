from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Dict, Any, Optional, Tuple, ClassVar
from datetime import datetime
import logging

try:
    from .sqlite_handler import SQLiteHandler
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False
    SQLiteHandler = None

if TYPE_CHECKING:
    from .sqlite_handler import SQLiteHandler as SQLiteHandlerType


class WriteQueue:
    """Stub WriteQueue implementation."""

    def __init__(self, csv_handler: Any) -> None:
        self.csv_handler = csv_handler

    def start_writer_thread(self) -> None:
        pass

    def stop_writer_thread(self, timeout: float = 15.0) -> None:
        pass


class CSVHandler:
    """CSV handler implementation backed by SQLite persistence."""

    _last_backup_path: ClassVar[Optional[Path]] = None

    def __init__(
        self,
        csv_path: Path,
        backup_dir: Optional[Path] = None,
        sqlite_db_path: Optional[str] = None,
    ):
        self.csv_path = csv_path
        self.backup_dir = backup_dir or (csv_path.parent / "backups")
        self.sqlite_db_path = sqlite_db_path
        self.logger = logging.getLogger(__name__)
        
        self.sqlite_handler = None
        if sqlite_db_path and SQLITE_AVAILABLE:
            try:
                self.sqlite_handler = SQLiteHandler(sqlite_db_path)
                self.logger.debug(f"🚀 SQLite persistence enabled for CSVHandler: {sqlite_db_path}")
            except Exception as e:
                self.logger.error(f"⚠️ Failed to initialize SQLite in CSVHandler: {e}")

        if not self.sqlite_handler:
            self.logger.error("No persistence engine available (SQLite disabled or failed)")

    def is_initialized(self) -> bool:
        """Check if SQLite persistence is initialized."""
        return self.sqlite_handler is not None

    @classmethod
    def create_handler(
        cls,
        csv_path: Path,
        enable_incremental_updates: bool = True,
        backup_dir: Optional[Path] = None,
        sqlite_db_path: Optional[str] = None,
    ) -> Tuple["CSVHandler", "WriteQueue", str]:
        """Factory helper to match CSVManager expectations."""
        handler = cls(
            csv_path,
            backup_dir=backup_dir,
            sqlite_db_path=sqlite_db_path,
        )
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
        """Update a record in SQLite persistence."""
        if self.sqlite_handler:
            try:
                if self.sqlite_handler.update_record(po_number, updates):
                    self.logger.debug(f"Successfully updated SQLite record for PO: {po_number}")
                    return True
            except Exception as e:
                self.logger.error(f"SQLite update failed for {po_number}: {e}")
        return False
