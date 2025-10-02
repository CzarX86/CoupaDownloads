"""
Performance test: browser initialization < 10 seconds.

This module contains performance tests to ensure that browser initialization
completes within acceptable time limits for both headless and visible modes.
"""

import pytest
import time
import statistics
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'EXPERIMENTAL'))

from corelib.browser import BrowserManager
from corelib.models import HeadlessConfiguration
from core.main import MainApp


class TestBrowserInitializationSpeed:
    """Performance tests for browser initialization speed."""
    
    @pytest.mark.performance
    def test_headless_browser_initialization_speed(self):
        """Test that headless browser initialization completes within 10 seconds."""
        print("\n⏱️ Testing headless browser initialization speed...")
        
        browser_manager = BrowserManager()
        
        # Mock the actual webdriver to avoid real browser startup
        with patch('selenium.webdriver.Edge') as mock_edge:
            mock_driver = Mock()
            mock_edge.return_value = mock_driver
            
            # Measure initialization time
            start_time = time.time()
            browser_manager.initialize_driver(headless=True)
            end_time = time.time()
            
            initialization_time = end_time - start_time
            
            print(f"Headless initialization time: {initialization_time:.3f} seconds")
            
            # Performance requirement: < 10 seconds
            assert initialization_time < 10.0, \
                f"Headless browser initialization took {initialization_time:.2f}s, should be < 10s"
            
            # Verify headless mode was used
            mock_edge.assert_called_once()
            call_args = mock_edge.call_args
            
            # Check options for headless arguments
            if call_args and 'options' in call_args[1]:
                options = call_args[1]['options']
                arguments = getattr(options, 'arguments', [])
                has_headless = any('--headless' in str(arg) for arg in arguments)
                assert has_headless, "Headless arguments should be present in browser options"
        
        print("✅ Headless browser initialization speed test PASSED")
    
    @pytest.mark.performance
    def test_visible_browser_initialization_speed(self):
        """Test that visible browser initialization completes within 10 seconds."""
        print("\n⏱️ Testing visible browser initialization speed...")
        
        browser_manager = BrowserManager()
        
        # Mock the actual webdriver to avoid real browser startup
        with patch('selenium.webdriver.Edge') as mock_edge:
            mock_driver = Mock()
            mock_edge.return_value = mock_driver
            
            # Measure initialization time
            start_time = time.time()
            browser_manager.initialize_driver(headless=False)
            end_time = time.time()
            
            initialization_time = end_time - start_time
            
            print(f"Visible initialization time: {initialization_time:.3f} seconds")
            
            # Performance requirement: < 10 seconds
            assert initialization_time < 10.0, \
                f"Visible browser initialization took {initialization_time:.2f}s, should be < 10s"
            
            # Verify visible mode was used (no headless arguments)
            mock_edge.assert_called_once()
            call_args = mock_edge.call_args
            
            if call_args and 'options' in call_args[1]:
                options = call_args[1]['options']
                arguments = getattr(options, 'arguments', [])
                has_headless = any('--headless' in str(arg) for arg in arguments)
                assert not has_headless, "Headless arguments should NOT be present in visible mode"
        
        print("✅ Visible browser initialization speed test PASSED")
    
    @pytest.mark.performance
    def test_multiple_initialization_speed_consistency(self):
        """Test that multiple browser initializations maintain consistent speed."""
        print("\n⏱️ Testing multiple initialization speed consistency...")
        
        browser_manager = BrowserManager()
        initialization_times = []
        
        # Test multiple initializations
        num_tests = 5
        
        for i in range(num_tests):
            with patch('selenium.webdriver.Edge') as mock_edge:
                mock_driver = Mock()
                mock_edge.return_value = mock_driver
                
                # Reset browser manager state
                browser_manager.driver = None
                
                # Measure initialization time
                start_time = time.time()
                browser_manager.initialize_driver(headless=True)
                end_time = time.time()
                
                initialization_time = end_time - start_time
                initialization_times.append(initialization_time)
                
                print(f"  Initialization {i+1}: {initialization_time:.3f}s")
        
        # Calculate statistics
        avg_time = statistics.mean(initialization_times)
        max_time = max(initialization_times)
        min_time = min(initialization_times)
        std_dev = statistics.stdev(initialization_times) if len(initialization_times) > 1 else 0
        
        print(f"Average time: {avg_time:.3f}s")
        print(f"Min time: {min_time:.3f}s")
        print(f"Max time: {max_time:.3f}s")
        print(f"Std deviation: {std_dev:.3f}s")
        
        # Performance requirements
        assert avg_time < 10.0, f"Average initialization time {avg_time:.2f}s should be < 10s"
        assert max_time < 10.0, f"Maximum initialization time {max_time:.2f}s should be < 10s"
        assert std_dev < 2.0, f"Time consistency std dev {std_dev:.2f}s should be < 2s"
        
        print("✅ Multiple initialization consistency test PASSED")
    
    @pytest.mark.performance
    def test_mainapp_browser_initialization_speed(self):
        """Test MainApp browser initialization speed with configuration."""
        print("\n⏱️ Testing MainApp browser initialization speed...")
        
        # Create headless configuration
        config = HeadlessConfiguration(enabled=True, source="interactive_setup")
        app = MainApp()
        app.set_headless_configuration(config)
        
        # Mock browser manager
        with patch.object(app, 'browser_manager') as mock_browser_manager:
            mock_browser_manager.initialize_driver.return_value = Mock()
            mock_browser_manager.driver = Mock()
            
            # Measure MainApp initialization time
            start_time = time.time()
            app.initialize_browser_once()
            end_time = time.time()
            
            initialization_time = end_time - start_time
            
            print(f"MainApp initialization time: {initialization_time:.3f} seconds")
            
            # Performance requirement: < 10 seconds
            assert initialization_time < 10.0, \
                f"MainApp browser initialization took {initialization_time:.2f}s, should be < 10s"
            
            # Verify browser was initialized with correct headless setting
            mock_browser_manager.initialize_driver.assert_called_once()
            call_args = mock_browser_manager.initialize_driver.call_args
            
            # Check that headless parameter was passed correctly
            if call_args and len(call_args) > 1:
                kwargs = call_args[1]
                assert kwargs.get('headless') == True, "MainApp should pass headless=True"
        
        print("✅ MainApp browser initialization speed test PASSED")
    
    @pytest.mark.performance
    def test_browser_options_creation_speed(self):
        """Test that browser options creation is fast and doesn't impact initialization."""
        print("\n⏱️ Testing browser options creation speed...")
        
        browser_manager = BrowserManager()
        option_times = []
        
        # Test options creation speed
        num_tests = 10
        
        for i in range(num_tests):
            start_time = time.time()
            options = browser_manager._create_browser_options(headless=True)
            end_time = time.time()
            
            creation_time = end_time - start_time
            option_times.append(creation_time)
        
        avg_option_time = statistics.mean(option_times)
        max_option_time = max(option_times)
        
        print(f"Average options creation time: {avg_option_time:.3f}s")
        print(f"Maximum options creation time: {max_option_time:.3f}s")
        
        # Options creation should be very fast (< 1 second)
        assert avg_option_time < 1.0, f"Options creation avg {avg_option_time:.2f}s should be < 1s"
        assert max_option_time < 1.0, f"Options creation max {max_option_time:.2f}s should be < 1s"
        
        print("✅ Browser options creation speed test PASSED")


