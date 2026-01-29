#!/usr/bin/env python3
"""
Test script to verify continuous UI updates during processing.
"""

import multiprocessing as mp
import time
import threading
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from src.worker_manager import WorkerManager
from src.lib.models import HeadlessConfiguration
from src.core.communication_manager import CommunicationManager
from src.ui_controller import UIController
from src.lib.folder_hierarchy import FolderHierarchyManager
from rich.live import Live
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table


def test_real_time_updates():
    """Test real-time updates during processing."""
    print("🧪 Testing Real-Time UI Updates")
    print("=" * 50)
    
    # Initialize components
    comm_manager = CommunicationManager()
    ui_controller = UIController()
    
    # Create a Rich Live display for real-time updates
    console = Console()
    
    # Start live updates in a separate thread
    ui_controller.start_live_updates(comm_manager, update_interval=0.5)
    
    # Simulate sending metrics from workers
    print("📤 Simulating metrics from workers...")
    
    try:
        # Send initial metrics
        for i in range(3):
            metric = {
                'worker_id': i % 2,  # Alternate between 2 workers
                'po_id': f'PO_TEST_{i+1}',
                'status': 'PROCESSING',
                'timestamp': time.time(),
                'duration': 0.0,
                'attachments_found': 3,
                'attachments_downloaded': 0,
                'message': f'Processing PO_TEST_{i+1}'
            }
            comm_manager.send_metric(metric)
            print(f"   Sent metric for Worker {metric['worker_id']}, PO {metric['po_id']}")
            time.sleep(0.3)
        
        # Send completion metrics
        for i in range(3):
            metric = {
                'worker_id': i % 2,  # Alternate between 2 workers
                'po_id': f'PO_TEST_{i+1}',
                'status': 'COMPLETED',
                'timestamp': time.time(),
                'duration': round(time.time() % 10, 2),
                'attachments_found': 3,
                'attachments_downloaded': 3,
                'message': f'Completed PO_TEST_{i+1}'
            }
            comm_manager.send_metric(metric)
            print(f"   Sent completion metric for Worker {metric['worker_id']}, PO {metric['po_id']}")
            time.sleep(0.3)
        
        print("⏰ Waiting for UI to update...")
        time.sleep(3)  # Allow time for UI updates
        
        # Stop live updates
        ui_controller.stop_live_updates()
        
        print("✅ Real-time update test completed")
        
    except Exception as e:
        ui_controller.stop_live_updates()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def simulate_worker_behavior():
    """Simulate how a real worker would behave with metrics."""
    print("\n🤖 Simulating Worker Behavior with Metrics")
    print("=" * 50)
    
    comm_manager = CommunicationManager()
    
    # Simulate a worker processing multiple POs
    worker_id = 1
    pos_to_process = ['PO1001', 'PO1002', 'PO1003']
    
    for i, po_num in enumerate(pos_to_process):
        # Send STARTED metric
        start_time = time.time()
        metric = {
            'worker_id': worker_id,
            'po_id': po_num,
            'status': 'STARTED',
            'timestamp': start_time,
            'duration': 0.0,
            'attachments_found': 4,
            'attachments_downloaded': 0,
            'message': f'Started processing {po_num}'
        }
        comm_manager.send_metric(metric)
        print(f"   Worker {worker_id} started {po_num}")
        
        # Simulate processing time
        time.sleep(0.5)
        
        # Send PROCESSING updates periodically
        for j in range(3):
            metric = {
                'worker_id': worker_id,
                'po_id': po_num,
                'status': 'PROCESSING',
                'timestamp': time.time(),
                'duration': round(time.time() - start_time, 2),
                'attachments_found': 4,
                'attachments_downloaded': j+1,  # Simulate progress
                'message': f'Downloading attachment {j+2}/4 for {po_num}'
            }
            comm_manager.send_metric(metric)
            print(f"   Worker {worker_id} progress on {po_num}: {j+2}/4")
            time.sleep(0.3)
        
        # Send COMPLETED metric
        end_time = time.time()
        metric = {
            'worker_id': worker_id,
            'po_id': po_num,
            'status': 'COMPLETED',
            'timestamp': end_time,
            'duration': round(end_time - start_time, 2),
            'attachments_found': 4,
            'attachments_downloaded': 4,
            'message': f'Completed {po_num} - 4/4 attachments'
        }
        comm_manager.send_metric(metric)
        print(f"   Worker {worker_id} completed {po_num} in {round(end_time - start_time, 2)}s")
        
        time.sleep(0.2)  # Small delay between POs
    
    # Get and display final metrics
    agg_metrics = comm_manager.get_aggregated_metrics()
    print(f"\n📊 Final Metrics:")
    print(f"   Total Processed: {agg_metrics['total_processed']}")
    print(f"   Successful: {agg_metrics['total_successful']}")
    print(f"   Workers Active: {list(agg_metrics['workers_status'].keys())}")


if __name__ == "__main__":
    print("🚀 Testing Real-Time UI Updates")
    print("=" * 60)
    
    # Test real-time updates
    test_real_time_updates()
    
    # Simulate worker behavior
    simulate_worker_behavior()
    
    print("\n" + "=" * 60)
    print("✅ All tests completed! UI should update in real-time during processing.")