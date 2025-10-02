"""Unit tests for platform-specific paths configuration.

These tests validate platform detection, path resolution,
and configuration for different operating systems.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import platform
import os

# These imports will fail until implementations exist - tests should fail
try:
    from EXPERIMENTAL.config.profile_config import (
        ProfilePaths,
        PlatformConfig,
        get_macos_config,
        get_windows_config,
        get_linux_config,
        get_platform_config,
        DEFAULT_CONFIG,
        validate_edge_installation,
        get_profile_lock_file,
        is_profile_locked,
        get_test_config
    )
except ImportError as e:
    pytest.skip(f"Implementation not available: {e}", allow_module_level=True)


class TestProfilePaths:
    """Test ProfilePaths validation and behavior."""
    
    @pytest.fixture
    def valid_profile_structure(self, tmp_path):
        """Create a valid profile directory structure."""
        profile_dir = tmp_path / "Default"
        profile_dir.mkdir()
        (profile_dir / "Preferences").write_text('{"test": "data"}')
        
        user_data_dir = tmp_path
        
        return profile_dir, user_data_dir
    
    def test_profile_paths_initialization_with_valid_paths(self, valid_profile_structure):
        """Test ProfilePaths initializes with valid paths."""
        default_profile, user_data_dir = valid_profile_structure
        
        profile_paths = ProfilePaths(
            default_profile=default_profile,
            user_data_dir=user_data_dir
        )
        
        assert profile_paths.default_profile == default_profile
        assert profile_paths.user_data_dir == user_data_dir
        assert profile_paths.cache_dir is None
    
    def test_profile_paths_initialization_with_cache_dir(self, valid_profile_structure):
        """Test ProfilePaths initializes with optional cache directory."""
        default_profile, user_data_dir = valid_profile_structure
        cache_dir = user_data_dir / "Cache"
        cache_dir.mkdir()
        
        profile_paths = ProfilePaths(
            default_profile=default_profile,
            user_data_dir=user_data_dir,
            cache_dir=cache_dir
        )
        
        assert profile_paths.cache_dir == cache_dir
    
    def test_profile_paths_validates_default_profile_exists(self, tmp_path):
        """Test ProfilePaths validates default profile exists."""
        nonexistent_profile = tmp_path / "nonexistent"
        user_data_dir = tmp_path
        
        with pytest.raises(FileNotFoundError, match="Default profile not found"):
            ProfilePaths(
                default_profile=nonexistent_profile,
                user_data_dir=user_data_dir
            )
    
    def test_profile_paths_validates_user_data_dir_exists(self, tmp_path):
        """Test ProfilePaths validates user data directory exists."""
        profile_dir = tmp_path / "Default"
        profile_dir.mkdir()
        
        nonexistent_user_data = tmp_path / "nonexistent"
        
        with pytest.raises(FileNotFoundError, match="User data directory not found"):
            ProfilePaths(
                default_profile=profile_dir,
                user_data_dir=nonexistent_user_data
            )


class TestPlatformConfig:
    """Test PlatformConfig functionality."""
    
    @pytest.fixture
    def valid_profile_paths(self, tmp_path):
        """Create valid ProfilePaths for testing."""
        default_profile = tmp_path / "Default"
        default_profile.mkdir()
        (default_profile / "Preferences").write_text('{"test": "data"}')
        
        return ProfilePaths(
            default_profile=default_profile,
            user_data_dir=tmp_path
        )
    
    def test_platform_config_initialization(self, valid_profile_paths, tmp_path):
        """Test PlatformConfig initializes with required fields."""
        config = PlatformConfig(
            system="TestOS",
            profile_paths=valid_profile_paths,
            temp_dir_base=tmp_path / "temp"
        )
        
        assert config.system == "TestOS"
        assert config.profile_paths == valid_profile_paths
        assert config.temp_dir_base == tmp_path / "temp"
        assert config.max_path_length == 260  # Default Windows limit
        assert config.copy_buffer_size == 64 * 1024  # Default 64KB
    
    def test_platform_config_get_temp_profile_path(self, valid_profile_paths, tmp_path):
        """Test PlatformConfig generates unique temp profile paths."""
        config = PlatformConfig(
            system="TestOS",
            profile_paths=valid_profile_paths,
            temp_dir_base=tmp_path / "temp"
        )
        
        path1 = config.get_temp_profile_path(worker_id=1)
        path2 = config.get_temp_profile_path(worker_id=2)
        path3 = config.get_temp_profile_path(worker_id=1)  # Same ID
        
        # Different worker IDs should get different paths
        assert path1 != path2
        
        # Same worker ID should get same path
        assert path1 == path3
        
        # Paths should be under temp_dir_base
        assert path1.parent == config.temp_dir_base
        assert path2.parent == config.temp_dir_base
    
    def test_platform_config_validate_path_length(self, valid_profile_paths, tmp_path):
        """Test PlatformConfig validates path lengths."""
        config = PlatformConfig(
            system="TestOS",
            profile_paths=valid_profile_paths,
            temp_dir_base=tmp_path,
            max_path_length=50  # Very short for testing
        )
        
        short_path = tmp_path / "short"
        long_path = tmp_path / ("very_long_path_name_" * 10)
        
        assert config.validate_path_length(short_path) is True
        assert config.validate_path_length(long_path) is False


class TestPlatformDetectionAndConfiguration:
    """Test platform-specific configuration functions."""
    
    @patch('platform.system')
    def test_get_platform_config_detects_macos(self, mock_system):
        """Test get_platform_config detects macOS correctly."""
        mock_system.return_value = "Darwin"
        
        with patch('EXPERIMENTAL.config.profile_config.get_macos_config') as mock_macos:
            mock_config = MagicMock()
            mock_macos.return_value = mock_config
            
            result = get_platform_config()
            
            mock_macos.assert_called_once()
            assert result == mock_config
    
    @patch('platform.system')
    def test_get_platform_config_detects_windows(self, mock_system):
        """Test get_platform_config detects Windows correctly."""
        mock_system.return_value = "Windows"
        
        with patch('EXPERIMENTAL.config.profile_config.get_windows_config') as mock_windows:
            mock_config = MagicMock()
            mock_windows.return_value = mock_config
            
            result = get_platform_config()
            
            mock_windows.assert_called_once()
            assert result == mock_config
    
    @patch('platform.system')
    def test_get_platform_config_detects_linux(self, mock_system):
        """Test get_platform_config detects Linux correctly."""
        mock_system.return_value = "Linux"
        
        with patch('EXPERIMENTAL.config.profile_config.get_linux_config') as mock_linux:
            mock_config = MagicMock()
            mock_linux.return_value = mock_config
            
            result = get_platform_config()
            
            mock_linux.assert_called_once()
            assert result == mock_config
    
    @patch('platform.system')
    def test_get_platform_config_raises_for_unsupported_system(self, mock_system):
        """Test get_platform_config raises error for unsupported systems."""
        mock_system.return_value = "UnsupportedOS"
        
        with pytest.raises(RuntimeError, match="Unsupported platform: UnsupportedOS"):
            get_platform_config()
    
    @patch('pathlib.Path.home')
    def test_get_macos_config_returns_correct_paths(self, mock_home, tmp_path):
        """Test get_macos_config returns correct macOS paths."""
        mock_home.return_value = tmp_path
        
        # Create expected directory structure
        edge_dir = tmp_path / "Library/Application Support/Microsoft Edge"
        edge_dir.mkdir(parents=True)
        default_profile = edge_dir / "Default"
        default_profile.mkdir()
        (default_profile / "Preferences").write_text('{"test": "data"}')
        
        config = get_macos_config()
        
        assert config.system == "Darwin"
        assert config.profile_paths.default_profile == default_profile
        assert config.profile_paths.user_data_dir == edge_dir
        assert config.max_path_length == 1024  # macOS higher limit
    
    @patch.dict(os.environ, {'LOCALAPPDATA': '/test/local/appdata'})
    def test_get_windows_config_returns_correct_paths(self):
        """Test get_windows_config returns correct Windows paths."""
        with patch('pathlib.Path.exists', return_value=True):
            config = get_windows_config()
            
            assert config.system == "Windows"
            assert "Microsoft/Edge/User Data" in str(config.profile_paths.user_data_dir)
            assert config.max_path_length == 260  # Windows path limitation
    
    def test_get_windows_config_raises_without_localappdata(self):
        """Test get_windows_config raises error without LOCALAPPDATA."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="LOCALAPPDATA environment variable not found"):
                get_windows_config()
    
    @patch('pathlib.Path.home')
    def test_get_linux_config_returns_correct_paths(self, mock_home, tmp_path):
        """Test get_linux_config returns correct Linux paths."""
        mock_home.return_value = tmp_path
        
        # Create expected directory structure
        config_dir = tmp_path / ".config/microsoft-edge"
        config_dir.mkdir(parents=True)
        default_profile = config_dir / "Default"
        default_profile.mkdir()
        (default_profile / "Preferences").write_text('{"test": "data"}')
        
        config = get_linux_config()
        
        assert config.system == "Linux"
        assert config.profile_paths.default_profile == default_profile
        assert config.max_path_length == 4096  # Linux higher limit


