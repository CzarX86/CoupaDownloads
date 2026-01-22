"""
Worker Pool Integration Contract

This module defines the integration contract between the ProfileManager
and the existing worker pool system in EXPERIMENTAL/workers/worker_pool.py
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable, TYPE_CHECKING
from dataclasses import dataclass
from .profile_manager_contract import WorkerProfile, VerificationResult

if TYPE_CHECKING:
    from .profile_manager_contract import ProfileManagerContract


@dataclass 
class WorkerConfig:
    """Configuration for a single worker"""
    worker_id: int
    headless: bool = True
    custom_options: Optional[List[str]] = None
    verification_required: bool = True
    max_verification_retries: int = 3


@dataclass
class WorkerStartupResult:
    """Result of worker startup with profile"""
    worker_id: int
    success: bool
    profile: Optional[WorkerProfile] = None
    verification_result: Optional[VerificationResult] = None
    error_message: Optional[str] = None
    startup_duration_seconds: float = 0.0


class ProfileAwareWorkerPoolContract(ABC):
    """Contract for worker pool with integrated profile management"""

    @abstractmethod
    def __init__(
        self,
        max_workers: int,
        profile_manager: 'ProfileManagerContract',
        worker_config_template: Optional[WorkerConfig] = None,
        startup_timeout: float = 60.0
    ):
        """
        Initialize worker pool with profile management
        
        Args:
            max_workers: Maximum number of concurrent workers
            profile_manager: ProfileManager instance for profile operations
            worker_config_template: Default configuration for workers
            startup_timeout: Maximum time for worker startup (seconds)
        """
        pass

    @abstractmethod
    def start_worker(self, worker_config: WorkerConfig) -> WorkerStartupResult:
        """
        Start a single worker with its own profile
        
        Args:
            worker_config: Configuration for the worker
            
        Returns:
            WorkerStartupResult with startup details
            
        Raises:
            WorkerStartupException: Worker failed to start
            ProfileException: Profile creation/verification failed
        """
        pass

    @abstractmethod
    def start_all_workers(
        self, 
        worker_configs: List[WorkerConfig]
    ) -> List[WorkerStartupResult]:
        """
        Start multiple workers with their profiles
        
        Args:
            worker_configs: List of worker configurations
            
        Returns:
            List of WorkerStartupResult for each worker
            
        Note:
            Partial failures are allowed - some workers may succeed while others fail
        """
        pass

    @abstractmethod
    def restart_worker(
        self, 
        worker_id: int, 
        new_profile: bool = True
    ) -> WorkerStartupResult:
        """
        Restart a specific worker, optionally with a new profile
        
        Args:
            worker_id: ID of worker to restart
            new_profile: Whether to create fresh profile or reuse existing
            
        Returns:
            WorkerStartupResult for the restarted worker
        """
        pass

    @abstractmethod
    def stop_worker(self, worker_id: int, cleanup_profile: bool = True) -> None:
        """
        Stop a specific worker and optionally cleanup its profile
        
        Args:
            worker_id: ID of worker to stop
            cleanup_profile: Whether to cleanup the worker's profile
        """
        pass

    @abstractmethod
    def stop_all_workers(self, cleanup_profiles: bool = True) -> None:
        """
        Stop all workers and optionally cleanup their profiles
        
        Args:
            cleanup_profiles: Whether to cleanup all worker profiles
        """
        pass

    @abstractmethod
    def get_worker_status(self, worker_id: int) -> Dict[str, Any]:
        """
        Get current status of a specific worker
        
        Args:
            worker_id: ID of worker to check
            
        Returns:
            Dictionary with worker and profile status information
        """
        pass

    @abstractmethod
    def get_all_worker_status(self) -> List[Dict[str, Any]]:
        """
        Get status of all workers
        
        Returns:
            List of worker status dictionaries
        """
        pass

    @abstractmethod
    def verify_all_profiles(self) -> Dict[int, VerificationResult]:
        """
        Re-verify profiles for all active workers
        
        Returns:
            Dictionary mapping worker_id to VerificationResult
        """
        pass

    @abstractmethod
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for the worker pool
        
        Returns:
            Dictionary with metrics like startup times, success rates, etc.
        """
        pass


class WorkerProfileEventHandler(ABC):
    """Event handler interface for worker and profile lifecycle events"""

    @abstractmethod
    def on_worker_starting(self, worker_id: int, config: WorkerConfig) -> None:
        """Called when worker startup begins"""
        pass

    @abstractmethod
    def on_profile_creating(self, worker_id: int) -> None:
        """Called when profile creation begins"""
        pass

    @abstractmethod
    def on_profile_created(self, worker_id: int, profile: WorkerProfile) -> None:
        """Called when profile creation completes"""
        pass

    @abstractmethod
    def on_profile_verification_starting(self, worker_id: int) -> None:
        """Called when profile verification begins"""
        pass

    @abstractmethod
    def on_profile_verification_completed(
        self, 
        worker_id: int, 
        result: VerificationResult
    ) -> None:
        """Called when profile verification completes"""
        pass

    @abstractmethod
    def on_worker_started(self, worker_id: int, result: WorkerStartupResult) -> None:
        """Called when worker startup completes"""
        pass

    @abstractmethod
    def on_worker_stopping(self, worker_id: int) -> None:
        """Called when worker shutdown begins"""
        pass

    @abstractmethod
    def on_profile_cleanup_starting(self, worker_id: int) -> None:
        """Called when profile cleanup begins"""
        pass

    @abstractmethod
    def on_profile_cleanup_completed(self, worker_id: int) -> None:
        """Called when profile cleanup completes"""
        pass

    @abstractmethod
    def on_worker_stopped(self, worker_id: int) -> None:
        """Called when worker shutdown completes"""
        pass

    @abstractmethod
    def on_verification_retry(
        self, 
        worker_id: int, 
        attempt: int, 
        max_attempts: int
    ) -> None:
        """Called when profile verification is retried"""
        pass

    @abstractmethod
    def on_worker_startup_failed(
        self, 
        worker_id: int, 
        error: Exception
    ) -> None:
        """Called when worker startup fails"""
        pass


# Exception classes for worker pool operations
class WorkerPoolException(Exception):
    """Base exception for worker pool operations"""
    pass


class WorkerStartupException(WorkerPoolException):
    """Worker failed to start"""
    pass


class WorkerNotFoundException(WorkerPoolException):
    """Worker with specified ID not found"""
    pass


class MaxWorkersExceededException(WorkerPoolException):
    """Attempted to exceed maximum worker limit"""
    pass


class WorkerPoolShutdownException(WorkerPoolException):
    """Operation attempted on shutdown worker pool"""
    pass