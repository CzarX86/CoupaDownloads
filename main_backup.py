"""
Main module for Coupa Downloads automation.
Orchestrates the entire workflow using modular components.
"""

from browser import BrowserManager
from config import Config
from csv_processor import CSVProcessor
from downloader import DownloadManager, LoginManager


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

        # Start browser
        self.driver = self.browser_manager.start(headless=Config.HEADLESS)

        # Initialize managers
        self.download_manager = DownloadManager(self.driver)
        self.login_manager = LoginManager(self.driver)

    def process_po_numbers(self) -> list:
        """Process PO numbers from CSV file."""
        csv_file_path = CSVProcessor.get_csv_file_path()
        po_entries = CSVProcessor.read_po_numbers_from_csv(csv_file_path)
        valid_entries = CSVProcessor.process_po_numbers(po_entries)

        if not valid_entries:
            print("❌ No valid PO numbers provided.")
            return []

        print(
            f"Processing {len(valid_entries)} PO(s): {[entry[0] for entry in valid_entries]}"
        )
        return valid_entries

    def download_attachments(self, valid_entries: list) -> None:
        """Download attachments for all valid PO numbers with login retry mechanism."""
        if not self.login_manager or not self.download_manager:
            raise RuntimeError("Managers not initialized. Call setup() first.")

        # Track POs that fail due to login issues for retry
        login_failed_pos = []
        login_completed = False

        for display_po, clean_po in valid_entries:
            # Check if we need to handle login
            if not login_completed:
                try:
                    # Check if already logged in
                    if self.login_manager.is_logged_in():
                        print("🔐 Already logged in - proceeding with downloads")
                        login_completed = True
                    else:
                        # Try to ensure login
                        self.login_manager.ensure_logged_in()
                        login_completed = True
                        print("🔐 Login completed successfully!")
                    
                    # If we have any POs that failed due to login, retry them now
                    if login_failed_pos:
                        print(f"🔄 Retrying {len(login_failed_pos)} POs that failed due to login...")
                        for retry_po, retry_clean_po in login_failed_pos:
                            print(f"  🔄 Retrying PO #{retry_po}...")
                            try:
                                self.download_manager.download_attachments_for_po(retry_po, retry_clean_po)
                            except Exception as retry_error:
                                error_msg = str(retry_error).lower()
                                if "login" in error_msg or "authentication" in error_msg or "sign_in" in error_msg:
                                    print(f"    🔐 PO #{retry_po} still failing due to login - will need manual intervention")
                                else:
                                    print(f"    ❌ PO #{retry_po} failed with different error: {retry_error}")
                        login_failed_pos.clear()  # Clear the retry list
                        
                except Exception as login_error:
                    print(f"🔐 Login still required: {login_error}")
                    # Continue with current PO, it will likely fail due to login

            # Download attachments for this PO
            try:
                self.download_manager.download_attachments_for_po(display_po, clean_po)
            except Exception as download_error:
                error_msg = str(download_error).lower()
                if "login" in error_msg or "authentication" in error_msg or "sign_in" in error_msg:
                    print(f"  🔐 PO #{display_po} failed due to login - will retry after login")
                    login_failed_pos.append((display_po, clean_po))
                else:
                    print(f"  ❌ PO #{display_po} failed with error: {download_error}")

        # If we still have POs that failed due to login after processing all entries
        if login_failed_pos and not login_completed:
            print(f"\n⚠️ {len(login_failed_pos)} POs failed due to login issues:")
            for po, _ in login_failed_pos:
                print(f"  • PO #{po}")
            print("💡 Please run the script again after logging in manually.")
        elif login_failed_pos:
            print(f"\n⚠️ {len(login_failed_pos)} POs still failed after login retry:")
            for po, _ in login_failed_pos:
                print(f"  • PO #{po}")
            print("💡 These POs may need manual investigation.")

    def run(self) -> None:
        """Main execution method."""
        try:
            print("🚀 Starting Coupa Downloader...")
            
            # Create backup of CSV before processing
            CSVProcessor.backup_csv()
            
            self.setup()
            valid_entries = self.process_po_numbers()
            
            if not valid_entries:
                print("📭 No POs to process.")
                return
            
            print(f"\n🎯 Processing {len(valid_entries)} POs...")
            self.download_attachments(valid_entries)
            
            # Generate final summary report
            print("\n🎉 Processing completed!")
            CSVProcessor.print_summary_report()
            
        except KeyboardInterrupt:
            print("\nScript interrupted by user.")
        except Exception as e:
            from config import Config

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
            self.browser_manager.cleanup()


def main() -> None:
    """Main entry point."""
    downloader = CoupaDownloader()
    downloader.run()


if __name__ == "__main__":
    main()
