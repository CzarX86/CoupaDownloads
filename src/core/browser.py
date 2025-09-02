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

from .config import Config
from .driver_manager import DriverManager


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
    
    def initialize_driver(self, headless: bool = False) -> webdriver.Edge:
        """Initialize the WebDriver with proper error handling. Supports headless mode."""
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
                print("⚠️ Profile directory is already in use. Falling back to default browser session.")
                # Retry without profile options
                options = self._create_browser_options_without_profile(headless=headless)
                service = EdgeService(
                    executable_path=driver_path,
                    log_output=subprocess.DEVNULL if not Config.SHOW_SELENIUM_LOGS else None
                )
                self.driver = webdriver.Edge(service=service, options=options)
                print(f"✅ Using Edge WebDriver without profile: {driver_path}")
                return self.driver
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
    
    def close_current_tab(self) -> None:
        """Close the current tab and switch back to the main tab."""
        if not self.driver:
            raise RuntimeError("Driver not initialized")
        
        try:
            current_handle = self.driver.current_window_handle
            all_handles = self.driver.window_handles
            
            if len(all_handles) <= 1:
                print("⚠️ Only one tab remaining, cannot close")
                return
            
            # Close current tab
            self.driver.close()
            print(f"🔒 Closed tab: {current_handle}")
            
            # Switch to the first remaining tab (should be the main tab)
            remaining_handles = [h for h in all_handles if h != current_handle]
            if remaining_handles:
                self.driver.switch_to.window(remaining_handles[0])
                print(f"🔄 Switched to main tab: {remaining_handles[0]}")
            else:
                print("⚠️ No remaining tabs to switch to")
                
        except Exception as e:
            print(f"⚠️ Error closing tab: {e}")
            # Try to switch to any available tab
            try:
                if self.driver.window_handles:
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    print("🔄 Recovered by switching to first available tab")
            except Exception as recovery_error:
                print(f"❌ Could not recover from tab error: {recovery_error}")
    
    def switch_to_main_tab(self) -> None:
        """Switch to the main tab (first tab)."""
        if not self.driver:
            raise RuntimeError("Driver not initialized")
        
        if self.driver.window_handles:
            main_handle = self.driver.window_handles[0]
            self.driver.switch_to.window(main_handle)
            print(f"🔄 Switched to main tab: {main_handle}")
    
    def switch_to_tab(self, tab_handle: str) -> None:
        """Switch to a specific tab by handle."""
        if not self.driver:
            raise RuntimeError("Driver not initialized")
        
        if tab_handle in self.driver.window_handles:
            self.driver.switch_to.window(tab_handle)
            print(f"🔄 Switched to tab: {tab_handle}")
        else:
            raise RuntimeError(f"Tab handle {tab_handle} not found")
    
    def keep_browser_open(self) -> None:
        """Keep the browser open instead of closing it."""
        if self.driver:
            print("🌐 Keeping browser open for persistent login session")
            print("💡 You can manually close the browser when done, or run the script again to continue processing")
            # Don't call cleanup() - let the browser stay open
        else:
            print("ℹ️ No browser instance to keep open")
    
    def force_cleanup(self) -> None:
        """Force cleanup and close browser (use when KEEP_BROWSER_OPEN is False)."""
        self.cleanup()
    
    def is_browser_responsive(self) -> bool:
        """Check if the browser is still responsive."""
        if not self.driver:
            return False
        
        try:
            # Try to get the current URL to test responsiveness
            self.driver.current_url
            return True
        except Exception:
            return False
    
    def ensure_browser_responsive(self) -> bool:
        """Ensure browser is responsive, try to recover if not."""
        if not self.is_browser_responsive():
            print("⚠️ Browser not responsive, attempting to recover...")
            try:
                # Try to switch to any available window
                if self.driver and self.driver.window_handles:
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    print("✅ Browser recovered")
                    return True
                else:
                    print("❌ No windows available")
                    return False
            except Exception as e:
                print(f"❌ Could not recover browser: {e}")
                return False
        return True 