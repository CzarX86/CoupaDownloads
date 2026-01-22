"""
Enhanced Profile model with corruption detection capabilities.

This module provides the Profile data model with support for:
- Browser profile cloning and isolation
- Corruption detection and validation
- Lifecycle management
- Cleanup operations
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime
from pathlib import Path
import uuid
import os
import shutil
import json


class ProfileStatus(Enum):
    """Profile lifecycle status enumeration."""
    CLONING = "cloning"
    READY = "ready"
    IN_USE = "in_use"
    CLEANUP = "cleanup"
    REMOVED = "removed"
    CORRUPTED = "corrupted"
    FAILED = "failed"


@dataclass
class Profile:
    """
    Enhanced Profile model with corruption detection.
    
    Represents an isolated browser profile clone for worker process isolation.
    Includes comprehensive validation, corruption detection, and cleanup management.
    """
    
    # Core identification
    profile_id: str = field(default_factory=lambda: f"profile-{uuid.uuid4().hex[:8]}")
    base_profile_path: str = ""
    worker_profile_path: str = ""
    profile_name: str = "Default"
    
    # Lifecycle management
    status: ProfileStatus = ProfileStatus.CLONING
    clone_time: datetime = field(default_factory=datetime.now)
    last_validation: Optional[datetime] = None
    
    # Worker association
    worker_id: Optional[str] = None
    
    # Corruption detection
    corruption_detected: bool = False
    corruption_reason: Optional[str] = None
    validation_errors: list = field(default_factory=list)
    
    # Size tracking for cleanup
    profile_size_bytes: int = 0
    
    def __post_init__(self):
        """Validate profile configuration after initialization."""
        if not self.profile_id:
            raise ValueError("Profile ID cannot be empty")
        
        if not self.base_profile_path:
            raise ValueError("Base profile path cannot be empty")
        
        if not self.worker_profile_path:
            self.worker_profile_path = self._generate_worker_profile_path()
        if not self.profile_name:
            self.profile_name = "Default"
    
    def _generate_worker_profile_path(self) -> str:
        """Generate worker-specific profile path."""
        if not self.base_profile_path:
            raise ValueError("Base profile path required to generate worker path")
        
        base_dir = Path(self.base_profile_path).parent
        profile_name = f"{self.profile_id}_{self.worker_id or 'worker'}"
        return str(base_dir / profile_name)
    
    def validate_base_profile(self) -> bool:
        """
        Validate that base profile exists and is readable.
        
        Returns:
            True if base profile is valid, False otherwise
        """
        try:
            base_path = Path(self.base_profile_path)
            
            # Check if path exists
            if not base_path.exists():
                self._mark_corrupted(f"Base profile path does not exist: {base_path}")
                return False
            
            # Check if it's a directory
            if not base_path.is_dir():
                self._mark_corrupted(f"Base profile path is not a directory: {base_path}")
                return False
            
            # Check read permissions
            if not os.access(base_path, os.R_OK):
                self._mark_corrupted(f"Cannot read base profile directory: {base_path}")
                return False
            
            # Check for essential browser profile files
            required_files = ['Preferences', 'Local State']  # Chrome/Edge profile files
            missing_files = []
            
            for required_file in required_files:
                file_path = base_path / required_file
                if not file_path.exists():
                    missing_files.append(required_file)
            
            if missing_files:
                self._mark_corrupted(f"Missing essential profile files: {missing_files}")
                return False
            
            self.last_validation = datetime.now()
            return True
            
        except Exception as e:
            self._mark_corrupted(f"Error validating base profile: {str(e)}")
            return False
    
    def clone_profile(self, force: bool = False) -> bool:
        """
        Clone base profile to worker-specific location.
        
        Args:
            force: Whether to overwrite existing worker profile
            
        Returns:
            True if cloning successful, False otherwise
        """
        try:
            # Validate base profile first
            if not self.validate_base_profile():
                return False
            
            self.status = ProfileStatus.CLONING
            
            base_path = Path(self.base_profile_path)
            worker_path = Path(self.worker_profile_path)
            
            # Check if worker profile already exists
            if worker_path.exists():
                if not force:
                    self._mark_corrupted(f"Worker profile already exists: {worker_path}")
                    return False
                else:
                    # Remove existing profile
                    shutil.rmtree(worker_path)
            
            # Ensure parent directory exists
            worker_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Clone the profile
            shutil.copytree(base_path, worker_path, dirs_exist_ok=True)
            
            # Calculate profile size
            self.profile_size_bytes = self._calculate_directory_size(worker_path)
            
            # Validate cloned profile
            if self.validate_worker_profile():
                self.status = ProfileStatus.READY
                return True
            else:
                self._mark_corrupted("Cloned profile failed validation")
                return False
                
        except Exception as e:
            self._mark_corrupted(f"Error cloning profile: {str(e)}")
            return False
    
    def validate_worker_profile(self) -> bool:
        """
        Validate that worker profile is properly cloned and accessible.
        
        Returns:
            True if worker profile is valid, False otherwise
        """
        try:
            worker_path = Path(self.worker_profile_path)
            
            # Check if worker profile exists
            if not worker_path.exists():
                self.validation_errors.append("Worker profile directory does not exist")
                return False
            
            # Check if it's a directory
            if not worker_path.is_dir():
                self.validation_errors.append("Worker profile path is not a directory")
                return False
            
            # Check read/write permissions
            if not os.access(worker_path, os.R_OK | os.W_OK):
                self.validation_errors.append("Insufficient permissions on worker profile")
                return False
            
            # Check for essential files (same as base profile)
            required_files = ['Preferences', 'Local State']
            missing_files = []
            
            for required_file in required_files:
                file_path = worker_path / required_file
                if not file_path.exists():
                    missing_files.append(required_file)
            
            if missing_files:
                self.validation_errors.append(f"Missing files in worker profile: {missing_files}")
                return False
            
            # Check for corruption indicators
            if self._check_corruption_indicators():
                return False
            
            self.last_validation = datetime.now()
            self.validation_errors.clear()
            return True
            
        except Exception as e:
            self.validation_errors.append(f"Error validating worker profile: {str(e)}")
            return False
    
    def _check_corruption_indicators(self) -> bool:
        """
        Check for known corruption indicators in profile.
        
        Returns:
            True if corruption detected, False otherwise
        """
        try:
            worker_path = Path(self.worker_profile_path)
            
            # Check for lock files that indicate unclean shutdown
            lock_files = list(worker_path.glob("**/*lock*"))
            if lock_files:
                self.validation_errors.append(f"Lock files detected: {[f.name for f in lock_files]}")
                return True
            
            # Check for crash dump files
            crash_files = list(worker_path.glob("**/crashpad_reports/*"))
            if crash_files:
                self.validation_errors.append("Crash dump files detected")
                # Note: Crash files don't necessarily indicate corruption
            
            # Check Preferences file integrity
            preferences_file = worker_path / 'Preferences'
            if preferences_file.exists():
                try:
                    with open(preferences_file, 'r', encoding='utf-8') as f:
                        json.load(f)
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    self.validation_errors.append(f"Corrupted Preferences file: {str(e)}")
                    return True
            
            return False
            
        except Exception as e:
            self.validation_errors.append(f"Error checking corruption indicators: {str(e)}")
            return True
    
    def _calculate_directory_size(self, directory: Path) -> int:
        """Calculate total size of directory in bytes."""
        total_size = 0
        try:
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception:
            # If we can't calculate size, return 0
            pass
        return total_size
    
    def _mark_corrupted(self, reason: str):
        """Mark profile as corrupted with reason."""
        self.status = ProfileStatus.CORRUPTED
        self.corruption_detected = True
        self.corruption_reason = reason
        self.validation_errors.append(reason)
    
    def cleanup(self, force: bool = False) -> bool:
        """
        Clean up worker profile directory and resources.
        
        Args:
            force: Whether to force cleanup even if profile is in use
            
        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            # Check if profile is safe to clean up
            if self.status == ProfileStatus.IN_USE and not force:
                return False
            
            self.status = ProfileStatus.CLEANUP
            
            worker_path = Path(self.worker_profile_path)
            if worker_path.exists():
                # Attempt to remove the profile directory
                shutil.rmtree(worker_path, ignore_errors=False)
            
            # Verify cleanup was successful
            if not worker_path.exists():
                self.status = ProfileStatus.REMOVED
                self.profile_size_bytes = 0
                return True
            else:
                self.status = ProfileStatus.FAILED
                return False
                
        except Exception as e:
            self.status = ProfileStatus.FAILED
            self.validation_errors.append(f"Error during cleanup: {str(e)}")
            return False
    
    def mark_in_use(self, worker_id: str):
        """Mark profile as in use by specified worker."""
        if self.status != ProfileStatus.READY:
            raise ValueError(f"Profile must be READY to mark as in use, current status: {self.status}")
        
        self.worker_id = worker_id
        self.status = ProfileStatus.IN_USE
    
    def mark_ready(self):
        """Mark profile as ready for use."""
        if self.status not in [ProfileStatus.IN_USE, ProfileStatus.READY]:
            raise ValueError(f"Cannot mark profile as ready from status: {self.status}")
        
        self.status = ProfileStatus.READY
    
    def get_status_info(self) -> dict:
        """
        Get comprehensive profile status information.
        
        Returns:
            Dictionary containing profile status and metrics
        """
        return {
            'profile_id': self.profile_id,
            'status': self.status.value,
            'worker_id': self.worker_id,
            'base_profile_path': self.base_profile_path,
            'worker_profile_path': self.worker_profile_path,
            'corruption_detected': self.corruption_detected,
            'corruption_reason': self.corruption_reason,
            'validation_errors': self.validation_errors.copy(),
            'profile_size_bytes': self.profile_size_bytes,
            'clone_time': self.clone_time.isoformat(),
            'last_validation': self.last_validation.isoformat() if self.last_validation else None,
            'exists': Path(self.worker_profile_path).exists() if self.worker_profile_path else False
        }
    
    def to_dict(self) -> dict:
        """Convert profile to dictionary representation."""
        return {
            'profile_id': self.profile_id,
            'base_profile_path': self.base_profile_path,
            'worker_profile_path': self.worker_profile_path,
            'status': self.status.value,
            'clone_time': self.clone_time.isoformat(),
            'last_validation': self.last_validation.isoformat() if self.last_validation else None,
            'worker_id': self.worker_id,
            'corruption_detected': self.corruption_detected,
            'corruption_reason': self.corruption_reason,
            'validation_errors': self.validation_errors.copy(),
            'profile_size_bytes': self.profile_size_bytes
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Profile':
        """Create profile from dictionary representation."""
        # Convert string status back to enum
        if 'status' in data and isinstance(data['status'], str):
            data['status'] = ProfileStatus(data['status'])
        
        # Convert ISO datetime strings back to datetime objects
        if 'clone_time' in data and isinstance(data['clone_time'], str):
            data['clone_time'] = datetime.fromisoformat(data['clone_time'])
        
        if 'last_validation' in data and data['last_validation']:
            data['last_validation'] = datetime.fromisoformat(data['last_validation'])
        
        return cls(**data)
    
    def __str__(self) -> str:
        """String representation of profile."""
        return f"Profile({self.profile_id}, {self.status.value}, worker={self.worker_id})"
    
    def __repr__(self) -> str:
        """Detailed representation of profile."""
        return (f"Profile(profile_id='{self.profile_id}', status={self.status}, "
                f"worker_id='{self.worker_id}', corruption_detected={self.corruption_detected})")
