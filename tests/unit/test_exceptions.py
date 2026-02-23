"""
Unit tests for exception hierarchy.

Tests cover:
- Error codes
- ErrorContext
- Exception types
- Serialization
"""

import pytest
import time

from src.core.exceptions import (
    ErrorCode,
    ErrorContext,
    CoupaError,
    ConfigurationError,
    InitializationError,
    BrowserError,
    BrowserNotFoundError,
    BrowserInitError,
    DriverNotFoundError,
    SessionExpiredError,
    TimeoutError,
    CoupaAPIError,
    CoupaUnreachableError,
    PONotFoundError,
    AttachmentsNotFoundError,
    WorkerError,
    WorkerInitError,
    WorkerCrashError,
    ProfileCloneError,
    FileSystemError,
    FileNotFoundError as CoupaFileNotFoundError,
    CSVError,
    SQLiteError,
    ResourceError,
    InsufficientMemoryError,
    DiskFullError,
    ValidationError,
    InvalidInputError,
)


class TestErrorCode:
    """Test ErrorCode enum."""
    
    def test_error_codes_exist(self):
        """Test all expected error codes exist."""
        assert ErrorCode.UNKNOWN_ERROR is not None
        assert ErrorCode.CONFIGURATION_ERROR is not None
        assert ErrorCode.BROWSER_NOT_FOUND is not None
        assert ErrorCode.BROWSER_INIT_FAILED is not None
        assert ErrorCode.PO_NOT_FOUND is not None
        assert ErrorCode.WORKER_INIT_FAILED is not None
        assert ErrorCode.FILE_NOT_FOUND is not None
        assert ErrorCode.INSUFFICIENT_MEMORY is not None
    
    def test_error_code_names(self):
        """Test error code names are descriptive."""
        assert ErrorCode.BROWSER_NOT_FOUND.name == "BROWSER_NOT_FOUND"
        assert ErrorCode.PO_NOT_FOUND.name == "PO_NOT_FOUND"


class TestErrorContext:
    """Test ErrorContext dataclass."""
    
    def test_default_values(self):
        """Test default context values."""
        ctx = ErrorContext()
        
        assert ctx.error_id is None
        assert ctx.component is None
        assert ctx.operation is None
        assert ctx.po_number is None
        assert ctx.worker_id is None
        assert ctx.extra == {}
        assert ctx.timestamp is None
        assert ctx.recovery_action is None
        assert ctx.is_recoverable is False
        assert ctx.should_retry is False
    
    def test_custom_values(self):
        """Test custom context values."""
        ctx = ErrorContext(
            error_id="test-123",
            component="BrowserManager",
            operation="initialize",
            po_number="PO123",
            worker_id=1,
            extra={"key": "value"},
            is_recoverable=True,
            should_retry=True,
            recovery_action="Retry initialization"
        )
        
        assert ctx.error_id == "test-123"
        assert ctx.component == "BrowserManager"
        assert ctx.operation == "initialize"
        assert ctx.po_number == "PO123"
        assert ctx.worker_id == 1
        assert ctx.extra == {"key": "value"}
        assert ctx.is_recoverable is True
        assert ctx.should_retry is True
        assert ctx.recovery_action == "Retry initialization"
    
    def test_auto_timestamp(self):
        """Test timestamp is auto-set by exception."""
        before = time.time()
        exc = BrowserInitError("Test", context=ErrorContext())
        after = time.time()
        
        assert exc.context.timestamp is not None
        assert before <= exc.context.timestamp <= after


