# Parallel Processing Implementation - Quick Start Guide

## Overview

This guide provides step-by-step validation scenarios for the parallel processing feature (002-fix-asyncronous-multiple). It covers setup, basic usage, advanced scenarios, and troubleshooting.

## Prerequisites

### System Requirements
- Python 3.12+ with Poetry package management
- Microsoft Edge browser (latest version)
- Minimum 8GB RAM for parallel processing
- 4+ CPU cores recommended for optimal performance

### Environment Setup
```bash
# Ensure in EXPERIMENTAL subproject
cd EXPERIMENTAL/

# Install/update dependencies
poetry install

# Verify Edge driver
poetry run python -c "from selenium import webdriver; from selenium.webdriver.edge.service import Service; print('Edge driver OK')"
```

### Test Data Preparation
```bash
# Create test data directory
mkdir -p data/test_parallel/

# Copy sample PO data (if available)
cp ../data/sample_documents/sample_pos.csv data/test_parallel/

# Or create minimal test data
echo "po_number,supplier,url,amount" > data/test_parallel/test_pos.csv
echo "PO-001,Supplier A,https://example.com/po1,1000.00" >> data/test_parallel/test_pos.csv
echo "PO-002,Supplier B,https://example.com/po2,2000.00" >> data/test_parallel/test_pos.csv
echo "PO-003,Supplier C,https://example.com/po3,1500.00" >> data/test_parallel/test_pos.csv
```

## Validation Scenarios

### Scenario 1: Basic Sequential Processing (Baseline)

**Purpose**: Validate existing functionality remains unchanged

```python
# test_sequential_baseline.py
from core.main import MainApp
from core.headless_config import HeadlessConfiguration

def test_sequential_processing():
    """Test single PO processing (existing functionality)"""
    
    # Initialize with parallel processing disabled
    config = HeadlessConfiguration(headless=True)
    app = MainApp(
        headless_config=config,
        enable_parallel=False  # Explicitly disable
    )
    
    # Test single PO
    po_data = {
        "po_number": "TEST-001",
        "supplier": "Test Supplier",
        "url": "https://example.com/po",
        "amount": 1000.00
    }
    
    result = app.process_single_po(po_data)
    print(f"Sequential processing result: {result}")
    
    # Test multiple POs sequentially
    po_list = [
        {"po_number": "TEST-001", "supplier": "Supplier A", "url": "https://example.com/po1", "amount": 1000.00},
        {"po_number": "TEST-002", "supplier": "Supplier B", "url": "https://example.com/po2", "amount": 2000.00}
    ]
    
    success_count, failed_count = app._process_po_entries(po_list)
    print(f"Sequential batch: {success_count} success, {failed_count} failed")

if __name__ == "__main__":
    test_sequential_processing()
```

**Expected Results**:
- Single PO processing works identically to before
- Multiple POs processed one by one
- No parallel workers created
- Existing logs and download structure preserved

**Run Test**:
```bash
poetry run python test_sequential_baseline.py
```

### Scenario 2: Basic Parallel Processing

**Purpose**: Validate parallel processing with minimal configuration

```python
# test_parallel_basic.py
from core.main import MainApp
from core.headless_config import HeadlessConfiguration
import time

def test_parallel_processing():
    """Test basic parallel processing functionality"""
    
    # Initialize with parallel processing enabled
    config = HeadlessConfiguration(headless=True)
    app = MainApp(
        headless_config=config,
        enable_parallel=True,
        max_workers=2  # Start with 2 workers
    )
    
    # Prepare test PO list
    po_list = [
        {"po_number": "PARALLEL-001", "supplier": "Supplier A", "url": "https://example.com/po1", "amount": 1000.00},
        {"po_number": "PARALLEL-002", "supplier": "Supplier B", "url": "https://example.com/po2", "amount": 2000.00},
        {"po_number": "PARALLEL-003", "supplier": "Supplier C", "url": "https://example.com/po3", "amount": 1500.00},
        {"po_number": "PARALLEL-004", "supplier": "Supplier D", "url": "https://example.com/po4", "amount": 2500.00}
    ]
    
    print(f"Processing {len(po_list)} POs with {app.max_workers} workers")
    start_time = time.time()
    
    success_count, failed_count = app._process_po_entries(po_list)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"Parallel processing completed in {duration:.2f} seconds")
    print(f"Results: {success_count} success, {failed_count} failed")
    print(f"Throughput: {len(po_list)/duration:.2f} POs/second")

if __name__ == "__main__":
    test_parallel_processing()
```

