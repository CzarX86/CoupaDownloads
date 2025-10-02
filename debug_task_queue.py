#!/usr/bin/env python3
"""
Debug script to test task queue behavior in isolation.
"""

import sys
import time
import asyncio
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "EXPERIMENTAL"))

from workers.task_queue import TaskQueue, ProcessingTask
from workers.persistent_pool import PersistentWorkerPool
from workers.models.config import PoolConfig


def test_task_queue_basic():
    """Test basic TaskQueue functionality."""
    print("=== Testing TaskQueue Basic Functionality ===")
    
    queue = TaskQueue(max_retries=3, task_timeout=30.0)
    
    # Test adding a task
    def dummy_task(po_data):
        return {'success': True, 'data': po_data}
    
    po_data = {
        'po_number': 'TEST001',
        'supplier': 'Test Supplier',
        'url': 'https://example.com/po/TEST001'
    }
    task_id = queue.add_task(dummy_task, po_data, priority=5)
    
    print(f"Added task: {task_id}")
    
    # Check queue status
    status = queue.get_queue_status()
    print(f"Queue status after adding task: {status}")
    
    # Try to get next task
    task = queue.get_next_task("worker_1")
    print(f"Got task: {task}")
    
    if task:
        print(f"Task details: po_number={task.po_data.get('po_number')}, task_id={task.task_id}")
    
    # Check status again
    status = queue.get_queue_status()
    print(f"Queue status after getting task: {status}")


async def test_worker_pool_task_submission():
    """Test task submission in PersistentWorkerPool."""
    print("\n=== Testing PersistentWorkerPool Task Submission ===")
    
    # Create minimal config
    import tempfile
    import os
    temp_dir = tempfile.mkdtemp()
    print(f"Using temp directory: {temp_dir}")
    
    config = PoolConfig(
        worker_count=2,
        headless_mode=True,
        base_profile_path=temp_dir,
        memory_threshold=0.8,
        shutdown_timeout=30
    )
    
    pool = PersistentWorkerPool(config)
    
    # Check initial queue status
    initial_status = pool.task_queue.get_queue_status()
    print(f"Initial queue status: {initial_status}")
    
    # Submit a test task
    po_data = {
        'po_number': 'TEST002',
        'supplier': 'Test Supplier 2', 
        'url': 'https://example.com/po/TEST002'
    }
    
    try:
        # Start the pool first
        pool._running = True
        
        handle = pool.submit_task(po_data)
        print(f"Submitted task with handle: {handle.task_id}")
        
        # Check queue status after submission
        after_submit_status = pool.task_queue.get_queue_status()
        print(f"Queue status after submit: {after_submit_status}")
        
        # Try to get next task manually
        task = pool.task_queue.get_next_task("debug_worker")
        print(f"Manually got task: {task}")
        
        if task:
            print(f"Task details: po_number={task.po_data.get('po_number')}, task_id={task.task_id}")
        
        # Final status
        final_status = pool.task_queue.get_queue_status()
        print(f"Final queue status: {final_status}")
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Starting Task Queue Debug Test...")
    
    # Test 1: Basic TaskQueue
    test_task_queue_basic()
    
    # Test 2: PersistentWorkerPool task submission
    asyncio.run(test_worker_pool_task_submission())
    
    print("\nTask Queue Debug Test Complete!")