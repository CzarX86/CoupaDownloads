from src.core.exceptions import SessionExpiredError
from src.workers.models import POTask, PoolConfig, Profile, TaskPriority, WorkerStatus
from src.workers.worker_process import WorkerProcess, WorkerFatalError


class _TabStub:
    def assign_po(self, _po_number: str) -> None:
        return None


class _CrashBrowserSession:
    def __init__(self):
        self.driver = object()
        self.active_tabs = {}
        self._using_playwright = False

    def create_tab(self, _task_id: str) -> str:
        raise RuntimeError("Failed to create new tab")

    def focus_main_window(self) -> bool:
        return True


class _RecoveringBrowserSession:
    def __init__(self, can_recover: bool):
        self.driver = object()
        self.active_tabs = {}
        self._using_playwright = False
        self.can_recover = can_recover
        self.recovery_attempts = 0

    def create_tab(self, task_id: str) -> str:
        self.active_tabs[task_id] = _TabStub()
        return f"tab-{task_id}"

    def close_tab(self, _tab_handle: str) -> None:
        return None

    def focus_main_window(self) -> bool:
        return True

    def recover_session(self) -> bool:
        self.recovery_attempts += 1
        return self.can_recover


def _build_process(tmp_path):
    base_profile = tmp_path / "base-profile"
    worker_profile = tmp_path / "worker-profile"
    downloads = tmp_path / "downloads"
    base_profile.mkdir()
    worker_profile.mkdir()
    downloads.mkdir()

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
    )
    process._running = True
    process.worker.status = WorkerStatus.READY
    return process


def _new_task() -> POTask:
    task = POTask(po_number="PO-123", priority=TaskPriority.NORMAL)
    task.task_id = "task-123"
    return task


def test_worker_escalates_after_three_consecutive_tab_creation_failures(tmp_path):
    process = _build_process(tmp_path)
    process.browser_session = _CrashBrowserSession()

    first = process.process_task(_new_task())
    second = process.process_task(_new_task())

    assert first["success"] is False
    assert second["success"] is False

    try:
        process.process_task(_new_task())
        assert False, "Expected WorkerFatalError on third consecutive tab creation failure"
    except WorkerFatalError:
        pass


def test_session_expiry_is_recovered_with_single_retry(tmp_path, monkeypatch):
    process = _build_process(tmp_path)
    session = _RecoveringBrowserSession(can_recover=True)
    process.browser_session = session

    calls = {"count": 0}

    def _fake_process_single_po(**_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise SessionExpiredError("session expired")
        return {"success": True, "status_code": "COMPLETED"}

    monkeypatch.setattr("src.workers.worker_process.process_single_po", _fake_process_single_po)

    result = process.process_task(_new_task())

    assert result["success"] is True
    assert calls["count"] == 2
    assert session.recovery_attempts == 1


def test_session_expiry_unrecoverable_escalates_to_worker_restart(tmp_path, monkeypatch):
    process = _build_process(tmp_path)
    session = _RecoveringBrowserSession(can_recover=False)
    process.browser_session = session

    def _fake_process_single_po(**_kwargs):
        raise SessionExpiredError("session expired")

    monkeypatch.setattr("src.workers.worker_process.process_single_po", _fake_process_single_po)

    try:
        process.process_task(_new_task())
        assert False, "Expected WorkerFatalError when session recovery fails"
    except WorkerFatalError:
        pass