**Expected Results**:
- Multiple workers created (2 in this case)
- POs processed concurrently
- Processing time significantly reduced vs sequential
- Separate browser profiles per worker
- Consolidated results returned

**Run Test**:
```bash
poetry run python test_parallel_basic.py
```

### Scenario 3: Profile Isolation Validation

**Purpose**: Validate that workers use isolated browser profiles

```python
# test_profile_isolation.py
from workers.profile_manager import ProfileManager
from workers.worker_pool import WorkerPool
import tempfile
import os

def test_profile_isolation():
    """Test that each worker gets an isolated browser profile"""
    
    # Test ProfileManager directly
    profile_manager = ProfileManager(base_profile_path="./browser_profile")
    
    # Create profiles for multiple workers
    worker_profiles = {}
    for i in range(3):
        worker_id = f"worker_{i}"
        profile_path = profile_manager.create_profile(worker_id)
        worker_profiles[worker_id] = profile_path
        
        print(f"Worker {worker_id} profile: {profile_path}")
        
        # Validate profile exists and is isolated
        assert os.path.exists(profile_path), f"Profile not created for {worker_id}"
        assert profile_path != profile_manager.base_profile_path, f"Profile not isolated for {worker_id}"
    
    # Validate profiles are unique
    profile_paths = list(worker_profiles.values())
    assert len(set(profile_paths)) == len(profile_paths), "Profiles not unique"
    
    # Test cleanup
    for worker_id, profile_path in worker_profiles.items():
        profile_manager.cleanup_profile(worker_id)
        assert not os.path.exists(profile_path), f"Profile not cleaned up for {worker_id}"
    
    print("Profile isolation validation passed")

def test_concurrent_profile_access():
    """Test concurrent profile creation and access"""
    
    from concurrent.futures import ThreadPoolExecutor
    import threading
    
    profile_manager = ProfileManager(base_profile_path="./browser_profile")
    created_profiles = []
    lock = threading.Lock()
    
    def create_worker_profile(worker_id):
        profile_path = profile_manager.create_profile(f"concurrent_worker_{worker_id}")
        with lock:
            created_profiles.append(profile_path)
        return profile_path
    
    # Create profiles concurrently
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(create_worker_profile, i) for i in range(4)]
        profiles = [future.result() for future in futures]
    
    # Validate all profiles created successfully
    assert len(profiles) == 4, "Not all profiles created"
    assert len(set(profiles)) == 4, "Profiles not unique in concurrent creation"
    
    # Cleanup
    for i, profile_path in enumerate(profiles):
        profile_manager.cleanup_profile(f"concurrent_worker_{i}")
    
    print("Concurrent profile access validation passed")

if __name__ == "__main__":
    test_profile_isolation()
    test_concurrent_profile_access()
```

**Expected Results**:
- Each worker gets unique temporary profile directory
- Profiles are isolated from base profile
- Concurrent profile creation works safely
- Cleanup removes all temporary profiles

**Run Test**:
```bash
poetry run python test_profile_isolation.py
```

### Scenario 4: Error Handling and Fallback

**Purpose**: Validate graceful handling of parallel processing failures

