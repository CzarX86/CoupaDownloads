"""CSV Handler Interface Contracts for CoupaDownloads incremental persistence."""

from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


class ProcessingStatus(Enum):
    """Enumeration of PO processing states."""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED" 
    ERROR = "ERROR"
    NO_ATTACHMENTS = "NO_ATTACHMENTS"


@dataclass
class CSVRecord:
    """Represents a single PO record in the CSV file."""
    po_number: str
    supplier: str
    priority: str
    supplier_segment: str
    spend_type: str
    l1_uu_supplier_name: str
    status: ProcessingStatus = ProcessingStatus.PENDING
    attachments_found: int = 0
    attachments_downloaded: int = 0
    attachment_names: List[str] = field(default_factory=list)
    last_processed: Optional[datetime] = None
    error_message: str = ""
    download_folder: str = ""
    coupa_url: str = ""


@dataclass
class WriteOperation:
    """Represents a queued CSV write operation."""
    operation_id: str
    po_number: str
    updates: Dict[str, Any]
    timestamp: datetime
    retry_count: int = 0
    priority: int = 0


@dataclass
class BackupMetadata:
    """Metadata for CSV backup files."""
    backup_path: Path
    original_path: Path
    created_at: datetime
    session_id: str
    record_count: int
    file_size_bytes: int


class CSVError(Exception):
    """Base exception for CSV handler errors."""
    pass


class CSVValidationError(CSVError):
    """Raised when CSV validation fails."""
    pass


class CSVWriteError(CSVError):
    """Raised when CSV write operation fails."""
    pass


class BackupError(CSVError):
    """Raised when backup operations fail."""
    pass


class CSVHandlerInterface(ABC):
    """Abstract interface for CSV persistence operations."""
    
    @abstractmethod
    def __init__(self, csv_path: Path, backup_dir: Optional[Path] = None):
        """Initialize handler with CSV file path and optional backup directory."""
        pass
        
    @abstractmethod
    def create_session_backup(self, session_id: str) -> Path:
        """Create backup before starting processing session."""
        pass
        
    @abstractmethod
    def get_pending_records(self) -> List[CSVRecord]:
        """Get all records that need processing (status != COMPLETED)."""
        pass
        
    @abstractmethod
    def update_record(self, po_number: str, updates: Dict[str, Any]) -> bool:
        """Update a single record with new field values."""
        pass
        
    @abstractmethod
    def get_processing_progress(self) -> Dict[str, int]:
        """Get current processing statistics."""
        pass
        
    @abstractmethod
    def validate_csv_integrity(self) -> bool:
        """Validate CSV file structure and data consistency."""
        pass


class WriteQueueInterface(ABC):
    """Abstract interface for thread-safe write operation serializer."""
    
    @abstractmethod
    def __init__(self, csv_handler: CSVHandlerInterface, max_retries: int = 3):
        """Initialize write queue with CSV handler."""
        pass
        
    @abstractmethod
    def submit_write(self, po_number: str, updates: Dict[str, Any]) -> str:
        """Submit write operation to queue."""
        pass
        
    @abstractmethod
    def start_writer_thread(self) -> None:
        """Start background thread for processing write queue."""
        pass
        
    @abstractmethod
    def stop_writer_thread(self, timeout: float = 30.0) -> bool:
        """Stop write queue processor gracefully."""
        pass
        
    @abstractmethod
    def get_queue_status(self) -> Dict[str, int]:
        """Get current queue statistics."""
        pass


class BackupManagerInterface(ABC):
    """Abstract interface for managing CSV backup operations."""
    
    @abstractmethod
    def __init__(self, backup_dir: Path, retention_count: int = 5):
        """Initialize backup manager."""
        pass
        
    @abstractmethod
    def create_backup(self, csv_path: Path, session_id: str) -> BackupMetadata:
        """Create timestamped backup of CSV file."""
        pass
        
    @abstractmethod
    def cleanup_old_backups(self) -> List[Path]:
        """Remove old backups beyond retention limit."""
        pass
        
    @abstractmethod
    def restore_from_backup(self, backup_metadata: BackupMetadata, target_path: Path) -> bool:
        """Restore CSV from backup file."""
        pass


class WorkerPoolCSVIntegration(ABC):
    """Contract for integrating CSV handler with existing worker pool."""
    
    @abstractmethod
    def inject_csv_handler(self, worker_pool: Any, csv_handler: CSVHandlerInterface) -> None:
        """Inject CSV handler into worker pool for result persistence."""
        pass
        
    @abstractmethod
    def setup_result_callback(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """Configure callback for worker result processing."""
        pass


class MainFlowCSVIntegration(ABC):
    """Contract for integrating with Core_main.py processing flow."""
    
    @abstractmethod
    def initialize_csv_handler(self, config: Dict[str, Any]) -> CSVHandlerInterface:
        """Initialize CSV handler from configuration."""
        pass
        
    @abstractmethod
    def setup_progress_reporting(self, progress_callback: Callable[[Dict[str, int]], None]) -> None:
        """Configure progress reporting for operator visibility."""
        pass