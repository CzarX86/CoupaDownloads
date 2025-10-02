"""
Profile entity for browser profile management.
Represents an isolated browser profile with its own cookies, cache, and settings.
"""

import os
import tempfile
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum


class ProfileStatus(Enum):
    """Status of a browser profile."""
    CREATING = "creating"
    READY = "ready"
    IN_USE = "in_use"
    CORRUPTED = "corrupted"
    CLEANING = "cleaning"
    DESTROYED = "destroyed"


@dataclass
class Profile:
    """
    Browser profile entity for isolated browser sessions.
    
    Each profile maintains its own:
    - Browser settings and preferences
    - Cookies and session data
    - Cache and temporary files
    - User data directory
    """
    
    profile_id: str
    base_path: str
    status: ProfileStatus = ProfileStatus.CREATING
    created_at: float = field(default_factory=time.time)
    last_used_at: Optional[float] = None
    use_count: int = 0
    corruption_count: int = 0
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize profile paths and validate base path."""
        if not self.base_path:
            raise ValueError("base_path is required for profile creation")
            
        # Ensure base path exists
        os.makedirs(self.base_path, exist_ok=True)
        
    @property
    def profile_path(self) -> str:
        """Full path to this profile's directory."""
        return os.path.join(self.base_path, f"profile_{self.profile_id}")
        
    @property
    def user_data_dir(self) -> str:
        """Path to browser user data directory within profile."""
        return os.path.join(self.profile_path, "user_data")
        
    @property
    def is_available(self) -> bool:
        """Check if profile is available for use."""
        return self.status in [ProfileStatus.READY]
        
    @property
    def is_corrupted(self) -> bool:
        """Check if profile is marked as corrupted."""
        return self.status == ProfileStatus.CORRUPTED
        
    @property
    def age_seconds(self) -> float:
        """Age of profile in seconds."""
        return time.time() - self.created_at
        
    @property
    def idle_seconds(self) -> Optional[float]:
        """Seconds since last use, None if never used."""
        if self.last_used_at is None:
            return None
        return time.time() - self.last_used_at
        
    def create_directories(self) -> None:
        """Create necessary directories for the profile."""
        try:
            self.status = ProfileStatus.CREATING
            
            # Create main profile directory
            os.makedirs(self.profile_path, exist_ok=True)
            
            # Create user data directory for browser
            os.makedirs(self.user_data_dir, exist_ok=True)
            
            # Create additional directories for organization
            cache_dir = os.path.join(self.profile_path, "cache")
            downloads_dir = os.path.join(self.profile_path, "downloads")
            
            os.makedirs(cache_dir, exist_ok=True)
            os.makedirs(downloads_dir, exist_ok=True)
            
            # Update size after creation
            self.update_size()
            
            self.status = ProfileStatus.READY
            
        except Exception as e:
            self.status = ProfileStatus.CORRUPTED
            self.corruption_count += 1
            raise RuntimeError(f"Failed to create profile directories: {e}")
            
    def mark_in_use(self) -> None:
        """Mark profile as currently in use."""
        if not self.is_available:
            raise RuntimeError(f"Profile {self.profile_id} is not available (status: {self.status})")
            
        self.status = ProfileStatus.IN_USE
        self.last_used_at = time.time()
        self.use_count += 1
        
    def mark_ready(self) -> None:
        """Mark profile as ready for use."""
        if self.status == ProfileStatus.IN_USE:
            self.status = ProfileStatus.READY
            self.last_used_at = time.time()
        else:
            raise RuntimeError(f"Cannot mark profile ready from status: {self.status}")
            
    def mark_corrupted(self, reason: Optional[str] = None) -> None:
        """Mark profile as corrupted."""
        self.status = ProfileStatus.CORRUPTED
        self.corruption_count += 1
        
        if reason:
            self.metadata['corruption_reason'] = reason
            self.metadata['corruption_timestamp'] = time.time()
            
    def update_size(self) -> None:
        """Update the size_bytes field by scanning profile directory."""
        if not os.path.exists(self.profile_path):
            self.size_bytes = 0
            return
            
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(self.profile_path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                    except (OSError, FileNotFoundError):
                        # Skip files that can't be accessed (may be locked)
                        continue
                        
            self.size_bytes = total_size
            
        except Exception:
            # If we can't calculate size, keep current value
            pass
            
    def cleanup(self) -> bool:
        """
        Clean up profile directory and files.
        Returns True if cleanup was successful.
        """
        if self.status == ProfileStatus.IN_USE:
            raise RuntimeError(f"Cannot cleanup profile {self.profile_id} while in use")
            
        try:
            self.status = ProfileStatus.CLEANING
            
            if os.path.exists(self.profile_path):
                # Try to remove the entire profile directory
                shutil.rmtree(self.profile_path)
                
            self.status = ProfileStatus.DESTROYED
            self.size_bytes = 0
            
            return True
            
        except Exception as e:
            self.status = ProfileStatus.CORRUPTED
            self.corruption_count += 1
            self.metadata['cleanup_error'] = str(e)
            self.metadata['cleanup_error_timestamp'] = time.time()
            return False
            
    def clone_from(self, source_profile: 'Profile') -> bool:
        """
        Clone settings and data from another profile.
        Returns True if cloning was successful.
        """
        if not source_profile.is_available and source_profile.status != ProfileStatus.IN_USE:
            raise ValueError(f"Source profile {source_profile.profile_id} is not in a valid state for cloning")
            
        if self.status != ProfileStatus.CREATING:
            raise RuntimeError(f"Cannot clone into profile {self.profile_id} with status {self.status}")
            
        try:
            # Ensure our directories exist
            self.create_directories()
            
            # Copy user data if source has it
            if os.path.exists(source_profile.user_data_dir):
                # Remove our empty user data dir
                if os.path.exists(self.user_data_dir):
                    shutil.rmtree(self.user_data_dir)
                    
                # Copy source user data
                shutil.copytree(source_profile.user_data_dir, self.user_data_dir)
                
            # Copy relevant metadata
            if 'browser_settings' in source_profile.metadata:
                self.metadata['browser_settings'] = source_profile.metadata['browser_settings'].copy()
                
            # Update size after cloning
            self.update_size()
            
            self.status = ProfileStatus.READY
            return True
            
        except Exception as e:
            self.status = ProfileStatus.CORRUPTED
            self.corruption_count += 1
            self.metadata['clone_error'] = str(e)
            self.metadata['clone_error_timestamp'] = time.time()
            return False
            
    def validate_integrity(self) -> bool:
        """
        Validate profile integrity.
        Returns True if profile appears to be in good condition.
        """
        try:
            # Check if basic directories exist
            if not os.path.exists(self.profile_path):
                return False
                
            if not os.path.exists(self.user_data_dir):
                return False
                
            # Check if user data directory is accessible
            try:
                os.listdir(self.user_data_dir)
            except (OSError, PermissionError):
                return False
                
            # Check for any corruption indicators in metadata
            if 'corruption_reason' in self.metadata:
                return False
                
            return True
            
        except Exception:
            return False
            
    def get_browser_arguments(self) -> list[str]:
        """
        Get browser arguments for launching with this profile.
        Returns list of command-line arguments for browser.
        """
        args = [
            f"--user-data-dir={self.user_data_dir}",
            "--no-default-browser-check",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-features=TranslateUI",
            "--disable-ipc-flooding-protection"
        ]
        
        # Add any custom arguments from metadata
        if 'browser_arguments' in self.metadata:
            args.extend(self.metadata['browser_arguments'])
            
        return args
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary representation."""
        return {
            'profile_id': self.profile_id,
            'base_path': self.base_path,
            'profile_path': self.profile_path,
            'status': self.status.value,
            'created_at': self.created_at,
            'last_used_at': self.last_used_at,
            'use_count': self.use_count,
            'corruption_count': self.corruption_count,
            'size_bytes': self.size_bytes,
            'age_seconds': self.age_seconds,
            'idle_seconds': self.idle_seconds,
            'is_available': self.is_available,
            'is_corrupted': self.is_corrupted,
            'metadata': self.metadata.copy()
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Profile':
        """Create profile from dictionary representation."""
        profile = cls(
            profile_id=data['profile_id'],
            base_path=data['base_path'],
            status=ProfileStatus(data['status']),
            created_at=data.get('created_at', time.time()),
            last_used_at=data.get('last_used_at'),
            use_count=data.get('use_count', 0),
            corruption_count=data.get('corruption_count', 0),
            size_bytes=data.get('size_bytes', 0),
            metadata=data.get('metadata', {})
        )
        return profile
        
    def __str__(self) -> str:
        """String representation of profile."""
        return f"Profile(id={self.profile_id}, status={self.status.value}, use_count={self.use_count})"
        
    def __repr__(self) -> str:
        """Detailed representation of profile."""
        return (f"Profile(profile_id='{self.profile_id}', base_path='{self.base_path}', "
                f"status={self.status.value}, created_at={self.created_at}, "
                f"use_count={self.use_count}, size_bytes={self.size_bytes})")