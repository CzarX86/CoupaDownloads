# ProcessingSession API Contract

**Module**: `EXPERIMENTAL.core.main`  
**Class**: `ProcessingSession`

## Constructor

```python
def __init__(
    self,
    headless_config: HeadlessConfiguration,
    enable_parallel: bool = True,
    max_workers: int = 4,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> None:
    """Initialize processing session for PO batch processing.
    
    Args:
        headless_config: Browser mode configuration
        enable_parallel: Whether to use parallel processing for multiple POs
        max_workers: Maximum number of parallel workers (1-8)
        progress_callback: Optional callback for progress updates
        
    Raises:
        ValueError: If max_workers not in valid range
        TypeError: If headless_config is not HeadlessConfiguration instance
    """
```

## Core Methods

### process_pos
```python
def process_pos(self, po_list: List[dict]) -> Tuple[int, int, Dict[str, Any]]:
    """Process list of POs with automatic mode selection.
    
    Args:
        po_list: List of PO data dictionaries with required keys:
                 - po_number: str
                 - supplier: str  
                 - url: str
                 - amount: float
                 
    Returns:
        Tuple[int, int, Dict[str, Any]]:
            - successful_count: Number of POs processed successfully
            - failed_count: Number of POs that failed processing
            - session_report: Detailed processing report and metrics
        
    Behavior:
        - If enable_parallel=True and len(po_list) > 1: Use WorkerPool
        - If enable_parallel=False or single PO: Use sequential processing
        - Maintains compatibility with existing EXPERIMENTAL workflow
        - Preserves all logging, progress tracking, and download organization
        
    Side Effects:
        - Creates worker pool if parallel processing selected
        - Updates progress via callback if configured
        - Logs processing mode selection and performance metrics
        - Maintains existing download directory structure
    """
```

### get_processing_mode
```python
def get_processing_mode(self, po_count: int) -> str:
    """Determine processing mode based on configuration and PO count.
    
    Args:
        po_count: Number of POs to process
        
    Returns:
        str: Processing mode ("sequential" or "parallel")
        
    Decision Criteria:
        - Parallel mode enabled in configuration
        - More than 1 PO to process
        - System resources adequate (memory, CPU)
        - No conflicting operations in progress
    """
```

### get_progress
```python
def get_progress(self) -> Dict[str, Any]:
    """Get current processing progress and status.
    
    Returns:
        Dict[str, Any]: Progress information with keys:
            - session_status: SessionStatus enum value
            - total_tasks: int total number of POs
            - completed_tasks: int number completed
            - failed_tasks: int number failed
            - active_tasks: int number currently processing
            - elapsed_time: float seconds since start
            - estimated_remaining: Optional[float] estimated seconds remaining
            - processing_mode: str ("sequential" or "parallel")
            - worker_details: List[Dict] per-worker status (if parallel)
    """
```

### stop_processing
```python
def stop_processing(self) -> bool:
    """Stop current processing session gracefully.
    
    Returns:
        bool: True if session stopped successfully
        
    Behavior:
        - Signals workers to complete current tasks and stop
        - Waits for graceful completion up to configured timeout
        - Performs resource cleanup (profiles, processes)
        - Updates session status and generates final report
    """
```

## Progress and Monitoring

### set_progress_callback
```python
def set_progress_callback(
    self, 
    callback: Callable[[Dict[str, Any]], None]
) -> None:
    """Set or update progress callback function.
    
    Args:
        callback: Function to call with progress updates
        
    Callback receives progress dictionary with current status
    Called approximately every 1-2 seconds during processing
    """
```

### get_session_report
```python
def get_session_report(self) -> Dict[str, Any]:
    """Generate comprehensive session report.
    
    Returns:
        Dict[str, Any]: Session report with keys:
            - session_id: str unique session identifier
            - start_time: datetime session start
            - end_time: Optional[datetime] session completion
            - processing_mode: str mode used
            - total_pos: int total POs processed
            - successful_pos: int successful completions
            - failed_pos: int processing failures
            - performance_metrics: Dict timing and throughput data
            - worker_performance: Dict per-worker statistics (if parallel)
            - error_summary: List[Dict] error details and frequencies
    """
```

