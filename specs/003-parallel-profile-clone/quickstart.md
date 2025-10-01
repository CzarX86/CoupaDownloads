# Quick Start: Parallel Profile Management

This guide demonstrates how to set up and test the parallel profile management system.

## Prerequisites

1. **Python Environment**: Python 3.12 with Poetry
2. **Browser**: Microsoft Edge installed
3. **Base Profile**: Default Edge profile with valid Coupa session
4. **Test Environment**: Access to Coupa test/development environment

## Basic Setup

### 1. Install Dependencies
```bash
cd /Users/juliocezar/Dev/work/CoupaDownloads
poetry install
```

### 2. Configure Base Profile Path
```python
# Example configuration - adjust paths for your system
import platform
from pathlib import Path

if platform.system() == "Darwin":  # macOS
    base_profile = Path.home() / "Library/Application Support/Microsoft Edge/Default"
elif platform.system() == "Windows":
    base_profile = Path.home() / "AppData/Local/Microsoft/Edge/User Data/Default"
else:
    raise RuntimeError("Unsupported platform")

print(f"Base profile path: {base_profile}")
assert base_profile.exists(), f"Base profile not found at {base_profile}"
```

### 3. Verify Base Profile
```python
# Check that base profile contains essential files
required_files = ["Preferences", "Local State"]
for file_name in required_files:
    file_path = base_profile / file_name
    assert file_path.exists(), f"Required file missing: {file_path}"

print("✓ Base profile verification passed")
```

## Simple Profile Manager Usage

### 1. Create ProfileManager Instance
```python
from pathlib import Path
from EXPERIMENTAL.workers.profile_manager import ProfileManager
from specs.parallel_profile_clone.contracts.profile_manager_contract import (
    VerificationConfig, VerificationMethod, RetryConfig
)

# Configure verification
verification_config = VerificationConfig(
    enabled_methods=[
        VerificationMethod.CAPABILITY_CHECK,
        VerificationMethod.AUTH_CHECK
    ],
    auth_check_url="https://your-coupa-instance.com/api/session",
    retry_config=RetryConfig(max_attempts=2, base_delay=1.0)
)

# Initialize manager
profile_manager = ProfileManager(
    base_profile_path=base_profile,
    max_concurrent_clones=3,
    verification_config=verification_config
)
```

### 2. Create Worker Profiles
```python
# Create profile for first worker (uses base profile)
worker1_profile = profile_manager.create_worker_profile(worker_id=1)
print(f"Worker 1 profile: {worker1_profile.profile_type} at {worker1_profile.profile_path}")

# Create profile for second worker (creates clone)
worker2_profile = profile_manager.create_worker_profile(worker_id=2)
print(f"Worker 2 profile: {worker2_profile.profile_type} at {worker2_profile.profile_path}")

# Create profile for third worker (creates clone)
worker3_profile = profile_manager.create_worker_profile(worker_id=3)
print(f"Worker 3 profile: {worker3_profile.profile_type} at {worker3_profile.profile_path}")
```

### 3. Verify Profiles
```python
# Verify each profile
profiles = [worker1_profile, worker2_profile, worker3_profile]

for profile in profiles:
    print(f"\nVerifying worker {profile.worker_id}...")
    verification_result = profile_manager.verify_profile(profile)
    
    if verification_result.is_success():
        print(f"✓ Worker {profile.worker_id} verification passed")
        print(f"  Duration: {verification_result.get_duration():.2f}s")
    else:
        print(f"✗ Worker {profile.worker_id} verification failed")
        print(f"  Failed methods: {verification_result.get_failed_methods()}")
        print(f"  Error: {verification_result.error_details}")
```

### 4. Cleanup Profiles
```python
# Cleanup all profiles
for profile in profiles:
    profile_manager.cleanup_profile(profile)
    print(f"✓ Cleaned up worker {profile.worker_id} profile")

# Shutdown manager
profile_manager.shutdown()
print("✓ ProfileManager shutdown complete")
```

## Integration with Worker Pool

### 1. Create Worker Pool with Profile Management
```python
from EXPERIMENTAL.workers.worker_pool import ProfileAwareWorkerPool
from specs.parallel_profile_clone.contracts.worker_integration_contract import WorkerConfig

# Configure workers
worker_configs = [
    WorkerConfig(worker_id=1, headless=False, verification_required=True),
    WorkerConfig(worker_id=2, headless=True, verification_required=True),
    WorkerConfig(worker_id=3, headless=True, verification_required=True),
]

# Create worker pool
worker_pool = ProfileAwareWorkerPool(
    max_workers=3,
    profile_manager=profile_manager,
    startup_timeout=120.0
)
```

