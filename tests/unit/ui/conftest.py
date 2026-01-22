# Pytest configuration for UI tests

"""
Configuration for testing Tkinter GUI components.
"""

import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

@pytest.fixture
def mock_tkinter_root():
    """Mock Tkinter root for headless testing"""
    class MockRoot:
        def after(self, delay, func):
            # In tests, just call immediately
            func()

        def destroy(self):
            pass

        def mainloop(self):
            pass

    return MockRoot()

@pytest.fixture
def gui_queue():
    """Provide a GUI queue for testing"""
    from src.ui.utils import gui_queue
    # Clear any existing items
    while not gui_queue.empty():
        try:
            gui_queue.get_nowait()
        except:
            break
    return gui_queue