"""
BrowserSession for tab-based PO processing.

This module provides the BrowserSession class for managing persistent
browser sessions with support for:
- Tab lifecycle management
- Authentication state preservation
- Session recovery capabilities
- Resource cleanup
"""

import time
from typing import Dict, Any, Optional, List
import structlog
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from .models import Tab, TabStatus, SessionStatus

# Resolve Coupa base/login URLs from central config (with .env support)
try:
    from ..lib.config import Config as _ExperimentalConfig  # type: ignore
    BASE_URL: str = getattr(_ExperimentalConfig, "BASE_URL", "https://unilever.coupahost.com")
    LOGIN_URL: str = getattr(_ExperimentalConfig, "LOGIN_URL", BASE_URL) or BASE_URL
except Exception:
    BASE_URL = "https://unilever.coupahost.com"
    LOGIN_URL = BASE_URL

logger = structlog.get_logger(__name__)


class BrowserSession:
    """
    Persistent browser session manager.
    
    Manages a long-lived WebDriver session with authentication
    state preservation and tab-based task processing.
    """
    
    def __init__(self):
        """Initialize browser session manager."""
        # WebDriver management
        self.driver: Optional[Any] = None
        self.main_window_handle: str = ""
        
        # Tab management
        self.active_tabs: Dict[str, Tab] = {}  # task_id -> Tab
        self.keeper_handle: Optional[str] = None
        
        # Session state
        self.status = SessionStatus.INITIALIZING
        self.session_cookies: Dict[str, Any] = {}
        self.authenticated = False
        
        # Timing
        self.startup_time = time.time()
        self.last_activity = time.time()
        
        # Error tracking
        self.error_count = 0
        self.last_error: Optional[str] = None
        
        logger.debug("BrowserSession initialized")

    def _log_window_handles(self, message: str) -> None:
        try:
            handles = self.driver.window_handles if self.driver else []
            logger.debug(
                message,
                handles=handles,
                main_handle=self.main_window_handle,
                keeper_handle=self.keeper_handle,
                active_tabs=list(self.active_tabs.keys()),
            )
        except Exception:
            logger.debug(message, handles="<unavailable>")

    def ensure_keeper_tab(self) -> bool:
        """Ensure a keeper tab exists to anchor the browser window."""
        if not self.driver:
            logger.warning("Cannot ensure keeper tab without WebDriver")
            return False

        try:
            handles = self.driver.window_handles
            if handles:
                if self.keeper_handle in handles:
                    return True
                if not self.keeper_handle:
                    self.keeper_handle = handles[0]
                    self.main_window_handle = handles[0]
                    return True

            # No keeper registered or existing; open a lightweight blank tab
            self.driver.execute_script("window.open('about:blank', '_blank');")
            handles = self.driver.window_handles
            if not handles:
                return False
            self.keeper_handle = handles[0]
            self.main_window_handle = handles[0]
            self.driver.switch_to.window(self.keeper_handle)
            self._log_window_handles("Keeper tab created")
            return True

        except Exception as exc:
            logger.error("Failed to ensure keeper tab", error=str(exc))
            return False

    def focus_main_window(self) -> bool:
        """Ensure the main (keeper) window handle is valid and focused."""
        if not self.driver:
            logger.warning("Cannot focus main window without WebDriver")
            return False

        try:
            handles = self.driver.window_handles
        except Exception as exc:
            logger.warning("Failed to retrieve window handles", error=str(exc))
            return False

        if not handles:
            logger.warning("No window handles available to focus")
            return False

        if self.keeper_handle and self.keeper_handle in handles:
            desired_handle = self.keeper_handle
        elif self.main_window_handle in handles:
            desired_handle = self.main_window_handle
        else:
            self._log_window_handles("Main handle missing; ensuring keeper")
            if not self.ensure_keeper_tab():
                return False
            desired_handle = self.keeper_handle or handles[0]

        try:
            self.driver.switch_to.window(desired_handle)
            if not self.main_window_handle:
                self.main_window_handle = desired_handle
            return True
        except Exception as exc:
            logger.warning("Failed to focus main window", error=str(exc))
            # Attempt to recover using the first available handle
            try:
                fallback = handles[0]
                self.driver.switch_to.window(fallback)
                self.main_window_handle = fallback
                self.keeper_handle = fallback
                return True
            except Exception as fallback_exc:
                logger.error("Unable to focus any window", error=str(fallback_exc))
                return False

    def authenticate(self) -> bool:
        """
        Establish authenticated session with Coupa.
        
        Returns:
            True if authentication successful, False otherwise
        """
        if not self.driver:
            logger.error("Cannot authenticate without WebDriver")
            return False
        
        try:
            logger.info("Authenticating with Coupa...", base_url=BASE_URL, login_url=LOGIN_URL)
            self.status = SessionStatus.INITIALIZING
            
            # Navigate to Coupa login page
            # This is configured per instance; prefer explicit COUPA_LOGIN_URL, else BASE_URL (SSO-friendly)
            self.driver.get(LOGIN_URL)
            
            # Wait for login page to load
            wait = WebDriverWait(self.driver, 10)
            
            # Check if already authenticated (redirected to dashboard)
            current_url = self.driver.current_url
            if "dashboard" in current_url or "home" in current_url:
                logger.info("Already authenticated with Coupa")
                self.authenticated = True
                self.status = SessionStatus.AUTHENTICATED
                self.last_activity = time.time()
                self.main_window_handle = self.driver.current_window_handle
                if not self.keeper_handle:
                    self.keeper_handle = self.main_window_handle
                self.focus_main_window()
                return True
            
            # Look for login form elements
            try:
                # Wait for email input field
                email_field = wait.until(
                    EC.presence_of_element_located((By.ID, "user_email"))
                )
                
                # Look for password field
                password_field = self.driver.find_element(By.ID, "user_password")
                
                # This is where you would input credentials
                # For security, credentials should come from environment variables
                # or secure configuration, not hardcoded
                
                # For now, we'll assume SSO or existing session
                logger.info("Login form detected - assuming SSO authentication")
                
                # Wait for potential SSO redirect or manual login
                time.sleep(5)
                
                # Check if authentication succeeded
                current_url = self.driver.current_url
                if "dashboard" in current_url or "home" in current_url:
                    self.authenticated = True
                    self.status = SessionStatus.AUTHENTICATED
                    logger.info("Authentication successful")
                    self.main_window_handle = self.driver.current_window_handle
                    if not self.keeper_handle:
                        self.keeper_handle = self.main_window_handle
                else:
                    logger.warning("Authentication may not be complete")
                    self.status = SessionStatus.ERROR
                    return False
                
            except TimeoutException:
                # No login form found - might already be authenticated
                logger.info("No login form found - checking authentication status")
                
                # Try to navigate to a protected page to test authentication
                self.driver.get(f"{BASE_URL}/order_headers")
                
                if "login" not in self.driver.current_url.lower():
                    self.authenticated = True
                    self.status = SessionStatus.AUTHENTICATED
                    logger.info("Authentication verified")
                    self.main_window_handle = self.driver.current_window_handle
                    if not self.keeper_handle:
                        self.keeper_handle = self.main_window_handle
                else:
                    logger.error("Authentication required but not completed")
                    self.status = SessionStatus.ERROR
                    return False
            
            # Store session cookies for potential recovery
            self.session_cookies = {cookie['name']: cookie['value'] 
                                  for cookie in self.driver.get_cookies()}
            
            self.last_activity = time.time()
            if not self.main_window_handle:
                self.main_window_handle = self.driver.current_window_handle
            if not self.keeper_handle:
                self.keeper_handle = self.main_window_handle
            self.focus_main_window()

            # Keep the keeper tab lightweight and neutral after auth so it doesn't land on Coupa pages
            try:
                if self.keeper_handle:
                    self.driver.switch_to.window(self.keeper_handle)
                    # Use about:blank to avoid extra loads while keeping session cookies in the profile
                    self.driver.get("about:blank")
            except Exception:
                # Non-fatal; just proceed
                pass
            return True
            
        except Exception as e:
            error_msg = f"Authentication failed: {str(e)}"
            logger.error(error_msg)
            self.last_error = error_msg
            self.error_count += 1
            self.status = SessionStatus.ERROR
            return False
    
    def create_tab(self, task_id: str) -> str:
        """
        Create new tab for PO processing.
        
        Args:
            task_id: Unique identifier for the task
            
        Returns:
            Window handle for the new tab
            
        Raises:
            RuntimeError: If tab creation fails
        """
        if not self.driver:
            raise RuntimeError("Cannot create tab without WebDriver")
        
        try:
            logger.debug("Creating new tab", task_id=task_id)

            # Keeper tab must exist before we spawn worker tabs
            self.ensure_keeper_tab()
            self.focus_main_window()

            # Capture current handles and open a new tab
            prev_handles = set(self.driver.window_handles)
            self.driver.execute_script("window.open('about:blank', '_blank');")
            
            # Determine the new handle reliably via set difference
            new_handles = set(self.driver.window_handles)
            created = list(new_handles - prev_handles)
            new_handle = created[0] if created else None

            # Fallback: search for a handle that's not main/keeper and not already tracked
            if not new_handle:
                for handle in self.driver.window_handles:
                    if handle not in (self.main_window_handle, self.keeper_handle) and \
                       handle not in [tab.window_handle for tab in self.active_tabs.values()]:
                        new_handle = handle
                        break

            if not new_handle:
                raise RuntimeError("Failed to create new tab")

            # Switch to new tab
            self.driver.switch_to.window(new_handle)

            # Create Tab model and register
            tab = Tab(
                window_handle=new_handle,
                task_id=task_id,
                po_number=""  # Will be set when task is assigned
            )
            self.active_tabs[task_id] = tab

            self.last_activity = time.time()
            self._log_window_handles("Worker tab created")
            logger.debug("Tab created successfully", task_id=task_id, handle=new_handle)

            return new_handle

        except Exception as e:
            error_msg = f"Failed to create tab: {str(e)}"
            logger.error(error_msg, task_id=task_id)
            self.last_error = error_msg
            self.error_count += 1
            raise RuntimeError(error_msg) from e
    
    def close_tab(self, tab_handle: str) -> None:
        """
        Close tab and cleanup resources.
        
        Args:
            tab_handle: Window handle of tab to close
        """
        if not self.driver:
            logger.warning("Cannot close tab without WebDriver")
            return
        
        try:
            logger.debug("Closing tab", handle=tab_handle)

            # Never close the keeper or the main window directly
            if tab_handle in (self.keeper_handle, self.main_window_handle):
                logger.debug("Refusing to close keeper/main tab", handle=tab_handle)
                self.focus_main_window()
                return

            # Find the tab by handle
            task_id = None
            for tid, tab in self.active_tabs.items():
                if tab.window_handle == tab_handle:
                    task_id = tid
                    break
            
            # Switch to the tab and close it
            if tab_handle in self.driver.window_handles:
                self.driver.switch_to.window(tab_handle)
                self.driver.close()
            
            # Remove from active tabs
            if task_id:
                tab = self.active_tabs[task_id]
                tab.status = TabStatus.CLOSED
                del self.active_tabs[task_id]
                logger.debug("Tab closed and removed", task_id=task_id)
            
            # Always refocus the main window after closing a tab
            self.focus_main_window()
            self._log_window_handles("Worker tab closed")
            # Ensure keeper tab still exists after close
            if not self.ensure_keeper_tab():
                logger.warning("Keeper tab missing after close; attempted recreation failed")

            self.last_activity = time.time()
            
        except Exception as e:
            error_msg = f"Error closing tab: {str(e)}"
            logger.warning(error_msg, handle=tab_handle)
            self.last_error = error_msg
            self.error_count += 1
    
    def switch_to_tab(self, task_id: str) -> bool:
        """
        Switch to specific tab by task ID.
        
        Args:
            task_id: Task identifier for the tab
            
        Returns:
            True if switch successful, False otherwise
        """
        if not self.driver:
            logger.error("Cannot switch tabs without WebDriver")
            return False
        
        if task_id not in self.active_tabs:
            logger.error("Tab not found", task_id=task_id)
            return False
        
        try:
            tab = self.active_tabs[task_id]
            self.driver.switch_to.window(tab.window_handle)
            self.last_activity = time.time()
            return True
            
        except Exception as e:
            logger.error("Failed to switch to tab", task_id=task_id, error=str(e))
            return False
    
    def switch_to_main_window(self) -> bool:
        """
        Switch back to main browser window.
        
        Returns:
            True if switch successful, False otherwise
        """
        if not self.driver:
            logger.error("Cannot switch to main window without WebDriver")
            return False
        
        try:
            self.driver.switch_to.window(self.main_window_handle)
            self.last_activity = time.time()
            return True
            
        except Exception as e:
            logger.error("Failed to switch to main window", error=str(e))
            return False
    
    def navigate_to_po(self, po_number: str, task_id: str) -> bool:
        """
        Navigate to specific PO page in given tab.
        
        Args:
            po_number: Purchase order number
            task_id: Task identifier for the tab
            
        Returns:
            True if navigation successful, False otherwise
        """
        if not self.driver or task_id not in self.active_tabs:
            return False
        
        try:
            # Switch to the tab
            if not self.switch_to_tab(task_id):
                return False
            
            # Update tab with PO number
            tab = self.active_tabs[task_id]
            tab.po_number = po_number
            tab.status = TabStatus.LOADING
            
            # Navigate to PO page
            po_url = f"{BASE_URL}/order_headers/{po_number}"
            self.driver.get(po_url)
            
            # Wait for page to load
            wait = WebDriverWait(self.driver, 10)
            wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            
            # Check if page loaded successfully
            current_url = self.driver.current_url
            if po_number in current_url:
                tab.status = TabStatus.PROCESSING
                logger.debug("Navigated to PO successfully", po_number=po_number, task_id=task_id)
                return True
            else:
                tab.status = TabStatus.ERROR
                tab.mark_error(f"Failed to navigate to PO {po_number}")
                logger.error("PO navigation failed", po_number=po_number, current_url=current_url)
                return False
            
        except TimeoutException:
            if task_id in self.active_tabs:
                self.active_tabs[task_id].mark_error(f"Timeout loading PO {po_number}")
            logger.error("Timeout navigating to PO", po_number=po_number)
            return False
            
        except Exception as e:
            if task_id in self.active_tabs:
                self.active_tabs[task_id].mark_error(f"Navigation error: {str(e)}")
            logger.error("Error navigating to PO", po_number=po_number, error=str(e))
            return False
    
    def is_page_ready(self, task_id: str) -> bool:
        """
        Check if page is ready for processing in given tab.
        
        Args:
            task_id: Task identifier for the tab
            
        Returns:
            True if page is ready, False otherwise
        """
        if not self.driver or task_id not in self.active_tabs:
            return False
        
        try:
            if not self.switch_to_tab(task_id):
                return False
            
            # Check document ready state
            ready_state = self.driver.execute_script("return document.readyState")
            if ready_state != "complete":
                return False
            
            # Check for common error indicators
            page_source = self.driver.page_source.lower()
            error_indicators = ["error", "not found", "access denied", "unauthorized"]
            
            for indicator in error_indicators:
                if indicator in page_source:
                    logger.warning("Error indicator found on page", 
                                 indicator=indicator, task_id=task_id)
                    return False
            
            return True
            
        except Exception as e:
            logger.error("Error checking page readiness", task_id=task_id, error=str(e))
            return False
    
    def recover_session(self) -> bool:
        """
        Attempt to recover from session errors.
        
        Returns:
            True if recovery successful, False otherwise
        """
        logger.info("Attempting session recovery")
        self.status = SessionStatus.RECOVERING
        
        try:
            # Check if driver is still responsive
            if self.driver:
                try:
                    current_url = self.driver.current_url
                    logger.debug("Driver responsive", current_url=current_url)
                except:
                    logger.warning("Driver not responsive, requiring re-authentication")
                    return self.authenticate()
            
            # Try to restore session using cookies
            if self.session_cookies and self.driver:
                try:
                    # Navigate to main page
                    self.driver.get(BASE_URL)
                    
                    # Restore cookies
                    for name, value in self.session_cookies.items():
                        try:
                            self.driver.add_cookie({'name': name, 'value': value})
                        except:
                            pass  # Some cookies might not be valid
                    
                    # Refresh to apply cookies
                    self.driver.refresh()
                    
                    # Test authentication
                    if self.authenticate():
                        self.status = SessionStatus.ACTIVE
                        logger.info("Session recovery successful")
                        return True
                    
                except Exception as e:
                    logger.warning("Cookie-based recovery failed", error=str(e))
            
            # If all else fails, try fresh authentication
            success = self.authenticate()
            if success:
                self.status = SessionStatus.ACTIVE
                logger.info("Session recovery via re-authentication successful")
            else:
                self.status = SessionStatus.ERROR
                logger.error("Session recovery failed")
            
            return success
            
        except Exception as e:
            logger.error("Session recovery failed", error=str(e))
            self.status = SessionStatus.ERROR
            self.last_error = f"Recovery failed: {str(e)}"
            return False
    
    def cleanup_all_tabs(self) -> None:
        """Close all tabs except main window."""
        if not self.driver:
            return
        
        logger.debug("Cleaning up all tabs")
        
        # Close all active tabs
        for task_id in list(self.active_tabs.keys()):
            tab = self.active_tabs[task_id]
            self.close_tab(tab.window_handle)
        
        # Switch back to main window
        self.switch_to_main_window()
    
    def get_uptime(self) -> float:
        """Get session uptime in seconds."""
        return time.time() - self.startup_time
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive session statistics.
        
        Returns:
            Dictionary containing session stats
        """
        active_tab_count = len(self.active_tabs)
        
        return {
            'status': self.status.value,
            'authenticated': self.authenticated,
            'uptime_seconds': self.get_uptime(),
            'last_activity': self.last_activity,
            'active_tabs': active_tab_count,
            'error_count': self.error_count,
            'last_error': self.last_error,
            'main_window_handle': self.main_window_handle,
            'has_driver': self.driver is not None
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary representation."""
        tab_info = {}
        for task_id, tab in self.active_tabs.items():
            tab_info[task_id] = tab.to_dict()
        
        return {
            'main_window_handle': self.main_window_handle,
            'active_tabs': tab_info,
            'status': self.status.value,
            'authenticated': self.authenticated,
            'startup_time': self.startup_time,
            'last_activity': self.last_activity,
            'error_count': self.error_count,
            'last_error': self.last_error,
            'uptime_seconds': self.get_uptime(),
            'has_driver': self.driver is not None
        }
