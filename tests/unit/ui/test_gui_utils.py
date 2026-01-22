# GUI Testing Utilities

"""
Cross-platform testing utilities for Tkinter GUI components.

Provides fixtures and utilities for testing GUI components in headless environments
and ensuring cross-platform compatibility.
"""

import pytest
import tkinter as tk
from tkinter import ttk
import sys
import os
from typing import Generator, Optional, Any
from unittest.mock import Mock, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))


class MockTkRoot:
    """Mock Tkinter root for headless testing."""

    def __init__(self):
        self.title_called = False
        self.geometry_called = False
        self.resizable_called = False
        self.protocol_called = False
        self.columnconfigure_called = False
        self.rowconfigure_called = False
        self.mainloop_called = False
        self.destroy_called = False

        # Mock widgets
        self.widgets = []

    def title(self, title: str):
        self.title_called = True
        self._title = title

    def geometry(self, geometry: str):
        self.geometry_called = True
        self._geometry = geometry

    def resizable(self, width: bool, height: bool):
        self.resizable_called = True
        self._resizable = (width, height)

    def protocol(self, protocol: str, func):
        self.protocol_called = True
        self._protocol_func = func

    def columnconfigure(self, index: int, **kwargs):
        self.columnconfigure_called = True

    def rowconfigure(self, index: int, **kwargs):
        self.rowconfigure_called = True

    def mainloop(self):
        self.mainloop_called = True
        # Don't actually run mainloop in tests

    def destroy(self):
        self.destroy_called = True

    def after(self, delay: int, func):
        # In tests, execute immediately
        func()


class MockTkWidget:
    """Mock Tkinter widget for testing."""

    def __init__(self, parent=None, **kwargs):
        self.parent = parent
        self.kwargs = kwargs
        self.grid_called = False
        self.pack_called = False
        self.place_called = False
        self.config_called = False

    def grid(self, **kwargs):
        self.grid_called = True
        self.grid_kwargs = kwargs

    def pack(self, **kwargs):
        self.pack_called = True
        self.pack_kwargs = kwargs

    def place(self, **kwargs):
        self.place_called = True
        self.place_kwargs = kwargs

    def config(self, **kwargs):
        self.config_called = True
        self.config_kwargs = kwargs

    def configure(self, **kwargs):
        self.configure_kwargs = kwargs


class MockMenu(tk.Menu):
    """Mock menu for testing."""

    def __init__(self, parent=None, **kwargs):
        # Don't call super().__init__ to avoid Tkinter issues in headless mode
        self.parent = parent
        self.kwargs = kwargs
        self.add_command_called = False
        self.add_separator_called = False
        self.add_cascade_called = False

    def add_command(self, **kwargs):
        self.add_command_called = True

    def add_separator(self):
        self.add_separator_called = True

    def add_cascade(self, **kwargs):
        self.add_cascade_called = True


class MockMessageBox:
    """Mock messagebox for testing."""

    @staticmethod
    def showinfo(title: str, message: str):
        return True

    @staticmethod
    def showerror(title: str, message: str):
        return True

    @staticmethod
    def showwarning(title: str, message: str):
        return True

    @staticmethod
    def askyesno(title: str, message: str):
        return True

    @staticmethod
    def askyesnocancel(title: str, message: str):
        return True


@pytest.fixture
def mock_tk_root():
    """Provide a mock Tkinter root for testing."""
    return MockTkRoot()


@pytest.fixture
def mock_tk_widget():
    """Provide a mock Tkinter widget for testing."""
    return MockTkWidget()


@pytest.fixture
def mock_menu():
    """Provide a mock menu for testing."""
    return MockMenu()


@pytest.fixture
def mock_messagebox():
    """Provide a mock messagebox for testing."""
    return MockMessageBox()


