# Quickstart: CSV Handler Integration

## Overview
This guide demonstrates how to integrate and test the incremental CSV persistence system in CoupaDownloads.

## Setup

### 1. Dependencies
All required dependencies are already in the project:
```bash
# Verify existing dependencies
poetry show | grep -E "pandas|structlog"
```

### 2. Test Data Preparation
```bash
# Create backup directory
mkdir -p data/backup

# Verify CSV structure
head -n 3 data/input/input.csv
# Should show: PO_NUMBER;STATUS;SUPPLIER;...
```

## Basic Integration

### 1. Import CSV Handler
```python
from src.csv.handler import CSVHandler
from src.csv.write_queue import WriteQueue
from pathlib import Path

# Initialize handler
csv_handler = CSVHandler(
    csv_path=Path("data/input/input.csv"),
    backup_dir=Path("data/backup")
)
```

### 2. Create Processing Session
```python
import uuid
from datetime import datetime

# Create session backup
session_id = str(uuid.uuid4())[:8]
backup_path = csv_handler.create_session_backup(session_id)
print(f"Backup created: {backup_path}")

# Get pending records
pending_records = csv_handler.get_pending_records()
print(f"Found {len(pending_records)} pending POs")
```

### 3. Process Single Record (Sequential Mode)
```python
# Simulate processing a PO
test_po = pending_records[0] if pending_records else None
if test_po:
    # Update with processing results
    updates = {
        'STATUS': 'COMPLETED',
        'ATTACHMENTS_FOUND': 2,
        'ATTACHMENTS_DOWNLOADED': 2,
        'AttachmentName': 'invoice.pdf;receipt.pdf',
        'LAST_PROCESSED': datetime.now().isoformat(),
        'DOWNLOAD_FOLDER': 'downloads/PO_12345',
        'COUPA_URL': 'https://coupa.com/purchase_orders/12345'
    }
    
    success = csv_handler.update_record(test_po.po_number, updates)
    print(f"Update result: {success}")
    
    # Verify progress
    progress = csv_handler.get_processing_progress()
    print(f"Progress: {progress}")
```

## Concurrent Processing Integration

### 1. Worker Pool Setup
```python
from src.csv.write_queue import WriteQueue
import threading
import time

# Initialize write queue for concurrent access
write_queue = WriteQueue(csv_handler, max_retries=3)
write_queue.start_writer_thread()

def simulate_worker(worker_id: int, po_batch: List[str]):
    """Simulate a worker processing POs"""
    for po_number in po_batch:
        print(f"Worker {worker_id} processing {po_number}")
        
        # Simulate processing time
        time.sleep(0.1)
        
        # Submit results via write queue
        updates = {
            'STATUS': 'COMPLETED',
            'ATTACHMENTS_FOUND': 1,
            'ATTACHMENTS_DOWNLOADED': 1,
            'AttachmentName': f'{po_number}_attachment.pdf',
            'LAST_PROCESSED': datetime.now().isoformat(),
            'DOWNLOAD_FOLDER': f'downloads/{po_number}',
            'COUPA_URL': f'https://coupa.com/purchase_orders/{po_number}'
        }
        
        operation_id = write_queue.submit_write(po_number, updates)
        print(f"Worker {worker_id} submitted operation {operation_id}")

# Test with multiple workers
if len(pending_records) >= 4:
    po_numbers = [r.po_number for r in pending_records[:4]]
    
    # Split work between 2 workers
    batch1 = po_numbers[:2]
    batch2 = po_numbers[2:]
    
    # Start worker threads
    worker1 = threading.Thread(target=simulate_worker, args=(1, batch1))
    worker2 = threading.Thread(target=simulate_worker, args=(2, batch2))
    
    worker1.start()
    worker2.start()
    
    worker1.join()
    worker2.join()
    
    # Check queue status
    queue_status = write_queue.get_queue_status()
    print(f"Queue status: {queue_status}")
    
    # Shutdown gracefully
    write_queue.stop_writer_thread(timeout=10.0)
```

## Error Handling Tests

### 1. Validation Test
```python
# Test CSV integrity validation
try:
    is_valid = csv_handler.validate_csv_integrity()
    print(f"CSV validation: {'PASS' if is_valid else 'FAIL'}")
except Exception as e:
    print(f"Validation error: {e}")
```

