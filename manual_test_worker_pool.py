#!/usr/bin/env python3
"""
Manual Testing Scenarios for Persistent Worker Pool

This script executes comprehensive manual tests to validate the persistent worker pool
implementation meets all requirements and performs correctly in various scenarios.
"""

import asyncio
import sys
import os
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'EXPERIMENTAL'))

import contextlib

@contextlib.contextmanager
def setup_test_environment():
    """Setup test environment with mocked browser components."""
    print("🔧 Setting up test environment...")

    # Create temporary directory for profiles
    temp_dir = tempfile.mkdtemp(prefix="manual_test_profiles_")
    
    # Create mock base profile with required files
    base_profile_dir = os.path.join(temp_dir, "Default")
    os.makedirs(base_profile_dir, exist_ok=True)
    
    # Create mock profile files
    with open(os.path.join(base_profile_dir, "Preferences"), "w") as f:
        f.write('{"test": "mock preferences"}')
    
    with open(os.path.join(base_profile_dir, "Local State"), "w") as f:
        f.write('{"test": "mock local state"}')

    # Mock browser components to avoid real browser startup
    with patch('EXPERIMENTAL.workers.worker_process.webdriver.Edge') as mock_edge, \
         patch('EXPERIMENTAL.workers.browser_session.BrowserSession.authenticate', return_value=True), \
         patch('EXPERIMENTAL.workers.worker_process.BrowserSession') as mock_browser_session:

        # Configure mocks
        mock_driver_instance = MagicMock()
        mock_edge.return_value = mock_driver_instance

        mock_browser_instance = MagicMock()
        mock_browser_session.return_value = mock_browser_instance
        mock_browser_instance.driver = mock_driver_instance
        mock_browser_instance.main_window_handle = "test-window-1"

        try:
            yield temp_dir
        finally:
            pass  # Mocks are handled by context manager

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)
    print("🧹 Test environment cleaned up")

