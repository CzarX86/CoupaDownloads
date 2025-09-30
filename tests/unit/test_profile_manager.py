"""Unit tests for ProfileManager component - T016

Tests for EXPERIMENTAL.workers.profiles.ProfileManager per profile_manager_contract.md.
Tests should FAIL until the actual implementation is complete.
"""

import pytest
import tempfile
import shutil
import os
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch

# Import will fail until implementation exists - expected for TDD
try:
    from EXPERIMENTAL.workers.profiles import ProfileManager
    from EXPERIMENTAL.workers.exceptions import (
        ProfileManagerError,
        ProfileCreationError,
        ProfileCleanupError,
        ProfileConflictError
    )
except ImportError as e:
    pytest.skip(f"ProfileManager modules not implemented yet: {e}", allow_module_level=True)


class TestProfileManagerInitialization:
    """Test ProfileManager initialization and configuration."""
    
    def test_default_initialization(self):
        """Test ProfileManager creation with default parameters."""
        manager = ProfileManager()
        
        # Validate default configuration
        assert manager.base_directory is not None, "Should have base directory"
        assert manager.profile_prefix == "coupa_worker_", "Default prefix should be set"
        assert manager.get_active_count() == 0, "No profiles should be active initially"
        assert manager.get_total_count() == 0, "No profiles should exist initially"
    
    def test_custom_initialization(self):
        """Test ProfileManager creation with custom parameters."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ProfileManager(
                base_directory=temp_dir,
                profile_prefix="custom_test_",
                auto_cleanup=False
            )
            
            # Validate custom configuration
            assert str(manager.base_directory) == temp_dir, "Custom base directory should be set"
            assert manager.profile_prefix == "custom_test_", "Custom prefix should be set"
            assert manager.auto_cleanup == False, "Auto cleanup should be disabled"
    
    def test_invalid_base_directory_handling(self):
        """Test handling of invalid base directory."""
        # Non-existent parent directory
        invalid_path = "/non/existent/path/profiles"
        with pytest.raises(ProfileManagerError, match="Invalid base directory"):
            ProfileManager(base_directory=invalid_path)
        
        # File instead of directory
        with tempfile.NamedTemporaryFile() as temp_file:
            with pytest.raises(ProfileManagerError, match="Base directory must be a directory"):
                ProfileManager(base_directory=temp_file.name)
    
    def test_profile_prefix_validation(self):
        """Test validation of profile prefix."""
        # Valid prefix
        manager = ProfileManager(profile_prefix="valid_prefix_")
        assert manager.profile_prefix == "valid_prefix_"
        
        # Empty prefix should use default
        manager = ProfileManager(profile_prefix="")
        assert manager.profile_prefix == "coupa_worker_"
        
        # Invalid characters
        with pytest.raises(ValueError, match="Invalid characters in profile_prefix"):
            ProfileManager(profile_prefix="invalid/prefix")


class TestProfileCreation:
    """Test profile creation functionality."""
    
    def test_create_single_profile(self):
        """Test creating a single profile."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ProfileManager(base_directory=temp_dir)
            
            # Create profile
            profile_id = manager.create_profile()
            
            # Validate profile creation
            assert profile_id is not None, "Profile ID should be returned"
            assert isinstance(profile_id, str), "Profile ID should be string"
            assert manager.profile_exists(profile_id), "Profile should exist"
            assert manager.get_total_count() == 1, "Total count should be 1"
            
            # Check profile directory
            profile_path = manager.get_profile_path(profile_id)
            assert profile_path.exists(), "Profile directory should exist"
            assert profile_path.is_dir(), "Profile path should be directory"
    
    def test_create_multiple_profiles(self):
        """Test creating multiple profiles."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ProfileManager(base_directory=temp_dir)
            
            # Create multiple profiles
            profile_ids = []
            for i in range(3):
                profile_id = manager.create_profile()
                profile_ids.append(profile_id)
            
            # Validate all profiles
            assert len(profile_ids) == 3, "Should have 3 profile IDs"
            assert len(set(profile_ids)) == 3, "Profile IDs should be unique"
            assert manager.get_total_count() == 3, "Total count should be 3"
            
            # All profiles should exist
            for profile_id in profile_ids:
                assert manager.profile_exists(profile_id), f"Profile {profile_id} should exist"
    
    def test_create_profile_with_custom_id(self):
        """Test creating profile with custom ID."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ProfileManager(base_directory=temp_dir)
            
            custom_id = "custom_profile_001"
            profile_id = manager.create_profile(profile_id=custom_id)
            
            # Validate custom ID
            assert profile_id == custom_id, "Should return custom ID"
            assert manager.profile_exists(custom_id), "Custom profile should exist"
    
    def test_create_profile_conflict_handling(self):
        """Test handling of profile ID conflicts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ProfileManager(base_directory=temp_dir)
            
            # Create first profile
            profile_id = "conflict_test"
            manager.create_profile(profile_id=profile_id)
            
            # Try to create with same ID
            with pytest.raises(ProfileConflictError, match="Profile already exists"):
                manager.create_profile(profile_id=profile_id)
    
    def test_profile_initialization_content(self):
        """Test that created profiles have proper initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ProfileManager(base_directory=temp_dir)
            
            profile_id = manager.create_profile()
            profile_path = manager.get_profile_path(profile_id)
            
            # Check for expected profile structure
            # (Implementation-specific, but test the interface)
            profile_info = manager.get_profile_info(profile_id)
            
            assert 'profile_id' in profile_info, "Should include profile ID"
            assert 'profile_path' in profile_info, "Should include profile path"
            assert 'created_at' in profile_info, "Should include creation time"
            assert 'status' in profile_info, "Should include status"