### 2. Recovery Test
```python
# Test resume functionality
print("\\nTesting recovery scenario...")

# Get current state
initial_progress = csv_handler.get_processing_progress()
print(f"Initial state: {initial_progress}")

# Simulate processing more records
remaining_pending = csv_handler.get_pending_records()
if remaining_pending:
    test_po = remaining_pending[0]
    
    # Simulate partial processing (ERROR state)
    error_updates = {
        'STATUS': 'ERROR',
        'ERROR_MESSAGE': 'Network timeout during download',
        'LAST_PROCESSED': datetime.now().isoformat()
    }
    
    csv_handler.update_record(test_po.po_number, error_updates)
    print(f"Simulated error for PO: {test_po.po_number}")
    
    # Verify error is in pending list (for retry)
    pending_after_error = csv_handler.get_pending_records()
    error_po_still_pending = any(r.po_number == test_po.po_number for r in pending_after_error)
    print(f"Error PO still pending for retry: {error_po_still_pending}")
```

## Integration with Existing Worker Pool

### 1. Modify Core_main.py
```python
# Add to imports
from src.csv.handler import CSVHandler
from src.csv.write_queue import WriteQueue

def main():
    # Initialize CSV handler
    csv_handler = CSVHandler(
        csv_path=Path("data/input/input.csv"),
        backup_dir=Path("data/backup")
    )
    
    # Create session backup
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = csv_handler.create_session_backup(session_id)
    logger.info("Session backup created", backup_path=str(backup_path))
    
    # Get pending work
    pending_records = csv_handler.get_pending_records()
    logger.info("Pending records loaded", count=len(pending_records))
    
    if USE_WORKER_POOL:
        # Parallel mode with write queue
        write_queue = WriteQueue(csv_handler)
        write_queue.start_writer_thread()
        
        # Initialize worker pool with CSV handler
        worker_pool = WorkerPool(worker_count=4)
        
        # Process POs (existing logic)
        # ... existing worker pool code ...
        
        # Ensure graceful shutdown
        write_queue.stop_writer_thread(timeout=30.0)
    else:
        # Sequential mode (direct CSV handler)
        for record in pending_records:
            # Process PO (existing logic)
            results = process_po(record.po_number)
            
            # Update CSV immediately
            csv_handler.update_record(record.po_number, results)
```

### 2. Modify Worker Class
```python
class Worker:
    def __init__(self, worker_id: int, csv_handler: CSVHandler):
        self.worker_id = worker_id
        self.csv_handler = csv_handler
    
    def process_po(self, po_number: str) -> Dict[str, Any]:
        """Process PO and return results for CSV update"""
        try:
            # Existing PO processing logic
            # ...
            
            results = {
                'STATUS': 'COMPLETED',
                'ATTACHMENTS_FOUND': len(attachments),
                'ATTACHMENTS_DOWNLOADED': len(downloaded),
                'AttachmentName': ';'.join(downloaded_names),
                'LAST_PROCESSED': datetime.now().isoformat(),
                'DOWNLOAD_FOLDER': download_path,
                'COUPA_URL': coupa_url
            }
            
            # Update CSV via handler (thread-safe)
            success = self.csv_handler.update_record(po_number, results)
            if not success:
                logger.warning("Failed to update CSV", po_number=po_number)
            
            return results
            
        except Exception as e:
            error_results = {
                'STATUS': 'ERROR',
                'ERROR_MESSAGE': str(e),
                'LAST_PROCESSED': datetime.now().isoformat()
            }
            self.csv_handler.update_record(po_number, error_results)
            raise
```

## Validation Checklist

After integration, verify these scenarios:

### ✅ Basic Functionality
- [ ] CSV loads successfully with existing data
- [ ] Backup created before processing starts
- [ ] Single record updates work correctly
- [ ] Progress tracking shows accurate counts

### ✅ Concurrent Access
- [ ] Multiple workers can update different records simultaneously
- [ ] No CSV corruption during concurrent writes
- [ ] Write queue processes operations in order
- [ ] Graceful shutdown waits for pending writes

### ✅ Error Handling
- [ ] Failed writes are retried up to 3 times
- [ ] Transient errors (disk space) are handled gracefully
- [ ] CSV validation detects corruption
- [ ] Error records remain in pending state for retry

### ✅ Recovery
- [ ] Restart correctly identifies pending records
- [ ] ERROR status records are included in pending list
- [ ] COMPLETED records are excluded from reprocessing
- [ ] Backup can be restored if needed

## Performance Validation

### Expected Performance
- CSV write operations: < 5 seconds for 10,000 records
- Memory usage: < 100MB additional for CSV handler
- Backup creation: < 10 seconds for typical CSV sizes

### Monitoring Commands
```bash
# Monitor CSV file changes during processing
watch -n 1 "tail -n 5 data/input/input.csv"

# Check backup directory
ls -la data/backup/

# Monitor processing logs
tail -f logs/processing.log | grep -E "(CSV|backup|write)"
```