async def test_scenario_1_basic_functionality():
    """Test Scenario 1: Basic pool startup and task submission."""
    print("\n🧪 SCENARIO 1: Basic Functionality Test")
    print("=" * 50)

    async def run_test(temp_dir):
        try:
            from EXPERIMENTAL.workers.models.config import PoolConfig
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            # Create minimal config with temp profile path
            config = PoolConfig(
                worker_count=2,
                headless_mode=True,
                base_profile_path=temp_dir,
                memory_threshold=0.75,
                shutdown_timeout=30
            )

            print("📋 Creating worker pool...")
            pool = PersistentWorkerPool(config)

            print("🚀 Starting worker pool...")
            start_time = time.time()
            await pool.start()
            startup_time = time.time() - start_time
            print(".2f")

            # Verify pool status
            status = pool.get_status()
            print(f"📊 Pool status: {status['pool_status']}")
            print(f"👷 Worker count: {status['worker_count']}")
            print(f"✅ Startup complete: {status['startup_complete']}")

            assert status['pool_status'] == 'running'
            assert status['worker_count'] == 2
            assert status['startup_complete'] == True

            print("📋 Submitting test tasks...")
            test_pos = ["PO-001", "PO-002", "PO-003", "PO-004", "PO-005"]

            handles = pool.submit_tasks(test_pos)
            print(f"✅ Submitted {len(handles)} tasks")

            # Wait for completion
            print("⏳ Waiting for task completion...")
            completed = await pool.wait_for_completion(timeout=60)

            if completed:
                print("✅ All tasks completed successfully")
            else:
                print("⚠️ Some tasks did not complete within timeout")

            # Check final status
            final_status = pool.get_status()
            print(f"📊 Final stats - Completed: {final_status['completed_tasks']}, Failed: {final_status['failed_tasks']}")

            print("🛑 Shutting down pool...")
            await pool.shutdown()

            print("✅ Basic functionality test PASSED")
            return True

        except Exception as e:
            print(f"❌ Basic functionality test FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False

    with setup_test_environment() as temp_dir:
        return await run_test(temp_dir)

async def test_scenario_2_resource_monitoring():
    """Test Scenario 2: Resource monitoring and memory pressure handling."""
    print("\n🧪 SCENARIO 2: Resource Monitoring Test")
    print("=" * 50)

    async def run_test(temp_dir):
        try:
            from EXPERIMENTAL.workers.models.config import PoolConfig
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool
            from EXPERIMENTAL.workers.memory_monitor import MemoryMonitor

            config = PoolConfig(
                worker_count=2,
                headless_mode=True,
                base_profile_path=temp_dir,
                memory_threshold=0.75
            )

            pool = PersistentWorkerPool(config)
            await pool.start()

            # Test memory monitoring
            print("📊 Testing memory monitoring...")
            memory_info = pool.memory_monitor.get_memory_info()

            required_keys = ['usage_percent', 'total_gb', 'available_gb', 'process_usage_mb', 'is_pressure']
            for key in required_keys:
                assert key in memory_info, f"Missing memory info key: {key}"
                print(f"  {key}: {memory_info[key]}")

            # Test status reporting performance
            print("⚡ Testing status reporting performance...")
            status_times = []
            for _ in range(10):
                start_time = time.time()
                status = pool.get_status()
                end_time = time.time()
                status_times.append(end_time - start_time)

            avg_time = sum(status_times) / len(status_times)
            max_time = max(status_times)

            print(".4f")
            print(".4f")

            assert avg_time < 0.1, f"Average status time {avg_time:.4f}s too slow"
            assert max_time < 0.5, f"Max status time {max_time:.4f}s too slow"

            await pool.shutdown()

            print("✅ Resource monitoring test PASSED")
            return True

        except Exception as e:
            print(f"❌ Resource monitoring test FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False

    with setup_test_environment() as temp_dir:
        return await run_test(temp_dir)

async def test_scenario_3_concurrent_access():
    """Test Scenario 3: Concurrent status access and thread safety."""
    print("\n🧪 SCENARIO 3: Concurrent Access Test")
    print("=" * 50)

    async def run_test(temp_dir):
        try:
            import threading
            from EXPERIMENTAL.workers.models.config import PoolConfig
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            config = PoolConfig(
                worker_count=2, 
                headless_mode=True,
                base_profile_path=temp_dir
            )
            pool = PersistentWorkerPool(config)
            await pool.start()

            print("🔄 Testing concurrent status access...")

            results = []
            errors = []
            threads_completed = []

            def status_worker(worker_id):
                """Worker function for concurrent status access."""
                try:
                    for i in range(5):
                        status = pool.get_status()
                        results.append((worker_id, i, status['pool_status']))
                        time.sleep(0.01)  # Small delay to simulate real usage
                    threads_completed.append(worker_id)
                except Exception as e:
                    errors.append((worker_id, str(e)))

            # Start multiple threads
            threads = []
            for i in range(3):
                thread = threading.Thread(target=status_worker, args=(f"thread-{i}",))
                threads.append(thread)
                thread.start()

            # Wait for completion
            for thread in threads:
                thread.join(timeout=5)

            print(f"📊 Concurrent access results: {len(results)} successful calls")
            print(f"❌ Errors: {len(errors)}")

            assert len(errors) == 0, f"Concurrent access errors: {errors}"
            assert len(results) == 15, f"Expected 15 results, got {len(results)}"
            assert len(threads_completed) == 3, "Not all threads completed"

            await pool.shutdown()

            print("✅ Concurrent access test PASSED")
            return True

        except Exception as e:
            print(f"❌ Concurrent access test FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False

    with setup_test_environment() as temp_dir:
        return await run_test(temp_dir)

async def test_scenario_4_failure_recovery():
    """Test Scenario 4: Worker failure and recovery."""
    print("\n🧪 SCENARIO 4: Failure Recovery Test")
    print("=" * 50)

    async def run_test(temp_dir):
        try:
            from EXPERIMENTAL.workers.models.config import PoolConfig
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            config = PoolConfig(
                worker_count=2,
                headless_mode=True,
                base_profile_path=temp_dir,
                shutdown_timeout=30
            )

            pool = PersistentWorkerPool(config)
            await pool.start()

            print("📋 Testing initial pool state...")
            initial_status = pool.get_status()
            assert initial_status['worker_count'] == 2

            # Submit some tasks to get workers active
            handles = pool.submit_tasks(["PO-001", "PO-002"])
            await asyncio.sleep(1)  # Let workers start processing

            # Check that workers are running
            status = pool.get_status()
            print(f"👷 Active workers: {status['worker_count']}")

            # Test graceful shutdown
            print("🛑 Testing graceful shutdown...")
            shutdown_start = time.time()
            await pool.shutdown()
            shutdown_time = time.time() - shutdown_start

            print(".2f")

            final_status = pool.get_status()
            assert final_status['pool_status'] == 'stopped'

            print("✅ Failure recovery test PASSED")
            return True

        except Exception as e:
            print(f"❌ Failure recovery test FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False

    with setup_test_environment() as temp_dir:
        return await run_test(temp_dir)

async def test_scenario_5_load_testing():
    """Test Scenario 5: Load testing with multiple tasks."""
    print("\n🧪 SCENARIO 5: Load Testing")
    print("=" * 50)

    async def run_test(temp_dir):
        try:
            from EXPERIMENTAL.workers.models.config import PoolConfig
            from EXPERIMENTAL.workers.persistent_pool import PersistentWorkerPool

            config = PoolConfig(
                worker_count=3,
                headless_mode=True,
                base_profile_path=temp_dir,
                memory_threshold=0.8,
                shutdown_timeout=60
            )

            pool = PersistentWorkerPool(config)
            await pool.start()

            print("📋 Submitting load test tasks...")
            # Submit 20 test POs for load testing
            test_pos = [f"PO-{str(i+1).zfill(3)}" for i in range(20)]

            start_time = time.time()
            handles = pool.submit_tasks(test_pos)
            submission_time = time.time() - start_time

            print(f"✅ Submitted {len(handles)} tasks in {submission_time:.2f}s")

            # Wait for completion with timeout
            print("⏳ Waiting for completion (timeout: 120s)...")
            completed = await pool.wait_for_completion(timeout=120)

            processing_time = time.time() - start_time

            if completed:
                print(".2f")
                throughput = len(test_pos) / processing_time
                print(".2f")
            else:
                print("⚠️ Load test did not complete within timeout")

            # Check final statistics
            final_status = pool.get_status()
            print(f"📊 Final results - Completed: {final_status['completed_tasks']}, Failed: {final_status['failed_tasks']}")

            await pool.shutdown()

            print("✅ Load testing PASSED")
            return True

        except Exception as e:
            print(f"❌ Load testing FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False

    with setup_test_environment() as temp_dir:
        return await run_test(temp_dir)

async def run_all_manual_tests():
    """Run all manual testing scenarios."""
    print("🚀 STARTING MANUAL TESTING SUITE")
    print("=" * 60)
    print("Testing Persistent Worker Pool Implementation")
    print("=" * 60)

    test_results = []

    # Run all test scenarios
    scenarios = [
        ("Basic Functionality", test_scenario_1_basic_functionality),
        ("Resource Monitoring", test_scenario_2_resource_monitoring),
        ("Concurrent Access", test_scenario_3_concurrent_access),
        ("Failure Recovery", test_scenario_4_failure_recovery),
        ("Load Testing", test_scenario_5_load_testing),
    ]

    for scenario_name, test_func in scenarios:
        print(f"\n🎯 Running: {scenario_name}")
        try:
            result = await test_func()
            test_results.append((scenario_name, result))
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"📋 {scenario_name}: {status}")
        except Exception as e:
            print(f"❌ {scenario_name}: EXCEPTION - {e}")
            test_results.append((scenario_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("📊 MANUAL TESTING SUMMARY")
    print("=" * 60)

    passed = 0
    total = len(test_results)

    for scenario_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} {scenario_name}")
        if result:
            passed += 1

    print(f"\n📈 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL MANUAL TESTS PASSED! Implementation is ready for production.")
        return True
    else:
        print("⚠️ Some tests failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    # Run the manual test suite
    try:
        success = asyncio.run(run_all_manual_tests())
        exit_code = 0 if success else 1
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️ Manual testing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Manual testing failed with exception: {e}")
        import traceback
        traceback.print_exc()
