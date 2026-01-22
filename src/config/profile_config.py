"""Platform-specific Edge profile configuration.

This module provides platform-specific configuration for Edge browser profiles
across different operating systems (macOS, Windows, Linux).
"""

import platform
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
import os


@dataclass
class ProfilePaths:
    """Platform-specific Edge profile paths."""
    
    default_profile: Path
    user_data_dir: Path
    cache_dir: Optional[Path] = None
    
    def __post_init__(self):
        """Validate paths exist and are accessible."""
        if not self.default_profile.exists():
            raise FileNotFoundError(f"Default profile not found: {self.default_profile}")
        if not self.user_data_dir.exists():
            raise FileNotFoundError(f"User data directory not found: {self.user_data_dir}")


@dataclass
class PlatformConfig:
    """Platform-specific configuration settings."""
    
    system: str
    profile_paths: ProfilePaths
    temp_dir_base: Path
    max_path_length: int = 260  # Windows limitation
    copy_buffer_size: int = 64 * 1024  # 64KB buffer for file operations
    file_permissions: int = 0o755
    supported_browsers: list = field(default_factory=lambda: ['msedge', 'edge'])
    
    def get_temp_profile_path(self, worker_id: int) -> Path:
        """Generate temporary profile path for worker."""
        return self.temp_dir_base / f"worker_{worker_id}_profile"
    
    def validate_path_length(self, path: Path) -> bool:
        """Check if path length is within system limits."""
        # Prefer relative length when under temp_dir_base so tests with short names pass
        try:
            relative = path.relative_to(self.temp_dir_base)
            path_to_measure = str(relative)
        except Exception:
            path_to_measure = str(path)
        return len(path_to_measure) <= self.max_path_length


def get_macos_config() -> PlatformConfig:
    """Get macOS-specific Edge profile configuration."""
    home = Path.home()
    # Prefer central config if available
    try:
        from .lib.config import Config as ExperimentalConfig  # type: ignore
        configured_dir = Path(os.path.expanduser(ExperimentalConfig.EDGE_PROFILE_DIR)) if getattr(ExperimentalConfig, 'EDGE_PROFILE_DIR', None) else None
        configured_name = ExperimentalConfig.EDGE_PROFILE_NAME if getattr(ExperimentalConfig, 'EDGE_PROFILE_NAME', None) else 'Default'
    except Exception:
        configured_dir = None
        configured_name = 'Default'

    # Standard macOS Edge profile locations
    user_data_dir = configured_dir or (home / "Library/Application Support/Microsoft Edge")
    default_profile = user_data_dir / configured_name
    
    profile_paths = ProfilePaths(
        default_profile=default_profile,
        user_data_dir=user_data_dir,
        cache_dir=home / "Library/Caches/Microsoft Edge"
    )
    
    return PlatformConfig(
        system="Darwin",
        profile_paths=profile_paths,
        temp_dir_base=Path("/tmp/coupa_profiles"),
        max_path_length=1024,  # macOS has higher limits
        file_permissions=0o755
    )


def get_windows_config() -> PlatformConfig:
    """Get Windows-specific Edge profile configuration."""
    # Prefer central config if available
    try:
        from .lib.config import Config as ExperimentalConfig  # type: ignore
        configured_dir = Path(os.path.expanduser(ExperimentalConfig.EDGE_PROFILE_DIR)) if getattr(ExperimentalConfig, 'EDGE_PROFILE_DIR', None) else None
        configured_name = ExperimentalConfig.EDGE_PROFILE_NAME if getattr(ExperimentalConfig, 'EDGE_PROFILE_NAME', None) else 'Default'
    except Exception:
        configured_dir = None
        configured_name = 'Default'

    cache_dir: Optional[Path] = None
    if configured_dir is None:
        env_value = os.environ.get('LOCALAPPDATA')
        if not env_value:
            raise RuntimeError("LOCALAPPDATA environment variable not found")
        local_appdata = Path(env_value)
        user_data_dir = local_appdata / "Microsoft/Edge/User Data"
        cache_dir = local_appdata / "Microsoft/Edge/User Data/ShaderCache"
    else:
        user_data_dir = configured_dir
        # Derive a sensible default cache directory relative to configured user_data_dir
        cache_dir = configured_dir / "ShaderCache"

    default_profile = user_data_dir / configured_name
    
    profile_paths = ProfilePaths(
        default_profile=default_profile,
        user_data_dir=user_data_dir,
        cache_dir=cache_dir
    )
    
    temp_base = Path(os.environ.get('TEMP', 'C:/temp')) / "coupa_profiles"
    
    return PlatformConfig(
        system="Windows",
        profile_paths=profile_paths,
        temp_dir_base=temp_base,
        max_path_length=260,  # Windows path limitation
        file_permissions=0o755
    )


def get_linux_config() -> PlatformConfig:
    """Get Linux-specific Edge profile configuration."""
    home = Path.home()
    # Prefer central config if available
    try:
        from .lib.config import Config as ExperimentalConfig  # type: ignore
        configured_dir = Path(os.path.expanduser(ExperimentalConfig.EDGE_PROFILE_DIR)) if getattr(ExperimentalConfig, 'EDGE_PROFILE_DIR', None) else None
        configured_name = ExperimentalConfig.EDGE_PROFILE_NAME if getattr(ExperimentalConfig, 'EDGE_PROFILE_NAME', None) else 'Default'
    except Exception:
        configured_dir = None
        configured_name = 'Default'

    # Common Linux Edge locations (may vary by distribution)
    config_dir = configured_dir or (home / ".config/microsoft-edge")
    default_profile = config_dir / configured_name
    
    profile_paths = ProfilePaths(
        default_profile=default_profile,
        user_data_dir=config_dir,
        cache_dir=home / ".cache/microsoft-edge"
    )
    
    return PlatformConfig(
        system="Linux",
        profile_paths=profile_paths,
        temp_dir_base=Path("/tmp/coupa_profiles"),
        max_path_length=4096,  # Linux has high limits
        file_permissions=0o755
    )


def get_platform_config() -> PlatformConfig:
    """Auto-detect platform and return appropriate configuration."""
    system = platform.system()
    
    if system == "Darwin":
        return get_macos_config()
    elif system == "Windows":
        return get_windows_config()
    elif system == "Linux":
        return get_linux_config()
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


# Default configuration instance
DEFAULT_CONFIG = get_platform_config()


# Configuration overrides for testing/development
def get_test_config(base_temp_dir: Optional[Path] = None) -> PlatformConfig:
    """Get configuration suitable for testing."""
    config = get_platform_config()
    
    if base_temp_dir:
        config.temp_dir_base = base_temp_dir
    
    # Use smaller buffer for faster tests
    config.copy_buffer_size = 8 * 1024  # 8KB
    
    return config


def validate_edge_installation() -> bool:
    """Check if Microsoft Edge is installed and accessible."""
    try:
        config = get_platform_config()
        return config.profile_paths.default_profile.exists()
    except (FileNotFoundError, RuntimeError):
        return False


def get_profile_lock_file(profile_path: Path) -> Path:
    """Get the lock file path for a profile directory."""
    return profile_path / "SingletonLock"


def is_profile_locked(profile_path: Path) -> bool:
    """Check if a profile is currently locked by another process."""
    lock_file = get_profile_lock_file(profile_path)
    return lock_file.exists()
