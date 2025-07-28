"""
Downloader module for Coupa Downloads automation.
Handles file operations, attachment downloading, and renaming.
"""

import os
import re
import time
from typing import List, Set, Tuple

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import Config


class FileManager:
    """Manages file operations following Single Responsibility Principle."""

    @staticmethod
    def get_supported_extensions() -> List[str]:
        """Get list of supported file extensions."""
        return Config.ALLOWED_EXTENSIONS

    @staticmethod
    def is_supported_file(filename: str) -> bool:
        """Check if file has supported extension."""
        return any(filename.lower().endswith(ext) for ext in Config.ALLOWED_EXTENSIONS)

    @staticmethod
    def extract_filename_from_aria_label(aria_label: str, index: int) -> str:
        """Extract filename from aria-label attribute."""
        if aria_label is None:
            return f"attachment_{index + 1}"

        filename_match = re.search(r"(.+?)\s*file attachment", aria_label)
        return filename_match.group(1) if filename_match else f"attachment_{index + 1}"

    @staticmethod
    def rename_downloaded_files(
        po_number: str, files_to_rename: set, download_folder: str
    ) -> None:
        """Rename only the newly downloaded files with PO prefix."""
        try:
            for filename in files_to_rename:
                # Check if file already has PO prefix (either our specific one or any PO prefix)
                if not filename.startswith(f"PO{po_number}_") and not filename.startswith("PO"):
                    old_path = os.path.join(download_folder, filename)
                    new_filename = f"PO{po_number}_{filename}"
                    new_path = os.path.join(download_folder, new_filename)
                    try:
                        os.rename(old_path, new_path)
                        print(f"    Renamed {filename} -> {new_filename}")
                    except Exception as e:
                        print(f"    Could not rename {filename}: {e}")
                else:
                    print(f"    Skipping {filename} - already has PO prefix")
        except Exception as e:
            print(f"    Error renaming files: {e}")

    @staticmethod
    def cleanup_double_po_prefixes(download_folder: str) -> None:
        """Clean up existing files with double PO prefixes (e.g., POPO15826591_...)."""
        try:
            for filename in os.listdir(download_folder):
                if filename.startswith("POPO"):
                    # Extract the part after the second PO
                    # POPO15826591_document.pdf -> PO15826591_document.pdf
                    clean_filename = filename[2:]  # Remove the first "PO"
                    old_path = os.path.join(download_folder, filename)
                    new_path = os.path.join(download_folder, clean_filename)
                    
                    try:
                        os.rename(old_path, new_path)
                        print(f"    Fixed double PO prefix: {filename} -> {clean_filename}")
                    except Exception as e:
                        print(f"    Could not fix {filename}: {e}")
        except Exception as e:
            print(f"    Error cleaning up double PO prefixes: {e}")

    @staticmethod
    def check_and_fix_unnamed_files(download_folder: str) -> None:
        """Check for and fix any files that don't have PO prefixes."""
        try:
            unnamed_files = []
            for filename in os.listdir(download_folder):
                if (os.path.isfile(os.path.join(download_folder, filename)) and 
                    not filename.startswith('.') and 
                    not filename.startswith("PO")):
                    unnamed_files.append(filename)
            
            if unnamed_files:
                print(f"    ⚠️ Found {len(unnamed_files)} unnamed files: {unnamed_files}")
                print(f"    💡 Run 'python fix_unnamed_files.py' to fix them")
        except Exception as e:
            print(f"    Error checking for unnamed files: {e}")