class TestCoupaErrorBase:
    """Test base CoupaError class."""
    
    def test_basic_exception(self):
        """Test basic exception creation."""
        exc = CoupaError("Test error")
        
        assert exc.message == "Test error"
        assert exc.code == ErrorCode.UNKNOWN_ERROR
        assert exc.__cause__ is None
    
    def test_exception_with_code(self):
        """Test exception with error code."""
        exc = CoupaError("Config error", code=ErrorCode.CONFIGURATION_ERROR)
        
        assert exc.code == ErrorCode.CONFIGURATION_ERROR
    
    def test_exception_with_context(self):
        """Test exception with context."""
        ctx = ErrorContext(component="Test", po_number="PO123")
        exc = CoupaError("Test", context=ctx)
        
        assert exc.context.component == "Test"
        assert exc.context.po_number == "PO123"
    
    def test_exception_with_cause(self):
        """Test exception with underlying cause."""
        try:
            raise ValueError("Original error")
        except ValueError as e:
            exc = CoupaError("Wrapped error", cause=e)
            assert exc.__cause__ is e
    
    def test_str_representation(self):
        """Test string representation."""
        exc = CoupaError(
            "Test error",
            code=ErrorCode.BROWSER_INIT_FAILED,
            context=ErrorContext(
                component="BrowserManager",
                po_number="PO123"
            )
        )
        
        str_repr = str(exc)
        assert "BROWSER_INIT_FAILED" in str_repr
        assert "Test error" in str_repr
        assert "BrowserManager" in str_repr
        assert "PO123" in str_repr
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        exc = CoupaError(
            "Test error",
            code=ErrorCode.WORKER_INIT_FAILED,
            context=ErrorContext(
                component="WorkerManager",
                po_number="PO123",
                worker_id=1,
                is_recoverable=True
            )
        )
        
        exc_dict = exc.to_dict()
        
        assert exc_dict["code"] == "WORKER_INIT_FAILED"
        assert exc_dict["message"] == "Test error"
        assert exc_dict["component"] == "WorkerManager"
        assert exc_dict["po_number"] == "PO123"
        assert exc_dict["worker_id"] == 1
        assert exc_dict["is_recoverable"] is True


class TestBrowserExceptions:
    """Test browser-related exceptions."""
    
    def test_browser_not_found_error(self):
        """Test BrowserNotFoundError."""
        exc = BrowserNotFoundError()
        
        assert exc.code == ErrorCode.BROWSER_NOT_FOUND
        assert exc.context.is_recoverable is True
        assert "Install Microsoft Edge" in exc.context.recovery_action
    
    def test_browser_init_error(self):
        """Test BrowserInitError."""
        exc = BrowserInitError("Failed to init")
        
        assert exc.code == ErrorCode.BROWSER_INIT_FAILED
        assert exc.context.is_recoverable is True
        assert exc.context.should_retry is True
    
    def test_driver_not_found_error(self):
        """Test DriverNotFoundError."""
        exc = DriverNotFoundError("Driver missing")
        
        assert exc.code == ErrorCode.DRIVER_NOT_FOUND
        assert "download" in exc.context.recovery_action.lower()
    
    def test_session_expired_error(self):
        """Test SessionExpiredError."""
        exc = SessionExpiredError()
        
        assert exc.code == ErrorCode.SESSION_EXPIRED
        assert exc.context.should_retry is True
    
    def test_timeout_error(self):
        """Test TimeoutError."""
        exc = TimeoutError("Timed out", operation="load_page", timeout=30.0)
        
        assert exc.code == ErrorCode.TIMEOUT_EXCEEDED
        assert exc.context.extra["timeout_seconds"] == 30.0
        assert exc.context.operation == "load_page"


class TestCoupaAPIExceptions:
    """Test Coupa API exceptions."""
    
    def test_coupa_unreachable_error(self):
        """Test CoupaUnreachableError."""
        exc = CoupaUnreachableError("https://example.com")
        
        assert exc.code == ErrorCode.COUPA_UNREACHABLE
        assert exc.context.extra["url"] == "https://example.com"
        assert exc.context.is_recoverable is False
    
    def test_po_not_found_error(self):
        """Test PONotFoundError."""
        exc = PONotFoundError("PO999")
        
        assert exc.code == ErrorCode.PO_NOT_FOUND
        assert exc.context.po_number == "PO999"
        assert exc.context.is_recoverable is False
    
    def test_attachments_not_found_error(self):
        """Test AttachmentsNotFoundError."""
        exc = AttachmentsNotFoundError("PO123")
        
        assert exc.code == ErrorCode.ATTACHMENTS_NOT_FOUND
        assert exc.context.po_number == "PO123"


