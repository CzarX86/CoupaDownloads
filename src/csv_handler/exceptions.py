"""Exception classes for CSV handler operations."""


class CSVError(Exception):
    """Base exception for CSV handler errors."""
    pass


class CSVValidationError(CSVError):
    """Raised when CSV validation fails."""
    pass


class CSVWriteError(CSVError):
    """Raised when CSV write operation fails."""
    pass


class BackupError(CSVError):
    """Raised when backup operations fail."""
    pass
