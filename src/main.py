import os
import sys
import random
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium.common.exceptions import InvalidSessionIdException, NoSuchWindowException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.core.browser import BrowserManager
from src.core.config import Config
from src.core.downloader import Downloader
from src.core.excel_processor import ExcelProcessor
from src.core.folder_hierarchy import FolderHierarchyManager


class MainApp:
    def __init__(self):
        self.excel_processor = ExcelProcessor()
        self.browser_manager = BrowserManager()
        self.folder_hierarchy = FolderHierarchyManager()
        self.driver = None
        self.lock = threading.Lock()  # Thread safety for browser operations

    def initialize_browser_once(self):
        """Initialize browser once and keep it open for all POs."""
        if not self.driver:
            print("🚀 Initializing browser for parallel processing...")
            self.browser_manager.initialize_driver()
            self.driver = self.browser_manager.driver
            print("✅ Browser initialized successfully")

    def process_single_po(self, po_data, hierarchy_cols, has_hierarchy_data, index, total):
        """Process a single PO using a new tab in the existing browser."""
        display_po = po_data['po_number']
        po_number = po_data['po_number']
        
        print(f"📋 Processing PO {index+1}/{total}: {display_po}")
        
        try:
            # Create hierarchical folder structure
            folder_path = self.folder_hierarchy.create_folder_path(
                po_data, hierarchy_cols, has_hierarchy_data
            )
            print(f"   📁 Folder: {folder_path}")
            
            # Create new tab for this PO
            with self.lock:
                # Open new tab
                self.driver.execute_script("window.open('');")
                # Switch to the new tab
                self.driver.switch_to.window(self.driver.window_handles[-1])
                
                # Update download directory for this tab
                self.driver.execute_script(f"""
                    window.localStorage.setItem('download.default_directory', '{folder_path}');
                """)
                
                # Create downloader for this tab
                downloader = Downloader(self.driver, self.browser_manager)
            
            # Process the PO
            success, message = downloader.download_attachments_for_po(po_number)
            
            # Update status
            self.excel_processor.update_po_status(
                display_po, 
                "Success" if success else "Error", 
                error_message=message,
                download_folder=folder_path
            )
            
            # Close this tab and return to main tab
            with self.lock:
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
            
            print(f"   ✅ {display_po}: {message}")
            return True
            
        except Exception as e:
            print(f"   ❌ Error processing {display_po}: {e}")
            self.excel_processor.update_po_status(display_po, "Error", error_message=str(e))
            
            # Try to close tab and return to main tab
            try:
                with self.lock:
                    if len(self.driver.window_handles) > 1:
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
                
            return False

    def run(self) -> None:
        """
        Main execution loop for processing POs with parallel tabs.
        """
        os.makedirs(Config.INPUT_DIR, exist_ok=True)
        os.makedirs(Config.DOWNLOAD_FOLDER, exist_ok=True)

        try:
            excel_path = self.excel_processor.get_excel_file_path()
            po_entries, original_cols, hierarchy_cols, has_hierarchy_data = self.excel_processor.read_po_numbers_from_excel(excel_path)
            valid_entries = self.excel_processor.process_po_numbers(po_entries)
        except Exception as e:
            print(f"❌ Failed to read or process Excel file: {e}")
            return

        if not valid_entries:
            print("No valid PO entries found to process.")
            return

        print(f"Found {len(valid_entries)} POs to process.")

        if Config.RANDOM_SAMPLE_POS and Config.RANDOM_SAMPLE_POS > 0:
            k = min(Config.RANDOM_SAMPLE_POS, len(valid_entries))
            print(f"Sampling {k} random POs for processing...")
            valid_entries = random.sample(valid_entries, k)

        # Initialize browser once
        self.initialize_browser_once()
        
        # Convert to list of PO data
        po_data_list = []
        for display_po, po_number in valid_entries:
            for entry in po_entries:
                if entry['po_number'] == display_po:
                    po_data_list.append(entry)
                    break

        print(f"🚀 Starting parallel processing with {len(po_data_list)} POs...")
        print("📊 Using browser tabs for parallel downloads")
        
        # Process POs with parallel tabs
        max_workers = min(5, len(po_data_list))  # Max 5 concurrent tabs
        successful = 0
        failed = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_po = {
                executor.submit(self.process_single_po, po_data, hierarchy_cols, has_hierarchy_data, i, len(po_data_list)): po_data
                for i, po_data in enumerate(po_data_list)
            }
            
            # Process completed tasks
            for future in as_completed(future_to_po):
                po_data = future_to_po[future]
                try:
                    result = future.result()
                    if result:
                        successful += 1
                    else:
                        failed += 1
                except Exception as e:
                    print(f"❌ Exception in {po_data['po_number']}: {e}")
                    failed += 1

        print("-" * 60)
        print(f"🎉 Processing complete!")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Total: {successful + failed}")

    def close(self):
        """Close the browser properly."""
        if self.driver:
            print("🔄 Closing browser...")
            self.browser_manager.cleanup()
            self.driver = None
            print("✅ Browser closed successfully")


if __name__ == "__main__":
    app = MainApp()
    try:
        app.run()
    finally:
        app.close()
