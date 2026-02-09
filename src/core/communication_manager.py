"""
Communication Manager for inter-process communication.

Manages communication between processes to share metrics and progress updates
for UI display in parallel processing scenarios.
"""

import multiprocessing as mp
import queue
import threading
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime


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
    
    def __init__(self, use_manager: bool = True):
        """Initialize the communication manager with a shared queue."""
        self._manager = mp.Manager() if use_manager else None
        self.metric_queue = self._manager.Queue() if self._manager else mp.Queue()
        self._metrics_buffer: List[Dict[str, Any]] = []
        self._metrics_lock = threading.Lock()
        self._max_buffer_size = 500
        self.finalization_queue = self._manager.Queue() if self._manager else mp.Queue()
        
        # Persistent state tracking
        self._pos_successful = set()
        self._pos_failed = set()
        self._pos_processing = set()  # Currently active POs
        self._worker_states = {}       # Latest state per worker
        self._total_pos_seen = set()   # All PO IDs encountered

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
            # Avoid frequent printing in workers
            pass
            
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
            except Exception:
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
                            # Processing or other transient state
                            self._pos_processing.add(po_id)

                    if worker_id is not None:
                        # Update worker state
                        self._worker_states[worker_id] = m

                # 2. Add to log/recent buffer
                self._metrics_buffer.extend(metrics)
                if self._max_buffer_size and len(self._metrics_buffer) > self._max_buffer_size:
                    self._metrics_buffer = self._metrics_buffer[-self._max_buffer_size:]

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
        except Exception:
            pass

    def get_finalization_tasks(self) -> List[Tuple[str, str]]:
        """Get all pending finalization tasks."""
        tasks = []
        while True:
            try:
                tasks.append(self.finalization_queue.get_nowait())
            except (queue.Empty, Exception):
                break
        return tasks
