from src.workers.models import PoolConfig, Profile
from src.workers.worker_process import WorkerProcess


class _MessengerStub:
    def __init__(self):
        self.metrics = []

    def send_metric(self, payload):
        self.metrics.append(payload)


def test_worker_process_emits_starting_and_ready_metrics(tmp_path, monkeypatch):
    base_profile = tmp_path / "base-profile"
    worker_profile = tmp_path / "worker-profile"
    base_profile.mkdir()
    worker_profile.mkdir()

    messenger = _MessengerStub()
    process = WorkerProcess(
        worker_id="worker-2",
        profile=Profile(
            base_profile_path=str(base_profile),
            worker_profile_path=str(worker_profile),
            worker_id="worker-2",
        ),
        config=PoolConfig(
            worker_count=2,
            autoscaling_enabled=True,
            base_profile_path=str(base_profile),
            download_root=str(tmp_path / "downloads"),
            profile_cleanup_on_shutdown=False,
        ),
        messenger=messenger,
    )

    monkeypatch.setattr(process, "_initialize_browser_session", lambda: None)

    process.start()

    statuses = [metric["status"] for metric in messenger.metrics]
    assert statuses[:2] == ["STARTING", "READY"]
    assert messenger.metrics[0]["worker_id"] == "worker-2"
    assert messenger.metrics[1]["message"] == "worker-2 is ready"
