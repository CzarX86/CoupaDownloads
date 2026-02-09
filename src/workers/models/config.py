"""
PoolConfig and TaskHandle models for worker pool configuration.

This module provides configuration and handle models with support for:
- Worker pool configuration and validation
- Task handle tracking and status
- Configuration serialization
- Constraint validation
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from pathlib import Path
import os
import uuid


@dataclass
class PoolConfig:
    """
    Configuration for PersistentWorkerPool.
    
    Provides comprehensive configuration with validation
    for worker pool initialization and operation.
    """
    
    # Worker configuration
    worker_count: int = 4
    headless_mode: bool = True
    execution_mode: str = "standard"  # standard, filtered, no_js, direct_http
    
    # Profile management
    base_profile_path: str = ""
    base_profile_name: str = "Default"
    hierarchy_columns: Optional[List[str]] = None
    has_hierarchy_data: bool = False
    download_root: str = ""
    sqlite_db_path: Optional[str] = None
    
    # Resource management
    memory_threshold: float = 0.85  # 85% of system RAM
    
    # Timeout configuration
    shutdown_timeout: float = 60.0  # 1 minute graceful shutdown
    task_timeout: float = 300.0     # 5 minutes per PO
    worker_startup_timeout: float = 30.0  # 30 seconds worker startup
    stagger_delay: float = 1.5            # seconds between starting workers
    
    # Retry configuration
    max_restart_attempts: int = 3
    
    # Observability
    observability_level: str = "basic"  # basic, detailed, complete
    enable_structured_logs: bool = True
    enable_metrics: bool = True
    
    # Advanced configuration
    profile_cleanup_on_shutdown: bool = True
    force_profile_recreation: bool = False
    enable_session_recovery: bool = True
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_worker_count()
        self._validate_memory_threshold()
        self._validate_timeouts()
        self._validate_base_profile_path()
        self._validate_observability_level()
        self._validate_base_profile_name()
        self._validate_hierarchy_columns()
        self._normalize_download_root()
    
    def _validate_worker_count(self):
        """Validate worker count is within allowed range."""
        if not isinstance(self.worker_count, int):
            raise ValueError("Worker count must be an integer")
        if self.worker_count < 1:
            raise ValueError("Worker count must be >= 1")
        # Optional hard cap via env (PERSISTENT_WORKERS_MAX) to avoid accidental overload
        import os as _os
        cap_val = _os.environ.get('PERSISTENT_WORKERS_MAX')
        if cap_val:
            try:
                cap_int = int(cap_val)
                if self.worker_count > cap_int:
                    raise ValueError(f"Worker count {self.worker_count} exceeds configured cap {cap_int}")
            except ValueError:
                # Ignore invalid cap
                pass
    
    def _validate_memory_threshold(self):
        """Validate memory threshold is within allowed range."""
        if not isinstance(self.memory_threshold, (int, float)):
            raise ValueError("Memory threshold must be a number")
        
        if not (0.5 <= self.memory_threshold <= 0.9):
            raise ValueError("Memory threshold must be between 50% (0.5) and 90% (0.9)")
    
    def _validate_timeouts(self):
        """Validate all timeout values are positive."""
        timeout_fields = ['shutdown_timeout', 'task_timeout', 'worker_startup_timeout']
        
        for field in timeout_fields:
            value = getattr(self, field)
            if not isinstance(value, (int, float)):
                raise ValueError(f"{field} must be a number")
            
            if value <= 0:
                raise ValueError(f"{field} must be positive")
    
    def _validate_base_profile_path(self):
        """Validate base profile path exists if provided."""
        if self.base_profile_path:
            profile_path = Path(self.base_profile_path)
            if not profile_path.exists():
                raise ValueError(f"Base profile path does not exist: {self.base_profile_path}")
            
            if not profile_path.is_dir():
                raise ValueError(f"Base profile path is not a directory: {self.base_profile_path}")
    
    def _validate_observability_level(self):
        """Validate observability level is supported."""
        valid_levels = ['basic', 'detailed', 'complete']
        if self.observability_level not in valid_levels:
            raise ValueError(f"Observability level must be one of: {valid_levels}")

    def _validate_base_profile_name(self) -> None:
        """Validate base profile name when provided."""
        if self.base_profile_name and not isinstance(self.base_profile_name, str):
            raise ValueError("Base profile name must be a string")
    
    def _validate_hierarchy_columns(self) -> None:
        """Validate hierarchy columns when provided."""
        if self.hierarchy_columns is not None:
            if not isinstance(self.hierarchy_columns, list):
                raise ValueError("hierarchy_columns must be a list of strings")
            for column in self.hierarchy_columns:
                if not isinstance(column, str):
                    raise ValueError("hierarchy_columns must contain only strings")
    
    def _normalize_download_root(self) -> None:
        """Normalize and ensure download root directory exists when provided."""
        if not self.download_root:
            return

        normalized = os.path.abspath(os.path.expanduser(self.download_root))
        try:
            os.makedirs(normalized, exist_ok=True)
        except Exception:
            raise ValueError(f"Failed to create download root directory: {normalized}")

        self.download_root = normalized
    
    def get_memory_threshold_bytes(self, total_system_memory: int) -> int:
        """Calculate memory threshold in bytes based on system memory."""
        return int(total_system_memory * self.memory_threshold)
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            'worker_count': self.worker_count,
            'headless_mode': self.headless_mode,
            'execution_mode': self.execution_mode,
            'base_profile_path': self.base_profile_path,
            'base_profile_name': self.base_profile_name,
            'hierarchy_columns': self.hierarchy_columns,
            'has_hierarchy_data': self.has_hierarchy_data,
            'download_root': self.download_root,
            'sqlite_db_path': self.sqlite_db_path,
            'memory_threshold': self.memory_threshold,
            'shutdown_timeout': self.shutdown_timeout,
            'task_timeout': self.task_timeout,
            'worker_startup_timeout': self.worker_startup_timeout,
            'max_restart_attempts': self.max_restart_attempts,
            'observability_level': self.observability_level,
            'enable_structured_logs': self.enable_structured_logs,
            'enable_metrics': self.enable_metrics,
            'profile_cleanup_on_shutdown': self.profile_cleanup_on_shutdown,
            'force_profile_recreation': self.force_profile_recreation,
            'enable_session_recovery': self.enable_session_recovery
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PoolConfig':
        """Create configuration from dictionary."""
        return cls(**data)
    
    @classmethod
    def create_default(
        cls,
        base_profile_path: str,
        worker_count: int = 4,
        headless_mode: bool = True,
        base_profile_name: str = "Default",
        hierarchy_columns: Optional[List[str]] = None,
        has_hierarchy_data: bool = False,
        download_root: str = "",
        sqlite_db_path: Optional[str] = None,
        stagger_delay: float = 0.5,
        execution_mode: str = "standard",
    ) -> 'PoolConfig':
        """Create default configuration with required parameters."""
        return cls(
            worker_count=worker_count,
            headless_mode=headless_mode,
            base_profile_path=base_profile_path,
            base_profile_name=base_profile_name,
            hierarchy_columns=hierarchy_columns,
            has_hierarchy_data=has_hierarchy_data,
            download_root=download_root,
            sqlite_db_path=sqlite_db_path,
            stagger_delay=stagger_delay,
            execution_mode=execution_mode,
        )


@dataclass
class TaskHandle:
    """
    Handle for tracking task processing status.
    
    Provides interface for monitoring task progress
    and retrieving results.
    """
    
    # Core identification
    task_id: str = field(default_factory=lambda: f"handle-{uuid.uuid4().hex[:8]}")
    po_number: str = ""
    po_data: Dict[str, Any] = field(default_factory=dict)
    
    # Status tracking
    submitted_at: float = field(default_factory=lambda: __import__('time').time())
    
    # Internal references (not serialized)
    _task_ref: Optional[Any] = field(default=None, repr=False)
    _pool_ref: Optional[Any] = field(default=None, repr=False)
    _result: Optional[Dict[str, Any]] = field(default=None, repr=False)
    
    def __post_init__(self):
        """Validate handle configuration."""
        if not self.task_id:
            raise ValueError("Task ID cannot be empty")
        
        if not self.po_number:
            raise ValueError("PO number cannot be empty")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current task status.
        
        Returns:
            Dictionary containing task status information
        """
        if self._task_ref:
            # Return actual task status if reference available
            return {
                'task_id': self.task_id,
                'po_number': self.po_number,
                'status': self._task_ref.status.value,
                'progress': 'unknown',  # Would be calculated from task state
                'error_message': self._task_ref.error_message,
                'retry_count': self._task_ref.retry_count
            }
        else:
            # Return basic information if no reference
            return {
                'task_id': self.task_id,
                'po_number': self.po_number,
                'status': 'unknown',
                'progress': 'unknown',
                'error_message': None,
                'retry_count': 0
            }
    
    def wait_for_completion(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Wait for task completion.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            Task result dictionary
            
        Raises:
            TimeoutError: If timeout exceeded
        """
        import time
        
        start_time = time.time()
        poll_interval = 1.0  # Poll every second
        
        while True:
            status = self.get_status()

            if self._result is not None:
                return self._result
            
            # Check if task is completed
            if status['status'] in ['completed', 'failed', 'cancelled']:
                return self._get_task_result()
            
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(f"Task {self.task_id} did not complete within {timeout} seconds")
            
            # Wait before next poll
            time.sleep(poll_interval)
    
    def _get_task_result(self) -> Dict[str, Any]:
        """Get comprehensive task result."""
        if self._result is not None:
            return self._result
        if self._task_ref:
            return {
                'task_id': self.task_id,
                'po_number': self.po_number,
                'status': self._task_ref.status.value,
                'success': self._task_ref.status.value == 'completed',
                'result_data': self._task_ref.result_data.copy(),
                'downloaded_files': self._task_ref.downloaded_files.copy(),
                'error_message': self._task_ref.error_message,
                'processing_time': self._task_ref.get_processing_time(),
                'retry_count': self._task_ref.retry_count,
                'metadata': self._task_ref.metadata.copy(),
            }
        else:
            # Fallback if no task reference
            return {
                'task_id': self.task_id,
                'po_number': self.po_number,
                'status': 'unknown',
                'success': False,
                'result_data': {},
                'downloaded_files': [],
                'error_message': 'Task reference not available',
                'processing_time': None,
                'retry_count': 0,
                'metadata': self.po_data.copy(),
            }
    
    def cancel(self) -> bool:
        """
        Attempt to cancel the task.
        
        Returns:
            True if cancellation was successful or task already completed
        """
        if self._task_ref and not self._task_ref.is_completed():
            self._task_ref.cancel("Cancelled via task handle")
            return True
        return False
    
    def to_dict(self) -> dict:
        """Convert handle to dictionary (excluding internal references)."""
        return {
            'task_id': self.task_id,
            'po_number': self.po_number,
            'submitted_at': self.submitted_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TaskHandle':
        """Create handle from dictionary."""
        return cls(
            task_id=data['task_id'],
            po_number=data['po_number'],
            submitted_at=data['submitted_at']
        )
    
    def __str__(self) -> str:
        """String representation of handle."""
        return f"TaskHandle({self.task_id}, {self.po_number})"
    
    def __repr__(self) -> str:
        """Detailed representation of handle."""
        return f"TaskHandle(task_id='{self.task_id}', po_number='{self.po_number}')"
