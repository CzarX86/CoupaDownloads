"""
Custom exceptions for parallel processing in EXPERIMENTAL workers module.

This module defines exception classes for different error conditions
that can occur during parallel PO processing operations.
"""

from typing import Optional, Any, Dict


class ParallelProcessingError(Exception):
    """Base exception for all parallel processing related errors."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """
        Initialize parallel processing error.
        
        Args:
            message: Human-readable error description
            context: Optional context information for debugging
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
    
    def __str__(self) -> str:
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} (Context: {context_str})"
        return self.message


class WorkerError(ParallelProcessingError):
    """Exception raised when worker process encounters an error."""
    
    def __init__(self, worker_id: str, message: str, 
                 context: Optional[Dict[str, Any]] = None):
        """
        Initialize worker error.
        
        Args:
            worker_id: Identifier of the failed worker
            message: Error description
            context: Additional error context
        """
        self.worker_id = worker_id
        full_context = {"worker_id": worker_id}
        if context:
            full_context.update(context)
        super().__init__(f"Worker {worker_id}: {message}", full_context)


class ProfileError(ParallelProcessingError):
    """Exception raised when browser profile operations fail."""
    
    def __init__(self, profile_path: str, operation: str, message: str,
                 context: Optional[Dict[str, Any]] = None):
        """
        Initialize profile error.
        
        Args:
            profile_path: Path to the problematic profile
            operation: Operation that failed (create, cleanup, validate)
            message: Error description
            context: Additional error context
        """
        self.profile_path = profile_path
        self.operation = operation
        full_context = {"profile_path": profile_path, "operation": operation}
        if context:
            full_context.update(context)
        super().__init__(f"Profile {operation} failed for {profile_path}: {message}", 
                         full_context)


