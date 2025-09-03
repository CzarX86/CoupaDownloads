"""
Configuration for Download Control System
Centralizes CSV file locations and other control settings.
"""

import os
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
CONTROL_DIR = DATA_DIR / "control"
INPUT_DIR = DATA_DIR / "input"

# Ensure directories exist
CONTROL_DIR.mkdir(parents=True, exist_ok=True)
INPUT_DIR.mkdir(parents=True, exist_ok=True)

# CSV file paths
DOWNLOAD_CONTROL_CSV = CONTROL_DIR / "download_control.csv"
DOWNLOAD_CONTROL_DEMO_CSV = CONTROL_DIR / "download_control_demo.csv"

# Download control settings
CSV_ENCODING = "utf-8"
CSV_DELIMITER = ","
CSV_QUOTING = "QUOTE_ALL"

# Status values
STATUS_PENDING = "PENDING"
STATUS_DOWNLOADING = "DOWNLOADING"
STATUS_COMPLETED = "COMPLETED"
STATUS_FAILED = "FAILED"

# Timeout settings (seconds)
DOWNLOAD_TIMEOUT = 60
TAB_TIMEOUT = 30
CSV_SAVE_TIMEOUT = 5

# File monitoring settings
FILE_CHECK_INTERVAL = 2  # seconds
FILE_SIZE_STABLE_TIME = 3  # seconds to wait for file size to stabilize
