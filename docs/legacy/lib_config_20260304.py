"""
Configuration module for Coupa Downloads automation (EXPERIMENTAL).

DEPRECATED: Use src.config.app_config.AppConfig instead.

This module is maintained for backward compatibility. All new code should use
the unified AppConfig class from src.config.app_config.

Migration guide:
    Old: from src.lib.config import Config
         config = Config()
    
    New: from src.config.app_config import AppConfig
         config = AppConfig()
"""

import os
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# Deprecation warning for the entire module
warnings.warn(
    "src.lib.config is deprecated. "
    "Use src.config.app_config.AppConfig instead. "
    "See docs/reports/REFACTORING_COMPLETE.md for migration guide.",
    DeprecationWarning,
    stacklevel=2
)


def generate_timestamped_download_folder(base_path: Optional[str] = None) -> str:
    """Generate a download folder with timestamp prefix.
    
    Format: yyyymmdd-hh"h"mm_CoupaDownloads
    Example: 20251002-14h30_CoupaDownloads
    
    Args:
        base_path: Base directory path (defaults to ~/Downloads)
    
    Returns:
        Full path to timestamped download folder
    """
    if base_path is None:
        base_path = str(Path.home() / "Downloads")
    
    # Generate timestamp in required format
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d-%Hh%M")
    
    # Create folder name with timestamp prefix
    folder_name = f"{timestamp}_CoupaDownloads"
    
    return str(Path(base_path) / folder_name)

# Compatibility: Re-export HeadlessConfiguration via a factory function signature
# used in contract/unit tests (accepts 'headless' kw while returning the real model)
try:
    from .models import HeadlessConfiguration as _HeadlessConfigurationModel

    def HeadlessConfiguration(headless: bool = True, source: str = "interactive_setup") -> _HeadlessConfigurationModel:  # type: ignore
        """Compatibility factory returning a HeadlessConfiguration model instance.

        Tests import HeadlessConfiguration from .lib.config and call it like a constructor
        with 'headless=True'. We return the actual dataclass instance from .lib.models.
        """
        return _HeadlessConfigurationModel(enabled=headless, source=source)
except Exception:
    # If models not available in certain import contexts, ignore; tests will skip.
    pass


class ExperimentalSettings(BaseSettings):
    """Strongly typed settings loaded from .env and defaults."""

    # Project paths
    PROJECT_ROOT: str = str(Path(__file__).resolve().parents[2])
    INPUT_DIR: str = str(Path(PROJECT_ROOT) / "data" / "input")
    # Default to a stable base folder; timestamping is applied at runtime in main
    DOWNLOAD_FOLDER: str = str(Path.home() / "Downloads" / "CoupaDownloads")

    # URLs and login
    BASE_URL: str = "https://unilever.coupahost.com"
    LOGIN_URL: Optional[str] = None
    LOGIN_TIMEOUT: int = 60

    # Profiles
    EDGE_PROFILE_DIR: str = str(Path.home() / "Library/Application Support/Microsoft Edge") if os.name != 'nt' else "%LOCALAPPDATA%/Microsoft/Edge/User Data"
    EDGE_PROFILE_NAME: str = "Default"
    USE_PROFILE: bool = True
    CLOSE_EDGE_PROCESSES: bool = True

    # Excel/input
    EXCEL_FILE_PATH: Optional[str] = None
    PAGE_DELAY: float = 0.0
    PROCESS_MAX_POS: Optional[int] = None
    RANDOM_SAMPLE_POS: Optional[int] = None

    # Parallel processing
    ENABLE_PARALLEL_PROCESSING: bool = True
    MAX_PARALLEL_WORKERS: int = 4
    PARALLEL_WORKER_TIMEOUT: int = 300
    PARALLEL_MIN_POS_THRESHOLD: int = 2
    PARALLEL_PROFILE_CLEANUP: bool = True
    USE_PROCESS_POOL: bool = False
    PROC_WORKERS: int = 4
    PROC_WORKERS_CAP: int = 16  # Relaxed default cap, overridden by ResourceAssessor
    RESOURCE_AWARE_SCALING: bool = True
    MIN_FREE_RAM_GB: float = 0.3  # Reduced for more permissive scaling
    EXECUTION_MODE: str = "standard"  # standard, filtered, no_js, direct_http

    # Batch Finalization
    BATCH_FINALIZATION_ENABLED: bool = True
    BATCH_FINALIZATION_INTERVAL: int = 30
    BATCH_FINALIZATION_INTERVAL: int = 5

    # Worker resource management
    WORKER_MEMORY_LIMIT_MB: int = 512
    WORKER_CPU_THRESHOLD: float = 0.8
    WORKER_PROFILE_SIZE_LIMIT_MB: int = 100

    # Driver manager
    EDGE_DRIVER_PATH: Optional[str] = "/Users/juliocezar/Dev/work/CoupaDownloads/drivers/msedgedriver"
    DRIVER_AUTO_DOWNLOAD: bool = True

    # Output verbosity and behavior
    VERBOSE_OUTPUT: bool = False
    SHOW_DETAILED_PROCESSING: bool = False
    SHOW_SELENIUM_LOGS: bool = False
    OVERWRITE_EXISTING_FILES: bool = True
    CREATE_BACKUP_BEFORE_OVERWRITE: bool = False
    FILTER_MSG_ARTIFACTS: bool = True
    MSG_ARTIFACT_MIN_SIZE: int = 1024
    MSG_IMAGE_MIN_SIZE: int = 5120
    MSG_TO_PDF_ENABLED: bool = True
    MSG_TO_PDF_OVERWRITE: bool = False
    # Force status suffix usage for consistent downstream folder processing
    ADD_STATUS_SUFFIX: bool = True

    # Error page checks
    ERROR_PAGE_CHECK_TIMEOUT: float = 2.0
    ERROR_PAGE_READY_CHECK_TIMEOUT: float = 1.0
    ERROR_PAGE_WAIT_POLL: float = 0.2
    EARLY_ERROR_CHECK_BEFORE_READY: bool = True

    model_config = SettingsConfigDict(env_file=str(Path(__file__).resolve().parents[2] / ".env"), env_file_encoding="utf-8")


