"""
Profile Manager API Contract

This module defines the API contract for the ProfileManager class
that handles browser profile creation, verification, and cleanup
for parallel worker processes.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass


class ProfileType(Enum):
    """Type of browser profile"""
    BASE = "base"      # Default Edge profile (read-only access)
    CLONE = "clone"    # Temporary profile copy (full access)


class VerificationMethod(Enum):
    """Available profile verification methods"""
    CAPABILITY_CHECK = "capability"     # WebDriver profile path verification
    AUTH_CHECK = "authentication"      # Session authentication verification
    FILE_VERIFICATION = "file"         # Critical file comparison


class VerificationStatus(Enum):
    """Status of profile verification"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ProfileStatus(Enum):
    """Status of a browser profile"""
    AVAILABLE = "available"
    LOCKED = "locked"
    CORRUPTED = "corrupted"
    MISSING = "missing"
    PERMISSION_DENIED = "permission_denied"


@dataclass
class RetryConfig:
    """Configuration for retry policies"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 10.0
    exponential_backoff: bool = True
    jitter: bool = True

    def __post_init__(self):
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.base_delay <= 0 or self.max_delay <= 0:
            raise ValueError("Delays must be positive")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay must be >= base_delay")


@dataclass
class VerificationConfig:
    """Configuration for profile verification"""
    enabled_methods: List[VerificationMethod]
    capability_timeout: float = 10.0
    auth_check_timeout: float = 30.0
    auth_check_url: str = ""
    file_verification_enabled: bool = False
    retry_config: Optional[RetryConfig] = None

    def __post_init__(self):
        if not self.enabled_methods:
            raise ValueError("At least one verification method must be enabled")
        if any(t <= 0 for t in [self.capability_timeout, self.auth_check_timeout]):
            raise ValueError("All timeout values must be positive")
        if self.retry_config is None:
            self.retry_config = RetryConfig()


@dataclass
class MethodResult:
    """Result of a single verification method"""
    method: VerificationMethod
    success: bool
    error_message: Optional[str] = None
    duration_seconds: float = 0.0
    details: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class VerificationResult:
    """Results of profile verification process"""
    worker_id: int
    overall_status: VerificationStatus
    method_results: Dict[VerificationMethod, MethodResult]
    started_at: datetime
    completed_at: datetime
    error_details: Optional[str] = None
    retry_count: int = 0

    def is_success(self) -> bool:
        """Returns True if all enabled methods passed"""
        return self.overall_status == VerificationStatus.SUCCESS

    def get_failed_methods(self) -> List[VerificationMethod]:
        """Returns list of verification methods that failed"""
        return [
            method for method, result in self.method_results.items()
            if not result.success
        ]

    def get_duration(self) -> float:
        """Returns total verification time in seconds"""
        return (self.completed_at - self.started_at).total_seconds()


@dataclass
class WorkerProfile:
    """Represents a browser profile for a specific worker"""
    worker_id: int
    profile_type: ProfileType
    profile_path: Path
    created_at: datetime
    verified_at: Optional[datetime] = None
    verification_status: VerificationStatus = VerificationStatus.PENDING
    selenium_options: Optional[List[str]] = None

    def __post_init__(self):
        if self.worker_id <= 0:
            raise ValueError("worker_id must be positive")
        if self.selenium_options is None:
            self.selenium_options = []

    def get_selenium_options(self) -> List[str]:
        """Returns WebDriver configuration options"""
        options = (self.selenium_options or []).copy()
        options.extend([
            f"--user-data-dir={self.profile_path}",
            "--no-first-run",
            "--disable-default-apps"
        ])
        return options

    def is_ready(self) -> bool:
        """Checks if profile is ready for browser startup"""
        return (
            self.profile_path.exists() and
            self.verification_status in [VerificationStatus.SUCCESS, VerificationStatus.PARTIAL]
        )

    def get_verification_summary(self) -> Dict[str, Any]:
        """Returns verification details"""
        return {
            "worker_id": self.worker_id,
            "profile_type": self.profile_type.value,
            "profile_path": str(self.profile_path),
            "verification_status": self.verification_status.value,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "is_ready": self.is_ready()
        }


class ProfileManagerContract(ABC):
    """Abstract base class defining the ProfileManager contract"""

    @abstractmethod
    def __init__(
        self,
        base_profile_path: Path,
        temp_directory: Optional[Path] = None,
        max_concurrent_clones: int = 5,
        clone_timeout: float = 30.0,
        verification_config: Optional[VerificationConfig] = None
    ):
        """
        Initialize ProfileManager with configuration
        
        Args:
            base_profile_path: Path to the default Edge profile
            temp_directory: Base directory for temporary profiles (default: system temp)
            max_concurrent_clones: Maximum simultaneous cloning operations
            clone_timeout: Maximum time for profile cloning (seconds)
            verification_config: Profile verification configuration
        """
        pass

    @abstractmethod
    def create_worker_profile(self, worker_id: int) -> WorkerProfile:
        """
        Creates isolated profile for worker
        
        Args:
            worker_id: Unique worker identifier
            
        Returns:
            WorkerProfile instance ready for use
            
        Raises:
            ProfileLockedException: Base profile is locked
            InsufficientSpaceException: Not enough disk space
            PermissionDeniedException: Cannot access profile paths
            ProfileCorruptedException: Base profile is damaged
        """
        pass

    @abstractmethod
    def verify_profile(self, profile: WorkerProfile) -> VerificationResult:
        """
        Verifies profile state using configured methods
        
        Args:
            profile: WorkerProfile to verify
            
        Returns:
            VerificationResult with detailed results
            
        Raises:
            VerificationTimeoutException: Verification timed out
        """
        pass

    @abstractmethod
    def cleanup_profile(self, profile: WorkerProfile) -> None:
        """
        Removes temporary profile and cleans up resources
        
        Args:
            profile: WorkerProfile to clean up
            
        Raises:
            CleanupException: Error during cleanup
        """
        pass

    @abstractmethod
    def get_base_profile_status(self) -> ProfileStatus:
        """
        Checks base profile availability
        
        Returns:
            ProfileStatus indicating base profile state
        """
        pass

    @abstractmethod
    def get_active_profiles(self) -> List[WorkerProfile]:
        """
        Returns list of currently managed profiles
        
        Returns:
            List of active WorkerProfile instances
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """
        Gracefully shutdown ProfileManager and cleanup all profiles
        """
        pass


# Exception classes
class ProfileException(Exception):
    """Base exception for profile-related errors"""
    pass


class ProfileLockedException(ProfileException):
    """Base profile is locked by another process"""
    pass


class InsufficientSpaceException(ProfileException):
    """Not enough disk space for profile operations"""
    pass


class PermissionDeniedException(ProfileException):
    """Insufficient permissions for profile operations"""
    pass


class ProfileCorruptedException(ProfileException):
    """Profile appears damaged or incomplete"""
    pass


class VerificationTimeoutException(ProfileException):
    """Profile verification exceeded timeout"""
    pass


class AuthenticationFailedException(ProfileException):
    """Authentication verification failed"""
    pass


class CapabilityMismatchException(ProfileException):
    """WebDriver reports different profile path than expected"""
    pass


class FileVerificationException(ProfileException):
    """Critical profile files missing or corrupted"""
    pass


class CleanupException(ProfileException):
    """Error during profile cleanup"""
    pass