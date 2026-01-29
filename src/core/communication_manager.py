"""
Communication Manager for inter-process communication.

Manages communication between processes to share metrics and progress updates
for UI display in parallel processing scenarios.
"""

import multiprocessing as mp
from typing import Dict, List, Any, Optional
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
    
    def __init__(self):
        """Initialize the communication manager with a shared queue."""
        self.metric_queue = mp.Queue()
        self._metrics_buffer: List[MetricMessage] = []
        
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
        metrics = []
        
        # Get all available metrics from the queue
        while not self.metric_queue.empty():
            try:
                metric = self.metric_queue.get_nowait()
                if isinstance(metric, MetricMessage):
                    metrics.append(asdict(metric))
                else:
                    metrics.append(metric)
            except Exception:
                # Queue is empty or other error
                break
                
        return metrics
        
    def get_aggregated_metrics(self) -> Dict[str, Any]:
        """
        Get aggregated metrics for UI display.
        
        Returns:
            Dictionary with aggregated metrics
        """
        all_metrics = self.get_metrics()
        
        if not all_metrics:
            return {
                'total_processed': 0,
                'total_successful': 0,
                'total_failed': 0,
                'workers_status': {},
                'recent_metrics': []
            }
            
        # Aggregate metrics
        total_processed = len(all_metrics)
        total_successful = sum(1 for m in all_metrics if m.get('status') == 'COMPLETED')
        total_failed = sum(1 for m in all_metrics if m.get('status') == 'FAILED')
        
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