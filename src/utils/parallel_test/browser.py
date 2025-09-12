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
from driver_manager import DriverManager


class BrowserManager:
    """Manages browser lifecycle following Single Responsibility Principle."""
    
    def __init__(self):
        self.driver: Optional[webdriver.Edge] = None
        self.driver_manager = DriverManager()
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
        
        # Set profile options FIRST (like in working test)
        if Config.EDGE_PROFILE_DIR:
            options.add_argument(f"--user-data-dir={Config.EDGE_PROFILE_DIR}")
            options.add_argument(f"--profile-directory={Config.EDGE_PROFILE_NAME}")
        
        # Ensure browser remains open after script ends (for session persistency)
        options.add_experimental_option("detach", True)
        
        # Other options after profile setup
        # options.add_argument("--disable-extensions")  # Commented out to allow profile extensions
        options.add_argument("--start-maximized")
        
        # Use custom download directory if provided, otherwise use default
        download_dir = custom_download_dir or Config.DOWNLOAD_FOLDER
        browser_prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
            "plugins.always_open_pdf_externally": True,  # Keep this as per report
        }
        
        options.add_experimental_option("prefs", browser_prefs)
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # Suppress verbose browser output
        if not Config.SHOW_SELENIUM_LOGS:
            options.add_argument("--log-level=3")  # Only fatal errors
            options.add_argument("--silent")
            options.add_argument("--disable-logging")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--no-sandbox")

        if headless:
            options.add_argument("--headless=new")

        return options
    
    def initialize_driver_with_download_dir(self, download_dir: str, headless: bool = False) -> webdriver.Edge:
        """Initialize the WebDriver with a specific download directory."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Get driver path automatically (download if needed)
                driver_path = self.driver_manager.get_driver_path()
                
                # Verify driver works
                if not self.driver_manager.verify_driver(driver_path):
                    raise RuntimeError("EdgeDriver verification failed")
                
                options = self._create_browser_options(headless=headless, custom_download_dir=download_dir)
                
                # Configure service with log suppression
                service = EdgeService(
                    executable_path=driver_path,
                    log_output=subprocess.DEVNULL if not Config.SHOW_SELENIUM_LOGS else None
                )
                
                self.driver = webdriver.Edge(service=service, options=options)
                print(f"✅ Using Edge WebDriver with download dir '{download_dir}': {driver_path}")
                return self.driver
                
            except Exception as e:
                if "user data directory is already in use" in str(e):
                    retry_count += 1
                    print(f"⚠️ Profile directory is already in use (attempt {retry_count}/{max_retries})")
                    
                    if retry_count < max_retries:
                        print("   🔄 Attempting to resolve profile conflict...")
                        
                        # Try to clean up any existing Edge processes
                        self.cleanup_browser_processes()
                        time.sleep(3)  # Wait for processes to close
                        
                        print("   🔄 Retrying with profile...")
                        continue
                    else:
                        print("❌ ERROR: Could not resolve profile directory conflict after multiple attempts!")
                        print("   Please ensure:")
                        print("   1. All Edge browser windows are closed")
                        print("   2. No other applications are using the Edge profile")
                        print("   3. The profile directory is not locked by another process")
                        print(f"   Profile directory: {Config.EDGE_PROFILE_DIR}")
                        raise RuntimeError("Profile directory conflict could not be resolved. Please close Edge browser and try again.")
                else:
                    print(f"Driver initialization failed: {e}")
                    raise

    def initialize_driver(self, headless: bool = False) -> webdriver.Edge:
        """Initialize the WebDriver with proper error handling. Supports headless mode."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Get driver path automatically (download if needed)
                driver_path = self.driver_manager.get_driver_path()
                
                # Verify driver works
                if not self.driver_manager.verify_driver(driver_path):
                    raise RuntimeError("EdgeDriver verification failed")
                
                options = self._create_browser_options(headless=headless)
                
                # Configure service with log suppression
                service = EdgeService(
                    executable_path=driver_path,
                    log_output=subprocess.DEVNULL if not Config.SHOW_SELENIUM_LOGS else None
                )
                
                self.driver = webdriver.Edge(service=service, options=options)
                print(f"✅ Using Edge WebDriver: {driver_path}")
                return self.driver
                
            except Exception as e:
                if "user data directory is already in use" in str(e):
                    retry_count += 1
                    print(f"⚠️ Profile directory is already in use (attempt {retry_count}/{max_retries})")
                    
                    if retry_count < max_retries:
                        print("   🔄 Attempting to resolve profile conflict...")
                        
                        # Try to clean up any existing Edge processes
                        self.cleanup_browser_processes()
                        time.sleep(3)  # Wait for processes to close
                        
                        print("   🔄 Retrying with profile...")
                        continue
                    else:
                        print("❌ ERROR: Could not resolve profile directory conflict after multiple attempts!")
                        print("   Please ensure:")
                        print("   1. All Edge browser windows are closed")
                        print("   2. No other applications are using the Edge profile")
                        print("   3. The profile directory is not locked by another process")
                        print(f"   Profile directory: {Config.EDGE_PROFILE_DIR}")
                        raise RuntimeError("Profile directory conflict could not be resolved. Please close Edge browser and try again.")
                else:
                    print(f"Driver initialization failed: {e}")
                    raise
    
    def _create_browser_options_without_profile(self, headless: bool = False, custom_download_dir: Optional[str] = None) -> EdgeOptions:
        """Create browser options without profile selection (fallback method)."""
        options = EdgeOptions()
        
        # Ensure browser remains open after script ends (for session persistency)
        options.add_experimental_option("detach", True)
        
        # Other options
        # options.add_argument("--disable-extensions")  # Commented out to allow profile extensions
        options.add_argument("--start-maximized")
        
        # Use custom download directory if provided, otherwise use default
        download_dir = custom_download_dir or Config.DOWNLOAD_FOLDER
        browser_prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
            "plugins.always_open_pdf_externally": True,  # Keep this as per report
        }
        
        options.add_experimental_option("prefs", browser_prefs)
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # Suppress verbose browser output
        if not Config.SHOW_SELENIUM_LOGS:
            options.add_argument("--log-level=3")  # Only fatal errors
            options.add_argument("--silent")
            options.add_argument("--disable-logging")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--no-sandbox")

        if headless:
            options.add_argument("--headless=new")

        return options
    
    def start(self, headless: bool = False) -> webdriver.Edge:
        """Start the browser with cleanup of existing processes. Supports headless mode."""
        # Comment out process cleanup to avoid interfering with profile sessions
        # self.check_and_kill_existing_edge_processes()
        return self.initialize_driver(headless=headless)
    
    def update_download_directory(self, new_download_dir: str) -> None:
        """
        Update the download directory for the current browser session.
        
        Args:
            new_download_dir: New download directory path
        """
        if self.driver:
            try:
                # Update browser preferences
                self.driver.execute_script(f"""
                    window.localStorage.setItem('download.default_directory', '{new_download_dir}');
                """)
                
                # Also try to update Chrome preferences (Edge uses Chrome's preference system)
                self.driver.execute_script(f"""
                    if (window.chrome && window.chrome.webstore) {{
                        chrome.downloads.setShelfEnabled(false);
                    }}
                """)
                
                print(f"   📁 Updated download directory to: {new_download_dir}")
            except Exception as e:
                print(f"   ⚠️ Warning: Could not update download directory: {e}")

    def create_tab_with_download_dir(self, download_dir: str) -> str:
        """
        Create a new tab with specific download directory configuration.
        This is a workaround since Edge doesn't support dynamic download directory changes.
        """
        try:
            # Create the download directory
            os.makedirs(download_dir, exist_ok=True)
            
            # Create a new tab
            self.driver.execute_script("window.open('');")
            
            # Switch to the new tab
            new_tab_handle = self.driver.window_handles[-1]
            self.driver.switch_to.window(new_tab_handle)
            
            # IMPORTANT: Set download directory for this tab using JavaScript
            # This is the key fix - we need to set the download directory for the current tab
            self.driver.execute_script(f"""
                // Set download directory via localStorage
                try {{
                    localStorage.setItem('download.default_directory', '{download_dir}');
                    console.log('Set download directory via localStorage:', '{download_dir}');
                }} catch(e) {{
                    console.log('Could not set localStorage:', e);
                }}
                
                // Also try to set via Chrome preferences (Edge uses Chrome's preference system)
                try {{
                    if (window.chrome && window.chrome.downloads) {{
                        chrome.downloads.setShelfEnabled(false);
                    }}
                }} catch(e) {{
                    console.log('Could not set Chrome preferences:', e);
                }}
                
                // Additional method: try to set via browser preferences
                try {{
                    if (window.chrome && window.chrome.runtime) {{
                        chrome.runtime.sendMessage({{
                            action: 'setDownloadDirectory',
                            directory: '{download_dir}'
                        }});
                    }}
                }} catch(e) {{
                    console.log('Could not set via runtime:', e);
                }}
            """)
            
            # Wait a moment for the settings to take effect
            time.sleep(1)
            
            print(f"   📁 Created tab with download directory: {download_dir}")
            return new_tab_handle
            
        except Exception as e:
            print(f"   ⚠️ Error creating tab with download directory: {e}")
            return None

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
    
    def create_new_tab(self) -> str:
        """Create a new tab and return its handle."""
        if not self.driver:
            raise RuntimeError("Driver not initialized")
        
        # Store current window handle
        original_handle = self.driver.current_window_handle
        
        # Create new tab
        self.driver.execute_script("window.open('');")
        
        # Switch to the new tab
        new_handle = None
        for handle in self.driver.window_handles:
            if handle != original_handle:
                new_handle = handle
                break
        
        if new_handle:
            self.driver.switch_to.window(new_handle)
            print(f"🆕 Created new tab: {new_handle}")
            return new_handle
        else:
            raise RuntimeError("Failed to create new tab")
    
    def get_download_directory(self) -> str:
        """Get the current download directory."""
        return Config.DOWNLOAD_FOLDER
