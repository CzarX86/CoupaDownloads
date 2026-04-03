"""
Browser management module for Coupa Downloads automation.
Handles WebDriver setup, cleanup, and process management.
"""

import os
import multiprocessing as mp
import signal
import subprocess
import sys
import time
from typing import Optional

from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService

from ..config.app_config import Config
from .driver_manager import DriverManager
from .models import HeadlessConfiguration, BrowserInstance, create_browser_instance_for_main_process


class HeadlessInitializationError(Exception):
    """Raised when headless browser initialization fails."""
    
    def __init__(self, attempt_number: int, original_error: str):
        self.attempt_number = attempt_number
        self.original_error = original_error
        super().__init__(f"Headless initialization failed on attempt {attempt_number}: {original_error}")


class UserFallbackChoice:
    """Handles user choice when headless mode fails."""
    
    VISIBLE_MODE = "visible"
    STOP_EXECUTION = "stop"
    
    @staticmethod
    def prompt_user() -> str:
        """Prompt user to choose fallback option."""
        print("\n⚠️ Headless mode initialization failed after retry.")
        print("Please choose how to proceed:")
        print("  1. Continue with visible browser (v)")
        print("  2. Stop execution (s)")
        
        while True:
            choice = input("Enter choice (v/s): ").lower().strip()
            if choice in ['v', 'visible']:
                return UserFallbackChoice.VISIBLE_MODE
            elif choice in ['s', 'stop']:
                return UserFallbackChoice.STOP_EXECUTION
            else:
                print("Invalid choice. Please enter 'v' for visible or 's' to stop.")


