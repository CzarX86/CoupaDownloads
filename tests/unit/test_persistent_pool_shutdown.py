import asyncio
from pathlib import Path

from src.workers.models import POTask, PoolConfig, TaskPriority, TaskStatus
from src.workers.persistent_pool import PersistentWorkerPool


def _build_pool(tmp_path: Path) -> PersistentWorkerPool:
    profile_dir = tmp_path / "profile"
    download_dir = tmp_path / "downloads"
    profile_dir.mkdir()
    download_dir.mkdir()

    config = PoolConfig(
        worker_count=1,
        base_profile_path=str(profile_dir),
        download_root=str(download_dir),
        profile_cleanup_on_shutdown=False,
    )
    return PersistentWorkerPool(config)


def test_shutdown_drops_not_started_tasks_but_keeps_active_task(tmp_path, monkeypatch):
    pool = _build_pool(tmp_path)
    pool._running = True

    first = pool.submit_task({"po_number": "PO-1"})
    pool.submit_task({"po_number": "PO-2"})

    active_task = pool.task_queue.get_next_task("worker-1")
    assert active_task is not None
    assert active_task.task_id == first.task_id

    calls = {"wait": 0, "stop_workers": 0}

    async def fake_wait_for_completion(timeout=None):
        calls["wait"] += 1
        stats = pool.task_queue.get_queue_status()
        assert stats["processing_tasks"] == 1
        assert stats["pending_tasks"] == 0
        return True

    async def fake_stop_workers(*, emergency=False):
        calls["stop_workers"] += 1
        assert emergency is False

    monkeypatch.setattr(pool, "wait_for_completion", fake_wait_for_completion)
    monkeypatch.setattr(pool, "_stop_workers", fake_stop_workers)

    asyncio.run(pool.shutdown(emergency=True))

    assert calls == {"wait": 1, "stop_workers": 1}


def test_shutdown_finishes_pending_work_finalization(tmp_path):
    pool = _build_pool(tmp_path)
    pool._running = True

    work_folder = tmp_path / "downloads" / "PO-9__WORK"
    work_folder.mkdir(parents=True, exist_ok=True)
    (work_folder / "file.txt").write_text("content", encoding="utf-8")

    po_task = POTask(po_number="PO-9", priority=TaskPriority.NORMAL)
    po_task.task_id = "task-po-9"
    po_task.status = TaskStatus.READY_TO_FINALIZE
    result = {
        "po_number": "PO-9",
        "status_code": "COMPLETED",
        "success": True,
        "final_folder": str(work_folder),
    }

    pool._po_tasks[po_task.task_id] = po_task
    pool._register_pending_finalization(po_task.task_id, po_task, result)

    asyncio.run(pool.shutdown(emergency=True))

    assert pool._pending_finalization_count() == 0
    assert result["final_folder"].endswith("_COMPLETED")
    assert "__WORK" not in result["final_folder"]
    assert Path(result["final_folder"]).is_dir()
    assert not work_folder.exists()
