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
    """Main interface for CSV persistence operations."""
    
    def __init__(self, csv_path: Path, backup_dir: Path = None):
        """Initialize handler with CSV file path and optional backup directory.
        
        Args:
            csv_path: Path to input CSV file
            backup_dir: Directory for backup files (default: csv_path.parent / 'backup')
            
        Raises:
            FileNotFoundError: If csv_path doesn't exist
            PermissionError: If insufficient file permissions
        """
        
    def create_session_backup(self, session_id: str) -> Path:
        """Create backup before starting processing session.
        
        Args:
            session_id: Unique identifier for processing session
            
        Returns:
            Path to created backup file
            
        Raises:
            IOError: If backup creation fails
        """
        
    def get_pending_records(self) -> List[CSVRecord]:
        """Get all records that need processing.
        
        Returns:
            List of records where status != COMPLETED
            
        Raises:
            ValueError: If CSV format is invalid
        """
        
    def update_record(self, po_number: str, updates: Dict[str, Any]) -> bool:
        """Update a single record with new field values.
        
        Args:
            po_number: PO identifier to update
            updates: Dictionary of field_name -> new_value
            
        Returns:
            True if update successful, False otherwise
            
        Raises:
            ValueError: If po_number not found or updates invalid
            IOError: If write operation fails after retries
        """
        
    def get_processing_progress(self) -> Dict[str, int]:
        """Get current processing statistics.
        
        Returns:
            Dictionary with keys: total, pending, completed, error, no_attachments
        """
        
    def validate_csv_integrity(self) -> bool:
        """Validate CSV file structure and data consistency.
        
        Returns:
            True if CSV is valid and consistent
            
        Raises:
            ValueError: If critical validation errors found
        """
```

## WriteQueue Interface

```python
from queue import Queue
from threading import Thread
from typing import Callable

@dataclass
class WriteOperation:
    operation_id: str
    po_number: str
    updates: Dict[str, Any]
    timestamp: datetime
    retry_count: int = 0
    priority: int = 0

class WriteQueue:
    """Thread-safe write operation serializer."""
    
    def __init__(self, csv_handler: CSVHandler, max_retries: int = 3):
        """Initialize write queue with CSV handler.
        
        Args:
            csv_handler: CSVHandler instance for write operations
            max_retries: Maximum retry attempts for failed writes
        """
        
    def submit_write(self, po_number: str, updates: Dict[str, Any]) -> str:
        """Submit write operation to queue.
        
        Args:
            po_number: Target record identifier
            updates: Field updates to apply
            
        Returns:
            Operation ID for tracking
            
        Raises:
            ValueError: If po_number or updates invalid
        """
        
    def start_writer_thread(self):
        """Start background thread for processing write queue."""
        
    def stop_writer_thread(self, timeout: float = 30.0) -> bool:
        """Stop write queue processor gracefully.
        
        Args:
            timeout: Maximum seconds to wait for shutdown
            
        Returns:
            True if shutdown successful within timeout
        """
        
    def get_queue_status(self) -> Dict[str, int]:
        """Get current queue statistics.
        
        Returns:
            Dictionary with keys: pending, completed, failed
        """
```

## BackupManager Interface

```python
@dataclass
class BackupMetadata:
    backup_path: Path
    original_path: Path
    created_at: datetime
    session_id: str
    record_count: int
    file_size_bytes: int

class BackupManager:
    """Manages CSV backup operations and retention."""
    
    def __init__(self, backup_dir: Path, retention_count: int = 5):
        """Initialize backup manager.
        
        Args:
            backup_dir: Directory for storing backup files
            retention_count: Number of recent backups to retain
        """
        
    def create_backup(self, csv_path: Path, session_id: str) -> BackupMetadata:
        """Create timestamped backup of CSV file.
        
        Args:
            csv_path: Source CSV file to backup
            session_id: Processing session identifier
            
        Returns:
            Metadata for created backup
            
        Raises:
            IOError: If backup creation fails
        """
        
    def cleanup_old_backups(self) -> List[Path]:
        """Remove old backups beyond retention limit.
        
        Returns:
            List of paths to deleted backup files
        """
        
    def restore_from_backup(self, backup_metadata: BackupMetadata, target_path: Path) -> bool:
        """Restore CSV from backup file.
        
        Args:
            backup_metadata: Backup to restore from
            target_path: Destination path for restored file
            
        Returns:
            True if restore successful
            
        Raises:
            FileNotFoundError: If backup file missing
            IOError: If restore operation fails
        """
```

## Error Handling Contracts

```python
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

# Error handling behavior contracts:
# 1. All write operations retry up to 3 times with exponential backoff
# 2. Validation errors are logged but don't halt processing 
# 3. Critical errors (file corruption) require manual intervention
# 4. Transient errors (disk space) are retried then logged as warnings
```

## Integration Contracts

### Worker Pool Integration
```python
class WorkerPoolCSVIntegration:
    """Contract for integrating CSV handler with existing worker pool."""
    
    def inject_csv_handler(self, worker_pool: 'WorkerPool', csv_handler: CSVHandler):
        """Inject CSV handler into worker pool for result persistence.
        
        Args:
            worker_pool: Existing CoupaDownloads WorkerPool instance
            csv_handler: Configured CSVHandler for persistence
        """
        
    def setup_result_callback(self, callback: Callable[[str, Dict], None]):
        """Configure callback for worker result processing.
        
        Args:
            callback: Function called when worker completes PO processing
                     Signature: callback(po_number: str, results: Dict[str, Any])
        """
```

### Main Flow Integration
```python
class MainFlowCSVIntegration:
    """Contract for integrating with Core_main.py processing flow."""
    
    def initialize_csv_handler(self, config: Dict[str, Any]) -> CSVHandler:
        """Initialize CSV handler from configuration.
        
        Args:
            config: Configuration dictionary from main flow
            
        Returns:
            Configured CSVHandler instance
        """
        
    def setup_progress_reporting(self, progress_callback: Callable[[Dict], None]):
        """Configure progress reporting for operator visibility.
        
        Args:
            progress_callback: Function called with progress updates
                             Signature: callback(progress: Dict[str, int])
        """
```