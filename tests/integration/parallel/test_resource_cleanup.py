"""
Resource cleanup verification tests for parallel processing.
Ensures proper cleanup of browser profiles, temporary files, and worker processes.
"""

import os
import time
import tempfile
import shutil
import psutil
import pytest
import threading
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Any


# Multiprocessing workers must be at module scope to be picklable on macOS (spawn)
def _worker_process_function(worker_id: int, duration: float):
    """Simple worker function that runs for specified duration."""
    start_time = time.time()
    while time.time() - start_time < duration:
        time.sleep(0.1)
    return f"Worker {worker_id} completed"


class TestResourceCleanup:
    """Test suite for verifying proper resource cleanup in parallel processing."""
    
    def test_temporary_profile_cleanup(self):
        """Test that temporary browser profiles are properly cleaned up."""
        # Simulate profile creation and cleanup
        profiles_created = []
        base_temp_dir = tempfile.gettempdir()
        
        try:
            # Create multiple temporary profiles
            for i in range(5):
                profile_dir = tempfile.mkdtemp(
                    prefix=f"test_coupa_profile_{i}_", 
                    dir=base_temp_dir
                )
                profiles_created.append(profile_dir)
                
                # Create some files in the profile directory
                os.makedirs(os.path.join(profile_dir, "Default"), exist_ok=True)
                with open(os.path.join(profile_dir, "Default", "Preferences"), 'w') as f:
                    f.write('{"test": "data"}')
                
                # Verify profile directory exists
                assert os.path.exists(profile_dir), f"Profile directory {profile_dir} should exist"
                assert os.path.isdir(profile_dir), f"Profile path {profile_dir} should be a directory"
            
            # Verify all profiles exist before cleanup
            for profile_dir in profiles_created:
                assert os.path.exists(profile_dir), "Profile should exist before cleanup"
            
            # Simulate cleanup process
            cleanup_start = time.time()
            cleaned_count = 0
            
            for profile_dir in profiles_created:
                if os.path.exists(profile_dir):
                    shutil.rmtree(profile_dir)
                    cleaned_count += 1
            
            cleanup_time = time.time() - cleanup_start
            
            # Verify cleanup performance
            assert cleanup_time < 5.0, f"Profile cleanup took too long: {cleanup_time:.2f}s"
            assert cleaned_count == len(profiles_created), f"Expected {len(profiles_created)} profiles cleaned, got {cleaned_count}"
            
            # Verify all profiles are gone
            for profile_dir in profiles_created:
                assert not os.path.exists(profile_dir), f"Profile {profile_dir} should be cleaned up"
            
            print(f"Successfully cleaned up {cleaned_count} profiles in {cleanup_time:.2f}s")
            
        except Exception as e:
            # Ensure cleanup even if test fails
            for profile_dir in profiles_created:
                if os.path.exists(profile_dir):
                    try:
                        shutil.rmtree(profile_dir)
                    except Exception:
                        pass
            raise e
    
    def test_worker_process_cleanup(self):
        """Test that worker processes are properly terminated."""
        import multiprocessing
        import signal
        
        # worker function moved to module scope (_worker_process_function)
        
        # Start multiple worker processes
        worker_processes = []
        max_workers = 4
        
        try:
            for i in range(max_workers):
                process = multiprocessing.Process(
                    target=_worker_process_function,
                    args=(i, 2.0)  # 2 second duration
                )
                process.start()
                worker_processes.append(process)
            
            # Verify all processes are running
            time.sleep(0.5)  # Give processes time to start
            running_count = 0
            for process in worker_processes:
                if process.is_alive():
                    running_count += 1
            
            assert running_count > 0, "At least some worker processes should be running"
            print(f"Started {running_count} worker processes")
            
            # Simulate cleanup - terminate all processes
            cleanup_start = time.time()
            terminated_count = 0
            
            for process in worker_processes:
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=2.0)  # Wait up to 2 seconds
                    
                    if process.is_alive():
                        # Force kill if still alive
                        process.kill()
                        process.join(timeout=1.0)
                    
                    terminated_count += 1
            
            cleanup_time = time.time() - cleanup_start
            
            # Verify cleanup performance and effectiveness
            assert cleanup_time < 5.0, f"Worker cleanup took too long: {cleanup_time:.2f}s"
            
            # Verify all processes are terminated
            alive_count = 0
            for process in worker_processes:
                if process.is_alive():
                    alive_count += 1
            
            assert alive_count == 0, f"{alive_count} processes still alive after cleanup"
            print(f"Successfully terminated {terminated_count} worker processes in {cleanup_time:.2f}s")
            
        except Exception as e:
            # Ensure cleanup even if test fails
            for process in worker_processes:
                if process.is_alive():
                    try:
                        process.terminate()
                        process.join(timeout=1.0)
                        if process.is_alive():
                            process.kill()
                            process.join(timeout=1.0)
                    except Exception:
                        pass
            raise e
    
    def test_memory_leak_detection(self):
        """Test for memory leaks during repeated resource allocation/cleanup."""
        import psutil
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform multiple cycles of resource allocation and cleanup
        cycles = 10
        max_memory_increase = 0
        
        for cycle in range(cycles):
            cycle_start_memory = process.memory_info().rss / 1024 / 1024
            
            # Simulate resource allocation
            temp_resources = []
            
            # Create temporary files and directories
            for i in range(10):
                temp_dir = tempfile.mkdtemp(prefix=f"memory_test_{cycle}_{i}_")
                temp_resources.append(temp_dir)
                
                # Create some files
                for j in range(5):
                    temp_file = os.path.join(temp_dir, f"file_{j}.txt")
                    with open(temp_file, 'w') as f:
                        f.write("test data " * 100)  # Small amount of data
            
            # Simulate some processing
            data_structures = []
            for i in range(100):
                data_structures.append([i] * 100)
            
            # Cleanup resources
            for temp_dir in temp_resources:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            
            # Clear data structures
            del data_structures
            del temp_resources
            
            # Force garbage collection
            import gc
            gc.collect()
            
            cycle_end_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = cycle_end_memory - initial_memory
            max_memory_increase = max(max_memory_increase, memory_increase)
            
            print(f"Cycle {cycle + 1}: Memory increase from baseline: {memory_increase:.2f}MB")
            
            # Allow some memory increase but detect significant leaks
            if memory_increase > 50:  # 50MB threshold
                print(f"Warning: Significant memory increase detected: {memory_increase:.2f}MB")
        
        final_memory = process.memory_info().rss / 1024 / 1024
        total_increase = final_memory - initial_memory
        
        print(f"Total memory increase after {cycles} cycles: {total_increase:.2f}MB")
        print(f"Maximum memory increase during cycles: {max_memory_increase:.2f}MB")
        
        # Assert no significant memory leaks
        assert total_increase < 100, f"Possible memory leak: {total_increase:.2f}MB increase"
        assert max_memory_increase < 75, f"Peak memory usage too high: {max_memory_increase:.2f}MB"
    
    def test_file_handle_cleanup(self):
        """Test that file handles are properly closed and cleaned up."""
        import tempfile
        
        initial_fd_count = len(os.listdir('/dev/fd')) if os.path.exists('/dev/fd') else 0
        
        # Create and manage multiple file handles
        file_handles = []
        temp_files = []
        
        try:
            # Create multiple temporary files
            for i in range(20):
                temp_file = tempfile.NamedTemporaryFile(
                    mode='w+',
                    prefix=f"handle_test_{i}_",
                    delete=False
                )
                file_handles.append(temp_file)
                temp_files.append(temp_file.name)
                
                # Write some data
                temp_file.write("test data " * 100)
                temp_file.flush()
            
            # Verify files are open
            assert len(file_handles) == 20, "All file handles should be created"
            
            # Close all file handles
            for handle in file_handles:
                handle.close()
            
            # Verify file handles are closed by trying to write (should fail)
            closed_count = 0
            for handle in file_handles:
                try:
                    handle.write("test")
                    handle.flush()
                except ValueError:  # I/O operation on closed file
                    closed_count += 1
            
            assert closed_count == len(file_handles), "All file handles should be closed"
            
            # Clean up temporary files
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            
            print(f"Successfully cleaned up {len(file_handles)} file handles and {len(temp_files)} temporary files")
            
        except Exception as e:
            # Ensure cleanup even if test fails
            for handle in file_handles:
                try:
                    handle.close()
                except Exception:
                    pass
            
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                except Exception:
                    pass
            
            raise e
    
    def test_concurrent_cleanup_safety(self):
        """Test that cleanup operations are safe when performed concurrently."""
        import threading
        import concurrent.futures
        
        # Create shared resources
        shared_resources = []
        resource_lock = threading.Lock()
        
        # Create temporary directories
        for i in range(20):
            temp_dir = tempfile.mkdtemp(prefix=f"concurrent_cleanup_{i}_")
            shared_resources.append(temp_dir)
            
            # Create some files in each directory
            for j in range(3):
                temp_file = os.path.join(temp_dir, f"file_{j}.txt")
                with open(temp_file, 'w') as f:
                    f.write(f"test data {i}-{j}")
        
        def cleanup_worker(worker_id: int, resources_subset: List[str]) -> Dict[str, Any]:
            """Worker function to clean up a subset of resources."""
            cleaned = 0
            errors = 0
            
            for resource in resources_subset:
                try:
                    with resource_lock:  # Ensure thread-safe cleanup
                        if os.path.exists(resource):
                            shutil.rmtree(resource)
                            cleaned += 1
                except Exception as e:
                    errors += 1
                    print(f"Worker {worker_id} cleanup error: {e}")
            
            return {
                'worker_id': worker_id,
                'cleaned': cleaned,
                'errors': errors
            }
        
        # Split resources among workers
        num_workers = 4
        resources_per_worker = len(shared_resources) // num_workers
        
        worker_assignments = []
        for i in range(num_workers):
            start_idx = i * resources_per_worker
            if i == num_workers - 1:
                # Last worker gets remaining resources
                end_idx = len(shared_resources)
            else:
                end_idx = start_idx + resources_per_worker
            
            worker_assignments.append(shared_resources[start_idx:end_idx])
        
        # Execute concurrent cleanup
        start_time = time.time()
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = []
            for i, resources_subset in enumerate(worker_assignments):
                future = executor.submit(cleanup_worker, i, resources_subset)
                futures.append(future)
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results.append(result)
        
        cleanup_time = time.time() - start_time
        
        # Verify results
        total_cleaned = sum(r['cleaned'] for r in results)
        total_errors = sum(r['errors'] for r in results)
        
        print(f"Concurrent cleanup results:")
        print(f"  Total cleaned: {total_cleaned}")
        print(f"  Total errors: {total_errors}")
        print(f"  Cleanup time: {cleanup_time:.2f}s")
        
        # Assertions
        assert cleanup_time < 10.0, f"Concurrent cleanup took too long: {cleanup_time:.2f}s"
        assert total_errors == 0, f"Cleanup errors occurred: {total_errors}"
        assert total_cleaned <= len(shared_resources), "Cannot clean more resources than created"
        
        # Verify all resources are actually cleaned up
        remaining_resources = 0
        for resource in shared_resources:
            if os.path.exists(resource):
                remaining_resources += 1
        
        assert remaining_resources == 0, f"{remaining_resources} resources not cleaned up"
        
        print(f"Successfully completed concurrent cleanup of {total_cleaned} resources")
    
    def test_cleanup_under_failure_conditions(self):
        """Test cleanup behavior when operations fail or are interrupted."""
        temp_resources = []
        
        try:
            # Create resources
            for i in range(10):
                temp_dir = tempfile.mkdtemp(prefix=f"failure_test_{i}_")
                temp_resources.append(temp_dir)
                
                # Create files
                for j in range(3):
                    temp_file = os.path.join(temp_dir, f"file_{j}.txt")
                    with open(temp_file, 'w') as f:
                        f.write("test data")
            
            # Simulate failure conditions
            failure_scenarios = [
                "permission_denied",
                "resource_busy",
                "partial_cleanup"
            ]
            
            for scenario in failure_scenarios:
                print(f"Testing scenario: {scenario}")
                open_handles = []  # Initialize for all scenarios
                
                if scenario == "permission_denied":
                    # Make some directories read-only (simulate permission issues)
                    protected_dirs = temp_resources[:3]
                    for temp_dir in protected_dirs:
                        try:
                            os.chmod(temp_dir, 0o444)  # Read-only
                        except Exception:
                            pass  # Skip if chmod not supported
                
                elif scenario == "resource_busy":
                    # Keep file handles open (simulate busy resources)
                    for temp_dir in temp_resources[3:6]:
                        try:
                            file_path = os.path.join(temp_dir, "busy_file.txt")
                            handle = open(file_path, 'w')
                            open_handles.append(handle)
                        except Exception:
                            pass
                
                # Attempt cleanup with error handling
                cleanup_start = time.time()
                cleaned_count = 0
                error_count = 0
                
                for temp_dir in temp_resources:
                    try:
                        if os.path.exists(temp_dir):
                            # Restore permissions if needed
                            try:
                                os.chmod(temp_dir, 0o755)
                            except Exception:
                                pass
                            
                            shutil.rmtree(temp_dir)
                            cleaned_count += 1
                    except Exception as e:
                        error_count += 1
                        print(f"  Expected cleanup error: {e}")
                
                cleanup_time = time.time() - cleanup_start
                
                print(f"  Scenario {scenario}: {cleaned_count} cleaned, {error_count} errors, {cleanup_time:.2f}s")
                
                # Close any open handles
                if scenario == "resource_busy":
                    for handle in open_handles:
                        try:
                            handle.close()
                        except Exception:
                            pass
                
                # Cleanup should complete within reasonable time even with errors
                assert cleanup_time < 5.0, f"Cleanup under failure took too long: {cleanup_time:.2f}s"
            
            print("Successfully tested cleanup under failure conditions")
            
        finally:
            # Final cleanup - ensure all resources are removed
            for temp_dir in temp_resources:
                try:
                    if os.path.exists(temp_dir):
                        # Restore permissions
                        try:
                            os.chmod(temp_dir, 0o755)
                            for root, dirs, files in os.walk(temp_dir):
                                for d in dirs:
                                    os.chmod(os.path.join(root, d), 0o755)
                                for f in files:
                                    os.chmod(os.path.join(root, f), 0o755)
                        except Exception:
                            pass
                        
                        shutil.rmtree(temp_dir)
                except Exception:
                    pass


