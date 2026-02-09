"""
Base types and contracts for core interfaces.

This module defines the shared types and abstract base classes that form the
contracts for the three core interfaces: ConfigurationManager, ProcessingController,
and StatusManager.
"""

import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum


# =============================================================================
# SHARED TYPES
# =============================================================================

class ProcessingStatus(Enum):
    """Enumeration of possible processing statuses."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class StatusEventType(Enum):
    """Types of status events that can be emitted."""
    PROCESSING_STARTED = "processing_started"
    PROCESSING_COMPLETED = "processing_completed"
    PROCESSING_FAILED = "processing_failed"
    PROGRESS_UPDATE = "progress_update"
    STATUS_CHANGED = "status_changed"


@dataclass
class ProcessingProgress:
    """Data structure for processing progress information."""
    session_id: str
    status: ProcessingStatus
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    active_tasks: int
    elapsed_time: float
    estimated_remaining: Optional[float] = None
    processing_mode: str = "sequential"
    worker_details: Optional[Dict[str, Any]] = None


@dataclass
class ConfigurationData:
    """Data structure for configuration information."""
    headless_mode: bool
    enable_parallel: bool
    max_workers: int
    download_folder: str
    input_file_path: str
    csv_enabled: bool = False
    csv_path: Optional[str] = None


@dataclass
class StatusUpdate:
    """Data structure for status update notifications."""
    event_type: StatusEventType
    session_id: Optional[str]
    timestamp: float
    data: Dict[str, Any]


# =============================================================================
# CALLBACK TYPES
# =============================================================================

StatusCallback = Callable[[StatusUpdate], None]
"""Callback function type for status updates."""


# =============================================================================
# INTERFACE CONTRACTS
# =============================================================================

class ConfigurationManagerInterface(ABC):
    """
    Abstract base class defining the ConfigurationManager interface contract.

    This interface provides clean configuration management without exposing
    internal complexity. All methods must use only built-in types (dict, str, bool)
    for serialization compatibility with UI frameworks.
    """

    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """
        Get current configuration as a dictionary.

        Returns:
            Dictionary containing all configuration settings using only
            built-in types (dict, str, bool, int, float, list).
        """
        pass

    @abstractmethod
    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        Save configuration from dictionary.

        Args:
            config: Dictionary with configuration settings.

        Returns:
            True if saved successfully, False otherwise.
        """
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate configuration dictionary.

        Args:
            config: Configuration dictionary to validate.

        Returns:
            Dictionary with validation results:
            {
                "valid": bool,
                "errors": List[str],  # Empty if valid
                "warnings": List[str]  # Optional warnings
            }
        """
        pass

    @abstractmethod
    def reset_to_defaults(self) -> bool:
        """
        Reset configuration to default values.

        Returns:
            True if reset successfully, False otherwise.
        """
        pass


class ProcessingControllerInterface(ABC):
    """
    Abstract base class defining the ProcessingController interface contract.

    This interface provides clean start/stop/status operations for processing
    workflows. Enforces single-session constraint and provides session management.
    """

    @abstractmethod
    def start_processing(self, config: Dict[str, Any]) -> str:
        """
        Start processing with given configuration.

        Args:
            config: Processing configuration dictionary.

        Returns:
            Session ID string (UUID4) on success.

        Raises:
            ValueError: If configuration is invalid.
            RuntimeError: If processing is already active or MainApp fails.
        """
        pass

    @abstractmethod
    def stop_processing(self, session_id: str) -> bool:
        """
        Stop processing for the specified session.

        Args:
            session_id: Session ID to stop.

        Returns:
            True if stopped successfully, False otherwise.
        """
        pass

    @abstractmethod
    def get_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get current processing status for the specified session.

        Args:
            session_id: Session ID to query.

        Returns:
            Dictionary with current status using only built-in types.
        """
        pass

    @abstractmethod
    def is_processing_active(self) -> bool:
        """
        Check if processing is currently active.

        Returns:
            True if processing is running, False otherwise.
        """
        pass


class StatusManagerInterface(ABC):
    """
    Abstract base class defining the StatusManager interface contract.

    This interface provides real-time status updates through a subscription system.
    Implements callback failure handling and thread-safe notifications.
    """

    @abstractmethod
    def subscribe_to_updates(self, callback: StatusCallback) -> str:
        """
        Subscribe to status updates.

        Args:
            callback: Function to call when status updates occur.

        Returns:
            Subscription ID string for unsubscribing.
        """
        pass

    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from status updates.

        Args:
            subscription_id: ID returned from subscribe_to_updates.

        Returns:
            True if unsubscribed successfully, False otherwise.
        """
        pass

    @abstractmethod
    def notify_status_update(self, update: StatusUpdate) -> None:
        """
        Notify all subscribers of a status update.

        Args:
            update: StatusUpdate to broadcast to subscribers.
        """
        pass

    @abstractmethod
    def get_subscriber_count(self) -> int:
        """
        Get number of active subscribers.

        Returns:
            Number of currently subscribed callbacks.
        """
        pass


# =============================================================================
# EXCEPTION TYPES
# =============================================================================

class InterfaceError(Exception):
    """Base exception for interface-related errors."""
    pass


class ConfigurationError(InterfaceError):
    """Raised when configuration operations fail."""
    pass


class ProcessingError(InterfaceError):
    """Raised when processing operations fail."""
    pass


class StatusError(InterfaceError):
    """Raised when status operations fail."""
    pass