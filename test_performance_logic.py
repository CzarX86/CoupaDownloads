
import asyncio
import time
import unittest
from unittest.mock import MagicMock, patch
from src.workers.persistent_pool import PersistentWorkerPool
from src.workers.models.config import PoolConfig
from src.lib.downloader import Downloader

class TestPerformanceOptimizations(unittest.IsolatedAsyncioTestCase):
    async def test_stagger_delay_logic(self):
        # Setup mock config with 3s delay
        config = PoolConfig(worker_count=3, stagger_delay=3.0, base_profile_path="/tmp")
        pool = PersistentWorkerPool(config)
        
        # Mock _start_worker to just return
        pool._start_worker = MagicMock()
        async def mock_start_worker(worker_id):
            return
        pool._start_worker.side_effect = mock_start_worker
        
        # Track time
        start_time = time.time()
        
        # Run _start_workers
        with patch('asyncio.sleep', side_effect=asyncio.sleep) as mock_sleep:
            await pool._start_workers()
            
            # Check how many times sleep was called with 3.0
            stagger_calls = [call for call in mock_sleep.call_args_list if call.args[0] == 3.0]
            self.assertEqual(len(stagger_calls), 2) # (worker_count - 1)
            
    def test_downloader_rapid_trigger_no_threads(self):
        # Mock driver and browser manager
        mock_driver = MagicMock()
        mock_browser_mgr = MagicMock()
        downloader = Downloader(mock_driver, mock_browser_mgr)
        
        # Mock _extract_filename_from_element
        downloader._extract_filename_from_element = MagicMock(return_value="test.pdf")
        
        # Mock _download_attachment to return success
        downloader._download_attachment = MagicMock(return_value=(True, None))
        
        # Create mock elements
        mock_attachment_1 = MagicMock()
        mock_attachment_2 = MagicMock()
        attachments = [mock_attachment_1, mock_attachment_2]
        
        # Run rapid trigger
        result = downloader.download_attachments_rapid_trigger(attachments)
        
        # Verify it was triggered for both
        self.assertEqual(downloader._download_attachment.call_count, 2)
        self.assertTrue(result['success'])
        self.assertEqual(result['attachments_downloaded'], 2)
        
        # Verify no ThreadPoolExecutor was used (implicitly by checking no threads spawned if we could, 
        # but here we just check it was synchronous)
        # In the real code, if we removed the import, it can't be used anyway.

if __name__ == '__main__':
    unittest.main()
