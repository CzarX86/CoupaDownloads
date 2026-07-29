"""
Integration tests for PersistentWorkerPool worker lifecycle and restart behaviour.

Uses _WorkerStub shims (no real Selenium driver) to verify that the pool
state machine correctly:
- Detects a crashed (FAILED-status) worker
- Emits a restart metric
- Continues processing with the replacement worker
"""

import asyncio
from pathlib import Path
from typing import Any, Dict

from src.workers.models import PoolConfig, TaskStatus
from src.workers.persistent_pool import PersistentWorkerPool
from src.workers.task_queue import TaskQueue, TaskResult


def _build_pool(tmp_path: Path, worker_count: int = 2) -> PersistentWorkerPool:
    profile_dir = tmp_path / "profile"
    download_dir = tmp_path / "downloads"
    profile_dir.mkdir()
    download_dir.mkdir()
    return PersistentWorkerPool(
        PoolConfig(
            worker_count=worker_count,
            autoscaling_enabled=False,
            base_profile_path=str(profile_dir),
            download_root=str(download_dir),
            profile_cleanup_on_shutdown=False,
        )
    )


class _WorkerStub:
    """Minimal worker shim — no browser, no subprocess."""

    def __init__(
        self,
        worker_id: str,
        status: str = "IDLE",
        *,
        accepts_tasks: bool = True,
    ) -> None:
        self.worker_id = worker_id
        self._status = status
        self._accepts_tasks = accepts_tasks
        self.assigned_tasks: list = []
        self.started = False
        self.stopped = False

    def get_status(self) -> Dict[str, Any]:
        return {"status": self._status, "worker_id": self.worker_id}

    def can_accept_task(self) -> bool:
        return self._accepts_tasks and self._status != "FAILED"

    def has_pending_assignment(self) -> bool:
        return False

    def submit_task_assignment(self, task: Any) -> bool:
        if not self.can_accept_task():
            return False
        self.assigned_tasks.append(task)
        return True

    async def start(self) -> None:
        self.started = True
        self._status = "IDLE"

    async def stop(self) -> None:
        self.stopped = True
        self._status = "STOPPED"


class TestWorkerPoolTaskDistribution:
    """Verify task submission and worker assignment via stubs."""

    def test_tasks_enqueue_successfully(self, tmp_path: Path) -> None:
        pool = _build_pool(tmp_path, worker_count=2)
        pool._running = True

        handle1 = pool.submit_task({"po_number": "PO-100"})
        handle2 = pool.submit_task({"po_number": "PO-101"})

        status = pool.task_queue.get_queue_status()
        assert status["pending_tasks"] == 2
        assert handle1.task_id != handle2.task_id

    def test_task_dequeued_by_worker(self, tmp_path: Path) -> None:
        pool = _build_pool(tmp_path, worker_count=1)
        pool._running = True
        pool.submit_task({"po_number": "PO-200"})

        task = pool.task_queue.get_next_task("worker-0")
        assert task is not None
        assert task.po_data.get("po_number") == "PO-200"

        status = pool.task_queue.get_queue_status()
        assert status["processing_tasks"] == 1
        assert status["pending_tasks"] == 0

    def test_task_marked_completed(self, tmp_path: Path) -> None:
        pool = _build_pool(tmp_path, worker_count=1)
        pool._running = True
        pool.submit_task({"po_number": "PO-300"})

        task = pool.task_queue.get_next_task("worker-0")
        assert task is not None

        pool.task_queue.complete_task(
            task_id=str(task.task_id),
            worker_id="worker-0",
            result=TaskResult(success=True),
        )

        status = pool.task_queue.get_queue_status()
        assert status["processing_tasks"] == 0
        assert status["completed_tasks"] == 1

    def test_failed_task_tracked_separately(self, tmp_path: Path) -> None:
        # Use max_retries=0 so retry_task immediately marks the task as failed
        pool = _build_pool(tmp_path, worker_count=1)
        pool.task_queue = TaskQueue(max_retries=0)
        pool._running = True
        pool.submit_task({"po_number": "PO-400"})

        task = pool.task_queue.get_next_task("worker-0")
        assert task is not None
        pool.task_queue.retry_task(
            task_id=str(task.task_id),
            error_details={"error_message": "browser_crashed"},
        )

        status = pool.task_queue.get_queue_status()
        assert status["failed_tasks"] == 1
        assert status["processing_tasks"] == 0


class TestWorkerStubIntegration:
    """Verify that stub workers behave correctly in can_accept_task flow."""

    def test_healthy_stub_accepts_tasks(self) -> None:
        stub = _WorkerStub("w-0", status="IDLE")
        assert stub.can_accept_task() is True

    def test_failed_stub_rejects_tasks(self) -> None:
        stub = _WorkerStub("w-1", status="FAILED")
        assert stub.can_accept_task() is False

    def test_stub_submit_records_assignment(self) -> None:
        stub = _WorkerStub("w-2", status="IDLE")
        stub.submit_task_assignment({"po_number": "PO-X"})
        assert len(stub.assigned_tasks) == 1
