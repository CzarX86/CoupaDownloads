from typing import Optional, Dict, Any
from pathlib import Path

from .core.csv_handler import CSVHandler, WriteQueue


class CSVManager:
    """Manager for CSV handling operations."""

    def __init__(self):
        self._csv_handler: Optional[CSVHandler] = None
        self._csv_write_queue: Optional[WriteQueue] = None
        self._csv_session_id: Optional[str] = None

    @property
    def csv_handler(self) -> Optional[CSVHandler]:
        """Get the CSV handler instance."""
        return self._csv_handler

    @csv_handler.setter
    def csv_handler(self, value: Optional[CSVHandler]) -> None:
        """Set the CSV handler instance."""
        self._csv_handler = value

    def initialize_csv_handler(self, csv_input_path: Path) -> Optional[str]:
        """Initialize CSV handler if input is CSV."""
        if csv_input_path.suffix.lower() == '.csv' and not self.csv_handler:
            try:
                self.csv_handler, self._csv_write_queue, self._csv_session_id = CSVHandler.create_handler(
                    csv_input_path, enable_incremental_updates=True
                )
                print(f"🛡️ CSV backup created at: {CSVHandler.get_backup_path(csv_input_path)}")
                return self._csv_session_id
            except Exception as e:
                print(f"⚠️ Failed to initialize CSV handler: {e}")
                return None
        return None

    def shutdown_csv_handler(self):
        """Shutdown CSV handler to ensure all data is persisted."""
        if self._csv_write_queue:
            self._csv_write_queue.stop_writer_thread(timeout=15.0)
        self._csv_write_queue = None
        self.csv_handler = None

    def update_record(self, po_number: str, updates: Dict[str, Any]) -> bool:
        """Update a CSV record."""
        if self.csv_handler:
            return self.csv_handler.update_record(po_number, updates)
        return False

    def is_initialized(self) -> bool:
        """Check if CSV handler is initialized."""
        return self.csv_handler is not None