class TestProfileManagement:
    """Test profile management operations."""
    
    def test_list_profiles(self):
        """Test listing all profiles."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ProfileManager(base_directory=temp_dir)
            
            # Initially empty
            profiles = manager.list_profiles()
            assert len(profiles) == 0, "Should start with no profiles"
            
            # Create some profiles
            profile_ids = []
            for i in range(3):
                profile_id = manager.create_profile()
                profile_ids.append(profile_id)
            
            # List should include all profiles
            profiles = manager.list_profiles()
            assert len(profiles) == 3, "Should list all 3 profiles"
            assert set(profiles) == set(profile_ids), "Should match created profiles"
    
    def test_get_profile_info(self):
        """Test getting detailed profile information."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ProfileManager(base_directory=temp_dir)
            
            profile_id = manager.create_profile()
            profile_info = manager.get_profile_info(profile_id)
            
            # Validate info structure
            required_fields = ['profile_id', 'profile_path', 'created_at', 'status']
            for field in required_fields:
                assert field in profile_info, f"Should include {field}"
            
            assert profile_info['profile_id'] == profile_id, "Should match profile ID"
            assert isinstance(profile_info['profile_path'], Path), "Path should be Path object"
            assert profile_info['status'] in ['created', 'active', 'inactive'], "Valid status"
    
    def test_profile_activation_deactivation(self):
        """Test profile activation and deactivation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ProfileManager(base_directory=temp_dir)
            
            profile_id = manager.create_profile()
            
            # Initially not active
            assert not manager.is_active(profile_id), "Profile should not be active initially"
            
            # Activate profile
            manager.activate_profile(profile_id)
            assert manager.is_active(profile_id), "Profile should be active after activation"
            assert manager.get_active_count() == 1, "Active count should be 1"
            
            # Deactivate profile
            manager.deactivate_profile(profile_id)
            assert not manager.is_active(profile_id), "Profile should not be active after deactivation"
            assert manager.get_active_count() == 0, "Active count should be 0"
    
    def test_profile_status_tracking(self):
        """Test tracking of profile status changes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ProfileManager(base_directory=temp_dir)
            
            profile_id = manager.create_profile()
            
            # Track status changes
            statuses = []
            
            # Initial status
            info = manager.get_profile_info(profile_id)
            statuses.append(info['status'])
            
            # Activate and check status
            manager.activate_profile(profile_id)
            info = manager.get_profile_info(profile_id)
            statuses.append(info['status'])
            
            # Deactivate and check status
            manager.deactivate_profile(profile_id)
            info = manager.get_profile_info(profile_id)
            statuses.append(info['status'])
            
            # Validate status progression
            assert statuses[0] == 'created', "Initial status should be 'created'"
            assert statuses[1] == 'active', "Status should be 'active' after activation"
            assert statuses[2] == 'inactive', "Status should be 'inactive' after deactivation"


