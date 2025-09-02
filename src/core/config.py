
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
    # DRIVER_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "drivers", "edgedriver_138")

    # File settings
    # Set to empty list to allow all file types, or add specific extensions to restrict
    # Common file types: [".pdf", ".msg", ".docx", ".xlsx", ".txt", ".jpg", ".png", ".zip", ".rar"]
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".msg", ".docx", ".xlsx", ".txt", ".jpg", ".png", ".zip", ".rar", ".csv", ".xml"]  # Allow common file types
    
    # Alternative: Allow all file types (uncomment to allow everything)
    # ALLOWED_EXTENSIONS: List[str] = []  # Empty list = allow all file types

    # Environment variables with defaults
    PAGE_DELAY = float(os.environ.get("PAGE_DELAY", "0"))
    # Edge user profile directory (for persistent sessions)
    _default_edge_profile = "~/Library/Application Support/Microsoft Edge" if os.name != 'nt' else "%LOCALAPPDATA%/Microsoft/Edge/User Data"
    EDGE_PROFILE_DIR = os.path.expanduser(os.environ.get("EDGE_PROFILE_DIR", _default_edge_profile))
    EDGE_PROFILE_NAME = os.environ.get("EDGE_PROFILE_NAME", "Default")  # e.g., 'Default', 'Profile 1'
    LOGIN_TIMEOUT = int(os.environ.get("LOGIN_TIMEOUT", "60"))
    HEADLESS = os.environ.get("HEADLESS", "false").lower() == "true"
    KEEP_BROWSER_OPEN = False

    # Whether to close the browser after execution (default: False)
    CLOSE_BROWSER_AFTER_EXECUTION = True

    # Limit number of POs to process (for testing or partial runs)
    PROCESS_MAX_POS = int(os.environ.get("PROCESS_MAX_POS", "0")) or None  # None means no limit

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

    # Output verbosity controls
    SHOW_EDGE_CRASH_STACKTRACE = False
    VERBOSE_OUTPUT = os.environ.get("VERBOSE_OUTPUT", "false").lower() == "true"
    SHOW_DETAILED_PROCESSING = os.environ.get("SHOW_DETAILED_PROCESSING", "false").lower() == "true"
    SHOW_SELENIUM_LOGS = os.environ.get("SHOW_SELENIUM_LOGS", "false").lower() == "true"
    
    # File handling controls
    OVERWRITE_EXISTING_FILES = os.environ.get("OVERWRITE_EXISTING_FILES", "true").lower() == "true"
    CREATE_BACKUP_BEFORE_OVERWRITE = os.environ.get("CREATE_BACKUP_BEFORE_OVERWRITE", "false").lower() == "true"
    
    # MSG processing controls
    FILTER_MSG_ARTIFACTS = os.environ.get("FILTER_MSG_ARTIFACTS", "true").lower() == "true"
    MSG_ARTIFACT_MIN_SIZE = int(os.environ.get("MSG_ARTIFACT_MIN_SIZE", "1024"))  # 1KB minimum
    MSG_IMAGE_MIN_SIZE = int(os.environ.get("MSG_IMAGE_MIN_SIZE", "5120"))  # 5KB minimum for images

    @classmethod
    def ensure_download_folder_exists(cls) -> None:
        """Ensure the download folder exists."""
        if not os.path.exists(cls.DOWNLOAD_FOLDER):
            os.makedirs(cls.DOWNLOAD_FOLDER)

    @classmethod
    def get_csv_file_path(cls) -> str:
        """Get the path to the input CSV file."""
        # Navigate from src/core/ to project root, then to data/input/
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        return os.path.join(project_root, "data", "input", "input.csv")
