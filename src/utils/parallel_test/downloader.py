import os
import time
from typing import List, Optional, Tuple
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException

from browser import BrowserManager
from config import Config
from download_control import DownloadControlManager


class Downloader:
    """
    Handles downloading attachments for a given PO number.
    This simplified version uses direct clicks and robust waits, based on
    successful test implementations.
    """

    def __init__(self, driver, browser_manager: BrowserManager, download_control: DownloadControlManager = None):
        self.driver = driver
        self.browser_manager = browser_manager
        self.download_control = download_control

    def _handle_browser_crash_popup(self):
        """Handle browser crash popup that appears when browser was closed abruptly."""
        try:
            # First, try to close any modal dialogs with JavaScript
            self.driver.execute_script("""
                // Close any modal dialogs
                var modals = document.querySelectorAll('.modal, [role="dialog"], .popup, .overlay');
                for (var i = 0; i < modals.length; i++) {
                    if (modals[i].style.display !== 'none') {
                        modals[i].style.display = 'none';
                    }
                }
                
                // Click any visible close buttons
                var closeButtons = document.querySelectorAll('button[aria-label*="Close"], button[title*="Close"], button:contains("OK"), button:contains("Close")');
                for (var i = 0; i < closeButtons.length; i++) {
                    if (closeButtons[i].offsetParent !== null) { // Check if visible
                        closeButtons[i].click();
                    }
                }
                
                // Try to remove any overlay elements
                var overlays = document.querySelectorAll('.overlay, .backdrop, .modal-backdrop');
                for (var i = 0; i < overlays.length; i++) {
                    overlays[i].remove();
                }
            """)
            
            time.sleep(1)
            
            # Look for common crash popup selectors
            popup_selectors = [
                "button[aria-label*='Close']",
                "button[title*='Close']", 
                "button:contains('OK')",
                "button:contains('Close')",
                "div[role='dialog'] button",
                ".modal button",
                "[data-testid*='close']",
                "[data-testid*='dismiss']"
            ]
            
            for selector in popup_selectors:
                try:
                    popup_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for button in popup_buttons:
                        if button.is_displayed():
                            print(f"   🔧 Found and closing browser crash popup...")
                            button.click()
                            time.sleep(1)
                            return
                except:
                    continue
            
            # Also try to find by text content
            try:
                page_source = self.driver.page_source.lower()
                if any(keyword in page_source for keyword in ['crashed', 'abruptly', 'restore', 'reopen']):
                    print(f"   🔧 Detected crash popup text, trying to close...")
                    # Try common close actions
                    self.driver.execute_script("window.close();")
                    time.sleep(1)
            except:
                pass
                
        except Exception as e:
            print(f"   ⚠️ Warning: Could not handle browser crash popup: {e}")

    def _extract_filename_from_element(
        self,
        attachment: WebElement,
    ) -> Optional[str]:
        """
        Extracts a filename from a Selenium WebElement using multiple strategies.
        This version is corrected to handle more edge cases.
        """
        # Strategy 1: Check text content for a filename with a valid extension
        text_content = attachment.text.strip()
        if text_content and any(
            ext in text_content.lower() for ext in Config.ALLOWED_EXTENSIONS
        ):
            return text_content

        # Strategy 2: Check 'aria-label' for descriptive text
        aria_label = attachment.get_attribute("aria-label")
        if aria_label and "file attachment" in aria_label:
            filename = aria_label.split("file attachment")[0].strip()
            if filename:  # Ensure it's not empty
                return filename

        # Strategy 3: Check 'title' attribute
        title = attachment.get_attribute("title")
        if title:
            # Check if title itself could be a filename
            if any(ext in title.lower() for ext in Config.ALLOWED_EXTENSIONS):
                return title

        # Strategy 4: Check 'href' for a downloadable link
        href = attachment.get_attribute("href")
        if href and href.strip() not in ("#", ""):
            # Check if the href contains something that looks like a file
            basename = os.path.basename(href)
            if "." in basename:  # A simple check for an extension
                return basename

        return None

    def _find_attachments(self) -> List[WebElement]:
        """
        Waits for and finds all attachment elements on the page using a robust
        WebDriverWait as proven effective in tests.
        """
        try:
            # Check if this is an error page first
            if "Oops! We couldn't find what you wanted" in self.driver.page_source:
                print("   ⚠️ Error page detected, using shorter timeout")
                timeout = 5  # Short timeout for error pages
            else:
                timeout = Config.ATTACHMENT_WAIT_TIMEOUT
            
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, Config.ATTACHMENT_SELECTOR)
                )
            )
            attachments = self.driver.find_elements(
                By.CSS_SELECTOR, Config.ATTACHMENT_SELECTOR
            )
            print(f"   ─ Found {len(attachments)} potential attachment(s).")
            
            # Debug: Show unique filenames found
            unique_filenames = set()
            for attachment in attachments:
                filename = self._extract_filename_from_element(attachment)
                if filename:
                    unique_filenames.add(filename)
            
            print(f"   📎 Unique filenames found: {list(unique_filenames)}")
            return attachments
        except TimeoutException:
            print("   ⚠ Timed out waiting for attachments to appear.")
            return []

    def _download_attachment(self, attachment: WebElement, filename: str) -> bool:
        """
        Performs a click on the attachment element with multiple fallback strategies
        to handle element click interception issues.
        Returns the actual filename saved by the browser.
        """
        try:
            print(f"      ⬇ Clicking to download '{filename}'...")
            
            # Get list of files before download
            import os
            from config import Config
            files_before = set()
            if os.path.exists(Config.DOWNLOAD_FOLDER):
                files_before = set(os.listdir(Config.DOWNLOAD_FOLDER))
            
            # Strategy 1: Try direct click first
            try:
                attachment.click()
                time.sleep(Config.PAGE_DELAY)
            except ElementClickInterceptedException:
                print(f"         ⚠ Element click intercepted, trying fallback strategies...")
                
                # Strategy 2: Scroll element into view and try again
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", attachment)
                    time.sleep(0.5)  # Brief pause for scroll to complete
                    attachment.click()
                    time.sleep(Config.PAGE_DELAY)
                except ElementClickInterceptedException:
                    print(f"         ⚠ Still intercepted after scroll, trying JavaScript click...")
                    
                    # Strategy 3: Use JavaScript click
                    try:
                        self.driver.execute_script("arguments[0].click();", attachment)
                        time.sleep(Config.PAGE_DELAY)
                    except Exception as js_error:
                        print(f"         ⚠ JavaScript click failed: {js_error}")
                        
                        # Strategy 4: Try to hide the floating element temporarily
                        try:
                            # Hide the floating buttons that might be intercepting
                            floating_elements = self.driver.find_elements(
                                By.CSS_SELECTOR, 
                                ".page_buttons_right.orderHeaderShowFloatingSection.floatingSectionOnTop"
                            )
                            if floating_elements:
                                self.driver.execute_script(
                                    "arguments[0].style.display = 'none';", 
                                    floating_elements[0]
                                )
                                time.sleep(0.3)
                                attachment.click()
                                time.sleep(Config.PAGE_DELAY)
                                # Restore the floating element
                                self.driver.execute_script(
                                    "arguments[0].style.display = 'block';", 
                                    floating_elements[0]
                                )
                                return True
                        except Exception as hide_error:
                            print(f"         ⚠ Hide strategy failed: {hide_error}")
                            
                            # Strategy 5: Final attempt with coordinates
                            try:
                                # Get element location and click at a specific point
                                location = attachment.location
                                size = attachment.size
                                # Click in the center of the element
                                x = location['x'] + size['width'] // 2
                                y = location['y'] + size['height'] // 2
                                
                                from selenium.webdriver.common.action_chains import ActionChains
                                actions = ActionChains(self.driver)
                                actions.move_to_element(attachment).click().perform()
                                time.sleep(Config.PAGE_DELAY)
                                return True
                            except Exception as coord_error:
                                print(f"         ⚠ Coordinate click failed: {coord_error}")
                                return False
                                
            # Wait for file to appear and get the actual filename
            actual_filename = self._wait_for_download_completion(files_before, filename)
            if actual_filename:
                print(f"         ✅ Download completed: {actual_filename}")
                return actual_filename
            else:
                print(f"         ❌ Download failed or file not detected")
                return None
                
        except Exception as e:
            print(f"      ❌ Failed to click on attachment '{filename}'. Reason: {e}")
            return False
    
    def _wait_for_download_completion(self, files_before: set, expected_filename: str) -> str:
        """
        Wait for download to complete and return the actual filename saved by the browser.
        """
        import os
        from config import Config
        import time
        
        max_wait = 30  # Maximum 30 seconds to wait
        wait_time = 0
        
        while wait_time < max_wait:
            time.sleep(1)
            wait_time += 1
            
            if os.path.exists(Config.DOWNLOAD_FOLDER):
                files_after = set(os.listdir(Config.DOWNLOAD_FOLDER))
                new_files = files_after - files_before
                
                # Look for the expected filename or variations
                base_name, ext = os.path.splitext(expected_filename)
                
                # Check for exact match first
                if expected_filename in new_files:
                    return expected_filename
                
                # Check for variations with (1), (2), etc.
                for i in range(1, 10):  # Check up to (9)
                    variation = f"{base_name} ({i}){ext}"
                    if variation in new_files:
                        return variation
                
                # Check for .crdownload files (in progress)
                crdownload_files = [f for f in new_files if f.endswith('.crdownload')]
                if crdownload_files:
                    continue  # Still downloading, wait more
                
                # If we have new files but none match our pattern, return the first one
                if new_files:
                    return list(new_files)[0]
        
        return None

    def download_attachments_for_po(self, po_number: str, tab_id: str = "MAIN", hierarchical_folder: str = None) -> Tuple[bool, str]:
        """
        Main workflow to find and download all attachments for a specific PO.
        Each downloadable file found will be registered in the CSV control system.
        Waits for all downloads to complete and calculates final status.
        Returns a tuple of (success_status, message).
        """
        # Store current tab handle to restore later
        original_tab_handle = self.driver.current_window_handle
        
        try:
            # Switch to the specific tab for this PO
            if tab_id != "MAIN":
                self.driver.switch_to.window(tab_id)
                print(f"   🔄 Switched to tab: {tab_id}")
            
            # Remove "PO" prefix if present to get the correct order number
            order_number = po_number.replace("PO", "") if po_number.startswith("PO") else po_number
            url = f"{Config.BASE_URL}/order_headers/{order_number}"
            print(f"\nProcessing PO #{po_number}")
            print(f"   Navigating to: {url}")
            
            # Navigate to the PO page in this specific tab
            self.driver.get(url)
            
            # Wait for page to load completely
            time.sleep(Config.TAB_SWITCH_DELAY)
            
            # Additional wait for first tab to ensure complete loading
            if tab_id != "MAIN" and len(self.driver.window_handles) <= 2:  # First or second tab
                print(f"   ⏳ Additional wait for first tab loading...")
                time.sleep(5)  # Extra 5 seconds for first tabs
            
            # Handle browser crash popup if it appears
            self._handle_browser_crash_popup()
            
            # Verify we're on the correct page (moved after navigation)
            current_url = self.driver.current_url
            if order_number not in current_url:
                print(f"   ⚠️ WARNING: Tab {tab_id} is not on the correct PO page!")
                print(f"      Expected: {order_number}, Current URL: {current_url}")
            
            # Check for error page, a useful feature from the recent changes

            # Check for error page, a useful feature from the recent changes
            if "Oops! We couldn't find what you wanted" in self.driver.page_source:
                msg = "PO not found or page error detected."
                print(f"   ❌ {msg}")
                # Register access issue in CSV
                if self.download_control:
                    self.download_control.register_download(po_number, tab_id, "ACCESS_ERROR", hierarchical_folder, error_message=msg)
                return False, msg

            # Wait for attachments with shorter timeout for error pages
            attachments = self._find_attachments()
            if not attachments:
                msg = "No attachments found."
                print(f"   ✅ {msg}")
                # Register no attachment status in CSV
                if self.download_control:
                    self.download_control.register_download(po_number, tab_id, "NO_ATTACHMENT", hierarchical_folder, error_message=msg)
                return True, msg

            total_attachments = len(attachments)
            print(f"   Processing {total_attachments} attachments...")
            downloaded_count = 0

            # Register each attachment in the CSV control system
            # Keep all attachments, including duplicates (as requested by user)
            
            for i, attachment in enumerate(attachments):
                filename = self._extract_filename_from_element(attachment)
                if not filename:
                    print(
                        f"      ⚠ Could not determine filename for attachment {i+1}, skipping."
                    )
                    continue

                # Register the download in CSV control system with unique key
                if self.download_control:
                    # Use the hierarchical folder as target_folder (where files will be moved later)
                    target_folder = hierarchical_folder or "/Users/juliocezar/Downloads/CoupaDownloads"
                    # Create unique key using index to handle duplicate filenames
                    file_key = self.download_control.register_download(po_number, tab_id, filename, target_folder, index=i)
                    print(f"      📝 Registered in CSV: {filename} (index {i+1})")
                else:
                    file_key = f"{po_number}_{filename}_{i}"

                # Update status to DOWNLOADING
                if self.download_control:
                    self.download_control.update_download_status(file_key, "DOWNLOADING")

                # Attempt to download the attachment
                actual_filename = self._download_attachment(attachment, filename)
                if actual_filename:
                    downloaded_count += 1
                    # Update the CSV record with the actual filename
                    if self.download_control:
                        self.download_control.update_download_filename(file_key, actual_filename)
                        self.download_control.update_download_status(file_key, "COMPLETED")
                else:
                    # Update status to ERROR
                    if self.download_control:
                        self.download_control.update_download_status(file_key, "ERROR", "Download failed")

            # Wait for all downloads to complete
            if self.download_control and total_attachments > 0:
                print(f"   ⏳ Waiting for all downloads to complete...")
                max_wait_time = 60  # Maximum 60 seconds to wait
                wait_time = 0
                while not self.download_control.is_po_complete(po_number) and wait_time < max_wait_time:
                    time.sleep(2)
                    wait_time += 2
                    print(f"      ⏱️ Waiting... ({wait_time}s)")
                
                if wait_time >= max_wait_time:
                    print(f"   ⚠️ Timeout waiting for downloads to complete")

            # Calculate final status based on download results
            if self.download_control:
                final_status = self.download_control.get_po_final_status(po_number)
                print(f"   📊 Final status calculated: {final_status}")
                
                # Move files with correct status
                if self.download_control.is_po_complete(po_number):
                    print(f"   📦 Moving files with status: {final_status}")
                    # Import here to avoid circular imports
                    from excel_processor import ExcelProcessor
                    excel_processor = ExcelProcessor()
                    self.download_control.move_completed_po_files(po_number, excel_processor)

            if downloaded_count > 0:
                msg = (
                    f"Initiated download for {downloaded_count}/{total_attachments} "
                    "attachments."
                )
                print(f"   ✅ {msg}")
                return True, msg
            else:
                msg = f"Failed to download any of the {total_attachments} attachments."
                print(f"   ❌ {msg}")
                return False, msg
                
        finally:
            # Always restore the original tab context
            try:
                if original_tab_handle in self.driver.window_handles:
                    self.driver.switch_to.window(original_tab_handle)
                    print(f"   🔄 Restored to original tab: {original_tab_handle}")
            except Exception as e:
                print(f"   ⚠️ Warning: Could not restore original tab: {e}")