@pytest.fixture(autouse=True)
def mock_tkinter_modules(monkeypatch):
    """Mock Tkinter modules to avoid GUI initialization in tests."""
    # Mock tkinter modules
    mock_tk = Mock()
    mock_tk.Tk = MockTkRoot
    mock_tk.Menu = MockMenu
    mock_ttk = Mock()
    mock_ttk.Frame = MockTkWidget
    mock_ttk.Label = MockTkWidget
    mock_ttk.Button = MockTkWidget
    mock_ttk.Entry = MockTkWidget
    mock_ttk.Spinbox = MockTkWidget

    monkeypatch.setattr('tkinter', mock_tk)
    monkeypatch.setattr('tkinter.ttk', mock_ttk)
    monkeypatch.setattr('tkinter.messagebox', MockMessageBox)


def create_test_gui_app(mock_root=None):
    """
    Create a test GUI application instance.

    Args:
        mock_root: Optional mock root to use instead of real Tk root

    Returns:
        CoupaDownloadsGUI instance configured for testing
    """
    if mock_root is None:
        mock_root = MockTkRoot()

    # Mock the core system
    from src.core.interfaces import CoreSystemInterface
    mock_core = Mock(spec=CoreSystemInterface)

    # Mock the UI state
    from src.ui.state import UIState
    ui_state = UIState()

    # Mock the communicator
    from src.ui.communication import GUICommunicator
    mock_communicator = Mock(spec=GUICommunicator)

    # Create GUI instance
    from src.ui.gui import CoupaDownloadsGUI
    app = CoupaDownloadsGUI.__new__(CoupaDownloadsGUI)
    app.root = mock_root  # type: ignore
    app.core_system = mock_core
    app.ui_state = ui_state
    app.communicator = mock_communicator
    app.current_config = None
    app.config_modified = False

    return app


def simulate_gui_event(app, event_name: str, **kwargs):
    """
    Simulate a GUI event for testing.

    Args:
        app: GUI application instance
        event_name: Name of the event to simulate
        **kwargs: Additional arguments for the event
    """
    if event_name == 'start_downloads':
        app.start_downloads()
    elif event_name == 'stop_downloads':
        app.stop_downloads()
    elif event_name == 'save_config':
        app.save_configuration()
    elif event_name == 'load_config':
        app._load_configuration()
    elif event_name == 'closing':
        app._on_closing()
    else:
        raise ValueError(f"Unknown event: {event_name}")


def assert_gui_layout_correct(widget, expected_layout: dict):
    """
    Assert that a GUI widget has the correct layout configuration.

    Args:
        widget: Widget to check
        expected_layout: Dictionary of expected layout properties
    """
    for prop, expected_value in expected_layout.items():
        if hasattr(widget, prop):
            actual_value = getattr(widget, prop)
            assert actual_value == expected_value, f"Layout property {prop}: expected {expected_value}, got {actual_value}"
        else:
            pytest.fail(f"Widget missing expected layout property: {prop}")


def wait_for_gui_update(timeout: float = 1.0):
    """
    Wait for GUI updates to complete.

    In a real GUI, this would wait for the event loop.
    In tests, this is a no-op since we don't run the event loop.

    Args:
        timeout: Maximum time to wait in seconds
    """
    # In test environment, GUI updates are synchronous
    pass


def get_cross_platform_display_info():
    """
    Get information about the current display environment.

    Returns:
        Dictionary with display information for cross-platform testing
    """
    return {
        'has_display': bool(os.environ.get('DISPLAY', '')),  # Linux/Unix
        'is_windows': os.name == 'nt',
        'is_macos': sys.platform == 'darwin',
        'is_linux': sys.platform.startswith('linux'),
        'tkinter_available': 'tkinter' in sys.modules or hasattr(sys, 'modules') and 'tkinter' in sys.modules,
    }


def skip_if_no_display():
    """
    Skip test if no display is available (headless environment).
    """
    display_info = get_cross_platform_display_info()
    if not display_info['has_display'] and not display_info['is_windows']:
        pytest.skip("Test requires display (not available in headless environment)")


def skip_if_not_cross_platform():
    """
    Skip test if not running on a cross-platform compatible environment.
    """
    display_info = get_cross_platform_display_info()
    if not display_info['tkinter_available']:
        pytest.skip("Tkinter not available on this platform")