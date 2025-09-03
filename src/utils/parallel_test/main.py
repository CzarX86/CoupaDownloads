import os
import sys
import random
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Import from current directory
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from browser import BrowserManager
from config import Config
from downloader import Downloader
from excel_processor import ExcelProcessor
from folder_hierarchy import FolderHierarchyManager
from download_control import DownloadControlManager


class TabManager:
    """Manages browser tabs for parallel processing."""
    
    def __init__(self, driver, browser_manager, folder_manager, download_control):
        self.driver = driver
        self.browser_manager = browser_manager
        self.folder_manager = folder_manager
        self.download_control = download_control
        self.lock = threading.Lock()
        self.active_tabs: Dict[str, str] = {}  # po_number -> tab_handle
        self.download_status: Dict[str, bool] = {}  # po_number -> download_started
    
    def create_tab_for_po(self, po_number: str) -> str:
        """Create a new tab for a specific PO with download directory."""
        with self.lock:
            # Create tab with temp download directory (files will be moved later)
            download_folder = Config.DOWNLOAD_FOLDER  # Use temp folder
            
            # Create tab with specific download directory
            new_handle = self.browser_manager.create_tab_with_download_dir(download_folder)
            
            if new_handle:
                self.active_tabs[po_number] = new_handle
                self.download_status[po_number] = False
                
                # Update tab state to OPEN in CSV control
                self.download_control.update_tab_state(new_handle, "OPEN")
                
                print(f"   🆕 Created tab for {po_number}: {new_handle}")
                return new_handle
            else:
                print(f"   ❌ Failed to create tab for {po_number}")
                return None
    
    def mark_download_started(self, po_number: str):
        """Mark that download has started for a PO."""
        with self.lock:
            self.download_status[po_number] = True
            print(f"   📥 Download started for {po_number}")
    
    def close_tab_for_po(self, po_number: str, wait_for_download: bool = False):
        """Close tab for a specific PO."""
        with self.lock:
            if po_number not in self.active_tabs:
                print(f"   ⚠️ No active tab found for {po_number}")
                return
            
            tab_handle = self.active_tabs[po_number]
            
            # Update tab state to CLOSED in CSV control
            self.download_control.update_tab_state(tab_handle, "CLOSED")
            
            # If this is the last PO and we need to wait for download
            if wait_for_download:
                print(f"   ⏳ Waiting for download to complete for {po_number}...")
                time.sleep(5)  # Wait for download to finish
            
            # Switch to the tab and close it
            try:
                self.driver.switch_to.window(tab_handle)
                self.driver.close()
                
                # Switch back to main tab
                if self.driver.window_handles:
                    self.driver.switch_to.window(self.driver.window_handles[0])
                
                # Remove from tracking
                del self.active_tabs[po_number]
                del self.download_status[po_number]
                
                print(f"   🔒 Tab closed for {po_number}")
                
            except Exception as e:
                print(f"   ⚠️ Error closing tab for {po_number}: {e}")
    
    def get_active_tab_count(self) -> int:
        """Get the number of active tabs."""
        with self.lock:
            return len(self.active_tabs)
    
    def get_remaining_pos(self) -> List[str]:
        """Get list of POs that still have active tabs."""
        with self.lock:
            return list(self.active_tabs.keys())


