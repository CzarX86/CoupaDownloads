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


def test_worker_process_startup_delay_is_small(tmp_path):
    process = _build_process(tmp_path, worker_id="worker-4")

    delay = process._get_startup_delay_seconds()

    assert 0.1 <= delay <= 0.31
