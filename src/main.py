"""
Main module for Coupa Downloads automation.
Orchestrates the entire workflow using modular components.
"""

from core.browser import BrowserManager
from core.config import Config
from core.unified_processor import UnifiedProcessor
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
        """Process PO numbers from input file (CSV or Excel)."""
        input_file_path = UnifiedProcessor.detect_input_file()
        po_entries = UnifiedProcessor.read_po_numbers(input_file_path)
        valid_entries = UnifiedProcessor.process_po_numbers(input_file_path)

        # Limit number of POs processed if configured
        from core.config import Config
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

    def handle_login_first(self) -> bool:
        """Handle login before processing any POs to prevent race conditions."""
        print("🔐 Checking login status...")
        
        try:
            # Navigate to neutral page first (not a specific PO)
            print("🌐 Navigating to Coupa homepage...")
            if self.driver:
                self.driver.get("https://unilever.coupahost.com")
            else:
                raise RuntimeError("Browser driver not initialized")
            
            # Check if already logged in
            if self.login_manager and self.login_manager.is_logged_in():
                print("✅ Already logged in - proceeding with downloads")
                return True
            else:
                print("🔐 Login required - please log in now...")
                # Wait for login completion
                if self.login_manager:
                    self.login_manager.ensure_logged_in()
                    print("✅ Login completed successfully!")
                    return True
                else:
                    raise RuntimeError("Login manager not initialized")

        except Exception as login_error:
            print(f"❌ Login failed: {login_error}")
            print("💡 Please ensure you're logged into Coupa before running the script.")
            return False

    def download_attachments(self, valid_entries: list) -> None:
        """Download attachments for all valid PO numbers after login is confirmed."""
        if not self.login_manager or not self.download_manager:
            raise RuntimeError("Managers not initialized. Call setup() first.")

        # STEP 1: Handle login FIRST before processing any POs
        if not self.handle_login_first():
            return

        # STEP 1.5: Ask user about MSG file processing
        msg_processing_enabled = self._ask_user_about_msg_processing()
        
        # STEP 2: Process all POs with browser session recovery
        progress_manager.start_processing(len(valid_entries))
        
        for i, (display_po, clean_po) in enumerate(valid_entries):
            try:
                # Start PO processing with progress indicator
                progress_manager.start_po(display_po)
                
                # Check if browser session is still valid
                if not self._is_browser_session_valid():
                    print("   ⚠️ Browser session lost, attempting to recover...")
                    if not self._recover_browser_session():
                        print("   ❌ Could not recover browser session, stopping processing")
                        break
                
                # Process the PO in the current tab (main tab)
                self.download_manager.download_attachments_for_po(display_po, clean_po, msg_processing_enabled)
                
            except Exception as download_error:
                if Config.VERBOSE_OUTPUT:
                    print(f"   ❌ PO #{display_po} failed with error: {download_error}")
                else:
                    print(f"   ❌ PO #{display_po} failed")
                
                # Check if it's a browser session error
                if "no such window" in str(download_error).lower() or "target window already closed" in str(download_error).lower():
                    print("🔄 Browser session error detected, attempting recovery...")
                    if not self._recover_browser_session():
                        print("❌ Could not recover browser session, stopping processing")
                        break
                
                # Continue with next PO
        
        # STEP 3: Navigate back to home page after processing all POs
        print(f"\n🏠 Navigating back to Coupa homepage...")
        try:
            if self.driver and self._is_browser_session_valid():
                self.driver.get("https://unilever.coupahost.com")
                print("✅ Successfully returned to Coupa homepage")
        except Exception as home_error:
            print(f"⚠️ Warning: Could not navigate back to homepage: {home_error}")
    
    def _is_browser_session_valid(self) -> bool:
        """Check if the browser session is still valid."""
        if not self.driver:
            return False
        
        try:
            # Try to get the current URL to test if session is still valid
            self.driver.current_url
            return True
        except Exception:
            return False
    
    def _ask_user_about_msg_processing(self) -> bool:
        """Ask user if they want to automatically process MSG files."""
        print("\n📧 MSG File Processing Options")
        print("=" * 40)
        print("Would you like to automatically process .msg files?")
        print("This will:")
        print("  • Convert .msg files to PDF format")
        print("  • Extract any attachments from .msg files")
        print("  • Create subfolders named after the original .msg file")
        print("  • Organize attachments in these subfolders")
        print()
        
        while True:
            try:
                response = input("Enable MSG processing? (y/n): ").strip().lower()
                if response in ['y', 'yes', '1']:
                    print("✅ MSG processing enabled")
                    return True
                elif response in ['n', 'no', '0']:
                    print("⏭️ MSG processing disabled")
                    return False
                else:
                    print("❌ Please enter 'y' for yes or 'n' for no")
            except KeyboardInterrupt:
                print("\n⏭️ MSG processing disabled (user cancelled)")
                return False
            except Exception as e:
                print(f"❌ Error reading input: {e}")
                return False

    def _recover_browser_session(self) -> bool:
        """Attempt to recover the browser session by restarting the browser."""
        try:
            print("🔄 Restarting browser session...")
            
            # Clean up old session
            if self.browser_manager:
                self.browser_manager.force_cleanup()
            
            # Restart browser
            self.driver = self.browser_manager.start(headless=Config.HEADLESS)
            
            # Reinitialize managers with new driver
            self.download_manager = DownloadManager(self.driver)
            self.login_manager = LoginManager(self.driver)
            
            # Try to handle login again
            if self.handle_login_first():
                print("✅ Browser session recovered successfully")
                return True
            else:
                print("❌ Could not log in after browser recovery")
                return False
                
        except Exception as e:
            print(f"❌ Failed to recover browser session: {e}")
            return False

    def run(self) -> None:
        """Main execution method."""
        try:
            print("🚀 Starting Coupa Downloader...")
            
            # Create backup of input file before processing
            UnifiedProcessor.backup_file()
            
            self.setup()
            valid_entries = self.process_po_numbers()
            
            if not valid_entries:
                print("📭 No POs to process.")
                return
            
            self.download_attachments(valid_entries)
            
            # Generate final summary report
            progress_manager.processing_completed()
            UnifiedProcessor.print_summary_report()
            
        except KeyboardInterrupt:
            print("\nScript interrupted by user.")
        except Exception as e:
            from core.config import Config

            print(f"Unexpected error: {e}")
            # Optionally suppress Edge WebDriver crash stacktrace
            if not Config.SHOW_EDGE_CRASH_STACKTRACE:
                import sys
                import traceback

                exc_type, exc_value, exc_tb = sys.exc_info()
                tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
                filtered_tb = [line for line in tb_lines if "edgedriver" not in line]
                print("".join(filtered_tb))
        finally:
            from core.config import Config
            print(f"[DEBUG] CLOSE_BROWSER_AFTER_EXECUTION: {Config.CLOSE_BROWSER_AFTER_EXECUTION}")
            print(f"[DEBUG] KEEP_BROWSER_OPEN: {Config.KEEP_BROWSER_OPEN}")
            if Config.CLOSE_BROWSER_AFTER_EXECUTION:
                self.browser_manager.cleanup()
                print("✅ Browser closed after execution (per config).")
            elif Config.KEEP_BROWSER_OPEN:
                # Ensure browser is on homepage before leaving open
                try:
                    if self.driver and self._is_browser_session_valid():
                        self.driver.get("https://unilever.coupahost.com")
                        print("✅ Browser parked on Coupa homepage for session persistency")
                except Exception as e:
                    print(f"⚠️ Could not park browser on homepage: {e}")
                self.browser_manager.keep_browser_open()
            else:
                self.browser_manager.cleanup()


def main() -> None:
    """Main entry point."""
    downloader = CoupaDownloader()
    downloader.run()


if __name__ == "__main__":
    main()
