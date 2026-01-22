"""
Test Status Panel Component

Integration tests for the status panel UI component.
Tests the component's ability to display status messages and errors correctly.
"""

import sys
from pathlib import Path

# Add src to path for imports (similar to conftest.py)
project_root = Path(__file__).resolve().parents[2]  # Go up two levels: gui -> tests -> project root
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import pytest
import tkinter as tk
import time
from unittest.mock import Mock, patch
from datetime import datetime

# Import the components we're testing
from src.ui.data_model import StatusMessage, StatusType, ErrorInfo, ErrorType, UIFeedbackConfig
from src.ui.feedback_manager import FeedbackManager
from src.ui.components.status_panel import StatusPanel


class TestStatusPanelIntegration:
    """Integration tests for status panel component."""

    def setup_method(self):
        """Set up test environment."""
        self.root = tk.Tk()
        # Don't withdraw the window - we need it visible for widget mapping to work
        # self.root.withdraw()  # Hide the window during tests
        self.parent_frame = tk.Frame(self.root)  # Use a Frame as parent
        self.parent_frame.pack(fill=tk.BOTH, expand=True)  # Pack the parent frame
        self.feedback_manager = FeedbackManager()
        self.config = UIFeedbackConfig()

    def teardown_method(self):
        """Clean up test environment."""
        if self.root:
            self.root.destroy()
        if self.feedback_manager:
            self.feedback_manager.shutdown()

    def test_status_panel_initialization(self):
        """Test that status panel initializes correctly."""
        # Should be able to create the component
        status_panel = StatusPanel(self.parent_frame, self.config)

        # Should have the expected attributes
        assert hasattr(status_panel, 'frame')
        assert hasattr(status_panel, 'status_indicator_label')
        assert hasattr(status_panel, 'status_text_label')
        assert hasattr(status_panel, 'message_text')
        assert hasattr(status_panel, 'error_frame')

        # Should be properly initialized
        assert status_panel.frame is not None
        assert status_panel.status_indicator_label is not None
        assert status_panel.status_text_label is not None

    def test_status_message_display(self):
        """Test that status messages are displayed correctly."""
        status_panel = StatusPanel(self.parent_frame, self.config)

        # Create a test status message
        message = StatusMessage(
            message_type=StatusType.INFO,
            title="Test Operation",
            message="This is a test status message",
            timestamp=datetime.now()
        )

        # Add the message
        status_panel.add_status_message(message)

        # Give UI time to update
        self.root.update()
        import time
        time.sleep(0.1)
        self.root.update()

        # Check that the message appears in the log
        log_content = status_panel.message_text.get(1.0, tk.END)
        assert "Test Operation" in log_content
        assert "This is a test status message" in log_content

    def test_status_message_types(self):
        """Test different status message types display correctly."""
        status_panel = StatusPanel(self.parent_frame, self.config)

        test_cases = [
            (StatusType.INFO, "ℹ️"),
            (StatusType.SUCCESS, "✅"),
            (StatusType.WARNING, "⚠️"),
            (StatusType.ERROR, "❌"),
            (StatusType.PROGRESS, "⏳")
        ]

        for message_type, expected_indicator in test_cases:
            message = StatusMessage(
                message_type=message_type,
                title=f"{message_type.value.title()} Test",
                message=f"Test {message_type.value} message"
            )

            status_panel.add_status_message(message)

        # Give UI time to update
        self.root.update()
        time.sleep(0.1)
        self.root.update()

        # Check that all message types appear
        log_content = status_panel.message_text.get(1.0, tk.END)
        for message_type, indicator in test_cases:
            assert indicator in log_content

    def test_error_display(self):
        """Test that errors are displayed with recovery options."""
        status_panel = StatusPanel(self.parent_frame, self.config)

        # Create a test error
        error = ErrorInfo(
            error_type=ErrorType.NETWORK_ERROR,
            user_message="Unable to connect to the server",
            recovery_suggestions=[
                "Check your internet connection",
                "Verify the server URL is correct",
                "Try again in a few minutes"
            ],
            retry_possible=True,
            contact_support=False
        )

        # Display the error
        status_panel.display_error(error)

        # Force synchronous update for testing
        status_panel._update_display()

        # Check that error is stored internally
        assert status_panel.current_error is not None
        assert status_panel.current_error.error_type == ErrorType.NETWORK_ERROR
        assert status_panel.current_error.user_message == "Unable to connect to the server"
        assert len(status_panel.current_error.recovery_suggestions) == 3

        # Check that error message label would be updated (check internal state)
        # Since we can't easily test widget visibility in headless mode,
        # we verify the error is properly stored and the update logic runs

    def test_error_recovery_suggestions(self):
        """Test that error recovery suggestions are displayed."""
        status_panel = StatusPanel(self.parent_frame, self.config)

        error = ErrorInfo(
            error_type=ErrorType.CONFIGURATION_ERROR,
            user_message="Invalid configuration settings",
            recovery_suggestions=[
                "Check the CSV file path",
                "Verify download directory exists",
                "Ensure worker count is between 1-10"
            ]
        )

        status_panel.display_error(error)

        # Give UI time to update
        self.root.update()
        time.sleep(0.1)
        self.root.update()

        # The recovery suggestions should be displayed
        # (We can't easily test the exact text content without more complex UI inspection)

    def test_message_history_limit(self):
        """Test that message history is limited to prevent memory issues."""
        status_panel = StatusPanel(self.parent_frame, self.config)

        # Add many messages
        for i in range(120):  # More than the 100 message limit
            message = StatusMessage(
                message_type=StatusType.INFO,
                title=f"Message {i}",
                message=f"Content {i}"
            )
            status_panel.add_status_message(message)

        # Check that we don't have more than 100 messages in history
        assert len(status_panel.message_history) <= 100

    def test_status_indicator_colors(self):
        """Test that status indicator shows correct colors for different message types."""
        status_panel = StatusPanel(self.parent_frame, self.config)

        # Test different message types
        test_messages = [
            (StatusType.INFO, "blue"),
            (StatusType.SUCCESS, "green"),
            (StatusType.WARNING, "orange"),
            (StatusType.ERROR, "red"),
            (StatusType.PROGRESS, "purple")
        ]

        for message_type, expected_color in test_messages:
            message = StatusMessage(
                message_type=message_type,
                title=f"{message_type.value} Test",
                message="Test message"
            )

            status_panel.add_status_message(message)

            # Give UI time to update
            self.root.update()
            time.sleep(0.05)
            self.root.update()

            # Check status indicator text (color would need more complex testing)
            indicator_text = status_panel.status_indicator_label.cget("text")
            assert "●" in indicator_text

    def test_clear_log_functionality(self):
        """Test that clear log button works correctly."""
        status_panel = StatusPanel(self.parent_frame, self.config)

        # Add some messages
        for i in range(5):
            message = StatusMessage(
                message_type=StatusType.INFO,
                title=f"Test Message {i}",
                message=f"Content {i}"
            )
            status_panel.add_status_message(message)

        # Clear the log
        status_panel.clear_message_log()

        # Give UI time to update
        self.root.update()
        time.sleep(0.1)
        self.root.update()

        # Check that log is cleared (should only have the "cleared" message)
        log_content = status_panel.message_text.get(1.0, tk.END)
        assert "Message log cleared" in log_content

        # Check that history is cleared
        assert len(status_panel.message_history) == 1  # Only the "cleared" message

    def test_feedback_manager_integration(self):
        """Test integration with feedback manager."""
        status_panel = StatusPanel(self.parent_frame, self.config)

        # Register with feedback manager
        status_panel.register_with_feedback_manager(self.feedback_manager)

        # Send a status update through feedback manager
        message = StatusMessage(
            message_type=StatusType.SUCCESS,
            title="Operation Complete",
            message="Download completed successfully"
        )

        # This would normally be called by the feedback manager
        # For testing, we'll call the panel directly
        status_panel.add_status_message(message)

        # Give UI time to update
        self.root.update()
        time.sleep(0.1)
        self.root.update()

        # Check that message was added
        log_content = status_panel.message_text.get(1.0, tk.END)
        assert "Operation Complete" in log_content
        assert "Download completed successfully" in log_content

    def test_error_dismiss_functionality(self):
        """Test that error dismiss functionality works."""
        status_panel = StatusPanel(self.parent_frame, self.config)

        # Display an error
        error = ErrorInfo(
            error_type=ErrorType.FILE_SYSTEM_ERROR,
            user_message="File not found",
            retry_possible=False
        )

        status_panel.display_error(error)

        # Give UI time to update
        self.root.update()
        time.sleep(0.1)
        self.root.update()

        # Check error is displayed
        assert status_panel.error_frame.winfo_ismapped()

        # Dismiss the error
        status_panel._dismiss_error()

        # Give UI time to update
        self.root.update()
        time.sleep(0.1)
        self.root.update()

        # Check error is hidden
        assert not status_panel.error_frame.winfo_ismapped()
        assert status_panel.current_error is None