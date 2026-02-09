"""
ProcessingController implementation for clean processing control.

This module provides the ProcessingController class that wraps MainApp
functionality to provide clean start/stop/status operations for UI integration.
"""

import uuid
import time
import threading
from typing import Dict, Any, Optional
from datetime import datetime

from .types import ProcessingControllerInterface


class ProcessingController(ProcessingControllerInterface):
    """
    ProcessingController provides clean start/stop/status operations for processing workflows.

    This class wraps MainApp functionality while enforcing single-session constraints
    and providing session-based processing management.
    """

    def __init__(self, main_app=None):
        """
        Initialize ProcessingController.

        Args:
            main_app: MainApp instance to wrap. If None, creates a new instance.
        """
        self._main_app = main_app
        self._active_session: Optional[Dict[str, Any]] = None
        self._session_lock = threading.Lock()
        self._status_cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()

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
        with self._session_lock:
            # Check single-session constraint
            if self._active_session is not None:
                raise RuntimeError("Processing is already active")

            # Validate configuration
            self._validate_config(config)

            # Generate session ID
            session_id = str(uuid.uuid4())

            # Initialize session data
            self._active_session = {
                "session_id": session_id,
                "config": config.copy(),
                "start_time": datetime.now().isoformat(),
                "state": "starting",
                "progress": 0.0,
                "current_operation": "Initializing processing",
                "items_processed": 0,
                "total_items": 0,
                "estimated_time_remaining": None,
                "error_message": ""
            }

            # Update cache
            with self._cache_lock:
                self._status_cache[session_id] = self._active_session.copy()

            # Start processing in background thread
            processing_thread = threading.Thread(
                target=self._run_processing,
                args=(session_id,),
                daemon=True
            )
            processing_thread.start()

            return session_id

    def stop_processing(self, session_id: str) -> bool:
        """
        Stop processing for the specified session.

        Args:
            session_id: Session ID to stop.

        Returns:
            True if stopped successfully, False otherwise.
        """
        with self._session_lock:
            if self._active_session is None or self._active_session["session_id"] != session_id:
                return False

            # Update session state
            self._active_session["state"] = "stopping"
            self._active_session["current_operation"] = "Stopping processing"

            # Update cache
            with self._cache_lock:
                self._status_cache[session_id] = self._active_session.copy()

            # TODO: Implement actual stopping logic when MainApp supports it
            # For now, just mark as completed
            self._active_session["state"] = "completed"
            self._active_session = None

            # Update cache
            with self._cache_lock:
                if session_id in self._status_cache:
                    self._status_cache[session_id] = {
                        "session_id": session_id,
                        "state": "completed",
                        "progress": 1.0,
                        "current_operation": "Processing completed",
                        "items_processed": 0,  # TODO: Get actual counts
                        "total_items": 0,
                        "start_time": datetime.now().isoformat(),  # TODO: Use actual start time
                        "estimated_time_remaining": 0,
                        "error_message": None
                    }

            return True

    def get_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get current processing status for the specified session.

        Args:
            session_id: Session ID to query.

        Returns:
            Dictionary with current status using only built-in types.
        """
        with self._cache_lock:
            if session_id in self._status_cache:
                status = self._status_cache[session_id].copy()
                # Return only the expected status fields
                return {
                    "session_id": status["session_id"],
                    "state": status["state"],
                    "progress": status["progress"],
                    "current_operation": status["current_operation"],
                    "items_processed": status["items_processed"],
                    "total_items": status["total_items"],
                    "start_time": status["start_time"],
                    "estimated_time_remaining": status["estimated_time_remaining"],
                    "error_message": status["error_message"]
                }

        # Return unknown status for non-existent sessions
        return {
            "session_id": session_id,
            "state": "unknown",
            "progress": 0.0,
            "current_operation": "Session not found",
            "items_processed": 0,
            "total_items": 0,
            "start_time": datetime.now().isoformat(),
            "estimated_time_remaining": None,
            "error_message": "Session not found"
        }

    def is_processing_active(self) -> bool:
        """
        Check if processing is currently active.

        Returns:
            True if processing is running, False otherwise.
        """
        with self._session_lock:
            return self._active_session is not None and self._active_session["state"] == "running"

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """
        Validate processing configuration.

        Args:
            config: Configuration dictionary to validate.

        Raises:
            ValueError: If configuration is invalid.
        """
        required_keys = {"headless_mode", "enable_parallel", "max_workers", "download_folder", "input_file_path"}

        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary")

        missing_keys = required_keys - config.keys()
        if missing_keys:
            raise ValueError(f"Missing required configuration keys: {missing_keys}")

        # Type validation
        if not isinstance(config["headless_mode"], bool):
            raise ValueError("headless_mode must be a boolean")

        if not isinstance(config["enable_parallel"], bool):
            raise ValueError("enable_parallel must be a boolean")

        if not isinstance(config["max_workers"], int) or config["max_workers"] < 1:
            raise ValueError("max_workers must be a positive integer")

        if not isinstance(config["download_folder"], str) or not config["download_folder"].strip():
            raise ValueError("download_folder must be a non-empty string")

        if not isinstance(config["input_file_path"], str) or not config["input_file_path"].strip():
            raise ValueError("input_file_path must be a non-empty string")

    def _run_processing(self, session_id: str) -> None:
        """
        Run processing in background thread.

        Args:
            session_id: Session ID for this processing run.
        """
        try:
            # Update status to running
            with self._session_lock:
                if self._active_session and self._active_session["session_id"] == session_id:
                    self._active_session["state"] = "running"
                    self._active_session["current_operation"] = "Running processing"

                    with self._cache_lock:
                        self._status_cache[session_id] = self._active_session.copy()

            # TODO: Implement actual MainApp processing
            # For now, simulate processing
            self._simulate_processing(session_id)

        except Exception as e:
            # Update status on error
            with self._session_lock:
                if self._active_session and self._active_session["session_id"] == session_id:
                    self._active_session["state"] = "error"
                    self._active_session["error_message"] = str(e)

                    with self._cache_lock:
                        self._status_cache[session_id] = self._active_session.copy()

                    self._active_session = None

    def _simulate_processing(self, session_id: str) -> None:
        """
        Simulate processing for testing purposes.

        Args:
            session_id: Session ID for this processing run.
        """
        import time

        # Simulate processing steps
        steps = [
            ("Loading configuration", 0.1),
            ("Reading input files", 0.3),
            ("Processing items", 0.7),
            ("Finalizing results", 0.9),
            ("Completing processing", 1.0)
        ]

        for operation, progress in steps:
            time.sleep(0.1)  # Simulate work

            with self._session_lock:
                if self._active_session and self._active_session["session_id"] == session_id:
                    self._active_session["progress"] = progress
                    self._active_session["current_operation"] = operation
                    self._active_session["items_processed"] = int(progress * 10)  # Simulate 10 items
                    self._active_session["total_items"] = 10

                    with self._cache_lock:
                        self._status_cache[session_id] = self._active_session.copy()

        # Complete processing
        with self._session_lock:
            if self._active_session and self._active_session["session_id"] == session_id:
                self._active_session["state"] = "completed"
                self._active_session["progress"] = 1.0
                self._active_session["current_operation"] = "Processing completed"
                self._active_session["items_processed"] = 10
                self._active_session["total_items"] = 10

                with self._cache_lock:
                    self._status_cache[session_id] = self._active_session.copy()

                self._active_session = None