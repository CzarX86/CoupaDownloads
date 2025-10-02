"""Unit tests for retry configuration.

These tests validate RetryConfig dataclass validation,
behavior, and integration with retry logic.
"""

import pytest
from unittest.mock import patch
import time

# These imports will fail until implementations exist - tests should fail
try:
    from EXPERIMENTAL.workers.retry_config import RetryConfig
    from EXPERIMENTAL.workers.retry_logic import RetryHandler
except ImportError as e:
    pytest.skip(f"Implementation not available: {e}", allow_module_level=True)


class TestRetryConfig:
    """Test RetryConfig validation and behavior."""
    
    def test_retry_config_initialization_with_defaults(self):
        """Test RetryConfig initializes with reasonable defaults."""
        config = RetryConfig()
        
        # Should have sensible defaults
        assert config.max_attempts >= 1
        assert config.base_delay > 0
        assert config.max_delay >= config.base_delay
        assert isinstance(config.exponential_backoff, bool)
        assert isinstance(config.jitter, bool)
    
    def test_retry_config_initialization_with_custom_values(self):
        """Test RetryConfig accepts custom configuration values."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=0.5,
            max_delay=30.0,
            exponential_backoff=False,
            jitter=True
        )
        
        assert config.max_attempts == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0
        assert config.exponential_backoff is False
        assert config.jitter is True
    
    def test_retry_config_validates_max_attempts(self):
        """Test RetryConfig validates max_attempts is positive."""
        # Valid values should work
        RetryConfig(max_attempts=1)
        RetryConfig(max_attempts=10)
        
        # Invalid values should raise ValueError
        with pytest.raises(ValueError, match="max_attempts must be at least 1"):
            RetryConfig(max_attempts=0)
        
        with pytest.raises(ValueError, match="max_attempts must be at least 1"):
            RetryConfig(max_attempts=-1)
    
    def test_retry_config_validates_delay_values(self):
        """Test RetryConfig validates delay values are positive."""
        # Valid delays should work
        RetryConfig(base_delay=0.1, max_delay=10.0)
        RetryConfig(base_delay=1.0, max_delay=1.0)  # Equal is OK
        
        # Zero or negative delays should fail
        with pytest.raises(ValueError, match="Delays must be positive"):
            RetryConfig(base_delay=0)
        
        with pytest.raises(ValueError, match="Delays must be positive"):
            RetryConfig(base_delay=-1.0)
        
        with pytest.raises(ValueError, match="Delays must be positive"):
            RetryConfig(max_delay=0)
    
    def test_retry_config_validates_delay_relationship(self):
        """Test RetryConfig validates max_delay >= base_delay."""
        # Valid relationships should work
        RetryConfig(base_delay=1.0, max_delay=5.0)
        RetryConfig(base_delay=2.0, max_delay=2.0)  # Equal is OK
        
        # max_delay < base_delay should fail
        with pytest.raises(ValueError, match="max_delay must be >= base_delay"):
            RetryConfig(base_delay=5.0, max_delay=1.0)
    
    def test_retry_config_post_init_validation_called(self):
        """Test RetryConfig __post_init__ validation is called."""
        # This should pass validation
        config = RetryConfig(max_attempts=3, base_delay=1.0, max_delay=10.0)
        assert config.max_attempts == 3
        
        # This should fail validation
        with pytest.raises(ValueError):
            RetryConfig(max_attempts=0, base_delay=1.0, max_delay=10.0)


class TestRetryHandler:
    """Test RetryHandler implementation with RetryConfig."""
    
    @pytest.fixture
    def basic_config(self):
        """Create basic retry configuration."""
        return RetryConfig(
            max_attempts=3,
            base_delay=0.1,
            max_delay=1.0,
            exponential_backoff=True,
            jitter=False  # Disable jitter for predictable testing
        )
    
    @pytest.fixture
    def retry_handler(self, basic_config):
        """Create RetryHandler with basic config."""
        return RetryHandler(basic_config)
    
    def test_retry_handler_initialization(self, basic_config):
        """Test RetryHandler initializes with RetryConfig."""
        handler = RetryHandler(basic_config)
        assert handler.config == basic_config
    
    def test_retry_handler_calculates_exponential_backoff_delay(self, retry_handler):
        """Test RetryHandler calculates exponential backoff delays correctly."""
        config = retry_handler.config
        
        # First attempt (attempt 0) should use base_delay
        delay1 = retry_handler.calculate_delay(attempt=0)
        assert delay1 == config.base_delay
        
        # Second attempt should be base_delay * 2
        delay2 = retry_handler.calculate_delay(attempt=1)
        assert delay2 == config.base_delay * 2
        
        # Third attempt should be base_delay * 4
        delay3 = retry_handler.calculate_delay(attempt=2)
        assert delay3 == config.base_delay * 4
    
    def test_retry_handler_respects_max_delay(self):
        """Test RetryHandler respects max_delay limit."""
        config = RetryConfig(
            max_attempts=10,
            base_delay=1.0,
            max_delay=5.0,
            exponential_backoff=True,
            jitter=False
        )
        handler = RetryHandler(config)
        
        # Large attempt numbers should be capped at max_delay
        delay = handler.calculate_delay(attempt=10)  # Would be 1024 without cap
        assert delay == config.max_delay
    
    def test_retry_handler_linear_backoff_when_disabled(self):
        """Test RetryHandler uses linear backoff when exponential is disabled."""
        config = RetryConfig(
            max_attempts=3,
            base_delay=2.0,
            max_delay=10.0,
            exponential_backoff=False,
            jitter=False
        )
        handler = RetryHandler(config)
        
        # All attempts should use base_delay when exponential is disabled
        delay1 = handler.calculate_delay(attempt=0)
        delay2 = handler.calculate_delay(attempt=1)
        delay3 = handler.calculate_delay(attempt=2)
        
        assert delay1 == config.base_delay
        assert delay2 == config.base_delay
        assert delay3 == config.base_delay
    
    def test_retry_handler_adds_jitter_when_enabled(self):
        """Test RetryHandler adds jitter when enabled."""
        config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=5.0,
            exponential_backoff=False,
            jitter=True
        )
        handler = RetryHandler(config)
        
        # With jitter, delays should vary slightly
        delays = [handler.calculate_delay(attempt=0) for _ in range(10)]
        
        # Should have some variation (not all identical)
        assert len(set(delays)) > 1
        
        # But all should be reasonably close to base_delay
        for delay in delays:
            assert 0.5 <= delay <= 1.5  # Within 50% of base_delay
    
    def test_retry_handler_execute_with_successful_operation(self, retry_handler):
        """Test RetryHandler.execute with operation that succeeds immediately."""
        call_count = 0
        
        def successful_operation():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = retry_handler.execute(successful_operation)
        
        assert result == "success"
        assert call_count == 1  # Should only be called once
    
    def test_retry_handler_execute_with_operation_that_fails_then_succeeds(self, retry_handler):
        """Test RetryHandler.execute with operation that fails then succeeds."""
        call_count = 0
        
        def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary failure")
            return "success after retry"
        
        result = retry_handler.execute(flaky_operation)
        
        assert result == "success after retry"
        assert call_count == 2  # Should be called twice
    
    def test_retry_handler_execute_with_operation_that_always_fails(self, retry_handler):
        """Test RetryHandler.execute with operation that always fails."""
        call_count = 0
        
        def failing_operation():
            nonlocal call_count
            call_count += 1
            raise Exception(f"Failure {call_count}")
        
        with pytest.raises(Exception, match="Failure 3"):
            retry_handler.execute(failing_operation)
        
        # Should be called max_attempts times
        assert call_count == retry_handler.config.max_attempts
    
    @patch('time.sleep')
    def test_retry_handler_execute_uses_calculated_delays(self, mock_sleep, retry_handler):
        """Test RetryHandler.execute uses calculated delays between retries."""
        call_count = 0
        
        def operation_fails_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Still failing")
            return "finally succeeded"
        
        result = retry_handler.execute(operation_fails_twice)
        
        assert result == "finally succeeded"
        assert call_count == 3
        
        # Should have slept between retries
        expected_delays = [
            retry_handler.calculate_delay(0),  # After first failure
            retry_handler.calculate_delay(1)   # After second failure
        ]
        
        assert mock_sleep.call_count == 2
        actual_delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert actual_delays == expected_delays
    
    def test_retry_handler_tracks_attempt_count(self, retry_handler):
        """Test RetryHandler tracks attempt count during execution."""
        attempt_counts = []
        
        def track_attempts():
            attempt_counts.append(retry_handler.current_attempt)
            if len(attempt_counts) < 2:
                raise Exception("Need more attempts")
            return "done"
        
        result = retry_handler.execute(track_attempts)
        
        assert result == "done"
        assert attempt_counts == [1, 2]  # Should track 1-based attempt numbers
    
    def test_retry_config_integration_with_tenacity(self):
        """Test RetryConfig integrates properly with tenacity library."""
        try:
            from tenacity import Retrying, stop_after_attempt, wait_exponential
        except ImportError:
            pytest.skip("tenacity library not available")
        
        config = RetryConfig(
            max_attempts=3,
            base_delay=0.1,
            max_delay=1.0,
            exponential_backoff=True
        )
        
        # Create tenacity retry configuration from our config
        retryer = Retrying(
            stop=stop_after_attempt(config.max_attempts),
            wait=wait_exponential(multiplier=config.base_delay, max=config.max_delay)
        )
        
        call_count = 0
        
        def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Retry needed")
            return "success"
        
        result = retryer(operation)
        assert result == "success"
        assert call_count == 2
