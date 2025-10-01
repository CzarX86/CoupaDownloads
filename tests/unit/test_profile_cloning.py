"""Unit tests for profile cloning logic.

These tests validate the core profile cloning functionality,
including directory copying, file filtering, and error handling.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import shutil
import tempfile
import os

# These imports will fail until implementations exist - tests should fail
try:
    from EXPERIMENTAL.workers.profile_manager import ProfileManager
    from EXPERIMENTAL.workers.profile_cloning import ProfileCloner
    from specs.parallel_profile_clone.contracts.profile_manager_contract import (
        ProfileType,
        InsufficientSpaceException,
        PermissionDeniedException,
        ProfileCorruptedException
    )
except ImportError as e:
    pytest.skip(f"Implementation not available: {e}", allow_module_level=True)


class TestProfileCloning:
    """Test profile cloning operations."""
    
    @pytest.fixture
    def source_profile(self, tmp_path):
        """Create a source profile with realistic structure."""
        profile_dir = tmp_path / "source_profile"
        profile_dir.mkdir()
        
        # Create realistic profile structure
        (profile_dir / "Preferences").write_text('{"profile": {"name": "Default"}}')
        (profile_dir / "Local State").write_text('{"profile": {"info_cache": {}}}')
        (profile_dir / "Cookies").write_bytes(b"SQLite format 3\x00" + b"\x00" * 100)
        
        # Create subdirectories
        (profile_dir / "Cache").mkdir()
        (profile_dir / "Cache" / "data_1").write_bytes(b"cache data")
        
        (profile_dir / "Local Storage").mkdir()
        (profile_dir / "Local Storage" / "leveldb").mkdir()
        (profile_dir / "Local Storage" / "leveldb" / "000003.log").write_bytes(b"leveldb data")
        
        # Create session storage
        (profile_dir / "Session Storage").mkdir()
        (profile_dir / "Session Storage" / "LOG").write_text("session log")
        
        return profile_dir
    
    @pytest.fixture
    def cloner(self, tmp_path):
        """Create ProfileCloner instance for testing."""
        return ProfileCloner(
            temp_directory=tmp_path / "clones",
            copy_buffer_size=8192,
            preserve_permissions=True
        )
    
    def test_profile_cloner_creates_exact_copy(self, cloner, source_profile, tmp_path):
        """Test ProfileCloner creates exact copy of source profile."""
        worker_id = 1
        clone_path = cloner.clone_profile(source_profile, worker_id)
        
        # Verify clone exists
        assert clone_path.exists()
        assert clone_path.is_dir()
        
        # Verify all files are copied
        assert (clone_path / "Preferences").exists()
        assert (clone_path / "Local State").exists()
        assert (clone_path / "Cookies").exists()
        
        # Verify subdirectories are copied
        assert (clone_path / "Cache").exists()
        assert (clone_path / "Cache" / "data_1").exists()
        assert (clone_path / "Local Storage" / "leveldb").exists()
        assert (clone_path / "Session Storage" / "LOG").exists()
    
    def test_profile_cloner_preserves_file_content(self, cloner, source_profile):
        """Test ProfileCloner preserves file content exactly."""
        clone_path = cloner.clone_profile(source_profile, worker_id=2)
        
        # Check file contents match exactly
        original_prefs = (source_profile / "Preferences").read_text()
        cloned_prefs = (clone_path / "Preferences").read_text()
        assert original_prefs == cloned_prefs
        
        original_cookies = (source_profile / "Cookies").read_bytes()
        cloned_cookies = (clone_path / "Cookies").read_bytes()
        assert original_cookies == cloned_cookies
    
    def test_profile_cloner_handles_special_files(self, cloner, source_profile):
        """Test ProfileCloner handles special files (locks, temp files)."""
        # Add lock file and temp files that should be excluded
        (source_profile / "SingletonLock").write_text("lock")
        (source_profile / "temp_file.tmp").write_text("temporary")
        (source_profile / ".DS_Store").write_text("system")
        
        clone_path = cloner.clone_profile(source_profile, worker_id=3)
        
        # Verify regular files are copied
        assert (clone_path / "Preferences").exists()
        
        # Verify special files are excluded
        assert not (clone_path / "SingletonLock").exists()
        assert not (clone_path / "temp_file.tmp").exists()
        assert not (clone_path / ".DS_Store").exists()
    
    @patch('shutil.copytree')
    def test_profile_cloner_uses_ignore_patterns(self, mock_copytree, cloner, source_profile):
        """Test ProfileCloner uses appropriate ignore patterns."""
        cloner.clone_profile(source_profile, worker_id=4)
        
        # Verify copytree was called with ignore function
        mock_copytree.assert_called_once()
        args, kwargs = mock_copytree.call_args
        assert 'ignore' in kwargs
        assert callable(kwargs['ignore'])
    
    def test_profile_cloner_creates_unique_paths(self, cloner, source_profile):
        """Test ProfileCloner creates unique paths for different workers."""
        clone1 = cloner.clone_profile(source_profile, worker_id=1)
        clone2 = cloner.clone_profile(source_profile, worker_id=2)
        clone3 = cloner.clone_profile(source_profile, worker_id=3)
        
        # All paths should be different
        assert clone1 != clone2 != clone3
        assert clone1 != clone3
        
        # All clones should exist
        assert clone1.exists() and clone2.exists() and clone3.exists()
    
    @patch('shutil.disk_usage')
    def test_profile_cloner_checks_disk_space(self, mock_disk_usage, cloner, source_profile):
        """Test ProfileCloner checks available disk space before cloning."""
        # Mock insufficient disk space
        mock_disk_usage.return_value = (1000000, 950000, 50000)  # 50KB free
        
        with pytest.raises(InsufficientSpaceException):
            cloner.clone_profile(source_profile, worker_id=5)
    
    def test_profile_cloner_estimates_profile_size(self, cloner, source_profile):
        """Test ProfileCloner accurately estimates profile size."""
        estimated_size = cloner.estimate_profile_size(source_profile)
        
        # Should return reasonable estimate
        assert estimated_size > 0
        
        # Should be close to actual directory size
        actual_size = sum(f.stat().st_size for f in source_profile.rglob('*') if f.is_file())
        assert abs(estimated_size - actual_size) < actual_size * 0.1  # Within 10%
    
    @patch('os.makedirs')
    def test_profile_cloner_handles_permission_errors(self, mock_makedirs, cloner, source_profile):
        """Test ProfileCloner handles permission errors gracefully."""
        mock_makedirs.side_effect = PermissionError("Access denied")
        
        with pytest.raises(PermissionDeniedException):
            cloner.clone_profile(source_profile, worker_id=6)
    
    def test_profile_cloner_validates_source_profile(self, cloner, tmp_path):
        """Test ProfileCloner validates source profile before cloning."""
        # Test with non-existent source
        nonexistent = tmp_path / "nonexistent"
        with pytest.raises(FileNotFoundError):
            cloner.clone_profile(nonexistent, worker_id=7)
        
        # Test with file instead of directory
        file_path = tmp_path / "file.txt"
        file_path.write_text("not a directory")
        with pytest.raises(ProfileCorruptedException):
            cloner.clone_profile(file_path, worker_id=8)
    
    def test_profile_cloner_cleanup_removes_clone(self, cloner, source_profile):
        """Test ProfileCloner cleanup removes cloned directory."""
        clone_path = cloner.clone_profile(source_profile, worker_id=9)
        assert clone_path.exists()
        
        # Cleanup clone
        cloner.cleanup_clone(clone_path)
        
        # Clone should be removed
        assert not clone_path.exists()
    
    def test_profile_cloner_cleanup_preserves_source(self, cloner, source_profile):
        """Test ProfileCloner cleanup never removes source profile."""
        clone_path = cloner.clone_profile(source_profile, worker_id=10)
        
        # Try to cleanup source (should be no-op or raise error)
        cloner.cleanup_clone(source_profile)
        
        # Source should still exist
        assert source_profile.exists()
    
    def test_profile_cloner_concurrent_cloning(self, cloner, source_profile):
        """Test ProfileCloner handles concurrent cloning operations."""
        import threading
        import time
        
        results = {}
        errors = {}
        
        def clone_worker(worker_id):
            try:
                result = cloner.clone_profile(source_profile, worker_id)
                results[worker_id] = result
            except Exception as e:
                errors[worker_id] = e
        
        # Start multiple cloning operations concurrently
        threads = []
        for worker_id in range(1, 6):  # 5 concurrent workers
            thread = threading.Thread(target=clone_worker, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        # All should succeed with unique paths
        assert len(errors) == 0, f"Concurrent cloning errors: {errors}"
        assert len(results) == 5
        
        # All paths should be unique
        paths = list(results.values())
        assert len(set(paths)) == len(paths)
    
    @patch('EXPERIMENTAL.workers.profile_cloning.time.time')
    def test_profile_cloner_tracks_timing(self, mock_time, cloner, source_profile):
        """Test ProfileCloner tracks cloning operation timing."""
        mock_time.side_effect = [100.0, 105.5]  # 5.5 second operation
        
        with patch.object(cloner, '_perform_copy') as mock_copy:
            clone_path = cloner.clone_profile(source_profile, worker_id=11)
            
            # Should have timing information
            assert hasattr(cloner, 'last_clone_duration')
            assert cloner.last_clone_duration == 5.5
