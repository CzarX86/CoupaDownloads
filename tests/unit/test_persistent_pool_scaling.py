import asyncio

from src.workers.task_queue import ProcessingTask
from src.workers.models import PoolConfig
from src.workers.persistent_pool import PersistentWorkerPool


class _WorkerStub:
    def __init__(self, worker_id, status, *, accepts_tasks=True, has_pending_assignment=False):
        self.worker_id = worker_id
        self._status = status
        self._accepts_tasks = accepts_tasks
        self._has_pending_assignment = has_pending_assignment
        self.assigned_tasks = []

    def get_status(self):
        return {"status": self._status}

    def can_accept_task(self):
        return self._accepts_tasks and not self._has_pending_assignment

    def submit_task_assignment(self, task):
        if not self.can_accept_task():
            return False
        self.assigned_tasks.append(task)
        self._has_pending_assignment = True
        return True

    def has_pending_assignment(self):
        return self._has_pending_assignment


def _build_pool(tmp_path, worker_count=4):
    profile_dir = tmp_path / "profile"
    download_dir = tmp_path / "downloads"
    profile_dir.mkdir()
    download_dir.mkdir()
    return PersistentWorkerPool(
        PoolConfig(
            worker_count=worker_count,
            autoscaling_enabled=worker_count > 1,
            base_profile_path=str(profile_dir),
            download_root=str(download_dir),
            profile_cleanup_on_shutdown=False,
        )
    )


def test_pool_starts_in_single_worker_mode_when_autoscaling_enabled(tmp_path):
    pool = _build_pool(tmp_path, worker_count=4)

    assert pool._autoscaling_enabled is True
    assert pool._active_worker_target == 1
    assert pool._target_worker_count == 4


def test_pool_uses_fixed_worker_target_when_autoscaling_disabled(tmp_path):
    profile_dir = tmp_path / "profile-fixed"
    download_dir = tmp_path / "downloads-fixed"
    profile_dir.mkdir()
    download_dir.mkdir()
    pool = PersistentWorkerPool(
        PoolConfig(
            worker_count=3,
            autoscaling_enabled=False,
            base_profile_path=str(profile_dir),
            download_root=str(download_dir),
            profile_cleanup_on_shutdown=False,
        )
    )

    assert pool._autoscaling_enabled is False
    assert pool._active_worker_target == 3


def test_calculate_worker_adjustment_scales_up_with_queue_pressure(tmp_path):
    pool = _build_pool(tmp_path, worker_count=4)
    pool.workers = {"worker-1": object()}

    adjustment = pool._calculate_worker_adjustment(
        {"pending_tasks": 3, "processing_tasks": 1},
        {"cpu_percent": 42.0, "available_ram_gb": 4.5},
    )

    assert adjustment == 1


def test_calculate_worker_adjustment_scales_up_when_three_workers_are_busy_and_one_is_waiting(tmp_path):
    pool = _build_pool(tmp_path, worker_count=6)
    pool.workers = {
        "worker-1": object(),
        "worker-2": object(),
        "worker-3": object(),
    }

    adjustment = pool._calculate_worker_adjustment(
        {"pending_tasks": 2, "processing_tasks": 3},
        {"cpu_percent": 58.0, "available_ram_gb": 3.2},
    )

    assert adjustment == 1


def test_calculate_worker_adjustment_holds_when_not_all_current_workers_are_busy(tmp_path):
    pool = _build_pool(tmp_path, worker_count=6)
    pool.workers = {
        "worker-1": object(),
        "worker-2": object(),
        "worker-3": object(),
    }

    adjustment = pool._calculate_worker_adjustment(
        {"pending_tasks": 3, "processing_tasks": 2},
        {"cpu_percent": 58.0, "available_ram_gb": 3.2},
    )

    assert adjustment == 0


def test_calculate_worker_adjustment_holds_fourth_worker_when_only_one_item_is_waiting(tmp_path):
    pool = _build_pool(tmp_path, worker_count=6)
    pool.workers = {
        "worker-1": object(),
        "worker-2": object(),
        "worker-3": object(),
    }

    adjustment = pool._calculate_worker_adjustment(
        {"pending_tasks": 1, "processing_tasks": 3},
        {"cpu_percent": 58.0, "available_ram_gb": 3.2},
    )

    assert adjustment == 0


