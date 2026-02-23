"""
Logging utilities for CoupaDownloads.

Provides structured logging setup, custom formatters, and logging helpers
to replace ad-hoc print statements throughout the codebase.
"""

import logging
import sys
import os
from typing import Optional, Dict, Any, List
from pathlib import Path

import structlog
from structlog.types import Processor


# Default log format for development
DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# JSON format for production
JSON_LOG_FORMAT = "json"


def setup_logging(
    level: str = "INFO",
    log_format: str = "default",
    log_file: Optional[str] = None,
    enable_structlog: bool = True,
) -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ("default", "json", "minimal")
        log_file: Optional file path for log output
        enable_structlog: Whether to enable structlog for structured logging
    """
    # Configure standard library logging
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create handlers
    handlers: List[logging.Handler] = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    handlers.append(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(log_level)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        format=DEFAULT_LOG_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Configure structlog if enabled
    if enable_structlog:
        _configure_structlog(log_format, log_level)
    
    # Reduce noise from noisy libraries
    _configure_library_loggers()


def _configure_structlog(log_format: str, log_level: int) -> None:
    """Configure structlog for structured logging."""
    
    # Choose processors based on format
    if log_format == "json":
        # JSON format for production
        processors: List[Processor] = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Console-friendly format for development
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _configure_library_loggers() -> None:
    """Configure log levels for third-party libraries to reduce noise."""
    
    # Selenium is very verbose
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Playwright can be noisy
    logging.getLogger("playwright").setLevel(logging.WARNING)
    
    # HTTPX for direct HTTP mode
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # Pandas warnings
    logging.getLogger("pandas").setLevel(logging.ERROR)
    
    # Structlog internal
    logging.getLogger("structlog").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def get_structlog(name: str):
    """
    Get a structlog instance for structured logging.
    
    Args:
        name: Logger name
        
    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)


class LogContext:
    """
    Context manager for adding contextual information to logs.
    
    Example:
        with LogContext(po_number="PO123", worker_id=1):
            logger.info("Processing PO")
    """
    
    def __init__(self, **context: Any):
        self.context = context
    
    def __enter__(self) -> 'LogContext':
        # Add context to current structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(**self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        # Clear context on exit
        structlog.contextvars.clear_contextvars()


class PerformanceLogger:
    """
    Context manager for logging operation duration.
    
    Example:
        with PerformanceLogger("process_po", po_number="PO123"):
            process_po(po_number)
    """
    
    def __init__(
        self,
        operation: str,
        logger: Optional[logging.Logger] = None,
        level: int = logging.INFO,
        **context: Any,
    ):
        self.operation = operation
        self.logger = logger or get_logger(__name__)
        self.level = level
        self.context = context
        self.start_time: Optional[float] = None
    
    def __enter__(self) -> 'PerformanceLogger':
        import time
        self.start_time = time.perf_counter()
        
        self.logger.log(
            self.level,
            f"Starting operation: {self.operation}",
            extra={
                "operation": self.operation,
                "phase": "start",
                **self.context,
            }
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        import time
        if self.start_time is None:
            return
        
        duration = time.perf_counter() - self.start_time
        
        if exc_type is not None:
            # Operation failed
            self.logger.error(
                f"Operation failed: {self.operation}",
                extra={
                    "operation": self.operation,
                    "phase": "error",
                    "duration_ms": duration * 1000,
                    "error": str(exc_val),
                    "error_type": exc_type.__name__,
                    **self.context,
                }
            )
        else:
            # Operation succeeded
            self.logger.log(
                self.level,
                f"Completed operation: {self.operation} in {duration:.3f}s",
                extra={
                    "operation": self.operation,
                    "phase": "complete",
                    "duration_ms": duration * 1000,
                    **self.context,
                }
            )


def log_function_call(logger_name: str = __name__):
    """
    Decorator to log function calls with timing.
    
    Example:
        @log_function_call("my_module")
        def process_po(po_number):
            ...
    """
    def decorator(func):
        import functools
        import time
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name)
            
            logger.debug(
                f"Calling {func.__name__}",
                extra={
                    "function": func.__name__,
                    "module": func.__module__,
                    "args_count": len(args),
                    "kwargs_count": len(kwargs),
                }
            )
            
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start
                
                logger.debug(
                    f"Completed {func.__name__} in {duration:.3f}s",
                    extra={
                        "function": func.__name__,
                        "duration_ms": duration * 1000,
                        "success": True,
                    }
                )
                return result
                
            except Exception as e:
                duration = time.perf_counter() - start
                
                logger.error(
                    f"Failed {func.__name__} after {duration:.3f}s",
                    extra={
                        "function": func.__name__,
                        "duration_ms": duration * 1000,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "success": False,
                    },
                    exc_info=True,
                )
                raise
        
        return wrapper
    return decorator


# Convenience function for creating module loggers
def get_module_logger(module_name: str) -> logging.Logger:
    """
    Get a logger for a module with standard configuration.
    
    Args:
        module_name: Usually __name__
        
    Returns:
        Configured logger
    """
    return logging.getLogger(module_name)
