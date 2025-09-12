import os
import sys
import random
import time
import threading
import pandas as pd
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
    
    def wait_for_downloads_completion(self, po_number: str, timeout: int = 60):
        """Wait for all downloads for a specific PO to complete."""
        if po_number not in self.active_tabs:
            print(f"   ⚠️ No active tab found for {po_number}")
            return False
        
        tab_handle = self.active_tabs[po_number]
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check if all downloads for this tab are complete
            if self.download_control.is_tab_complete(tab_handle):
                elapsed = int(time.time() - start_time)
                print(f"   ✅ All downloads completed for {po_number} (took {elapsed}s)")
                return True
            
            # Check for ongoing downloads
            tab_downloads = self.download_control.get_tab_downloads(tab_handle)
            downloading_count = sum(1 for record in tab_downloads if record.status == "DOWNLOADING")
            
            if downloading_count > 0:
                elapsed = int(time.time() - start_time)
                print(f"   ⏳ {downloading_count} download(s) in progress for {po_number} ({elapsed}s)...")
            
            time.sleep(2)
        
        print(f"   ⚠️ Timeout waiting for downloads to complete for {po_number} ({timeout}s)")
        return False
    
    def close_tab_for_po(self, po_number: str, wait_for_download: bool = False):
        """Close tab for a specific PO with enhanced error handling."""
        with self.lock:
            if po_number not in self.active_tabs:
                print(f"   ⚠️ No active tab found for {po_number}")
                return
            
            tab_handle = self.active_tabs[po_number]
            
            # Update tab state to CLOSED in CSV control
            try:
                self.download_control.update_tab_state(tab_handle, "CLOSED")
            except Exception as e:
                print(f"   ⚠️ Warning: Could not update CSV tab state: {e}")
            
            # If this is the last PO and we need to wait for download
            if wait_for_download:
                print(f"   ⏳ Waiting for download to complete for {po_number}...")
                time.sleep(5)  # Wait for download to finish
            
            # Enhanced tab closing with multiple strategies
            try:
                # Strategy 1: Check if tab still exists
                if tab_handle not in self.driver.window_handles:
                    print(f"   ℹ️ Tab {tab_handle} already closed for {po_number}")
                    # Remove from tracking even if tab was already closed
                    if po_number in self.active_tabs:
                        del self.active_tabs[po_number]
                    if po_number in self.download_status:
                        del self.download_status[po_number]
                    return
                
                # Strategy 2: Try to switch to tab and close it
                try:
                    self.driver.switch_to.window(tab_handle)
                    self.driver.close()
                    print(f"   🔒 Tab closed for {po_number}")
                    
                except Exception as switch_error:
                    print(f"   ⚠️ Could not switch to tab {tab_handle}: {switch_error}")
                    
                    # Strategy 3: Try to close tab by executing JavaScript
                    try:
                        self.driver.execute_script(f"window.open('', '{tab_handle}').close();")
                        print(f"   🔒 Tab closed via JavaScript for {po_number}")
                    except Exception as js_error:
                        print(f"   ⚠️ JavaScript close failed: {js_error}")
                        
                        # Strategy 4: Force close by removing from window handles tracking
                        print(f"   ⚠️ Tab {po_number} may be in inconsistent state")
                
                # Switch back to main tab if available
                try:
                    if self.driver.window_handles:
                        self.driver.switch_to.window(self.driver.window_handles[0])
                    else:
                        print(f"   ⚠️ No windows available after closing tab")
                except Exception as switch_back_error:
                    print(f"   ⚠️ Could not switch back to main tab: {switch_back_error}")
                
                # Remove from tracking
                if po_number in self.active_tabs:
                    del self.active_tabs[po_number]
                if po_number in self.download_status:
                    del self.download_status[po_number]
                
            except Exception as e:
                print(f"   ❌ Error closing tab for {po_number}: {e}")
                # Still try to remove from tracking even if close failed
                try:
                    if po_number in self.active_tabs:
                        del self.active_tabs[po_number]
                    if po_number in self.download_status:
                        del self.download_status[po_number]
                except:
                    pass
    
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
        """Process a single PO using a new tab in the existing browser with enhanced error handling."""
        display_po = po_data['po_number']
        po_number = po_data['po_number']
        
        print(f"📋 Processing PO {index+1}/{total}: {display_po}")
        
        # Enhanced error tracking
        max_retries = 2
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                # Create hierarchical folder structure (only for display, actual folder created later with status)
                folder_path = self.folder_hierarchy.create_folder_path(
                    po_data, hierarchy_cols, has_hierarchy_data
                )
                print(f"   📁 Folder: {folder_path}")
                
                # Enhanced tab creation with retry logic
                tab_handle = None
                for tab_attempt in range(3):  # Try up to 3 times to create tab
                    try:
                        tab_handle = self.tab_manager.create_tab_for_po(po_number)
                        if tab_handle:
                            break
                        else:
                            print(f"   ⚠️ Tab creation attempt {tab_attempt + 1} failed, retrying...")
                            time.sleep(1)
                    except Exception as e:
                        print(f"   ⚠️ Tab creation error (attempt {tab_attempt + 1}): {e}")
                        if tab_attempt < 2:
                            time.sleep(2)
                        else:
                            raise e
                
                if not tab_handle:
                    raise Exception("Failed to create tab after multiple attempts")
                
                # Create downloader for this tab
                downloader = Downloader(self.driver, self.browser_manager, self.download_control)
                
                # Enhanced PO processing with better error handling
                success, message = downloader.download_attachments_for_po(po_number, tab_handle, folder_path)
                
                # Mark download as started
                self.tab_manager.mark_download_started(po_number)
                
                # Get additional information for Excel update
                supplier = po_data.get('supplier', '')
                attachments_found = po_data.get('attachments_found', 0)
                attachments_downloaded = po_data.get('attachments_downloaded', 0)
                coupa_url = f"{Config.BASE_URL}/order_headers/{po_number}"
                attachment_names = po_data.get('attachment_names', '')
                
                # Enhanced Excel update with retry logic
                excel_updated = False
                for excel_attempt in range(3):  # Try up to 3 times to update Excel
                    try:
                        self.excel_processor.update_po_status(
                            display_po, 
                            "Success" if success else "Error", 
                            supplier=supplier,
                            attachments_found=attachments_found,
                            attachments_downloaded=attachments_downloaded,
                            error_message=message,
                            download_folder=folder_path,
                            coupa_url=coupa_url,
                            attachment_names=attachment_names
                        )
                        excel_updated = True
                        break
                    except Exception as e:
                        print(f"   ⚠️ Excel update error (attempt {excel_attempt + 1}): {e}")
                        if excel_attempt < 2:
                            time.sleep(2)
                        else:
                            print(f"   ❌ Failed to update Excel after multiple attempts")
                
                # Wait for downloads to complete before closing tab
                print(f"   ⏳ Waiting for downloads to complete for {po_number}...")
                self.tab_manager.wait_for_downloads_completion(po_number, timeout=60)
                
                # Enhanced tab closing with better error handling
                try:
                    self.tab_manager.close_tab_for_po(po_number, wait_for_download=True)
                except Exception as e:
                    print(f"   ⚠️ Warning: Error closing tab for {po_number}: {e}")
                
                print(f"   ✅ {display_po}: {message}")
                return True
                
            except Exception as e:
                retry_count += 1
                error_msg = str(e)
                
                # Enhanced error categorization
                if "no such window" in error_msg.lower():
                    error_category = "WINDOW_CLOSED"
                elif "no such element" in error_msg.lower():
                    error_category = "ELEMENT_NOT_FOUND"
                elif "timeout" in error_msg.lower():
                    error_category = "TIMEOUT"
                elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                    error_category = "NETWORK_ERROR"
                else:
                    error_category = "UNKNOWN_ERROR"
                
                print(f"   ❌ Error processing {display_po} (attempt {retry_count}/{max_retries + 1}): {error_msg}")
                print(f"   📊 Error category: {error_category}")
                
                # Try to close tab on error
                try:
                    self.tab_manager.close_tab_for_po(po_number)
                except:
                    pass
                
                # If this is the last retry, update Excel with error and return False
                if retry_count > max_retries:
                    try:
                        self.excel_processor.update_po_status(
                            display_po, 
                            "Error", 
                            error_message=f"{error_category}: {error_msg}",
                            coupa_url=f"{Config.BASE_URL}/order_headers/{po_number}"
                        )
                    except:
                        print(f"   ❌ Failed to update Excel with error status")
                    
                    return False
                else:
                    # Wait before retry with exponential backoff
                    wait_time = 2 ** retry_count
                    print(f"   ⏳ Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    
                    # Try to recover by creating a new tab
                    try:
                        # Clean up any existing tab for this PO
                        self.tab_manager.close_tab_for_po(po_number)
                        time.sleep(1)
                    except:
                        pass
                    
                    print(f"   🔄 Retrying {display_po}...")
                    continue
        
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
            
            # Filter POs to process - include POs with 'Pending' status or nan/empty status
            pending_pos = [po for po in po_entries if po.get('status', 'Pending') == 'Pending' or pd.isna(po.get('status')) or po.get('status') == '']
            
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
