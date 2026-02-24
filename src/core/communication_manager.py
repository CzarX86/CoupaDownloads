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
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MetricMessage:
    """Structure for metric messages sent between processes."""
    worker_id: int
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
        self.metric_queue: Any = self._manager.Queue() if self._manager else mp.Queue()
        self._metrics_buffer: List[Dict[str, Any]] = []
        self._metrics_lock: threading.Lock = threading.Lock()
        self._max_buffer_size: int = 500
        self.finalization_queue: Any = self._manager.Queue() if self._manager else mp.Queue()

        # Persistent state tracking
        self._pos_successful: Set[str] = set()
        self._pos_failed: Set[str] = set()
        self._pos_processing: Set[str] = set()  # Currently active POs
        self._worker_states: Dict[int, Dict[str, Any]] = {}       # Latest state per worker
        self._total_pos_seen: Set[str] = set()   # All PO IDs encountered

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
        
    def send_metric(self, metric_dict: Dict[str, Any]) -> None:
        """
        Send a metric message to the shared queue.

        Args:
            metric_dict: Dictionary containing metric information
        """
        try:
            metric_message = MetricMessage(**metric_dict)
            self.metric_queue.put(metric_message)
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
            else:
                metrics.append(metric)

        if metrics:
            with self._metrics_lock:
                # 1. Update persistent state
                for m in metrics:
                    po_id = m.get('po_id')
                    status = m.get('status', '').upper()
                    worker_id = m.get('worker_id')

                    if po_id:
                        self._total_pos_seen.add(po_id)

                        # Handle status transitions
                        if status in {'COMPLETED', 'NO_ATTACHMENTS', 'PARTIAL', 'SUCCESS'}:
                            self._pos_successful.add(po_id)
                            self._pos_failed.discard(po_id)
                            self._pos_processing.discard(po_id)
                        elif status in {'FAILED', 'ERROR'}:
                            self._pos_failed.add(po_id)
                            self._pos_successful.discard(po_id)
                            self._pos_processing.discard(po_id)
                        else:
                            # Processing or other transient state (STARTED, PROCESSING, etc.)
                            self._pos_processing.add(po_id)

                    if worker_id is not None:
                        # Update worker state with full metric data
                        self._worker_states[worker_id] = m
                        logger.debug("Worker state updated", extra={
                            "worker_id": worker_id,
                            "po_id": po_id,
                            "status": status
                        })

                # 2. Add to log/recent buffer - keep more history for UI
                self._metrics_buffer.extend(metrics)
                buffer_limit = max(self._max_buffer_size, 200)  # Increased for better UI history
                if len(self._metrics_buffer) > buffer_limit:
                    self._metrics_buffer = self._metrics_buffer[-buffer_limit:]

                logger.debug("Metrics buffer updated", extra={
                    "new_metrics": len(metrics),
                    "buffer_size": len(self._metrics_buffer)
                })

        return metrics
        
    def get_aggregated_metrics(self) -> Dict[str, Any]:
        """
        Get aggregated metrics for UI display based on persistent state.
        
        Returns:
            Dictionary with aggregated metrics
        """
        self._drain_queue()

        with self._metrics_lock:
            return {
                'total_processed': len(self._pos_successful) + len(self._pos_failed),
                'total_successful': len(self._pos_successful),
                'total_failed': len(self._pos_failed),
                'total_seen': len(self._total_pos_seen),
                'active_count': len(self._pos_processing),
                'workers_status': dict(self._worker_states),
                'recent_metrics': list(self._metrics_buffer[-10:])
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
