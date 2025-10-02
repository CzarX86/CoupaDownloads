"""
Tests for ResourceMonitor implementation.
Validates resource monitoring functionality for parallel processing.
"""

import os
import time
import pytest
import threading
from datetime import datetime, timedelta
from pathlib import Path
import tempfile

from EXPERIMENTAL.workers.resource_monitor import (
    ResourceMonitor, ResourceSnapshot, WorkerMetrics, ResourceLimits,
    ResourceOptimizer, create_default_monitor
)


class TestResourceMonitor:
    """Test suite for ResourceMonitor functionality."""
    
    def test_resource_monitor_initialization(self):
        """Test ResourceMonitor can be initialized with correct defaults."""
        monitor = create_default_monitor()
        
        assert monitor.monitoring_interval == 1.0
        assert monitor.history_limit == 1000
        assert monitor.limits.max_cpu_percent == 85.0
        assert monitor.limits.max_memory_percent == 80.0
        assert len(monitor.snapshots) == 0
        assert len(monitor.worker_metrics) == 0
        
        # Test initial snapshot is taken
        assert monitor.initial_snapshot is not None
        assert monitor.initial_snapshot.cpu_percent >= 0
        assert monitor.initial_snapshot.memory_mb > 0
    
    def test_worker_registration(self):
        """Test worker registration and metrics tracking."""
        monitor = create_default_monitor()
        
        # Register workers
        monitor.register_worker("worker_1")
        monitor.register_worker("worker_2")
        
        assert len(monitor.worker_metrics) == 2
        assert "worker_1" in monitor.worker_metrics
        assert "worker_2" in monitor.worker_metrics
        
        # Check worker metrics initialization
        worker1 = monitor.worker_metrics["worker_1"]
        assert worker1.worker_id == "worker_1"
        assert worker1.processed_items == 0
        assert worker1.failed_items == 0
        assert worker1.status == "active"
        assert isinstance(worker1.start_time, datetime)
    
    def test_worker_metrics_updates(self):
        """Test updating worker metrics."""
        monitor = create_default_monitor()
        monitor.register_worker("test_worker")
        
        # Update metrics
        monitor.update_worker_metrics(
            "test_worker", 
            processed_items=5, 
            failed_items=1, 
            status="processing"
        )
        
        worker = monitor.worker_metrics["test_worker"]
        assert worker.processed_items == 5
        assert worker.failed_items == 1
        assert worker.status == "processing"
        
        # Test completion
        monitor.unregister_worker("test_worker")
        assert worker.status == "completed"
        assert worker.end_time is not None
    
    def test_resource_snapshot(self):
        """Test resource snapshot creation and data structure."""
        monitor = create_default_monitor()
        snapshot = monitor._take_snapshot()
        
        assert isinstance(snapshot, ResourceSnapshot)
        assert isinstance(snapshot.timestamp, datetime)
        assert snapshot.cpu_percent >= 0
        assert snapshot.memory_mb > 0
        assert snapshot.memory_percent >= 0
        assert snapshot.disk_usage_mb > 0
        assert snapshot.process_count > 0
        
        # Test serialization
        snapshot_dict = snapshot.to_dict()
        assert "timestamp" in snapshot_dict
        assert "cpu_percent" in snapshot_dict
        assert "memory_mb" in snapshot_dict
        assert isinstance(snapshot_dict["cpu_percent"], float)
    
    def test_monitoring_start_stop(self):
        """Test starting and stopping the monitoring loop."""
        monitor = create_default_monitor(monitoring_interval=0.1)
        
        # Start monitoring
        monitor.start_monitoring()
        assert monitor._monitoring_thread is not None
        assert monitor._monitoring_thread.is_alive()
        
        # Let it collect some data
        time.sleep(0.5)
        
        # Check that snapshots are being collected
        assert len(monitor.snapshots) > 0
        
        # Stop monitoring
        monitor.stop_monitoring()
        assert not monitor._monitoring_thread.is_alive()
    
    def test_context_manager(self):
        """Test ResourceMonitor as context manager."""
        monitor = create_default_monitor(monitoring_interval=0.1)
        
        with monitor:
            assert monitor._monitoring_thread is not None
            assert monitor._monitoring_thread.is_alive()
            
            # Register a worker
            monitor.register_worker("context_worker")
            time.sleep(0.3)
            
            assert len(monitor.snapshots) > 0
            assert "context_worker" in monitor.worker_metrics
        
        # Should be stopped after context exit
        assert not monitor._monitoring_thread.is_alive()
    
    def test_resource_limits_checking(self):
        """Test resource limits and alert generation."""
        limits = ResourceLimits(
            max_cpu_percent=50.0,
            max_memory_percent=60.0,
            warning_cpu_percent=40.0,
            warning_memory_percent=50.0
        )
        
        # Test CPU checking
        assert limits.check_cpu(30.0) == "normal"
        assert limits.check_cpu(45.0) == "warning"
        assert limits.check_cpu(55.0) == "critical"
        
        # Test memory checking
        assert limits.check_memory(40.0) == "normal"
        assert limits.check_memory(55.0) == "warning"
        assert limits.check_memory(65.0) == "critical"
    
    def test_alert_generation(self):
        """Test alert generation when limits are exceeded."""
        # Set low limits to trigger alerts
        limits = ResourceLimits(
            max_cpu_percent=1.0,  # Very low to trigger alerts
            max_memory_percent=1.0,
            warning_cpu_percent=0.5,
            warning_memory_percent=0.5
        )
        
        monitor = ResourceMonitor(
            monitoring_interval=0.1,
            limits=limits
        )
        
        # Add alert callback to capture alerts
        captured_alerts = []
        def alert_callback(alert):
            captured_alerts.append(alert)
        
        monitor.add_alert_callback(alert_callback)
        
        with monitor:
            time.sleep(0.3)  # Let it run and generate alerts
        
        # Should have generated alerts due to low limits
        assert len(captured_alerts) > 0
        assert len(monitor.alerts) > 0
        
        # Check alert structure
        alert = captured_alerts[0]
        assert "type" in alert
        assert "level" in alert
        assert "message" in alert
        assert "timestamp" in alert
    
    def test_performance_summary(self):
        """Test performance summary generation."""
        monitor = create_default_monitor(monitoring_interval=0.1)
        
        with monitor:
            # Register workers and simulate activity
            monitor.register_worker("worker_1")
            monitor.register_worker("worker_2")
            
            time.sleep(0.5)
            
            monitor.update_worker_metrics("worker_1", processed_items=10, failed_items=1)
            monitor.update_worker_metrics("worker_2", processed_items=15, failed_items=0)
            
            time.sleep(0.3)
        
        summary = monitor.get_performance_summary()
        
        assert "monitoring_duration" in summary
        assert "averages" in summary
        assert "peaks" in summary
        assert "worker_performance" in summary
        assert "alert_summary" in summary
        
        # Check worker performance data
        worker_perf = summary["worker_performance"]
        assert worker_perf["total_workers"] == 2
        assert worker_perf["total_processed"] == 25
        assert worker_perf["total_failed"] == 1
    
    def test_data_export(self):
        """Test exporting monitoring data to JSON."""
        monitor = create_default_monitor(monitoring_interval=0.1)
        
        with monitor:
            monitor.register_worker("export_worker")
            time.sleep(0.3)
            monitor.update_worker_metrics("export_worker", processed_items=5)
        
        # Export to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_path = Path(f.name)
        
        try:
            monitor.export_data(export_path)
            
            # Verify file was created and contains data
            assert export_path.exists()
            assert export_path.stat().st_size > 0
            
            # Load and verify JSON structure
            import json
            with open(export_path, 'r') as f:
                data = json.load(f)
            
            assert "metadata" in data
            assert "snapshots" in data
            assert "worker_metrics" in data
            assert "alerts" in data
            assert "summary" in data
            
            # Check worker data
            assert "export_worker" in data["worker_metrics"]
            worker_data = data["worker_metrics"]["export_worker"]
            assert worker_data["processed_items"] == 5
            
        finally:
            # Clean up temp file
            if export_path.exists():
                export_path.unlink()
    
    def test_worker_details(self):
        """Test getting detailed worker information."""
        monitor = create_default_monitor()
        
        # Test empty workers
        details = monitor.get_worker_details()
        assert isinstance(details, dict)
        assert len(details) == 0
        
        # Register workers
        monitor.register_worker("detail_worker_1")
        monitor.register_worker("detail_worker_2")
        
        # Update metrics
        monitor.update_worker_metrics("detail_worker_1", processed_items=8, failed_items=2)
        
        # Test all workers
        all_details = monitor.get_worker_details()
        assert len(all_details) == 2
        assert "detail_worker_1" in all_details
        assert "detail_worker_2" in all_details
        
        # Test specific worker
        worker1_details = monitor.get_worker_details("detail_worker_1")
        assert worker1_details["worker_id"] == "detail_worker_1"
        assert worker1_details["processed_items"] == 8
        assert worker1_details["failed_items"] == 2
        
        # Test non-existent worker
        nonexistent = monitor.get_worker_details("nonexistent")
        assert "error" in nonexistent


