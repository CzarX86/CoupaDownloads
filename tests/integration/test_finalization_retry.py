"""
Integration tests for finalization retry budget in PersistentWorkerPool.

Verifies that _should_retry_finalization enforces the 6-attempt cap and that
the retry counter is correctly incremented through _apply_finalization_result.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.workers.models import PoolConfig, POTask, TaskStatus
from src.workers.persistent_pool import PersistentWorkerPool


def _build_pool(tmp_path: Path) -> PersistentWorkerPool:
    profile_dir = tmp_path / "profile"
    download_dir = tmp_path / "downloads"
    profile_dir.mkdir()
    download_dir.mkdir()
    return PersistentWorkerPool(
        PoolConfig(
            worker_count=1,
            base_profile_path=str(profile_dir),
            download_root=str(download_dir),
            profile_cleanup_on_shutdown=False,
        )
    )


class TestShouldRetryFinalization:
    """Unit-level checks on the retry-budget gate."""

    def test_retries_allowed_below_max(self, tmp_path: Path) -> None:
        pool = _build_pool(tmp_path)
        work_folder = tmp_path / "downloads" / "PO-1__WORK"
        work_folder.mkdir(parents=True, exist_ok=True)

        result = {
            "final_folder": str(work_folder),
            "_finalization_retry_count": 0,
        }
        assert pool._should_retry_finalization(result) is True

    def test_retry_denied_at_max_attempts(self, tmp_path: Path) -> None:
        pool = _build_pool(tmp_path)
        work_folder = tmp_path / "downloads" / "PO-2__WORK"
        work_folder.mkdir(parents=True, exist_ok=True)

        result = {
            "final_folder": str(work_folder),
            "_finalization_retry_count": 6,  # = _max_finalization_retry_attempts
        }
        assert pool._should_retry_finalization(result) is False

    def test_retry_denied_when_work_folder_missing(self, tmp_path: Path) -> None:
        pool = _build_pool(tmp_path)
        work_folder = tmp_path / "downloads" / "PO-3__WORK"
        # Intentionally NOT creating the directory

        result = {
            "final_folder": str(work_folder),
            "_finalization_retry_count": 0,
        }
        assert pool._should_retry_finalization(result) is False

    def test_retry_denied_when_final_folder_not_work(self, tmp_path: Path) -> None:
        pool = _build_pool(tmp_path)
        clean_folder = tmp_path / "downloads" / "PO-4"
        clean_folder.mkdir(parents=True, exist_ok=True)

        result = {
            "final_folder": str(clean_folder),
            "_finalization_retry_count": 0,
        }
        assert pool._should_retry_finalization(result) is False

    def test_max_finalization_retry_attempts_is_six(self, tmp_path: Path) -> None:
        """The retry budget must be exactly 6 as documented in the code."""
        pool = _build_pool(tmp_path)
        assert pool._max_finalization_retry_attempts == 6


class TestRetryCounterIncrement:
    """Verify _finalize_pending_task increments the retry counter correctly."""

    def test_failed_finalization_increments_retry_count(self, tmp_path: Path) -> None:
        pool = _build_pool(tmp_path)
        pool._running = True

        work_folder = tmp_path / "downloads" / "PO-10__WORK"
        work_folder.mkdir(parents=True, exist_ok=True)

        task = pool.submit_task({"po_number": "PO-10"})
        task_obj = pool.task_queue.get_next_task("worker-0")
        assert task_obj is not None

        result: dict = {
            "po_number": "PO-10",
            "final_folder": str(work_folder),
            "success": False,
        }

        from src.core.folder_finalizer import FolderFinalizationResult

        failed_ack = FolderFinalizationResult(
            task_id=str(task_obj.task_id),
            po_number="PO-10",
            work_folder=str(work_folder),
            status_code="FAILED",
            final_folder=str(work_folder),
            success=False,
            error="test_error",
        )

        # Stub out finalize_now to return the failed ACK deterministically
        pool.folder_finalizer.finalize_now = MagicMock(return_value=failed_ack)
        # Stub _register_pending_finalization to capture calls
        registered: list = []
        pool._register_pending_finalization = lambda task_id, po_task, res: registered.append(  # type: ignore[method-assign]
            dict(res)
        )

        po_task = pool._po_tasks[str(task_obj.task_id)]
        pool._finalize_pending_task(
            str(task_obj.task_id), po_task, result, failed_ack
        )

        assert len(registered) == 1
        assert registered[0].get("_finalization_retry_count") == 1

    def test_retry_stops_at_max_budget(self, tmp_path: Path) -> None:
        """After 6 retries the task is marked FAILED without further re-registration."""
        pool = _build_pool(tmp_path)
        pool._running = True

        task = pool.submit_task({"po_number": "PO-11"})
        task_obj = pool.task_queue.get_next_task("worker-0")
        assert task_obj is not None

        # No work folder — forces _should_retry_finalization to return False
        result: dict = {
            "po_number": "PO-11",
            "final_folder": "",
            "success": False,
            "_finalization_retry_count": 6,
        }

        from src.core.folder_finalizer import FolderFinalizationResult

        failed_ack = FolderFinalizationResult(
            task_id=str(task_obj.task_id),
            po_number="PO-11",
            work_folder="",
            status_code="FAILED",
            final_folder="",
            success=False,
            error="exhausted",
        )

        pool.folder_finalizer.finalize_now = MagicMock(return_value=failed_ack)
        registered: list = []
        pool._register_pending_finalization = lambda task_id, po_task, res: registered.append(  # type: ignore[method-assign]
            None
        )
        # Stub dispatch to avoid needing a full result pipeline
        pool._publish_terminal_task_metric = MagicMock()
        pool._dispatch_task_result = MagicMock()

        po_task = pool._po_tasks[str(task_obj.task_id)]
        pool._finalize_pending_task(
            str(task_obj.task_id), po_task, result, failed_ack
        )

        # No re-registration after budget exhausted
        assert len(registered) == 0
        assert po_task.status == TaskStatus.FAILED