```python
# test_error_handling.py
from core.main import MainApp
from core.headless_config import HeadlessConfiguration
from workers.exceptions import ParallelProcessingError

def test_parallel_fallback():
    """Test fallback to sequential processing on parallel failure"""
    
    config = HeadlessConfiguration(headless=True)
    app = MainApp(
        headless_config=config,
        enable_parallel=True,
        max_workers=8  # Deliberately high to potentially trigger resource limits
    )
    
    # Mix of valid and problematic POs
    po_list = [
        {"po_number": "VALID-001", "supplier": "Good Supplier", "url": "https://example.com/po1", "amount": 1000.00},
        {"po_number": "INVALID-URL", "supplier": "Bad Supplier", "url": "invalid-url", "amount": 2000.00},
        {"po_number": "VALID-002", "supplier": "Good Supplier", "url": "https://example.com/po2", "amount": 1500.00},
        {"po_number": "TIMEOUT-TEST", "supplier": "Slow Supplier", "url": "https://httpbin.org/delay/10", "amount": 2500.00}
    ]
    
    try:
        success_count, failed_count = app._process_po_entries(po_list)
        print(f"Error handling test: {success_count} success, {failed_count} failed")
        
        # Should complete despite errors
        assert success_count + failed_count == len(po_list), "Not all POs accounted for"
        
    except Exception as e:
        print(f"Unexpected error (should be handled gracefully): {e}")
        raise

def test_resource_exhaustion():
    """Test behavior when system resources are exhausted"""
    
    # Test with more workers than reasonable for system
    config = HeadlessConfiguration(headless=True)
    app = MainApp(
        headless_config=config,
        enable_parallel=True,
        max_workers=16  # High worker count
    )
    
    # Large PO list
    po_list = [
        {"po_number": f"STRESS-{i:03d}", "supplier": f"Supplier {i}", 
         "url": f"https://example.com/po{i}", "amount": 1000.00 + i}
        for i in range(20)
    ]
    
    try:
        success_count, failed_count = app._process_po_entries(po_list)
        print(f"Resource stress test: {success_count} success, {failed_count} failed")
        
    except Exception as e:
        print(f"Resource exhaustion handled: {e}")
        # Should not crash the application

if __name__ == "__main__":
    test_parallel_fallback()
    test_resource_exhaustion()
```

**Expected Results**:
- Invalid POs handled gracefully without stopping processing
- Resource exhaustion triggers fallback mechanisms
- Application remains stable under stress
- Partial results returned even with failures

**Run Test**:
```bash
poetry run python test_error_handling.py
```

### Scenario 5: Performance Measurement

**Purpose**: Measure and validate performance improvements

```python
# test_performance.py
from core.main import MainApp
from core.headless_config import HeadlessConfiguration
import time
import statistics

def measure_processing_time(app, po_list, runs=3):
    """Measure processing time across multiple runs"""
    times = []
    
    for run in range(runs):
        print(f"Run {run + 1}/{runs}")
        start_time = time.time()
        success_count, failed_count = app._process_po_entries(po_list)
        end_time = time.time()
        
        duration = end_time - start_time
        times.append(duration)
        print(f"  Duration: {duration:.2f}s, Success: {success_count}, Failed: {failed_count}")
    
    return {
        'mean': statistics.mean(times),
        'stdev': statistics.stdev(times) if len(times) > 1 else 0,
        'min': min(times),
        'max': max(times)
    }

def test_performance_comparison():
    """Compare sequential vs parallel processing performance"""
    
    # Prepare test data
    po_list = [
        {"po_number": f"PERF-{i:03d}", "supplier": f"Supplier {i}", 
         "url": f"https://example.com/po{i}", "amount": 1000.00 + i}
        for i in range(8)  # 8 POs for meaningful comparison
    ]
    
    config = HeadlessConfiguration(headless=True)
    
    # Test sequential processing
    print("Testing Sequential Processing...")
    sequential_app = MainApp(
        headless_config=config,
        enable_parallel=False
    )
    sequential_stats = measure_processing_time(sequential_app, po_list)
    
    # Test parallel processing (2 workers)
    print("\nTesting Parallel Processing (2 workers)...")
    parallel_app_2 = MainApp(
        headless_config=config,
        enable_parallel=True,
        max_workers=2
    )
    parallel_stats_2 = measure_processing_time(parallel_app_2, po_list)
    
    # Test parallel processing (4 workers)
    print("\nTesting Parallel Processing (4 workers)...")
    parallel_app_4 = MainApp(
        headless_config=config,
        enable_parallel=True,
        max_workers=4
    )
    parallel_stats_4 = measure_processing_time(parallel_app_4, po_list)
    
    # Calculate improvements
    improvement_2w = sequential_stats['mean'] / parallel_stats_2['mean']
    improvement_4w = sequential_stats['mean'] / parallel_stats_4['mean']
    
    print(f"\n=== Performance Results ===")
    print(f"Sequential:     {sequential_stats['mean']:.2f}s ± {sequential_stats['stdev']:.2f}s")
    print(f"Parallel (2w):  {parallel_stats_2['mean']:.2f}s ± {parallel_stats_2['stdev']:.2f}s")
    print(f"Parallel (4w):  {parallel_stats_4['mean']:.2f}s ± {parallel_stats_4['stdev']:.2f}s")
    print(f"\nSpeedup with 2 workers: {improvement_2w:.2f}x")
    print(f"Speedup with 4 workers: {improvement_4w:.2f}x")
    
    # Validate performance targets
    assert improvement_2w > 1.5, f"2-worker speedup too low: {improvement_2w:.2f}x"
    assert improvement_4w > 2.0, f"4-worker speedup too low: {improvement_4w:.2f}x"
    
    print("\nPerformance targets met!")

if __name__ == "__main__":
    test_performance_comparison()
```

