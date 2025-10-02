"""Contract tests for WorkerProfile methods.

These tests validate that WorkerProfile implementations provide
the expected interface and behavior.
"""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

# Import the contracts - these imports will fail until implementations exist
try:
    from specs.parallel_profile_clone.contracts.profile_manager_contract import (
        WorkerProfile,
        ProfileType,
        VerificationStatus
    )
    from EXPERIMENTAL.workers.worker_profile import WorkerProfile as WorkerProfileImpl
except ImportError as e:
    pytest.skip(f"Implementation not available: {e}", allow_module_level=True)


class TestWorkerProfileContract:
    """Test WorkerProfile contract compliance."""
    
    @pytest.fixture
    def profile_path(self, tmp_path):
        """Create a temporary profile directory."""
        profile_dir = tmp_path / "test_profile"
        profile_dir.mkdir()
        # Create some profile files
        (profile_dir / "Preferences").write_text('{"test": "data"}')
        return profile_dir
    
    @pytest.fixture
    def base_worker_profile(self, profile_path):
        """Create a base WorkerProfile instance."""
        return WorkerProfileImpl(
            worker_id=1,
            profile_type=ProfileType.BASE,
            profile_path=profile_path,
            created_at=datetime.now()
        )
    
    @pytest.fixture
    def clone_worker_profile(self, tmp_path):
        """Create a clone WorkerProfile instance."""
        clone_path = tmp_path / "clone_profile"
        clone_path.mkdir()
        (clone_path / "Preferences").write_text('{"clone": "data"}')
        
        return WorkerProfileImpl(
            worker_id=2,
            profile_type=ProfileType.CLONE,
            profile_path=clone_path,
            created_at=datetime.now()
        )
    
    def test_worker_profile_has_required_fields(self, base_worker_profile):
        """Test WorkerProfile has all required fields."""
        assert hasattr(base_worker_profile, 'worker_id')
        assert hasattr(base_worker_profile, 'profile_type')
        assert hasattr(base_worker_profile, 'profile_path')
        assert hasattr(base_worker_profile, 'created_at')
        assert hasattr(base_worker_profile, 'verified_at')
        assert hasattr(base_worker_profile, 'verification_status')
        assert hasattr(base_worker_profile, 'selenium_options')
    
    def test_worker_profile_field_types(self, base_worker_profile):
        """Test WorkerProfile field types are correct."""
        assert isinstance(base_worker_profile.worker_id, int)
        assert isinstance(base_worker_profile.profile_type, ProfileType)
        assert isinstance(base_worker_profile.profile_path, Path)
        assert isinstance(base_worker_profile.created_at, datetime)
        assert isinstance(base_worker_profile.verification_status, VerificationStatus)
    
    def test_worker_profile_validation_positive_worker_id(self):
        """Test WorkerProfile validates positive worker_id."""
        with pytest.raises(ValueError, match="worker_id must be positive"):
            WorkerProfileImpl(
                worker_id=-1,
                profile_type=ProfileType.BASE,
                profile_path=Path("/tmp/test"),
                created_at=datetime.now()
            )
    
    def test_get_selenium_options_returns_list(self, base_worker_profile):
        """Test get_selenium_options returns list of strings."""
        options = base_worker_profile.get_selenium_options()
        assert isinstance(options, list)
        assert all(isinstance(opt, str) for opt in options)
    
    def test_get_selenium_options_includes_user_data_dir(self, base_worker_profile):
        """Test get_selenium_options includes user-data-dir option."""
        options = base_worker_profile.get_selenium_options()
        profile_option = f"--user-data-dir={base_worker_profile.profile_path}"
        assert profile_option in options
    
    def test_get_selenium_options_includes_standard_options(self, base_worker_profile):
        """Test get_selenium_options includes standard Edge options."""
        options = base_worker_profile.get_selenium_options()
        assert "--no-first-run" in options
        assert "--disable-default-apps" in options
    
    def test_is_ready_true_when_profile_exists_and_verified(self, base_worker_profile):
        """Test is_ready returns True when profile exists and is verified."""
        base_worker_profile.verification_status = VerificationStatus.SUCCESS
        assert base_worker_profile.is_ready() is True
    
    def test_is_ready_true_when_profile_exists_and_partial(self, base_worker_profile):
        """Test is_ready returns True even with partial verification."""
        base_worker_profile.verification_status = VerificationStatus.PARTIAL
        assert base_worker_profile.is_ready() is True
    
    def test_is_ready_false_when_profile_missing(self, tmp_path):
        """Test is_ready returns False when profile path doesn't exist."""
        missing_path = tmp_path / "missing_profile"
        profile = WorkerProfileImpl(
            worker_id=1,
            profile_type=ProfileType.CLONE,
            profile_path=missing_path,
            created_at=datetime.now(),
            verification_status=VerificationStatus.SUCCESS
        )
        assert profile.is_ready() is False
    
    def test_is_ready_false_when_not_verified(self, base_worker_profile):
        """Test is_ready returns False when verification failed."""
        base_worker_profile.verification_status = VerificationStatus.FAILED
        assert base_worker_profile.is_ready() is False
    
    def test_get_verification_summary_returns_dict(self, base_worker_profile):
        """Test get_verification_summary returns dictionary."""
        summary = base_worker_profile.get_verification_summary()
        assert isinstance(summary, dict)
    
    def test_get_verification_summary_includes_required_fields(self, base_worker_profile):
        """Test get_verification_summary includes all required fields."""
        summary = base_worker_profile.get_verification_summary()
        
        required_fields = [
            'worker_id', 'profile_type', 'profile_path',
            'verification_status', 'verified_at', 'is_ready'
        ]
        
        for field in required_fields:
            assert field in summary
    
    def test_verification_summary_field_types(self, base_worker_profile):
        """Test get_verification_summary field types are serializable."""
        summary = base_worker_profile.get_verification_summary()
        
        assert isinstance(summary['worker_id'], int)
        assert isinstance(summary['profile_type'], str)
        assert isinstance(summary['profile_path'], str)
        assert isinstance(summary['verification_status'], str)
        assert isinstance(summary['is_ready'], bool)
    
    def test_custom_selenium_options_preserved(self, profile_path):
        """Test custom selenium options are preserved and merged."""
        custom_options = ["--headless", "--disable-gpu"]
        profile = WorkerProfileImpl(
            worker_id=1,
            profile_type=ProfileType.BASE,
            profile_path=profile_path,
            created_at=datetime.now(),
            selenium_options=custom_options
        )
        
        options = profile.get_selenium_options()
        
        # Custom options should be included
        for custom_opt in custom_options:
            assert custom_opt in options
        
        # Standard options should also be included
        assert f"--user-data-dir={profile_path}" in options
        assert "--no-first-run" in options
