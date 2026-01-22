# Research: Incremental CSV Handler Implementation

## Overview
Research findings for implementing safe, incremental CSV persistence in CoupaDownloads with concurrent worker support and fault tolerance.

## Technical Decisions

### CSV Write Serialization Strategy
**Decision**: Implement thread-safe write queue using `queue.Queue` with single writer thread  
**Rationale**: 
- Prevents file corruption from concurrent writes
- Simple implementation without complex file locking
- Maintains write order for audit purposes
- Works across multiprocessing boundaries with queue serialization

**Alternatives considered**:
- File locking (`fcntl.flock`): Platform-dependent, deadlock risks
- Atomic writes (temp file + rename): Good but doesn't solve concurrent access
- Worker partitioning: Complex row ownership, reduces parallelism benefits

### CSV Library Choice
**Decision**: Continue using `pandas` with custom persistence wrapper  
**Rationale**:
- Already integrated in project dependencies
- Excellent CSV manipulation and UTF-8 handling
- DataFrame operations for filtering unprocessed POs
- Built-in validation and error handling

**Alternatives considered**:
- `csv` module: Lower level, more complex for data manipulation
- `polars`: Faster but adds new dependency and learning curve

### Backup Strategy Implementation  
**Decision**: Timestamped backups before each session with configurable retention  
**Rationale**:
- Session-level backups provide recovery points without excessive overhead
- Timestamp naming allows easy identification of recovery points
- Configurable retention prevents disk space issues

**Alternatives considered**:
- Per-PO backups: Too frequent, performance impact
- Daily backups: Too infrequent, potential for significant data loss
- No backups: Violates fault tolerance requirements

### Resume Logic Implementation
**Decision**: Hybrid approach checking STATUS field and LAST_PROCESSED timestamp  
**Rationale**:
- STATUS != 'COMPLETED' catches interrupted processing
- Timestamp validation detects incomplete writes or corrupted data
- Provides robust recovery from various failure scenarios

**Alternatives considered**:
- STATUS-only: Misses timestamp-based corruption detection
- Timestamp-only: Complex date parsing, timezone issues
- External state file: Additional complexity, synchronization issues

### Error Handling Strategy
**Decision**: Retry with exponential backoff + graceful degradation  
**Rationale**:
- Handles transient file system issues (disk space, temporary locks)
- Exponential backoff prevents resource exhaustion
- Continue processing other POs maintains system availability
- Detailed logging provides debugging information

**Alternatives considered**:
- Immediate failure: Too brittle for production use
- Infinite retries: Risk of infinite loops
- Skip without logging: Poor debugging experience

### Performance Optimization
**Decision**: Batch validation + write-through caching for frequently accessed CSV metadata  
**Rationale**:
- Single CSV integrity check after each write (not per-field)
- In-memory cache of CSV structure reduces file I/O
- Write-through ensures cache consistency

**Alternatives considered**:
- Per-field validation: Too expensive for large files
- No validation: Doesn't meet integrity requirements
- Write-back caching: Risk of data loss on crashes

## Integration Points

### Worker Pool Integration
- Modify existing `WorkerPool` to inject `CSVHandler` instance
- Workers call `csv_handler.update_record()` after each PO completion
- Write queue handles serialization automatically

### Main Flow Integration  
- `Core_main.py` initializes `CSVHandler` with backup creation
- Sequential mode uses same `CSVHandler` interface (queue depth=1)
- Progress reporting hooks into CSV record counting

### Error Recovery Integration
- Startup checks for incomplete processing via `get_pending_pos()`
- Resume from interruption point automatically
- Operator visibility through structured logging

## Dependencies Analysis

### New Dependencies (None Required)
All required functionality available through existing project dependencies:
- `pandas`: CSV manipulation and I/O
- `multiprocessing.Queue`: Cross-process communication
- `threading.Queue`: Thread-safe write serialization  
- `structlog`: Error logging and audit trails
- `pathlib`: File system operations
- `datetime`: Timestamp generation

### Dependency Compatibility
- Python 3.12: All features available
- Poetry management: No conflicts with existing lock file
- Cross-platform: Works on macOS/Linux target platforms

## Risk Assessment

### Low Risk
- CSV corruption: Prevented by write serialization
- Performance degradation: Minimal overhead with queue design
- Integration complexity: Clean separation of concerns

### Medium Risk  
- Disk space management: Mitigated by backup retention policies
- Memory usage with large CSVs: Pandas memory optimization available

### Mitigation Strategies
- Backup cleanup: Implement retention policy (keep last N backups)
- Memory monitoring: Add CSV size checks and chunking if needed
- Performance monitoring: Log write operation timing for optimization

## Implementation Phases
1. **Core CSVHandler**: Basic read/write with validation
2. **Write Queue**: Thread-safe serialization layer  
3. **Backup System**: Session-based backup with retention
4. **Worker Integration**: Multiprocessing-safe interfaces
5. **Error Handling**: Retry logic and graceful degradation
6. **Testing**: Concurrent access and recovery scenarios