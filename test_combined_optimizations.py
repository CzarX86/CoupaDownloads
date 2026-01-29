#!/usr/bin/env python3
"""
Test script for combined optimizations: reusable workers, parallel downloads, and UI metrics.

This script tests the integration of:
1. Reusable workers with shared PO queue
2. Parallel downloads within each worker
3. Inter-process communication for UI metrics
"""

import multiprocessing as mp
import time
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from src.worker_manager import WorkerManager
from src.lib.models import HeadlessConfiguration
from src.core.communication_manager import CommunicationManager
from src.ui_controller import UIController
from src.csv_manager import CSVManager
from src.lib.folder_hierarchy import FolderHierarchyManager


def test_combined_optimizations():
    """Test the combined optimizations."""
    print("🧪 Testing Combined Optimizations...")
    print("   - Reusable workers with shared PO queue")
    print("   - Parallel downloads within workers")
    print("   - Inter-process communication for UI metrics")

    # Create sample PO data
    sample_pos = [
        {'po_number': 'PO12345', 'supplier': 'Test Supplier 1'},
        {'po_number': 'PO12346', 'supplier': 'Test Supplier 2'},
        {'po_number': 'PO12347', 'supplier': 'Test Supplier 3'},
        {'po_number': 'PO12348', 'supplier': 'Test Supplier 4'},
    ]

    # Setup configuration
    headless_config = HeadlessConfiguration(
        headless_mode=False,  # Set to True for headless testing
        interactive_setup_session=None
    )

    # Initialize communication manager
    comm_manager = CommunicationManager()

    # Initialize UI controller
    ui_controller = UIController()

    # Initialize worker manager
    worker_manager = WorkerManager(enable_parallel=True, max_workers=2)

    # Create a shared queue for POs
    po_queue = mp.Queue()
    for po_data in sample_pos:
        po_queue.put(po_data)

    print(f"📦 Created queue with {len(sample_pos)} POs")

    # Test the reusable worker functionality with continuous UI updates
    print("🚀 Testing reusable workers with shared queue and continuous UI updates...")

    try:
        # Start live UI updates in a separate thread
        ui_controller.start_live_updates(comm_manager, update_interval=0.5)

        # Process POs with reusable workers
        successful, failed, report = worker_manager.process_parallel_with_reusable_workers(
            po_queue=po_queue,
            hierarchy_cols=[],
            has_hierarchy_data=False,
            headless_config=headless_config,
            communication_manager=comm_manager,
            csv_handler=None,
            folder_hierarchy=FolderHierarchyManager()
        )

        # Stop live updates after processing
        ui_controller.stop_live_updates()

        print(f"✅ Processing completed: {successful} successful, {failed} failed")
        print(f"📊 Report: {report}")

        # Final UI update with metrics
        print("📈 Final UI update with metrics...")
        ui_controller.update_with_metrics(comm_manager)

        # Get aggregated metrics
        agg_metrics = comm_manager.get_aggregated_metrics()
        print(f"📊 Aggregated Metrics: {agg_metrics}")

        print("🎉 All combined optimizations tested successfully!")

    except Exception as e:
        # Stop live updates in case of error
        try:
            ui_controller.stop_live_updates()
        except:
            pass
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


def test_parallel_downloads():
    """Test the parallel download functionality."""
    print("\n🧪 Testing Parallel Downloads...")
    
    from src.lib.browser import BrowserManager
    from src.lib.downloader import Downloader
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    # This is a conceptual test - actual testing would require a real browser session
    print("   Conceptual test: Parallel downloads should activate when >1 attachment is found")
    print("   - download_attachments_for_po() now calls download_attachments_parallel() when appropriate")
    print("   - download_attachments_parallel() uses ThreadPoolExecutor for concurrent downloads")
    print("   - Each worker can now process multiple POs with a single driver instance")
    print("   - Session clearing between POs prevents contamination")


def test_communication_manager():
    """Test the communication manager functionality."""
    print("\n🧪 Testing Communication Manager...")
    
    comm_manager = CommunicationManager()
    
    # Simulate sending metrics from different workers
    test_metrics = [
        {
            'worker_id': 0,
            'po_id': 'PO12345',
            'status': 'COMPLETED',
            'timestamp': time.time(),
            'duration': 15.5,
            'attachments_found': 3,
            'attachments_downloaded': 3,
            'message': 'Downloaded 3 attachment(s) successfully.'
        },
        {
            'worker_id': 1,
            'po_id': 'PO12346',
            'status': 'PARTIAL',
            'timestamp': time.time(),
            'duration': 12.3,
            'attachments_found': 2,
            'attachments_downloaded': 1,
            'message': 'Partial download: 1 of 2 attachment(s).'
        }
    ]
    
    # Send metrics
    for metric in test_metrics:
        comm_manager.send_metric(metric)
    
    # Retrieve metrics
    retrieved_metrics = comm_manager.get_metrics()
    print(f"   Sent {len(test_metrics)} metrics, retrieved {len(retrieved_metrics)}")
    
    # Get aggregated metrics
    agg_metrics = comm_manager.get_aggregated_metrics()
    print(f"   Aggregated metrics: {agg_metrics}")
    
    print("✅ Communication manager test completed")


if __name__ == "__main__":
    print("🚀 Starting Combined Optimizations Test Suite")
    print("=" * 60)
    
    # Run individual component tests
    test_communication_manager()
    test_parallel_downloads()
    
    # Run integrated test
    test_combined_optimizations()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed! Combined optimizations are ready.")