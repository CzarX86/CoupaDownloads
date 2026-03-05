"""
Unified Application Configuration for CoupaDownloads.

This module provides a single source of truth for all application configuration,
replacing the scattered configuration across multiple modules.

Usage:
    from src.config.app_config import AppConfig
    
    config = AppConfig()
    download_folder = config.download_folder
    max_workers = config.max_workers
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from enum import Enum

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExecutionMode(str, Enum):
    """Execution mode for processing."""
    STANDARD = "standard"
    FILTERED = "filtered"
    NO_JS = "no_js"
    DIRECT_HTTP = "direct_http"


class AppConfig(BaseSettings):
    """
    Unified application configuration loaded from .env and defaults.
    
    All configuration values are accessible as properties with type safety
    and validation.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars
    )
    
    # =========================================================================
    # Project Paths
    # =========================================================================
    
    project_root: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[2],
        description="Root directory of the project"
    )
    
    input_dir: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[2] / "data" / "input",
        description="Directory containing input files"
    )
    
    download_folder: Path = Field(
        default_factory=lambda: Path.home() / "Downloads" / "CoupaDownloads",
        description="Default download folder for attachments"
    )
    
    # =========================================================================
    # Browser Configuration
    # =========================================================================
    
    base_url: str = Field(
        default="https://unilever.coupahost.com",
        description="Base URL for Coupa instance"
    )
    
    login_url: Optional[str] = Field(
        default=None,
        description="Explicit login URL (defaults to base_url/sessions/new)"
    )
    
    login_timeout: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Timeout for login in seconds"
    )
    
    edge_profile_dir: str = Field(
        default_factory=lambda: str(Path.home() / "Library" / "Application Support" / "Microsoft Edge") if os.name != 'nt' else "%LOCALAPPDATA%/Microsoft Edge/User Data",
        description="Directory for Edge browser profiles"
    )
    
    edge_profile_name: str = Field(
        default="Default",
        description="Name of Edge profile to use"
    )
    
    use_profile: bool = Field(
        default=True,
        description="Whether to use browser profiles"
    )
    
    headless: bool = Field(
        default=True,
        description="Run browser in headless mode"
    )
    
    # =========================================================================
    # Processing Configuration
    # =========================================================================
    
    enable_parallel_processing: bool = Field(
        default=True,
        description="Enable parallel processing of POs"
    )
    
    max_workers: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Maximum number of parallel workers"
    )
    
    use_process_pool: bool = Field(
        default=False,
        description="Use ProcessPoolExecutor for parallel processing"
    )
    
    proc_workers: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Number of worker processes"
    )
    
    proc_workers_cap: int = Field(
        default=16,
        ge=1,
        description="Maximum cap for worker processes"
    )
    
    resource_aware_scaling: bool = Field(
        default=True,
        description="Automatically adjust workers based on available RAM"
    )
    
    min_free_ram_gb: float = Field(
        default=0.3,
        ge=0.1,
        description="Minimum free RAM in GB to maintain"
    )
    
    execution_mode: ExecutionMode = Field(
        default=ExecutionMode.STANDARD,
        description="Execution mode for processing"
    )
    
    # =========================================================================
    # Input Configuration
    # =========================================================================
    
    excel_file_path: Optional[Path] = Field(
        default=None,
        description="Explicit path to input Excel/CSV file"
    )
    
    page_delay: float = Field(
        default=0.0,
        ge=0.0,
        description="Delay between page operations in seconds"
    )
    
    process_max_pos: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum number of POs to process"
    )
    
    random_sample_pos: Optional[int] = Field(
        default=None,
        ge=1,
        description="Process random sample of POs"
    )
    
    # =========================================================================
    # Batch Finalization
    # =========================================================================
    
    batch_finalization_enabled: bool = Field(
        default=True,
        description="Enable batch finalization of folders"
    )
    
    batch_finalization_interval: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Interval for batch finalization in seconds"
    )
    
    # =========================================================================
    # Driver Configuration
    # =========================================================================
    
    driver_auto_download: bool = Field(
        default=True,
        description="Automatically download EdgeDriver if not found"
    )
    
    edge_driver_path: Optional[Path] = Field(
        default=None,
        description="Explicit path to EdgeDriver"
    )

    page_load_timeout: int = Field(
        default=30,
        ge=5,
        description="Timeout for page loading in seconds"
    )

    attachment_wait_timeout: int = Field(
        default=15,
        ge=1,
        description="Timeout for waiting for attachments to appear"
    )

    download_wait_timeout: int = Field(
        default=60,
        ge=1,
        description="Timeout for file downloads to complete"
    )
    
    # =========================================================================
    # Selectors & Logic
    # =========================================================================

    attachment_selector: str = Field(
        default="a[href*='attachment'], a[href*='download'], [aria-label*='attachment'], [title*='attachment'], a[download]",
        description="CSS selector for matching attachment links"
    )

    supplier_name_css_selectors: List[str] = Field(
        default=[
            "span[data-supplier-name]",
            "span[class*='supplier-name']",
            ".supplier-info span",
            "[data-testid*='supplier'] span",
            "section:nth-of-type(2) div:nth-of-type(2) span:nth-of-type(3)",
            "section div[class*='supplier'] span",
            "section span:contains('supplier')",
            "div[class*='po-detail'] span:nth-child(3)"
        ],
        description="Priority list of CSS selectors for supplier name"
    )

    supplier_name_xpath: str = Field(
        default="/html/body/div[1]/div[5]/div/div/div[4]/div/div[3]/section[2]/div[2]/div[1]/div/span[3]",
        description="Fallback XPath for supplier name"
    )

    error_page_markers: List[str] = Field(
        default=[
            "Oops! We couldn't find what you wanted",
            "You are not authorized",
            "Access denied",
            "The page you were looking for doesn't exist",
            "Desculpe, não encontramos o que você procurava",
        ],
        description="Text markers to identify error pages"
    )

    error_page_css_selectors: List[str] = Field(
        default=[
            "div.flash_error",
            "div.flash-error",
            "div.notice",
            "div#error_explanation",
        ],
        description="CSS selectors used to detect Coupa error pages"
    )

    error_page_xpath_selectors: List[str] = Field(
        default=[
            "//div[contains(@class,'flash') and contains(.,'Oops')]",
            "//h1[contains(.,'Oops') or contains(.,'Sorry')]",
        ],
        description="XPath selectors used to detect Coupa error pages"
    )

    error_page_check_timeout: float = Field(
        default=2.0,
        ge=0.1,
        description="Timeout (seconds) for error page detection before DOM ready"
    )

    error_page_ready_check_timeout: float = Field(
        default=1.0,
        ge=0.0,
        description="Timeout (seconds) for error page detection after DOM ready"
    )

    error_page_wait_poll: float = Field(
        default=0.2,
        ge=0.05,
        description="Polling interval (seconds) for error page detection waits"
    )

    early_error_check_before_ready: bool = Field(
        default=True,
        description="Whether to run error-page detection before waiting for DOM ready"
    )

    pr_fallback_enabled: bool = Field(
        default=True,
        description="Enable navigation fallback to PR when PO has no attachments or PDFs"
    )

    pr_fallback_link_timeout: float = Field(
        default=4.0,
        ge=0.5,
        description="Timeout (seconds) to locate PR link on PO page"
    )

    pr_fallback_link_poll: float = Field(
        default=0.2,
        ge=0.05,
        description="Polling interval (seconds) when waiting for PR link"
    )

    pr_fallback_ready_timeout: float = Field(
        default=8.0,
        ge=0.0,
        description="Additional wait (seconds) for PR page DOM ready after navigation"
    )

    pr_link_css_selectors: List[str] = Field(
        default=[
            "a[href*='/requisition_headers/']",
            "a[href*='requisition_header']",
            "a[data-testid*='requisition']",
            "a[data-qa*='requisition']",
            "a[href*='/req/']",
        ],
        description="CSS selectors to locate PR link from PO page"
    )

    pr_link_xpath_candidates: List[str] = Field(
        default=[
            "//a[contains(@href,'/requisition_') or contains(@href,'/requisition-')]",
            "//a[contains(@href,'requisition_headers')]",
            "//a[contains(normalize-space(.),'Requisition')]",
            "//a[contains(normalize-space(.),'Requisição')]",
        ],
        description="XPath candidates to locate PR link from PO page"
    )

    pr_link_text_candidates: List[str] = Field(
        default=[
            "Requisition",
            "Purchase Requisition",
            "Requisição",
            "Requisições",
        ],
        description="Link text snippets used to locate PR link from PO page"
    )

    # =========================================================================
    # Logging & Verbosity
    # =========================================================================
    
    verbose_output: bool = Field(
        default=False,
        description="Enable verbose output"
    )
    
    show_detailed_processing: bool = Field(
        default=False,
        description="Show detailed processing information"
    )
    
    show_selenium_logs: bool = Field(
        default=False,
        description="Show Selenium logs"
    )
    
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    
    # =========================================================================
    # UI Configuration
    # =========================================================================
    
    enable_interactive_ui: bool = Field(
        default=True,
        description="Enable interactive UI prompts"
    )
    
    ui_mode: str = Field(
        default="premium",
        description="UI mode (premium, standard, none)"
    )
    
    suppress_worker_output: bool = Field(
        default=True,
        description="Suppress worker output during execution"
    )
    
    # =========================================================================
    # Parallel Processing (Legacy Support)
    # =========================================================================
    
    parallel_min_pos_threshold: int = Field(
        default=2,
        ge=1,
        description="Minimum POs to enable parallel processing"
    )
    
    parallel_worker_timeout: int = Field(
        default=300,
        ge=60,
        description="Timeout for parallel workers in seconds"
    )
    
    parallel_profile_cleanup: bool = Field(
        default=True,
        description="Clean up profiles after parallel processing"
    )
    
    # =========================================================================
    # Validators
    # =========================================================================
    
    @field_validator('download_folder', mode='before')
    @classmethod
    def expand_download_folder(cls, v):
        """Expand ~ in download folder path."""
        if isinstance(v, str):
            return Path(v).expanduser()
        return v
    
    @field_validator('excel_file_path', mode='before')
    @classmethod
    def expand_excel_path(cls, v):
        """Expand ~ in Excel file path."""
        if isinstance(v, str):
            return Path(v).expanduser()
        return v
    
    @field_validator('edge_driver_path', mode='before')
    @classmethod
    def expand_driver_path(cls, v):
        """Expand ~ in driver path."""
        if isinstance(v, str):
            return Path(v).expanduser()
        return v
    
    # =========================================================================
    # Computed Properties
    # =========================================================================
    
    @property
    def stable_download_folder(self) -> Path:
        """
        Get download folder with timestamp for stability.
        
        Returns a timestamped folder to avoid conflicts between runs.
        Format: yyyymmdd-hh"h"mm_CoupaDownloads
        """
        timestamp = datetime.now().strftime('%Y%m%d-%Hh%M')
        parent = self.download_folder.parent
        base_name = self.download_folder.name
        
        # Add timestamp if not already present
        if not any(c.isdigit() for c in self.download_folder.name):
            return parent / f"{timestamp}_{base_name}"
        return self.download_folder
    
    @property
    def effective_login_url(self) -> str:
        """Get effective login URL (explicit or derived from base_url)."""
        if self.login_url:
            return self.login_url
        return f"{self.base_url}/sessions/new"
    
    @property
    def effective_workers(self) -> int:
        """Get effective worker count (respects cap)."""
        return min(self.proc_workers, self.proc_workers_cap)
    
    # =========================================================================
    # Backward Compatibility
    # =========================================================================
    
    @property
    def EXCEL_FILE_PATH(self) -> Optional[Path]:
        """Legacy compatibility for ExperimentalConfig.EXCEL_FILE_PATH."""
        return self.excel_file_path
    
    @EXCEL_FILE_PATH.setter
    def EXCEL_FILE_PATH(self, value: Optional[Path]):
        self.excel_file_path = value
    
    @property
    def DOWNLOAD_FOLDER(self) -> Path:
        """Legacy compatibility for ExperimentalConfig.DOWNLOAD_FOLDER."""
        return self.download_folder
    
    @DOWNLOAD_FOLDER.setter
    def DOWNLOAD_FOLDER(self, value: Path):
        self.download_folder = value
    
    @property
    def EDGE_PROFILE_DIR(self) -> str:
        """Legacy compatibility for ExperimentalConfig.EDGE_PROFILE_DIR."""
        return self.edge_profile_dir
    
    @EDGE_PROFILE_DIR.setter
    def EDGE_PROFILE_DIR(self, value: str):
        self.edge_profile_dir = value
    
    @property
    def EDGE_PROFILE_NAME(self) -> str:
        """Legacy compatibility for ExperimentalConfig.EDGE_PROFILE_NAME."""
        return self.edge_profile_name
    
    @EDGE_PROFILE_NAME.setter
    def EDGE_PROFILE_NAME(self, value: str):
        self.edge_profile_name = value
    
    @property
    def USE_PROCESS_POOL(self) -> bool:
        """Legacy compatibility for ExperimentalConfig.USE_PROCESS_POOL."""
        return self.use_process_pool
    
    @USE_PROCESS_POOL.setter
    def USE_PROCESS_POOL(self, value: bool):
        self.use_process_pool = value
    
    @property
    def PROC_WORKERS(self) -> int:
        """Legacy compatibility for ExperimentalConfig.PROC_WORKERS."""
        return self.proc_workers
    
    @PROC_WORKERS.setter
    def PROC_WORKERS(self, value: int):
        self.proc_workers = value
    
    @property
    def HEADLESS(self) -> bool:
        """Legacy compatibility for Config.HEADLESS."""
        return self.headless
    
    @HEADLESS.setter
    def HEADLESS(self, value: bool):
        self.headless = value
    
    @property
    def BASE_URL(self) -> str:
        """Legacy compatibility for Config.BASE_URL."""
        return self.base_url
    
    @property
    def LOGIN_URL(self) -> Optional[str]:
        """Legacy compatibility for Config.LOGIN_URL."""
        return self.effective_login_url
    
    @property
    def LOGIN_TIMEOUT(self) -> int:
        """Legacy compatibility for Config.LOGIN_TIMEOUT."""
        return self.login_timeout
    
    @property
    def USE_PROFILE(self) -> bool:
        """Legacy compatibility for Config.USE_PROFILE."""
        return self.use_profile
    
    @property
    def ENABLE_PARALLEL_PROCESSING(self) -> bool:
        """Legacy compatibility for Config.ENABLE_PARALLEL_PROCESSING."""
        return self.enable_parallel_processing
    
    @property
    def MAX_PARALLEL_WORKERS(self) -> int:
        """Legacy compatibility for Config.MAX_PARALLEL_WORKERS."""
        return self.max_workers
    
    @property
    def PARALLEL_MIN_POS_THRESHOLD(self) -> int:
        """Legacy compatibility for Config.PARALLEL_MIN_POS_THRESHOLD."""
        return self.parallel_min_pos_threshold
    
    @property
    def RESOURCE_AWARE_SCALING(self) -> bool:
        """Legacy compatibility for Config.RESOURCE_AWARE_SCALING."""
        return self.resource_aware_scaling
    
    @property
    def MIN_FREE_RAM_GB(self) -> float:
        """Legacy compatibility for Config.MIN_FREE_RAM_GB."""
        return self.min_free_ram_gb
    
    @property
    def EXECUTION_MODE(self) -> ExecutionMode:
        """Legacy compatibility for Config.EXECUTION_MODE."""
        return self.execution_mode
    
    @property
    def VERBOSE_OUTPUT(self) -> bool:
        """Legacy compatibility for Config.VERBOSE_OUTPUT."""
        return self.verbose_output
    
    @property
    def SHOW_DETAILED_PROCESSING(self) -> bool:
        """Legacy compatibility for Config.SHOW_DETAILED_PROCESSING."""
        return self.show_detailed_processing
    
    @property
    def SHOW_SELENIUM_LOGS(self) -> bool:
        """Legacy compatibility for Config.SHOW_SELENIUM_LOGS."""
        return self.show_selenium_logs
    
    @property
    def DRIVER_AUTO_DOWNLOAD(self) -> bool:
        """Legacy compatibility for Config.DRIVER_AUTO_DOWNLOAD."""
        return self.driver_auto_download
    
    @property
    def EDGE_DRIVER_PATH(self) -> Optional[Path]:
        """Legacy compatibility for Config.EDGE_DRIVER_PATH."""
        return self.edge_driver_path
    
    @property
    def ATTACHMENT_WAIT_TIMEOUT(self) -> int:
        """Legacy compatibility for Config.ATTACHMENT_WAIT_TIMEOUT."""
        return self.attachment_wait_timeout
    
    @property
    def DOWNLOAD_WAIT_TIMEOUT(self) -> int:
        """Legacy compatibility for Config.DOWNLOAD_WAIT_TIMEOUT."""
        return self.download_wait_timeout
    
    @property
    def PAGE_LOAD_TIMEOUT(self) -> int:
        """Legacy compatibility for Config.PAGE_LOAD_TIMEOUT."""
        return self.page_load_timeout

    @property
    def ATTACHMENT_SELECTOR(self) -> str:
        """Legacy compatibility for Config.ATTACHMENT_SELECTOR."""
        return self.attachment_selector

    @property
    def SUPPLIER_NAME_CSS_SELECTORS(self) -> List[str]:
        """Legacy compatibility for Config.SUPPLIER_NAME_CSS_SELECTORS."""
        return self.supplier_name_css_selectors

    @property
    def SUPPLIER_NAME_XPATH(self) -> str:
        """Legacy compatibility for Config.SUPPLIER_NAME_XPATH."""
        return self.supplier_name_xpath

    @property
    def ERROR_PAGE_MARKERS(self) -> List[str]:
        """Legacy compatibility for Config.ERROR_PAGE_MARKERS."""
        return self.error_page_markers

    @property
    def ERROR_PAGE_CSS_SELECTORS(self) -> List[str]:
        """Legacy compatibility for Config.ERROR_PAGE_CSS_SELECTORS."""
        return self.error_page_css_selectors

    @property
    def ERROR_PAGE_XPATH_SELECTORS(self) -> List[str]:
        """Legacy compatibility for Config.ERROR_PAGE_XPATH_SELECTORS."""
        return self.error_page_xpath_selectors

    @property
    def ERROR_PAGE_CHECK_TIMEOUT(self) -> float:
        """Legacy compatibility for Config.ERROR_PAGE_CHECK_TIMEOUT."""
        return self.error_page_check_timeout

    @property
    def ERROR_PAGE_READY_CHECK_TIMEOUT(self) -> float:
        """Legacy compatibility for Config.ERROR_PAGE_READY_CHECK_TIMEOUT."""
        return self.error_page_ready_check_timeout

    @property
    def ERROR_PAGE_WAIT_POLL(self) -> float:
        """Legacy compatibility for Config.ERROR_PAGE_WAIT_POLL."""
        return self.error_page_wait_poll

    @property
    def EARLY_ERROR_CHECK_BEFORE_READY(self) -> bool:
        """Legacy compatibility for Config.EARLY_ERROR_CHECK_BEFORE_READY."""
        return self.early_error_check_before_ready

    @property
    def PR_FALLBACK_ENABLED(self) -> bool:
        """Legacy compatibility for Config.PR_FALLBACK_ENABLED."""
        return self.pr_fallback_enabled

    @property
    def PR_FALLBACK_LINK_TIMEOUT(self) -> float:
        """Legacy compatibility for Config.PR_FALLBACK_LINK_TIMEOUT."""
        return self.pr_fallback_link_timeout

    @property
    def PR_FALLBACK_LINK_POLL(self) -> float:
        """Legacy compatibility for Config.PR_FALLBACK_LINK_POLL."""
        return self.pr_fallback_link_poll

    @property
    def PR_FALLBACK_READY_TIMEOUT(self) -> float:
        """Legacy compatibility for Config.PR_FALLBACK_READY_TIMEOUT."""
        return self.pr_fallback_ready_timeout

    @property
    def PR_LINK_CSS_SELECTORS(self) -> List[str]:
        """Legacy compatibility for Config.PR_LINK_CSS_SELECTORS."""
        return self.pr_link_css_selectors

    @property
    def PR_LINK_XPATH_CANDIDATES(self) -> List[str]:
        """Legacy compatibility for Config.PR_LINK_XPATH_CANDIDATES."""
        return self.pr_link_xpath_candidates

    @property
    def PR_LINK_TEXT_CANDIDATES(self) -> List[str]:
        """Legacy compatibility for Config.PR_LINK_TEXT_CANDIDATES."""
        return self.pr_link_text_candidates
    
    @property
    def INPUT_DIR(self) -> Path:
        """Legacy compatibility for Config.INPUT_DIR."""
        return self.input_dir
    
    @property
    def PROJECT_ROOT(self) -> Path:
        """Legacy compatibility for Config.PROJECT_ROOT."""
        return self.project_root


# Global instance for backward compatibility
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """
    Get or create global AppConfig instance.
    
    Returns:
        AppConfig instance (cached)
    """
    global _config
    if _config is None:
        _config = AppConfig()
    return _config


# Backward compatibility: Allow imports like `from src.config.app_config import Config`
Config = AppConfig
ExperimentalSettings = AppConfig
