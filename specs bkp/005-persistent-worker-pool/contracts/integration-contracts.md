# Integration Contracts: Worker Pool to Existing System

## Core Integration Points

### 1. Core_main.py Integration

#### Entry Point Contract
```python
# Current: src/Core_main.py
def main() -> None:
    """Enhanced with persistent worker pool capability"""
    # Existing initialization remains unchanged
    setup_logging()
    validate_environment()
    
    # NEW: Pool configuration from environment/config
    use_persistent_pool = get_config('USE_PERSISTENT_POOL', default=True)
    
    if use_persistent_pool:
        # NEW: Use persistent worker pool
        result = process_with_persistent_pool()
    else:
        # EXISTING: Fallback to current implementation
        result = process_with_current_flow()
```

#### Configuration Migration
- Existing CSV processing logic preserved
- Current download validation unchanged  
- Logging integration maintained
- Error handling patterns consistent

### 2. CSV Processing Integration

#### Batch Task Generation
```python
# Integration with existing CSV reader
def create_po_tasks_from_csv(csv_path: str) -> List[POTask]:
    """Convert CSV rows to POTask objects"""
    # Leverage existing CSV validation
    # Transform to worker pool task format
    # Preserve existing error handling
```

#### Progress Tracking
```python
# Enhanced progress reporting
def track_batch_progress(pool: PersistentWorkerPool) -> ProgressReport:
    """Integrate with existing progress display"""
    status = pool.get_status()
    # Map to existing progress format
    # Maintain current UI/logging patterns
```

### 3. Download Management Integration

#### File Output Contract
- **Location**: Preserve existing `download/` directory structure
- **Naming**: Maintain current file naming conventions
- **Validation**: Use existing download verification logic
- **Cleanup**: Integrate with current temporary file management

#### Result Aggregation
```python
# Enhanced result collection
@dataclass
class BatchResult:
    """Extended existing result format"""
    total_pos: int
    successful_downloads: int
    failed_downloads: int
    processing_time: float
    
    # NEW: Worker pool specific metrics
    worker_restarts: int
    memory_peak_usage: float
    average_po_time: float
```

### 4. Error Handling Integration

#### Exception Mapping
```python
# Map worker pool errors to existing error handling
ERROR_MAPPING = {
    ProfileCorruptionError: "PROFILE_ERROR",  # Existing error code
    InsufficientResourcesError: "RESOURCE_ERROR",  # Existing error code  
    PONotFoundError: "PO_NOT_FOUND",  # Existing error code
    NetworkError: "NETWORK_ERROR"  # Existing error code
}
```

#### Recovery Procedures
- **Worker Crash**: Log using existing logger, continue with remaining workers
- **Session Timeout**: Use existing retry logic patterns
- **Memory Pressure**: Log memory warnings using current warning system
- **Profile Issues**: Trigger existing error reporting mechanisms

## Implementation Strategy

### Phase 1: Core Worker Pool (EXPERIMENTAL/)
```
EXPERIMENTAL/
├── workers/
│   ├── __init__.py
│   ├── persistent_pool.py      # PersistentWorkerPool class
│   ├── worker_process.py       # Worker class  
│   └── browser_session.py      # BrowserSession class
├── core/
│   ├── __init__.py
│   ├── task_queue.py          # Enhanced TaskQueue
│   ├── profile_manager.py     # Enhanced ProfileManager
│   └── memory_monitor.py      # Enhanced MemoryMonitor
└── integration/
    ├── __init__.py
    ├── csv_adapter.py         # CSV → POTask conversion
    ├── result_collector.py    # Result aggregation
    └── main_adapter.py        # Core_main.py integration
```

### Phase 2: Core_main.py Enhancement
```python
# Minimal changes to existing entry point
def main() -> None:
    """Enhanced main function with pool option"""
    try:
        if should_use_persistent_pool():
            from EXPERIMENTAL.integration.main_adapter import process_with_pool
            return process_with_pool()
        else:
            # Existing implementation unchanged
            return original_main_flow()
    except Exception as e:
        # Existing error handling unchanged
        handle_error(e)
```

### Phase 3: Configuration Integration
```python
# Enhanced configuration with backward compatibility
@dataclass
class ProcessingConfig:
    """Extended existing config"""
    # Existing fields preserved
    csv_path: str
    download_path: str
    headless_mode: bool
    
    # NEW: Worker pool specific
    use_persistent_pool: bool = True
    worker_count: int = 4
    memory_threshold: float = 0.75
    worker_timeout: float = 300.0
```

## Backward Compatibility Guarantees

### 1. CLI Interface Preservation
- All existing command line arguments work unchanged
- New arguments are optional with sensible defaults
- Help text enhanced but existing options preserved

### 2. Configuration File Compatibility  
- Existing `myscript_config.json` format supported
- New fields optional with defaults
- No breaking changes to existing keys

### 3. Output Format Preservation
- CSV output format unchanged
- Log message formats preserved  
- Progress display maintains current style
- Error codes and messages consistent

### 4. Environment Variable Support
- Existing environment variables work unchanged
- New variables use consistent naming pattern
- Documentation updated to reflect new options

## Testing Integration Contracts

### Unit Test Integration
```python
# Enhanced test structure
class TestWorkerPoolIntegration(unittest.TestCase):
    """Integration tests preserving existing test patterns"""
    
    def test_csv_processing_compatibility(self):
        """Verify CSV processing works with both implementations"""
        
    def test_download_output_format(self):
        """Verify output format matches existing expectations"""
        
    def test_error_handling_consistency(self):
        """Verify error codes match existing implementation"""
```

### Performance Test Integration
```python
# Performance comparison tests
class TestPerformanceRegression(unittest.TestCase):
    """Ensure worker pool improves or maintains performance"""
    
    def test_memory_usage_improvement(self):
        """Verify memory usage is lower than current implementation"""
        
    def test_processing_speed_improvement(self):
        """Verify processing time is faster or equivalent"""
```

## Migration Strategy

### Development Phase Migration
1. **Week 1**: Implement core worker pool in EXPERIMENTAL/
2. **Week 2**: Create integration adapters
3. **Week 3**: Add configuration switches to Core_main.py
4. **Week 4**: Integration testing and performance validation

### Production Migration Plan
1. **Phase A**: Deploy with persistent pool disabled by default
2. **Phase B**: Enable persistent pool with fallback option
3. **Phase C**: Make persistent pool default with legacy option
4. **Phase D**: Remove legacy implementation after validation period

### Rollback Procedures
- Environment variable to disable persistent pool
- Automatic fallback on worker pool initialization failure
- Preserve existing implementation as backup
- Clear error messages indicating fallback usage

This integration contract ensures the worker pool enhancement integrates seamlessly with existing systems while providing clear upgrade paths and safety mechanisms.