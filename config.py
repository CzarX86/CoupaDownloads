
"""
Configuration module for Coupa Downloads automation.
Handles all settings, environment variables, and constants.
"""

import os
from typing import List


class Config:
    """Configuration class following Single Responsibility Principle."""

    # Base URLs and paths
    BASE_URL = "https://unilever.coupahost.com/order_headers/{}"
    DOWNLOAD_FOLDER = os.path.expanduser("~/Downloads/CoupaDownloads")
    DRIVER_PATH = os.path.join(os.path.dirname(__file__), "drivers", "edgedriver_138")

    # File settings
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".msg", ".docx"]

    # Environment variables with defaults
    PAGE_DELAY = float(os.environ.get("PAGE_DELAY", "0"))
    # Edge user profile directory (for persistent sessions)
    EDGE_PROFILE_DIR = os.path.expanduser(os.environ.get("EDGE_PROFILE_DIR", "~/Library/Application Support/Microsoft Edge"))
    EDGE_PROFILE_NAME = os.environ.get("EDGE_PROFILE_NAME", "Default")  # e.g., 'Default', 'Profile 1'
    LOGIN_TIMEOUT = int(os.environ.get("LOGIN_TIMEOUT", "60"))
    HEADLESS = os.environ.get("HEADLESS", "false").lower() == "true"
    KEEP_BROWSER_OPEN = False

    # Whether to close the browser after execution (default: False)
    CLOSE_BROWSER_AFTER_EXECUTION = True

    # Limit number of POs to process (for testing or partial runs)
    PROCESS_MAX_POS = int(os.environ.get("PROCESS_MAX_POS", "10")) or None  # None means no limit

    # Browser settings
    BROWSER_OPTIONS = {
        "download.default_directory": DOWNLOAD_FOLDER,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False,
    }

    # CSS Selectors
    ATTACHMENT_SELECTOR = "span[aria-label*='file attachment'], span[role='button'][aria-label*='file attachment'], span[title*='.pdf'], span[title*='.docx'], span[title*='.msg']"
    
    # Supplier name selectors (CSS preferred, XPath as fallback)
    SUPPLIER_NAME_CSS_SELECTORS = [
        # Try semantic selectors first (most robust)
        "span[data-supplier-name]",
        "span[class*='supplier-name']",
        ".supplier-info span",
        "[data-testid*='supplier'] span",
        
        # Try structural selectors (more flexible than XPath)
        "section:nth-of-type(2) div:nth-of-type(2) span:nth-of-type(3)",
        "section div[class*='supplier'] span",
        
        # Generic fallbacks
        "section span:contains('supplier')",
        "div[class*='po-detail'] span:nth-child(3)"
    ]
    
    # XPath as final fallback (your original)
    SUPPLIER_NAME_XPATH = "/html/body/div[1]/div[5]/div/div/div[4]/div/div[3]/section[2]/div[2]/div[1]/div/span[3]"

    # Timeouts
    PAGE_LOAD_TIMEOUT = 15
    ATTACHMENT_WAIT_TIMEOUT = 10
    DOWNLOAD_WAIT_TIMEOUT = 30

    # Toggle Edge WebDriver crash stacktrace reporting
    SHOW_EDGE_CRASH_STACKTRACE = False

    @classmethod
    def ensure_download_folder_exists(cls) -> None:
        """Ensure the download folder exists."""
        if not os.path.exists(cls.DOWNLOAD_FOLDER):
            os.makedirs(cls.DOWNLOAD_FOLDER)

    @classmethod
    def get_csv_file_path(cls) -> str:
        """Get the path to the input CSV file."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(script_dir, "input.csv")