class TestWorkerExceptions:
    """Test worker-related exceptions."""
    
    def test_worker_init_error(self):
        """Test WorkerInitError."""
        exc = WorkerInitError("Init failed", worker_id=1)
        
        assert exc.code == ErrorCode.WORKER_INIT_FAILED
        assert exc.context.worker_id == 1
        assert exc.context.should_retry is True
    
    def test_worker_crash_error(self):
        """Test WorkerCrashError."""
        exc = WorkerCrashError("Crashed", worker_id=2)
        
        assert exc.code == ErrorCode.WORKER_CRASHED
        assert exc.context.worker_id == 2
        assert exc.context.should_retry is True
    
    def test_profile_clone_error(self):
        """Test ProfileCloneError."""
        exc = ProfileCloneError("Clone failed")
        
        assert exc.code == ErrorCode.PROFILE_CLONE_FAILED
        assert exc.context.should_retry is True


class TestFileSystemExceptions:
    """Test file system exceptions."""
    
    def test_file_not_found_error(self):
        """Test Coupa FileNotFoundError."""
        exc = CoupaFileNotFoundError("/path/to/file")
        
        assert exc.code == ErrorCode.FILE_NOT_FOUND
        assert exc.context.extra["path"] == "/path/to/file"
    
    def test_csv_error(self):
        """Test CSVError."""
        exc = CSVError("Read failed")
        
        assert exc.code == ErrorCode.CSV_READ_ERROR
        assert exc.context.is_recoverable is True
    
    def test_sqlite_error(self):
        """Test SQLiteError."""
        exc = SQLiteError("DB locked")
        
        assert exc.code == ErrorCode.SQLITE_ERROR
        assert exc.context.is_recoverable is True


class TestResourceExceptions:
    """Test resource exceptions."""
    
    def test_insufficient_memory_error(self):
        """Test InsufficientMemoryError."""
        exc = InsufficientMemoryError(required_mb=1000, available_mb=500)
        
        assert exc.code == ErrorCode.INSUFFICIENT_MEMORY
        assert exc.context.extra["required_mb"] == 1000
        assert exc.context.extra["available_mb"] == 500
        assert exc.context.is_recoverable is False
    
    def test_disk_full_error(self):
        """Test DiskFullError."""
        exc = DiskFullError("/downloads")
        
        assert exc.code == ErrorCode.DISK_FULL
        assert exc.context.extra["path"] == "/downloads"
        assert "Free up disk space" in exc.context.recovery_action


class TestValidationExceptions:
    """Test validation exceptions."""
    
    def test_validation_error(self):
        """Test ValidationError."""
        exc = ValidationError("Invalid value", field="po_number")
        
        assert exc.code == ErrorCode.VALIDATION_FAILED
        assert exc.context.extra["field"] == "po_number"
    
    def test_invalid_input_error(self):
        """Test InvalidInputError."""
        exc = InvalidInputError("Bad input")
        
        assert exc.code == ErrorCode.INVALID_INPUT
        assert exc.context.is_recoverable is False


class TestExceptionInheritance:
    """Test exception inheritance hierarchy."""
    
    def test_browser_error_is_coupa_error(self):
        """Test BrowserError inherits from CoupaError."""
        exc = BrowserInitError("Test")
        assert isinstance(exc, CoupaError)
    
    def test_worker_error_is_coupa_error(self):
        """Test WorkerError inherits from CoupaError."""
        exc = WorkerInitError("Test")
        assert isinstance(exc, CoupaError)
    
    def test_file_system_error_is_coupa_error(self):
        """Test FileSystemError inherits from CoupaError."""
        exc = CSVError("Test")
        assert isinstance(exc, CoupaError)
    
    def test_catch_all_browser_errors(self):
        """Test catching all browser errors."""
        try:
            raise BrowserNotFoundError()
        except BrowserError as e:
            assert isinstance(e, BrowserError)
        except Exception:
            pytest.fail("Should have caught BrowserError")
