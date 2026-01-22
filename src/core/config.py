# Configuration data structures

"""
Data classes for CoupaDownloads configuration settings.
"""

from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from typing import Optional


@dataclass
class ConfigurationSettings:
    """
    User preferences for download operations, persisted across sessions.

    Fields:
        worker_count: Number of parallel download workers (1-10)
        download_directory: Directory for downloaded files (must be writable)
        csv_file_path: Input CSV file with download targets (must exist and be readable)
        max_retries: Maximum retry attempts per download (0-5)
        headless: Run browser in headless mode (no GUI) (default: False)
        last_modified: Timestamp of last configuration change (auto-updated)
    """
    worker_count: int = 4
    download_directory: Optional[Path] = None
    csv_file_path: Optional[Path] = None
    max_retries: int = 2
    headless: bool = True
    last_modified: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.worker_count < 1 or self.worker_count > 10:
            raise ValueError("worker_count must be between 1 and 10")

        if self.max_retries < 0 or self.max_retries > 5:
            raise ValueError("max_retries must be between 0 and 5")

        # Convert string paths to Path objects
        if isinstance(self.download_directory, str):
            self.download_directory = Path(self.download_directory)
        if isinstance(self.csv_file_path, str):
            self.csv_file_path = Path(self.csv_file_path)

    def is_valid(self) -> bool:
        """
        Check if configuration is valid for use.

        Returns:
            True if all required fields are set and valid
        """
        if not self.download_directory or not self.csv_file_path:
            return False

        if not self.download_directory.exists() or not self.download_directory.is_dir():
            return False

        if not self.csv_file_path.exists() or not self.csv_file_path.is_file():
            return False

        # Check if download directory is writable
        try:
            test_file = self.download_directory / '.write_test'
            test_file.touch()
            test_file.unlink()
        except (OSError, PermissionError):
            return False

        return True

    def get_validation_errors(self) -> list[str]:
        """
        Get list of validation error messages.

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if not self.download_directory:
            errors.append("Download directory is required")
        elif not self.download_directory.exists():
            errors.append(f"Download directory does not exist: {self.download_directory}")
        elif not self.download_directory.is_dir():
            errors.append(f"Path is not a directory: {self.download_directory}")
        else:
            # Check writability
            try:
                test_file = self.download_directory / '.write_test'
                test_file.touch()
                test_file.unlink()
            except (OSError, PermissionError):
                errors.append(f"Download directory is not writable: {self.download_directory}")

        if not self.csv_file_path:
            errors.append("CSV file path is required")
        elif not self.csv_file_path.exists():
            errors.append(f"CSV file does not exist: {self.csv_file_path}")
        elif not self.csv_file_path.is_file():
            errors.append(f"Path is not a file: {self.csv_file_path}")
        elif self.csv_file_path.suffix.lower() != '.csv':
            errors.append(f"File must have .csv extension: {self.csv_file_path}")

        return errors