"""
Custom exception hierarchy for CoupaDownloads.

Provides structured error handling with error codes, context tracking,
and recovery strategies. Replaces bare Exception usage throughout the codebase.
"""

from typing import Optional, Dict, Any, List
from enum import Enum, auto
from dataclasses import dataclass, field


class ErrorCode(Enum):
    """Standardized error codes for all CoupaDownloads errors."""
    
    # General errors (1000-1999)
    UNKNOWN_ERROR = auto()
    CONFIGURATION_ERROR = auto()
    INITIALIZATION_ERROR = auto()
    SHUTDOWN_ERROR = auto()
    
    # Browser errors (2000-2999)
    BROWSER_NOT_FOUND = auto()
    BROWSER_INIT_FAILED = auto()
    BROWSER_CRASHED = auto()
    DRIVER_NOT_FOUND = auto()
    DRIVER_VERSION_MISMATCH = auto()
    SESSION_EXPIRED = auto()
    SESSION_INVALID = auto()
    PAGE_LOAD_FAILED = auto()
    ELEMENT_NOT_FOUND = auto()
    TIMEOUT_EXCEEDED = auto()
    
    # Coupa/API errors (3000-3999)
    COUPA_UNREACHABLE = auto()
    COUPA_AUTH_FAILED = auto()
    COUPA_PAGE_ERROR = auto()
    PO_NOT_FOUND = auto()
    ATTACHMENTS_NOT_FOUND = auto()
    DOWNLOAD_FAILED = auto()
    
    # Worker errors (4000-4999)
    WORKER_INIT_FAILED = auto()
    WORKER_CRASHED = auto()
    WORKER_TIMEOUT = auto()
    WORKER_COMMUNICATION_FAILED = auto()
    PROFILE_CLONE_FAILED = auto()
    PROFILE_CORRUPTED = auto()
    
    # File system errors (5000-5999)
    FILE_NOT_FOUND = auto()
    FILE_ACCESS_DENIED = auto()
    DISK_FULL = auto()
    INVALID_PATH = auto()
    CSV_READ_ERROR = auto()
    CSV_WRITE_ERROR = auto()
    SQLITE_ERROR = auto()
    
    # Resource errors (6000-6999)
    INSUFFICIENT_MEMORY = auto()
    INSUFFICIENT_DISK_SPACE = auto()
    CPU_OVERLOADED = auto()
    NETWORK_UNAVAILABLE = auto()
    
    # Validation errors (7000-7999)
    INVALID_INPUT = auto()
    VALIDATION_FAILED = auto()
    MISSING_REQUIRED_FIELD = auto()


@dataclass
class ErrorContext:
    """Contextual information about an error for debugging and recovery."""
    
    #: Unique error identifier (can be used for correlation)
    error_id: Optional[str] = None
    
    #: Component where error occurred (e.g., "WorkerManager", "Downloader")
    component: Optional[str] = None
    
    #: Operation being performed when error occurred
    operation: Optional[str] = None
    
    #: PO number being processed (if applicable)
    po_number: Optional[str] = None
    
    #: Worker ID (if applicable)
    worker_id: Optional[int] = None
    
    #: Additional context key-value pairs
    extra: Dict[str, Any] = field(default_factory=dict)
    
    #: Timestamp of error (auto-set by exception)
    timestamp: Optional[float] = None
    
    #: Suggested recovery action
    recovery_action: Optional[str] = None
    
    #: Whether this error is recoverable
    is_recoverable: bool = False
    
    #: Whether to retry the operation
    should_retry: bool = False


class CoupaError(Exception):
    """
    Base exception for all CoupaDownloads errors.
    
    All custom exceptions should inherit from this class.
    Provides consistent error handling, logging, and recovery.
    """
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.context = context or ErrorContext()
        self.__cause__ = cause
        
        # Auto-set timestamp
        import time
        if self.context.timestamp is None:
            self.context.timestamp = time.time()
    
    def __str__(self) -> str:
        """Format error for display/logging."""
        parts = [f"[{self.code.name}] {self.message}"]
        
        if self.context.component:
            parts.append(f"Component: {self.context.component}")
        if self.context.operation:
            parts.append(f"Operation: {self.context.operation}")
        if self.context.po_number:
            parts.append(f"PO: {self.context.po_number}")
        if self.context.extra:
            extra_str = ", ".join(f"{k}={v}" for k, v in self.context.extra.items())
            parts.append(f"Context: {extra_str}")
        
        return " | ".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/metrics."""
        return {
            "error_id": self.context.error_id,
            "code": self.code.name,
            "message": self.message,
            "component": self.context.component,
            "operation": self.context.operation,
            "po_number": self.context.po_number,
            "worker_id": self.context.worker_id,
            "is_recoverable": self.context.is_recoverable,
            "should_retry": self.context.should_retry,
            "recovery_action": self.context.recovery_action,
            "timestamp": self.context.timestamp,
        }


# =============================================================================
# CONFIGURATION ERRORS (1000-1999)
# =============================================================================

class ConfigurationError(CoupaError):
    """Error in application configuration."""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            code=ErrorCode.CONFIGURATION_ERROR,
            **kwargs
        )


class InitializationError(CoupaError):
    """Error during component initialization."""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            code=ErrorCode.INITIALIZATION_ERROR,
            **kwargs
        )


# =============================================================================
# BROWSER ERRORS (2000-2999)
# =============================================================================

class BrowserError(CoupaError):
    """Base class for browser-related errors."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, **kwargs)


