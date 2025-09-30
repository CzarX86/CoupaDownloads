"""
Quick test for ResourceMonitor to verify basic functionality without long-running tests.
"""

import time
import tempfile
from pathlib import Path
from EXPERIMENTAL.workers.resource_monitor import create_default_monitor


def test_resource_monitor_quick():
    """Quick test of ResourceMonitor functionality."""
    print("Testing ResourceMonitor basic functionality...")
    
    # Create monitor with very fast interval for testing
    monitor = create_default_monitor(monitoring_interval=0.05)
    
    try:
        # Test 1: Basic functionality
        monitor.start_monitoring()
        print("✅ Monitoring started")
        
        # Test 2: Worker registration
        monitor.register_worker("quick_test_worker")
        print("✅ Worker registered")
        
        # Test 3: Brief monitoring period
        time.sleep(0.2)  # Very short monitoring period
        
        # Test 4: Update metrics
        monitor.update_worker_metrics("quick_test_worker", processed_items=3, failed_items=0)
        print("✅ Metrics updated")
        
        # Test 5: Get status (should be fast)
        status = monitor.get_current_status()
        assert status['workers']['active_count'] > 0
        print(f"✅ Status retrieved: {status['workers']['active_count']} workers")
        
        # Test 6: Stop monitoring
        monitor.stop_monitoring()
        print("✅ Monitoring stopped")
        
        # Test 7: Quick export test
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            export_path = Path(f.name)
        
        try:
            # This should be fast since monitoring is stopped
            monitor.export_data(export_path)
            print(f"✅ Data exported to {export_path}")
            
            # Verify file exists and has content
            assert export_path.exists()
            assert export_path.stat().st_size > 10  # At least some content
            print("✅ Export file validated")
            
        finally:
            # Cleanup
            if export_path.exists():
                export_path.unlink()
        
        print("🎉 All ResourceMonitor tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    finally:
        # Ensure cleanup
        try:
            monitor.stop_monitoring()
        except:
            pass


if __name__ == "__main__":
    success = test_resource_monitor_quick()
    exit(0 if success else 1)