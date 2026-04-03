"""
Communication Manager for inter-process communication.

Manages communication between processes to share metrics and progress updates
for UI display in parallel processing scenarios.
"""

from __future__ import annotations

import multiprocessing as mp
import queue
import threading
import logging
import time
from collections import deque
from dataclasses import dataclass, asdict
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

from .eta import ETAEstimator, is_terminal_status

logger = logging.getLogger(__name__)

TERMINAL_RUN_STATES = {"completed", "failed", "interrupted"}


@dataclass
class MetricMessage:
    """Structure for metric messages sent between processes."""
    worker_id: Any
    po_id: str
    status: str
    timestamp: float
    duration: float = 0.0
    attachments_found: int = 0
    attachments_downloaded: int = 0
    message: str = ""


class CommunicationManager:
    """
    Manages communication inter-processes for metrics and progress updates.

    Uses multiprocessing.Queue for thread-safe communication between processes.
    Enhanced with persistent state tracking to prevent data loss.
    """

    def __init__(self, use_manager: bool = True) -> None:
        """Initialize the communication manager with a shared queue."""
        self._manager: Optional[mp.managers.SyncManager] = mp.Manager() if use_manager else None
        self.metric_queue: Any = self._manager.Queue() if self._manager else queue.Queue()
        self._metrics_lock: threading.Lock = threading.Lock()
        self._max_buffer_size: int = 500
        self._metrics_buffer: Deque[Dict[str, Any]] = deque(maxlen=self._max_buffer_size)
        self.finalization_queue: Any = self._manager.Queue() if self._manager else queue.Queue()

        # Persistent state tracking
        self._pos_successful: Set[str] = set()
        self._pos_failed: Set[str] = set()
        self._pos_processing: Set[str] = set()  # Currently active POs
        self._worker_states: Dict[Any, Dict[str, Any]] = {}       # Latest state per worker
        self._total_pos_seen: Set[str] = set()   # All PO IDs encountered
        self._po_statuses: Dict[str, str] = {}
        self._eta_estimator = ETAEstimator()
        self._run_state: str = "idle"
        self._run_started_at: Optional[float] = None
        self._run_finished_at: Optional[float] = None
        self._run_summary: Dict[str, Any] = {}
        self._resource_metrics: Dict[str, Any] = {}

    def __getstate__(self) -> Dict[str, Any]:
        """Ensure the manager remains picklable for multiprocessing."""
        state = self.__dict__.copy()
        # Locks are not picklable; recreate after unpickling.
        state['_metrics_lock'] = None
        # Managers are not picklable; keep the proxy queue only.
        state['_manager'] = None
        return state

    def __setstate__(self, state: Dict[str, Any]) -> None:
        self.__dict__.update(state)
        if self.__dict__.get('_metrics_lock') is None:
            self._metrics_lock = threading.Lock()

    @staticmethod
    def _is_worker_state_candidate(worker_id: Any) -> bool:
        """Return True only for real worker identifiers used in the worker grid."""
        if worker_id is None:
            return False
        if isinstance(worker_id, int):
            return worker_id >= 0
        if isinstance(worker_id, str):
            try:
                return int(worker_id) >= 0
            except (TypeError, ValueError):
                return not worker_id.startswith("-")
        return True

    @staticmethod
    def _is_trackable_po(po_id: Any) -> bool:
        """Ignore synthetic/system messages in throughput and ETA accounting."""
        if po_id is None:
            return False
        normalized = str(po_id).strip().upper()
        return normalized not in {"", "SYSTEM", "PROGRESS_UPDATE"}

    @staticmethod
    def _worker_state_signature(metric: Dict[str, Any]) -> tuple[Any, ...]:
        """Build a signature used to coalesce repeated worker snapshots."""
        return (
            metric.get("po_id"),
            metric.get("status"),
            metric.get("attachments_found", 0),
            metric.get("attachments_downloaded", 0),
            metric.get("message", ""),
        )

    def configure_total_pos(self, total_pos: int) -> None:
        """Set the expected total PO count used by ETA estimation."""
        with self._metrics_lock:
            self._eta_estimator.configure_total_items(total_pos)

    def set_run_state(self, state: str, *, summary: Optional[Dict[str, Any]] = None, timestamp: Optional[float] = None) -> None:
        """Publish the lifecycle state of the current processing run."""
        ts = float(timestamp if timestamp is not None else time.time())
        normalized_state = str(state or "idle").strip().lower()

        with self._metrics_lock:
            self._run_state = normalized_state
            if normalized_state == "running" and self._run_started_at is None:
                self._run_started_at = ts
            if normalized_state in TERMINAL_RUN_STATES:
                self._run_finished_at = ts
            if summary is not None:
                self._run_summary = dict(summary)

    def get_run_state(self) -> Dict[str, Any]:
        """Return a snapshot of the processing run lifecycle state."""
        with self._metrics_lock:
            return {
                "state": self._run_state,
                "started_at": self._run_started_at,
                "finished_at": self._run_finished_at,
                "summary": dict(self._run_summary),
            }
        
    def send_metric(self, metric_dict: Dict[str, Any]) -> None:
        """
        Send a metric message to the shared queue.

        Args:
            metric_dict: Dictionary containing metric information
        """
        try:
            self.metric_queue.put(dict(metric_dict))
        except Exception as e:
            # Log exception with context instead of silently swallowing
            logger.warning(
                "Failed to send metric",
                extra={
                    "error": str(e),
                    "metric": metric_dict,
                    "worker_id": metric_dict.get("worker_id"),
                    "po_id": metric_dict.get("po_id"),
                }
            )

    def publish_activity(
        self,
        message: str,
        *,
        status: str = "INFO",
        worker_id: int = -1,
        po_id: str = "SYSTEM",
        timestamp: Optional[float] = None,
        **extra: Any,
    ) -> None:
        """Publish a system activity entry so the UI can show non-worker progress."""
        activity: Dict[str, Any] = {
            "worker_id": worker_id,
            "po_id": po_id,
            "status": status,
            "timestamp": float(timestamp if timestamp is not None else time.time()),
            "message": str(message),
            "attachments_found": 0,
            "attachments_downloaded": 0,
        }
        if extra:
            activity.update(extra)
        self.send_metric(activity)
            
    def get_metrics(self) -> List[Dict[str, Any]]:
        """
        Consume all available metrics from the queue.
        
        Returns:
            List of metric dictionaries
        """
        return self._drain_queue()

    def _drain_queue(self) -> List[Dict[str, Any]]:
        """Drain available metrics into the buffer and return new items."""
        metrics: List[Dict[str, Any]] = []

        count = 0
        while count < 100:  # Throttle to avoid freezing UI
            try:
                metric = self.metric_queue.get_nowait()
                count += 1
            except queue.Empty:
                break
            except Exception as e:
                # Log unexpected queue errors
                logger.warning("Unexpected error draining metric queue", extra={"error": str(e)})
                break

            if isinstance(metric, MetricMessage):
                metrics.append(asdict(metric))
            elif isinstance(metric, dict):
                metrics.append(metric)
            else:
                metrics.append(dict(metric) if hasattr(metric, '__iter__') else {'raw': metric})

        if metrics:
            with self._metrics_lock:
                buffer_updates: List[Dict[str, Any]] = []
                # 1. Update persistent state
                for m in metrics:
                    po_id = m.get('po_id')
                    status = m.get('status', '').upper()
                    worker_id = m.get('worker_id')
                    timestamp = float(m.get('timestamp', time.time()))
                    resource_snapshot = m.get('resource_snapshot')
                    is_resource_snapshot = isinstance(resource_snapshot, dict)
                    should_track_po = self._is_trackable_po(po_id)

                    if is_resource_snapshot:
                        self._resource_metrics = dict(resource_snapshot)

                    self._eta_estimator.set_start_time_if_missing(timestamp)

                    if should_track_po:
                        normalized_po_id = str(po_id)
                        self._total_pos_seen.add(normalized_po_id)
                        previous_status = self._po_statuses.get(normalized_po_id, "")
                        if is_terminal_status(previous_status) and not is_terminal_status(status):
                            continue
                        self._po_statuses[normalized_po_id] = status

                        # Handle status transitions
                        if status in {'COMPLETED', 'NO_ATTACHMENTS', 'PARTIAL', 'SUCCESS'}:
                            self._pos_successful.add(normalized_po_id)
                            self._pos_failed.discard(normalized_po_id)
                            self._pos_processing.discard(normalized_po_id)
                        elif status in {'FAILED', 'ERROR', 'TIMEOUT'}:
                            # TIMEOUT here means permanently failed (retries exhausted).
                            # Transient timeouts are published as RETRYING, not TIMEOUT.
                            self._pos_failed.add(normalized_po_id)
                            self._pos_successful.discard(normalized_po_id)
                            self._pos_processing.discard(normalized_po_id)
                        elif status in {'RETRYING', 'PENDING', 'QUEUED'}:
                            self._pos_processing.discard(normalized_po_id)
                        else:
                            # Processing or other transient state (STARTED, PROCESSING, etc.)
                            self._pos_processing.add(normalized_po_id)

                        if is_terminal_status(status) and not is_terminal_status(previous_status):
                            self._eta_estimator.record_completion(timestamp)

                    should_buffer_metric = not is_resource_snapshot
                    if self._is_worker_state_candidate(worker_id):
                        previous_worker_state = self._worker_states.get(worker_id)
                        is_duplicate_worker_state = (
                            previous_worker_state is not None
                            and self._worker_state_signature(previous_worker_state) == self._worker_state_signature(m)
                        )
                        self._worker_states[worker_id] = m
                        should_buffer_metric = should_buffer_metric and not is_duplicate_worker_state
                    elif worker_id is not None:
                        should_buffer_metric = should_buffer_metric

                    if should_buffer_metric:
                        buffer_updates.append(m)

                # 2. Add to bounded recent history for UI activity feed
                self._metrics_buffer.extend(buffer_updates)

        return metrics
        
    def get_aggregated_metrics(self) -> Dict[str, Any]:
        """
        Get aggregated metrics for UI display based on persistent state.
        
        Returns:
            Dictionary with aggregated metrics
        """
        self._drain_queue()

        with self._metrics_lock:
            total_processed = len(self._pos_successful) + len(self._pos_failed)
            eta_state = self._eta_estimator.build_state(
                processed_items=total_processed,
                active_items=len(self._pos_processing),
                now=time.time(),
            )
            return {
                'total_processed': total_processed,
                'total_successful': len(self._pos_successful),
                'total_failed': len(self._pos_failed),
                'total_seen': len(self._total_pos_seen),
                'active_count': len(self._pos_processing),
                'workers_status': dict(self._worker_states),
                'recent_metrics': list(self._metrics_buffer)[-10:],
                'throughput': {
                    'dynamic_rate_per_minute': eta_state.dynamic_rate_per_minute,
                    'stability_score': eta_state.stability_score,
                    'confidence_state': eta_state.confidence_state,
                },
                'eta': {
                    'seconds': eta_state.eta_seconds,
                    'display': eta_state.eta_display,
                    'stability_score': eta_state.stability_score,
                    'confidence_state': eta_state.confidence_state,
                },
                'resources': dict(self._resource_metrics),
                'run': {
                    'state': self._run_state,
                    'started_at': self._run_started_at,
                    'finished_at': self._run_finished_at,
                    'summary': dict(self._run_summary),
                },
            }
    def signal_finalization(self, folder_path: str, status_code: str) -> None:
        """Signal that a folder is ready for finalization."""
        try:
            self.finalization_queue.put((folder_path, status_code))
        except Exception as e:
            logger.warning(
                "Failed to signal folder finalization",
                extra={
                    "error": str(e),
                    "folder_path": folder_path,
                    "status_code": status_code,
                }
            )

    def get_finalization_tasks(self) -> List[Tuple[str, str]]:
        """Get all pending finalization tasks."""
        tasks = []
        while True:
            try:
                tasks.append(self.finalization_queue.get_nowait())
            except (queue.Empty, Exception):
                break
        return tasks