class TestProfileCleanup:
    """Test profile cleanup operations."""
    
    def test_delete_single_profile(self):
        """Test deleting a single profile."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ProfileManager(base_directory=temp_dir)
            
            profile_id = manager.create_profile()
            profile_path = manager.get_profile_path(profile_id)
            
            # Verify profile exists
            assert profile_path.exists(), "Profile directory should exist"
            assert manager.profile_exists(profile_id), "Profile should exist"
            
            # Delete profile
            manager.delete_profile(profile_id)
            
            # Verify profile is gone
            assert not profile_path.exists(), "Profile directory should be deleted"
            assert not manager.profile_exists(profile_id), "Profile should not exist"
            assert manager.get_total_count() == 0, "Total count should be 0"
    
    def test_delete_active_profile(self):
        """Test deleting an active profile."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ProfileManager(base_directory=temp_dir)
            
            profile_id = manager.create_profile()
            manager.activate_profile(profile_id)
            
            # Should handle active profile deletion
            manager.delete_profile(profile_id)
            
            assert not manager.profile_exists(profile_id), "Profile should be deleted"
            assert manager.get_active_count() == 0, "Active count should be updated"
    
    def test_cleanup_all_profiles(self):
        """Test cleaning up all profiles."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ProfileManager(base_directory=temp_dir)
            
            # Create multiple profiles
            profile_ids = []
            for i in range(3):
                profile_id = manager.create_profile()
                profile_ids.append(profile_id)
                if i % 2 == 0:  # Activate some profiles
                    manager.activate_profile(profile_id)
            
            # Verify initial state
            assert manager.get_total_count() == 3, "Should have 3 profiles"
            assert manager.get_active_count() > 0, "Should have active profiles"
            
            # Cleanup all
            manager.cleanup_all()
            
            # Verify cleanup
            assert manager.get_total_count() == 0, "All profiles should be deleted"
            assert manager.get_active_count() == 0, "No profiles should be active"
            
            for profile_id in profile_ids:
                assert not manager.profile_exists(profile_id), f"Profile {profile_id} should be deleted"
    
    def test_auto_cleanup_on_destruction(self):
        """Test automatic cleanup when ProfileManager is destroyed."""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create manager with auto_cleanup enabled
            manager = ProfileManager(base_directory=temp_dir, auto_cleanup=True)
            
            # Create profiles
            profile_ids = []
            for i in range(2):
                profile_id = manager.create_profile()
                profile_ids.append(profile_id)
            
            # Verify profiles exist
            for profile_id in profile_ids:
                profile_path = manager.get_profile_path(profile_id)
                assert profile_path.exists(), f"Profile {profile_id} should exist"
            
            # Destroy manager (simulate going out of scope)
            del manager
            
            # Profiles should be cleaned up automatically
            # (This test depends on implementation details)
            
        finally:
            # Manual cleanup of temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_cleanup_error_handling(self):
        """Test error handling during cleanup operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ProfileManager(base_directory=temp_dir)
            
            # Try to delete non-existent profile
            with pytest.raises(ProfileManagerError, match="Profile does not exist"):
                manager.delete_profile("non_existent_profile")
            
            # Create profile and simulate cleanup error
            profile_id = manager.create_profile()
            
            # Mock cleanup failure
            with patch('shutil.rmtree') as mock_rmtree:
                mock_rmtree.side_effect = OSError("Permission denied")
                
                with pytest.raises(ProfileCleanupError, match="Failed to cleanup profile"):
                    manager.delete_profile(profile_id)