class TestResourceOptimizer:
    """Test suite for ResourceOptimizer functionality."""
    
    def test_optimizer_initialization(self):
        """Test ResourceOptimizer initialization."""
        monitor = create_default_monitor()
        optimizer = ResourceOptimizer(monitor)
        
        assert optimizer.monitor is monitor
    
    def test_worker_count_recommendation(self):
        """Test worker count recommendations."""
        monitor = create_default_monitor()
        optimizer = ResourceOptimizer(monitor)
        
        # Register some workers
        monitor.register_worker("opt_worker_1")
        monitor.register_worker("opt_worker_2")
        
        # Get recommendation
        recommendation = optimizer.get_worker_count_recommendation()
        
        assert "current_workers" in recommendation
        assert "recommended_workers" in recommendation
        assert "reason" in recommendation
        assert "confidence" in recommendation
        
        assert isinstance(recommendation["current_workers"], int)
        assert isinstance(recommendation["recommended_workers"], int)
        assert recommendation["current_workers"] >= 0
        assert recommendation["recommended_workers"] >= 1
    
    def test_performance_recommendations(self):
        """Test performance optimization recommendations."""
        monitor = create_default_monitor()
        optimizer = ResourceOptimizer(monitor)
        
        # Take a snapshot to have some data
        with monitor:
            time.sleep(0.1)
        
        recommendations = optimizer.get_performance_recommendations()
        
        assert isinstance(recommendations, list)
        
        # Each recommendation should have required fields
        for rec in recommendations:
            assert "type" in rec
            assert "priority" in rec
            assert "title" in rec
            assert "description" in rec
            assert "action" in rec


