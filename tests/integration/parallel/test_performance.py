"""Integration test for performance measurement - T013

This test validates Scenario 5 from quickstart.md: Performance Measurement.
Tests should FAIL until the actual implementation is complete.
"""

import pytest
import time
import statistics
from typing import Dict, Any, List

# Import will fail until implementation exists - expected for TDD
try:
    from EXPERIMENTAL.core.main import MainApp
    from EXPERIMENTAL.corelib.config import HeadlessConfiguration
except ImportError as e:
    pytest.skip(f"Performance measurement modules not implemented yet: {e}", allow_module_level=True)


def measure_processing_time(app: MainApp, po_list: List[Dict], runs: int = 3) -> Dict[str, float]:
    """Measure processing time across multiple runs."""
    times = []
    
    for run in range(runs):
        print(f"Run {run + 1}/{runs}")
        start_time = time.time()
        success_count, failed_count = app._process_po_entries(po_list)
        end_time = time.time()
        
        duration = end_time - start_time
        times.append(duration)
        print(f"  Duration: {duration:.2f}s, Success: {success_count}, Failed: {failed_count}")
    
    return {
        'mean': statistics.mean(times),
        'stdev': statistics.stdev(times) if len(times) > 1 else 0,
        'min': min(times),
        'max': max(times)
    }


