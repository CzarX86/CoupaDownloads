from src.workers.models import POTask, PoolConfig, Profile, TaskPriority
from src.workers.worker_process import WorkerProcess


class _MessengerStub:
    def __init__(self):
        self.metrics = []

    def send_metric(self, payload):
        self.metrics.append(payload)


def _build_process(tmp_path):
    base_profile = tmp_path / "base-profile"
    worker_profile = tmp_path / "worker-profile"
    downloads = tmp_path / "downloads"
    base_profile.mkdir()
    worker_profile.mkdir()
    downloads.mkdir()

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
            download_root=str(downloads),
            profile_cleanup_on_shutdown=False,
        ),
        messenger=messenger,
    )
    return process, messenger


def test_worker_progress_metrics_are_debounced_in_aggregated_mode(tmp_path, monkeypatch):
    process, messenger = _build_process(tmp_path)
    monkeypatch.setattr("src.workers.worker_process.time.time", lambda: 10.0)

    task = POTask(po_number="PO-42", priority=TaskPriority.NORMAL)
    task.task_id = "task-42"

    process._emit_task_progress(
        task,
        {
            "attachments_found": 4,
            "attachments_downloaded": 1,
            "message": "Downloading attachment 1/4",
        },
    )
    process._emit_task_progress(
        task,
        {
            "attachments_found": 4,
            "attachments_downloaded": 1,
            "message": "Downloading attachment 1/4",
        },
    )

    assert len(messenger.metrics) == 1
    assert messenger.metrics[0]["status"] == "PROCESSING"


def test_worker_progress_metrics_emit_when_download_count_changes(tmp_path, monkeypatch):
    process, messenger = _build_process(tmp_path)
    timestamps = iter([10.0, 10.1])
    monkeypatch.setattr("src.workers.worker_process.time.time", lambda: next(timestamps))

    task = POTask(po_number="PO-42", priority=TaskPriority.NORMAL)
    task.task_id = "task-42"

    process._emit_task_progress(
        task,
        {
            "attachments_found": 4,
            "attachments_downloaded": 1,
            "message": "Downloading attachment 1/4",
        },
    )
    process._emit_task_progress(
        task,
        {
            "attachments_found": 4,
            "attachments_downloaded": 2,
            "message": "Downloading attachment 2/4",
        },
    )

    assert [metric["attachments_downloaded"] for metric in messenger.metrics] == [1, 2]