_settings = ExperimentalSettings()


class Config:
    """Compatibility facade exposing settings as class attributes."""

    # Base URLs and paths
    PROJECT_ROOT = _settings.PROJECT_ROOT
    BASE_URL = _settings.BASE_URL
    LOGIN_URL = _settings.LOGIN_URL or _settings.BASE_URL
    INPUT_DIR = _settings.INPUT_DIR
    # Normalize download folder to expanded absolute path to avoid "~" literals
    DOWNLOAD_FOLDER = os.path.abspath(os.path.expanduser(_settings.DOWNLOAD_FOLDER))

    # File settings
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".msg", ".eml", ".docx", ".xlsx", ".txt", ".jpg", ".png", ".zip", ".rar", ".csv", ".xml"]

    # Core toggles
    PAGE_DELAY = _settings.PAGE_DELAY
    EDGE_PROFILE_DIR = os.path.expanduser(_settings.EDGE_PROFILE_DIR)
    EDGE_PROFILE_NAME = _settings.EDGE_PROFILE_NAME
    LOGIN_TIMEOUT = _settings.LOGIN_TIMEOUT
    KEEP_BROWSER_OPEN = False
    CLOSE_BROWSER_AFTER_EXECUTION = True
    PROCESS_MAX_POS = _settings.PROCESS_MAX_POS
    RANDOM_SAMPLE_POS = _settings.RANDOM_SAMPLE_POS
    EXCEL_FILE_PATH = _settings.EXCEL_FILE_PATH

    # Parallel processing settings
    ENABLE_PARALLEL_PROCESSING = _settings.ENABLE_PARALLEL_PROCESSING
    MAX_PARALLEL_WORKERS = _settings.MAX_PARALLEL_WORKERS
    PARALLEL_WORKER_TIMEOUT = _settings.PARALLEL_WORKER_TIMEOUT
    PARALLEL_MIN_POS_THRESHOLD = _settings.PARALLEL_MIN_POS_THRESHOLD
    PARALLEL_PROFILE_CLEANUP = _settings.PARALLEL_PROFILE_CLEANUP
    USE_PROCESS_POOL = _settings.USE_PROCESS_POOL
    PROC_WORKERS = _settings.PROC_WORKERS
    PROC_WORKERS_CAP = _settings.PROC_WORKERS_CAP
    RESOURCE_AWARE_SCALING = _settings.RESOURCE_AWARE_SCALING
    MIN_FREE_RAM_GB = _settings.MIN_FREE_RAM_GB
    EXECUTION_MODE = _settings.EXECUTION_MODE
    
    # Batch Finalization settings
    BATCH_FINALIZATION_ENABLED = _settings.BATCH_FINALIZATION_ENABLED
    BATCH_FINALIZATION_INTERVAL = _settings.BATCH_FINALIZATION_INTERVAL
    
    # Worker resource management
    WORKER_MEMORY_LIMIT_MB = _settings.WORKER_MEMORY_LIMIT_MB
    WORKER_CPU_THRESHOLD = _settings.WORKER_CPU_THRESHOLD
    WORKER_PROFILE_SIZE_LIMIT_MB = _settings.WORKER_PROFILE_SIZE_LIMIT_MB

    # Driver manager
    EDGE_DRIVER_PATH = _settings.EDGE_DRIVER_PATH
    DRIVER_AUTO_DOWNLOAD = _settings.DRIVER_AUTO_DOWNLOAD

    # Browser settings (constructed)
    BROWSER_OPTIONS = {
        "download.default_directory": DOWNLOAD_FOLDER,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False,
    }

    # CSS Selectors
    ATTACHMENT_SELECTOR = "a[href*='attachment'], a[href*='download'], [aria-label*='attachment'], [title*='attachment'], a[download]"
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
    PAGE_LOAD_TIMEOUT = 30  # Increased for stability
    ATTACHMENT_WAIT_TIMEOUT = 15
    DOWNLOAD_WAIT_TIMEOUT = 60 # Increased for larger files

    # Error page detection (Coupa "Oops/No Access" markers)
    ERROR_PAGE_MARKERS = [
        "Oops! We couldn't find what you wanted",
        "You are not authorized",
        "Access denied",
        "The page you were looking for doesn't exist",
        "Desculpe, não encontramos o que você procurava",
    ]
    ERROR_PAGE_CSS_SELECTORS = [
        "div.flash_error",
        "div.flash-error",
        "div.notice",
        "div#error_explanation",
    ]
    ERROR_PAGE_XPATH_SELECTORS = [
        "//div[contains(@class,'flash') and contains(.,'Oops')]",
        "//h1[contains(.,'Oops') or contains(.,'Sorry')]",
    ]
    ERROR_PAGE_CHECK_TIMEOUT = _settings.ERROR_PAGE_CHECK_TIMEOUT
    ERROR_PAGE_READY_CHECK_TIMEOUT = _settings.ERROR_PAGE_READY_CHECK_TIMEOUT
    ERROR_PAGE_WAIT_POLL = _settings.ERROR_PAGE_WAIT_POLL
    EARLY_ERROR_CHECK_BEFORE_READY = _settings.EARLY_ERROR_CHECK_BEFORE_READY

    # PR fallback navigation controls
    PR_FALLBACK_ENABLED = True
    PR_FALLBACK_LINK_TIMEOUT = 4.0
    PR_FALLBACK_LINK_POLL = 0.2
    PR_FALLBACK_READY_TIMEOUT = 8.0
    PR_LINK_CSS_SELECTORS = [
        "a[href*='/requisition_headers/']",
        "a[href*='requisition_header']",
        "a[data-testid*='requisition']",
        "a[data-qa*='requisition']",
        "a[href*='/req/']",
    ]
    PR_LINK_XPATH_CANDIDATES = [
        "//a[contains(@href,'/requisition_') or contains(@href,'/requisition-')]",
        "//a[contains(@href,'requisition_headers')]",
        "//a[contains(normalize-space(.),'Requisition')]",
        "//a[contains(normalize-space(.),'Requisição')]",
    ]
    PR_LINK_TEXT_CANDIDATES = [
        "Requisition",
        "Purchase Requisition",
        "Requisição",
        "Requisições",
    ]

    # Output verbosity controls
    SHOW_EDGE_CRASH_STACKTRACE = False
    VERBOSE_OUTPUT = _settings.VERBOSE_OUTPUT
    SHOW_DETAILED_PROCESSING = _settings.SHOW_DETAILED_PROCESSING
    SHOW_SELENIUM_LOGS = _settings.SHOW_SELENIUM_LOGS
    
    # File handling controls
    OVERWRITE_EXISTING_FILES = _settings.OVERWRITE_EXISTING_FILES
    CREATE_BACKUP_BEFORE_OVERWRITE = _settings.CREATE_BACKUP_BEFORE_OVERWRITE
    
    # MSG processing controls
    FILTER_MSG_ARTIFACTS = _settings.FILTER_MSG_ARTIFACTS
    MSG_ARTIFACT_MIN_SIZE = _settings.MSG_ARTIFACT_MIN_SIZE
    MSG_IMAGE_MIN_SIZE = _settings.MSG_IMAGE_MIN_SIZE
    MSG_TO_PDF_ENABLED = _settings.MSG_TO_PDF_ENABLED
    MSG_TO_PDF_OVERWRITE = _settings.MSG_TO_PDF_OVERWRITE

    # Folder naming controls
    ADD_STATUS_SUFFIX = _settings.ADD_STATUS_SUFFIX

    # Profile usage and startup behavior
    USE_PROFILE = _settings.USE_PROFILE
    CLOSE_EDGE_PROCESSES = _settings.CLOSE_EDGE_PROCESSES

    @classmethod
    def ensure_download_folder_exists(cls) -> None:
        path = os.path.abspath(os.path.expanduser(cls.DOWNLOAD_FOLDER))
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

    @classmethod
    def get_csv_file_path(cls) -> str:
        return os.path.join(cls.INPUT_DIR, "input.csv")

    @classmethod
    def validate_parallel_config(cls) -> bool:
        """Validate parallel processing configuration."""
        # Allow any positive worker count; optional cap via env MAX_PARALLEL_WORKERS_CAP
        if cls.MAX_PARALLEL_WORKERS < 1:
            print(f"⚠️ Warning: MAX_PARALLEL_WORKERS {cls.MAX_PARALLEL_WORKERS} < 1, using default 4")
            cls.MAX_PARALLEL_WORKERS = 4
        else:
            cap_env = os.environ.get('MAX_PARALLEL_WORKERS_CAP')
            if cap_env:
                try:
                    cap_int = int(cap_env)
                    if cls.MAX_PARALLEL_WORKERS > cap_int:
                        print(f"⚠️ Info: Capping MAX_PARALLEL_WORKERS {cls.MAX_PARALLEL_WORKERS} to {cap_int} per env cap")
                        cls.MAX_PARALLEL_WORKERS = cap_int
                except Exception:
                    pass
        
        if cls.PARALLEL_WORKER_TIMEOUT < 60:
            print(f"⚠️ Warning: PARALLEL_WORKER_TIMEOUT {cls.PARALLEL_WORKER_TIMEOUT}s too low, using minimum 60s")
            cls.PARALLEL_WORKER_TIMEOUT = 60
        
        if cls.PARALLEL_MIN_POS_THRESHOLD < 1:
            print(f"⚠️ Warning: PARALLEL_MIN_POS_THRESHOLD {cls.PARALLEL_MIN_POS_THRESHOLD} too low, using minimum 1")
            cls.PARALLEL_MIN_POS_THRESHOLD = 1
        
        return True

    @classmethod
    def get_parallel_config(cls) -> dict:
        """Get parallel processing configuration as dictionary."""
        cls.validate_parallel_config()
        
        return {
            'enabled': cls.ENABLE_PARALLEL_PROCESSING,
            'max_workers': cls.MAX_PARALLEL_WORKERS,
            'worker_timeout': cls.PARALLEL_WORKER_TIMEOUT,
            'min_pos_threshold': cls.PARALLEL_MIN_POS_THRESHOLD,
            'profile_cleanup': cls.PARALLEL_PROFILE_CLEANUP,
            'memory_limit_mb': cls.WORKER_MEMORY_LIMIT_MB,
            'cpu_threshold': cls.WORKER_CPU_THRESHOLD,
            'profile_size_limit_mb': cls.WORKER_PROFILE_SIZE_LIMIT_MB
        }

    @classmethod
    def should_use_parallel_processing(cls, po_count: int) -> bool:
        """Determine if parallel processing should be used based on configuration and PO count."""
        if not cls.ENABLE_PARALLEL_PROCESSING:
            return False

        if po_count < cls.PARALLEL_MIN_POS_THRESHOLD:
            return False

        # Additional checks could be added here for system resources
        return True


