# GUI Component Tests

"""
Tests for GUI components using cross-platform testing utilities.
"""

import pytest
from .test_gui_utils import (
    MockTkRoot,
    get_cross_platform_display_info,
    skip_if_no_display
)


class TestGUIUtils:
    """Test the GUI testing utilities."""

    def test_mock_root_creation(self):
        """Test that mock root can be created."""
        root = MockTkRoot()
        assert root is not None
        assert not root.title_called
        assert not root.geometry_called

    def test_mock_root_methods(self):
        """Test mock root method calls."""
        root = MockTkRoot()

        root.title("Test")
        assert root.title_called
        assert root._title == "Test"

        root.geometry("800x600")
        assert root.geometry_called
        assert root._geometry == "800x600"

        root.mainloop()
        assert root.mainloop_called

        root.destroy()
        assert root.destroy_called

    def test_display_info(self):
        """Test display info detection."""
        info = get_cross_platform_display_info()

        assert isinstance(info, dict)
        assert 'has_display' in info
        assert 'is_windows' in info
        assert 'is_macos' in info
        assert 'is_linux' in info
        assert 'tkinter_available' in info

        # All values should be booleans
        for key, value in info.items():
            assert isinstance(value, bool), f"{key} should be boolean"

    def test_skip_decorator(self):
        """Test that skip decorator works."""
        # This test should not be skipped in normal environments
        # The skip_if_no_display decorator would skip the test if no display
        pass