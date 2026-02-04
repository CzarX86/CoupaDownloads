"""
Communication Manager for inter-process communication.

Manages communication between processes to share metrics and progress updates
for UI display in parallel processing scenarios.
"""

import multiprocessing as mp
import queue
import threading
from typing import Dict, List, Any
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
    """
    
    def __init__(self, use_manager: bool = True):
        """Initialize the communication manager with a shared queue."""
        self._manager = mp.Manager() if use_manager else None
        self.metric_queue = self._manager.Queue() if self._manager else mp.Queue()
        self._metrics_buffer: List[Dict[str, Any]] = []
        self._metrics_lock = threading.Lock()
        self._max_buffer_size = 1000

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
            print(f"Error sending metric: {e}")
            
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

        while True:
            try:
                metric = self.metric_queue.get_nowait()
            except queue.Empty:
                break
            except Exception as e:
                print(f"Error receiving metric: {e}")
                break

            if isinstance(metric, MetricMessage):
                metrics.append(asdict(metric))
            else:
                metrics.append(metric)

        if metrics:
            with self._metrics_lock:
                self._metrics_buffer.extend(metrics)
                if self._max_buffer_size and len(self._metrics_buffer) > self._max_buffer_size:
                    self._metrics_buffer = self._metrics_buffer[-self._max_buffer_size:]

        return metrics
        
    def get_aggregated_metrics(self) -> Dict[str, Any]:
        """
        Get aggregated metrics for UI display.
        
        Returns:
            Dictionary with aggregated metrics
        """
        self._drain_queue()

        with self._metrics_lock:
            all_metrics = list(self._metrics_buffer)

        if not all_metrics:
            return {
                'total_processed': 0,
                'total_successful': 0,
                'total_failed': 0,
                'workers_status': {},
                'recent_metrics': []
            }
            
        # Aggregate metrics by latest PO status
        latest_by_po: Dict[str, Dict[str, Any]] = {}
        for metric in all_metrics:
            po_id = metric.get('po_id')
            if not po_id:
                continue
            latest_by_po[po_id] = metric

        total_processed = len(latest_by_po)
        total_successful = sum(
            1
            for m in latest_by_po.values()
            if m.get('status') in {'COMPLETED', 'NO_ATTACHMENTS', 'PARTIAL'}
        )
        total_failed = sum(
            1 for m in latest_by_po.values() if m.get('status') == 'FAILED'
        )
        
        # Group by worker
        workers_status = {}
        for metric in all_metrics:
            worker_id = metric.get('worker_id', 0)
            if worker_id not in workers_status:
                workers_status[worker_id] = []
            workers_status[worker_id].append(metric)
            
        return {
            'total_processed': total_processed,
            'total_successful': total_successful,
            'total_failed': total_failed,
            'workers_status': workers_status,
            'recent_metrics': all_metrics[-10:]  # Last 10 metrics
        }
