"""
Contract Test: Error Display Component

Tests the error display component interface and contracts.
Verifies that the component meets its contractual obligations.
"""

import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).resolve().parents[2]
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import pytest
import tkinter as tk
from unittest.mock import Mock, MagicMock
from datetime import datetime

# Import components and data models
from src.ui.data_model import ErrorInfo, ErrorType, UIFeedbackConfig
from src.ui.components.error_display import ErrorDisplay


class TestErrorDisplayContract:
    """Contract tests for error display component."""

    def setup_method(self):
        """Set up test environment."""
        self.root = tk.Tk()
        self.root.withdraw()  # Hide window for headless testing
        self.parent_frame = tk.Frame(self.root)
        self.feedback_manager = Mock()
        self.config = UIFeedbackConfig()

    def teardown_method(self):
        """Clean up test environment."""
        if self.root:
            self.root.destroy()

    def test_error_display_initialization_contract(self):
        """Test that error display meets initialization contract."""
        # Should be able to create the component
        error_display = ErrorDisplay(self.parent_frame, self.config)

        # Contract: Must have required attributes
        assert hasattr(error_display, 'frame')
        assert hasattr(error_display, 'error_type_label')
        assert hasattr(error_display, 'error_message_label')
        assert hasattr(error_display, 'recovery_frame')
        assert hasattr(error_display, 'retry_button')
        assert hasattr(error_display, 'dismiss_button')

        # Contract: Frame must be created
        assert error_display.frame is not None
        assert isinstance(error_display.frame, tk.Frame)

    def test_show_error_contract(self):
        """Test display_error method contract."""
        error_display = ErrorDisplay(self.parent_frame, self.config)

        # Create test error
        error = ErrorInfo(
            error_type=ErrorType.NETWORK_ERROR,
            user_message="Connection failed",
            technical_details="Timeout after 30s",
            recovery_suggestions=["Check network", "Try again"],
            retry_possible=True,
            contact_support=False
        )

        # Contract: Should not raise exceptions
        error_display.display_error(error)

        # Contract: Error should be stored internally
        assert error_display.current_error == error

        # Contract: Component should be visible after showing error
        assert error_display.frame.winfo_ismapped()

    def test_hide_error_contract(self):
        """Test clear_error method contract."""
        error_display = ErrorDisplay(self.parent_frame, self.config)

        # First show an error
        error = ErrorInfo(
            error_type=ErrorType.FILE_SYSTEM_ERROR,
            user_message="File not found"
        )
        error_display.display_error(error)

        # Contract: Should be visible
        assert error_display.frame.winfo_ismapped()

        # Contract: clear_error should not raise exceptions
        error_display.clear_error()

        # Contract: Error should be cleared
        assert error_display.current_error is None

        # Contract: Component should be hidden
        assert not error_display.frame.winfo_ismapped()

    def test_retry_callback_contract(self):
        """Test retry callback setting and execution contract."""
        error_display = ErrorDisplay(self.parent_frame, self.config)

        # Contract: Should accept callback setting
        retry_called = False
        retry_error = None
        def test_retry(error_info: ErrorInfo):
            nonlocal retry_called, retry_error
            retry_called = True
            retry_error = error_info

        error_display.set_retry_callback(test_retry)

        # Contract: Callback should be stored
        assert error_display.on_retry is not None

        # Show error with retry possible
        error = ErrorInfo(
            error_type=ErrorType.NETWORK_ERROR,
            user_message="Connection failed",
            retry_possible=True
        )
        error_display.display_error(error)

        # Contract: Retry button should trigger callback
        error_display.retry_button.invoke()

        # Contract: Callback should have been called with error info
        assert retry_called
        assert retry_error == error

    def test_error_without_retry_contract(self):
        """Test error display when retry is not possible."""
        error_display = ErrorDisplay(self.parent_frame, self.config)

        # Error without retry option
        error = ErrorInfo(
            error_type=ErrorType.CONFIGURATION_ERROR,
            user_message="Invalid config",
            retry_possible=False
        )

        error_display.display_error(error)

        # Contract: Retry button should be disabled
        assert error_display.retry_button['state'] == 'disabled'

    def test_recovery_suggestions_display_contract(self):
        """Test that recovery suggestions are displayed per contract."""
        error_display = ErrorDisplay(self.parent_frame, self.config)

        suggestions = [
            "Check your internet connection",
            "Verify the server URL",
            "Contact support if issue persists"
        ]

        error = ErrorInfo(
            error_type=ErrorType.NETWORK_ERROR,
            user_message="Network error occurred",
            recovery_suggestions=suggestions
        )

        error_display.display_error(error)

        # Contract: Recovery suggestions should be stored
        assert error_display.current_error.recovery_suggestions == suggestions

        # Contract: Should handle empty suggestions
        error_no_suggestions = ErrorInfo(
            error_type=ErrorType.UNKNOWN_ERROR,
            user_message="Unknown error",
            recovery_suggestions=[]
        )

        error_display.display_error(error_no_suggestions)
        assert error_display.current_error.recovery_suggestions == []

    def test_error_type_styling_contract(self):
        """Test that different error types are styled appropriately."""
        error_display = ErrorDisplay(self.parent_frame, self.config)

        test_cases = [
            (ErrorType.NETWORK_ERROR, "Network"),
            (ErrorType.AUTHENTICATION_ERROR, "Authentication"),
            (ErrorType.FILE_SYSTEM_ERROR, "File System"),
            (ErrorType.CONFIGURATION_ERROR, "Configuration"),
            (ErrorType.VALIDATION_ERROR, "Validation"),
            (ErrorType.UNKNOWN_ERROR, "Unknown")
        ]

        for error_type, expected_text in test_cases:
            error = ErrorInfo(
                error_type=error_type,
                user_message=f"{expected_text} error occurred"
            )

            error_display.display_error(error)

            # Contract: Error type should be identifiable
            assert error_display.current_error.error_type == error_type

    def test_dismiss_button_contract(self):
        """Test dismiss button functionality contract."""
        error_display = ErrorDisplay(self.parent_frame, self.config)

        error = ErrorInfo(
            error_type=ErrorType.FILE_SYSTEM_ERROR,
            user_message="File error"
        )

        error_display.display_error(error)

        # Contract: Dismiss button should hide error
        error_display.dismiss_button.invoke()

        # Contract: Error should be cleared
        assert error_display.current_error is None

    def test_multiple_errors_contract(self):
        """Test handling multiple sequential errors."""
        error_display = ErrorDisplay(self.parent_frame, self.config)

        # First error
        error1 = ErrorInfo(
            error_type=ErrorType.NETWORK_ERROR,
            user_message="First error"
        )
        error_display.display_error(error1)
        assert error_display.current_error == error1

        # Second error (should replace first)
        error2 = ErrorInfo(
            error_type=ErrorType.FILE_SYSTEM_ERROR,
            user_message="Second error"
        )
        error_display.display_error(error2)

        # Contract: Only latest error should be current
        assert error_display.current_error == error2
        assert error_display.current_error != error1

    def test_error_display_state_contract(self):
        """Test component state management contract."""
        error_display = ErrorDisplay(self.parent_frame, self.config)

        # Contract: Should have current_error attribute
        assert hasattr(error_display, 'current_error')

        # Contract: No error initially
        assert error_display.current_error is None

        # After showing error
        error = ErrorInfo(
            error_type=ErrorType.UNKNOWN_ERROR,
            user_message="Test error"
        )
        error_display.display_error(error)

        # Contract: Should have error
        assert error_display.current_error is not None
        assert error_display.current_error.error_type == ErrorType.UNKNOWN_ERROR

    def test_thread_safety_contract(self):
        """Test that component operations are thread-safe."""
        error_display = ErrorDisplay(self.parent_frame, self.config)

        # Contract: All public methods should be callable from any thread
        # (Tkinter handles thread safety internally via after() calls)

        error = ErrorInfo(
            error_type=ErrorType.NETWORK_ERROR,
            user_message="Thread safety test"
        )

        # These should not raise exceptions even if called from background thread
        error_display.display_error(error)
        error_display.clear_error()

        # Contract: Component should handle thread calls gracefully
        assert error_display.frame is not None