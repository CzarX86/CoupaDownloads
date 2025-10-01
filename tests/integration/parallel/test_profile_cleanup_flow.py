"""Integration tests for profile cleanup flow (T017)."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

try:
    from EXPERIMENTAL.workers.profile_manager import ProfileManager
    from specs.parallel_profile_clone.contracts.profile_manager_contract import (
        WorkerProfile,
        VerificationStatus,
        ProfileType,
    )
except ImportError as e:
    pytest.skip(f"Implementation not available: {e}", allow_module_level=True)


@pytest.fixture
def manager(tmp_path: Path) -> ProfileManager:
    # Current implementation expects a string path
    return ProfileManager(base_profile_path=str(tmp_path))


def test_cleanup_profile_removes_directory(manager, tmp_path):
    # Create a fake worker profile directory
    clone = tmp_path / "clone_1"
    clone.mkdir()
    (clone / "Preferences").write_text("{}")

    profile = WorkerProfile(
        worker_id=1,
        profile_type=ProfileType.CLONE,
        profile_path=clone,
        created_at=MagicMock()
    )

    assert clone.exists()
    manager.cleanup_profile(profile)
    assert not clone.exists()


def test_shutdown_cleans_all_active_profiles(manager, tmp_path):
    # Prepare two fake profiles and register them as active
    c1 = tmp_path / "c1"; c1.mkdir(); (c1 / "Preferences").write_text("{}")
    c2 = tmp_path / "c2"; c2.mkdir(); (c2 / "Preferences").write_text("{}")

    p1 = WorkerProfile(worker_id=1, profile_type=ProfileType.CLONE, profile_path=c1, created_at=MagicMock())
    p2 = WorkerProfile(worker_id=2, profile_type=ProfileType.CLONE, profile_path=c2, created_at=MagicMock())

    # Emulate manager tracking
    if hasattr(manager, "_active_profiles"):
        manager._active_profiles = [p1, p2]

    manager.shutdown()

    assert not c1.exists()
    assert not c2.exists()
