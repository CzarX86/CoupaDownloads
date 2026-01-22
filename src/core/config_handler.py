# Configuration file handling

"""
Secure configuration file management for CoupaDownloads GUI.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
import configparser
import stat

from .config import ConfigurationSettings


class ConfigHandler:
    """
    Handles loading and saving configuration settings with secure file permissions.

    Configuration is stored in INI format at ~/.coupadownloads/config.ini
    with 600 permissions (user read/write only).
    """

    CONFIG_DIR = Path.home() / '.coupadownloads'
    CONFIG_FILE = CONFIG_DIR / 'config.ini'
    BACKUP_SUFFIX = '.backup'

    def __init__(self):
        """Initialize configuration handler"""
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        """Ensure configuration directory exists with proper permissions"""
        if not self.CONFIG_DIR.exists():
            self.CONFIG_DIR.mkdir(parents=True)
            # Set directory permissions to 700 (user rwx only)
            self.CONFIG_DIR.chmod(stat.S_IRWXU)

    def _secure_file_permissions(self, file_path: Path):
        """Set secure file permissions (600 - user read/write only)"""
        if file_path.exists():
            file_path.chmod(stat.S_IRUSR | stat.S_IWUSR)

    def load_configuration(self) -> Optional[ConfigurationSettings]:
        """
        Load configuration from disk.

        Returns:
            ConfigurationSettings if file exists and is valid, None otherwise
        """
        if not self.CONFIG_FILE.exists():
            return None

        try:
            config = configparser.ConfigParser()
            config.read(self.CONFIG_FILE)

            if not config.has_section('downloads'):
                return None

            section = config['downloads']

            # Load values with defaults
            worker_count = section.getint('worker_count', 4)
            download_dir = section.get('download_directory')
            csv_file = section.get('csv_file_path')
            max_retries = section.getint('max_retries', 2)

            # Convert paths
            download_directory = Path(download_dir) if download_dir else None
            csv_file_path = Path(csv_file) if csv_file else None

            settings = ConfigurationSettings(
                worker_count=worker_count,
                download_directory=download_directory,
                csv_file_path=csv_file_path,
                max_retries=max_retries
            )

            return settings

        except (configparser.Error, ValueError, OSError) as e:
            # Log error but don't crash - return None for invalid config
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to load configuration: {e}")
            return None

    def save_configuration(self, config: ConfigurationSettings) -> bool:
        """
        Save configuration to disk with secure permissions.

        Args:
            config: ConfigurationSettings to save

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Create backup if config file exists
            if self.CONFIG_FILE.exists():
                backup_file = self.CONFIG_FILE.with_suffix(self.BACKUP_SUFFIX)
                self.CONFIG_FILE.replace(backup_file)

            # Create config parser
            config_parser = configparser.ConfigParser()
            config_parser.add_section('downloads')

            # Set values
            config_parser.set('downloads', 'worker_count', str(config.worker_count))
            if config.download_directory:
                config_parser.set('downloads', 'download_directory', str(config.download_directory))
            if config.csv_file_path:
                config_parser.set('downloads', 'csv_file_path', str(config.csv_file_path))
            config_parser.set('downloads', 'max_retries', str(config.max_retries))

            # Write to temporary file first, then move
            temp_file = self.CONFIG_FILE.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                config_parser.write(f)

            # Set secure permissions on temp file
            self._secure_file_permissions(temp_file)

            # Atomic move to final location
            temp_file.replace(self.CONFIG_FILE)

            # Ensure final file has secure permissions
            self._secure_file_permissions(self.CONFIG_FILE)

            return True

        except (OSError, configparser.Error) as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to save configuration: {e}")
            return False

    def get_config_path(self) -> Path:
        """
        Get the path to the configuration file.

        Returns:
            Path to configuration file
        """
        return self.CONFIG_FILE

    def config_exists(self) -> bool:
        """
        Check if configuration file exists.

        Returns:
            True if configuration file exists
        """
        return self.CONFIG_FILE.exists()

    def delete_configuration(self) -> bool:
        """
        Delete configuration file.

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            if self.CONFIG_FILE.exists():
                self.CONFIG_FILE.unlink()
            return True
        except OSError:
            return False