class TestResourceMonitoring:
    """Test suite for monitoring resource usage during parallel operations."""
    
    def test_resource_usage_monitoring(self):
        """Test monitoring of CPU, memory, and disk usage during operations."""
        import psutil
        
        process = psutil.Process(os.getpid())
        
        # Baseline measurements
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        initial_cpu = process.cpu_percent()
        
        print(f"Initial resource usage:")
        print(f"  Memory: {initial_memory:.2f}MB")
        print(f"  CPU: {initial_cpu:.1f}%")
        
        # Simulate resource-intensive operations
        monitoring_data = []
        operation_duration = 3.0  # seconds
        start_time = time.time()
        
        def monitor_resources():
            """Background monitoring function."""
            while time.time() - start_time < operation_duration:
                current_memory = process.memory_info().rss / 1024 / 1024
                current_cpu = process.cpu_percent()
                
                monitoring_data.append({
                    'timestamp': time.time() - start_time,
                    'memory_mb': current_memory,
                    'cpu_percent': current_cpu,
                    'memory_increase': current_memory - initial_memory
                })
                
                time.sleep(0.1)  # Monitor every 100ms
        
        # Start monitoring in background
        monitor_thread = threading.Thread(target=monitor_resources)
        monitor_thread.start()
        
        # Simulate workload
        temp_resources = []
        for i in range(50):
            # Create temporary resources
            temp_dir = tempfile.mkdtemp(prefix=f"monitor_test_{i}_")
            temp_resources.append(temp_dir)
            
            # Create files with some CPU/IO work
            for j in range(10):
                temp_file = os.path.join(temp_dir, f"file_{j}.txt")
                with open(temp_file, 'w') as f:
                    f.write("data " * 1000)  # Some data
            
            time.sleep(0.05)  # Small delay between operations
        
        # Wait for monitoring to complete
        monitor_thread.join()
        
        # Cleanup
        for temp_dir in temp_resources:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except Exception:
                pass
        
        # Analyze monitoring data
        if monitoring_data:
            max_memory = max(d['memory_mb'] for d in monitoring_data)
            max_cpu = max(d['cpu_percent'] for d in monitoring_data)
            max_memory_increase = max(d['memory_increase'] for d in monitoring_data)
            
            print(f"Peak resource usage during operations:")
            print(f"  Peak memory: {max_memory:.2f}MB")
            print(f"  Peak CPU: {max_cpu:.1f}%")
            print(f"  Peak memory increase: {max_memory_increase:.2f}MB")
            
            # Validate resource usage is within reasonable bounds
            assert max_memory_increase < 200, f"Memory increase too high: {max_memory_increase:.2f}MB"
            assert len(monitoring_data) > 10, "Monitoring should collect sufficient data points"
            
            print(f"Collected {len(monitoring_data)} monitoring data points")
        else:
            print("Warning: No monitoring data collected")


if __name__ == "__main__":
    # Run resource cleanup tests
    pytest.main([__file__, "-v", "--tb=short"])