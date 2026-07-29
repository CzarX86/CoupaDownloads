import urllib3

from src.workers.models import PoolConfig, Profile
from src.workers.worker_process import WorkerProcess


def _build_process(tmp_path, worker_id="worker-1"):
    base_profile = tmp_path / f"{worker_id}-base"
    worker_profile = tmp_path / f"{worker_id}-profile"
    downloads = tmp_path / f"{worker_id}-downloads"
    base_profile.mkdir()
    worker_profile.mkdir()
    downloads.mkdir()

    return WorkerProcess(
        worker_id=worker_id,
        profile=Profile(
            base_profile_path=str(base_profile),
            worker_profile_path=str(worker_profile),
            worker_id=worker_id,
        ),
        config=PoolConfig(
            worker_count=2,
            autoscaling_enabled=True,
            base_profile_path=str(base_profile),
            download_root=str(downloads),
            profile_cleanup_on_shutdown=False,
        ),
    )


def test_connection_pool_patch_is_applied_only_once(tmp_path, monkeypatch):
    process = _build_process(tmp_path)
    original_init = urllib3.connectionpool.HTTPConnectionPool.__init__
    monkeypatch.setattr(urllib3.connectionpool.HTTPConnectionPool, "__init__", original_init)

    process._configure_connection_pools()
    first_patch = urllib3.connectionpool.HTTPConnectionPool.__init__

    process._configure_connection_pools()
    second_patch = urllib3.connectionpool.HTTPConnectionPool.__init__

    assert first_patch is second_patch
