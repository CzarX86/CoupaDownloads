"""
Retry utilities with exponential backoff for CoupaDownloads.

Provides decorators and context managers for automatic retry logic
with configurable backoff strategies.
"""

import time
import logging
import random
from typing import Callable, Type, Tuple, Optional, Any, List
from functools import wraps
from datetime import datetime

from ..config.constants import (
    MAX_WORKER_RETRY_COUNT,
    RETRY_BACKOFF_MULTIPLIER,
)
from .exceptions import CoupaError

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_retries: int = MAX_WORKER_RETRY_COUNT,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = RETRY_BACKOFF_MULTIPLIER,
        jitter: bool = True,
        jitter_factor: float = 0.1,
        retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
        retryable_error_codes: Optional[List[str]] = None,
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_retries: Maximum number of retry attempts (0 = no retries)
            base_delay: Initial delay between retries in seconds
            max_delay: Maximum delay cap in seconds
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
            jitter_factor: Jitter as fraction of calculated delay (0.1 = ±10%)
            retryable_exceptions: Exception types that should trigger retry
            retryable_error_codes: Error codes that should trigger retry
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.jitter_factor = jitter_factor
        self.retryable_exceptions = retryable_exceptions or (Exception,)
        self.retryable_error_codes = retryable_error_codes or None
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt number.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff
        delay = self.base_delay * (self.exponential_base ** attempt)
        
        # Cap at max_delay
        delay = min(delay, self.max_delay)
        
        # Add jitter if enabled
        if self.jitter:
            jitter_range = delay * self.jitter_factor
            delay += random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay)  # Ensure non-negative
        
        return delay
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        Determine if operation should be retried.
        
        Args:
            exception: The exception that was raised
            attempt: Current attempt number
            
        Returns:
            True if should retry, False otherwise
        """
        if attempt >= self.max_retries:
            return False
        
        # Check if exception type is retryable
        if not isinstance(exception, self.retryable_exceptions):
            return False
        
        # Check error code if it's a CoupaError
        if isinstance(exception, CoupaError):
            if self.retryable_error_codes is not None:
                if exception.code.name not in self.retryable_error_codes:
                    return False
            
            # Check context flags
            if hasattr(exception, 'context'):
                if not exception.context.should_retry:
                    return False
        
        return True


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    max_retries: int = MAX_WORKER_RETRY_COUNT,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    log_level: int = logging.WARNING,
    operation_name: Optional[str] = None,
):
    """
    Decorator for automatic retry with exponential backoff.
    
    Args:
        config: RetryConfig instance (overrides other parameters if provided)
        max_retries: Maximum retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
        retryable_exceptions: Exception types to retry
        log_level: Log level for retry messages
        operation_name: Name of operation for logging
        
    Returns:
        Decorated function with retry logic
        
    Example:
        @retry_with_backoff(
            max_retries=3,
            retryable_exceptions=(BrowserInitError, TimeoutError),
            operation_name="browser_init"
        )
        def initialize_browser():
            ...
    """
    if config is None:
        config = RetryConfig(
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
            retryable_exceptions=retryable_exceptions,
        )
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            op_name = operation_name or func.__name__
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    last_exception = e
                    
                    if not config.should_retry(e, attempt):
                        logger.error(
                            f"Operation '{op_name}' failed after {attempt + 1} attempts",
                            extra={
                                "operation": op_name,
                                "attempt": attempt + 1,
                                "max_retries": config.max_retries,
                                "error": str(e),
                                "error_type": type(e).__name__,
                            }
                        )
                        raise
                    
                    # Log retry
                    delay = config.calculate_delay(attempt)
                    logger.log(
                        log_level,
                        f"Operation '{op_name}' failed (attempt {attempt + 1}/{config.max_retries + 1}), "
                        f"retrying in {delay:.2f}s",
                        extra={
                            "operation": op_name,
                            "attempt": attempt + 1,
                            "delay": delay,
                            "error": str(e),
                        }
                    )
                    
                    # Wait before retry
                    time.sleep(delay)
            
            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError(f"Retry loop exited unexpectedly for '{op_name}'")
        
        return wrapper
    return decorator


class RetryContext:
    """
    Context manager for retry logic in imperative code.
    
    Example:
        with RetryContext(max_retries=3) as retry:
            while retry.should_continue():
                try:
                    result = do_something()
                    retry.success(result)
                    return result
                except TemporaryError as e:
                    retry.fail(e)
    """
    
    def __init__(
        self,
        max_retries: int = MAX_WORKER_RETRY_COUNT,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        operation_name: Optional[str] = None,
    ):
        self.config = RetryConfig(
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
        )
        self.operation_name = operation_name or "operation"
        self.attempt = 0
        self._success = False
        self._result = None
        self._last_error = None
    
    def __enter__(self) -> 'RetryContext':
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        # If exception occurred and we haven't succeeded, log it
        if exc_type is not None and not self._success:
            logger.error(
                f"Operation '{self.operation_name}' failed with exception",
                extra={
                    "operation": self.operation_name,
                    "attempt": self.attempt,
                    "error": str(exc_val),
                    "error_type": exc_type.__name__,
                }
            )
        return False  # Don't suppress exceptions
    
    def should_continue(self) -> bool:
        """Check if another attempt should be made."""
        return self.attempt <= self.config.max_retries and not self._success
    
    def success(self, result: Any = None) -> None:
        """Mark operation as successful."""
        self._success = True
        self._result = result
        
        if self.attempt > 0:
            logger.info(
                f"Operation '{self.operation_name}' succeeded after {self.attempt + 1} attempts",
                extra={"operation": self.operation_name, "attempt": self.attempt}
            )
    
    def fail(self, exception: Exception) -> None:
        """
        Record a failure and wait for next attempt.
        
        Args:
            exception: The exception that occurred
            
        Raises:
            Exception: If max retries exceeded
        """
        self._last_error = exception
        
        if not self.config.should_retry(exception, self.attempt):
            logger.error(
                f"Operation '{self.operation_name}' failed after {self.attempt + 1} attempts",
                extra={
                    "operation": self.operation_name,
                    "attempt": self.attempt,
                    "error": str(exception),
                }
            )
            raise exception
        
        # Wait before next attempt
        delay = self.config.calculate_delay(self.attempt)
        logger.warning(
            f"Operation '{self.operation_name}' failed (attempt {self.attempt + 1}), "
            f"retrying in {delay:.2f}s",
            extra={
                "operation": self.operation_name,
                "attempt": self.attempt,
                "delay": delay,
                "error": str(exception),
            }
        )
        
        time.sleep(delay)
        self.attempt += 1
    
    @property
    def result(self) -> Any:
        """Get the result of successful operation."""
        if not self._success:
            raise RuntimeError("Operation did not succeed")
        return self._result


def retry_browser_operations(func: Callable) -> Callable:
    """
    Specialized retry decorator for browser operations.
    
    Retries on common browser errors with appropriate delays.
    """
    from .exceptions import (
        BrowserInitError,
        SessionExpiredError,
        TimeoutError,
    )
    
    @wraps(func)
    @retry_with_backoff(
        max_retries=2,
        base_delay=1.0,
        retryable_exceptions=(BrowserInitError, SessionExpiredError, TimeoutError),
        operation_name=func.__name__,
    )
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    return wrapper


def retry_coupa_operations(func: Callable) -> Callable:
    """
    Specialized retry decorator for Coupa API/page operations.
    
    Retries on transient Coupa errors.
    """
    from .exceptions import (
        CoupaUnreachableError,
        PONotFoundError,
        AttachmentsNotFoundError,
    )
    
    @wraps(func)
    @retry_with_backoff(
        max_retries=3,
        base_delay=0.5,
        retryable_exceptions=(CoupaUnreachableError,),
        operation_name=func.__name__,
    )
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    return wrapper