class MainApp:
    def __init__(self):
        self.excel_processor = ExcelProcessor()
        self.browser_manager = BrowserManager()
        self.folder_manager = FolderHierarchyManager()
        self.folder_hierarchy = FolderHierarchyManager()
        self.download_control = DownloadControlManager()  # Initialize CSV control
        self.driver = None
        self.tab_manager = None
        self.lock = threading.Lock()  # Thread safety for browser operations

    def initialize_browser_once(self):
        """Initialize browser once and keep it open for all POs."""
        if not self.driver:
            print("🚀 Initializing browser for parallel processing...")
            self.browser_manager.initialize_driver()
            self.driver = self.browser_manager.driver
            self.tab_manager = TabManager(self.driver, self.browser_manager, self.folder_manager, self.download_control)
            print("✅ Browser initialized successfully")

    def process_single_po(self, po_data, hierarchy_cols, has_hierarchy_data, index, total):
        """Process a single PO using a new tab in the existing browser."""
        display_po = po_data['po_number']
        po_number = po_data['po_number']
        
        print(f"📋 Processing PO {index+1}/{total}: {display_po}")
        
        try:
            # Create hierarchical folder structure (only for display, actual folder created later with status)
            folder_path = self.folder_hierarchy.create_folder_path(
                po_data, hierarchy_cols, has_hierarchy_data
            )
            print(f"   📁 Folder: {folder_path}")
            
            # Create new tab for this PO (use temp folder for downloads)
            tab_handle = self.tab_manager.create_tab_for_po(po_number)
            
            # Create downloader for this tab
            downloader = Downloader(self.driver, self.browser_manager, self.download_control)
            
            # Process the PO with real tab ID and hierarchical folder
            success, message = downloader.download_attachments_for_po(po_number, tab_handle, folder_path)
            
            # Mark download as started
            self.tab_manager.mark_download_started(po_number)
            
            # Update status
            self.excel_processor.update_po_status(
                display_po, 
                "Success" if success else "Error", 
                error_message=message,
                download_folder=folder_path
            )
            
            # Determine if we should wait for download completion
            is_last_po = (index + 1) == total
            wait_for_download = is_last_po
            
            # Close this tab
            self.tab_manager.close_tab_for_po(po_number, wait_for_download=wait_for_download)
            
            print(f"   ✅ {display_po}: {message}")
            return True
            
        except Exception as e:
            print(f"   ❌ Error processing {display_po}: {e}")
            self.excel_processor.update_po_status(display_po, "Error", error_message=str(e))
            
            # Try to close tab
            try:
                self.tab_manager.close_tab_for_po(po_number)
            except:
                pass
                
            return False

    def run(self) -> None:
        """Main execution loop for processing POs."""
        os.makedirs(Config.INPUT_DIR, exist_ok=True)
        os.makedirs(Config.DOWNLOAD_FOLDER, exist_ok=True)

        try:
            excel_path = self.excel_processor.get_excel_file_path()
            po_entries, original_cols, hierarchy_cols, has_hierarchy_data = self.excel_processor.read_po_numbers_from_excel(excel_path)
            
            if not po_entries:
                print("❌ No POs found in Excel file")
                return
            
            # Filter POs to process
            pending_pos = [po for po in po_entries if po.get('status', 'Pending') == 'Pending']
            
            if not pending_pos:
                print("✅ All POs already processed")
                return
            
            # Apply random sample if configured
            if Config.RANDOM_SAMPLE_POS and Config.RANDOM_SAMPLE_POS != 'all':
                sample_size = int(Config.RANDOM_SAMPLE_POS)
                if len(pending_pos) > sample_size:
                    pending_pos = random.sample(pending_pos, sample_size)
                    print(f"📊 Random sample: processing {len(pending_pos)} POs")
            
            print(f"🚀 Starting parallel processing of {len(pending_pos)} POs")
            
            # Initialize browser once
            self.initialize_browser_once()
            
            # Process POs with limited parallelism - respect both MAX_WORKERS and MAX_PARALLEL_TABS
            max_workers = min(Config.MAX_WORKERS, Config.MAX_PARALLEL_TABS, len(pending_pos))
            print(f"🔄 Using {max_workers} parallel workers (max tabs: {Config.MAX_PARALLEL_TABS})")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_po = {
                    executor.submit(
                        self.process_single_po, 
                        po_data, 
                        hierarchy_cols, 
                        has_hierarchy_data, 
                        i, 
                        len(pending_pos)
                    ): po_data 
                    for i, po_data in enumerate(pending_pos)
                }
                
                # Process completed tasks
                completed = 0
                for future in as_completed(future_to_po):
                    po_data = future_to_po[future]
                    try:
                        result = future.result()
                        completed += 1
                        print(f"📈 Progress: {completed}/{len(pending_pos)} POs completed")
                        
                        # Show active tabs status
                        active_tabs = self.tab_manager.get_active_tab_count()
                        if active_tabs > 0:
                            remaining_pos = self.tab_manager.get_remaining_pos()
                            print(f"   📊 Active tabs: {active_tabs} ({', '.join(remaining_pos)})")
                        
                    except Exception as e:
                        print(f"❌ Exception for {po_data['po_number']}: {e}")
                        completed += 1
            
            # Final cleanup - ensure all tabs are closed
            print("🧹 Final cleanup - ensuring all tabs are closed...")
            remaining_pos = self.tab_manager.get_remaining_pos()
            for po_number in remaining_pos:
                print(f"   🔒 Closing remaining tab for {po_number}")
                self.tab_manager.close_tab_for_po(po_number, wait_for_download=True)
            
            print(f"✅ Parallel processing completed! {completed}/{len(pending_pos)} POs processed")
            
        except Exception as e:
            print(f"❌ Error in main execution: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            # Close browser
            if self.driver:
                print("🧹 Closing browser...")
                self.browser_manager.cleanup()


if __name__ == "__main__":
    app = MainApp()
    app.run()
