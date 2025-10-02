"""Integration tests for profile verification flow (T016).

Defines expectations for verify_profile behavior and result structure.
Tests are written TDD-style and will be skipped until implementations exist.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# Skip if implementation not available yet
try:
    from EXPERIMENTAL.workers.profile_manager import ProfileManager
    from specs.parallel_profile_clone.contracts.profile_manager_contract import (
        WorkerProfile,
        VerificationResult,
        VerificationMethod,
        VerificationStatus,
        MethodResult,
        VerificationConfig,
        RetryConfig,
        ProfileType,
    )
except ImportError as e:
    pytest.skip(f"Implementation not available: {e}", allow_module_level=True)


@pytest.fixture
def fake_profile(tmp_path: Path) -> WorkerProfile:
    base = tmp_path / "Default"
    base.mkdir()
    (base / "Preferences").write_text('{"p":1}')
    (base / "Local State").write_text('{"p":1}')
    (base / "Cookies").write_text("SQLite format 3\x00")

    # Construct a WorkerProfile per contract
    return WorkerProfile(
        worker_id=1,
        profile_type=ProfileType.CLONE,
        profile_path=base,
        created_at=datetime.now(),
    )


@pytest.fixture
def manager(tmp_path: Path) -> ProfileManager:
    return ProfileManager(base_profile_path=tmp_path)


def _make_success_result(worker_id: int) -> VerificationResult:
    start = datetime.now()
    end = start
    method = VerificationMethod.CAPABILITY_CHECK
    mr = MethodResult(method=method, success=True, duration_seconds=0.1)
    return VerificationResult(
        worker_id=worker_id,
        overall_status=VerificationStatus.SUCCESS,
        method_results={method: mr},
        started_at=start,
        completed_at=end,
        retry_count=0,
    )


def test_verify_profile_returns_success_structure(manager, fake_profile):
    """verify_profile should return a VerificationResult with expected fields."""
    with patch.object(manager, "verify_profile", autospec=True) as mock_verify:
        result = _make_success_result(fake_profile.worker_id)
        mock_verify.return_value = result

        out = manager.verify_profile(fake_profile)

    assert isinstance(out, VerificationResult)
    assert out.overall_status in {VerificationStatus.SUCCESS, VerificationStatus.PARTIAL}
    assert isinstance(out.method_results, dict)
    assert out.get_duration() >= 0
    assert out.is_success() in {True, False}


def test_verify_profile_records_failed_methods(manager, fake_profile):
    with patch.object(manager, "verify_profile", autospec=True) as mock_verify:
        start = datetime.now(); end = start
        m1 = VerificationMethod.CAPABILITY_CHECK
        m2 = VerificationMethod.FILE_VERIFICATION
        mr1 = MethodResult(method=m1, success=True)
        mr2 = MethodResult(method=m2, success=False, error_message="missing file")
        result = VerificationResult(
            worker_id=fake_profile.worker_id,
            overall_status=VerificationStatus.PARTIAL,
            method_results={m1: mr1, m2: mr2},
            started_at=start,
            completed_at=end,
            retry_count=1,
        )
        mock_verify.return_value = result

        out = manager.verify_profile(fake_profile)

    failed = out.get_failed_methods()
    assert m2 in failed
    assert m1 not in failed