**Expected Results**:
- Parallel processing shows 1.5x+ speedup with 2 workers
- 4-worker configuration shows 2.0x+ speedup
- Performance consistent across multiple runs
- Meets or exceeds target performance improvements

**Run Test**:
```bash
poetry run python test_performance.py
```

### Scenario 6: Integration with Existing Workflow

**Purpose**: Validate integration with existing EXPERIMENTAL workflow

```python
# test_integration.py
from core.main import MainApp
from core.headless_config import HeadlessConfiguration
import os

def test_backward_compatibility():
    """Test that existing code still works unchanged"""
    
    # Test existing MainApp initialization (without parallel parameters)
    app_legacy = MainApp()
    assert hasattr(app_legacy, 'process_single_po'), "Legacy method missing"
    
    # Test with old-style configuration
    config = HeadlessConfiguration(headless=False)
    app_configured = MainApp(headless_config=config)
    
    # Should default to sequential processing
    po_data = {
        "po_number": "LEGACY-001",
        "supplier": "Legacy Supplier",
        "url": "https://example.com/legacy",
        "amount": 1000.00
    }
    
    # This should work exactly as before
    result = app_configured.process_single_po(po_data)
    print(f"Legacy integration test: {result}")

def test_download_structure():
    """Test that download directory structure is preserved"""
    
    config = HeadlessConfiguration(headless=True)
    app = MainApp(
        headless_config=config,
        enable_parallel=True,
        max_workers=2
    )
    
    po_list = [
        {"po_number": "DOWNLOAD-001", "supplier": "Supplier A", "url": "https://example.com/po1", "amount": 1000.00},
        {"po_number": "DOWNLOAD-002", "supplier": "Supplier B", "url": "https://example.com/po2", "amount": 2000.00}
    ]
    
    # Clear download directory first
    download_dir = "../download"
    if os.path.exists(download_dir):
        for file in os.listdir(download_dir):
            os.remove(os.path.join(download_dir, file))
    
    success_count, failed_count = app._process_po_entries(po_list)
    
    # Check that download structure is maintained
    # (This would be specific to actual download implementation)
    print(f"Download structure test completed: {success_count} success, {failed_count} failed")

def test_logging_integration():
    """Test that logging works correctly with parallel processing"""
    
    config = HeadlessConfiguration(headless=True)
    app = MainApp(
        headless_config=config,
        enable_parallel=True,
        max_workers=2
    )
    
    po_list = [
        {"po_number": "LOG-001", "supplier": "Supplier A", "url": "https://example.com/po1", "amount": 1000.00},
        {"po_number": "LOG-002", "supplier": "Supplier B", "url": "https://example.com/po2", "amount": 2000.00}
    ]
    
    # Process with logging enabled
    success_count, failed_count = app._process_po_entries(po_list)
    
    # Logs should contain parallel processing information
    # (Implementation would check actual log files)
    print(f"Logging test completed: {success_count} success, {failed_count} failed")

if __name__ == "__main__":
    test_backward_compatibility()
    test_download_structure()
    test_logging_integration()
```

**Expected Results**:
- Existing code works without modification
- Download directory structure preserved
- Logging includes parallel processing details
- No breaking changes to public interfaces

**Run Test**:
```bash
poetry run python test_integration.py
```

## Comprehensive Test Suite

