"""
Core modules for CoupaDownloads.
Contains the main business logic components.
"""

from .browser import BrowserManager
from .config import Config
from .csv_processor import CSVProcessor
from .downloader import DownloadManager, LoginManager

__all__ = [
    'BrowserManager',
    'Config', 
    'CSVProcessor',
    'DownloadManager',
    'LoginManager'
] 