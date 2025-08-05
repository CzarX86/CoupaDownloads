#!/usr/bin/env python3
"""
Quick Fix for PO16277411 Timeout Issue
Increases download timeout and adds retry logic for failed downloads.
"""

import os
import sys
import time
import tempfile
import shutil
from typing import List, Optional
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.config import Config
from core.csv_processor import CSVProcessor


class TimeoutFixDownloader:
    """Enhanced downloader with improved timeout handling and retry logic."""
    
    def __init__(self, driver):
        self.driver = driver
        self.max_retries = 3
        self.base_timeout_per_file = 30  # Increased from 10 to 30 seconds
        self.retry_delay = 2  # Seconds between retries
    
    def download_po_with_retry(self, display_po: str, clean_po: str) -> bool:
        """Download PO attachments with enhanced retry logic and timeout handling."""
        
        print(f"\n🔧 Enhanced download for PO #{display_po}")
        print(f"  Timeout: {self.base_timeout_per_file} seconds per file")
        print(f"  Max retries: {self.max_retries}")
        
        try:
            # Navigate to PO page
            po_url = Config.BASE_URL.format(clean_po)
            print(f"  🌐 Navigating to: {po_url}")
            self.driver.get(po_url)
            
            # Check if page exists
            if "Page Not Found" in self.driver.title or "404" in self.driver.title:
                print(f"  ❌ PO #{display_po} not found")
                CSVProcessor.update_po_status(display_po, 'FAILED', error_message='PO page not found', coupa_url=po_url)
                return False
            
            # Find attachments
            from selenium.webdriver.common.by import By
            attachments = self.driver.find_elements(By.CSS_SELECTOR, Config.ATTACHMENT_SELECTOR)
            attachments_found = len(attachments)
            
            if not attachments:
                print(f"  📭 No attachments found for PO #{display_po}")
                CSVProcessor.update_po_status(display_po, 'NO_ATTACHMENTS', 
                                            attachments_found=0, attachments_downloaded=0, coupa_url=po_url)
                return True
            
            print(f"  Found {attachments_found} attachments")
            
            # Extract supplier name
            supplier_name = self._extract_supplier_name()
            supplier_folder = self._create_supplier_folder(supplier_name)
            
            # Track initial file count
            initial_count = self._count_existing_files(supplier_folder)
            
            # Download with enhanced timeout and retry logic
            successful_downloads = self._download_attachments_with_retry(
                attachments, display_po, supplier_folder
            )
            
            # Count final files
            final_count = self._count_existing_files(supplier_folder)
            attachments_downloaded = final_count - initial_count
            
            # Update status
            if attachments_downloaded == attachments_found:
                status = 'COMPLETED'
                print(f"  ✅ Successfully downloaded all {attachments_downloaded} attachments")
            elif attachments_downloaded > 0:
                status = 'PARTIAL'
                print(f"  ⚠️ Downloaded {attachments_downloaded} of {attachments_found} attachments")
            else:
                status = 'FAILED'
                print(f"  ❌ Failed to download any attachments")
            
            # Update CSV
            CSVProcessor.update_po_status(
                display_po, 
                status, 
                supplier=supplier_name,
                attachments_found=attachments_found,
                attachments_downloaded=attachments_downloaded,
                download_folder=f"{supplier_name}/",
                coupa_url=po_url
            )
            
            return attachments_downloaded > 0
            
        except Exception as e:
            print(f"  ❌ Error processing PO #{display_po}: {str(e)}")
            CSVProcessor.update_po_status(display_po, 'FAILED', error_message=str(e)[:100], coupa_url=po_url)
            return False
    
    def _download_attachments_with_retry(self, attachments, display_po: str, supplier_folder: str) -> int:
        """Download attachments with retry logic for each file."""
        
        successful_downloads = 0
        
        for index, attachment in enumerate(attachments):
            filename = self._get_filename_from_attachment(attachment, index)
            print(f"    📎 Processing attachment {index + 1}: {filename}")
            
            # Try to download with retries
            for attempt in range(self.max_retries):
                try:
                    if self._download_single_attachment_with_timeout(attachment, index, supplier_folder, display_po):
                        successful_downloads += 1
                        print(f"    ✅ Successfully downloaded: {filename}")
                        break
                    else:
                        print(f"    ⚠️ Attempt {attempt + 1} failed for: {filename}")
                        if attempt < self.max_retries - 1:
                            print(f"    🔄 Retrying in {self.retry_delay} seconds...")
                            time.sleep(self.retry_delay)
                        else:
                            print(f"    ❌ All {self.max_retries} attempts failed for: {filename}")
                            
                except Exception as e:
                    print(f"    ❌ Error on attempt {attempt + 1}: {str(e)}")
                    if attempt < self.max_retries - 1:
                        print(f"    🔄 Retrying in {self.retry_delay} seconds...")
                        time.sleep(self.retry_delay)
                    else:
                        print(f"    ❌ All {self.max_retries} attempts failed for: {filename}")
        
        return successful_downloads
    
    def _download_single_attachment_with_timeout(self, attachment, index: int, supplier_folder: str, display_po: str) -> bool:
        """Download a single attachment with enhanced timeout handling."""
        
        try:
            # Get filename
            filename = self._get_filename_from_attachment(attachment, index)
            
            # Skip unsupported files
            if not self._is_supported_file(filename):
                print(f"    ⏭️ Skipping unsupported file: {filename}")
                return False
            
            # Check if clickable
            if not attachment.is_enabled() or not attachment.is_displayed():
                print(f"    ⚠️ Attachment {index + 1} is not clickable")
                return False
            
            # Use temporary directory method with enhanced timeout
            return self._temp_dir_download_with_timeout(attachment, filename, supplier_folder, display_po)
            
        except Exception as e:
            print(f"    ❌ Download error: {str(e)}")
            return False
    
    def _temp_dir_download_with_timeout(self, attachment, filename: str, supplier_folder: str, display_po: str) -> bool:
        """Download using temp directory with enhanced timeout."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Change download directory
                self.driver.execute_cdp_cmd('Page.setDownloadBehavior', {
                    'behavior': 'allow',
                    'downloadPath': temp_dir
                })
                
                # Click the attachment
                self.driver.execute_script("arguments[0].scrollIntoView();", attachment)
                time.sleep(0.5)
                attachment.click()
                
                # Wait for download with enhanced timeout
                timeout = self.base_timeout_per_file
                if self._wait_for_download_complete(temp_dir, timeout):
                    # Move file with proper name
                    return self._move_file_with_proper_name(temp_dir, filename, supplier_folder, display_po)
                else:
                    print(f"    ⏰ Download timeout after {timeout} seconds")
                    return False
                    
            except Exception as e:
                print(f"    ❌ Temp dir download error: {str(e)}")
                return False
            finally:
                # Restore download directory
                try:
                    self.driver.execute_cdp_cmd('Page.setDownloadBehavior', {
                        'behavior': 'allow',
                        'downloadPath': Config.DOWNLOAD_FOLDER
                    })
                except:
                    pass
    
    def _wait_for_download_complete(self, directory: str, timeout: int) -> bool:
        """Wait for download to complete with enhanced timeout handling."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check for .crdownload files
            files = os.listdir(directory)
            crdownload_files = [f for f in files if f.endswith('.crdownload')]
            
            if not crdownload_files:
                # Check if any files were downloaded
                downloaded_files = [f for f in files if os.path.isfile(os.path.join(directory, f))]
                if downloaded_files:
                    return True
                else:
                    # No files downloaded yet, continue waiting
                    time.sleep(1)
                    continue
            
            # Still downloading, wait
            time.sleep(1)
        
        return False
    
    def _move_file_with_proper_name(self, temp_dir: str, filename: str, supplier_folder: str, display_po: str) -> bool:
        """Move downloaded file with proper PO prefix."""
        try:
            temp_files = [f for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
            if not temp_files:
                return False
            
            # Use the first downloaded file
            downloaded_file = temp_files[0]
            
            # Create proper filename
            clean_po_number = display_po.replace("PO", "") if display_po.startswith("PO") else display_po
            proper_filename = f"PO{clean_po_number}_{filename}"
            
            source_path = os.path.join(temp_dir, downloaded_file)
            dest_path = os.path.join(supplier_folder, proper_filename)
            
            # Handle duplicates
            counter = 1
            while os.path.exists(dest_path):
                name, ext = os.path.splitext(filename)
                proper_filename = f"PO{clean_po_number}_{name}_{counter}{ext}"
                dest_path = os.path.join(supplier_folder, proper_filename)
                counter += 1
            
            # Move file
            shutil.move(source_path, dest_path)
            print(f"    ✅ Saved as: {proper_filename}")
            return True
            
        except Exception as e:
            print(f"    ❌ Error moving file: {str(e)}")
            return False
    
    def _get_filename_from_attachment(self, attachment, index: int) -> str:
        """Extract filename from attachment element."""
        try:
            aria_label = attachment.get_attribute("aria-label")
            if aria_label:
                import re
                filename_match = re.search(r"(.+?)\s*file attachment", aria_label)
                if filename_match:
                    return filename_match.group(1).strip()
            
            # Fallback to generic name
            return f"attachment_{index + 1}"
        except:
            return f"attachment_{index + 1}"
    
    def _is_supported_file(self, filename: str) -> bool:
        """Check if file type is supported."""
        return any(filename.lower().endswith(ext) for ext in Config.ALLOWED_EXTENSIONS)
    
    def _extract_supplier_name(self) -> str:
        """Extract supplier name from the page."""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # Try CSS selectors first
            for selector in Config.SUPPLIER_NAME_CSS_SELECTORS:
                try:
                    element = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    supplier_name = element.text.strip()
                    if supplier_name:
                        return self._clean_folder_name(supplier_name)
                except:
                    continue
            
            # Fallback to XPath
            try:
                element = self.driver.find_element(By.XPATH, Config.SUPPLIER_NAME_XPATH)
                supplier_name = element.text.strip()
                if supplier_name:
                    return self._clean_folder_name(supplier_name)
            except:
                pass
            
        except Exception as e:
            print(f"    ⚠️ Could not extract supplier name: {e}")
        
        return "Unknown_Supplier"
    
    def _clean_folder_name(self, name: str) -> str:
        """Clean name for use as folder name."""
        import re
        cleaned = re.sub(r'[<>:"/\\|?*&\s]', '_', name)
        cleaned = re.sub(r'_+', '_', cleaned).strip('_')
        if len(cleaned) > 100:
            cleaned = cleaned[:100].rstrip('_')
        return cleaned if cleaned else "Unknown_Supplier"
    
    def _create_supplier_folder(self, supplier_name: str) -> str:
        """Create supplier folder and return path."""
        supplier_folder = os.path.join(Config.DOWNLOAD_FOLDER, supplier_name)
        try:
            if not os.path.exists(supplier_folder):
                os.makedirs(supplier_folder)
                print(f"  📁 Created supplier folder: {supplier_name}")
            return supplier_folder
        except Exception as e:
            print(f"  ⚠️ Could not create supplier folder: {e}")
            return Config.DOWNLOAD_FOLDER
    
    def _count_existing_files(self, folder: str) -> int:
        """Count existing files in folder."""
        try:
            return len([f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))])
        except:
            return 0


def main():
    """Main function to test the timeout fix."""
    print("🔧 PO16277411 Timeout Fix Test")
    print("="*50)
    
    # This would typically be used with a WebDriver instance
    # For now, just demonstrate the configuration
    print(f"Base timeout per file: 30 seconds (increased from 10)")
    print(f"Max retries per file: 3")
    print(f"Retry delay: 2 seconds")
    print(f"Total timeout for 2 files: 60 seconds (increased from 20)")
    
    print("\n✅ Timeout fix configuration ready for implementation")


if __name__ == "__main__":
    main() 