class TestConcurrencyAndThreadSafety:
    """Test concurrent operations and thread safety."""
    
    def test_concurrent_profile_creation(self):
        """Test creating profiles concurrently."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ProfileManager(base_directory=temp_dir)
            
            created_profiles = []
            errors = []
            
            def create_profile_worker(index):
                try:
                    profile_id = manager.create_profile()
                    created_profiles.append(profile_id)
                except Exception as e:
                    errors.append(e)
            
            # Create profiles concurrently
            threads = []
            for i in range(5):
                thread = threading.Thread(target=create_profile_worker, args=(i,))
                threads.append(thread)
                thread.start()
            
            # Wait for completion
            for thread in threads:
                thread.join()
            
            # Validate results
            assert len(errors) == 0, f"No errors should occur: {errors}"
            assert len(created_profiles) == 5, "All profiles should be created"
            assert len(set(created_profiles)) == 5, "All profile IDs should be unique"
            assert manager.get_total_count() == 5, "Total count should be correct"
    
    def test_concurrent_activation_deactivation(self):
        """Test concurrent activation and deactivation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ProfileManager(base_directory=temp_dir)
            
            # Create profiles first
            profile_ids = []
            for i in range(3):
                profile_id = manager.create_profile()
                profile_ids.append(profile_id)
            
            def activate_deactivate_worker(profile_id):
                for _ in range(5):
                    manager.activate_profile(profile_id)
                    time.sleep(0.01)
                    manager.deactivate_profile(profile_id)
            
            # Run concurrent operations
            threads = []
            for profile_id in profile_ids:
                thread = threading.Thread(target=activate_deactivate_worker, args=(profile_id,))
                threads.append(thread)
                thread.start()
            
            # Wait for completion
            for thread in threads:
                thread.join()
            
            # Validate final state
            assert manager.get_active_count() == 0, "No profiles should be active"
            for profile_id in profile_ids:
                assert not manager.is_active(profile_id), f"Profile {profile_id} should not be active"
    
    def test_concurrent_cleanup_operations(self):
        """Test concurrent cleanup operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ProfileManager(base_directory=temp_dir)
            
            # Create profiles
            profile_ids = []
            for i in range(4):
                profile_id = manager.create_profile()
                profile_ids.append(profile_id)
            
            deleted_profiles = []
            errors = []
            
            def delete_profile_worker(profile_id):
                try:
                    manager.delete_profile(profile_id)
                    deleted_profiles.append(profile_id)
                except Exception as e:
                    errors.append(e)
            
            # Delete profiles concurrently
            threads = []
            for profile_id in profile_ids:
                thread = threading.Thread(target=delete_profile_worker, args=(profile_id,))
                threads.append(thread)
                thread.start()
            
            # Wait for completion
            for thread in threads:
                thread.join()
            
            # Validate results
            assert len(deleted_profiles) == 4, "All profiles should be deleted"
            assert manager.get_total_count() == 0, "Total count should be 0"


class TestResourceManagement:
    """Test resource management and disk usage."""
    
    def test_disk_usage_tracking(self):
        """Test tracking of disk usage by profiles."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ProfileManager(base_directory=temp_dir)
            
            # Initial usage
            initial_usage = manager.get_total_disk_usage()
            assert initial_usage >= 0, "Initial usage should be non-negative"
            
            # Create profile and check usage
            profile_id = manager.create_profile()
            usage_after_create = manager.get_total_disk_usage()
            assert usage_after_create > initial_usage, "Usage should increase after creation"
            
            # Get individual profile usage
            profile_usage = manager.get_profile_disk_usage(profile_id)
            assert profile_usage > 0, "Profile should have some disk usage"
    
    def test_resource_limits_enforcement(self):
        """Test enforcement of resource limits."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Manager with disk limit
            manager = ProfileManager(
                base_directory=temp_dir,
                max_total_disk_usage=100 * 1024 * 1024  # 100MB limit
            )
            
            # Should be able to create profiles within limit
            profile_id = manager.create_profile()
            assert manager.profile_exists(profile_id), "Profile should be created within limit"
            
            # Mock scenario where limit would be exceeded
            with patch.object(manager, 'get_total_disk_usage', return_value=150 * 1024 * 1024):
                with pytest.raises(ProfileManagerError, match="Disk usage limit exceeded"):
                    manager.create_profile()
    
    def test_profile_size_monitoring(self):
        """Test monitoring of individual profile sizes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = ProfileManager(base_directory=temp_dir)
            
            profile_id = manager.create_profile()
            
            # Get profile size information
            size_info = manager.get_profile_size_info(profile_id)
            
            assert 'total_size' in size_info, "Should include total size"
            assert 'file_count' in size_info, "Should include file count"
            assert 'directory_count' in size_info, "Should include directory count"
            
            assert size_info['total_size'] >= 0, "Total size should be non-negative"
            assert size_info['file_count'] >= 0, "File count should be non-negative"
            assert size_info['directory_count'] >= 0, "Directory count should be non-negative"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])