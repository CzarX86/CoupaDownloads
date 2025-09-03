import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Ensure the src directory is in the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

from src.main import MainApp


@patch('src.main.ExcelProcessor')
@patch('src.main.BrowserManager')
@patch('src.main.Downloader')
def test_application_smoke_run(MockDownloader, MockBrowserManager, MockExcel):
    """
    Smoke test to ensure the MainApp initializes and runs without crashing.
    """
    # 1. Setup Mocks
    mock_excel_instance = MockExcel.return_value
    mock_excel_instance.get_excel_file_path.return_value = 'dummy_path.xlsx'
    mock_excel_instance.read_po_numbers_from_excel.return_value = ([{'po_number': 'SMOKE_TEST_PO'}], [], [], False)
    mock_excel_instance.process_po_numbers.return_value = [('SMOKE_TEST_PO', 'SMOKE_TEST_PO_CLEAN')]

    mock_downloader_instance = MockDownloader.return_value
    mock_downloader_instance.download_attachments_for_po.return_value = (True, "Smoke test success")

    # 2. Instantiate and Run the App
    app = MainApp()
    
    try:
        app.run()
    except Exception as e:
        pytest.fail(f"MainApp.run() raised an unexpected exception during smoke test: {e}")

    # 3. Assertions
    mock_excel_instance.read_po_numbers_from_excel.assert_called_once_with('dummy_path.xlsx')
    mock_downloader_instance.download_attachments_for_po.assert_called_once_with('SMOKE_TEST_PO_CLEAN')
    mock_excel_instance.update_po_status.assert_called_once_with(
        'SMOKE_TEST_PO', 'Success', error_message='Smoke test success'
    )
