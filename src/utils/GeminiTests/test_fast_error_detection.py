import os
import sys
import time
import pytest
from unittest.mock import MagicMock

# Ensure the src and MyScript directories are in the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'MyScript'))

from src.core.downloader import Downloader
from src.core.config import Config


@pytest.fixture
def mock_driver():
    driver = MagicMock()
    driver.find_elements = MagicMock()
    return driver


@pytest.fixture
def downloader(mock_driver):
    mock_manager = MagicMock()
    mock_manager.driver = mock_driver
    return Downloader(mock_driver, mock_manager)


@pytest.mark.parametrize(
    "page_fragment",
    [
        "Oops! We couldn't find what you wanted",
        "You are not authorized",
        "Access denied",
        "The page you were looking for doesn't exist",
    ],
)
def test_downloader_early_error_detection_markers(downloader, mock_driver, page_fragment):
    po_number = "PO9999999"
    mock_driver.page_source = page_fragment

    result = downloader.download_attachments_for_po(po_number)

    assert result.get('success') is False
    assert result.get('message') == "PO not found or page error detected."
    # Early return should happen before attachment search
    mock_driver.find_elements.assert_not_called()


def test_downloader_early_error_detection_case_insensitive(downloader, mock_driver):
    po_number = "9999999"
    mock_driver.page_source = "oOpS! We couldN'T find what you wanted"

    result = downloader.download_attachments_for_po(po_number)
    assert result.get('success') is False
    mock_driver.find_elements.assert_not_called()


class _SwitchTo:
    def __init__(self, outer):
        self.outer = outer

    def window(self, handle):
        if handle not in self.outer.window_handles:
            self.outer.window_handles.append(handle)
        self.outer.current_window_handle = handle


class FakeDriver:
    def __init__(self):
        self.window_handles = ['main']
        self.current_window_handle = 'main'
        self.page_source = ''
        self.switch_to = _SwitchTo(self)

    def execute_script(self, script):
        # Simulate opening a new tab
        if 'window.open' in script:
            new_handle = f'tab{len(self.window_handles)}'
            self.window_handles.append(new_handle)
        return None

    def get(self, url):
        # No-op; page_source should be preset by the test
        return None


def test_tab_manager_create_tab_early_error_returns_none(monkeypatch):
    # Import here to ensure sys.path is already set
    from MyScript.browser_tab_manager import FIFOTabManager

    # Force very short timeout for unit test speed
    monkeypatch.setattr(Config, 'ERROR_PAGE_CHECK_TIMEOUT', 0.2, raising=False)
    monkeypatch.setattr(Config, 'EARLY_ERROR_CHECK_BEFORE_READY', True, raising=False)

    driver = FakeDriver()
    driver.page_source = "Access denied"

    mgr = FIFOTabManager(driver, window_ids=['main'])
    res = mgr.create_tab_for_url(0, "https://example.invalid", window_id='main', window_name='Main')
    assert res is None
    # Ensure no active tab registered
    assert 0 not in mgr.active_tabs


@pytest.mark.parametrize(
    "marker",
    Config.ERROR_PAGE_MARKERS,
)
def test_tab_manager_is_error_page_uses_markers(marker):
    from MyScript.browser_tab_manager import FIFOTabManager

    driver = FakeDriver()
    # Create a second tab handle and switch to it
    driver.execute_script("window.open('');")
    second = driver.window_handles[-1]
    driver.switch_to.window(second)
    driver.page_source = marker

    mgr = FIFOTabManager(driver, window_ids=['main'])
    assert mgr._is_error_page(second) is True
