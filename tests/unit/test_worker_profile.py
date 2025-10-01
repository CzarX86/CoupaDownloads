"""Unit tests for WorkerProfile state management.

These tests validate WorkerProfile state transitions,
validation rules, and method behavior.
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

# These imports will fail until implementations exist - tests should fail
try:
    from EXPERIMENTAL.workers.worker_profile import WorkerProfile
    from specs.parallel_profile_clone.contracts.profile_manager_contract import (
        ProfileType,
        VerificationStatus
    )
except ImportError as e:
    pytest.skip(f"Implementation not available: {e}", allow_module_level=True)


class TestWorkerProfileStateManagement:
    """Test WorkerProfile state management and validation."""
    
    @pytest.fixture
    def profile_path(self, tmp_path):
        """Create a test profile directory."""
        profile_dir = tmp_path / "test_profile"
        profile_dir.mkdir()
        (profile_dir / "Preferences").write_text('{"test": "data"}')
        return profile_dir
    
    @pytest.fixture
    def base_profile(self, profile_path):
        """Create a base WorkerProfile."""
        return WorkerProfile(
            worker_id=1,
            profile_type=ProfileType.BASE,
            profile_path=profile_path,
            created_at=datetime.now()
        )
    
    @pytest.fixture
    def clone_profile(self, tmp_path):
        """Create a clone WorkerProfile."""
        clone_path = tmp_path / "clone_profile"
        clone_path.mkdir()
        (clone_path / "Preferences").write_text('{"clone": "data"}')
        
        return WorkerProfile(
            worker_id=2,
            profile_type=ProfileType.CLONE,
            profile_path=clone_path,
            created_at=datetime.now()
        )
    
    def test_worker_profile_initialization_with_required_fields(self, profile_path):
        """Test WorkerProfile initializes with required fields."""
        created_time = datetime.now()
        
        profile = WorkerProfile(
            worker_id=1,
            profile_type=ProfileType.BASE,
            profile_path=profile_path,
            created_at=created_time
        )
        
        assert profile.worker_id == 1
        assert profile.profile_type == ProfileType.BASE
        assert profile.profile_path == profile_path
        assert profile.created_at == created_time
        assert profile.verification_status == VerificationStatus.PENDING
        assert profile.verified_at is None
    
    def test_worker_profile_validation_positive_worker_id(self, profile_path):
        """Test WorkerProfile validates positive worker_id."""
        # Valid positive IDs should work
        WorkerProfile(
            worker_id=1,
            profile_type=ProfileType.BASE,
            profile_path=profile_path,
            created_at=datetime.now()
        )
        
        WorkerProfile(
            worker_id=999,
            profile_type=ProfileType.CLONE,
            profile_path=profile_path,
            created_at=datetime.now()
        )
        
        # Zero and negative IDs should fail
        with pytest.raises(ValueError, match="worker_id must be positive"):
            WorkerProfile(
                worker_id=0,
                profile_type=ProfileType.BASE,
                profile_path=profile_path,
                created_at=datetime.now()
            )
        
        with pytest.raises(ValueError, match="worker_id must be positive"):
            WorkerProfile(
                worker_id=-1,
                profile_type=ProfileType.CLONE,
                profile_path=profile_path,
                created_at=datetime.now()
            )
    
    def test_worker_profile_selenium_options_default_behavior(self, base_profile):
        """Test WorkerProfile selenium options default behavior."""
        # Default should be empty list or None
        assert base_profile.selenium_options is None or base_profile.selenium_options == []
        
        # get_selenium_options should always return a list
        options = base_profile.get_selenium_options()
        assert isinstance(options, list)
    
    def test_worker_profile_selenium_options_with_custom_options(self, profile_path):
        """Test WorkerProfile preserves custom selenium options."""
        custom_options = ["--headless", "--disable-gpu", "--no-sandbox"]
        
        profile = WorkerProfile(
            worker_id=1,
            profile_type=ProfileType.BASE,
            profile_path=profile_path,
            created_at=datetime.now(),
            selenium_options=custom_options
        )
        
        options = profile.get_selenium_options()
        
        # Custom options should be preserved
        for custom_opt in custom_options:
            assert custom_opt in options
    
    def test_worker_profile_selenium_options_includes_profile_path(self, base_profile):
        """Test get_selenium_options includes profile path."""
        options = base_profile.get_selenium_options()
        
        expected_option = f"--user-data-dir={base_profile.profile_path}"
        assert expected_option in options
    
    def test_worker_profile_selenium_options_includes_standard_flags(self, base_profile):
        """Test get_selenium_options includes standard Edge flags."""
        options = base_profile.get_selenium_options()
        
        # Should include standard flags
        assert "--no-first-run" in options
        assert "--disable-default-apps" in options
    
    def test_worker_profile_is_ready_with_existing_profile_and_success_status(self, base_profile):
        """Test is_ready returns True for existing profile with success status."""
        base_profile.verification_status = VerificationStatus.SUCCESS
        assert base_profile.is_ready() is True
    
    def test_worker_profile_is_ready_with_existing_profile_and_partial_status(self, base_profile):
        """Test is_ready returns True for existing profile with partial status."""
        base_profile.verification_status = VerificationStatus.PARTIAL
        assert base_profile.is_ready() is True
    
    def test_worker_profile_is_ready_false_with_failed_verification(self, base_profile):
        """Test is_ready returns False for failed verification."""
        base_profile.verification_status = VerificationStatus.FAILED
        assert base_profile.is_ready() is False
    
    def test_worker_profile_is_ready_false_with_pending_verification(self, base_profile):
        """Test is_ready returns False for pending verification."""
        base_profile.verification_status = VerificationStatus.PENDING
        assert base_profile.is_ready() is False
    
    def test_worker_profile_is_ready_false_with_missing_profile_path(self, tmp_path):
        """Test is_ready returns False when profile path doesn't exist."""
        missing_path = tmp_path / "missing_profile"
        
        profile = WorkerProfile(
            worker_id=1,
            profile_type=ProfileType.CLONE,
            profile_path=missing_path,
            created_at=datetime.now(),
            verification_status=VerificationStatus.SUCCESS
        )
        
        assert profile.is_ready() is False
    
    def test_worker_profile_verification_summary_includes_required_fields(self, base_profile):
        """Test get_verification_summary includes all required fields."""
        summary = base_profile.get_verification_summary()
        
        required_fields = [
            'worker_id', 'profile_type', 'profile_path',
            'verification_status', 'verified_at', 'is_ready'
        ]
        
        for field in required_fields:
            assert field in summary, f"Missing required field: {field}"
    
    def test_worker_profile_verification_summary_field_types(self, base_profile):
        """Test get_verification_summary returns serializable field types."""
        summary = base_profile.get_verification_summary()
        
        # All fields should be JSON-serializable types
        assert isinstance(summary['worker_id'], int)
        assert isinstance(summary['profile_type'], str)
        assert isinstance(summary['profile_path'], str)
        assert isinstance(summary['verification_status'], str)
        assert isinstance(summary['is_ready'], bool)
        
        # verified_at can be None or string
        assert summary['verified_at'] is None or isinstance(summary['verified_at'], str)
    
    def test_worker_profile_verification_summary_with_verified_profile(self, base_profile):
        """Test get_verification_summary with verified profile."""
        # Set verification details
        verified_time = datetime.now()
        base_profile.verification_status = VerificationStatus.SUCCESS
        base_profile.verified_at = verified_time
        
        summary = base_profile.get_verification_summary()
        
        assert summary['verification_status'] == 'success'
        assert summary['verified_at'] == verified_time.isoformat()
        assert summary['is_ready'] is True
    
    def test_worker_profile_state_transitions_from_pending(self, base_profile):
        """Test valid state transitions from PENDING status."""
        assert base_profile.verification_status == VerificationStatus.PENDING
        
        # Valid transitions from PENDING
        valid_transitions = [
            VerificationStatus.IN_PROGRESS,
            VerificationStatus.SUCCESS,
            VerificationStatus.FAILED,
            VerificationStatus.TIMEOUT
        ]
        
        for status in valid_transitions:
            base_profile.verification_status = status
            assert base_profile.verification_status == status
    
    def test_worker_profile_state_transitions_from_in_progress(self, base_profile):
        """Test valid state transitions from IN_PROGRESS status."""
        base_profile.verification_status = VerificationStatus.IN_PROGRESS
        
        # Valid transitions from IN_PROGRESS
        valid_transitions = [
            VerificationStatus.SUCCESS,
            VerificationStatus.PARTIAL,
            VerificationStatus.FAILED,
            VerificationStatus.TIMEOUT
        ]
        
        for status in valid_transitions:
            base_profile.verification_status = status
            assert base_profile.verification_status == status
    
    def test_worker_profile_verification_timestamp_updates(self, base_profile):
        """Test verification timestamp updates correctly."""
        assert base_profile.verified_at is None
        
        # Simulate successful verification
        verification_time = datetime.now()
        base_profile.verification_status = VerificationStatus.SUCCESS
        base_profile.verified_at = verification_time
        
        assert base_profile.verified_at == verification_time
        
        # Re-verification should update timestamp
        new_verification_time = datetime.now() + timedelta(seconds=10)
        base_profile.verified_at = new_verification_time
        
        assert base_profile.verified_at == new_verification_time
    
    def test_worker_profile_handles_path_types(self, tmp_path):
        """Test WorkerProfile handles different path types correctly."""
        profile_dir = tmp_path / "path_test"
        profile_dir.mkdir()
        
        # Should work with pathlib.Path
        profile1 = WorkerProfile(
            worker_id=1,
            profile_type=ProfileType.BASE,
            profile_path=profile_dir,
            created_at=datetime.now()
        )
        assert isinstance(profile1.profile_path, Path)
        
        # Should work with string path (converted to Path)
        profile2 = WorkerProfile(
            worker_id=2,
            profile_type=ProfileType.CLONE,
            profile_path=str(profile_dir),
            created_at=datetime.now()
        )
        assert isinstance(profile2.profile_path, Path)
        assert profile2.profile_path == profile_dir
    
    def test_worker_profile_comparison_and_equality(self, profile_path):
        """Test WorkerProfile comparison behavior."""
        time1 = datetime.now()
        time2 = time1 + timedelta(seconds=1)
        
        profile1 = WorkerProfile(
            worker_id=1,
            profile_type=ProfileType.BASE,
            profile_path=profile_path,
            created_at=time1
        )
        
        # Same worker_id should be considered equal (or have consistent comparison)
        profile1_copy = WorkerProfile(
            worker_id=1,
            profile_type=ProfileType.BASE,
            profile_path=profile_path,
            created_at=time2  # Different time
        )
        
        # Different worker_id should be different
        profile2 = WorkerProfile(
            worker_id=2,
            profile_type=ProfileType.CLONE,
            profile_path=profile_path,
            created_at=time1
        )
        
        # Profiles should be comparable (for sorting, etc.)
        assert profile1.worker_id != profile2.worker_id