class BrowserNotFoundError(BrowserError):
    """Microsoft Edge browser not found on system."""
    def __init__(self, message: str = "Microsoft Edge browser not found", **kwargs):
        super().__init__(
            message,
            code=ErrorCode.BROWSER_NOT_FOUND,
            context=ErrorContext(
                is_recoverable=True,
                recovery_action="Install Microsoft Edge from https://www.microsoft.com/edge"
            ),
            **kwargs
        )


class BrowserInitError(BrowserError):
    """Failed to initialize browser."""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            code=ErrorCode.BROWSER_INIT_FAILED,
            context=ErrorContext(
                is_recoverable=True,
                should_retry=True,
                recovery_action="Retry browser initialization or check for existing processes"
            ),
            **kwargs
        )


class DriverNotFoundError(BrowserError):
    """EdgeDriver not found or incompatible."""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            code=ErrorCode.DRIVER_NOT_FOUND,
            context=ErrorContext(
                is_recoverable=True,
                recovery_action="Run driver auto-download or install manually"
            ),
            **kwargs
        )


class SessionExpiredError(BrowserError):
    """Browser session has expired."""
    def __init__(self, message: str = "Browser session expired", **kwargs):
        super().__init__(
            message,
            code=ErrorCode.SESSION_EXPIRED,
            context=ErrorContext(
                is_recoverable=True,
                should_retry=True,
                recovery_action="Re-initialize browser session"
            ),
            **kwargs
        )


class TimeoutError(BrowserError):
    """Operation exceeded timeout limit."""
    def __init__(self, message: str, operation: str, timeout: float, **kwargs):
        context = ErrorContext(
            operation=operation,
            extra={"timeout_seconds": timeout},
            is_recoverable=True,
            should_retry=True,
            recovery_action=f"Increase timeout or retry {operation}"
        )
        if kwargs.get('context'):
            context.extra.update(kwargs['context'].extra)
        
        super().__init__(
            message,
            code=ErrorCode.TIMEOUT_EXCEEDED,
            context=context,
            **kwargs
        )


# =============================================================================
# COUPA ERRORS (3000-3999)
# =============================================================================