class TestIntegration:
    """Integration tests for ResourceMonitor with parallel processing."""
    
    def test_multiple_workers_simulation(self):
        """Test monitoring multiple workers with realistic workload."""
        monitor = create_default_monitor(monitoring_interval=0.1)
        
        with monitor:
            # Simulate starting multiple workers
            worker_ids = [f"sim_worker_{i}" for i in range(4)]
            
            for worker_id in worker_ids:
                monitor.register_worker(worker_id)
            
            # Simulate processing over time
            for step in range(10):
                time.sleep(0.1)
                
                for i, worker_id in enumerate(worker_ids):
                    # Different workers process at different rates
                    processed = step * (i + 1) * 2
                    failed = step // 3 if i == 0 else 0  # First worker has some failures
                    
                    monitor.update_worker_metrics(
                        worker_id,
                        processed_items=processed,
                        failed_items=failed,
                        status="processing"
                    )
            
            # Complete workers at different times
            for i, worker_id in enumerate(worker_ids):
                if i < 2:  # Complete first two workers
                    monitor.unregister_worker(worker_id)
        
        # Validate final state
        status = monitor.get_current_status()
        summary = monitor.get_performance_summary()
        
        # Note: After context exit, all workers may show as completed
        # Check that we had 4 workers total and some completed
        assert status["workers"]["active_count"] + status["workers"]["completed_count"] >= 2
        assert summary["worker_performance"]["total_workers"] == 4
        assert summary["worker_performance"]["total_processed"] > 0
        
        print(f"Integration test completed:")
        print(f"  Total processed: {summary['worker_performance']['total_processed']}")
        print(f"  Total failed: {summary['worker_performance']['total_failed']}")
        print(f"  Average throughput: {summary['worker_performance']['average_throughput']:.2f}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])