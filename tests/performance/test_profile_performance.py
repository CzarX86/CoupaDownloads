"""
Performance benchmarking for profile cloning (T050).

Measures time to create N profiles from a small base directory. This is a
lightweight test intended to run quickly; it does not enforce hard thresholds
but records timings for inspection.
"""

import time
from pathlib import Path
import pytest


try:
    from EXPERIMENTAL.workers.profile_manager import ProfileManager
except Exception as e:
    pytest.skip(f"ProfileManager not available: {e}", allow_module_level=True)


def _make_base(tmp_path: Path) -> Path:
    base = tmp_path / "Default"; base.mkdir()
    (base / "Preferences").write_text("{}")
    (base / "Local State").write_text("{}")
    (base / "Cookies").write_text("SQLite format 3\x00")
    return base


def test_clone_performance_smoke(tmp_path: Path):
    base = _make_base(tmp_path)
    manager = ProfileManager(base_profile_path=str(base), max_profiles=5)

    n = 5
    t0 = time.time()
    created = []
    for i in range(1, n + 1):
        p = manager.create_profile(worker_id=str(i))
        created.append(Path(p))
    elapsed = time.time() - t0

    # Soft assertion: cloning shouldn’t be unreasonably slow on tiny base
    assert elapsed < 10.0, f"Cloning {n} tiny profiles took {elapsed:.2f}s"

    manager.cleanup_all_profiles()
    for p in created:
        assert not p.exists()