class CoupaAPIError(CoupaError):
    """Base class for Coupa API/page errors."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, **kwargs)


class CoupaUnreachableError(CoupaAPIError):
    """Cannot connect to Coupa instance."""
    def __init__(self, url: str, **kwargs):
        super().__init__(
            f"Cannot connect to Coupa at {url}",
            code=ErrorCode.COUPA_UNREACHABLE,
            context=ErrorContext(
                extra={"url": url},
                is_recoverable=False,
                recovery_action="Check network connection and Coupa URL"
            ),
            **kwargs
        )


class PONotFoundError(CoupaAPIError):
    """PO number not found in Coupa."""
    def __init__(self, po_number: str, **kwargs):
        super().__init__(
            f"PO {po_number} not found in Coupa",
            code=ErrorCode.PO_NOT_FOUND,
            context=ErrorContext(
                po_number=po_number,
                is_recoverable=False,
                recovery_action="Verify PO number is correct"
            ),
            **kwargs
        )


class AttachmentsNotFoundError(CoupaAPIError):
    """No attachments found for PO."""
    def __init__(self, po_number: str, **kwargs):
        super().__init__(
            f"No attachments found for PO {po_number}",
            code=ErrorCode.ATTACHMENTS_NOT_FOUND,
            context=ErrorContext(
                po_number=po_number,
                is_recoverable=False,
                recovery_action="Check if PO has attachments in Coupa"
            ),
            **kwargs
        )


# =============================================================================
# WORKER ERRORS (4000-4999)
# =============================================================================

class WorkerError(CoupaError):
    """Base class for worker-related errors."""
    def __init__(self, message: str, worker_id: Optional[int] = None, **kwargs):
        context = kwargs.pop('context', None) or ErrorContext()
        if worker_id is not None:
            context.worker_id = worker_id
        super().__init__(message, context=context, **kwargs)


class WorkerInitError(WorkerError):
    """Failed to initialize worker."""
    def __init__(self, message: str, worker_id: Optional[int] = None, **kwargs):
        super().__init__(
            message,
            worker_id=worker_id,
            code=ErrorCode.WORKER_INIT_FAILED,
            context=ErrorContext(
                worker_id=worker_id,
                is_recoverable=True,
                should_retry=True,
                recovery_action="Retry worker initialization"
            ),
            **kwargs
        )


class WorkerCrashError(WorkerError):
    """Worker process crashed unexpectedly."""
    def __init__(self, message: str, worker_id: Optional[int] = None, **kwargs):
        super().__init__(
            message,
            worker_id=worker_id,
            code=ErrorCode.WORKER_CRASHED,
            context=ErrorContext(
                worker_id=worker_id,
                is_recoverable=True,
                should_retry=True,
                recovery_action="Restart worker with fresh browser profile"
            ),
            **kwargs
        )


class ProfileCloneError(WorkerError):
    """Failed to clone browser profile."""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            code=ErrorCode.PROFILE_CLONE_FAILED,
            context=ErrorContext(
                is_recoverable=True,
                should_retry=True,
                recovery_action="Clean up profiles and retry"
            ),
            **kwargs
        )


# =============================================================================
# FILE SYSTEM ERRORS (5000-5999)
# =============================================================================

class FileSystemError(CoupaError):
    """Base class for file system errors."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, **kwargs)


class FileNotFoundError(FileSystemError):
    """File not found."""
    def __init__(self, path: str, **kwargs):
        super().__init__(
            f"File not found: {path}",
            code=ErrorCode.FILE_NOT_FOUND,
            context=ErrorContext(
                extra={"path": path},
                is_recoverable=False,
                recovery_action="Verify file path is correct"
            ),
            **kwargs
        )


class CSVError(FileSystemError):
    """Error reading or writing CSV files."""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            code=ErrorCode.CSV_READ_ERROR if "read" in message.lower() else ErrorCode.CSV_WRITE_ERROR,
            context=ErrorContext(
                is_recoverable=True,
                recovery_action="Check file permissions and disk space"
            ),
            **kwargs
        )


class SQLiteError(FileSystemError):
    """Error with SQLite database operations."""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            code=ErrorCode.SQLITE_ERROR,
            context=ErrorContext(
                is_recoverable=True,
                recovery_action="Check database file permissions and disk space"
            ),
            **kwargs
        )


# =============================================================================
# RESOURCE ERRORS (6000-6999)
# =============================================================================

class ResourceError(CoupaError):
    """Base class for resource-related errors."""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, **kwargs)


class InsufficientMemoryError(ResourceError):
    """Not enough memory available."""
    def __init__(self, required_mb: int, available_mb: int, **kwargs):
        super().__init__(
            f"Insufficient memory: required {required_mb}MB, available {available_mb}MB",
            code=ErrorCode.INSUFFICIENT_MEMORY,
            context=ErrorContext(
                extra={
                    "required_mb": required_mb,
                    "available_mb": available_mb
                },
                is_recoverable=False,
                recovery_action="Close other applications or reduce worker count"
            ),
            **kwargs
        )


class DiskFullError(ResourceError):
    """Disk space exhausted."""
    def __init__(self, path: str, **kwargs):
        super().__init__(
            f"Disk full at {path}",
            code=ErrorCode.DISK_FULL,
            context=ErrorContext(
                extra={"path": path},
                is_recoverable=False,
                recovery_action="Free up disk space or change download location"
            ),
            **kwargs
        )


# =============================================================================
# VALIDATION ERRORS (7000-7999)
# =============================================================================

class ValidationError(CoupaError):
    """Input validation failed."""
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        context = kwargs.pop('context', None) or ErrorContext()
        if field:
            context.extra['field'] = field

        super().__init__(
            message,
            code=ErrorCode.VALIDATION_FAILED,
            context=context,
            **kwargs
        )


class InvalidInputError(ValidationError):
    """Invalid input provided."""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            context=ErrorContext(
                is_recoverable=False,
                recovery_action="Check input format and values"
            ),
            **kwargs
        )