# =============================================================================
# DEPRECATED: Backward Compatibility Wrappers
# =============================================================================
# These classes redirect to AppConfig for backward compatibility during migration.
# All new code should import directly from src.config.app_config.


def _get_app_config():
    """Lazy import of AppConfig to avoid circular imports."""
    from ..config.app_config import AppConfig
    return AppConfig()


class Config:
    """
    DEPRECATED: Backward compatibility wrapper for AppConfig.
    
    This class redirects all attribute access to AppConfig for backward
    compatibility during the migration period.
    
    Migration:
        Old: from src.lib.config import Config
             config = Config.DOWNLOAD_FOLDER
        
        New: from src.config.app_config import AppConfig
             config = AppConfig().download_folder
    """
    
    def __init__(self):
        warnings.warn(
            "Config is deprecated. Use src.config.app_config.AppConfig instead.",
            DeprecationWarning,
            stacklevel=2
        )
    
    def __getattribute__(self, name):
        # Redirect to AppConfig for all attributes except special ones
        if name.startswith('_') or name in ('__class__', '__doc__', '__init__', '__getattribute__'):
            return object.__getattribute__(self, name)

        # Special-case legacy uppercase fields that map to AppConfig
        if name == 'PAGE_DELAY':
            try:
                return float(getattr(_get_app_config(), 'page_delay'))
            except Exception:
                return 0.0
        
        # Get AppConfig and redirect
        app_config = _get_app_config()
        try:
            return getattr(app_config, name)
        except AttributeError:
            # Fallback to old behavior for class attributes
            return object.__getattribute__(self, name)
    
    @classmethod
    def __getattr__(cls, name):
        """Class-level attribute access for backward compatibility."""
        if name == 'PAGE_DELAY':
            try:
                return float(getattr(_get_app_config(), 'page_delay'))
            except Exception:
                return 0.0
        app_config = _get_app_config()
        try:
            return getattr(app_config, name)
        except AttributeError:
            raise AttributeError(f"{cls.__name__} has no attribute '{name}'")


