"""
Browser management module for Coupa Downloads automation.
Handles WebDriver setup, cleanup, and process management.
"""

import os
import signal
import subprocess
import sys
import time
from typing import Optional

from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService

from config import Config


class BrowserManager:
    """Manages browser lifecycle following Single Responsibility Principle."""
    
    def __init__(self):
        self.driver: Optional[webdriver.Edge] = None
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum: int, frame) -> None:
        """Handle interrupt signals for graceful shutdown."""
        print(f"\n🛑 Received signal {signum}. Shutting down gracefully...")
        self.cleanup()
        sys.exit(0)
    
    def cleanup_browser_processes(self) -> None:
        """Kill all Edge browser processes to ensure clean shutdown."""
        try:
            if sys.platform == "darwin":  # macOS
                subprocess.run(["pkill", "-f", "Microsoft Edge"], capture_output=True)
                subprocess.run(["pkill", "-f", "msedge"], capture_output=True)
            elif sys.platform == "win32":  # Windows
                subprocess.run(["taskkill", "/f", "/im", "msedge.exe"], capture_output=True)
            else:  # Linux
                subprocess.run(["pkill", "-f", "microsoft-edge"], capture_output=True)
                subprocess.run(["pkill", "-f", "msedge"], capture_output=True)
            print("🧹 Cleaned up Edge browser processes")
        except Exception as e:
            print(f"⚠️ Warning: Could not clean up Edge processes: {e}")
    
    def check_and_kill_existing_edge_processes(self) -> None:
        """Check for existing Edge processes and kill them before starting."""
        try:
            if sys.platform == "darwin":  # macOS
                result = subprocess.run(["pgrep", "-f", "Microsoft Edge"], capture_output=True)
                if result.returncode == 0:
                    print("🔍 Found existing Edge processes. Cleaning up...")
                    self.cleanup_browser_processes()
                    time.sleep(2)  # Give processes time to close
            elif sys.platform == "win32":  # Windows
                result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq msedge.exe"], capture_output=True)
                if "msedge.exe" in result.stdout.decode():
                    print("🔍 Found existing Edge processes. Cleaning up...")
                    self.cleanup_browser_processes()
                    time.sleep(2)
            else:  # Linux
                result = subprocess.run(["pgrep", "-f", "microsoft-edge"], capture_output=True)
                if result.returncode == 0:
                    print("🔍 Found existing Edge processes. Cleaning up...")
                    self.cleanup_browser_processes()
                    time.sleep(2)
        except Exception as e:
            print(f"⚠️ Warning: Could not check for existing Edge processes: {e}")
    
    def _create_browser_options(self, headless: bool = False, custom_download_dir: Optional[str] = None) -> EdgeOptions:
        """Create and configure browser options. Supports headless mode and custom download directory."""
        options = EdgeOptions()
        options.add_argument("--disable-extensions")
        options.add_argument("--start-maximized")
        
        # Use custom download directory if provided, otherwise use default
        download_dir = custom_download_dir or Config.DOWNLOAD_FOLDER
        browser_prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
        }
        
        options.add_experimental_option("prefs", browser_prefs)
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        if headless:
            options.add_argument("--headless=new")

        # Real-profile reuse
        if Config.EDGE_PROFILE_DIR:
            options.add_argument(f"--user-data-dir={Config.EDGE_PROFILE_DIR}")
            options.add_argument("--profile-directory=Default")

        return options
    
    def initialize_driver(self, headless: bool = False) -> webdriver.Edge:
        """Initialize the WebDriver with proper error handling. Supports headless mode."""
        # Check if local driver exists
        if not Config.DRIVER_PATH or not os.path.exists(Config.DRIVER_PATH):
            raise FileNotFoundError(f"WebDriver not found at {Config.DRIVER_PATH}")

        try:
            options = self._create_browser_options(headless=headless)
            service = EdgeService(executable_path=Config.DRIVER_PATH)
            self.driver = webdriver.Edge(service=service, options=options)
            print(f"Using local Edge WebDriver: {Config.DRIVER_PATH}")
            return self.driver
        except Exception as e:
            print(f"Driver initialization failed: {e}")
            raise
    
    def start(self, headless: bool = False) -> webdriver.Edge:
        """Start the browser with cleanup of existing processes. Supports headless mode."""
        self.check_and_kill_existing_edge_processes()
        return self.initialize_driver(headless=headless)
    
    def cleanup(self) -> None:
        """Clean up browser processes and close driver."""
        self.cleanup_browser_processes()
        
        if self.driver:
            try:
                self.driver.quit()
                print("✅ Browser closed successfully.")
            except Exception as e:
                print(f"⚠️ Warning: Could not close browser cleanly: {e}")
        else:
            print("ℹ️ No browser instance to close.") 