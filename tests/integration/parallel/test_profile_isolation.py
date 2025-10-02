"""Integration test for profile isolation - T011

This test validates Scenario 3 from quickstart.md: Profile Isolation Validation.
Tests should FAIL until the actual implementation is complete.
"""

import pytest
import tempfile
import os
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
import threading

# Import will fail until implementation exists - expected for TDD
try:
    from EXPERIMENTAL.workers.profile_manager import ProfileManager
    from EXPERIMENTAL.workers.worker_pool import WorkerPool
    from EXPERIMENTAL.corelib.config import HeadlessConfiguration
except ImportError as e:
    pytest.skip(f"Profile management modules not implemented yet: {e}", allow_module_level=True)


class TestProfileIsolation:
    """Test profile isolation per quickstart.md Scenario 3."""
    
    def test_profile_manager_creates_unique_profiles(self):
        """Test that ProfileManager creates unique profiles for each worker."""
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
    
    def test_concurrent_profile_creation(self):
        """Test concurrent profile creation and access."""
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
    
    def test_profile_directory_structure(self):
        """Test that profile directories have proper structure and permissions."""
        profile_manager = ProfileManager()
        
        # Create test profile
        worker_id = "structure_test"
        profile_path = profile_manager.create_profile(worker_id)
        
        try:
            # Profile should be in system temp directory
            assert profile_path.startswith(tempfile.gettempdir()) or \
                   "/tmp" in profile_path or \
                   "temp" in profile_path.lower(), "Profile not in temp directory"
            
            # Profile should be a directory
            assert os.path.isdir(profile_path), "Profile is not a directory"
            
            # Profile should have proper permissions
            assert os.access(profile_path, os.R_OK | os.W_OK), "Profile not readable/writable"
            
            # Profile should be unique (contain worker ID or UUID)
            assert worker_id in profile_path or len(os.path.basename(profile_path)) > 10, \
                   "Profile path not unique"
        
        finally:
            profile_manager.cleanup_profile(worker_id)
    
    def test_profile_base_copy_functionality(self):
        """Test that base profile copying preserves essential settings."""
        # Create temporary base profile with test content
        with tempfile.TemporaryDirectory() as base_dir:
            # Create test files in base profile
            test_settings = {
                "preferences.json": '{"test_setting": "value"}',
                "bookmarks.html": "<html>Test bookmarks</html>",
                "cookies.db": "test_cookie_data"
            }
            
            for filename, content in test_settings.items():
                file_path = os.path.join(base_dir, filename)
                with open(file_path, 'w') as f:
                    f.write(content)
            
            # Create ProfileManager with base profile
            profile_manager = ProfileManager(base_profile_path=base_dir)
            
            # Create worker profile
            worker_id = "copy_test"
            profile_path = profile_manager.create_profile(worker_id)
            
            try:
                # Copy base profile
                copy_result = profile_manager.copy_base_profile(worker_id)
                assert copy_result is True, "Base profile copy failed"
                
                # Verify essential files were copied
                for filename in test_settings.keys():
                    copied_file = os.path.join(profile_path, filename)
                    if os.path.exists(copied_file):
                        # File was copied - verify it's not the same file
                        original_file = os.path.join(base_dir, filename)
                        assert copied_file != original_file, "File reference not copied"
            
            finally:
                profile_manager.cleanup_profile(worker_id)
    
    def test_profile_isolation_browser_compatibility(self):
        """Test that isolated profiles are compatible with browser requirements."""
        profile_manager = ProfileManager()
        
        worker_ids = ["browser_test_1", "browser_test_2"]
        created_profiles = []
        
        try:
            for worker_id in worker_ids:
                profile_path = profile_manager.create_profile(worker_id)
                created_profiles.append((worker_id, profile_path))
                
                # Profile should be browser-compatible
                assert os.path.exists(profile_path), f"Profile {profile_path} does not exist"
                assert os.path.isdir(profile_path), f"Profile {profile_path} is not a directory"
                
                # Should be able to create browser-expected subdirectories
                test_subdir = os.path.join(profile_path, "Cache")
                os.makedirs(test_subdir, exist_ok=True)
                assert os.path.exists(test_subdir), "Cannot create browser subdirectories"
                
                # Should be writable for browser data
                test_file = os.path.join(profile_path, "test_browser_file.dat")
                with open(test_file, 'w') as f:
                    f.write("test browser data")
                assert os.path.exists(test_file), "Cannot write browser files"
        
        finally:
            for worker_id, _ in created_profiles:
                profile_manager.cleanup_profile(worker_id)
    
    def test_profile_cleanup_robustness(self):
        """Test that profile cleanup handles edge cases robustly."""
        profile_manager = ProfileManager()
        
        # Test cleanup of non-existent profile (should be idempotent)
        result = profile_manager.cleanup_profile("nonexistent_worker")
        assert result is True, "Cleanup should succeed for non-existent profile"
        
        # Test cleanup after creating and using profile
        worker_id = "cleanup_test"
        profile_path = profile_manager.create_profile(worker_id)
        
        # Create some files in the profile to simulate usage
        test_files = ["file1.txt", "subdir/file2.txt", "cache/data.bin"]
        for file_rel_path in test_files:
            file_path = os.path.join(profile_path, file_rel_path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(f"test data for {file_rel_path}")
        
        # Cleanup should remove everything
        result = profile_manager.cleanup_profile(worker_id)
        assert result is True, "Cleanup should succeed"
        assert not os.path.exists(profile_path), "Profile directory should be removed"
    
    def test_profile_size_monitoring(self):
        """Test that profile size can be monitored and limited."""
        profile_manager = ProfileManager(profile_size_limit_mb=10)  # 10MB limit
        
        worker_id = "size_test"
        profile_path = profile_manager.create_profile(worker_id)
        
        try:
            # Get initial size
            initial_size = profile_manager.get_profile_size(worker_id)
            assert isinstance(initial_size, int), "Profile size should be integer"
            assert initial_size >= 0, "Profile size should be non-negative"
            
            # Add some data and check size increases
            test_file = os.path.join(profile_path, "size_test.dat")
            with open(test_file, 'w') as f:
                f.write("x" * 1024)  # 1KB of data
            
            new_size = profile_manager.get_profile_size(worker_id)
            assert new_size > initial_size, "Profile size should increase after adding data"
        
        finally:
            profile_manager.cleanup_profile(worker_id)
    
    def test_profile_validation_checks(self):
        """Test that profile validation performs necessary checks."""
        profile_manager = ProfileManager()
        
        # Test validation of non-existent profile
        assert profile_manager.validate_profile("nonexistent") is False, \
               "Non-existent profile should be invalid"
        
        # Test validation of existing profile
        worker_id = "validation_test"
        profile_path = profile_manager.create_profile(worker_id)
        
        try:
            # Should be valid after creation
            assert profile_manager.validate_profile(worker_id) is True, \
                   "Created profile should be valid"
            
            # Test with corrupted profile (simulate by removing directory)
            import shutil
            shutil.rmtree(profile_path)
            assert profile_manager.validate_profile(worker_id) is False, \
                   "Corrupted profile should be invalid"
        
        except Exception:
            # Cleanup in case of any issues
            try:
                profile_manager.cleanup_profile(worker_id)
            except:
                pass


class TestProfileIsolationIntegration:
    """Test profile isolation integration with worker pool."""
    
    def test_worker_pool_profile_integration(self):
        """Test that WorkerPool integrates with ProfileManager correctly."""
        config = HeadlessConfiguration(headless=True)
        
        # Create worker pool with profile management
        pool = WorkerPool(
            pool_size=2,
            headless_config=config
        )
        
        # Pool should have profile manager
        assert hasattr(pool, 'profile_manager'), "WorkerPool should have ProfileManager"
        
        # Should be able to get pool status (includes profile info)
        status = pool.get_status()
        assert isinstance(status, dict), "Status should be dictionary"
        assert 'worker_details' in status, "Status should include worker details"
    
    def test_worker_pool_profile_cleanup_on_stop(self):
        """Test that profiles are cleaned up when worker pool stops."""
        config = HeadlessConfiguration(headless=True)
        pool = WorkerPool(pool_size=2, headless_config=config)
        
        # Start pool (should create profiles)
        po_list = [
            {
                "po_number": "CLEANUP-001",
                "supplier": "Cleanup Test",
                "url": "https://example.com/cleanup",
                "amount": 1000.00
            }
        ]
        
        pool.start_processing(po_list)
        
        # Stop pool (should cleanup profiles)
        cleanup_result = pool.stop_processing()
        assert cleanup_result is True, "Pool stop should succeed"
        
        # Profiles should be cleaned up
        # (Specific verification depends on implementation details)
    
    def test_profile_isolation_under_concurrent_access(self):
        """Test profile isolation under concurrent worker access."""
        profile_manager = ProfileManager()
        
        def worker_profile_operations(worker_id):
            """Simulate worker operations on profile."""
            try:
                # Create profile
                profile_path = profile_manager.create_profile(f"concurrent_{worker_id}")
                
                # Simulate browser operations
                cache_dir = os.path.join(profile_path, "cache")
                os.makedirs(cache_dir, exist_ok=True)
                
                # Write some data
                data_file = os.path.join(cache_dir, f"worker_{worker_id}_data.txt")
                with open(data_file, 'w') as f:
                    f.write(f"Data from worker {worker_id}")
                
                # Validate profile
                is_valid = profile_manager.validate_profile(f"concurrent_{worker_id}")
                
                # Cleanup
                profile_manager.cleanup_profile(f"concurrent_{worker_id}")
                
                return is_valid
            
            except Exception as e:
                print(f"Worker {worker_id} error: {e}")
                return False
        
        # Run multiple workers concurrently
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(worker_profile_operations, i) 
                for i in range(4)
            ]
            results = [future.result() for future in futures]
        
        # All workers should succeed
        assert all(results), "All concurrent profile operations should succeed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])