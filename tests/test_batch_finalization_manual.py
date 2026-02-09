
import os
import shutil
import time
import uuid
import threading
from typing import Dict, Any, List

import structlog
from src.workers.persistent_pool import PersistentWorkerPool
from src.workers.models import PoolConfig, TaskPriority, TaskStatus, WorkerStatus
from src.lib.config import Config

# Configure logging
structlog.configure()
logger = structlog.get_logger()

# Test directory
TEST_DL_ROOT = os.path.abspath("./test_downloads_batch")

def setup_test_env():
    if os.path.exists(TEST_DL_ROOT):
        shutil.rmtree(TEST_DL_ROOT)
    os.makedirs(TEST_DL_ROOT)
    os.makedirs(os.path.join(TEST_DL_ROOT, "profiles"))
    Config.DOWNLOAD_FOLDER = TEST_DL_ROOT
    Config.BATCH_FINALIZATION_ENABLED = True
    Config.BATCH_FINALIZATION_INTERVAL = 5 # Short interval for testing

def cleanup_test_env():
    # if os.path.exists(TEST_DL_ROOT):
    #     shutil.rmtree(TEST_DL_ROOT)
    pass

class MockDownloader:
    def __init__(self, *args, **kwargs):
        pass
    def download_attachments_for_po(self, po_number, on_attachments_found=None):
        logger.info("Mock downloader processing PO", po=po_number)
        
        # Simulate JIT callback trigger
        if on_attachments_found:
            data = {
                'supplier_name': 'Test Supplier',
                'attachments_found': 2,
                'status_code': 'PROCESSING',
                'po_number': po_number
            }
            path = on_attachments_found(data)
            logger.info("JIT folder created", path=path)
            
            # Create dummy files
            os.makedirs(path, exist_ok=True)
            with open(os.path.join(path, "test_file.txt"), "w") as f:
                f.write("test content")
        
        return {
            'success': True,
            'status_code': 'COMPLETED',
            'attachments_downloaded': 1,
            'files': ['test_file.txt'],
            'final_folder': path if 'path' in locals() else None
        }

def mock_process_single_po(po_number, po_data, driver, browser_manager, **kwargs):
    logger.info("Mock process_single_po called", po=po_number)
    
    # Simulate JIT folder creation if callback provided
    path = os.path.join(TEST_DL_ROOT, f"{po_number}__WORK")
    if 'progress_callback' in kwargs:
        cb = kwargs['progress_callback']
        # The callback is actually a ProgressBridge, we need to find how it's called
        pass
    
    # Let's just create the folder manually to simulate what happened
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "dummy.txt"), "w") as f:
        f.write("dummy")
        
    return {
        'success': True,
        'status_code': 'COMPLETED',
        'attachments_downloaded': 1,
        'files': ['dummy.txt'],
        'final_folder': path
    }

def run_test():
    setup_test_env()
    
    config = PoolConfig(
        worker_count=2,
        download_root=TEST_DL_ROOT,
        base_profile_path=os.path.join(TEST_DL_ROOT, "profiles"),
        headless_mode=True
    )
    
    # Monkeypatch WorkerProcess._process_po_task to use our mock
    import src.workers.worker_process
    original_process = src.workers.worker_process.process_single_po
    src.workers.worker_process.process_single_po = mock_process_single_po
    
    # Also skip browser initialization for speed
    def mock_init_browser(self):
        class MockDriver:
            def __init__(self):
                self.current_url = "https://example.com"
                self.title = "Mock Title"
                self.current_window_handle = "main"
                self.window_handles = ["main"]
            def execute_cdp_cmd(self, *args, **kwargs): pass
            @property
            def switch_to(self):
                return type('MockSwitchTo', (), {'window': lambda *args: None})()
            def quit(self): pass
            def close(self): pass
            
        class MockSession:
            def __init__(self):
                self.driver = MockDriver()
                self.main_window_handle = "main"
                self.keeper_handle = "main"
                self.active_tabs = {}
            def authenticate(self): return True
            def ensure_keeper_tab(self): pass
            def focus_main_window(self): pass
            def create_tab(self, *args):
                tid = args[0] if args else "unknown"
                self.active_tabs[tid] = type('MockTab', (), {'assign_po': lambda *a: None})()
                return "tab_handle"
            def close_tab(self, *args): pass

        self.browser_session = MockSession()
        self._running = True
        self.worker.status = WorkerStatus.READY
    
    src.workers.worker_process.WorkerProcess._initialize_browser_session = mock_init_browser
    src.workers.worker_process.WorkerProcess._validate_webdriver_health = lambda self, driver: True

    pool = PersistentWorkerPool(config)
    
    import asyncio
    
    async def main():
        await pool.start()
        
        # Submit a task
        po_data = {'po_number': 'PO123', 'Supplier': 'Test Supplier'}
        handle = pool.submit_task(po_data)
        
        print(f"Task submitted: {handle.task_id}")
        
        # Wait for task to reach READY_TO_FINALIZE
        start_wait = time.time()
        while time.time() - start_wait < 10:
            status = handle.get_status()['status']
            if status == 'ready_to_finalize':
                print("Task reached READY_TO_FINALIZE state!")
                # Verify folder exists with __WORK suffix
                folders = os.listdir(TEST_DL_ROOT)
                print(f"Folders in root: {folders}")
                break
            await asyncio.sleep(0.5)
        
        # Wait for batch finalizer to process it
        print("Waiting for batch finalizer...")
        start_wait = time.time()
        while time.time() - start_wait < 15:
            status = handle.get_status()['status']
            if status == 'completed':
                print("Task reached COMPLETED state after batch finalization!")
                # Verify folder is renamed
                folders = os.listdir(TEST_DL_ROOT)
                print(f"Folders in root after finalization: {folders}")
                break
            await asyncio.sleep(1)
            
        await pool.shutdown()
        print("Test complete.")

    asyncio.run(main())
    
    # Restore original
    src.workers.worker_process.process_single_po = original_process

if __name__ == "__main__":
    run_test()
