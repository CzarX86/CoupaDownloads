"""
Unit tests for retry utilities.

Tests cover:
- RetryConfig configuration
- @retry_with_backoff decorator
- RetryContext context manager
- Specialized decorators
"""

import pytest
import time
from unittest.mock import Mock, patch

from src.core.retry import (
    RetryConfig,
    retry_with_backoff,
    RetryContext,
    retry_browser_operations,
    retry_coupa_operations,
)
from src.core.exceptions import BrowserInitError, SessionExpiredError, CoupaUnreachableError


class TestRetryConfig:
    """Test RetryConfig configuration and delay calculation."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = RetryConfig()
        
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert config.jitter_factor == 0.1
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = RetryConfig(
            max_retries=5,
            base_delay=0.5,
            max_delay=30.0,
            exponential_base=1.5,
            jitter=False,
        )
        
        assert config.max_retries == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0
        assert config.exponential_base == 1.5
        assert config.jitter is False
    
    def test_calculate_delay_exponential(self):
        """Test exponential backoff delay calculation."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        
        # Delay = base * (exponential_base ^ attempt)
        assert config.calculate_delay(0) == 1.0   # 1 * 2^0 = 1
        assert config.calculate_delay(1) == 2.0   # 1 * 2^1 = 2
        assert config.calculate_delay(2) == 4.0   # 1 * 2^2 = 4
        assert config.calculate_delay(3) == 8.0   # 1 * 2^3 = 8
    
    def test_calculate_delay_with_max(self):
        """Test delay is capped at max_delay."""
        config = RetryConfig(base_delay=1.0, max_delay=10.0, exponential_base=2.0, jitter=False)
        
        # Without max cap: 1 * 2^10 = 1024
        # With max cap: 10.0
        delay = config.calculate_delay(10)
        assert delay <= 10.0
    
    def test_calculate_delay_with_jitter(self):
        """Test jitter adds randomness to delay."""
        config = RetryConfig(base_delay=1.0, jitter=True, jitter_factor=0.1, jitter_factor=0.1)
        
        # Run multiple times to check jitter
        delays = [config.calculate_delay(1) for _ in range(10)]
        
        # All delays should be close to base (2.0) ± 10%
        for delay in delays:
            assert 1.8 <= delay <= 2.2
    
    def test_should_retry_max_retries(self):
        """Test should_retry returns False after max retries."""
        config = RetryConfig(max_retries=3)
        
        assert config.should_retry(Exception(), 0) is True
        assert config.should_retry(Exception(), 1) is True
        assert config.should_retry(Exception(), 2) is True
        assert config.should_retry(Exception(), 3) is False  # Exceeded
    
    def test_should_retry_exception_type(self):
        """Test should_retry checks exception type."""
        config = RetryConfig(retryable_exceptions=(ValueError, TypeError))
        
        assert config.should_retry(ValueError(), 0) is True
        assert config.should_retry(TypeError(), 0) is True
        assert config.should_retry(RuntimeError(), 0) is False  # Not in list


class TestRetryWithBackoff:
    """Test @retry_with_backoff decorator."""
    
    def test_success_no_retry(self):
        """Test successful execution doesn't retry."""
        call_count = 0
        
        @retry_with_backoff(max_retries=3)
        def succeed():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = succeed()
        
        assert result == "success"
        assert call_count == 1  # Called only once
    
    def test_retry_on_failure(self):
        """Test retry on expected failure."""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, retryable_exceptions=(ValueError,))
        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        result = fail_then_succeed()
        
        assert result == "success"
        assert call_count == 3  # Called 3 times (2 failures + 1 success)
    
    def test_no_retry_on_unexpected_exception(self):
        """Test no retry on unexpected exception type."""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, retryable_exceptions=(ValueError,))
        def fail_with_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("Unexpected error")
        
        with pytest.raises(TypeError):
            fail_with_type_error()
        
        assert call_count == 1  # Called only once, no retry
    
    def test_retry_exhausted(self):
        """Test exception raised after max retries exhausted."""
        call_count = 0
        
        @retry_with_backoff(max_retries=2, base_delay=0.01)
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError):
            always_fail()
        
        assert call_count == 3  # Initial + 2 retries
    
    def test_operation_name_in_logs(self, caplog):
        """Test operation name appears in logs."""
        @retry_with_backoff(
            max_retries=1,
            base_delay=0.01,
            operation_name="test_operation"
        )
        def fail():
            raise ValueError("Error")
        
        with caplog.at_level("ERROR"):
            with pytest.raises(ValueError):
                fail()
        
        assert "test_operation" in caplog.text


class TestRetryContext:
    """Test RetryContext context manager."""
    
    def test_success_on_first_try(self):
        """Test success on first attempt."""
        with RetryContext(max_retries=3) as retry:
            while retry.should_continue():
                result = "success"
                retry.success(result)
        
        assert retry.result == "success"
        assert retry.attempt == 0
    
    def test_success_after_failures(self):
        """Test success after initial failures."""
        call_count = 0
        
        with RetryContext(max_retries=3, base_delay=0.01) as retry:
            while retry.should_continue():
                call_count += 1
                try:
                    if call_count < 3:
                        raise ValueError("Temporary error")
                    retry.success("success")
                except ValueError as e:
                    retry.fail(e)
        
        assert retry.result == "success"
        assert call_count == 3
    
    def test_max_retries_exceeded(self):
        """Test exception raised after max retries."""
        call_count = 0
        
        with pytest.raises(ValueError):
            with RetryContext(max_retries=2, base_delay=0.01) as retry:
                while retry.should_continue():
                    call_count += 1
                    try:
                        raise ValueError("Always fails")
                    except ValueError as e:
                        retry.fail(e)
        
        assert call_count == 3  # Initial + 2 retries
    
    def test_result_not_available_on_failure(self):
        """Test result property raises if not succeeded."""
        retry = RetryContext()
        retry._success = False
        
        with pytest.raises(RuntimeError, match="did not succeed"):
            _ = retry.result


class TestSpecializedDecorators:
    """Test specialized retry decorators."""
    
    def test_retry_browser_operations(self):
        """Test retry_browser_operations decorator."""
        call_count = 0
        
        @retry_browser_operations
        def init_browser():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise BrowserInitError("Init failed")
            return "browser"
        
        # Should retry on BrowserInitError
        result = init_browser()
        assert result == "browser"
        assert call_count == 2
    
    def test_retry_coupa_operations(self):
        """Test retry_coupa_operations decorator."""
        call_count = 0
        
        @retry_coupa_operations
        def fetch_from_coupa():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise CoupaUnreachableError("https://coupa.example.com")
            return "data"
        
        # Should retry on CoupaUnreachableError
        result = fetch_from_coupa()
        assert result == "data"
        assert call_count == 2