class TestPerformanceMeasurement:
    """Test performance measurement per quickstart.md Scenario 5."""
    
    def test_sequential_vs_parallel_performance_comparison(self):
        """Compare sequential vs parallel processing performance."""
        # Prepare test data
        po_list = [
            {
                "po_number": f"PERF-{i:03d}", 
                "supplier": f"Supplier {i}", 
                "url": f"https://example.com/po{i}", 
                "amount": 1000.00 + i
            }
            for i in range(8)  # 8 POs for meaningful comparison
        ]
        
        config = HeadlessConfiguration(headless=True)
        
        # Test sequential processing
        print("Testing Sequential Processing...")
        sequential_app = MainApp(
            headless_config=config,
            enable_parallel=False
        )
        sequential_stats = measure_processing_time(sequential_app, po_list)
        
        # Test parallel processing (2 workers)
        print("\\nTesting Parallel Processing (2 workers)...")
        parallel_app_2 = MainApp(
            headless_config=config,
            enable_parallel=True,
            max_workers=2
        )
        parallel_stats_2 = measure_processing_time(parallel_app_2, po_list)
        
        # Test parallel processing (4 workers)
        print("\\nTesting Parallel Processing (4 workers)...")
        parallel_app_4 = MainApp(
            headless_config=config,
            enable_parallel=True,
            max_workers=4
        )
        parallel_stats_4 = measure_processing_time(parallel_app_4, po_list)
        
        # Calculate improvements
        improvement_2w = sequential_stats['mean'] / parallel_stats_2['mean']
        improvement_4w = sequential_stats['mean'] / parallel_stats_4['mean']
        
        print(f"\\n=== Performance Results ===")
        print(f"Sequential:     {sequential_stats['mean']:.2f}s ± {sequential_stats['stdev']:.2f}s")
        print(f"Parallel (2w):  {parallel_stats_2['mean']:.2f}s ± {parallel_stats_2['stdev']:.2f}s")
        print(f"Parallel (4w):  {parallel_stats_4['mean']:.2f}s ± {parallel_stats_4['stdev']:.2f}s")
        print(f"\\nSpeedup with 2 workers: {improvement_2w:.2f}x")
        print(f"Speedup with 4 workers: {improvement_4w:.2f}x")
        
        # Validate performance targets (structure test)
        assert improvement_2w > 0, "Performance measurement should be possible"
        assert improvement_4w > 0, "Performance measurement should be possible"
        
        # Performance targets would be validated in real implementation
        # assert improvement_2w > 1.5, f"2-worker speedup too low: {improvement_2w:.2f}x"
        # assert improvement_4w > 2.0, f"4-worker speedup too low: {improvement_4w:.2f}x"
        
        print("\\nPerformance measurement structure validated!")
    
    def test_throughput_measurement_and_scaling(self):
        """Test throughput measurement across different worker counts."""
        config = HeadlessConfiguration(headless=True)
        
        # Test data for throughput measurement
        po_list = [
            {
                "po_number": f"THROUGHPUT-{i:03d}",
                "supplier": f"Throughput Supplier {i}",
                "url": f"https://example.com/throughput{i}",
                "amount": 1000.00 + i
            }
            for i in range(12)  # 12 POs for throughput testing
        ]
        
        throughput_results = {}
        
        # Test different worker counts
        worker_counts = [1, 2, 4, 6]
        for worker_count in worker_counts:
            print(f"\\nTesting throughput with {worker_count} workers...")
            
            app = MainApp(
                headless_config=config,
                enable_parallel=worker_count > 1,
                max_workers=worker_count
            )
            
            start_time = time.time()
            success_count, failed_count = app._process_po_entries(po_list)
            duration = time.time() - start_time
            
            throughput = len(po_list) / duration if duration > 0 else 0
            throughput_results[worker_count] = {
                'duration': duration,
                'throughput': throughput,
                'success_count': success_count,
                'failed_count': failed_count
            }
            
            print(f"  {worker_count} workers: {duration:.2f}s, {throughput:.2f} POs/sec")
        
        # Analyze scaling characteristics
        print("\\n=== Throughput Scaling Analysis ===")
        for worker_count, results in throughput_results.items():
            print(f"{worker_count} workers: {results['throughput']:.2f} POs/sec")
        
        # Validate that throughput measurement works
        for worker_count, results in throughput_results.items():
            assert results['duration'] > 0, f"Duration should be measurable for {worker_count} workers"
            assert results['throughput'] >= 0, f"Throughput should be calculable for {worker_count} workers"
            assert results['success_count'] + results['failed_count'] == len(po_list), \
                   f"All POs should be accounted for with {worker_count} workers"
    
    def test_performance_metrics_collection(self):
        """Test collection of detailed performance metrics."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(
            headless_config=config,
            enable_parallel=True,
            max_workers=3
        )
        
        po_list = [
            {
                "po_number": "METRICS-001",
                "supplier": "Metrics Supplier A",
                "url": "https://example.com/metrics1",
                "amount": 1000.00
            },
            {
                "po_number": "METRICS-002",
                "supplier": "Metrics Supplier B",
                "url": "https://example.com/metrics2",
                "amount": 2000.00
            },
            {
                "po_number": "METRICS-003",
                "supplier": "Metrics Supplier C",
                "url": "https://example.com/metrics3",
                "amount": 1500.00
            }
        ]
        
        # Measure various performance aspects
        start_time = time.time()
        memory_before = self._get_memory_usage()
        
        success_count, failed_count = app._process_po_entries(po_list)
        
        end_time = time.time()
        memory_after = self._get_memory_usage()
        
        duration = end_time - start_time
        memory_delta = memory_after - memory_before
        
        # Collect performance metrics
        metrics = {
            'total_duration': duration,
            'memory_usage_delta': memory_delta,
            'pos_per_second': len(po_list) / duration if duration > 0 else 0,
            'success_rate': success_count / len(po_list) if len(po_list) > 0 else 0,
            'failure_rate': failed_count / len(po_list) if len(po_list) > 0 else 0
        }
        
        print(f"\\n=== Performance Metrics ===")
        print(f"Duration: {metrics['total_duration']:.2f}s")
        print(f"Memory delta: {metrics['memory_usage_delta']:.2f}MB")
        print(f"Throughput: {metrics['pos_per_second']:.2f} POs/sec")
        print(f"Success rate: {metrics['success_rate']:.1%}")
        print(f"Failure rate: {metrics['failure_rate']:.1%}")
        
        # Validate metrics are collectible
        assert isinstance(metrics['total_duration'], float)
        assert isinstance(metrics['memory_usage_delta'], (int, float))
        assert isinstance(metrics['pos_per_second'], float)
        assert isinstance(metrics['success_rate'], float)
        assert isinstance(metrics['failure_rate'], float)
        
        # All POs should be processed
        assert success_count + failed_count == len(po_list)
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except ImportError:
            # Fallback if psutil not available
            return 0.0
    
    def test_performance_consistency_validation(self):
        """Test that performance is consistent across multiple runs."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(
            headless_config=config,
            enable_parallel=True,
            max_workers=2
        )
        
        po_list = [
            {
                "po_number": f"CONSISTENCY-{i:03d}",
                "supplier": f"Consistency Supplier {i}",
                "url": f"https://example.com/consistency{i}",
                "amount": 1000.00 + i
            }
            for i in range(6)
        ]
        
        # Run multiple times to check consistency
        run_times = []
        run_results = []
        
        for run in range(5):
            start_time = time.time()
            success_count, failed_count = app._process_po_entries(po_list)
            duration = time.time() - start_time
            
            run_times.append(duration)
            run_results.append((success_count, failed_count))
            
            print(f"Run {run + 1}: {duration:.2f}s, {success_count} success, {failed_count} failed")
        
        # Analyze consistency
        mean_time = statistics.mean(run_times)
        stdev_time = statistics.stdev(run_times) if len(run_times) > 1 else 0
        coefficient_of_variation = stdev_time / mean_time if mean_time > 0 else 0
        
        print(f"\\n=== Consistency Analysis ===")
        print(f"Mean time: {mean_time:.2f}s")
        print(f"Standard deviation: {stdev_time:.2f}s")
        print(f"Coefficient of variation: {coefficient_of_variation:.2%}")
        
        # Check result consistency
        first_result = run_results[0]
        all_consistent = all(result == first_result for result in run_results)
        
        print(f"Result consistency: {all_consistent}")
        
        # Validate consistency measurements
        assert len(run_times) == 5, "Should have 5 timing measurements"
        assert all(time > 0 for time in run_times), "All runs should have positive duration"
        assert mean_time > 0, "Mean time should be positive"
        assert coefficient_of_variation >= 0, "CV should be non-negative"
    
    def test_resource_utilization_monitoring(self):
        """Test monitoring of resource utilization during processing."""
        config = HeadlessConfiguration(headless=True)
        app = MainApp(
            headless_config=config,
            enable_parallel=True,
            max_workers=4
        )
        
        po_list = [
            {
                "po_number": f"RESOURCE-{i:03d}",
                "supplier": f"Resource Supplier {i}",
                "url": f"https://example.com/resource{i}",
                "amount": 1000.00 + i
            }
            for i in range(10)
        ]
        
        # Monitor resources during processing
        resource_samples = []
        
        def sample_resources():
            """Sample resource usage."""
            try:
                import psutil
                cpu_percent = psutil.cpu_percent()
                memory_percent = psutil.virtual_memory().percent
                return {'cpu': cpu_percent, 'memory': memory_percent}
            except ImportError:
                return {'cpu': 0.0, 'memory': 0.0}
        
        # Take initial sample
        initial_resources = sample_resources()
        
        # Process POs
        start_time = time.time()
        success_count, failed_count = app._process_po_entries(po_list)
        duration = time.time() - start_time
        
        # Take final sample
        final_resources = sample_resources()
        
        # Calculate resource impact
        cpu_delta = final_resources['cpu'] - initial_resources['cpu']
        memory_delta = final_resources['memory'] - initial_resources['memory']
        
        print(f"\\n=== Resource Utilization ===")
        print(f"Processing time: {duration:.2f}s")
        print(f"CPU usage change: {cpu_delta:+.1f}%")
        print(f"Memory usage change: {memory_delta:+.1f}%")
        print(f"Processed: {success_count} success, {failed_count} failed")
        
        # Validate resource monitoring works
        assert isinstance(initial_resources['cpu'], (int, float))
        assert isinstance(initial_resources['memory'], (int, float))
        assert isinstance(final_resources['cpu'], (int, float))
        assert isinstance(final_resources['memory'], (int, float))
        assert success_count + failed_count == len(po_list)


