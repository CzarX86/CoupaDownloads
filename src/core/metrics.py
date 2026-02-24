"""
Prometheus metrics for CoupaDownloads.

Provides metrics export for monitoring and alerting.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import time


@dataclass
class MetricValue:
    """Represents a single metric value."""
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    metric_type: str = "gauge"  # gauge, counter, histogram


class MetricsCollector:
    """
    Collects and exposes metrics for Prometheus scraping.
    
    Metrics are stored in memory and can be exported in Prometheus format.
    """
    
    def __init__(self) -> None:
        """Initialize metrics collector."""
        self._metrics: Dict[str, MetricValue] = {}
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, list] = {}
    
    # =========================================================================
    # Counter Metrics
    # =========================================================================
    
    def inc_counter(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Increment a counter metric.
        
        Args:
            name: Metric name
            value: Value to increment by
            labels: Optional labels for the metric
        """
        key = self._make_key(name, labels)
        self._counters[key] = self._counters.get(key, 0) + value
    
    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> int:
        """Get counter value."""
        key = self._make_key(name, labels)
        return self._counters.get(key, 0)
    
    # =========================================================================
    # Gauge Metrics
    # =========================================================================
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Set a gauge metric.
        
        Args:
            name: Metric name
            value: Gauge value
            labels: Optional labels for the metric
        """
        key = self._make_key(name, labels)
        self._gauges[key] = value
    
    def inc_gauge(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment gauge."""
        key = self._make_key(name, labels)
        self._gauges[key] = self._gauges.get(key, 0.0) + value
    
    def dec_gauge(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Decrement gauge."""
        key = self._make_key(name, labels)
        self._gauges[key] = self._gauges.get(key, 0.0) - value
    
    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get gauge value."""
        key = self._make_key(name, labels)
        return self._gauges.get(key, 0.0)
    
    # =========================================================================
    # Histogram Metrics
    # =========================================================================
    
    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        buckets: Optional[list] = None
    ) -> None:
        """
        Observe a histogram value.
        
        Args:
            name: Metric name
            value: Observed value
            labels: Optional labels
            buckets: Bucket boundaries (default: standard buckets)
        """
        if buckets is None:
            buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        
        key = self._make_key(name, labels)
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)
    
    def get_histogram_summary(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Get histogram summary statistics."""
        key = self._make_key(name, labels)
        values = self._histograms.get(key, [])
        
        if not values:
            return {'count': 0, 'sum': 0.0, 'avg': 0.0}
        
        return {
            'count': len(values),
            'sum': sum(values),
            'avg': sum(values) / len(values),
            'min': min(values),
            'max': max(values),
        }
    
    # =========================================================================
    # PO Processing Metrics
    # =========================================================================
    
    def record_po_started(self, po_number: str, worker_id: int) -> None:
        """Record PO processing started."""
        self.inc_counter('pos_started_total', labels={'worker_id': str(worker_id)})
        self.set_gauge('po_processing', 1.0, labels={'po_number': po_number})
    
    def record_po_completed(
        self,
        po_number: str,
        worker_id: int,
        duration: float,
        status: str,
        attachments_found: int = 0,
        attachments_downloaded: int = 0
    ) -> None:
        """Record PO processing completed."""
        self.inc_counter('pos_completed_total', labels={'status': status})
        self.observe_histogram('po_processing_seconds', duration, labels={'status': status})
        self.set_gauge('po_processing', 0.0, labels={'po_number': po_number})
        
        if attachments_found > 0:
            self.inc_counter(
                'attachments_found_total',
                value=attachments_found,
                labels={'po_number': po_number}
            )
        
        if attachments_downloaded > 0:
            self.inc_counter(
                'attachments_downloaded_total',
                value=attachments_downloaded,
                labels={'po_number': po_number}
            )
    
    def record_po_failed(self, po_number: str, worker_id: int, error_type: str) -> None:
        """Record PO processing failed."""
        self.inc_counter('pos_failed_total', labels={'error_type': error_type})
        self.set_gauge('po_processing', 0.0, labels={'po_number': po_number})
    
    # =========================================================================
    # Worker Metrics
    # =========================================================================
    
    def record_worker_started(self, worker_id: int) -> None:
        """Record worker started."""
        self.inc_counter('workers_started_total')
        self.set_gauge('workers_active', 1.0, labels={'worker_id': str(worker_id)})
    
    def record_worker_stopped(self, worker_id: int) -> None:
        """Record worker stopped."""
        self.dec_gauge('workers_active', labels={'worker_id': str(worker_id)})
    
    def record_worker_error(self, worker_id: int, error_type: str) -> None:
        """Record worker error."""
        self.inc_counter('worker_errors_total', labels={'worker_id': str(worker_id), 'error_type': error_type})
    
    # =========================================================================
    # System Metrics
    # =========================================================================
    
    def record_system_resources(
        self,
        cpu_percent: float,
        memory_percent: float,
        disk_percent: float
    ) -> None:
        """Record system resource usage."""
        self.set_gauge('system_cpu_percent', cpu_percent)
        self.set_gauge('system_memory_percent', memory_percent)
        self.set_gauge('system_disk_percent', disk_percent)
    
    # =========================================================================
    # Export Methods
    # =========================================================================
    
    def _make_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Create unique key for metric with labels."""
        if not labels:
            return name
        
        label_str = ','.join(f'{k}={v}' for k, v in sorted(labels.items()))
        return f'{name}{{{label_str}}}'
    
    def export_prometheus(self) -> str:
        """
        Export all metrics in Prometheus text format.
        
        Returns:
            Metrics in Prometheus exposition format
        """
        lines = []
        
        # Export counters
        for key, value in self._counters.items():
            name = key.split('{')[0] if '{' in key else key
            lines.append(f'# TYPE {name} counter')
            lines.append(f'{key} {value}')
        
        # Export gauges
        for key, value in self._gauges.items():
            name = key.split('{')[0] if '{' in key else key
            lines.append(f'# TYPE {name} gauge')
            lines.append(f'{key} {value}')
        
        # Export histogram summaries
        for key, values in self._histograms.items():
            name = key.split('{')[0] if '{' in key else key
            if values:
                lines.append(f'# TYPE {name} histogram')
                lines.append(f'{name}_count{key[len(name):]} {len(values)}')
                lines.append(f'{name}_sum{key[len(name):]} {sum(values)}')
        
        return '\n'.join(lines)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics as dictionary."""
        return {
            'counters': dict(self._counters),
            'gauges': dict(self._gauges),
            'histograms': {k: self.get_histogram_summary(k.split('{')[0]) for k in self._histograms},
        }
    
    def reset(self) -> None:
        """Reset all metrics."""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
