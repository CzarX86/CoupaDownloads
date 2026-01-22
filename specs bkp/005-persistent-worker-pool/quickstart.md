# Quick Start: Persistent Worker Pool Implementation

## Development Environment Setup

### Prerequisites Check
```bash
# Verify Python version
python --version  # Should be 3.12+

# Verify Poetry installation  
poetry --version  # Should be 1.8+

# Check system resources
python -c "import psutil; print(f'RAM: {psutil.virtual_memory().total / (1024**3):.1f}GB')"
# Should be 4GB+ for optimal performance
```

### Environment Activation
```bash
cd /Users/juliocezar/Dev/work/CoupaDownloads
poetry install                    # Install all dependencies
poetry shell                     # Activate virtual environment
```

## Quick Development Workflow

### 1. Current Implementation Status
The implementation is partially complete with functional models and services:

```bash
# Test current implementation status
python src/test_current_implementation.py

# Expected output:
# ✅ Models import correctly
# ✅ Services initialize properly  
# ✅ Basic functionality works
# ❌ Integration tests fail (expected - missing worker pool)
```

### 2. Implementation Location
All new code goes in the `EXPERIMENTAL/` subproject:

```bash
# Navigate to implementation directory
cd EXPERIMENTAL/

# Directory structure should exist:
ls -la
# Should show: workers/, core/, corelib/, integration/ directories
```

### 3. Core Development Pattern

#### A. Worker Pool Implementation
```python
# EXPERIMENTAL/workers/persistent_pool.py
from src.models.worker import Worker, WorkerStatus
from src.services.task_queue import TaskQueue
from src.services.memory_monitor import MemoryMonitor

class PersistentWorkerPool:
    """Main orchestrator class"""
    def __init__(self, config: PoolConfig):
        self.config = config
        self.workers: List[Worker] = []
        self.task_queue = TaskQueue()
        self.memory_monitor = MemoryMonitor()
        
    def start(self) -> None:
        """Start all worker processes"""
        # Implementation here
        
    def submit_task(self, task: POTask) -> TaskHandle:
        """Submit PO task for processing"""
        # Implementation here
```

#### B. Worker Process Implementation  
```python
# EXPERIMENTAL/workers/worker_process.py
from src.models.browser_session import BrowserSession
from src.models.po_task import POTask

class WorkerProcess:
    """Individual worker process"""
    def __init__(self, worker_id: str, profile_path: str):
        self.worker_id = worker_id
        self.profile_path = profile_path
        self.browser_session = None
        
    def process_po(self, task: POTask) -> POResult:
        """Process single PO task"""
        # Implementation here
```

### 4. Integration with Existing System

#### Core_main.py Enhancement
```python
# Add to src/Core_main.py
def main() -> None:
    """Enhanced main with worker pool option"""
    try:
        if should_use_worker_pool():
            from EXPERIMENTAL.integration.main_adapter import process_with_pool
            return process_with_pool()
        else:
            # Existing logic unchanged
            return existing_main_logic()
    except Exception as e:
        # Existing error handling
        handle_error(e)
```

### 5. Testing Strategy

#### Unit Tests
```bash
# Run existing tests (should pass)
pytest tests/ -v

# Test specific models/services  
pytest tests/ -k "test_worker or test_profile"

# Test integration (will fail until implementation complete)
pytest tests/ -k "integration" --tb=short
```

#### Integration Testing
```python
# EXPERIMENTAL/tests/test_integration.py
def test_worker_pool_basic_flow():
    """Test basic worker pool functionality"""
    pool = PersistentWorkerPool(config)
    pool.start()
    
    task = POTask(po_number="PO123")
    handle = pool.submit_task(task)
    
    result = handle.wait_for_completion(timeout=60)
    assert result.success
    
    pool.shutdown()
```

## Implementation Checklist

### Phase 1: Core Worker Pool (Week 1)
- [ ] `PersistentWorkerPool` class with lifecycle management
- [ ] `WorkerProcess` with browser session management  
- [ ] `BrowserSession` with tab-based processing
- [ ] Basic task submission and result collection
- [ ] Memory monitoring integration

### Phase 2: Process Management (Week 2)  
- [ ] Worker process spawning and monitoring
- [ ] Profile cloning and isolation
- [ ] Graceful shutdown handling
- [ ] Error recovery and restart logic
- [ ] Resource cleanup procedures

### Phase 3: Integration (Week 3)
- [ ] CSV to POTask conversion adapter
- [ ] Result aggregation and reporting
- [ ] Core_main.py integration points
- [ ] Configuration management
- [ ] Backward compatibility layer

### Phase 4: Testing & Validation (Week 4)
- [ ] Unit tests for all new components
- [ ] Integration tests with existing system
- [ ] Performance benchmarking
- [ ] Memory usage validation
- [ ] Error handling verification

## Development Tips

### 1. Leverage Existing Infrastructure
```python
# Use existing models and services
from src.models.worker import Worker
from src.services.profile_manager import ProfileManager

# Don't recreate - extend and integrate
class EnhancedProfileManager(ProfileManager):
    """Extended with worker pool features"""
```

### 2. Maintain Backward Compatibility
```python
# Always provide fallback to existing implementation
def process_pos(use_worker_pool: bool = True):
    if use_worker_pool:
        try:
            return new_worker_pool_processing()
        except Exception as e:
            log.warning(f"Worker pool failed: {e}, falling back")
            return existing_processing()
    else:
        return existing_processing()
```

### 3. Debugging and Monitoring
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Monitor memory usage during development
python -c "
from src.services.memory_monitor import MemoryMonitor
monitor = MemoryMonitor()
print(f'Memory: {monitor.get_memory_usage():.1f}%')
"

# Profile execution for performance optimization
python -m cProfile -o profile.stats your_test_script.py
```

### 4. Error Handling Patterns
```python
# Follow existing error handling patterns
try:
    result = worker.process_po(task)
except AuthenticationError:
    # Retry with session refresh
    worker.browser_session.authenticate()
    result = worker.process_po(task)
except NetworkError as e:
    # Use existing retry logic
    return retry_with_backoff(lambda: worker.process_po(task))
```

## Quick Validation Commands

### Verify Implementation Progress
```bash
# Check if core classes exist and import
python -c "
from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool
from EXPERIMENTAL.workers.worker_process import WorkerProcess
print('✅ Core classes import successfully')
"

# Test basic instantiation  
python -c "
from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool
pool = PersistentWorkerPool(worker_count=2, headless_mode=True)
print('✅ Worker pool instantiates correctly')
"

# Verify integration points
python -c "
from EXPERIMENTAL.integration.main_adapter import process_with_pool
print('✅ Integration adapter available')
"
```

### Performance Baseline
```bash
# Measure current implementation performance
time python src/Core_main.py --csv data/sample_documents/small_test.csv

# Measure worker pool performance (after implementation)
time python src/Core_main.py --csv data/sample_documents/small_test.csv --use-pool

# Compare memory usage
python tools/memory_profiler.py src/Core_main.py
```

This quick start guide provides the essential information needed to begin implementing the persistent worker pool feature while leveraging existing infrastructure and maintaining backward compatibility.