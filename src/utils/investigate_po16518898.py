#!/usr/bin/env python3
"""
Investigation script for PO16518898 download issue.
This script uses the actual methods from our program to debug why only 1 file was downloaded.
"""

import os
import sys
import time
from typing import List, Dict, Any

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.browser import BrowserManager
from core.config import Config
from core.downloader import DownloadManager, FileManager
from core.excel_processor import ExcelProcessor
from core.folder_hierarchy import FolderHierarchyManager


class PO16518898Investigator:
    """Investigator for PO16518898 using actual program methods."""
    
    def __init__(self):
        self.browser_manager = BrowserManager()
        self.driver = None
        self.download_manager = None
        self.file_manager = FileManager()
        self.folder_hierarchy = FolderHierarchyManager()
        
        # PO16518898 specific data
        self.po_number = "16518898"
        self.display_po = f"PO{self.po_number}"
        self.clean_po = self.po_number
        self.po_url = Config.BASE_URL.format(self.clean_po)
        
        # Mock PO data for investigation
        self.po_data = {
            'po_number': self.display_po,
            'status': 'PENDING',
            'supplier': '',
            'attachments_found': 0,
            'attachments_downloaded': 0
        }
        
    def setup_investigation(self):
        """Setup the investigation environment."""
        print("🔧 Setting up investigation environment...")
        
        try:
            # Setup browser using the correct method
            self.driver = self.browser_manager.initialize_driver()
            if not self.driver:
                print("❌ Failed to setup browser")
                return False
            
            # Setup download manager
            self.download_manager = DownloadManager(self.driver)
            
            print("✅ Investigation environment ready")
            return True
            
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False
    
    def investigate_po_page(self):
        """Investigate the PO page using actual program methods."""
        print(f"\n🔍 Investigating PO {self.display_po}...")
        print(f"🌐 URL: {self.po_url}")
        
        try:
            # Navigate to PO page
            print("   🌐 Navigating to PO page...")
            self.driver.get(self.po_url)
            
            # Check if page exists
            if "Page Not Found" in self.driver.title or "404" in self.driver.title:
                print(f"  ❌ PO #{self.display_po} not found")
                return False
            
            # Wait for page to load
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            WebDriverWait(self.driver, Config.PAGE_LOAD_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            print(f"  ✅ Page loaded successfully")
            print(f"  📄 Page title: {self.driver.title}")
            print(f"  🌐 Current URL: {self.driver.current_url}")
            
            # Check for login redirect
            if "login" in self.driver.current_url.lower() or "sign_in" in self.driver.current_url.lower() or "identity" in self.driver.current_url.lower():
                print(f"  🔐 Login required for PO #{self.display_po}")
                print(f"  ⚠️ Please login manually and press Enter when ready...")
                input("Press Enter after logging in...")
                
                # Navigate back to PO page after login
                print(f"  🌐 Navigating back to PO page...")
                self.driver.get(self.po_url)
                time.sleep(3)
                
                print(f"  📄 Page title after login: {self.driver.title}")
                print(f"  🌐 Current URL after login: {self.driver.current_url}")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Error navigating to PO page: {e}")
            return False
    
    def investigate_attachments(self):
        """Investigate attachments using actual program methods."""
        print(f"\n📎 Investigating attachments...")
        
        try:
            # Use the actual _find_attachments method from DownloadManager
            attachments = self.download_manager._find_attachments()
            attachments_found = len(attachments)
            
            print(f"  📊 Total attachments found: {attachments_found}")
            
            if not attachments:
                print("  ❌ No attachments found on page")
                return []
            
            # Analyze each attachment
            attachment_details = []
            for i, attachment in enumerate(attachments):
                try:
                    aria_label = attachment.get_attribute("aria-label")
                    role = attachment.get_attribute("role")
                    class_name = attachment.get_attribute("class")
                    href = attachment.get_attribute("href")
                    onclick = attachment.get_attribute("onclick")
                    download_attr = attachment.get_attribute("download")
                    
                    # Extract filename using actual method
                    filename = self.file_manager.extract_filename_from_aria_label(aria_label, i)
                    
                    # Check if file is supported
                    is_supported = self.file_manager.is_supported_file(filename)
                    
                    # Check element state
                    is_enabled = attachment.is_enabled()
                    is_displayed = attachment.is_displayed()
                    
                    print(f"\n  📄 Attachment {i+1}:")
                    print(f"    Filename: '{filename}'")
                    print(f"    Aria-label: '{aria_label}'")
                    print(f"    Role: '{role}'")
                    print(f"    Class: '{class_name}'")
                    print(f"    Href: '{href}'")
                    print(f"    Onclick: '{onclick}'")
                    print(f"    Download attr: '{download_attr}'")
                    print(f"    Supported: {is_supported}")
                    print(f"    Enabled: {is_enabled}")
                    print(f"    Displayed: {is_displayed}")
                    
                    attachment_details.append({
                        'element': attachment,
                        'index': i,
                        'filename': filename,
                        'aria_label': aria_label,
                        'role': role,
                        'class_name': class_name,
                        'href': href,
                        'onclick': onclick,
                        'download_attr': download_attr,
                        'is_supported': is_supported,
                        'is_enabled': is_enabled,
                        'is_displayed': is_displayed
                    })
                    
                except Exception as e:
                    print(f"    ❌ Error analyzing attachment {i+1}: {e}")
            
            return attachment_details
            
        except Exception as e:
            print(f"  ❌ Error investigating attachments: {e}")
            return []
    
    def test_attachment_downloads(self, attachment_details):
        """Test downloading each attachment using actual program methods."""
        print(f"\n🖱️ Testing attachment downloads...")
        
        download_results = []
        
        for attachment_info in attachment_details:
            attachment = attachment_info['element']
            index = attachment_info['index']
            filename = attachment_info['filename']
            
            print(f"\n  🖱️ Testing download for attachment {index+1}: '{filename}'")
            
            # Check if file is supported
            if not attachment_info['is_supported']:
                print(f"    ⚠️ Skipping - unsupported file type")
                download_results.append({
                    'index': index,
                    'filename': filename,
                    'success': False,
                    'reason': 'Unsupported file type'
                })
                continue
            
            # Check if element is clickable
            if not attachment_info['is_enabled']:
                print(f"    ⚠️ Skipping - element not enabled")
                download_results.append({
                    'index': index,
                    'filename': filename,
                    'success': False,
                    'reason': 'Element not enabled'
                })
                continue
            
            if not attachment_info['is_displayed']:
                print(f"    ⚠️ Skipping - element not displayed")
                download_results.append({
                    'index': index,
                    'filename': filename,
                    'success': False,
                    'reason': 'Element not displayed'
                })
                continue
            
            # Try to download using actual method
            try:
                print(f"    🖱️ Attempting download...")
                
                # Use the actual _download_attachment method
                self.download_manager._download_attachment(attachment, index)
                
                print(f"    ✅ Download attempt completed")
                download_results.append({
                    'index': index,
                    'filename': filename,
                    'success': True,
                    'reason': 'Download attempted'
                })
                
                # Brief pause between downloads
                time.sleep(1)
                
            except Exception as e:
                print(f"    ❌ Download failed: {e}")
                download_results.append({
                    'index': index,
                    'filename': filename,
                    'success': False,
                    'reason': str(e)
                })
        
        return download_results
    
    def check_download_results(self):
        """Check what files were actually downloaded."""
        print(f"\n📂 Checking download results...")
        
        # Check the default download directory
        download_dir = os.path.expanduser("~/Downloads")
        
        if os.path.exists(download_dir):
            files = os.listdir(download_dir)
            recent_files = []
            
            # Get current time for comparison
            current_time = time.time()
            
            for file in files:
                file_path = os.path.join(download_dir, file)
                # Check if file was modified in the last 5 minutes
                if os.path.getmtime(file_path) > current_time - 300:  # 5 minutes
                    size = os.path.getsize(file_path)
                    modified_time = time.ctime(os.path.getmtime(file_path))
                    recent_files.append({
                        'name': file,
                        'size': size,
                        'modified': modified_time
                    })
            
            if recent_files:
                print(f"📁 Recent files in download directory ({download_dir}):")
                for file_info in recent_files:
                    print(f"  📄 {file_info['name']} ({file_info['size']} bytes, modified: {file_info['modified']})")
            else:
                print(f"📁 No recent files found in download directory")
        else:
            print(f"❌ Download directory not found: {download_dir}")
    
    def run_investigation(self):
        """Run the complete investigation."""
        print("🔍 Starting investigation for PO16518898...")
        print("=" * 60)
        
        # Setup
        if not self.setup_investigation():
            return
        
        try:
            # Investigate PO page
            if not self.investigate_po_page():
                return
            
            # Investigate attachments
            attachment_details = self.investigate_attachments()
            
            if not attachment_details:
                print("❌ No attachments found to investigate")
                return
            
            # Test downloads
            download_results = self.test_attachment_downloads(attachment_details)
            
            # Check results
            self.check_download_results()
            
            # Summary
            print(f"\n" + "=" * 60)
            print(f"📋 INVESTIGATION SUMMARY")
            print(f"=" * 60)
            print(f"Total attachments found: {len(attachment_details)}")
            print(f"Supported file types: {sum(1 for a in attachment_details if a['is_supported'])}")
            print(f"Unsupported file types: {sum(1 for a in attachment_details if not a['is_supported'])}")
            print(f"Clickable elements: {sum(1 for a in attachment_details if a['is_enabled'] and a['is_displayed'])}")
            print(f"Download attempts: {sum(1 for r in download_results if r['success'])}")
            print(f"Failed attempts: {sum(1 for r in download_results if not r['success'])}")
            
            # Identify potential issues
            print(f"\n🔍 POTENTIAL ISSUES IDENTIFIED:")
            
            unsupported_files = [a for a in attachment_details if not a['is_supported']]
            if unsupported_files:
                print(f"  ⚠️ Unsupported file types: {len(unsupported_files)}")
                for file_info in unsupported_files:
                    print(f"    - {file_info['filename']}")
            
            unclickable_elements = [a for a in attachment_details if not (a['is_enabled'] and a['is_displayed'])]
            if unclickable_elements:
                print(f"  ⚠️ Unclickable elements: {len(unclickable_elements)}")
                for file_info in unclickable_elements:
                    print(f"    - {file_info['filename']} (enabled: {file_info['is_enabled']}, displayed: {file_info['is_displayed']})")
            
            failed_downloads = [r for r in download_results if not r['success']]
            if failed_downloads:
                print(f"  ⚠️ Failed downloads: {len(failed_downloads)}")
                for result in failed_downloads:
                    print(f"    - {result['filename']}: {result['reason']}")
            
            if not unsupported_files and not unclickable_elements and not failed_downloads:
                print(f"  ✅ No obvious issues found - all attachments should be downloadable")
            
        finally:
            if self.driver:
                self.driver.quit()
                print("🔧 Browser closed")


def main():
    """Main function."""
    investigator = PO16518898Investigator()
    investigator.run_investigation()


if __name__ == "__main__":
    main()
