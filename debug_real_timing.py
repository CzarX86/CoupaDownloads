#!/usr/bin/env python3
"""
Debug script to test the actual worker pool with real timing.
"""

import sys
import asyncio
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "EXPERIMENTAL"))

from workers.persistent_pool import PersistentWorkerPool
from workers.models.config import PoolConfig


async def test_real_timing():
    """Test the real timing of worker startup and task processing."""
    print("=== Testing Real Worker Pool Timing ===")
    
    # Create config similar to production
    config = PoolConfig(
        worker_count=2,
        headless_mode=True,
        base_profile_path="/Users/juliocezar/Dev/work/CoupaDownloads/storage/browser_profiles",
        memory_threshold=0.8,
        shutdown_timeout=30
    )
    
    pool = PersistentWorkerPool(config)
    
    print("1. Starting worker pool...")
    start_time = time.time()
    await pool.start()
    startup_time = time.time() - start_time
    print(f"   Worker pool started in {startup_time:.2f} seconds")
    
    # Check initial status
    status = pool.task_queue.get_queue_status()
    print(f"2. Initial queue status: {status}")
    
    # Create test tasks
    test_tasks = []
    for i in range(3):
        test_tasks.append({
            'po_number': f'TEST{i+1:03d}',
            'supplier': f'Test Supplier {i+1}',
            'url': f'https://unilever.coupahost.com/po/TEST{i+1:03d}'
        })
    
    print(f"3. Submitting {len(test_tasks)} tasks...")
    submit_time = time.time()
    handles = pool.submit_tasks(test_tasks)
    submit_duration = time.time() - submit_time
    print(f"   Tasks submitted in {submit_duration:.3f} seconds")
    
    # Check status after submission
    status_after_submit = pool.task_queue.get_queue_status()
    print(f"4. Status after submit: {status_after_submit}")
    
    # Wait a bit and check again
    print("5. Waiting 2 seconds and checking status...")
    await asyncio.sleep(2)
    status_after_wait = pool.task_queue.get_queue_status()
    print(f"   Status after 2s wait: {status_after_wait}")
    
    # Wait for completion with timeout
    print("6. Waiting for completion...")
    completion_start = time.time()
    completed = await pool.wait_for_completion(timeout=60)
    completion_time = time.time() - completion_start
    
    print(f"   Completion result: {completed}")
    print(f"   Completion wait time: {completion_time:.2f} seconds")
    
    # Final status
    final_status = pool.task_queue.get_queue_status()
    print(f"7. Final queue status: {final_status}")
    
    # Shutdown
    print("8. Shutting down...")
    await pool.shutdown()
    
    print("Test completed!")


if __name__ == "__main__":
    asyncio.run(test_real_timing())