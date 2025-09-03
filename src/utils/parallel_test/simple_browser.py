#!/usr/bin/env python3
"""
Simplified browser manager for parallel testing.
"""

import os
import subprocess
from selenium import webdriver
from selenium.webdriver.edge.service import EdgeService
from selenium.webdriver.edge.options import Options


class SimpleBrowserManager:
    """Simplified browser manager for parallel testing."""
    
    def __init__(self):
        self.driver = None
        self.download_dir = os.path.expanduser("~/Downloads/CoupaDownloads")
        
    def initialize_driver(self, download_dir: str = None) -> webdriver.Edge:
        """Initialize Edge driver with custom download directory."""
        if download_dir:
            self.download_dir = download_dir
            
        # Create download directory
        os.makedirs(self.download_dir, exist_ok=True)
        
        # Configure Edge options
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
        options.add_argument("--disable-javascript")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Set download directory
        prefs = {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
            "profile.default_content_setting_values.notifications": 2
        }
        options.add_experimental_option("prefs", prefs)
        
        # Initialize driver
        try:
            self.driver = webdriver.Edge(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            print(f"   🌐 Browser initialized with download dir: {self.download_dir}")
            return self.driver
        except Exception as e:
            print(f"   ❌ Failed to initialize browser: {e}")
            raise
    
    def close_driver(self):
        """Close the browser driver."""
        if self.driver:
            try:
                self.driver.quit()
                print("   🔒 Browser closed")
            except Exception as e:
                print(f"   ⚠️ Error closing browser: {e}")
            finally:
                self.driver = None