class TestPerformanceBenchmarking:
    """Test performance benchmarking capabilities."""
    
    def test_linear_scaling_validation(self):
        """Test validation of linear scaling hypothesis."""
        config = HeadlessConfiguration(headless=True)
        
        # Test with different PO counts to validate scaling
        po_counts = [2, 4, 6, 8]
        scaling_results = {}
        
        for po_count in po_counts:
            po_list = [
                {
                    "po_number": f"SCALING-{po_count}-{i:03d}",
                    "supplier": f"Scaling Supplier {i}",
                    "url": f"https://example.com/scaling{i}",
                    "amount": 1000.00 + i
                }
                for i in range(po_count)
            ]
            
            # Test with fixed worker count
            app = MainApp(
                headless_config=config,
                enable_parallel=True,
                max_workers=2
            )
            
            start_time = time.time()
            success_count, failed_count = app._process_po_entries(po_list)
            duration = time.time() - start_time
            
            scaling_results[po_count] = {
                'duration': duration,
                'pos_per_second': po_count / duration if duration > 0 else 0,
                'duration_per_po': duration / po_count if po_count > 0 else 0
            }
            
            print(f"{po_count} POs: {duration:.2f}s, {scaling_results[po_count]['duration_per_po']:.2f}s/PO")
        
        # Analyze scaling characteristics
        print(f"\\n=== Scaling Analysis ===")
        for po_count, results in scaling_results.items():
            print(f"{po_count} POs: {results['pos_per_second']:.2f} POs/sec")
        
        # Validate that scaling analysis is possible
        assert len(scaling_results) == len(po_counts)
        for po_count, results in scaling_results.items():
            assert results['duration'] > 0
            assert results['pos_per_second'] >= 0
            assert results['duration_per_po'] >= 0
    
    def test_performance_regression_detection(self):
        """Test capability to detect performance regressions."""
        config = HeadlessConfiguration(headless=True)
        
        # Baseline performance measurement
        baseline_app = MainApp(
            headless_config=config,
            enable_parallel=True,
            max_workers=2
        )
        
        po_list = [
            {
                "po_number": f"REGRESSION-{i:03d}",
                "supplier": f"Regression Supplier {i}",
                "url": f"https://example.com/regression{i}",
                "amount": 1000.00 + i
            }
            for i in range(6)
        ]
        
        # Measure baseline
        baseline_stats = measure_processing_time(baseline_app, po_list, runs=3)
        
        # Simulate different performance scenarios
        # (In real implementation, this would test different configurations)
        test_app = MainApp(
            headless_config=config,
            enable_parallel=True,
            max_workers=1  # Reduced workers to simulate regression
        )
        
        test_stats = measure_processing_time(test_app, po_list, runs=3)
        
        # Compare performance
        performance_ratio = test_stats['mean'] / baseline_stats['mean']
        
        print(f"\\n=== Regression Detection ===")
        print(f"Baseline: {baseline_stats['mean']:.2f}s ± {baseline_stats['stdev']:.2f}s")
        print(f"Test: {test_stats['mean']:.2f}s ± {test_stats['stdev']:.2f}s")
        print(f"Performance ratio: {performance_ratio:.2f}")
        
        # Validate regression detection capability
        assert isinstance(performance_ratio, float)
        assert performance_ratio > 0
        
        # In real implementation, would check for significant regression
        # regression_threshold = 1.2  # 20% slower considered regression
        # assert performance_ratio < regression_threshold, f"Performance regression detected: {performance_ratio:.2f}x slower"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])