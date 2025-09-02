"""
Main module for Coupa Downloads automation.
Orchestrates the entire workflow using modular components with enhanced folder hierarchy.
"""

import os
from core.browser import BrowserManager
from core.config import Config
from core.excel_processor import ExcelProcessor
from core.downloader import DownloadManager, LoginManager
from core.progress_manager import progress_manager
from core.driver_manager import DriverManager


class CoupaDownloader:
    """Main orchestrator class following Single Responsibility Principle."""

    def __init__(self):
        self.browser_manager = BrowserManager()
        self.driver = None
        self.download_manager = None
        self.login_manager = None
        self.excel_processor = ExcelProcessor()

    def setup(self) -> None:
        """Setup the downloader with browser and managers."""
        # Ensure download folder exists
        Config.ensure_download_folder_exists()

        # Debug: Print driver detection info
        print("🔍 Debug: Driver detection info")
        driver_manager = DriverManager()
        print(f"  Drivers directory: {driver_manager.drivers_dir}")
        print(f"  Platform: {driver_manager.platform}")
        
        edge_version = driver_manager.get_edge_version()
        print(f"  Edge version: {edge_version}")
        
        candidates = driver_manager._scan_local_drivers()
        print(f"  Driver candidates: {candidates}")
        
        compatible = driver_manager._find_compatible_local_driver()
        print(f"  Compatible driver: {compatible}")

        # Start browser
        self.driver = self.browser_manager.start(headless=Config.HEADLESS)

        # Initialize managers
        self.download_manager = DownloadManager(self.driver)
        self.login_manager = LoginManager(self.driver)

    def process_po_numbers(self) -> list:
        """Process PO numbers from Excel file with hierarchy support."""
        excel_file_path = self.excel_processor.get_excel_file_path()
        
        # Check if Excel file exists
        if not os.path.exists(excel_file_path):
            raise FileNotFoundError(f"Excel file not found: {excel_file_path}")
        
        try:
            # Read Excel file with hierarchy analysis
            po_entries, original_cols, hierarchy_cols, has_hierarchy_data = self.excel_processor.read_po_numbers_from_excel(excel_file_path)
            
            # Process and validate PO numbers
            valid_entries = self.excel_processor.process_po_numbers(po_entries)
            
            # Store hierarchy information for later use
            self.hierarchy_cols = hierarchy_cols
            self.has_hierarchy_data = has_hierarchy_data
            self.po_entries = po_entries  # Store full PO data for hierarchy creation

            # Limit number of POs processed if configured
            if Config.PROCESS_MAX_POS is not None:
                valid_entries = valid_entries[:Config.PROCESS_MAX_POS]
                print(f"⚡ Limiting to top {Config.PROCESS_MAX_POS} POs for this run.")

            if not valid_entries:
                print("❌ No valid PO numbers provided.")
                return []

            print(f"📋 Processing {len(valid_entries)} PO(s)...")
            if Config.VERBOSE_OUTPUT:
                print(f"   PO list: {[entry[0] for entry in valid_entries]}")
            return valid_entries
            
        except Exception as e:
            print(f"❌ Error processing Excel file: {e}")
            raise

    def handle_login_first(self) -> bool:
        """Handle login before processing POs."""
        try:
            print("🔐 Checking login status...")
            if self.login_manager.is_logged_in():
                print("✅ Already logged in")
                return True
            else:
                print("🔐 Login required")
                return self.login_manager.handle_login()
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False

    def run(self) -> None:
        """Main execution method with enhanced folder hierarchy."""
        try:
            # Setup
            self.setup()
            
            # Get PO numbers to process
            valid_entries = self.process_po_numbers()
            
            if not valid_entries:
                print("❌ No valid PO numbers found to process")
                return
            
            # Handle login if needed
            if not self.handle_login_first():
                print("❌ Login failed, cannot proceed")
                return
            
            # Process each PO
            for display_po, clean_po in valid_entries:
                # Find the full PO data for hierarchy
                po_data = self._find_po_data_by_number(display_po)
                
                if not po_data:
                    print(f"⚠️ Could not find PO data for {display_po}, skipping")
                    continue
                
                try:
                    # Download attachments with hierarchy support
                    downloaded_files = self.download_manager.download_attachments_for_po(
                        display_po, clean_po, po_data, self.hierarchy_cols, self.has_hierarchy_data
                    )
                    
                    # Log download results
                    if downloaded_files:
                        print(f"  📎 Downloaded {len(downloaded_files)} files for {display_po}")
                    else:
                        print(f"  📭 No files downloaded for {display_po}")
                        
                except Exception as e:
                    if "login" in str(e).lower():
                        print("🔐 Login required - attempting login...")
                        if self.login_manager.handle_login():
                            # Retry the download
                            downloaded_files = self.download_manager.download_attachments_for_po(
                                display_po, clean_po, po_data, self.hierarchy_cols, self.has_hierarchy_data
                            )
                        else:
                            print("❌ Login retry failed")
                    else:
                        print(f"❌ Error processing {display_po}: {e}")
            
            # Print summary
            self.excel_processor.print_summary_report()
            
        except KeyboardInterrupt:
            print("\n⏹️ Process interrupted by user")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if self.driver and Config.CLOSE_BROWSER_AFTER_EXECUTION:
                self.driver.quit()

    def _find_po_data_by_number(self, po_number: str) -> dict:
        """Find PO data by PO number from the stored entries."""
        for entry in self.po_entries:
            if entry['po_number'] == po_number:
                return entry
        return None


def main():
    """Main entry point."""
    downloader = CoupaDownloader()
    downloader.run()


if __name__ == "__main__":
    main()
