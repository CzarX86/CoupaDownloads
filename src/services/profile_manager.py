"""
ProfileManager service for browser profile lifecycle management.
Handles profile creation, corruption detection, cleanup, and reuse optimization.
"""

import os
import time
import shutil
import threading
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..models.profile import Profile, ProfileStatus


class ProfileManager:
    """
    Service for managing browser profile lifecycle.
    
    Responsibilities:
    - Create and initialize browser profiles
    - Detect and handle profile corruption
    - Optimize profile reuse and cleanup
    - Monitor profile disk usage
    - Handle profile cloning for worker isolation
    """
    
    def __init__(self, base_path: str, max_profiles: int = 20, cleanup_threshold_mb: int = 500):
        """
        Initialize ProfileManager.
        
        Args:
            base_path: Base directory for all profiles
            max_profiles: Maximum number of profiles to maintain
            cleanup_threshold_mb: Profile size threshold for cleanup (MB)
        """
        self.base_path = base_path
        self.max_profiles = max_profiles
        self.cleanup_threshold_bytes = cleanup_threshold_mb * 1024 * 1024
        
        # Profile tracking
        self.profiles: Dict[str, Profile] = {}
        self.available_profiles: List[str] = []  # profile_ids
        self.in_use_profiles: List[str] = []     # profile_ids
        self.corrupted_profiles: List[str] = []  # profile_ids
        
        # Threading
        self._lock = threading.RLock()
        self._cleanup_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="profile_cleanup")
        
        # Statistics
        self.stats = {
            'total_created': 0,
            'total_corrupted': 0,
            'total_cleaned': 0,
            'total_reused': 0,
            'corruption_rate': 0.0
        }
        
        # Ensure base directory exists
        os.makedirs(self.base_path, exist_ok=True)
        
    def create_profile(self, profile_id: Optional[str] = None) -> Optional[Profile]:
        """
        Create a new browser profile.
        
        Args:
            profile_id: Optional custom profile ID
            
        Returns:
            Profile instance if successful, None otherwise
        """
        with self._lock:
            if profile_id is None:
                profile_id = f"profile_{int(time.time())}_{len(self.profiles)}"
                
            if profile_id in self.profiles:
                raise ValueError(f"Profile {profile_id} already exists")
                
            try:
                profile = Profile(profile_id=profile_id, base_path=self.base_path)
                profile.create_directories()
                
                self.profiles[profile_id] = profile
                self.available_profiles.append(profile_id)
                self.stats['total_created'] += 1
                
                return profile
                
            except Exception as e:
                # If profile creation failed, clean up any partial state
                if profile_id in self.profiles:
                    del self.profiles[profile_id]
                return None
                
    def get_available_profile(self) -> Optional[Profile]:
        """
        Get an available profile for use.
        
        Returns:
            Available Profile instance, or None if none available
        """
        with self._lock:
            if not self.available_profiles:
                # Try to create a new profile if under limit
                if len(self.profiles) < self.max_profiles:
                    return self.create_profile()
                return None
                
            profile_id = self.available_profiles.pop(0)
            profile = self.profiles[profile_id]
            
            # Validate profile integrity before returning
            if not profile.validate_integrity():
                profile.mark_corrupted("Failed integrity check")
                self._mark_corrupted(profile_id)
                return self.get_available_profile()  # Recursive retry
                
            # Mark as in use
            profile.mark_in_use()
            self.in_use_profiles.append(profile_id)
            self.stats['total_reused'] += 1
            
            return profile
            
    def return_profile(self, profile_id: str, corrupted: bool = False) -> bool:
        """
        Return a profile after use.
        
        Args:
            profile_id: ID of the profile to return
            corrupted: Whether the profile is corrupted
            
        Returns:
            True if profile was returned successfully
        """
        with self._lock:
            if profile_id not in self.profiles:
                return False
                
            profile = self.profiles[profile_id]
            
            # Remove from in-use list
            if profile_id in self.in_use_profiles:
                self.in_use_profiles.remove(profile_id)
                
            if corrupted:
                profile.mark_corrupted("Marked corrupted by caller")
                self._mark_corrupted(profile_id)
            else:
                # Update profile size and check for cleanup
                profile.update_size()
                
                if profile.size_bytes > self.cleanup_threshold_bytes:
                    # Profile is too large, clean it up
                    self._schedule_cleanup(profile_id)
                else:
                    # Mark as ready for reuse
                    profile.mark_ready()
                    self.available_profiles.append(profile_id)
                    
            return True
            
    def clone_profile(self, source_profile_id: str, target_profile_id: Optional[str] = None) -> Optional[Profile]:
        """
        Clone an existing profile for worker isolation.
        
        Args:
            source_profile_id: ID of source profile to clone
            target_profile_id: Optional ID for new profile
            
        Returns:
            Cloned Profile instance if successful
        """
        with self._lock:
            if source_profile_id not in self.profiles:
                return None
                
            source_profile = self.profiles[source_profile_id]
            
            if target_profile_id is None:
                target_profile_id = f"{source_profile_id}_clone_{int(time.time())}"
                
            try:
                cloned_profile = Profile(profile_id=target_profile_id, base_path=self.base_path)
                
                if cloned_profile.clone_from(source_profile):
                    self.profiles[target_profile_id] = cloned_profile
                    self.available_profiles.append(target_profile_id)
                    return cloned_profile
                    
            except Exception:
                pass
                
            return None
            
    def cleanup_profile(self, profile_id: str) -> bool:
        """
        Clean up a profile and remove it from management.
        
        Args:
            profile_id: ID of profile to clean up
            
        Returns:
            True if cleanup was successful
        """
        with self._lock:
            if profile_id not in self.profiles:
                return False
                
            profile = self.profiles[profile_id]
            
            # Remove from all tracking lists
            for profile_list in [self.available_profiles, self.in_use_profiles, self.corrupted_profiles]:
                if profile_id in profile_list:
                    profile_list.remove(profile_id)
                    
            # Perform cleanup
            success = profile.cleanup()
            
            # Remove from management
            del self.profiles[profile_id]
            self.stats['total_cleaned'] += 1
            
            return success
            
    def cleanup_corrupted_profiles(self) -> int:
        """
        Clean up all corrupted profiles.
        
        Returns:
            Number of profiles cleaned up
        """
        with self._lock:
            corrupted_ids = self.corrupted_profiles.copy()
            cleaned_count = 0
            
            for profile_id in corrupted_ids:
                if self.cleanup_profile(profile_id):
                    cleaned_count += 1
                    
            return cleaned_count
            
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of profile management.
        
        Returns:
            Dictionary with status information
        """
        with self._lock:
            total_size = sum(p.size_bytes for p in self.profiles.values())
            
            return {
                'total_profiles': len(self.profiles),
                'available_profiles': len(self.available_profiles),
                'in_use_profiles': len(self.in_use_profiles),
                'corrupted_profiles': len(self.corrupted_profiles),
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / 1024 / 1024, 2),
                'base_path': self.base_path,
                'max_profiles': self.max_profiles,
                'cleanup_threshold_mb': self.cleanup_threshold_bytes // 1024 // 1024,
                'statistics': self.stats.copy()
            }
            
    def _mark_corrupted(self, profile_id: str) -> None:
        """
        Mark a profile as corrupted.
        
        Args:
            profile_id: ID of profile to mark as corrupted
        """
        if profile_id not in self.corrupted_profiles:
            self.corrupted_profiles.append(profile_id)
            self.stats['total_corrupted'] += 1
            
        # Update corruption rate
        if self.stats['total_created'] > 0:
            self.stats['corruption_rate'] = self.stats['total_corrupted'] / self.stats['total_created']
            
    def _schedule_cleanup(self, profile_id: str) -> None:
        """
        Schedule asynchronous cleanup of a profile.
        
        Args:
            profile_id: ID of profile to clean up
        """
        def cleanup_task():
            self.cleanup_profile(profile_id)
            
        self._cleanup_executor.submit(cleanup_task)
        
    def shutdown(self) -> None:
        """
        Shutdown profile manager and clean up resources.
        """
        with self._lock:
            # Clean up all profiles
            profile_ids = list(self.profiles.keys())
            for profile_id in profile_ids:
                self.cleanup_profile(profile_id)
                
            # Shutdown cleanup executor
            self._cleanup_executor.shutdown(wait=True)
