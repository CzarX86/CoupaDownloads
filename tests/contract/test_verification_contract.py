"""Contract tests for VerificationResult interface.

These tests validate that VerificationResult implementations
provide the expected interface and behavior.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

# Import the contracts - these imports will fail until implementations exist
try:
    from specs.parallel_profile_clone.contracts.profile_manager_contract import (
        VerificationResult,
        VerificationStatus,
        VerificationMethod,
        MethodResult
    )
    from EXPERIMENTAL.workers.verification_result import (
        VerificationResult as VerificationResultImpl,
        MethodResult as MethodResultImpl
    )
except ImportError as e:
    pytest.skip(f"Implementation not available: {e}", allow_module_level=True)


class TestVerificationResultContract:
    """Test VerificationResult contract compliance."""
    
    @pytest.fixture
    def method_results(self):
        """Create test method results."""
        return {
            VerificationMethod.CAPABILITY_CHECK: MethodResultImpl(
                method=VerificationMethod.CAPABILITY_CHECK,
                success=True,
                duration_seconds=1.5
            ),
            VerificationMethod.AUTH_CHECK: MethodResultImpl(
                method=VerificationMethod.AUTH_CHECK,
                success=False,
                error_message="Authentication failed",
                duration_seconds=5.0
            )
        }
    
    @pytest.fixture
    def successful_verification_result(self, method_results):
        """Create a successful verification result."""
        # Override auth check to be successful
        method_results[VerificationMethod.AUTH_CHECK].success = True
        method_results[VerificationMethod.AUTH_CHECK].error_message = None
        
        return VerificationResultImpl(
            worker_id=1,
            overall_status=VerificationStatus.SUCCESS,
            method_results=method_results,
            started_at=datetime.now() - timedelta(seconds=10),
            completed_at=datetime.now()
        )
    
    @pytest.fixture
    def failed_verification_result(self, method_results):
        """Create a failed verification result."""
        return VerificationResultImpl(
            worker_id=2,
            overall_status=VerificationStatus.FAILED,
            method_results=method_results,
            started_at=datetime.now() - timedelta(seconds=15),
            completed_at=datetime.now(),
            error_details="Profile verification failed"
        )
    
    def test_verification_result_has_required_fields(self, successful_verification_result):
        """Test VerificationResult has all required fields."""
        result = successful_verification_result
        
        assert hasattr(result, 'worker_id')
        assert hasattr(result, 'overall_status')
        assert hasattr(result, 'method_results')
        assert hasattr(result, 'started_at')
        assert hasattr(result, 'completed_at')
        assert hasattr(result, 'error_details')
        assert hasattr(result, 'retry_count')
    
    def test_verification_result_field_types(self, successful_verification_result):
        """Test VerificationResult field types are correct."""
        result = successful_verification_result
        
        assert isinstance(result.worker_id, int)
        assert isinstance(result.overall_status, VerificationStatus)
        assert isinstance(result.method_results, dict)
        assert isinstance(result.started_at, datetime)
        assert isinstance(result.completed_at, datetime)
        assert isinstance(result.retry_count, int)
    
    def test_is_success_returns_true_for_successful_verification(self, successful_verification_result):
        """Test is_success returns True for successful verification."""
        assert successful_verification_result.is_success() is True
    
    def test_is_success_returns_false_for_failed_verification(self, failed_verification_result):
        """Test is_success returns False for failed verification."""
        assert failed_verification_result.is_success() is False
    
    def test_get_failed_methods_returns_empty_list_for_success(self, successful_verification_result):
        """Test get_failed_methods returns empty list for successful verification."""
        failed_methods = successful_verification_result.get_failed_methods()
        assert isinstance(failed_methods, list)
        assert len(failed_methods) == 0
    
    def test_get_failed_methods_returns_failed_methods(self, failed_verification_result):
        """Test get_failed_methods returns list of failed verification methods."""
        failed_methods = failed_verification_result.get_failed_methods()
        assert isinstance(failed_methods, list)
        assert len(failed_methods) > 0
        assert VerificationMethod.AUTH_CHECK in failed_methods
    
    def test_get_duration_returns_positive_float(self, successful_verification_result):
        """Test get_duration returns positive duration in seconds."""
        duration = successful_verification_result.get_duration()
        assert isinstance(duration, float)
        assert duration > 0
    
    def test_get_duration_calculates_correctly(self):
        """Test get_duration calculates time difference correctly."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=5.5)
        
        result = VerificationResultImpl(
            worker_id=1,
            overall_status=VerificationStatus.SUCCESS,
            method_results={},
            started_at=start_time,
            completed_at=end_time
        )
        
        duration = result.get_duration()
        assert abs(duration - 5.5) < 0.1  # Allow small floating point difference


class TestMethodResultContract:
    """Test MethodResult contract compliance."""
    
    @pytest.fixture
    def successful_method_result(self):
        """Create a successful method result."""
        return MethodResultImpl(
            method=VerificationMethod.CAPABILITY_CHECK,
            success=True,
            duration_seconds=1.2,
            details={'profile_path': '/tmp/test_profile'}
        )
    
    @pytest.fixture
    def failed_method_result(self):
        """Create a failed method result."""
        return MethodResultImpl(
            method=VerificationMethod.AUTH_CHECK,
            success=False,
            error_message="Connection timeout",
            duration_seconds=10.0,
            details={'endpoint': 'https://test.coupa.com', 'status_code': 408}
        )
    
    def test_method_result_has_required_fields(self, successful_method_result):
        """Test MethodResult has all required fields."""
        result = successful_method_result
        
        assert hasattr(result, 'method')
        assert hasattr(result, 'success')
        assert hasattr(result, 'error_message')
        assert hasattr(result, 'duration_seconds')
        assert hasattr(result, 'details')
    
    def test_method_result_field_types(self, successful_method_result):
        """Test MethodResult field types are correct."""
        result = successful_method_result
        
        assert isinstance(result.method, VerificationMethod)
        assert isinstance(result.success, bool)
        assert isinstance(result.duration_seconds, (int, float))
        assert result.details is None or isinstance(result.details, dict)
    
    def test_method_result_success_case(self, successful_method_result):
        """Test MethodResult for successful verification."""
        result = successful_method_result
        
        assert result.success is True
        assert result.error_message is None or result.error_message == ""
        assert result.duration_seconds > 0
    
    def test_method_result_failure_case(self, failed_method_result):
        """Test MethodResult for failed verification."""
        result = failed_method_result
        
        assert result.success is False
        assert result.error_message is not None
        assert len(result.error_message) > 0
        assert result.duration_seconds >= 0
    
    def test_method_result_details_optional(self):
        """Test MethodResult details field is optional."""
        result = MethodResultImpl(
            method=VerificationMethod.FILE_VERIFICATION,
            success=True,
            duration_seconds=0.5
        )
        
        assert result.details is None or result.details == {}
    
    def test_method_result_post_init_validation(self):
        """Test MethodResult __post_init__ validation works correctly."""
        # Should initialize empty details dict if None
        result = MethodResultImpl(
            method=VerificationMethod.CAPABILITY_CHECK,
            success=True,
            duration_seconds=1.0,
            details=None
        )
        
        # Post-init should set empty dict
        assert result.details == {}
