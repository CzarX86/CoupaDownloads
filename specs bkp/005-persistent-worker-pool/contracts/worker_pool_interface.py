"""
API Contract: PersistentWorkerPool Interface
Defines the contract for worker pool lifecycle management and PO processing coordination.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import datetime

class PoolStatus(Enum):
    INITIALIZING = "initializing"
    READY = "ready" 
    PROCESSING = "processing"
    SHUTTING_DOWN = "shutting_down"
    TERMINATED = "terminated"

class WorkerStatus(Enum):
    STARTING = "starting"
    READY = "ready"
    PROCESSING = "processing"
    IDLE = "idle"
    CRASHED = "crashed"
    RESTARTING = "restarting"
    TERMINATING = "terminating"
    TERMINATED = "terminated"

@dataclass
class WorkerInfo:
    """Information about a worker process"""
    worker_id: str
    status: WorkerStatus
    memory_usage: int  # bytes
    processed_count: int
    current_task: Optional[str]  # PO number or None
    profile_path: str

@dataclass
class PoolConfiguration:
    """Configuration for worker pool initialization"""
    worker_count: int  # 1-8
    headless_mode: bool
    base_profile_path: str
    memory_threshold: float  # 0.75 = 75% of system RAM
    shutdown_timeout: int  # seconds (60)

@dataclass
class POTask:
    """Purchase Order processing task"""
    task_id: str
    po_number: str
    po_data: Dict[str, Any]
    priority: int = 0
    retry_count: int = 0

@dataclass
class ProcessingResult:
    """Result of PO processing operation"""
    task_id: str
    po_number: str
    success: bool
    worker_id: str
    processing_time: float  # seconds
    error_message: Optional[str] = None
    downloaded_files: List[str] = None

class PersistentWorkerPoolInterface:
    """Contract for persistent worker pool operations"""
    
    def initialize(self, config: PoolConfiguration) -> bool:
        """
        Initialize worker pool with specified configuration.
        
        Args:
            config: Pool configuration including worker count and settings
            
        Returns:
            True if initialization successful, False otherwise
            
        Raises:
            ProfileCorruptionError: If base profile is corrupted
            InsufficientResourcesError: If system cannot support worker count
        """
        pass
    
    def add_tasks(self, tasks: List[POTask]) -> None:
        """
        Add PO processing tasks to the queue.
        
        Args:
            tasks: List of PO tasks to process
            
        Raises:
            PoolNotReadyError: If pool is not in READY or PROCESSING state
        """
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current pool status and worker information.
        
        Returns:
            Dictionary containing:
            - pool_status: Current PoolStatus
            - workers: List of WorkerInfo for each worker
            - pending_tasks: Number of tasks in queue
            - total_memory_usage: Total memory used by all workers
            - processing_stats: Completion counts and timing stats
        """
        pass
    
    def get_worker_info(self, worker_id: str) -> Optional[WorkerInfo]:
        """
        Get information about specific worker.
        
        Args:
            worker_id: Unique identifier for worker
            
        Returns:
            WorkerInfo if worker exists, None otherwise
        """
        pass
    
    def restart_worker(self, worker_id: str) -> bool:
        """
        Restart a specific worker process.
        
        Args:
            worker_id: Worker to restart
            
        Returns:
            True if restart initiated successfully
            
        Raises:
            WorkerNotFoundError: If worker_id doesn't exist
            ProfileCorruptionError: If worker profile is corrupted
        """
        pass
    
    def shutdown(self, timeout: Optional[int] = None) -> bool:
        """
        Initiate graceful shutdown of worker pool.
        
        Args:
            timeout: Maximum seconds to wait for completion (default from config)
            
        Returns:
            True if all workers shut down cleanly within timeout
        """
        pass
    
    def force_shutdown(self) -> None:
        """
        Force immediate termination of all workers.
        Used when graceful shutdown times out.
        """
        pass

class WorkerInterface:
    """Contract for individual worker operations"""
    
    def start(self, worker_id: str, profile_path: str, headless: bool) -> bool:
        """
        Start worker with browser session initialization.
        
        Args:
            worker_id: Unique worker identifier
            profile_path: Path to worker's browser profile
            headless: Whether to run browser in headless mode
            
        Returns:
            True if worker started successfully
        """
        pass
    
    def process_task(self, task: POTask) -> ProcessingResult:
        """
        Process a single PO task using new tab.
        
        Args:
            task: PO task to process
            
        Returns:
            ProcessingResult with success status and details
        """
        pass
    
    def check_health(self) -> Dict[str, Any]:
        """
        Check worker health and session status.
        
        Returns:
            Dictionary with health metrics:
            - session_active: bool
            - memory_usage: int (bytes)
            - tabs_open: int
            - last_activity: datetime
        """
        pass
    
    def stop(self, timeout: int = 60) -> bool:
        """
        Stop worker gracefully.
        
        Args:
            timeout: Maximum seconds to wait for current task completion
            
        Returns:
            True if stopped cleanly within timeout
        """
        pass

# Exception Classes
class PoolError(Exception):
    """Base exception for pool operations"""
    pass

class ProfileCorruptionError(PoolError):
    """Raised when browser profile corruption is detected"""
    pass

class InsufficientResourcesError(PoolError):
    """Raised when system cannot support requested configuration"""
    pass

class PoolNotReadyError(PoolError):
    """Raised when operation attempted on non-ready pool"""
    pass

class WorkerNotFoundError(PoolError):
    """Raised when worker_id doesn't exist"""
    pass

class SessionTimeoutError(PoolError):
    """Raised when browser session becomes invalid"""
    pass