"""End-to-end integration test for multi-worker profile flow (T019).

This test exercises creating multiple worker profiles, verifying them,
and cleaning up, using patched verification to avoid real browser work.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

try:
    from EXPERIMENTAL.workers.profile_manager import ProfileManager
    from specs.parallel_profile_clone.contracts.profile_manager_contract import (
        VerificationConfig,
        VerificationMethod,
        RetryConfig,
        VerificationStatus,
    )
except ImportError as e:
    pytest.skip(f"Implementation not available: {e}", allow_module_level=True)


@pytest.fixture
def base_profile(tmp_path: Path) -> Path:
    p = tmp_path / "Default"; p.mkdir()
    (p / "Preferences").write_text("{}")
    (p / "Local State").write_text("{}")
    (p / "Cookies").write_text("SQLite format 3\x00")
    return p


def test_end_to_end_multi_worker_flow(base_profile, tmp_path):
    vc = VerificationConfig(enabled_methods=[VerificationMethod.CAPABILITY_CHECK], retry_config=RetryConfig(max_attempts=1, base_delay=0.1))
    manager = ProfileManager(base_profile_path=str(base_profile), max_profiles=4)

    created = []
    with patch.object(manager, "verify_profile") as mock_verify:
        ok = MagicMock(); ok.overall_status = VerificationStatus.SUCCESS; ok.is_success.return_value = True
        mock_verify.return_value = ok

        for wid in range(1, 5):
            p = manager.create_profile(worker_id=str(wid))
            created.append(Path(p))

    # Profiles should be distinct and exist
    assert len(created) == 4
    assert len(set(created)) == 4
    for path in created:
        assert path.exists()

    # Cleanup
    # Cleanup via public API available
    manager.cleanup_all_profiles()
    for path in created:
        assert not path.exists()