### 2. Start All Workers
```python
# Start workers with profile management
startup_results = worker_pool.start_all_workers(worker_configs)

# Check results
for result in startup_results:
    if result.success:
        print(f"✓ Worker {result.worker_id} started successfully")
        print(f"  Profile: {result.profile.profile_type}")
        print(f"  Verification: {result.verification_result.overall_status}")
    else:
        print(f"✗ Worker {result.worker_id} failed to start")
        print(f"  Error: {result.error_message}")
```

### 3. Monitor Worker Status
```python
# Get status of all workers
worker_statuses = worker_pool.get_all_worker_status()

for status in worker_statuses:
    print(f"Worker {status['worker_id']}:")
    print(f"  Status: {status['status']}")
    print(f"  Profile: {status['profile_type']} at {status['profile_path']}")
    print(f"  Last verification: {status['last_verification']}")
```

### 4. Re-verify Profiles
```python
# Re-verify all profiles
verification_results = worker_pool.verify_all_profiles()

for worker_id, result in verification_results.items():
    if result.is_success():
        print(f"✓ Worker {worker_id} re-verification passed")
    else:
        print(f"✗ Worker {worker_id} re-verification failed")
        # Restart worker with new profile if needed
        restart_result = worker_pool.restart_worker(worker_id, new_profile=True)
        print(f"  Restart result: {restart_result.success}")
```

### 5. Cleanup and Shutdown
```python
# Stop all workers and cleanup profiles
worker_pool.stop_all_workers(cleanup_profiles=True)
print("✓ All workers stopped and profiles cleaned up")
```

## Testing Scenarios

### Scenario 1: Single Worker with Base Profile
```python
def test_single_worker_base_profile():
    """Test single worker using base profile directly"""
    profile = profile_manager.create_worker_profile(worker_id=1)
    assert profile.profile_type == ProfileType.BASE
    assert profile.profile_path == base_profile
    
    verification = profile_manager.verify_profile(profile)
    assert verification.is_success()
    
    # No cleanup needed for base profile
    print("✓ Single worker test passed")
```

### Scenario 2: Multiple Workers with Cloned Profiles
```python
def test_multiple_workers_cloned_profiles():
    """Test multiple workers with independent cloned profiles"""
    profiles = []
    
    # Create 3 workers
    for worker_id in range(1, 4):
        profile = profile_manager.create_worker_profile(worker_id)
        profiles.append(profile)
        
        if worker_id == 1:
            assert profile.profile_type == ProfileType.BASE
        else:
            assert profile.profile_type == ProfileType.CLONE
            assert profile.profile_path != base_profile
    
    # Verify all profiles
    for profile in profiles:
        verification = profile_manager.verify_profile(profile)
        assert verification.is_success()
    
    # Cleanup cloned profiles
    for profile in profiles:
        if profile.profile_type == ProfileType.CLONE:
            profile_manager.cleanup_profile(profile)
    
    print("✓ Multiple workers test passed")
```

### Scenario 3: Profile Verification Failure and Recovery
```python
def test_verification_failure_recovery():
    """Test profile verification failure and recovery"""
    profile = profile_manager.create_worker_profile(worker_id=2)
    
    # Simulate verification failure by corrupting profile
    critical_file = profile.profile_path / "Preferences"
    if critical_file.exists():
        critical_file.unlink()  # Remove critical file
    
    # First verification should fail
    verification1 = profile_manager.verify_profile(profile)
    assert not verification1.is_success()
    
    # Cleanup and recreate profile
    profile_manager.cleanup_profile(profile)
    profile_new = profile_manager.create_worker_profile(worker_id=2)
    
    # Second verification should succeed
    verification2 = profile_manager.verify_profile(profile_new)
    assert verification2.is_success()
    
    profile_manager.cleanup_profile(profile_new)
    print("✓ Verification failure recovery test passed")
```

## Troubleshooting

### Common Issues

1. **Base Profile Locked**
   - Error: `ProfileLockedException`
   - Solution: Close all Edge browser instances before starting

2. **Insufficient Disk Space**
   - Error: `InsufficientSpaceException`
   - Solution: Free up disk space or configure smaller temp directory

3. **Permission Denied**
   - Error: `PermissionDeniedException`
   - Solution: Run with appropriate permissions or check profile directory ownership

4. **Authentication Verification Failed**
   - Error: `AuthenticationFailedException`
   - Solution: Ensure base profile has valid Coupa session and check network connectivity

### Debugging Commands

```python
# Check base profile status
status = profile_manager.get_base_profile_status()
print(f"Base profile status: {status}")

# Get performance metrics
metrics = worker_pool.get_performance_metrics()
print(f"Performance metrics: {metrics}")

# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Next Steps

1. **Scale Testing**: Test with higher worker counts (5-10 workers)
2. **Performance Tuning**: Optimize profile cloning for your hardware
3. **Integration**: Integrate with existing Coupa download workflows
4. **Monitoring**: Add metrics collection for production use
5. **Error Handling**: Implement application-specific error recovery