### Run All Tests
```bash
# Create comprehensive test runner
cat > run_all_tests.py << 'EOF'
#!/usr/bin/env python3
"""
Comprehensive test suite for parallel processing implementation
"""

import subprocess
import sys
import time

def run_test(test_name, test_file):
    """Run a single test and report results"""
    print(f"\n{'='*60}")
    print(f"Running {test_name}")
    print(f"{'='*60}")
    
    start_time = time.time()
    try:
        result = subprocess.run(
            ["poetry", "run", "python", test_file],
            capture_output=True,
            text=True,
            check=False
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ {test_name} PASSED ({duration:.2f}s)")
            print(result.stdout)
            return True
        else:
            print(f"❌ {test_name} FAILED ({duration:.2f}s)")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except Exception as e:
        duration = time.time() - start_time
        print(f"💥 {test_name} ERROR ({duration:.2f}s): {e}")
        return False

def main():
    """Run all validation tests"""
    tests = [
        ("Sequential Baseline", "test_sequential_baseline.py"),
        ("Basic Parallel Processing", "test_parallel_basic.py"),
        ("Profile Isolation", "test_profile_isolation.py"),
        ("Error Handling", "test_error_handling.py"),
        ("Performance Measurement", "test_performance.py"),
        ("Integration", "test_integration.py")
    ]
    
    print("Parallel Processing Implementation - Comprehensive Test Suite")
    print(f"Running {len(tests)} test scenarios...")
    
    results = []
    start_time = time.time()
    
    for test_name, test_file in tests:
        passed = run_test(test_name, test_file)
        results.append((test_name, passed))
    
    total_duration = time.time() - start_time
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed_count}/{total_count} tests passed")
    print(f"Total time: {total_duration:.2f} seconds")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed! Parallel processing implementation ready.")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed. Review implementation.")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

# Make executable
chmod +x run_all_tests.py

# Run all tests
poetry run python run_all_tests.py
```

## Troubleshooting

### Common Issues

#### 1. Profile Creation Failures
```bash
# Check base profile exists
ls -la ./browser_profile/

# Check permissions
ls -la /tmp/  # Should be writable

# Test profile manager manually
poetry run python -c "
from workers.profile_manager import ProfileManager
pm = ProfileManager('./browser_profile')
profile = pm.create_profile('test')
print(f'Created: {profile}')
pm.cleanup_profile('test')
print('Cleaned up successfully')
"
```

#### 2. Worker Pool Startup Issues
```bash
# Check system resources
free -h  # Memory usage
nproc    # CPU cores
ps aux | grep python  # Existing Python processes

# Test worker pool manually
poetry run python -c "
from workers.worker_pool import WorkerPool
pool = WorkerPool(max_workers=2)
pool.start()
print('Pool started')
pool.stop()
print('Pool stopped')
"
```

#### 3. Performance Below Expectations
```bash
# Monitor system during processing
htop &  # or top
iostat 1 &  # Monitor I/O

# Run single test with verbose logging
PYTHONPATH=. poetry run python test_performance.py

# Profile the application
poetry run python -m cProfile -o profile.stats test_parallel_basic.py
poetry run python -c "import pstats; pstats.Stats('profile.stats').sort_stats('time').print_stats(10)"
```

### Debug Mode

Enable debug logging for detailed troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Add to test files for verbose output
import structlog
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
```

### Environment Validation

```bash
# Verify complete environment setup
poetry run python -c "
import sys
print(f'Python: {sys.version}')

from selenium import webdriver
from selenium.webdriver.edge.service import Service
print('Selenium: OK')

import multiprocessing
print(f'CPU cores: {multiprocessing.cpu_count()}')

import tempfile
temp_dir = tempfile.mkdtemp()
print(f'Temp directory: {temp_dir}')

import psutil
print(f'Available memory: {psutil.virtual_memory().available / (1024**3):.1f} GB')
"
```

## Next Steps

After successful validation:

1. **Integration Testing**: Test with real Coupa environment and data
2. **Performance Tuning**: Optimize worker count and timeouts for production
3. **Monitoring Setup**: Implement production monitoring and alerting
4. **Documentation Update**: Update main project documentation with parallel processing features
5. **Rollout Planning**: Plan gradual rollout strategy with fallback options

---

*This guide ensures comprehensive validation of parallel processing implementation before production deployment*