class TaskQueueError(ParallelProcessingError):
    """Exception raised when task queue operations fail."""
    
    def __init__(self, operation: str, message: str,
                 task_id: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        """
        Initialize task queue error.
        
        Args:
            operation: Queue operation that failed
            message: Error description
            task_id: Optional task identifier related to the error
            context: Additional error context
        """
        self.operation = operation
        self.task_id = task_id
        full_context = {"operation": operation}
        if task_id:
            full_context["task_id"] = task_id
        if context:
            full_context.update(context)
        
        error_msg = f"Task queue {operation} failed"
        if task_id:
            error_msg += f" for task {task_id}"
        error_msg += f": {message}"
        
        super().__init__(error_msg, full_context)


class ResourceExhaustionError(ParallelProcessingError):
    """Exception raised when system resources are exhausted."""
    
    def __init__(self, resource_type: str, current_usage: float, 
                 threshold: float, message: str,
                 context: Optional[Dict[str, Any]] = None):
        """
        Initialize resource exhaustion error.
        
        Args:
            resource_type: Type of resource (CPU, memory, etc.)
            current_usage: Current resource utilization (0.0-1.0)
            threshold: Resource threshold that was exceeded (0.0-1.0)
            message: Error description
            context: Additional error context
        """
        self.resource_type = resource_type
        self.current_usage = current_usage
        self.threshold = threshold
        
        full_context = {
            "resource_type": resource_type,
            "current_usage": f"{current_usage:.2%}",
            "threshold": f"{threshold:.2%}"
        }
        if context:
            full_context.update(context)
        
        super().__init__(
            f"Resource exhaustion: {resource_type} usage {current_usage:.2%} "
            f"exceeds threshold {threshold:.2%} - {message}",
            full_context
        )


class WorkerTimeoutError(WorkerError):
    """Exception raised when worker process times out."""
    
    def __init__(self, worker_id: str, timeout_seconds: float,
                 operation: str, context: Optional[Dict[str, Any]] = None):
        """
        Initialize worker timeout error.
        
        Args:
            worker_id: Identifier of the timed out worker
            timeout_seconds: Timeout duration that was exceeded
            operation: Operation that timed out
            context: Additional error context
        """
        self.timeout_seconds = timeout_seconds
        self.operation = operation
        
        full_context = {"timeout_seconds": timeout_seconds, "operation": operation}
        if context:
            full_context.update(context)
        
        super().__init__(
            worker_id,
            f"Operation '{operation}' timed out after {timeout_seconds}s",
            full_context
        )


# Profile Management Exceptions

class ProfileManagerError(ParallelProcessingError):
    """Base exception for profile management errors."""
    pass


class ProfileCreationError(ProfileManagerError):
    """Exception raised when profile creation fails."""
    
    def __init__(self, worker_id: str, message: str,
                 context: Optional[Dict[str, Any]] = None):
        """
        Initialize profile creation error.
        
        Args:
            worker_id: Identifier of worker for failed profile creation
            message: Error description
            context: Additional error context
        """
        self.worker_id = worker_id
        full_context = {"worker_id": worker_id}
        if context:
            full_context.update(context)
        super().__init__(f"Profile creation failed for worker {worker_id}: {message}", 
                         full_context)


class ProfileCleanupError(ProfileManagerError):
    """Exception raised when profile cleanup fails."""
    
    def __init__(self, worker_id: str, message: str,
                 context: Optional[Dict[str, Any]] = None):
        """
        Initialize profile cleanup error.
        
        Args:
            worker_id: Identifier of worker for failed profile cleanup
            message: Error description
            context: Additional error context
        """
        self.worker_id = worker_id
        full_context = {"worker_id": worker_id}
        if context:
            full_context.update(context)
        super().__init__(f"Profile cleanup failed for worker {worker_id}: {message}", 
                         full_context)


class ProfileConflictError(ProfileManagerError):
    """Exception raised when profile conflicts occur."""
    
    def __init__(self, worker_id: str, existing_worker_id: str,
                 context: Optional[Dict[str, Any]] = None):
        """
        Initialize profile conflict error.
        
        Args:
            worker_id: Identifier of worker requesting profile
            existing_worker_id: Identifier of worker with existing profile
            context: Additional error context
        """
        self.worker_id = worker_id
        self.existing_worker_id = existing_worker_id
        full_context = {"worker_id": worker_id, "existing_worker_id": existing_worker_id}
        if context:
            full_context.update(context)
        super().__init__(
            f"Profile conflict: Worker {worker_id} conflicts with existing worker {existing_worker_id}",
            full_context
        )


class ProfileLockedException(ProfileManagerError):
    """Raised when a base profile or target profile appears locked by another process."""

    def __init__(self, profile_path: str, context: Optional[Dict[str, Any]] = None):
        full_context = {"profile_path": profile_path}
        if context:
            full_context.update(context)
        super().__init__(f"Profile appears to be locked: {profile_path}", full_context)


class InsufficientSpaceException(ProfileManagerError):
    """Raised when there isn't enough disk space to create/clone profiles."""

    def __init__(self, required_bytes: int, available_bytes: int, context: Optional[Dict[str, Any]] = None):
        full_context = {"required_bytes": required_bytes, "available_bytes": available_bytes}
        if context:
            full_context.update(context)
        super().__init__(
            f"Insufficient disk space (required={required_bytes}, available={available_bytes})",
            full_context,
        )


class PermissionDeniedException(ProfileManagerError):
    """Raised when required filesystem permissions are missing."""

    def __init__(self, path: str, operation: str = "read/write", context: Optional[Dict[str, Any]] = None):
        full_context = {"path": path, "operation": operation}
        if context:
            full_context.update(context)
        super().__init__(f"Permission denied for {operation} on {path}", full_context)


class ProfileCorruptedException(ProfileManagerError):
    """Raised when a base profile directory is missing required structure/files."""

    def __init__(self, profile_path: str, message: str = "Profile structure invalid", context: Optional[Dict[str, Any]] = None):
        full_context = {"profile_path": profile_path}
        if context:
            full_context.update(context)
        super().__init__(f"{message}: {profile_path}", full_context)


# Task Queue Exceptions

class TaskValidationError(TaskQueueError):
    """Exception raised when task data fails validation."""
    
    def __init__(self, field_name: str, message: str,
                 context: Optional[Dict[str, Any]] = None):
        """
        Initialize task validation error.
        
        Args:
            field_name: Name of field that failed validation
            message: Error description
            context: Additional error context
        """
        self.field_name = field_name
        full_context = {"field_name": field_name}
        if context:
            full_context.update(context)
        super().__init__("validation", f"Field '{field_name}': {message}", 
                         context=full_context)


class QueueCapacityError(TaskQueueError):
    """Exception raised when queue reaches capacity limit."""
    
    def __init__(self, current_size: int, max_capacity: int,
                 context: Optional[Dict[str, Any]] = None):
        """
        Initialize queue capacity error.
        
        Args:
            current_size: Current queue size
            max_capacity: Maximum allowed capacity
            context: Additional error context
        """
        self.current_size = current_size
        self.max_capacity = max_capacity
        full_context = {"current_size": current_size, "max_capacity": max_capacity}
        if context:
            full_context.update(context)
        super().__init__("capacity", 
                         f"Queue capacity exceeded: {current_size}/{max_capacity}",
                         context=full_context)


class TaskTimeoutError(TaskQueueError):
    """Exception raised when task execution times out."""
    
    def __init__(self, task_id: str, timeout_seconds: float,
                 context: Optional[Dict[str, Any]] = None):
        """
        Initialize task timeout error.
        
        Args:
            task_id: Identifier of timed out task
            timeout_seconds: Timeout duration that was exceeded
            context: Additional error context
        """
        self.task_id = task_id
        self.timeout_seconds = timeout_seconds
        full_context = {"task_id": task_id, "timeout_seconds": timeout_seconds}
        if context:
            full_context.update(context)
        super().__init__("timeout", 
                         f"Task {task_id} timed out after {timeout_seconds}s",
                         task_id=task_id, context=full_context)


# Worker Pool Exceptions

class WorkerPoolError(ParallelProcessingError):
    """Base exception for worker pool errors."""
    pass


class WorkerCreationError(WorkerPoolError):
    """Exception raised when worker creation fails."""
    
    def __init__(self, worker_id: str, message: str,
                 context: Optional[Dict[str, Any]] = None):
        """
        Initialize worker creation error.
        
        Args:
            worker_id: Identifier of worker that failed to create
            message: Error description
            context: Additional error context
        """
        self.worker_id = worker_id
        full_context = {"worker_id": worker_id}
        if context:
            full_context.update(context)
        super().__init__(f"Worker creation failed for {worker_id}: {message}", 
                         full_context)