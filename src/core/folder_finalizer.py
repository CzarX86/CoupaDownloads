"""
Asynchronous folder finalization with ACK semantics.

This module centralizes __WORK -> final status renaming and offers a queue-based
finalizer with deterministic fallback for timeout/error scenarios.
"""

from __future__ import annotations

import os
import queue
import re
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict, Optional

import structlog

from ..lib.folder_hierarchy import FolderHierarchyManager

logger = structlog.get_logger(__name__)


@dataclass
class FolderFinalizationResult:
    """Finalization ACK contract shared by caller paths."""

    task_id: str
    po_number: str
    work_folder: str
    status_code: str
    final_folder: str
    success: bool
    error: str = ""
    started_at: float = 0.0
    finished_at: float = 0.0

    @property
    def latency_seconds(self) -> float:
        """Finalization latency in seconds."""
        if self.finished_at <= self.started_at:
            return 0.0
        return self.finished_at - self.started_at


@dataclass
class _QueuedFinalization:
    task_id: str
    po_number: str
    status_code: str
    work_folder: str
    result_ref: Dict[str, Any]
    future: Future[FolderFinalizationResult]
    enqueued_at: float


class FolderFinalizer:
    """Batch finalizer service with background workers and flush/ACK support."""

    def __init__(
        self,
        batch_interval: float = 5.0,
        batch_size: int = 50,
        ack_timeout_seconds: float = 20.0,
        worker_count: int = 1,
        logger_context: str = "default",
    ):
        self.batch_interval = max(0.1, float(batch_interval))
        self.batch_size = max(1, int(batch_size))
        self.ack_timeout_seconds = max(1.0, float(ack_timeout_seconds))
        self.worker_count = max(1, int(worker_count))
        self.logger = logger.bind(finalizer_context=logger_context)

        self._queue: "queue.Queue[_QueuedFinalization]" = queue.Queue()
        self._stop_event = threading.Event()
        self._state_lock = threading.Lock()
        self._idle_cv = threading.Condition(self._state_lock)
        self._pending_count = 0
        self._inflight_count = 0

        self._total_finalized = 0
        self._total_fallback = 0
        self._total_timeout = 0
        self._total_latency_seconds = 0.0

        self._executor = ThreadPoolExecutor(max_workers=self.worker_count)
        self._worker = threading.Thread(
            target=self._run_loop,
            name=f"FolderFinalizer-{logger_context}",
            daemon=True,
        )
        self._worker.start()

    def enqueue(self, task_ref: Any, result_ref: Dict[str, Any]) -> Future[FolderFinalizationResult]:
        """Queue a finalization request and return a future ACK."""
        request = self._build_request(task_ref, result_ref)

        if not self._needs_finalization(request.work_folder):
            future: Future[FolderFinalizationResult] = Future()
            result = FolderFinalizationResult(
                task_id=request.task_id,
                po_number=request.po_number,
                work_folder=request.work_folder,
                status_code=request.status_code,
                final_folder=request.work_folder,
                success=True,
                started_at=time.time(),
                finished_at=time.time(),
            )
            future.set_result(result)
            return future

        with self._state_lock:
            self._pending_count += 1

        self._queue.put(request)
        try:
            self.logger.info(
                "finalization_enqueued",
                task_id=request.task_id,
                po_number=request.po_number,
                work_folder=request.work_folder,
                status_code=request.status_code,
            )
        except Exception:
            pass
        return request.future

    def finalize_now(
        self,
        task_ref: Any,
        result_ref: Dict[str, Any],
        reason: str = "fallback",
    ) -> FolderFinalizationResult:
        """Run deterministic inline finalization as a fallback path."""
        request = self._build_request(task_ref, result_ref)
        with self._state_lock:
            self._total_fallback += 1
        try:
            self.logger.warning(
                "finalization_fallback",
                reason=reason,
                task_id=request.task_id,
                po_number=request.po_number,
                work_folder=request.work_folder,
                status_code=request.status_code,
            )
        except Exception:
            pass
        return self._execute_request(request)

    def flush(self, timeout: Optional[float] = None) -> bool:
        """Wait until queue and in-flight work are fully drained."""
        deadline = None if timeout is None else (time.time() + max(0.0, timeout))

        with self._idle_cv:
            while (self._pending_count + self._inflight_count) > 0:
                if deadline is not None:
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        return False
                    self._idle_cv.wait(timeout=min(0.2, remaining))
                else:
                    self._idle_cv.wait(timeout=0.2)
        return True

    def pending_count(self) -> int:
        """Current pending + in-flight finalization count."""
        with self._state_lock:
            return self._pending_count + self._inflight_count

    def mark_timeout(self, amount: int = 1) -> None:
        """Increment timeout counter for observability."""
        if amount <= 0:
            return
        with self._state_lock:
            self._total_timeout += amount

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate finalization metrics."""
        with self._state_lock:
            finalized = self._total_finalized
            avg_latency = (self._total_latency_seconds / finalized) if finalized else 0.0
            return {
                "pending": self._pending_count,
                "inflight": self._inflight_count,
                "total_finalized": finalized,
                "total_fallback": self._total_fallback,
                "total_timeout": self._total_timeout,
                "average_latency_seconds": avg_latency,
            }

    def shutdown(self, flush: bool = True, timeout: Optional[float] = None) -> None:
        """Stop background workers and release resources."""
        if flush:
            self.flush(timeout=timeout or self.ack_timeout_seconds)

        self._stop_event.set()
        # Join with a generous timeout so the run loop finishes its current batch
        # before we shut down the executor it depends on.
        self._worker.join(timeout=max(5.0, self.batch_interval * 4))
        # Executor shutdown happens after the thread is done (or timed out) so
        # _run_loop never races with executor teardown.
        self._executor.shutdown(wait=False)

        while True:
            try:
                orphan = self._queue.get_nowait()
            except queue.Empty:
                break
            if not orphan.future.done():
                orphan.future.set_exception(RuntimeError("Folder finalizer shutdown before processing item"))
            with self._state_lock:
                self._pending_count = max(0, self._pending_count - 1)
                self._idle_cv.notify_all()

    def _run_loop(self) -> None:
        """Batch worker loop."""
        while not self._stop_event.is_set() or self.pending_count() > 0:
            batch = self._collect_batch()
            if not batch:
                continue

            with self._state_lock:
                self._pending_count = max(0, self._pending_count - len(batch))
                self._inflight_count += len(batch)

            try:
                try:
                    futures = {
                        self._executor.submit(self._execute_request, item): item
                        for item in batch
                    }
                except RuntimeError:
                    # Executor already shut down (e.g. Ctrl+C during shutdown race).
                    # Cancel all items in this batch so their futures don't hang.
                    for item in batch:
                        if not item.future.done():
                            item.future.set_exception(
                                RuntimeError("Folder finalizer executor shut down before processing item")
                            )
                    return

                for done in as_completed(futures):
                    item = futures[done]
                    try:
                        result = done.result()
                    except Exception as err:  # pragma: no cover - defensive
                        result = FolderFinalizationResult(
                            task_id=item.task_id,
                            po_number=item.po_number,
                            work_folder=item.work_folder,
                            status_code=item.status_code,
                            final_folder=item.work_folder,
                            success=False,
                            error=str(err),
                            started_at=time.time(),
                            finished_at=time.time(),
                        )
                    if not item.future.done():
                        item.future.set_result(result)
            finally:
                with self._state_lock:
                    self._inflight_count = max(0, self._inflight_count - len(batch))
                    self._idle_cv.notify_all()

    def _collect_batch(self) -> list[_QueuedFinalization]:
        """Collect up to batch_size finalization requests."""
        try:
            first = self._queue.get(timeout=self.batch_interval)
        except queue.Empty:
            return []

        batch = [first]
        while len(batch) < self.batch_size:
            try:
                batch.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return batch

    def _execute_request(self, item: _QueuedFinalization) -> FolderFinalizationResult:
        """Finalize one folder and produce normalized ACK."""
        started_at = time.time()
        final_folder = item.work_folder
        success = False
        error = ""

        for attempt in range(3):
            try:
                if not item.work_folder:
                    raise ValueError("Missing work folder path")

                if not self._needs_finalization(item.work_folder):
                    final_folder = item.work_folder
                    success = True
                    break

                if os.path.exists(item.work_folder):
                    manager = FolderHierarchyManager()
                    final_folder = manager.finalize_folder(item.work_folder, item.status_code)
                    if self._needs_finalization(final_folder):
                        raise RuntimeError(f"Folder remained in work state after finalization: {final_folder}")
                    success = True
                    break

                inferred = self._infer_finalized_path(item.work_folder, item.status_code)
                if inferred and os.path.exists(inferred):
                    final_folder = inferred
                    success = True
                    break

                raise FileNotFoundError(f"Work folder not found: {item.work_folder}")
            except Exception as exc:
                error = str(exc)
                success = False
                if attempt < 2:
                    time.sleep(0.6)
                    continue

        finished_at = time.time()
        result = FolderFinalizationResult(
            task_id=item.task_id,
            po_number=item.po_number,
            work_folder=item.work_folder,
            status_code=item.status_code,
            final_folder=final_folder,
            success=success,
            error=error,
            started_at=started_at,
            finished_at=finished_at,
        )

        if success:
            item.result_ref["final_folder"] = final_folder

        with self._state_lock:
            if success:
                self._total_finalized += 1
                self._total_latency_seconds += result.latency_seconds

        try:
            self.logger.info(
                "finalization_ack",
                task_id=item.task_id,
                po_number=item.po_number,
                success=success,
                final_folder=final_folder,
                error=error,
                latency_seconds=round(result.latency_seconds, 3),
            )
        except Exception:
            pass
        return result

    def _build_request(self, task_ref: Any, result_ref: Dict[str, Any]) -> _QueuedFinalization:
        """Create a queue item from task/result references."""
        task_ref_id = ""
        task_ref_po = ""
        if isinstance(task_ref, dict):
            task_ref_id = str(task_ref.get("task_id", ""))
            task_ref_po = str(task_ref.get("po_number", ""))
        else:
            task_ref_id = str(getattr(task_ref, "task_id", "") or "")
            task_ref_po = str(getattr(task_ref, "po_number", "") or "")

        task_id = str(
            task_ref_id
            or result_ref.get("task_id")
            or f"finalize-{int(time.time() * 1000)}"
        )
        po_number = str(
            task_ref_po
            or result_ref.get("po_number")
            or result_ref.get("po_number_display")
            or "unknown"
        )
        status_code = str(result_ref.get("status_code") or "FAILED").upper()
        work_folder = str(result_ref.get("final_folder") or result_ref.get("download_folder") or "")

        return _QueuedFinalization(
            task_id=task_id,
            po_number=po_number,
            status_code=status_code,
            work_folder=work_folder,
            result_ref=result_ref,
            future=Future(),
            enqueued_at=time.time(),
        )

    @staticmethod
    def _needs_finalization(path: str) -> bool:
        return bool(path) and str(path).endswith("__WORK")

    @staticmethod
    def _suffix_for_status(status_code: str) -> str:
        status = (status_code or "FAILED").upper().strip()
        return f"_{status}"

    def _infer_finalized_path(self, work_folder: str, status_code: str) -> str:
        """Infer final path if another actor already renamed this folder."""
        base_dir = os.path.dirname(work_folder)
        base_name = os.path.basename(work_folder)
        stripped = re.sub(r"[_]*(?:__WORK)+[_]*$", "", base_name, flags=re.IGNORECASE)
        stripped = re.sub(r"_+", "_", stripped).strip("_")
        if not stripped:
            return ""
        return os.path.join(base_dir, f"{stripped}{self._suffix_for_status(status_code)}")
