"""
Browser Orchestrator module.

Extracted from MainApp to handle all browser lifecycle operations,
including initialization, cleanup, and session management.
"""

import logging
from typing import Optional, Any
import threading

from ..lib.browser import BrowserManager
from ..lib.models import HeadlessConfiguration

logger = logging.getLogger(__name__)


class BrowserOrchestrator:
    """
    Manages browser lifecycle for CoupaDownloads.
    
    Responsibilities:
    - Browser initialization (single instance for sequential processing)
    - Download directory updates
    - Browser cleanup and shutdown
    - Thread-safe browser access
    
    This class was extracted from MainApp to improve separation of concerns
    and reduce class complexity.
    """
    
    def __init__(self, browser_manager: BrowserManager):
        """
        Initialize browser orchestrator.
        
        Args:
            browser_manager: BrowserManager instance for WebDriver control
        """
        self.browser_manager = browser_manager
        self.driver: Optional[Any] = None
        self.lock = threading.Lock()
        self._initialized = False
    
    def initialize_browser(self, headless: bool = True) -> Any:
        """
        Initialize browser if not already initialized.
        
        Args:
            headless: Whether to run browser in headless mode
            
        Returns:
            WebDriver instance
        """
        if not self.driver:
            logger.info("Initializing browser", extra={"headless": headless})
            with self.lock:
                if not self.driver:  # Double-check locking
                    self.browser_manager.initialize_driver(headless=headless)
                    self.driver = self.browser_manager.driver
                    self._initialized = True
                    logger.info("Browser initialized successfully")
        return self.driver
    
    def is_browser_responsive(self) -> bool:
        """
        Check if browser is still responsive.
        
        Returns:
            True if browser is responsive, False otherwise
        """
        if not self.driver:
            return False
        
        try:
            # Try to execute a simple command to check responsiveness
            self.driver.current_url
            return True
        except Exception as e:
            logger.debug("Browser not responsive", extra={"error": str(e)})
            return False
    
    def update_download_directory(self, path: str) -> None:
        """
        Update browser download directory.
        
        Args:
            path: New download directory path
        """
        if not self.driver:
            logger.warning("Cannot update download directory: browser not initialized")
            return
        
        try:
            self.browser_manager.update_download_directory(path)
            logger.debug("Download directory updated", extra={"path": path})
        except Exception as e:
            logger.warning(
                "Failed to update download directory",
                extra={"path": path, "error": str(e)}
            )
    
    def get_driver(self) -> Optional[Any]:
        """
        Get current driver instance.
        
        Returns:
            WebDriver instance or None if not initialized
        """
        return self.driver
    
    def cleanup(self, emergency: bool = False) -> None:
        """
        Cleanup browser resources.
        
        Args:
            emergency: If True, perform accelerated cleanup with minimal timeouts
        """
        if not self.driver:
            return
        
        logger.info("Closing browser", extra={"emergency": emergency})
        
        try:
            with self.lock:
                if self.driver:
                    self.browser_manager.cleanup()
                    self.driver = None
                    self._initialized = False
            logger.info("Browser closed successfully")
        except Exception as e:
            if emergency:
                logger.warning(
                    "Error during emergency browser cleanup (ignoring)",
                    extra={"error": str(e)}
                )
            else:
                logger.error("Error closing browser", extra={"error": str(e)})
                raise
    
    def is_initialized(self) -> bool:
        """
        Check if browser has been initialized.
        
        Returns:
            True if initialized, False otherwise
        """
        return self._initialized and self.driver is not None
    
    def execute_with_lock(self, operation: callable, *args, **kwargs) -> Any:
        """
        Execute a browser operation with thread-safe locking.
        
        Args:
            operation: Function to execute
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation
            
        Returns:
            Result of operation
        """
        with self.lock:
            if not self.driver:
                raise RuntimeError("Browser not initialized")
            return operation(self.driver, *args, **kwargs)
