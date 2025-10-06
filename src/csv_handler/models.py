"""Data models for CSV handler module."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List


class ProcessingStatus(Enum):
    """Processing status for PO records."""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"
    NO_ATTACHMENTS = "NO_ATTACHMENTS"


@dataclass
class CSVRecord:
    """Represents a single CSV record with all fields."""

    po_number: str
    status: ProcessingStatus = ProcessingStatus.PENDING
    supplier: str = ""
    attachments_found: int = 0
    attachments_downloaded: int = 0
    attachment_names: List[str] = field(default_factory=list)
    last_processed: Optional[datetime] = None
    error_message: str = ""
    download_folder: str = ""
    coupa_url: str = ""
    priority: str = ""
    supplier_segment: str = ""
    spend_type: str = ""
    l1_uu_supplier_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary format for CSV writing."""
        return {
            'PO_NUMBER': self.po_number,
            'STATUS': self.status.value,
            'SUPPLIER': self.supplier,
            'ATTACHMENTS_FOUND': self.attachments_found,
            'ATTACHMENTS_DOWNLOADED': self.attachments_downloaded,
            'AttachmentName': ';'.join(self.attachment_names),
            'LAST_PROCESSED': self.last_processed.isoformat() if self.last_processed else '',
            'ERROR_MESSAGE': self.error_message,
            'DOWNLOAD_FOLDER': self.download_folder,
            'COUPA_URL': self.coupa_url,
            'Priority': self.priority,
            'Supplier Segment': self.supplier_segment,
            'Spend Type': self.spend_type,
            'L1 UU Supplier Name': self.l1_uu_supplier_name
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CSVRecord':
        """Create record from dictionary (from CSV reading)."""
        last_processed_raw = data.get('LAST_PROCESSED')
        last_processed_value: Optional[datetime] = None
        if last_processed_raw:
            try:
                last_processed_value = datetime.fromisoformat(str(last_processed_raw))
            except ValueError:
                last_processed_value = None

        attachment_field = str(data.get('AttachmentName', '')).strip()
        attachment_names = [part for part in attachment_field.split(';') if part]

        status_raw = str(data.get('STATUS', 'PENDING') or 'PENDING').upper()
        try:
            status_value = ProcessingStatus(status_raw)
        except ValueError:
            status_value = ProcessingStatus.PENDING

        return cls(
            po_number=str(data.get('PO_NUMBER', '')),
            status=status_value,
            supplier=str(data.get('SUPPLIER', '')),
            attachments_found=int(data.get('ATTACHMENTS_FOUND', 0) or 0),
            attachments_downloaded=int(data.get('ATTACHMENTS_DOWNLOADED', 0) or 0),
            attachment_names=attachment_names,
            last_processed=last_processed_value,
            error_message=str(data.get('ERROR_MESSAGE', '')),
            download_folder=str(data.get('DOWNLOAD_FOLDER', '')),
            coupa_url=str(data.get('COUPA_URL', '')),
            priority=str(data.get('Priority', '')),
            supplier_segment=str(data.get('Supplier Segment', '')),
            spend_type=str(data.get('Spend Type', '')),
            l1_uu_supplier_name=str(data.get('L1 UU Supplier Name', ''))
        )
    
    def update_from_dict(self, updates: Dict[str, Any]) -> 'CSVRecord':
        """Create new record with updated fields."""
        current_dict = self.to_dict()
        current_dict.update(updates)
        return self.from_dict(current_dict)


@dataclass
class WriteOperation:
    """Represents a write operation in the queue."""

    operation_id: str
    po_number: str
    updates: Dict[str, Any]
    timestamp: datetime
    retry_count: int = 0
    max_retries: int = 3
    priority: int = 0
    error_message: str = ""

    @property
    def has_retries_left(self) -> bool:
        """Check if operation can be retried."""
        return self.retry_count < self.max_retries

    def increment_retry(self, error_msg: str = "") -> None:
        """Increment retry count and update error message."""
        self.retry_count += 1
        self.error_message = error_msg


@dataclass
class BackupMetadata:
    """Metadata for backup files."""
    backup_path: Path
    original_path: Path
    created_at: datetime
    session_id: str
    record_count: int
    file_size_bytes: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'backup_path': str(self.backup_path),
            'original_path': str(self.original_path),
            'created_at': self.created_at.isoformat(),
            'session_id': self.session_id,
            'record_count': self.record_count,
            'file_size_bytes': self.file_size_bytes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BackupMetadata':
        """Create from dictionary (JSON deserialization)."""
        return cls(
            backup_path=Path(data['backup_path']),
            original_path=Path(data['original_path']),
            created_at=datetime.fromisoformat(data['created_at']),
            session_id=data['session_id'],
            record_count=int(data['record_count']),
            file_size_bytes=int(data['file_size_bytes'])
        )


@dataclass
class QueueStatus:
    """Status information for write queue."""
    pending: int = 0
    completed: int = 0
    failed: int = 0
    queue_size: int = 0
    writer_active: bool = False
    last_write_time: Optional[datetime] = None
    total_operations: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for status reporting."""
        return {
            'pending': self.pending,
            'completed': self.completed,
            'failed': self.failed,
            'queue_size': self.queue_size,
            'writer_active': self.writer_active,
            'last_write_time': self.last_write_time.isoformat() if self.last_write_time else None,
            'total_operations': self.total_operations
        }


# Required CSV columns for validation
REQUIRED_CSV_COLUMNS = [
    'PO_NUMBER',
    'STATUS',
    'SUPPLIER',
    'ATTACHMENTS_FOUND',
    'ATTACHMENTS_DOWNLOADED',
    'AttachmentName',
    'LAST_PROCESSED',
    'ERROR_MESSAGE',
    'DOWNLOAD_FOLDER',
    'COUPA_URL',
    'Priority',
    'Supplier Segment',
    'Spend Type',
    'L1 UU Supplier Name'
]