class ExperimentalConfig:
    """
    DEPRECATED: Backward compatibility wrapper for AppConfig.
    
    This is an alias for Config, maintained for code that imports
    ExperimentalConfig instead.
    
    Migration:
        Old: from src.lib.config import ExperimentalConfig
             config = ExperimentalConfig.DOWNLOAD_FOLDER
        
        New: from src.config.app_config import AppConfig
             config = AppConfig().download_folder
    """
    
    def __init__(self):
        warnings.warn(
            "ExperimentalConfig is deprecated. Use src.config.app_config.AppConfig instead.",
            DeprecationWarning,
            stacklevel=2
        )
    
    def __getattribute__(self, name):
        # Same redirection logic as Config
        if name.startswith('_') or name in ('__class__', '__doc__', '__init__', '__getattribute__'):
            return object.__getattribute__(self, name)

        if name == 'PAGE_DELAY':
            try:
                return float(getattr(_get_app_config(), 'page_delay'))
            except Exception:
                return 0.0
        
        app_config = _get_app_config()
        try:
            return getattr(app_config, name)
        except AttributeError:
            return object.__getattribute__(self, name)
    
    @classmethod
    def __getattr__(cls, name):
        """Class-level attribute access for backward compatibility."""
        if name == 'PAGE_DELAY':
            try:
                return float(getattr(_get_app_config(), 'page_delay'))
            except Exception:
                return 0.0
        app_config = _get_app_config()
        try:
            return getattr(app_config, name)
        except AttributeError:
            raise AttributeError(f"{cls.__name__} has no attribute '{name}'")


# Re-export for backward compatibility
ExperimentalSettings = ExperimentalConfig

# Module-level singleton instances for backward compatibility
# These ensure Config.XYZ and ExperimentalConfig.XYZ work at the class level
sys.modules[__name__].Config = sys.modules[__name__].Config()  # type: ignore
sys.modules[__name__].ExperimentalConfig = sys.modules[__name__].ExperimentalConfig()  # type: ignore
