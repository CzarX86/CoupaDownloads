"""Structured logging configuration for profile management.

This module configures structlog for consistent, structured logging
across the profile management system with proper context tracking.
"""

import sys
import structlog
from typing import Any, Dict, Optional
from pathlib import Path
import logging.config
import logging


# Log levels configuration
LOG_LEVELS = {
    "CRITICAL": 50,
    "ERROR": 40,
    "WARNING": 30,
    "INFO": 20,
    "DEBUG": 10
}


def configure_structlog(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    json_logs: bool = False,
    include_timestamp: bool = True,
    include_caller: bool = False
) -> None:
    """Configure structlog for profile management logging.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        json_logs: Whether to output logs in JSON format
        include_timestamp: Whether to include timestamps in logs
        include_caller: Whether to include caller information
    """
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=LOG_LEVELS.get(level.upper(), logging.INFO),
    )
    
    # Processors for log formatting
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
    ]
    
    if include_timestamp:
        processors.append(structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"))
    
    if include_caller:
        processors.append(structlog.processors.CallsiteParameterAdder(
            parameters=[structlog.processors.CallsiteParameter.FILENAME,
                       structlog.processors.CallsiteParameter.LINENO,
                       structlog.processors.CallsiteParameter.FUNC_NAME]
        ))
    
    # Add final processor based on output format
    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(LOG_LEVELS.get(level.upper(), logging.INFO)),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure file logging if requested
    if log_file:
        setup_file_logging(log_file, level, json_logs)


def setup_file_logging(log_file: Path, level: str, json_format: bool = True) -> None:
    """Set up additional file-based logging.
    
    Args:
        log_file: Path to log file
        level: Logging level
        json_format: Whether to use JSON format for file logs
    """
    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(LOG_LEVELS.get(level.upper(), logging.INFO))
    
    if json_format:
        formatter = logging.Formatter('%(message)s')
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    file_handler.setFormatter(formatter)
    
    # Add to root logger
    logging.getLogger().addHandler(file_handler)


def get_logger(name: str, **context: Any) -> structlog.BoundLogger:
    """Get a structured logger with optional context.
    
    Args:
        name: Logger name (typically module name)
        **context: Additional context to bind to logger
    
    Returns:
        Configured structlog logger instance
    """
    logger = structlog.get_logger(name)
    if context:
        logger = logger.bind(**context)
    return logger


def get_profile_logger(worker_id: int, profile_type: str = "unknown") -> structlog.BoundLogger:
    """Get a logger specifically configured for profile operations.
    
    Args:
        worker_id: Worker ID for context
        profile_type: Type of profile (base/clone)
    
    Returns:
        Logger with profile-specific context
    """
    return get_logger(
        "profile_manager",
        worker_id=worker_id,
        profile_type=profile_type,
        component="profile_ops"
    )


def get_verification_logger(worker_id: int, method: str) -> structlog.BoundLogger:
    """Get a logger for profile verification operations.
    
    Args:
        worker_id: Worker ID for context
        method: Verification method name
    
    Returns:
        Logger with verification-specific context
    """
    return get_logger(
        "profile_verification",
        worker_id=worker_id,
        verification_method=method,
        component="verification"
    )


def get_worker_pool_logger(pool_size: int) -> structlog.BoundLogger:
    """Get a logger for worker pool operations.
    
    Args:
        pool_size: Size of the worker pool
    
    Returns:
        Logger with worker pool context
    """
    return get_logger(
        "worker_pool",
        pool_size=pool_size,
        component="worker_management"
    )


# Context managers for operation logging
class LoggedOperation:
    """Context manager for logging operations with duration tracking."""
    
    def __init__(self, logger: structlog.BoundLogger, operation: str, **context: Any):
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time = None
    
    def __enter__(self):
        import time
        self.start_time = time.time()
        self.logger.info(f"Starting {self.operation}", **self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        duration = time.time() - (self.start_time or 0)
        
        if exc_type is None:
            self.logger.info(
                f"Completed {self.operation}",
                duration_seconds=round(duration, 3),
                **self.context
            )
        else:
            self.logger.error(
                f"Failed {self.operation}",
                duration_seconds=round(duration, 3),
                error_type=exc_type.__name__,
                error_message=str(exc_val),
                **self.context
            )
        return False  # Don't suppress exceptions


# Default logging configuration
def setup_default_logging(debug: bool = False) -> None:
    """Set up default logging configuration for the application.
    
    Args:
        debug: Whether to enable debug-level logging
    """
    level = "DEBUG" if debug else "INFO"
    configure_structlog(
        level=level,
        json_logs=False,
        include_timestamp=True,
        include_caller=debug
    )


# Initialize default logging when module is imported
setup_default_logging()
