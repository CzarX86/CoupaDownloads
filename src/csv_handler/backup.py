"""Backup manager implementation for CSV backup operations."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import List

from .models import BackupMetadata


class BackupManager:
    """Manage CSV backups with retention policies."""

    def __init__(self, backup_dir: Path, retention_count: int = 5) -> None:
        if retention_count < 1:
            raise ValueError("retention_count must be at least 1")

        self.backup_dir = backup_dir
        self.retention_count = retention_count
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, csv_path: Path, session_id: str) -> BackupMetadata:
        """Create a timestamped backup of the CSV file."""
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{csv_path.stem}_{timestamp}_{session_id}.csv"
        backup_path = self.backup_dir / backup_name

        shutil.copy2(csv_path, backup_path)

        record_count = self._count_records(csv_path)
        file_size_bytes = backup_path.stat().st_size

        metadata = BackupMetadata(
            backup_path=backup_path,
            original_path=csv_path,
            created_at=datetime.utcnow(),
            session_id=session_id,
            record_count=record_count,
            file_size_bytes=file_size_bytes,
        )

        self.cleanup_old_backups()
        return metadata

    def cleanup_old_backups(self) -> List[Path]:
        """Remove old backups beyond the retention limit."""
        backups = sorted(
            [p for p in self.backup_dir.glob("*.csv") if p.is_file()],
            key=lambda path: path.stat().st_mtime,
        )

        if len(backups) <= self.retention_count:
            return []

        to_remove = backups[:-self.retention_count]
        removed: List[Path] = []
        for backup in to_remove:
            try:
                backup.unlink()
                removed.append(backup)
            except FileNotFoundError:
                continue

        return removed

    def restore_from_backup(self, backup_metadata: BackupMetadata, target_path: Path) -> bool:
        """Restore CSV from a backup file."""
        if not backup_metadata.backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_metadata.backup_path}")

        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_metadata.backup_path, target_path)
        return True

    @staticmethod
    def _count_records(csv_path: Path) -> int:
        """Count CSV records excluding header."""
        with csv_path.open("r", encoding="utf-8", errors="ignore") as handle:
            # Subtract 1 for header line if file not empty
            total_lines = sum(1 for _ in handle)
        return max(total_lines - 1, 0)