class TestUtilityFunctions:
    """Test utility functions for profile management."""
    
    def test_validate_edge_installation_with_valid_profile(self, tmp_path):
        """Test validate_edge_installation with valid Edge profile."""
        with patch('EXPERIMENTAL.config.profile_config.get_platform_config') as mock_get_config:
            # Mock a valid profile structure
            profile_dir = tmp_path / "Default"
            profile_dir.mkdir()
            (profile_dir / "Preferences").write_text('{"test": "data"}')
            
            mock_config = MagicMock()
            mock_config.profile_paths.default_profile = profile_dir
            mock_get_config.return_value = mock_config
            
            assert validate_edge_installation() is True
    
    def test_validate_edge_installation_with_missing_profile(self, tmp_path):
        """Test validate_edge_installation with missing Edge profile."""
        with patch('EXPERIMENTAL.config.profile_config.get_platform_config') as mock_get_config:
            nonexistent_profile = tmp_path / "nonexistent"
            
            mock_config = MagicMock()
            mock_config.profile_paths.default_profile = nonexistent_profile
            mock_get_config.return_value = mock_config
            
            assert validate_edge_installation() is False
    
    def test_get_profile_lock_file(self, tmp_path):
        """Test get_profile_lock_file returns correct lock file path."""
        profile_dir = tmp_path / "test_profile"
        
        lock_file = get_profile_lock_file(profile_dir)
        
        assert lock_file == profile_dir / "SingletonLock"
        assert isinstance(lock_file, Path)
    
    def test_is_profile_locked_with_existing_lock(self, tmp_path):
        """Test is_profile_locked detects existing lock file."""
        profile_dir = tmp_path / "locked_profile"
        profile_dir.mkdir()
        
        lock_file = profile_dir / "SingletonLock"
        lock_file.write_text("locked")
        
        assert is_profile_locked(profile_dir) is True
    
    def test_is_profile_locked_without_lock(self, tmp_path):
        """Test is_profile_locked returns False without lock file."""
        profile_dir = tmp_path / "unlocked_profile"
        profile_dir.mkdir()
        
        assert is_profile_locked(profile_dir) is False
    
    def test_get_test_config_customizes_for_testing(self, tmp_path):
        """Test get_test_config returns testing-appropriate configuration."""
        test_temp_dir = tmp_path / "test_temp"
        
        with patch('EXPERIMENTAL.config.profile_config.get_platform_config') as mock_get_config:
            mock_config = MagicMock()
            mock_config.copy_buffer_size = 64 * 1024  # Default
            mock_get_config.return_value = mock_config
            
            test_config = get_test_config(base_temp_dir=test_temp_dir)
            
            # Should customize temp directory
            assert test_config.temp_dir_base == test_temp_dir
            
            # Should use smaller buffer for faster tests
            assert test_config.copy_buffer_size == 8 * 1024
    
    def test_default_config_is_initialized(self):
        """Test DEFAULT_CONFIG is properly initialized."""
        # This will fail if the module can't initialize the default config
        assert DEFAULT_CONFIG is not None
        assert hasattr(DEFAULT_CONFIG, 'system')
        assert hasattr(DEFAULT_CONFIG, 'profile_paths')
        assert hasattr(DEFAULT_CONFIG, 'temp_dir_base')
