# Data Model: CSV Handler Components

## Core Entities

### CSVRecord
Represents a single row in the CoupaDownloads CSV file.

**Fields**:
- `po_number: str` - Primary identifier (PO_NUMBER column)
- `supplier: str` - Supplier name (SUPPLIER column)  
- `priority: str` - Processing priority (Priority column)
- `supplier_segment: str` - Business segment (Supplier Segment column)
- `spend_type: str` - Spending category (Spend Type column)
- `l1_uu_supplier_name: str` - Normalized supplier name (L1 UU Supplier Name column)

**Status Fields** (updated during processing):
- `status: ProcessingStatus` - Current processing state (STATUS column)
- `attachments_found: int` - Count of discovered attachments (ATTACHMENTS_FOUND column)
- `attachments_downloaded: int` - Count of successfully downloaded files (ATTACHMENTS_DOWNLOADED column)
- `attachment_names: List[str]` - Semicolon-separated list of file names (AttachmentName column)
- `last_processed: datetime` - Processing timestamp (LAST_PROCESSED column)
- `error_message: str` - Error details if processing failed (ERROR_MESSAGE column)
- `download_folder: str` - Local storage path (DOWNLOAD_FOLDER column)
- `coupa_url: str` - Source URL in Coupa system (COUPA_URL column)

**Validation Rules**:
- `po_number` must be non-empty and unique within CSV
- `status` must be valid ProcessingStatus enum value
- `attachments_found >= attachments_downloaded` (logical consistency)
- `last_processed` must be ISO format timestamp when status != PENDING
- `error_message` required when status == ERROR

**State Transitions**:
```
PENDING → COMPLETED (successful processing)
PENDING → ERROR (processing failure)
PENDING → NO_ATTACHMENTS (no files found)
ERROR → COMPLETED (retry success)
ERROR → NO_ATTACHMENTS (retry reveals no attachments)
```

### ProcessingStatus
Enumeration of possible PO processing states.

**Values**:
- `PENDING` - Not yet processed or processing incomplete
- `COMPLETED` - Successfully processed with all attachments downloaded
- `ERROR` - Processing failed with recoverable or permanent error
- `NO_ATTACHMENTS` - Processing completed but no attachments found

**Business Rules**:
- New records default to `PENDING`
- Only `COMPLETED` records are excluded from reprocessing
- `ERROR` records can be retried automatically or manually
- `NO_ATTACHMENTS` is a valid completion state

### WriteOperation
Represents a single CSV write request in the queue.

**Fields**:
- `operation_id: str` - Unique identifier for tracking
- `po_number: str` - Target record identifier
- `updates: Dict[str, Any]` - Field name → new value mapping
- `timestamp: datetime` - When operation was queued
- `retry_count: int` - Number of write attempts (default: 0)
- `priority: int` - Queue priority (default: 0 for FIFO)

**Validation Rules**:
- `po_number` must exist in CSV
- `updates` keys must be valid CSV column names
- `retry_count >= 0` and `retry_count <= 3` (max retries)
- `timestamp` must be set when queued

### BackupMetadata
Tracks automatic CSV backup files for recovery.

**Fields**:
- `backup_path: Path` - Full path to backup file
- `original_path: Path` - Path to original CSV file
- `created_at: datetime` - Backup creation timestamp
- `session_id: str` - Processing session identifier
- `record_count: int` - Number of records in backup
- `file_size_bytes: int` - Backup file size for monitoring

**Business Rules**:
- Backups created before each processing session starts
- Backup filename format: `input_YYYYMMDD_HHMMSS_{session_id}.csv`
- Retention policy: Keep last 5 backups, delete older ones
- Backup validation: Must have same record count as original

### WorkerSession
Represents an active processing session (sequential or parallel).

**Fields**:
- `session_id: str` - Unique session identifier
- `worker_count: int` - Number of parallel workers (1 for sequential)
- `started_at: datetime` - Session start timestamp
- `csv_handler: CSVHandler` - Reference to CSV persistence layer
- `write_queue: WriteQueue` - Shared write serialization queue
- `processed_count: int` - Running count of completed POs
- `total_count: int` - Total POs to process in this session

**Lifecycle**:
1. **Initialize**: Create session, backup CSV, scan for pending records
2. **Process**: Workers update records via write queue
3. **Monitor**: Track progress, handle errors, log status
4. **Cleanup**: Close write queue, finalize logging, cleanup temp files

## Relationships

### CSVRecord ↔ WriteOperation
- **One-to-Many**: Each CSVRecord can have multiple WriteOperations (retries, updates)
- **Constraint**: Only one active WriteOperation per CSVRecord at a time
- **Cascade**: WriteOperation references CSVRecord by po_number

### WorkerSession → CSVHandler → WriteQueue
- **Composition**: WorkerSession owns CSVHandler instance
- **Aggregation**: CSVHandler uses WriteQueue for thread safety  
- **Constraint**: One WriteQueue per WorkerSession

### BackupMetadata ↔ WorkerSession
- **One-to-One**: Each WorkerSession creates exactly one BackupMetadata
- **Temporal**: BackupMetadata.created_at <= WorkerSession.started_at
- **Cleanup**: Old backups cleaned up independent of session lifecycle

## Data Flow

### Write Path
1. Worker completes PO processing
2. Creates WriteOperation with updates
3. WriteQueue serializes operation to single writer thread
4. CSVHandler applies updates to pandas DataFrame
5. CSV file written atomically with validation
6. WriteOperation marked complete or retry

### Read Path  
1. CSVHandler loads CSV into pandas DataFrame on initialization
2. get_pending_records() filters by status != COMPLETED
3. Records distributed to workers for processing
4. Progress tracking via processed_count updates

### Recovery Path
1. Startup scans CSV for records with status != COMPLETED
2. Recent backups available if CSV corruption detected
3. Resume processing from interruption point
4. Failed WriteOperations retried up to 3 times

## Performance Characteristics

### Memory Usage
- CSV loaded once per session into pandas DataFrame
- WriteQueue bounded to prevent memory exhaustion
- BackupMetadata lightweight tracking structures

### I/O Patterns  
- Sequential CSV reads on session startup
- Serialized CSV writes via WriteQueue (no concurrent file access)
- Batch backup operations before processing

### Concurrency Model
- Multiple workers → Single WriteQueue → Single CSV writer thread
- No file locking required (serialized writes eliminate contention)
- Worker isolation: No shared mutable state except WriteQueue