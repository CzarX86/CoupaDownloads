"""Unit tests for ProfileManager initialization.

These tests validate ProfileManager initialization logic,
configuration validation, and basic setup operations.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# These imports will fail until implementations exist - tests should fail
try:
    from EXPERIMENTAL.workers.profile_manager import ProfileManager
    from specs.parallel_profile_clone.contracts.profile_manager_contract import (
        VerificationConfig,
        VerificationMethod,
        RetryConfig,
        ProfileLockedException,
        InsufficientSpaceException,
        PermissionDeniedException,
        ProfileCorruptedException
    )
except ImportError as e:
    pytest.skip(f"Implementation not available: {e}", allow_module_level=True)


class TestProfileManagerInitialization:
    """Test ProfileManager initialization and configuration."""
    
    @pytest.fixture
    def valid_base_profile(self, tmp_path):
        """Create a valid base profile directory."""
        profile_dir = tmp_path / "valid_profile"
        profile_dir.mkdir()
        # Create required profile files
        (profile_dir / "Preferences").write_text('{"profile": {"name": "Default"}}')
        (profile_dir / "Local State").write_text('{"profile": {"info_cache": {}}}')
        (profile_dir / "Cookies").write_text("SQLite format 3\x00")
        return profile_dir
    
    @pytest.fixture
    def verification_config(self):
        """Create valid verification configuration."""
        return VerificationConfig(
            enabled_methods=[VerificationMethod.CAPABILITY_CHECK, VerificationMethod.AUTH_CHECK],
            capability_timeout=5.0,
            auth_check_timeout=15.0,
            auth_check_url="https://test.coupa.com/api/health",
            retry_config=RetryConfig(max_attempts=2, base_delay=1.0)
        )
    
    def test_profile_manager_initialization_with_valid_parameters(self, valid_base_profile, verification_config, tmp_path):
        """Test ProfileManager initializes correctly with valid parameters."""
        temp_dir = tmp_path / "temp_profiles"
        
        manager = ProfileManager(
            base_profile_path=valid_base_profile,
            temp_directory=temp_dir,
            max_concurrent_clones=3,
            clone_timeout=30.0,
            verification_config=verification_config
        )
        
        assert manager.base_profile_path == valid_base_profile
        assert manager.temp_directory == temp_dir
        assert manager.max_concurrent_clones == 3
        assert manager.clone_timeout == 30.0
        assert manager.verification_config == verification_config
    
    def test_profile_manager_initialization_with_defaults(self, valid_base_profile):
        """Test ProfileManager uses appropriate defaults for optional parameters."""
        manager = ProfileManager(base_profile_path=valid_base_profile)
        
        # Should have reasonable defaults
        assert manager.temp_directory is not None
        assert manager.max_concurrent_clones > 0
        assert manager.clone_timeout > 0
        assert manager.verification_config is not None
    
    def test_profile_manager_initialization_creates_temp_directory(self, valid_base_profile, tmp_path):
        """Test ProfileManager creates temp directory if it doesn't exist."""
        temp_dir = tmp_path / "nonexistent_temp"
        assert not temp_dir.exists()
        
        manager = ProfileManager(
            base_profile_path=valid_base_profile,
            temp_directory=temp_dir
        )
        
        # Temp directory should be created during initialization
        assert temp_dir.exists()
        assert temp_dir.is_dir()
    
    def test_profile_manager_initialization_validates_base_profile_exists(self, tmp_path):
        """Test ProfileManager raises error if base profile doesn't exist."""
        nonexistent_profile = tmp_path / "nonexistent_profile"
        
        with pytest.raises((FileNotFoundError, ProfileCorruptedException)):
            ProfileManager(base_profile_path=nonexistent_profile)
    
    def test_profile_manager_initialization_validates_base_profile_structure(self, tmp_path):
        """Test ProfileManager validates base profile structure."""
        incomplete_profile = tmp_path / "incomplete_profile"
        incomplete_profile.mkdir()
        # Missing required files
        
        with pytest.raises(ProfileCorruptedException):
            ProfileManager(base_profile_path=incomplete_profile)
    
    def test_profile_manager_initialization_validates_permissions(self, valid_base_profile, tmp_path):
        """Test ProfileManager validates directory permissions."""
        # Create temp directory with restricted permissions
        restricted_temp = tmp_path / "restricted_temp"
        restricted_temp.mkdir(mode=0o444)  # Read-only
        
        with pytest.raises(PermissionDeniedException):
            ProfileManager(
                base_profile_path=valid_base_profile,
                temp_directory=restricted_temp
            )
    
    def test_profile_manager_initialization_validates_clone_parameters(self, valid_base_profile):
        """Test ProfileManager validates clone-related parameters."""
        # Test invalid max_concurrent_clones
        with pytest.raises(ValueError):
            ProfileManager(
                base_profile_path=valid_base_profile,
                max_concurrent_clones=0
            )
        
        with pytest.raises(ValueError):
            ProfileManager(
                base_profile_path=valid_base_profile,
                max_concurrent_clones=-1
            )
    
    def test_profile_manager_initialization_validates_timeout_parameters(self, valid_base_profile):
        """Test ProfileManager validates timeout parameters."""
        # Test invalid clone_timeout
        with pytest.raises(ValueError):
            ProfileManager(
                base_profile_path=valid_base_profile,
                clone_timeout=0
            )
        
        with pytest.raises(ValueError):
            ProfileManager(
                base_profile_path=valid_base_profile,
                clone_timeout=-5.0
            )
    
    def test_profile_manager_initialization_validates_verification_config(self, valid_base_profile):
        """Test ProfileManager validates verification configuration."""
        # Test invalid verification config
        invalid_config = VerificationConfig(
            enabled_methods=[],  # Empty methods list should be invalid
        )
        
        with pytest.raises(ValueError):
            ProfileManager(
                base_profile_path=valid_base_profile,
                verification_config=invalid_config
            )
    
    @patch('EXPERIMENTAL.workers.profile_manager.shutil.disk_usage')
    def test_profile_manager_initialization_checks_disk_space(self, mock_disk_usage, valid_base_profile, tmp_path):
        """Test ProfileManager checks available disk space."""
        # Mock insufficient disk space
        mock_disk_usage.return_value = (1000000, 900000, 100000)  # total, used, free (100KB free)
        
        with pytest.raises(InsufficientSpaceException):
            ProfileManager(
                base_profile_path=valid_base_profile,
                temp_directory=tmp_path / "temp"
            )
    
    @patch('EXPERIMENTAL.workers.profile_manager.os.path.exists')
    def test_profile_manager_initialization_detects_profile_lock(self, mock_exists, valid_base_profile):
        """Test ProfileManager detects locked base profile."""
        # Mock profile lock file exists
        mock_exists.side_effect = lambda path: str(path).endswith('SingletonLock')
        
        with pytest.raises(ProfileLockedException):
            ProfileManager(base_profile_path=valid_base_profile)
    
    def test_profile_manager_initialization_sets_up_logging(self, valid_base_profile):
        """Test ProfileManager sets up structured logging."""
        with patch('EXPERIMENTAL.workers.profile_manager.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            manager = ProfileManager(base_profile_path=valid_base_profile)
            
            # Should have set up logger
            mock_get_logger.assert_called_once()
            assert hasattr(manager, 'logger')
    
    def test_profile_manager_initialization_sets_up_concurrency_control(self, valid_base_profile):
        """Test ProfileManager sets up concurrency control mechanisms."""
        manager = ProfileManager(
            base_profile_path=valid_base_profile,
            max_concurrent_clones=3
        )
        
        # Should have concurrency control attributes
        assert hasattr(manager, '_clone_semaphore')
        assert hasattr(manager, '_active_profiles')
        assert hasattr(manager, '_profile_lock')
    
    def test_profile_manager_initialization_loads_platform_config(self, valid_base_profile):
        """Test ProfileManager loads appropriate platform configuration."""
        with patch('EXPERIMENTAL.workers.profile_manager.get_platform_config') as mock_get_config:
            mock_config = MagicMock()
            mock_get_config.return_value = mock_config
            
            manager = ProfileManager(base_profile_path=valid_base_profile)
            
            # Should have loaded platform config
            mock_get_config.assert_called_once()
            assert manager.platform_config == mock_config
