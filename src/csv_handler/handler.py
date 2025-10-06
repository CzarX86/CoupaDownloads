"""CSV Handler implementation for incremental persistence."""

from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .backup import BackupManager
from .models import (
    CSVRecord,
    ProcessingStatus,
    REQUIRED_CSV_COLUMNS,
)
from .write_queue import WriteQueue


class CSVHandler:
    """Provide deterministic CSV read/write operations with backup support."""

    def __init__(
        self,
        csv_path: Path,
        backup_dir: Optional[Path] = None,
        write_queue: Optional[WriteQueue] = None,
        backup_manager: Optional[BackupManager] = None,
    ) -> None:
        self.csv_path = csv_path
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")

        self.backup_dir = backup_dir or self.csv_path.parent / "backup"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.backup_manager = backup_manager or BackupManager(self.backup_dir)
        self.write_queue = write_queue
        self._lock = threading.RLock()
        self._load_dataframe()

    def _load_dataframe(self) -> None:
        self._dataframe = pd.read_csv(self.csv_path, sep=';', dtype=str, keep_default_na=False).fillna('')
        missing = [col for col in REQUIRED_CSV_COLUMNS if col not in self._dataframe.columns]
        if missing:
            raise ValueError(f"CSV missing required columns: {', '.join(missing)}")

    def create_session_backup(self, session_id: str) -> Path:
        """Create a backup prior to mutating CSV data."""
        with self._lock:
            metadata = self.backup_manager.create_backup(self.csv_path, session_id)
        return metadata.backup_path

    def get_pending_records(self) -> List[CSVRecord]:
        """Return records that require processing (STATUS != COMPLETED)."""
        with self._lock:
            pending_df = self._dataframe[self._dataframe['STATUS'].str.upper() != ProcessingStatus.COMPLETED.value]
            records = pending_df.to_dict(orient='records')
        return [CSVRecord.from_dict(record) for record in records]

    def update_record(self, po_number: str, updates: Dict[str, Any]) -> bool:
        """Update a record in-memory and flush to disk."""
        if not po_number:
            raise ValueError("po_number is required")

        with self._lock:
            mask = self._dataframe['PO_NUMBER'] == po_number
            if not mask.any():
                raise ValueError(f"PO number not found: {po_number}")

            normalized_updates = self._normalize_updates(updates)
            for column, value in normalized_updates.items():
                if column not in self._dataframe.columns:
                    continue
                self._dataframe.loc[mask, column] = value

            self._persist()
        return True

    def queue_record_update(self, po_number: str, updates: Dict[str, Any]) -> str:
        """Submit an update to the write queue if configured, else apply immediately."""
        if self.write_queue:
            return self.write_queue.submit_write(po_number, updates)
        self.update_record(po_number, updates)
        return ""

    def get_processing_progress(self) -> Dict[str, int]:
        """Return current processing statistics."""
        with self._lock:
            total = len(self._dataframe.index)
            completed = int((self._dataframe['STATUS'].str.upper() == ProcessingStatus.COMPLETED.value).sum())
            pending = total - completed
        return {
            'total': total,
            'completed': completed,
            'pending': pending,
        }

    def validate_csv_integrity(self) -> bool:
        """Ensure required columns exist."""
        with self._lock:
            missing = [col for col in REQUIRED_CSV_COLUMNS if col not in self._dataframe.columns]
        return not missing

    def refresh(self) -> None:
        """Reload the CSV from disk (useful after external modifications)."""
        with self._lock:
            self._load_dataframe()

    def _persist(self) -> None:
        self._dataframe.to_csv(self.csv_path, sep=';', index=False, encoding='utf-8')

    @staticmethod
    def _normalize_updates(updates: Dict[str, Any]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}
        for key, value in updates.items():
            column = key.strip()
            if column == 'STATUS' and value:
                normalized[column] = str(value).upper()
            elif column == 'AttachmentName' and isinstance(value, list):
                normalized[column] = ';'.join(str(item) for item in value if item)
            elif isinstance(value, datetime):
                normalized[column] = value.isoformat()
            else:
                normalized[column] = value
        if 'LAST_PROCESSED' not in normalized:
            normalized['LAST_PROCESSED'] = datetime.utcnow().isoformat()
        return normalized