## Integration with MainApp

### Enhanced MainApp Constructor
```python
# MainApp class enhancement
def __init__(
    self,
    headless_config: Optional[HeadlessConfiguration] = None,
    enable_parallel: bool = False,
    max_workers: int = 4
) -> None:
    """Initialize MainApp with optional parallel processing support.
    
    Args:
        headless_config: Browser mode configuration
        enable_parallel: Whether to use parallel processing for multiple POs
        max_workers: Number of workers for parallel mode (1-8)
        
    Note:
        Backward compatibility: existing single PO processing unchanged
        Parallel processing opt-in via enable_parallel parameter
    """
```

### Backward Compatibility Methods
```python
def process_single_po(self, po_data: dict) -> bool:
    """Process single PO (existing method - unchanged).
    
    Note:
        This method remains unchanged for backward compatibility.
        Uses sequential processing regardless of parallel configuration.
    """

def _process_po_entries(self, po_list: List[dict]) -> Tuple[int, int]:
    """Process multiple POs with automatic mode selection.
    
    Note:
        Enhanced to use ProcessingSession for mode selection
        Maintains existing interface and return format
        Adds parallel processing capability when beneficial
    """
```

## Error Handling Integration

### Parallel Processing Fallback
```python
def _handle_parallel_failure(
    self,
    error: Exception,
    po_list: List[dict],
    partial_results: Tuple[int, int]
) -> Tuple[int, int]:
    """Handle parallel processing failures with graceful fallback.
    
    Args:
        error: Exception that occurred during parallel processing
        po_list: Original PO list being processed
        partial_results: Results from workers that completed
        
    Returns:
        Tuple[int, int]: Final processing results
        
    Behavior:
        1. Log parallel processing failure details
        2. Identify remaining unprocessed POs
        3. Fall back to sequential processing for remaining items
        4. Combine results from parallel and sequential phases
        5. Report fallback in session summary
    """
```

### Resource Management
```python
def _monitor_resources(self) -> Dict[str, Any]:
    """Monitor system resources during processing.
    
    Returns:
        Dict[str, Any]: Resource usage information
        
    Monitors:
        - Memory usage per worker and total
        - CPU utilization across workers
        - Disk space for profiles and downloads
        - Network bandwidth utilization
    """
```

## Configuration Management

### Processing Mode Configuration
```python
def configure_parallel_processing(
    self,
    enabled: bool,
    max_workers: Optional[int] = None,
    worker_timeout: Optional[int] = None
) -> None:
    """Configure parallel processing parameters.
    
    Args:
        enabled: Whether to enable parallel processing
        max_workers: Maximum number of workers (if changing)
        worker_timeout: Timeout per worker task (if changing)
    """
```

### Performance Tuning
```python
def auto_configure_workers(self, po_count: int) -> int:
    """Automatically determine optimal worker count.
    
    Args:
        po_count: Number of POs to process
        
    Returns:
        int: Recommended worker count
        
    Considers:
        - System CPU cores and memory
        - PO count and estimated processing time
        - Historical performance data
        - Current system load
    """
```

## Testing and Validation Support

### Test Mode Configuration
```python
def enable_test_mode(
    self,
    mock_workers: bool = False,
    simulate_failures: bool = False,
    fixed_timing: bool = False
) -> None:
    """Configure session for testing scenarios.
    
    Args:
        mock_workers: Use mock worker pool for testing
        simulate_failures: Inject controlled failures for testing
        fixed_timing: Use deterministic timing for reproducible tests
    """
```

### Validation Hooks
```python
def validate_session_state(self) -> List[str]:
    """Validate session state consistency.
    
    Returns:
        List[str]: List of validation errors (empty if valid)
        
    Validates:
        - Worker pool state consistency
        - Task queue integrity
        - Resource allocation and cleanup
        - Progress tracking accuracy
    """
```

---

*Contract defines ProcessingSession integration for parallel processing support*