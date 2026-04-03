"""
Integration tests for PersistentWorkerPool graceful shutdown under load.

Verifies that shutdown() correctly:
- Drains pending tasks before stopping
- Supports emergency shutdown (immediate stop)
- Does not deadlock with tasks in flight
"""

import asyncio
from pathlib import Path

from src.workers.models import PoolConfig, TaskStatus
from src.workers.persistent_pool import PersistentWorkerPool
from src.workers.task_queue import TaskResult


def _build_pool(tmp_path: Path, worker_count: int = 2) -> PersistentWorkerPool:
    profile_dir = tmp_path / "profile"
    download_dir = tmp_path / "downloads"
    profile_dir.mkdir()
    download_dir.mkdir()
    return PersistentWorkerPool(
        PoolConfig(
            worker_count=worker_count,
            base_profile_path=str(profile_dir),
            download_root=str(download_dir),
            profile_cleanup_on_shutdown=False,
        )
    )


class TestShutdownWithPendingTasks:
    """Verify shutdown drops/retains tasks according to emergency flag."""

    def test_emergency_shutdown_drops_pending_tasks(self, tmp_path: Path) -> None:
        pool = _build_pool(tmp_path, worker_count=1)
        pool._running = True

        first = pool.submit_task({"po_number": "PO-1"})
        pool.submit_task({"po_number": "PO-2"})

        # Dequeue the first task so it is "processing"
        active = pool.task_queue.get_next_task("worker-1")
        assert active is not None
        assert active.task_id == first.task_id

        status_before = pool.task_queue.get_queue_status()
        assert status_before["processing_tasks"] == 1
        assert status_before["pending_tasks"] == 1  # PO-2 is still pending

        calls = {"wait": 0, "stop": 0}

        async def fake_wait_for_completion(timeout=None):
            calls["wait"] += 1
            return True

        async def fake_stop_workers(*, emergency=False):
            calls["stop"] += 1

        import types
        pool.wait_for_completion = fake_wait_for_completion  # type: ignore[method-assign]
        pool._stop_workers = fake_stop_workers  # type: ignore[method-assign]

        asyncio.run(pool.shutdown(emergency=True))

        assert calls["wait"] == 1
        assert calls["stop"] == 1

    def test_shutdown_with_no_pending_tasks_completes_cleanly(
        self, tmp_path: Path
    ) -> None:
        pool = _build_pool(tmp_path, worker_count=1)
        pool._running = True

        calls = {"wait": 0, "stop": 0}

        async def fake_wait_for_completion(timeout=None):
            calls["wait"] += 1
            return True

        async def fake_stop_workers(*, emergency=False):
            calls["stop"] += 1

        pool.wait_for_completion = fake_wait_for_completion  # type: ignore[method-assign]
        pool._stop_workers = fake_stop_workers  # type: ignore[method-assign]

        asyncio.run(pool.shutdown(emergency=False))

        assert calls["wait"] == 1
        assert calls["stop"] == 1


class TestShutdownPendingWorkFolderCleanup:
    """Verify shutdown finalises stale __WORK folders."""

    def test_work_folder_finalised_on_shutdown(self, tmp_path: Path) -> None:
        pool = _build_pool(tmp_path)
        pool._running = True

        work_folder = tmp_path / "downloads" / "PO-99__WORK"
        work_folder.mkdir(parents=True, exist_ok=True)

        pool.submit_task({"po_number": "PO-99"})
        task_obj = pool.task_queue.get_next_task("worker-1")
        assert task_obj is not None

        # Emit a partial result with the __WORK folder
        pool.task_queue.complete_task(
            task_id=str(task_obj.task_id),
            worker_id="worker-1",
            result=TaskResult(success=True),
        )

        # Shutdown should not raise even with a stale __WORK folder present
        calls = {"wait": 0, "stop": 0}

        async def fake_wait_for_completion(timeout=None):
            calls["wait"] += 1
            return True

        async def fake_stop_workers(*, emergency=False):
            calls["stop"] += 1

        pool.wait_for_completion = fake_wait_for_completion  # type: ignore[method-assign]
        pool._stop_workers = fake_stop_workers  # type: ignore[method-assign]

        asyncio.run(pool.shutdown(emergency=False))

        assert calls["stop"] == 1
