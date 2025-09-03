import os
import sys
import pytest
from unittest.mock import MagicMock, patch, call

# Ensure the src directory is in the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

# Import the real exceptions
from selenium.common.exceptions import InvalidSessionIdException, NoSuchWindowException

# Now import the application class
from src.main import MainApp


@pytest.fixture
def mock_dependencies():
    """Mocks all major dependencies of MainApp."""
    with patch('src.main.ExcelProcessor') as MockExcel, \
         patch('src.main.BrowserManager') as MockBrowserManager, \
         patch('src.main.Downloader') as MockDownloader:
        
        mock_excel_instance = MockExcel.return_value
        mock_browser_manager_instance = MockBrowserManager.return_value
        mock_downloader_instance = MockDownloader.return_value

        # Set up the app instance with mocked dependencies
        app = MainApp()
        app.excel_processor = mock_excel_instance
        app.browser_manager = mock_browser_manager_instance
        app.downloader = mock_downloader_instance

        yield app, mock_excel_instance, mock_browser_manager_instance, mock_downloader_instance


def test_main_run_success_path(mock_dependencies):
    """Test the main run loop for a simple successful execution."""
    app, mock_excel, _, mock_downloader = mock_dependencies
    
    # Setup mocks for the new Excel workflow
    mock_excel.get_excel_file_path.return_value = 'dummy_path.xlsx'
    mock_excel.read_po_numbers_from_excel.return_value = ([{'po_number': 'PO1'}, {'po_number': 'PO2'}], [], [], False)
    mock_excel.process_po_numbers.return_value = [('PO1', '1'), ('PO2', '2')]
    mock_downloader.download_attachments_for_po.return_value = (True, "Downloaded 2 files.")
    
    app.run()

    assert mock_downloader.download_attachments_for_po.call_count == 2
    update_calls = [
        call('PO1', 'Success', error_message='Downloaded 2 files.'),
        call('PO2', 'Success', error_message='Downloaded 2 files.')
    ]
    mock_excel.update_po_status.assert_has_calls(update_calls, any_order=True)


def test_main_run_with_download_error(mock_dependencies):
    """Test the main run loop when the downloader returns an error."""
    app, mock_excel, _, mock_downloader = mock_dependencies

    mock_excel.get_excel_file_path.return_value = 'dummy_path.xlsx'
    mock_excel.read_po_numbers_from_excel.return_value = ([{'po_number': 'PO3'}], [], [], False)
    mock_excel.process_po_numbers.return_value = [('PO3', '3')]
    mock_downloader.download_attachments_for_po.return_value = (False, "Failed to download.")

    app.run()

    mock_downloader.download_attachments_for_po.assert_called_once_with('3')
    mock_excel.update_po_status.assert_called_once_with('PO3', 'Error', error_message='Failed to download.')


def test_main_run_session_exception_recovery(mock_dependencies):
    """Test the session recovery mechanism in the main loop."""
    app, mock_excel, mock_browser_manager, mock_downloader = mock_dependencies

    mock_excel.get_excel_file_path.return_value = 'dummy_path.xlsx'
    mock_excel.read_po_numbers_from_excel.return_value = ([{'po_number': 'PO4'}, {'po_number': 'PO5'}], [], [], False)
    mock_excel.process_po_numbers.return_value = [('PO4', '4'), ('PO5', '5')]
    
    mock_downloader.download_attachments_for_po.side_effect = [
        InvalidSessionIdException("Session lost"),
        (True, "Downloaded after recovery"),
        (True, "PO5 downloaded")
    ]

    app.run()

    assert mock_downloader.download_attachments_for_po.call_count == 3
    download_calls = [call('4'), call('4'), call('5')]
    mock_downloader.download_attachments_for_po.assert_has_calls(download_calls)

    mock_browser_manager.cleanup.assert_called_once()
    mock_browser_manager.initialize_driver.assert_called_once()

    status_calls = [
        call('PO4', 'Error', error_message='Browser session expired. Retrying.'),
        call('PO4', 'Success', error_message='Downloaded after recovery'),
        call('PO5', 'Success', error_message='PO5 downloaded')
    ]
    mock_excel.update_po_status.assert_has_calls(status_calls, any_order=False)