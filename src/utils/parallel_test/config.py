"""
Configuration module for Coupa Downloads automation.
Handles all settings, environment variables, and constants.
"""

import os
from typing import List


class Config:
    """Configuration class following Single Responsibility Principle."""

    # Base URLs and paths
    BASE_URL = "https://unilever.coupahost.com"
    # Define project root dynamically
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    INPUT_DIR = os.path.join(PROJECT_ROOT, "data", "input")
    DOWNLOAD_FOLDER = os.path.expanduser("~/Downloads/CoupaDownloads/Temp")  # Temporary download folder

    # File settings
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".msg", ".docx", ".xlsx", ".txt", ".jpg", ".png", ".zip", ".rar", ".csv", ".xml"]

    # Environment variables with defaults
    PAGE_DELAY = float(os.environ.get("PAGE_DELAY", "0"))
    _default_edge_profile = "~/Library/Application Support/Microsoft Edge" if os.name != 'nt' else "%LOCALAPPDATA%/Microsoft/Edge/User Data"
    EDGE_PROFILE_DIR = os.path.expanduser(os.environ.get("EDGE_PROFILE_DIR", _default_edge_profile))
    EDGE_PROFILE_NAME = os.environ.get("EDGE_PROFILE_NAME", "Default")
    LOGIN_TIMEOUT = int(os.environ.get("LOGIN_TIMEOUT", "60"))
    HEADLESS = os.environ.get("HEADLESS", "false").lower() == "true"
    KEEP_BROWSER_OPEN = False
    CLOSE_BROWSER_AFTER_EXECUTION = True
    PROCESS_MAX_POS = int(os.environ.get("PROCESS_MAX_POS", "3")) or None
    RANDOM_SAMPLE_POS = int(os.environ.get("RANDOM_SAMPLE_POS", "3")) or None

    # Browser settings
    BROWSER_OPTIONS = {
        "download.default_directory": DOWNLOAD_FOLDER,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False,
    }

    # CSS Selectors
    ATTACHMENT_SELECTOR = "div[class*='commentAttachments'] a[href*='attachment_file'], div[class*='attachment'] a[href*='attachment_file'], div[class*='attachment'] a[href*='download'], div[class*='attachment'] a[href*='attachment'], span[aria-label*='file attachment'], span[role='button'][aria-label*='file attachment'], span[title*='.pdf'], span[title*='.docx'], span[title*='.msg']"
    SUPPLIER_NAME_CSS_SELECTORS = [
        "span[data-supplier-name]",
        "span[class*='supplier-name']",
        ".supplier-info span",
        "[data-testid*='supplier'] span",
        "section:nth-of-type(2) div:nth-of-type(2) span:nth-of-type(3)",
        "section div[class*='supplier'] span",
        "section span:contains('supplier')",
        "div[class*='po-detail'] span:nth-child(3)"
    ]
    SUPPLIER_NAME_XPATH = "/html/body/div[1]/div[5]/div/div/div[4]/div/div[3]/section[2]/div[2]/div[1]/div/span[3]"

    # Timeouts
    PAGE_LOAD_TIMEOUT = 15
    ATTACHMENT_WAIT_TIMEOUT = 25  # Increased timeout for first tab (was 15)
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
    MSG_ARTIFACT_MIN_SIZE = int(os.environ.get("MSG_ARTIFACT_MIN_SIZE", "1024"))
    MSG_IMAGE_MIN_SIZE = int(os.environ.get("MSG_IMAGE_MIN_SIZE", "5120"))

    # Parallel processing settings
    MAX_WORKERS = 5  # Number of parallel tabs (increased for better performance)
    MAX_PARALLEL_TABS = 5  # Maximum number of tabs open simultaneously
    TAB_TIMEOUT = 30  # Timeout for tab operations
    TAB_SWITCH_DELAY = 3  # Delay between tab switches (increased for stability)

    @classmethod
    def ensure_download_folder_exists(cls) -> None:
        if not os.path.exists(cls.DOWNLOAD_FOLDER):
            os.makedirs(cls.DOWNLOAD_FOLDER)

    @classmethod
    def get_csv_file_path(cls) -> str:
        return os.path.join(cls.INPUT_DIR, "input.csv")
