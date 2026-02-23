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