class DownloadManager:
    """Manages download operations following Single Responsibility Principle."""

    def __init__(self, driver: webdriver.Edge):
        self.driver = driver
        self.file_manager = FileManager()

    def _wait_for_download_complete(self, directory: str, timeout: int = 30) -> None:
        """Wait for all .crdownload files to disappear."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not any(f.endswith(".crdownload") for f in os.listdir(directory)):
                return
            time.sleep(1)
        raise TimeoutException(f"Downloads not completed within {timeout} seconds")

    def _wait_for_attachments(self) -> None:
        """Wait for attachments to load on the page."""
        try:
            WebDriverWait(self.driver, Config.ATTACHMENT_WAIT_TIMEOUT).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, Config.ATTACHMENT_SELECTOR)
                )
            )
        except TimeoutException:
            raise TimeoutException("Timed out waiting for attachments to load")

    def _find_attachments(self) -> List:
        """Find all attachment elements on the page."""
        attachments = self.driver.find_elements(By.CSS_SELECTOR, Config.ATTACHMENT_SELECTOR)
        print(f"    Found {len(attachments)} attachment elements using selector: {Config.ATTACHMENT_SELECTOR}")
        
        # Debug: Print details of each attachment found
        for i, attachment in enumerate(attachments):
            try:
                aria_label = attachment.get_attribute("aria-label")
                role = attachment.get_attribute("role")
                class_name = attachment.get_attribute("class")
                print(f"      Attachment {i+1}: aria-label='{aria_label}', role='{role}', class='{class_name}'")
            except Exception as e:
                print(f"      Attachment {i+1}: Error getting attributes - {e}")
        
        return attachments

    def _download_attachment(self, attachment, index: int) -> None:
        """Download a single attachment."""
        try:
            # Get filename from aria-label
            aria_label = attachment.get_attribute("aria-label")
            filename = self.file_manager.extract_filename_from_aria_label(
                aria_label, index
            )

            print(f"    Processing attachment {index + 1}: {filename}")

            # Skip unsupported file types
            if not self.file_manager.is_supported_file(filename):
                print(f"    Skipping unsupported file: {filename}")
                return

            # Check if element is clickable
            if not attachment.is_enabled():
                print(f"    Warning: Attachment {index + 1} is not enabled")
                return

            if not attachment.is_displayed():
                print(f"    Warning: Attachment {index + 1} is not displayed")
                return

            # Try to click the attachment
            try:
                # Scroll into view first
                self.driver.execute_script("arguments[0].scrollIntoView();", attachment)
                time.sleep(0.5)  # Brief pause after scrolling
                
                # Try regular click first
                attachment.click()
                print(f"    Successfully clicked: {filename}")
            except Exception as click_error:
                print(f"    Regular click failed, trying JavaScript click: {click_error}")
                # Fallback to JavaScript click
                self.driver.execute_script("arguments[0].click();", attachment)
                print(f"    JavaScript click successful: {filename}")

            # Brief pause between downloads
            time.sleep(1)

        except Exception as e:
            print(f"    Failed to download attachment {index + 1}: {str(e)}")
            print(f"    Aria-label: {aria_label if 'aria_label' in locals() else 'Not available'}")

    def download_attachments_for_po(self, display_po: str, clean_po: str) -> None:
        """Download all attachments for a specific PO and update CSV status."""
        from selenium.common.exceptions import TimeoutException
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from csv_processor import CSVProcessor

        print(f"\n📋 Processing PO #{display_po}...")

        try:
            # Navigate to PO page
            po_url = Config.BASE_URL.format(clean_po)
            print(f"  🌐 Navigating to: {po_url}")
            self.driver.get(po_url)

            # Check if page exists
            if "Page Not Found" in self.driver.title or "404" in self.driver.title:
                print(f"  ❌ PO #{display_po} not found")
                CSVProcessor.update_po_status(display_po, 'FAILED', error_message='PO page not found', coupa_url=po_url)
                return

            # Wait for page to load
            WebDriverWait(self.driver, Config.PAGE_LOAD_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Check for login redirect
            if "login" in self.driver.current_url.lower() or "sign_in" in self.driver.current_url.lower():
                print(f"  🔐 Login required for PO #{display_po}")
                CSVProcessor.update_po_status(display_po, 'FAILED', error_message='Login required', coupa_url=po_url)
                return

            # Find attachments
            attachments = self._find_attachments()
            attachments_found = len(attachments)
            
            if not attachments:
                print(f"  📭 No attachments found for PO #{display_po}")
                CSVProcessor.update_po_status(display_po, 'NO_ATTACHMENTS', 
                                            attachments_found=0, attachments_downloaded=0, coupa_url=po_url)
                return

            print(f"  Found {attachments_found} attachments. Downloading with proper names...")

            # Extract supplier name for folder organization
            supplier_name = self._extract_supplier_name()
            
            # Track downloads before starting
            initial_count = self._count_existing_files(supplier_name)
            
            # Use temporary directory approach for clean downloads
            self._download_with_proper_names(attachments, display_po, supplier_name)
            
            # Count files after download
            final_count = self._count_existing_files(supplier_name)
            attachments_downloaded = final_count - initial_count
            
            # Update CSV status based on results
            if attachments_downloaded == attachments_found:
                status = 'COMPLETED'
                print(f"  ✅ Successfully downloaded all {attachments_downloaded} attachments")
            elif attachments_downloaded > 0:
                status = 'PARTIAL'
                print(f"  ⚠️ Downloaded {attachments_downloaded} of {attachments_found} attachments")
            else:
                status = 'FAILED'
                print(f"  ❌ Failed to download any attachments")
            
            # Update CSV with results
            CSVProcessor.update_po_status(
                display_po, 
                status, 
                supplier=supplier_name,
                attachments_found=attachments_found,
                attachments_downloaded=attachments_downloaded,
                download_folder=f"{supplier_name}/",
                coupa_url=po_url
            )

        except TimeoutException:
            print(f"  Timed out waiting for PO #{display_po} page to load. Skipping.")
            CSVProcessor.update_po_status(display_po, 'FAILED', error_message='Page load timeout', coupa_url=po_url)
        except Exception as e:
            print(f"  Error processing PO #{display_po}: {str(e)}")
            CSVProcessor.update_po_status(display_po, 'FAILED', error_message=str(e)[:100], coupa_url=po_url)

    def _extract_supplier_name(self) -> str:
        """Extract supplier name from the PO page using cascading selector approach."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        # Try CSS selectors first (preferred approach)
        for i, css_selector in enumerate(Config.SUPPLIER_NAME_CSS_SELECTORS, 1):
            try:
                print(f"  🔍 Trying CSS selector {i}: {css_selector}")
                supplier_element = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
                )
                
                supplier_name = supplier_element.text.strip()
                
                if supplier_name and len(supplier_name) > 2:  # Valid supplier name
                    cleaned_name = self._clean_folder_name(supplier_name)
                    print(f"  ✅ Found supplier via CSS: {supplier_name} → {cleaned_name}")
                    return cleaned_name
                else:
                    print(f"  ⚠️ CSS selector found element but text is too short: '{supplier_name}'")
                    
            except Exception as e:
                print(f"  ❌ CSS selector {i} failed: {str(e)[:50]}...")
                continue
        
        # Fallback to XPath (your original method)
        try:
            print(f"  🔄 Falling back to XPath: {Config.SUPPLIER_NAME_XPATH}")
            supplier_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, Config.SUPPLIER_NAME_XPATH))
            )
            
            supplier_name = supplier_element.text.strip()
            
            if supplier_name:
                cleaned_name = self._clean_folder_name(supplier_name)
                print(f"  ✅ Found supplier via XPath: {supplier_name} → {cleaned_name}")
                return cleaned_name
            else:
                print(f"  ⚠️ XPath found element but text is empty")
                
        except Exception as e:
            print(f"  ❌ XPath extraction failed: {e}")
        
        # Final fallback
        print(f"  📁 All methods failed, using 'Unknown_Supplier'")
        return "Unknown_Supplier"

    def _clean_folder_name(self, name: str) -> str:
        """Clean a name to be safe for use as a folder name."""
        import re
        
        # Replace spaces and invalid characters with underscores
        cleaned = re.sub(r'[<>:"/\\|?*&\s]', '_', name)
        
        # Remove multiple underscores and trim
        cleaned = re.sub(r'_+', '_', cleaned).strip('_')
        
        # Limit length to avoid filesystem issues
        if len(cleaned) > 100:
            cleaned = cleaned[:100].rstrip('_')
        
        # Ensure it's not empty
        if not cleaned:
            cleaned = "Unknown_Supplier"
            
        return cleaned

    def _create_supplier_folder(self, supplier_name: str) -> str:
        """Create and return the path to the supplier-specific folder."""
        supplier_folder = os.path.join(Config.DOWNLOAD_FOLDER, supplier_name)
        
        try:
            if not os.path.exists(supplier_folder):
                os.makedirs(supplier_folder)
                print(f"  📁 Created supplier folder: {supplier_name}")
            else:
                print(f"  📁 Using existing supplier folder: {supplier_name}")
            
            return supplier_folder
            
        except Exception as e:
            print(f"  ⚠️ Could not create supplier folder '{supplier_name}': {e}")
            print(f"  📁 Using main download folder instead")
            return Config.DOWNLOAD_FOLDER

    def _download_with_proper_names(self, attachments, display_po: str, supplier_name: str = "Unknown_Supplier") -> None:
        """Download attachments using true 'Save As' method with direct HTTP requests."""
        print(f"    🎯 Using true 'Save As' method for {len(attachments)} attachments...")
        
        # Create supplier-specific folder
        supplier_folder = self._create_supplier_folder(supplier_name)
        
        # Try the direct download approach first
        if self._try_direct_download_method(attachments, display_po, supplier_folder):
            return
        
        # If direct download fails, try right-click Save As method
        print(f"    🔄 Direct download failed, trying right-click Save As method...")
        if self._try_right_click_save_as_method(attachments, display_po, supplier_folder):
            return
        
        # If that fails too, fall back to temporary directory method
        print(f"    🔄 Right-click method failed, trying temporary directory method...")
        self._try_temp_directory_method(attachments, display_po, supplier_folder)

    def _try_direct_download_method(self, attachments, display_po: str, supplier_folder: str) -> bool:
        """Try to download files directly using requests library."""
        import requests
        
        try:
            # Get cookies from the current browser session
            cookies = {cookie['name']: cookie['value'] for cookie in self.driver.get_cookies()}
            
            success_count = 0
            
            for index, attachment in enumerate(attachments):
                try:
                    # Get filename and download URL
                    aria_label = attachment.get_attribute("aria-label")
                    filename = self.file_manager.extract_filename_from_aria_label(aria_label, index)
                    
                    if not self.file_manager.is_supported_file(filename):
                        print(f"    ⏭️ Skipping unsupported file: {filename}")
                        continue
                    
                    # Try to get the download URL
                    download_url = self._extract_download_url(attachment)
                    if not download_url:
                        print(f"    ⚠️ Could not extract download URL for: {filename}")
                        continue
                    
                    # Create proper filename with PO prefix
                    proper_filename = f"PO{display_po}_{filename}"
                    dest_path = os.path.join(supplier_folder, proper_filename)
                    
                    # Handle duplicate filenames
                    counter = 1
                    while os.path.exists(dest_path):
                        name, ext = os.path.splitext(filename)
                        proper_filename = f"PO{display_po}_{name}_{counter}{ext}"
                        dest_path = os.path.join(Config.DOWNLOAD_FOLDER, proper_filename)
                        counter += 1
                    
                    # Download directly with proper filename
                    print(f"    📥 Downloading directly: {filename} → {proper_filename}")
                    
                    response = requests.get(download_url, cookies=cookies, stream=True, timeout=30)
                    response.raise_for_status()
                    
                    with open(dest_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    print(f"    ✅ Successfully saved: {proper_filename}")
                    success_count += 1
                    
                except Exception as e:
                    print(f"    ❌ Failed to download {filename} directly: {e}")
                    continue
            
            if success_count > 0:
                print(f"    🎉 Successfully downloaded {success_count} files using direct method!")
                return True
            else:
                print(f"    ⚠️ No files downloaded using direct method")
                return False
                
        except Exception as e:
            print(f"    ❌ Direct download method failed: {e}")
            return False

    def _extract_download_url(self, attachment) -> str | None:
        """Extract the download URL from an attachment element."""
        try:
            # Try different methods to get the download URL
            
            # Method 1: Check if it's a direct link
            href = attachment.get_attribute("href")
            if href and href.startswith("http"):
                return href
            
            # Method 2: Check parent elements for links
            parent = attachment.find_element(By.XPATH, "..")
            href = parent.get_attribute("href")
            if href and href.startswith("http"):
                return href
            
            # Method 3: Look for onclick handlers that might contain URLs
            onclick = attachment.get_attribute("onclick")
            if onclick:
                import re
                url_match = re.search(r"(https?://[^\s'\"]+)", onclick)
                if url_match:
                    return url_match.group(1)
            
            # Method 4: Check data attributes
            for attr in ["data-url", "data-href", "data-download-url"]:
                url = attachment.get_attribute(attr)
                if url and url.startswith("http"):
                    return url
            
            return None
            
        except Exception as e:
            print(f"    ⚠️ Error extracting download URL: {e}")
            return None

    def _try_right_click_save_as_method(self, attachments, display_po: str, supplier_folder: str) -> bool:
        """Try to use right-click 'Save As' method."""
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.keys import Keys
        
        try:
            success_count = 0
            
            for index, attachment in enumerate(attachments):
                try:
                    # Get filename
                    aria_label = attachment.get_attribute("aria-label")
                    filename = self.file_manager.extract_filename_from_aria_label(aria_label, index)
                    
                    if not self.file_manager.is_supported_file(filename):
                        print(f"    ⏭️ Skipping unsupported file: {filename}")
                        continue
                    
                    print(f"    🖱️ Right-clicking on: {filename}")
                    
                    # Scroll element into view
                    self.driver.execute_script("arguments[0].scrollIntoView();", attachment)
                    time.sleep(0.5)
                    
                    # Right-click on the attachment
                    actions = ActionChains(self.driver)
                    actions.context_click(attachment).perform()
                    time.sleep(1)
                    
                    # Try to find and click "Save As" or similar option
                    # This is browser-specific and might not work reliably
                    try:
                        # Send keys to select "Save As" (this is very browser-dependent)
                        actions.send_keys(Keys.ARROW_DOWN).perform()  # Navigate to Save As
                        time.sleep(0.5)
                        actions.send_keys(Keys.ENTER).perform()  # Select Save As
                        time.sleep(1)
                        
                        # This would require handling the Save As dialog
                        # which is very complex and OS-dependent
                        print(f"    ⚠️ Right-click method is complex and browser-dependent")
                        break  # Exit after first attempt
                        
                    except Exception as dialog_error:
                        print(f"    ❌ Could not handle Save As dialog: {dialog_error}")
                        break
                        
                except Exception as e:
                    print(f"    ❌ Right-click failed for {filename}: {e}")
                    continue
            
            # This method is experimental and likely won't work reliably
            print(f"    ⚠️ Right-click Save As method is not reliable - skipping")
            return False
            
        except Exception as e:
            print(f"    ❌ Right-click Save As method failed: {e}")
            return False

    def _try_temp_directory_method(self, attachments, display_po: str, supplier_folder: str) -> None:
        """Fallback to temporary directory method."""
        import tempfile
        import shutil
        
        # Create temporary directory for this PO
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"    📁 Using temporary directory: {temp_dir}")
            
            # Use CDP to change download directory (works with Edge!)
            try:
                self.driver.execute_cdp_cmd('Page.setDownloadBehavior', {
                    'behavior': 'allow',
                    'downloadPath': temp_dir
                })
                print(f"    ✅ Changed download directory to temp folder")
            except Exception as e:
                print(f"    ⚠️ Could not change download directory: {e}")
                print(f"    🔄 Falling back to file tracking method...")
                return self._fallback_download_method(attachments, display_po, supplier_folder)
            
            try:
                # Download each attachment to temp directory
                for index, attachment in enumerate(attachments):
                    self._download_attachment_simple(attachment, index)

                # Wait for downloads to complete in temp directory
                self._wait_for_download_complete(temp_dir, timeout=len(attachments) * 10)
                
                # Move files with proper names to final destination
                self._move_files_with_proper_names(temp_dir, display_po, supplier_folder)
                
            finally:
                # Restore original download directory
                try:
                    self.driver.execute_cdp_cmd('Page.setDownloadBehavior', {
                        'behavior': 'allow',
                        'downloadPath': Config.DOWNLOAD_FOLDER
                    })
                    print(f"    ✅ Restored download directory")
                except Exception as e:
                    print(f"    ⚠️ Could not restore download directory: {e}")

    def _download_attachment_simple(self, attachment, index: int) -> None:
        """Download a single attachment with simplified logic."""
        try:
            # Get filename from aria-label
            aria_label = attachment.get_attribute("aria-label")
            filename = self.file_manager.extract_filename_from_aria_label(aria_label, index)

            print(f"    Processing attachment {index + 1}: {filename}")

            # Skip unsupported file types
            if not self.file_manager.is_supported_file(filename):
                print(f"    Skipping unsupported file: {filename}")
                return

            # Check if element is clickable
            if not attachment.is_enabled() or not attachment.is_displayed():
                print(f"    Warning: Attachment {index + 1} is not clickable")
                return

            # Try to click the attachment
            try:
                self.driver.execute_script("arguments[0].scrollIntoView();", attachment)
                time.sleep(0.5)
                attachment.click()
                print(f"    ✅ Successfully downloaded: {filename}")
            except Exception as click_error:
                print(f"    Regular click failed, trying JavaScript click: {click_error}")
                self.driver.execute_script("arguments[0].click();", attachment)
                print(f"    ✅ JavaScript click successful: {filename}")

            time.sleep(1)  # Brief pause between downloads

        except Exception as e:
            print(f"    ❌ Failed to download attachment {index + 1}: {str(e)}")

    def _move_files_with_proper_names(self, temp_dir: str, display_po: str, supplier_folder: str) -> None:
        """Move files from temp directory to final destination with proper PO prefixes."""
        import shutil
        
        try:
            temp_files = [f for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
            if not temp_files:
                print("    ⚠️ No files downloaded to temporary directory")
                return
            
            print(f"    📦 Moving {len(temp_files)} files with proper names...")
            
            for filename in temp_files:
                # Create proper filename with PO prefix
                proper_filename = f"PO{display_po}_{filename}"
                
                source_path = os.path.join(temp_dir, filename)
                dest_path = os.path.join(supplier_folder, proper_filename)
                
                # Handle duplicate filenames
                counter = 1
                while os.path.exists(dest_path):
                    name, ext = os.path.splitext(filename)
                    proper_filename = f"PO{display_po}_{name}_{counter}{ext}"
                    dest_path = os.path.join(supplier_folder, proper_filename)
                    counter += 1
                
                # Move file with proper name
                shutil.move(source_path, dest_path)
                print(f"    ✅ Saved as: {proper_filename}")
                    
        except Exception as e:
            print(f"    ❌ Error moving files: {e}")

    def _fallback_download_method(self, attachments, display_po: str, supplier_folder: str) -> None:
        """Fallback to the old method if CDP doesn't work."""
        print("    🔄 Using fallback download method...")
        
        # Track files before download
        before_files = set(os.listdir(supplier_folder))

        # Download each attachment
        for index, attachment in enumerate(attachments):
            self._download_attachment_simple(attachment, index)

        # Wait for downloads to complete
        self._wait_for_download_complete(supplier_folder, timeout=len(attachments) * 10)
        
        # Track files after download and rename new ones
        after_files = set(os.listdir(supplier_folder))
        new_files = after_files - before_files
        
        if new_files:
            self.file_manager.rename_downloaded_files(display_po, new_files, supplier_folder)
        
        # Clean up any issues
        self.file_manager.cleanup_double_po_prefixes(supplier_folder)

    def _count_existing_files(self, supplier_name: str) -> int:
        """Count existing files in supplier folder."""
        try:
            supplier_folder = os.path.join(Config.DOWNLOAD_FOLDER, supplier_name)
            if os.path.exists(supplier_folder):
                return len([f for f in os.listdir(supplier_folder) 
                           if os.path.isfile(os.path.join(supplier_folder, f))])
            return 0
        except Exception:
            return 0


class LoginManager:
    """Manages login detection and monitoring."""

    def __init__(self, driver: webdriver.Edge):
        self.driver = driver

    def ensure_logged_in(self) -> None:
        """Detect Coupa login page and automatically monitor for successful login."""
        if (
            "login" in self.driver.current_url
            or "sign_in" in self.driver.current_url
            or "Log in" in self.driver.title
        ):
            print("Detected login page. Please log in manually...")

            # Monitor for successful login indicators
            max_wait_time = Config.LOGIN_TIMEOUT
            start_time = time.time()

            while time.time() - start_time < max_wait_time:
                try:
                    # Check for indicators of successful login
                    current_url = self.driver.current_url

                    # Success indicators (URLs that indicate logged-in state)
                    success_indicators = [
                        "order_headers",  # PO pages
                        "dashboard",  # Dashboard
                        "home",  # Home page
                        "profile",  # Profile page
                        "settings",  # Settings page
                    ]

                    # Check if we're on a logged-in page
                    if any(
                        indicator in current_url for indicator in success_indicators
                    ):
                        print("✅ Login detected automatically!")
                        return

                    # Check if we're still on login page
                    if "login" in current_url or "sign_in" in current_url:
                        print("⏳ Waiting for login completion...", end="\r")
                        time.sleep(1)
                        continue

                    # If we're not on login page and not on a known success page,
                    # assume login was successful
                    if "login" not in current_url and "sign_in" not in current_url:
                        print("✅ Login detected automatically!")
                        return

                except Exception as e:
                    print(f"⚠️ Error checking login status: {e}")
                    time.sleep(1)
                    continue

            # If we reach here, login timeout occurred
            print(f"\n❌ Login timeout after {max_wait_time} seconds.")
            print("Please ensure you've logged in and the page has loaded.")
            raise TimeoutException("Login timeout - please try again")

        # If not on login page, assume already logged in
        print("✅ Already logged in or not on login page.")