def test_calculate_worker_adjustment_scales_down_under_pressure(tmp_path):
    pool = _build_pool(tmp_path, worker_count=4)
    pool.workers = {"worker-1": object(), "worker-2": object(), "worker-3": object()}

    adjustment = pool._calculate_worker_adjustment(
        {"pending_tasks": 0, "processing_tasks": 1},
        {"cpu_percent": 95.0, "available_ram_gb": 0.4},
    )

    assert adjustment == -1


def test_calculate_worker_adjustment_holds_when_scale_up_is_not_safe(tmp_path):
    pool = _build_pool(tmp_path, worker_count=4)
    pool.workers = {"worker-1": object()}

    adjustment = pool._calculate_worker_adjustment(
        {"pending_tasks": 4, "processing_tasks": 1},
        {"cpu_percent": 84.0, "available_ram_gb": 2.0},
    )

    assert adjustment == 0


def test_dispatch_assigns_one_task_to_each_idle_worker(tmp_path, monkeypatch):
    pool = _build_pool(tmp_path, worker_count=4)
    pool.workers = {
        "worker-1": _WorkerStub("worker-1", "ready"),
        "worker-2": _WorkerStub("worker-2", "ready"),
    }

    assignments = [
        ProcessingTask(task_id="task-1", po_data={"po_number": "PO-1"}, task_function=lambda _: {}),
        ProcessingTask(task_id="task-2", po_data={"po_number": "PO-2"}, task_function=lambda _: {}),
    ]

    def _next_task(_worker_id):
        return assignments.pop(0) if assignments else None

    monkeypatch.setattr(pool.task_queue, "get_next_task", _next_task)

    dispatched = pool._dispatch_tasks_to_idle_workers()

    assert dispatched == 2
    assert [task.task_id for task in pool.workers["worker-1"].assigned_tasks] == ["task-1"]
    assert [task.task_id for task in pool.workers["worker-2"].assigned_tasks] == ["task-2"]


def test_scale_down_skips_worker_with_reserved_assignment(tmp_path):
    pool = _build_pool(tmp_path, worker_count=4)
    pool.workers = {
        "worker-1": _WorkerStub("worker-1", "ready"),
        "worker-2": _WorkerStub("worker-2", "ready", has_pending_assignment=True),
    }

    assert pool._pick_idle_worker_for_scale_down() == "worker-1"


def test_collect_resource_snapshot_uses_nonblocking_cpu_sampling(tmp_path, monkeypatch):
    pool = _build_pool(tmp_path, worker_count=4)
    cpu_calls = []

    class _VirtualMemoryStub:
        available = 5 * (1024 ** 3)
        percent = 43.0

    def _cpu_percent(*, interval=None):
        cpu_calls.append(interval)
        return 41.0

    monkeypatch.setattr("src.workers.persistent_pool.psutil.virtual_memory", lambda: _VirtualMemoryStub())
    monkeypatch.setattr("src.workers.persistent_pool.psutil.cpu_percent", _cpu_percent)

    snapshot = pool._collect_resource_snapshot()

    assert snapshot["cpu_percent"] == 41.0
    assert snapshot["memory_percent"] == 43.0
    assert cpu_calls == [None]


def test_dispatch_loop_does_not_attempt_scaling(tmp_path, monkeypatch):
    pool = _build_pool(tmp_path, worker_count=4)
    pool._running = True
    dispatch_calls = []
    scale_calls = []

    def _dispatch():
        dispatch_calls.append("dispatch")
        pool._running = False
        return 0

    async def _scale_up(*args, **kwargs):
        scale_calls.append("scale-up")
        return True

    monkeypatch.setattr(pool, "_dispatch_tasks_to_idle_workers", _dispatch)
    monkeypatch.setattr(pool, "_scale_up_one", _scale_up)

    asyncio.run(pool._process_task_queue())

    assert dispatch_calls == ["dispatch"]
    assert scale_calls == []