class TestBrowserInitializationPerformanceUnderLoad:
    """Test browser initialization performance under various load conditions."""
    
    @pytest.mark.performance
    def test_concurrent_browser_initialization_speed(self):
        """Test browser initialization speed when multiple instances are created."""
        print("\n⏱️ Testing concurrent browser initialization performance...")
        
        import threading
        import concurrent.futures
        
        def initialize_browser_worker(worker_id, headless_mode):
            """Worker function for concurrent initialization testing."""
            browser_manager = BrowserManager()
            
            with patch('selenium.webdriver.Edge') as mock_edge:
                mock_driver = Mock()
                mock_edge.return_value = mock_driver
                
                start_time = time.time()
                browser_manager.initialize_driver(headless=headless_mode)
                end_time = time.time()
                
                return {
                    'worker_id': worker_id,
                    'headless': headless_mode,
                    'time': end_time - start_time
                }
        
        # Test with 4 concurrent workers (simulate process pool)
        num_workers = 4
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Submit tasks
            futures = []
            for i in range(num_workers):
                headless_mode = i % 2 == 0  # Alternate between headless/visible
                future = executor.submit(initialize_browser_worker, i, headless_mode)
                futures.append(future)
            
            # Collect results
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results.append(result)
                print(f"  Worker {result['worker_id']} ({'headless' if result['headless'] else 'visible'}): {result['time']:.3f}s")
        
        # Analyze concurrent performance
        times = [r['time'] for r in results]
        avg_time = statistics.mean(times)
        max_time = max(times)
        
        print(f"Concurrent average time: {avg_time:.3f}s")
        print(f"Concurrent maximum time: {max_time:.3f}s")
        
        # Performance requirements for concurrent execution
        assert avg_time < 10.0, f"Concurrent avg time {avg_time:.2f}s should be < 10s"
        assert max_time < 15.0, f"Concurrent max time {max_time:.2f}s should be < 15s (allowing overhead)"
        
        print("✅ Concurrent browser initialization performance test PASSED")
    
    @pytest.mark.performance
    def test_browser_initialization_memory_efficiency(self):
        """Test that browser initialization doesn't consume excessive memory."""
        print("\n⏱️ Testing browser initialization memory efficiency...")
        
        import psutil
        import gc
        
        process = psutil.Process()
        
        # Baseline memory usage
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        browser_managers = []
        
        # Create multiple browser managers
        num_managers = 5
        
        for i in range(num_managers):
            with patch('selenium.webdriver.Edge') as mock_edge:
                mock_driver = Mock()
                mock_edge.return_value = mock_driver
                
                browser_manager = BrowserManager()
                browser_manager.initialize_driver(headless=True)
                browser_managers.append(browser_manager)
        
        # Check memory usage after initialization
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - baseline_memory
        
        print(f"Baseline memory: {baseline_memory:.1f} MB")
        print(f"Final memory: {final_memory:.1f} MB")
        print(f"Memory increase: {memory_increase:.1f} MB")
        print(f"Memory per manager: {memory_increase / num_managers:.1f} MB")
        
        # Memory efficiency requirements (allowing for test framework overhead)
        assert memory_increase < 100.0, f"Memory increase {memory_increase:.1f}MB should be < 100MB"
        
        # Cleanup
        del browser_managers
        gc.collect()
        
        print("✅ Browser initialization memory efficiency test PASSED")
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_browser_initialization_stress_test(self):
        """Stress test: rapid sequential browser initializations."""
        print("\n⏱️ Running browser initialization stress test...")
        
        num_iterations = 20
        times = []
        
        for i in range(num_iterations):
            browser_manager = BrowserManager()
            
            with patch('selenium.webdriver.Edge') as mock_edge:
                mock_driver = Mock()
                mock_edge.return_value = mock_driver
                
                start_time = time.time()
                browser_manager.initialize_driver(headless=True)
                end_time = time.time()
                
                initialization_time = end_time - start_time
                times.append(initialization_time)
                
                # Cleanup
                browser_manager.cleanup()
                del browser_manager
        
        # Analyze stress test results
        avg_time = statistics.mean(times)
        max_time = max(times)
        min_time = min(times)
        
        # Check for performance degradation
        first_half_avg = statistics.mean(times[:num_iterations//2])
        second_half_avg = statistics.mean(times[num_iterations//2:])
        degradation = second_half_avg - first_half_avg
        
        print(f"Stress test - Average time: {avg_time:.3f}s")
        print(f"Stress test - Min time: {min_time:.3f}s")
        print(f"Stress test - Max time: {max_time:.3f}s")
        print(f"Performance degradation: {degradation:.3f}s")
        
        # Stress test requirements
        assert avg_time < 10.0, f"Stress test avg time {avg_time:.2f}s should be < 10s"
        assert degradation < 2.0, f"Performance degradation {degradation:.2f}s should be < 2s"
        
        print("✅ Browser initialization stress test PASSED")


# Test configuration
def pytest_configure(config):
    """Configure pytest for performance testing."""
    config.addinivalue_line("markers", "performance: mark test as performance test")
    config.addinivalue_line("markers", "slow: mark test as slow performance test")

if __name__ == "__main__":
    # Run performance tests if executed directly
    import pytest
    pytest.main([__file__, "-v", "-m", "performance"])