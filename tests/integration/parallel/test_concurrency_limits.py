"""Integration tests for concurrency limits in ProfileManager (T018)."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import threading

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


def test_max_concurrent_clones_is_respected(base_profile, tmp_path):
    vc = VerificationConfig(enabled_methods=[VerificationMethod.CAPABILITY_CHECK], retry_config=RetryConfig(max_attempts=1, base_delay=0.1))
    manager = ProfileManager(base_profile_path=str(base_profile), max_profiles=2)

    # Patch actual clone work to block until released to simulate long copy
    active = 0
    peak = 0
    gate = threading.Event()

    def fake_clone(worker_id):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        gate.wait(timeout=1.0)
        active -= 1
        m = MagicMock()
        m.profile_path = tmp_path / f"c{worker_id}"; m.profile_path.mkdir(exist_ok=True)
        return m

    with patch.object(manager, "_create_profile_directory", side_effect=lambda wid: fake_clone(wid)):
        with patch.object(manager, "verify_profile") as mock_verify:
            ok = MagicMock(); ok.overall_status = VerificationStatus.SUCCESS; ok.is_success.return_value = True
            mock_verify.return_value = ok

            # Start 3 threads; only 2 should run clone concurrently
            threads = [threading.Thread(target=manager.create_profile, args=(str(i),)) for i in (1,2,3)]
            for t in threads:
                t.start()
            # Give them time to start and block
            for _ in range(10):
                if peak >= 2:
                    break
                threading.Event().wait(0.05)
            # Release gate to finish
            gate.set()
            for t in threads:
                t.join()

    assert peak <= 2, f"Expected concurrency peak <= 2, got {peak}"
