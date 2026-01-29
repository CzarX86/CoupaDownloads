#!/usr/bin/env python3
"""
Demonstration of how the combined optimizations would work in a real application.

This script shows the proper way to integrate continuous UI updates with
the reusable workers and parallel downloads.
"""

import multiprocessing as mp
import time
import threading
from pathlib import Path
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from src.worker_manager import WorkerManager
from src.lib.models import HeadlessConfiguration
from src.core.communication_manager import CommunicationManager
from src.ui_controller import UIController
from src.lib.folder_hierarchy import FolderHierarchyManager


def simulate_continuous_processing():
    """Simulate how continuous UI updates would work during actual processing."""
    print("🎯 Demonstrating Continuous UI Updates During Processing")
    print("=" * 60)
    
    # Create sample PO data
    sample_pos = [
        {'po_number': 'PO12345', 'supplier': 'Test Supplier 1'},
        {'po_number': 'PO12346', 'supplier': 'Test Supplier 2'},
        {'po_number': 'PO12347', 'supplier': 'Test Supplier 3'},
        {'po_number': 'PO12348', 'supplier': 'Test Supplier 4'},
        {'po_number': 'PO12349', 'supplier': 'Test Supplier 5'},
    ]
    
    # Setup configuration
    headless_config = HeadlessConfiguration(
        headless_mode=False,
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
    
    # Start the UI in a live display (simulated)
    print("\n📊 Starting UI with live updates...")
    
    # In a real application, we would start the UI updates in a separate thread
    # while the processing runs in the background
    def run_ui_updates():
        """Function to run UI updates continuously."""
        import time
        ui_controller.start_live_updates(comm_manager, update_interval=1.0)
        
    # Start UI updates in a background thread
    ui_thread = threading.Thread(target=run_ui_updates, daemon=True)
    ui_thread.start()
    
    print("🚀 Starting processing with reusable workers...")
    
    try:
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
        
        print(f"\n✅ Processing completed: {successful} successful, {failed} failed")
        print(f"📊 Report: {report['processing_mode']}, {report['worker_count']} workers used")
        
        # Allow UI to catch up with final updates
        time.sleep(2)
        
        # Stop UI updates
        ui_controller.stop_live_updates()
        
        # Final metrics display
        agg_metrics = comm_manager.get_aggregated_metrics()
        print(f"\n📈 Final Aggregated Metrics:")
        print(f"   Total Processed: {agg_metrics['total_processed']}")
        print(f"   Successful: {agg_metrics['total_successful']}")
        print(f"   Failed: {agg_metrics['total_failed']}")
        
        print("\n🎉 Combined optimizations demonstration completed successfully!")
        
    except Exception as e:
        # Stop UI updates in case of error
        try:
            ui_controller.stop_live_updates()
        except:
            pass
        print(f"❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()


def demonstrate_worker_metrics():
    """Demonstrate how worker metrics are sent and received."""
    print("\n🔍 Demonstrating Worker Metrics Flow")
    print("=" * 60)
    
    # Initialize communication manager
    comm_manager = CommunicationManager()
    
    # Simulate metrics being sent from different workers
    print("📤 Simulating metrics from workers...")
    
    # Simulate worker 0 processing a PO
    metric1 = {
        'worker_id': 0,
        'po_id': 'PO12345',
        'status': 'PROCESSING',
        'timestamp': time.time(),
        'duration': 5.2,
        'attachments_found': 3,
        'attachments_downloaded': 2,
        'message': 'Downloading attachments...'
    }
    comm_manager.send_metric(metric1)
    
    # Simulate worker 1 processing a PO
    metric2 = {
        'worker_id': 1,
        'po_id': 'PO12346',
        'status': 'COMPLETED',
        'timestamp': time.time(),
        'duration': 12.7,
        'attachments_found': 5,
        'attachments_downloaded': 5,
        'message': 'Downloaded 5 attachment(s) successfully.'
    }
    comm_manager.send_metric(metric2)
    
    # Simulate worker 0 completing its PO
    metric3 = {
        'worker_id': 0,
        'po_id': 'PO12345',
        'status': 'COMPLETED',
        'timestamp': time.time(),
        'duration': 8.4,
        'attachments_found': 3,
        'attachments_downloaded': 3,
        'message': 'Downloaded 3 attachment(s) successfully.'
    }
    comm_manager.send_metric(metric3)
    
    print("📥 Retrieving metrics from communication manager...")
    metrics = comm_manager.get_metrics()
    print(f"   Retrieved {len(metrics)} metrics")
    
    for i, metric in enumerate(metrics):
        print(f"   Metric {i+1}: Worker {metric['worker_id']} - PO {metric['po_id']} - Status: {metric['status']}")
    
    print("\n📊 Getting aggregated metrics...")
    agg_metrics = comm_manager.get_aggregated_metrics()
    print(f"   Total Processed: {agg_metrics['total_processed']}")
    print(f"   Successful: {agg_metrics['total_successful']}")
    print(f"   Workers Status: {list(agg_metrics['workers_status'].keys())}")


if __name__ == "__main__":
    print("🚀 Combined Optimizations - Continuous UI Updates Demo")
    print("=" * 80)
    
    # Demonstrate metrics flow
    demonstrate_worker_metrics()
    
    # Show how continuous processing would work
    simulate_continuous_processing()
    
    print("\n" + "=" * 80)
    print("✅ Demo completed! The UI updates continuously during processing.")
    print("   - Workers send metrics to CommunicationManager")
    print("   - UI polls for metrics and updates display")
    print("   - Real-time visibility into each worker's progress")