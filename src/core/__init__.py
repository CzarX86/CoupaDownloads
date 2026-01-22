"""
Core interfaces package for CoupaDownloads.

This package provides clean interfaces for UI integration while maintaining
backward compatibility with existing CLI functionality.
"""

from .types import (
    # Enums
    ProcessingStatus,
    StatusEventType,

    # Data classes
    ProcessingProgress,
    ConfigurationData,
    StatusUpdate,

    # Callback types
    StatusCallback,

    # Interface contracts
    ConfigurationManagerInterface,
    ProcessingControllerInterface,
    StatusManagerInterface,

    # Exceptions
    InterfaceError,
    ConfigurationError,
    ProcessingError,
    StatusError,
)

# Concrete implementations
from .config_interface import ConfigurationManager
from .processing_controller import ProcessingController
from .status_manager import StatusManager

__version__ = "0.1.0"
__all__ = [
    # Enums
    "ProcessingStatus",
    "StatusEventType",

    # Data classes
    "ProcessingProgress",
    "ConfigurationData",
    "StatusUpdate",

    # Callback types
    "StatusCallback",

    # Interface contracts
    "ConfigurationManagerInterface",
    "ProcessingControllerInterface",
    "StatusManagerInterface",

    # Concrete implementations
    "ConfigurationManager",
    "ProcessingController",
    "StatusManager",

    # Exceptions
    "InterfaceError",
    "ConfigurationError",
    "ProcessingError",
    "StatusError",
]