class BrowserManager:
    """Manages browser lifecycle following Single Responsibility Principle."""
    
    def __init__(self):
        self.driver: Optional[webdriver.Edge] = None
        self.driver_manager = DriverManager()
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        # Only install handlers in the main process to avoid noisy duplicates
        try:
            if mp.current_process().name == "MainProcess":
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
        except Exception:
            # Best-effort only
            pass
    
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
    
    def _create_browser_options(self, headless: bool = False, custom_download_dir: Optional[str] = None, custom_profile_dir: Optional[str] = None) -> EdgeOptions:
        """Create and configure browser options. Supports headless mode, custom download directory, and profile isolation."""
        options = EdgeOptions()
        
        # Profile isolation support for parallel processing
        if custom_profile_dir:
            # Use custom profile directory for isolated workers
            options.add_argument(f"--user-data-dir={custom_profile_dir}")
            # Use the correct profile name (usually 'Default') to match the cloned content
            p_name = Config.EDGE_PROFILE_NAME or 'Default'
            options.add_argument(f"--profile-directory={p_name}")
            print(f"🔧 Using isolated profile: {custom_profile_dir} with profile name: {p_name}")
        elif Config.USE_PROFILE and Config.EDGE_PROFILE_DIR:
            # Use default profile configuration
            options.add_argument(f"--user-data-dir={Config.EDGE_PROFILE_DIR}")
            options.add_argument(f"--profile-directory={Config.EDGE_PROFILE_NAME}")
        
        # Do NOT detach: ensure WebDriver controls lifecycle to avoid orphaned processes
        options.add_experimental_option("detach", False)
        
        # Other options after profile setup
        # options.add_argument("--disable-extensions")  # Commented out to allow profile extensions
        options.add_argument("--start-maximized")
        
        # Use custom download directory if provided, otherwise use default
        base_dir = custom_download_dir or Config.DOWNLOAD_FOLDER
        download_dir = os.path.abspath(os.path.expanduser(base_dir))
        browser_prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
            "plugins.always_open_pdf_externally": True,  # Keep this as per report
        }
        try:
            print(f"[browser] prefs download.default_directory = {download_dir}")
        except Exception:
            pass
        
        options.add_experimental_option("prefs", browser_prefs)
        # Enable CDP performance log so Page.downloadWillBegin / Page.downloadProgress
        # events can be consumed via driver.get_log("performance").
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
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
        # Get driver path automatically (download if needed)
        driver_path = self.driver_manager.get_driver_path()
        
        try:
            # Optionally kill existing processes (avoids profile locks)
            if Config.CLOSE_EDGE_PROCESSES:
                self.check_and_kill_existing_edge_processes()
            
            # Verify driver works
            if not self.driver_manager.verify_driver(driver_path):
                raise RuntimeError("EdgeDriver verification failed")
            
            options = self._create_browser_options(headless=headless, custom_download_dir=download_dir)
            
            # Configure service with log suppression
            service = EdgeService(
                executable_path=driver_path,
                log_output=(subprocess.DEVNULL if not Config.SHOW_SELENIUM_LOGS else sys.stderr)
            )
            
            self.driver = webdriver.Edge(service=service, options=options)
            # Force-set download directory via DevTools to override any profile prefs
            try:
                self.update_download_directory(download_dir)
            except Exception:
                pass
            print(f"✅ Using Edge WebDriver with download dir '{download_dir}': {driver_path}")
            return self.driver
        except Exception as e:
            if "user data directory is already in use" in str(e):
                print("⚠️ Profile directory is already in use. Falling back to default browser session.")
                # Retry without profile options
                options = self._create_browser_options_without_profile(headless=headless, custom_download_dir=download_dir)
                service = EdgeService(
                    executable_path=driver_path,
                    log_output=(subprocess.DEVNULL if not Config.SHOW_SELENIUM_LOGS else sys.stderr)
                )
                self.driver = webdriver.Edge(service=service, options=options)
                print(f"✅ Using Edge WebDriver without profile (download dir '{download_dir}'): {driver_path}")
                return self.driver
            else:
                print(f"❌ Driver initialization failed: {e}")
                raise

    def initialize_driver_with_profile(self, headless: bool = False, profile_dir: Optional[str] = None, download_dir: Optional[str] = None) -> webdriver.Edge:
        """Initialize the WebDriver with isolated profile for parallel processing."""
        # Get driver path automatically (download if needed)
        driver_path = self.driver_manager.get_driver_path()
        
        try:
            # Create browser options with profile isolation
            options = self._create_browser_options(
                headless=headless, 
                custom_download_dir=os.path.abspath(os.path.expanduser(download_dir or Config.DOWNLOAD_FOLDER)),
                custom_profile_dir=profile_dir
            )
            
            # Configure service with log suppression
            service = EdgeService(
                executable_path=driver_path,
                log_output=(subprocess.DEVNULL if not Config.SHOW_SELENIUM_LOGS else sys.stderr)
            )
            
            self.driver = webdriver.Edge(service=service, options=options)
            # Force-set download directory via DevTools to override any profile prefs
            try:
                self.update_download_directory(download_dir or Config.DOWNLOAD_FOLDER)
            except Exception:
                pass
            
            profile_info = f" with profile {profile_dir}" if profile_dir else ""
            download_info = f" and download dir '{download_dir}'" if download_dir else ""
            print(f"✅ Using Edge WebDriver{profile_info}{download_info}: {driver_path}")
            
            return self.driver
            
        except Exception as e:
            print(f"❌ Driver initialization with profile failed: {e}")
            # For parallel workers, don't fallback to avoid conflicts
            raise

    def initialize_driver(self, headless: bool = False) -> webdriver.Edge:
        """Initialize the WebDriver with proper error handling and retry logic. Supports headless mode."""
        # Create browser instance for tracking
        browser_instance = BrowserInstance(headless_mode=headless)
        
        # First attempt
        try:
            return self._attempt_driver_initialization(headless, browser_instance)
        except Exception as first_error:
            print(f"⚠️ Browser initialization failed (attempt 1): {first_error}")
            
            # Only retry if headless mode was requested
            if headless:
                print("🔄 Retrying headless browser initialization...")
                browser_instance = browser_instance.increment_attempts()
                
                try:
                    return self._attempt_driver_initialization(headless, browser_instance)
                except Exception as retry_error:
                    print(f"❌ Headless retry failed (attempt 2): {retry_error}")
                    
                    # Prompt user for fallback choice
                    choice = UserFallbackChoice.prompt_user()
                    
                    if choice == UserFallbackChoice.STOP_EXECUTION:
                        raise HeadlessInitializationError(2, str(retry_error))
                    elif choice == UserFallbackChoice.VISIBLE_MODE:
                        print("🔄 Attempting visible mode as fallback...")
                        browser_instance = browser_instance.update_headless_mode(False)
                        return self._attempt_driver_initialization(False, browser_instance)
                    else:
                        raise HeadlessInitializationError(2, str(retry_error))
            else:
                # Re-raise original error for non-headless failures
                raise first_error
    
    def _attempt_driver_initialization(self, headless: bool, browser_instance: BrowserInstance) -> webdriver.Edge:
        """Attempt to initialize the WebDriver with given configuration."""
        # Get driver path automatically (download if needed)
        driver_path = self.driver_manager.get_driver_path()
        
        # Verify driver works
        if not self.driver_manager.verify_driver(driver_path):
            raise RuntimeError("EdgeDriver verification failed")
        
        options = self._create_browser_options(headless=headless)
        
        # Configure service with log suppression
        service = EdgeService(
            executable_path=driver_path,
            log_output=(subprocess.DEVNULL if not Config.SHOW_SELENIUM_LOGS else sys.stderr)
        )
        
        mode_str = "headless" if headless else "visible"
        attempt_str = f" (attempt {browser_instance.initialization_attempts})" if browser_instance.initialization_attempts > 1 else ""
        print(f"[browser] Launching Edge WebDriver in {mode_str} mode{attempt_str}...", flush=True)
        
        try:
            self.driver = webdriver.Edge(service=service, options=options)
            # Force-set download directory via DevTools to override any profile prefs
            try:
                self.update_download_directory(Config.DOWNLOAD_FOLDER)
            except Exception:
                pass
            print(f"✅ Using Edge WebDriver in {mode_str} mode: {driver_path}")
            return self.driver
        except Exception as e:
            if "user data directory is already in use" in str(e):
                print("⚠️ Profile directory is already in use. Falling back to default browser session.")
                # Retry without profile options
                options = self._create_browser_options_without_profile(headless=headless)
                service = EdgeService(
                    executable_path=driver_path,
                    log_output=(subprocess.DEVNULL if not Config.SHOW_SELENIUM_LOGS else sys.stderr)
                )
                print(f"[browser] Launching Edge WebDriver in {mode_str} mode (no profile)...", flush=True)
                self.driver = webdriver.Edge(service=service, options=options)
                print(f"✅ Using Edge WebDriver in {mode_str} mode without profile: {driver_path}")
                return self.driver
            else:
                raise e
    
    def _create_browser_options_without_profile(self, headless: bool = False, custom_download_dir: Optional[str] = None) -> EdgeOptions:
        """Create browser options without profile selection (fallback method)."""
        options = EdgeOptions()
        
        # Do NOT detach in fallback either
        options.add_experimental_option("detach", False)
        
        # Other options
        # options.add_argument("--disable-extensions")  # Commented out to allow profile extensions
        options.add_argument("--start-maximized")
        
        # Use custom download directory if provided, otherwise use default
        base_dir = custom_download_dir or Config.DOWNLOAD_FOLDER
        download_dir = os.path.abspath(os.path.expanduser(base_dir))
        browser_prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
            "plugins.always_open_pdf_externally": True,  # Keep this as per report
        }
        
        options.add_experimental_option("prefs", browser_prefs)
        # Enable CDP performance log so Page.downloadWillBegin / Page.downloadProgress
        # events can be consumed via driver.get_log("performance").
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
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
                # Expand ~ to ensure we have an absolute path
                expanded_dir = os.path.abspath(os.path.expanduser(new_download_dir))
                # Ensure directory exists
                os.makedirs(expanded_dir, exist_ok=True)

                # Preferred: Chromium DevTools Protocol - works on Edge (Chromium)
                try:
                    self.driver.execute_cdp_cmd(
                        "Page.setDownloadBehavior",
                        {"behavior": "allow", "downloadPath": expanded_dir,
                         "eventsEnabled": True}
                    )
                    print(f"   📁 Updated download directory via DevTools (Page) to: {expanded_dir}")
                    return
                except Exception as cdp_err:
                    print(f"   ⚠️ DevTools Page.setDownloadBehavior failed: {cdp_err}. Trying Browser.setDownloadBehavior.")
                    try:
                        self.driver.execute_cdp_cmd(
                            "Browser.setDownloadBehavior",
                            {"behavior": "allow", "downloadPath": expanded_dir}
                        )
                        print(f"   📁 Updated download directory via DevTools (Browser) to: {expanded_dir}")
                        return
                    except Exception as cdp_err2:
                        print(f"   ⚠️ DevTools Browser.setDownloadBehavior failed: {cdp_err2}.")

                # Both CDP methods failed — the download directory cannot be changed
                # at runtime.  Downloads will continue to go to the path that was
                # configured when the browser was launched (initial prefs).
                # This can cause files to land in the root download folder instead of
                # the expected PO subfolder.
                print(
                    f"   ❌ Could not redirect download directory to: {expanded_dir}\n"
                    f"   ❌ Both Page.setDownloadBehavior and Browser.setDownloadBehavior failed.\n"
                    f"   ❌ Files will be saved to the path set at browser launch. "
                    f"Check Edge/WebDriver version compatibility."
                )
            except Exception as e:
                print(f"   ⚠️ Warning: Could not update download directory: {e}")

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
    
    def clear_session(self) -> None:
        """Clear browser session data between POs to prevent contamination."""
        if not self.driver:
            print("⚠️ No driver to clear session")
            return

        try:
            # Clear cookies to prevent session contamination between POs
            self.driver.delete_all_cookies()
            print("🍪 Cleared all cookies")

            # Clear local storage
            try:
                self.driver.execute_script("window.localStorage.clear();")
                print("🗂️ Cleared local storage")
            except Exception:
                pass  # Not critical if this fails

            # Clear session storage
            try:
                self.driver.execute_script("window.sessionStorage.clear();")
                print("📋 Cleared session storage")
            except Exception:
                pass  # Not critical if this fails

            # Navigate to about:blank to reset page state
            try:
                self.driver.get("about:blank")
                print("🔄 Navigated to blank page")
            except Exception:
                pass  # Not critical if this fails

        except Exception as e:
            print(f"⚠️ Error clearing session: {e}")

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
