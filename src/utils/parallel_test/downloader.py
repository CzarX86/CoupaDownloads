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

    def __init__(self, driver, browser_manager: BrowserManager, download_control: DownloadControlManager = None, download_dir: str = None):
        self.driver = driver
        self.browser_manager = browser_manager
        self.download_control = download_control
        self.download_dir = download_dir or Config.DOWNLOAD_FOLDER

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
        Waits for and finds all attachment elements on the page using enhanced
        element detection with multiple strategies and better error handling.
        """
        try:
            # Enhanced page state detection
            page_source = self.driver.page_source
            
            # Check for various error conditions first
            error_indicators = [
                "Oops! We couldn't find what you wanted",
                "Page not found",
                "Access denied",
                "Session expired",
                "Login required"
            ]
            
            is_error_page = any(indicator in page_source for indicator in error_indicators)
            
            if is_error_page:
                print("   ⚠️ Error page detected, using shorter timeout")
                timeout = 3  # Short timeout for error pages
            else:
                timeout = Config.ATTACHMENT_WAIT_TIMEOUT
            
            # Enhanced attachment detection with multiple selectors
            attachment_selectors = [
                Config.ATTACHMENT_SELECTOR,  # Primary selector
                "a[href*='attachment']",     # Fallback 1: links with attachment in URL
                "a[href*='download']",       # Fallback 2: links with download in URL
                ".attachment",               # Fallback 3: elements with attachment class
                "[data-testid*='attachment']" # Fallback 4: test ID based
            ]
            
            attachments = []
            used_selector = None
            
            # Try each selector until we find elements or exhaust all options
            for selector in attachment_selectors:
                try:
                    print(f"   🔍 Trying selector: {selector}")
                    
                    # Wait for elements with this selector
                    WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    
                    # Find all elements matching this selector
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    # Filter out elements that don't look like attachments
                    valid_attachments = []
                    for element in elements:
                        try:
                            # Check if element has attributes that suggest it's a downloadable file
                            href = element.get_attribute("href") or ""
                            text = element.text.strip()
                            title = element.get_attribute("title") or ""
                            
                            # Look for file extensions or download indicators
                            has_file_extension = any(ext in (href + text + title).lower() 
                                                   for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt', '.zip', '.rar'])
                            has_download_indicator = any(indicator in (href + text + title).lower() 
                                                       for indicator in ['download', 'attachment', 'file'])
                            
                            if has_file_extension or has_download_indicator or text:
                                valid_attachments.append(element)
                                
                        except Exception as e:
                            # If we can't check the element, include it anyway
                            valid_attachments.append(element)
                    
                    if valid_attachments:
                        attachments = valid_attachments
                        used_selector = selector
                        print(f"   ✅ Found {len(attachments)} potential attachment(s) using selector: {selector}")
                        break
                        
                except TimeoutException:
                    print(f"   ⏳ No elements found with selector: {selector}")
                    continue
                except Exception as e:
                    print(f"   ⚠️ Error with selector {selector}: {e}")
                    continue
            
            if not attachments:
                print("   ⚠️ No attachments found with any selector")
                return []
            
            # Enhanced validation of found attachments
            validated_attachments = []
            for attachment in attachments:
                try:
                    # Ensure element is still valid and visible
                    if attachment.is_displayed() and attachment.is_enabled():
                        validated_attachments.append(attachment)
                    else:
                        print(f"   ⚠️ Skipping hidden/disabled element")
                except Exception as e:
                    print(f"   ⚠️ Skipping invalid element: {e}")
            
            attachments = validated_attachments
            print(f"   📎 Validated {len(attachments)} attachment(s)")
            
            # Debug: Show unique filenames found
            unique_filenames = set()
            for attachment in attachments:
                try:
                    filename = self._extract_filename_from_element(attachment)
                    if filename:
                        unique_filenames.add(filename)
                except Exception as e:
                    print(f"   ⚠️ Error extracting filename: {e}")
            
            if unique_filenames:
                print(f"   📎 Unique filenames found: {list(unique_filenames)}")
            
            return attachments
            
        except TimeoutException:
            print("   ⚠️ Timed out waiting for attachments to appear.")
            return []
        except Exception as e:
            print(f"   ❌ Error finding attachments: {e}")
            return []

    def _download_attachment(self, attachment: WebElement, filename: str, download_dir: str = None) -> bool:
        """
        Performs a click on the attachment element with enhanced error handling and
        multiple fallback strategies to handle element click interception issues.
        Returns the actual filename saved by the browser.
        """
        try:
            print(f"      ⬇ Clicking to download '{filename}'...")
            
            # Enhanced element validation before attempting download
            try:
                # Check if element is still valid and accessible
                if not attachment.is_displayed():
                    print(f"         ❌ Element is not displayed")
                    return None
                if not attachment.is_enabled():
                    print(f"         ❌ Element is not enabled")
                    return None
                    
                # Get element properties to validate it's still the same
                element_tag = attachment.tag_name
                element_href = attachment.get_attribute("href") or ""
                print(f"         📎 Element details: {element_tag}, href: {element_href[:50]}...")
                
            except Exception as e:
                print(f"         ❌ Element validation failed: {e}")
                return None
            
            # Get list of files before download
            import os
            from config import Config
            files_before = set()
            # Use the dynamic download directory if provided, otherwise use Config default
            target_download_dir = download_dir or Config.DOWNLOAD_FOLDER
            if os.path.exists(target_download_dir):
                files_before = set(os.listdir(target_download_dir))
            
            # Strategy 1: Try direct click first with enhanced error handling
            try:
                # Ensure element is in viewport before clicking
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", attachment)
                time.sleep(0.5)  # Brief pause for scroll to complete
                
                attachment.click()
                time.sleep(Config.PAGE_DELAY)
                print(f"         ✅ Direct click successful")
                
            except ElementClickInterceptedException:
                print(f"         ⚠ Element click intercepted, trying fallback strategies...")
                
                # Strategy 2: Enhanced scroll and retry
                try:
                    # More aggressive scrolling
                    self.driver.execute_script("""
                        arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});
                        window.scrollBy(0, -100); // Adjust for fixed headers
                    """, attachment)
                    time.sleep(1)  # Longer pause for smooth scroll
                    
                    attachment.click()
                    time.sleep(Config.PAGE_DELAY)
                    print(f"         ✅ Scroll + click successful")
                    
                except ElementClickInterceptedException:
                    print(f"         ⚠ Still intercepted after scroll, trying JavaScript click...")
                    
                    # Strategy 3: Enhanced JavaScript click
                    try:
                        # Multiple JavaScript click strategies
                        self.driver.execute_script("""
                            // Try multiple click methods
                            arguments[0].click();
                            arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true}));
                        """, attachment)
                        time.sleep(Config.PAGE_DELAY)
                        print(f"         ✅ JavaScript click successful")
                        
                    except Exception as js_error:
                        print(f"         ⚠ JavaScript click failed: {js_error}")
                        
                        # Strategy 4: Enhanced floating element handling
                        try:
                            # Hide multiple types of floating elements
                            floating_selectors = [
                                ".page_buttons_right.orderHeaderShowFloatingSection.floatingSectionOnTop",
                                ".floating", ".overlay", ".modal", ".popup",
                                "[style*='position: fixed']", "[style*='position: absolute']"
                            ]
                            
                            hidden_elements = []
                            for selector in floating_selectors:
                                floating_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                for element in floating_elements:
                                    if element.is_displayed():
                                        self.driver.execute_script("arguments[0].style.display = 'none';", element)
                                        hidden_elements.append(element)
                            
                            if hidden_elements:
                                print(f"         🔧 Hidden {len(hidden_elements)} floating elements")
                                time.sleep(0.5)
                                
                                # Try clicking again
                                attachment.click()
                                time.sleep(Config.PAGE_DELAY)
                                
                                # Restore the hidden elements
                                for element in hidden_elements:
                                    try:
                                        self.driver.execute_script("arguments[0].style.display = 'block';", element)
                                    except:
                                        pass  # Ignore restoration errors
                                        
                                print(f"         ✅ Floating element strategy successful")
                            else:
                                raise Exception("No floating elements found to hide")
                                
                        except Exception as hide_error:
                            print(f"         ⚠ Floating element strategy failed: {hide_error}")
                            
                            # Strategy 5: Enhanced coordinate-based clicking
                            try:
                                # Get element location with enhanced validation
                                location = attachment.location
                                size = attachment.size
                                
                                if location and size:
                                    # Click in the center of the element
                                    x = location['x'] + size['width'] // 2
                                    y = location['y'] + size['height'] // 2
                                    
                                    from selenium.webdriver.common.action_chains import ActionChains
                                    actions = ActionChains(self.driver)
                                    
                                    # Move to element first, then click
                                    actions.move_to_element(attachment).pause(0.5).click().perform()
                                    time.sleep(Config.PAGE_DELAY)
                                    print(f"         ✅ Coordinate-based click successful")
                                else:
                                    raise Exception("Invalid element location or size")
                                    
                            except Exception as coord_error:
                                print(f"         ⚠ Coordinate click failed: {coord_error}")
                                
                                # Strategy 6: Final fallback - direct href navigation
                                try:
                                    href = attachment.get_attribute("href")
                                    if href and href.startswith("http"):
                                        print(f"         🔗 Final fallback: Direct navigation to {href}")
                                        self.driver.get(href)
                                        time.sleep(Config.PAGE_DELAY)
                                        print(f"         ✅ Direct navigation successful")
                                    else:
                                        raise Exception("No valid href for direct navigation")
                                        
                                except Exception as nav_error:
                                    print(f"         ❌ All download strategies failed: {nav_error}")
                                    return None
                                    
            except Exception as e:
                print(f"         ❌ Unexpected error during click: {e}")
                return None
                                
            # Wait for file to appear and get the actual filename
            actual_filename = self._wait_for_download_completion(files_before, filename, download_dir)
            if actual_filename:
                print(f"         ✅ Download completed: {actual_filename}")
                return actual_filename
            else:
                print(f"         ❌ Download failed or file not detected")
                return None
                
        except Exception as e:
            print(f"      ❌ Failed to click on attachment '{filename}'. Reason: {e}")
            return False
    
    def _wait_for_download_completion(self, files_before: set, expected_filename: str, download_dir: str = None) -> str:
        """
        Wait for download to complete and return the actual filename saved by the browser.
        """
        import os
        import time
        
        # Use the dynamic download directory if provided, otherwise use Config default
        target_download_dir = download_dir or Config.DOWNLOAD_FOLDER
        
        max_wait = 60  # Maximum 60 seconds to wait for downloads
        wait_time = 0
        stable_size_count = 0
        last_file_size = 0
        
        while wait_time < max_wait:
            time.sleep(1)
            wait_time += 1
            
            if os.path.exists(target_download_dir):
                files_after = set(os.listdir(target_download_dir))
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
                    print(f"         ⏳ Download in progress: {crdownload_files[0]}")
                    continue  # Still downloading, wait more
                
                # Check for .tmp files (temporary download files)
                tmp_files = [f for f in new_files if f.endswith('.tmp')]
                if tmp_files:
                    print(f"         ⏳ Temporary file detected: {tmp_files[0]}")
                    continue  # Still downloading, wait more
                
                # Check file size stability for large files
                if new_files:
                    for new_file in new_files:
                        file_path = os.path.join(target_download_dir, new_file)
                        if os.path.exists(file_path):
                            current_size = os.path.getsize(file_path)
                            if current_size == last_file_size and current_size > 0:
                                stable_size_count += 1
                                if stable_size_count >= 3:  # File size stable for 3 seconds
                                    print(f"         ✅ File size stable: {new_file} ({current_size} bytes)")
                                    return new_file
                            else:
                                stable_size_count = 0
                                last_file_size = current_size
                                print(f"         📊 File size changing: {new_file} ({current_size} bytes)")
                    
                    # If we have new files but none match our pattern, return the first one
                    if not crdownload_files and not tmp_files:
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
        original_tab_handle = None
        try:
            original_tab_handle = self.driver.current_window_handle
        except:
            pass  # Handle case where driver might be in invalid state
        
        try:
            # Enhanced tab validation and switching
            if tab_id != "MAIN":
                # Verify tab still exists before switching
                if tab_id not in self.driver.window_handles:
                    msg = f"Tab {tab_id} no longer exists (window closed)"
                    print(f"   ❌ {msg}")
                    return False, msg
                
                try:
                    self.driver.switch_to.window(tab_id)
                    print(f"   🔄 Switched to tab: {tab_id}")
                except Exception as e:
                    msg = f"Failed to switch to tab {tab_id}: {e}"
                    print(f"   ❌ {msg}")
                    return False, msg
            
            # Remove "PO" or "PM" prefix (case-insensitive) to get the correct order number
            up = (po_number or '').upper()
            order_number = po_number[2:] if up.startswith(("PO", "PM")) else po_number
            url = f"{Config.BASE_URL}/order_headers/{order_number}"
            print(f"\nProcessing PO #{po_number}")
            print(f"   Navigating to: {url}")
            
            # Navigate to the PO page in this specific tab with enhanced error handling
            try:
                self.driver.get(url)
            except Exception as e:
                msg = f"Navigation failed: {e}"
                print(f"   ❌ {msg}")
                return False, msg
            
            # Enhanced page loading with better error detection
            time.sleep(Config.TAB_SWITCH_DELAY)
            
            # Additional wait for first tab to ensure complete loading
            if tab_id != "MAIN" and len(self.driver.window_handles) <= 2:  # First or second tab
                print(f"   ⏳ Additional wait for first tab loading...")
                time.sleep(5)  # Extra 5 seconds for first tabs
            
            # Handle browser crash popup if it appears
            self._handle_browser_crash_popup()
            
            # Enhanced page validation
            current_url = self.driver.current_url
            if order_number not in current_url:
                print(f"   ⚠️ WARNING: Tab {tab_id} is not on the correct PO page!")
                print(f"      Expected: {order_number}, Current URL: {current_url}")
            
            # Enhanced page loading check with better error handling
            time.sleep(1)  # Brief delay to ensure page content is loaded
            print(f"   🔍 Checking for valid PO page...")
            
            # Wait for page to be fully loaded before checking elements
            try:
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                # Wait for either the valid PO element or error element to appear
                WebDriverWait(self.driver, 15).until(  # Increased timeout
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "#order_header_requisition_header")),
                        EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div/h1"))
                    )
                )
                print(f"   ✅ Page fully loaded")
            except Exception as e:
                print(f"   ⚠️ Page load timeout: {e}")
                # Continue anyway, but with more caution
            
            # Enhanced valid page detection with multiple strategies
            valid_page = False
            try:
                # Strategy 1: Check for main PO element
                order_header_element = self.driver.find_element(By.CSS_SELECTOR, "#order_header_requisition_header")
                if order_header_element and order_header_element.is_displayed():
                    valid_page = True
                    print(f"   ✅ Valid PO page detected (method 1)")
            except:
                pass  # Element not found, try other methods
            
            if not valid_page:
                # Strategy 2: Check for error page elements
                try:
                    error_elements = self.driver.find_elements(By.XPATH, "/html/body/div[2]/div/h1")
                    if error_elements:
                        error_text = error_elements[0].text
                        if "not found" in error_text.lower() or "error" in error_text.lower():
                            msg = f"Error page detected: {error_text}"
                            print(f"   ❌ {msg}")
                            if self.download_control:
                                self.download_control.register_download(po_number, tab_id, "ACCESS_ERROR", hierarchical_folder, error_message=msg)
                            return False, msg
                except:
                    pass
                
                # Strategy 3: Check URL patterns
                if "order_headers" not in current_url or order_number not in current_url:
                    msg = "Invalid URL - PO page not accessible"
                    print(f"   ❌ {msg}")
                    if self.download_control:
                        self.download_control.register_download(po_number, tab_id, "ACCESS_ERROR", hierarchical_folder, error_message=msg)
                    return False, msg
                
                # Strategy 4: Final fallback - assume valid if we got this far
                valid_page = True
                print(f"   ✅ Assuming valid page (fallback)")
            
            print(f"   ✅ Valid PO page confirmed, proceeding with attachment search...")

            # Enhanced attachment search with better error handling
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

            # Process attachments with enhanced error handling
            for i, attachment in enumerate(attachments):
                try:
                    filename = self._extract_filename_from_element(attachment)
                    if not filename:
                        print(f"      ⚠ Could not determine filename for attachment {i+1}, skipping.")
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

                    # Attempt to download the attachment with enhanced error handling
                    actual_filename = self._download_attachment(attachment, filename, self.download_dir)
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
                            
                except Exception as e:
                    print(f"      ❌ Error processing attachment {i+1}: {e}")
                    if self.download_control:
                        file_key = f"{po_number}_attachment_{i}"
                        self.download_control.update_download_status(file_key, "ERROR", f"Processing error: {e}")

            # Enhanced download completion waiting
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
                try:
                    final_status = self.download_control.get_po_final_status(po_number)
                    print(f"   📊 Final status calculated: {final_status}")
                    
                    # Move files with correct status
                    if self.download_control.is_po_complete(po_number):
                        print(f"   📦 Moving files with status: {final_status}")
                        # Import here to avoid circular imports
                        from excel_processor import ExcelProcessor
                        excel_processor = ExcelProcessor()
                        # Pass the hierarchical_folder as base_download_dir
                        base_dir = os.path.dirname(hierarchical_folder) if hierarchical_folder else None
                        self.download_control.move_completed_po_files(po_number, excel_processor, base_dir)
                except Exception as e:
                    print(f"   ⚠️ Error in final status calculation: {e}")

            if downloaded_count > 0:
                msg = f"Initiated download for {downloaded_count}/{total_attachments} attachments."
                print(f"   ✅ {msg}")
                return True, msg
            else:
                msg = f"Failed to download any of the {total_attachments} attachments."
                print(f"   ❌ {msg}")
                return False, msg
                
        except Exception as e:
            msg = f"Critical error in download_attachments_for_po: {e}"
            print(f"   ❌ {msg}")
            return False, msg
            
        finally:
            # Enhanced tab restoration with better error handling
            try:
                if original_tab_handle and original_tab_handle in self.driver.window_handles:
                    self.driver.switch_to.window(original_tab_handle)
                    print(f"   🔄 Restored to original tab: {original_tab_handle}")
            except Exception as e:
                print(f"   ⚠️ Warning: Could not restore original tab: {e}")
                # Try to switch to any available tab
                try:
                    if self.driver.window_handles:
                        self.driver.switch_to.window(self.driver.window_handles[0])
                        print(f"   🔄 Switched to first available tab")
                except:
                    print(f"   ❌ Critical: No valid tabs available")
