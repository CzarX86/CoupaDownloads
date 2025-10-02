"""Unit tests for profile verification methods.

These tests validate the profile verification system,
including different verification methods and result aggregation.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime
import time

# These imports will fail until implementations exist - tests should fail
try:
    from EXPERIMENTAL.workers.profile_verification import ProfileVerifier
    from EXPERIMENTAL.workers.verifiers.capability_verifier import CapabilityVerifier
    from EXPERIMENTAL.workers.verifiers.auth_verifier import AuthVerifier
    from EXPERIMENTAL.workers.verifiers.file_verifier import FileVerifier
    from specs.parallel_profile_clone.contracts.profile_manager_contract import (
        VerificationMethod,
        VerificationStatus,
        VerificationConfig,
        MethodResult,
        VerificationResult,
        WorkerProfile,
        ProfileType,
        RetryConfig
    )
except ImportError as e:
    pytest.skip(f"Implementation not available: {e}", allow_module_level=True)


class TestProfileVerification:
    """Test profile verification operations."""
    
    @pytest.fixture
    def worker_profile(self, tmp_path):
        """Create test WorkerProfile."""
        profile_path = tmp_path / "test_profile"
        profile_path.mkdir()
        (profile_path / "Preferences").write_text('{"test": "data"}')
        
        return WorkerProfile(
            worker_id=1,
            profile_type=ProfileType.CLONE,
            profile_path=profile_path,
            created_at=datetime.now()
        )
    
    @pytest.fixture
    def verification_config(self):
        """Create test verification configuration."""
        return VerificationConfig(
            enabled_methods=[
                VerificationMethod.CAPABILITY_CHECK,
                VerificationMethod.AUTH_CHECK,
                VerificationMethod.FILE_VERIFICATION
            ],
            capability_timeout=5.0,
            auth_check_timeout=10.0,
            auth_check_url="https://test.coupa.com/health",
            file_verification_enabled=True,
            retry_config=RetryConfig(max_attempts=2, base_delay=1.0)
        )
    
    @pytest.fixture
    def verifier(self, verification_config):
        """Create ProfileVerifier instance."""
        return ProfileVerifier(verification_config)
    
    def test_profile_verifier_initialization(self, verification_config):
        """Test ProfileVerifier initializes correctly."""
        verifier = ProfileVerifier(verification_config)
        
        assert verifier.config == verification_config
        assert hasattr(verifier, 'capability_verifier')
        assert hasattr(verifier, 'auth_verifier')
        assert hasattr(verifier, 'file_verifier')
    
    def test_profile_verifier_runs_all_enabled_methods(self, verifier, worker_profile):
        """Test ProfileVerifier runs all enabled verification methods."""
        with patch.object(verifier.capability_verifier, 'verify') as mock_cap, \
             patch.object(verifier.auth_verifier, 'verify') as mock_auth, \
             patch.object(verifier.file_verifier, 'verify') as mock_file:
            
            # Mock successful verifications
            mock_cap.return_value = MethodResult(
                method=VerificationMethod.CAPABILITY_CHECK,
                success=True,
                duration_seconds=1.0
            )
            mock_auth.return_value = MethodResult(
                method=VerificationMethod.AUTH_CHECK,
                success=True,
                duration_seconds=2.0
            )
            mock_file.return_value = MethodResult(
                method=VerificationMethod.FILE_VERIFICATION,
                success=True,
                duration_seconds=0.5
            )
            
            result = verifier.verify_profile(worker_profile)
            
            # All methods should be called
            mock_cap.assert_called_once_with(worker_profile)
            mock_auth.assert_called_once_with(worker_profile)
            mock_file.assert_called_once_with(worker_profile)
            
            # Result should be successful
            assert result.overall_status == VerificationStatus.SUCCESS
            assert len(result.method_results) == 3
    
    def test_profile_verifier_handles_partial_success(self, verifier, worker_profile):
        """Test ProfileVerifier handles partial verification success."""
        with patch.object(verifier.capability_verifier, 'verify') as mock_cap, \
             patch.object(verifier.auth_verifier, 'verify') as mock_auth, \
             patch.object(verifier.file_verifier, 'verify') as mock_file:
            
            # Mock mixed results
            mock_cap.return_value = MethodResult(
                method=VerificationMethod.CAPABILITY_CHECK,
                success=True,
                duration_seconds=1.0
            )
            mock_auth.return_value = MethodResult(
                method=VerificationMethod.AUTH_CHECK,
                success=False,
                error_message="Auth failed",
                duration_seconds=5.0
            )
            mock_file.return_value = MethodResult(
                method=VerificationMethod.FILE_VERIFICATION,
                success=True,
                duration_seconds=0.5
            )
            
            result = verifier.verify_profile(worker_profile)
            
            # Should be partial success
            assert result.overall_status == VerificationStatus.PARTIAL
            assert len(result.get_failed_methods()) == 1
            assert VerificationMethod.AUTH_CHECK in result.get_failed_methods()
    
    def test_profile_verifier_handles_complete_failure(self, verifier, worker_profile):
        """Test ProfileVerifier handles complete verification failure."""
        with patch.object(verifier.capability_verifier, 'verify') as mock_cap, \
             patch.object(verifier.auth_verifier, 'verify') as mock_auth, \
             patch.object(verifier.file_verifier, 'verify') as mock_file:
            
            # Mock all failures
            mock_cap.return_value = MethodResult(
                method=VerificationMethod.CAPABILITY_CHECK,
                success=False,
                error_message="Cap check failed",
                duration_seconds=1.0
            )
            mock_auth.return_value = MethodResult(
                method=VerificationMethod.AUTH_CHECK,
                success=False,
                error_message="Auth failed",
                duration_seconds=5.0
            )
            mock_file.return_value = MethodResult(
                method=VerificationMethod.FILE_VERIFICATION,
                success=False,
                error_message="File check failed",
                duration_seconds=0.5
            )
            
            result = verifier.verify_profile(worker_profile)
            
            # Should be complete failure
            assert result.overall_status == VerificationStatus.FAILED
            assert len(result.get_failed_methods()) == 3
    
    def test_profile_verifier_respects_timeout_configuration(self, worker_profile):
        """Test ProfileVerifier respects timeout configuration."""
        # Create config with very short timeouts
        short_timeout_config = VerificationConfig(
            enabled_methods=[VerificationMethod.AUTH_CHECK],
            auth_check_timeout=0.1,  # Very short timeout
            retry_config=RetryConfig(max_attempts=1)
        )
        
        verifier = ProfileVerifier(short_timeout_config)
        
        with patch.object(verifier.auth_verifier, 'verify') as mock_auth:
            # Mock slow verification
            def slow_verify(profile):
                time.sleep(0.2)  # Longer than timeout
                return MethodResult(
                    method=VerificationMethod.AUTH_CHECK,
                    success=True,
                    duration_seconds=0.2
                )
            
            mock_auth.side_effect = slow_verify
            
            result = verifier.verify_profile(worker_profile)
            
            # Should timeout
            assert result.overall_status == VerificationStatus.TIMEOUT
    
    def test_profile_verifier_implements_retry_logic(self, verifier, worker_profile):
        """Test ProfileVerifier implements retry logic for failed verifications."""
        with patch.object(verifier.auth_verifier, 'verify') as mock_auth:
            # First call fails, second succeeds
            mock_auth.side_effect = [
                MethodResult(
                    method=VerificationMethod.AUTH_CHECK,
                    success=False,
                    error_message="Temporary failure"
                ),
                MethodResult(
                    method=VerificationMethod.AUTH_CHECK,
                    success=True,
                    duration_seconds=2.0
                )
            ]
            
            result = verifier.verify_profile(worker_profile)
            
            # Should have retried and succeeded
            assert mock_auth.call_count == 2
            assert result.retry_count == 1
            # Final result should reflect the successful retry
            auth_result = result.method_results[VerificationMethod.AUTH_CHECK]
            assert auth_result.success is True
    
    def test_profile_verifier_tracks_verification_timing(self, verifier, worker_profile):
        """Test ProfileVerifier tracks verification timing accurately."""
        with patch('time.time') as mock_time:
            mock_time.side_effect = [100.0, 105.0]  # 5 second verification
            
            with patch.object(verifier, '_run_verification_methods') as mock_run:
                mock_run.return_value = {}
                
                result = verifier.verify_profile(worker_profile)
                
                # Should track timing
                duration = result.get_duration()
                assert duration == 5.0
    
    def test_profile_verifier_aggregates_results_correctly(self, verifier, worker_profile):
        """Test ProfileVerifier aggregates method results correctly."""
        method_results = {
            VerificationMethod.CAPABILITY_CHECK: MethodResult(
                method=VerificationMethod.CAPABILITY_CHECK,
                success=True,
                duration_seconds=1.0
            ),
            VerificationMethod.AUTH_CHECK: MethodResult(
                method=VerificationMethod.AUTH_CHECK,
                success=True,
                duration_seconds=2.0
            )
        }
        
        overall_status = verifier._aggregate_results(method_results)
        
        # All successful should be SUCCESS
        assert overall_status == VerificationStatus.SUCCESS
        
        # Mixed results should be PARTIAL
        method_results[VerificationMethod.AUTH_CHECK].success = False
        overall_status = verifier._aggregate_results(method_results)
        assert overall_status == VerificationStatus.PARTIAL
        
        # All failed should be FAILED
        method_results[VerificationMethod.CAPABILITY_CHECK].success = False
        overall_status = verifier._aggregate_results(method_results)
        assert overall_status == VerificationStatus.FAILED
    
    def test_profile_verifier_skips_disabled_methods(self, worker_profile):
        """Test ProfileVerifier skips disabled verification methods."""
        # Config with only capability check enabled
        limited_config = VerificationConfig(
            enabled_methods=[VerificationMethod.CAPABILITY_CHECK],
            capability_timeout=5.0
        )
        
        verifier = ProfileVerifier(limited_config)
        
        with patch.object(verifier.capability_verifier, 'verify') as mock_cap, \
             patch.object(verifier.auth_verifier, 'verify') as mock_auth:
            
            mock_cap.return_value = MethodResult(
                method=VerificationMethod.CAPABILITY_CHECK,
                success=True,
                duration_seconds=1.0
            )
            
            result = verifier.verify_profile(worker_profile)
            
            # Only capability check should be called
            mock_cap.assert_called_once()
            mock_auth.assert_not_called()
            
            # Should only have one result
            assert len(result.method_results) == 1
            assert VerificationMethod.CAPABILITY_CHECK in result.method_results
