import os
import sys
import random
import pytest
import time

# Ensure the src directory is in the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

from src.core.browser import BrowserManager
from src.core.downloader import Downloader
from src.core.excel_processor import ExcelProcessor
from src.core.config import Config


@pytest.fixture(scope="module")
def browser_session():
    """Fixture to manage a single browser session for the entire test module."""
    print("\n--- E2E Test Setup ---")
    print("IMPORTANT: Ensure you are logged into Coupa in your Edge profile.")
    browser_manager = BrowserManager()
    try:
        driver = browser_manager.initialize_driver()
        yield driver, browser_manager
    finally:
        print("\n--- E2E Test Teardown ---")
        browser_manager.cleanup()


@pytest.fixture
def e2e_downloader(browser_session):
    """Provides a Downloader instance for E2E tests."""
    driver, manager = browser_session
    return Downloader(driver, manager)


@pytest.fixture
def po_sample():
    """Fixture to read the input file and provide a random sample of POs."""
    excel_processor = ExcelProcessor()
    try:
        excel_path = excel_processor.get_excel_file_path()
        if not os.path.exists(excel_path):
            pytest.skip(f"Input file not found, skipping E2E test: {excel_path}")
        
        po_entries, _, _, _ = excel_processor.read_po_numbers_from_excel(excel_path)
        valid_entries = excel_processor.process_po_numbers(po_entries)
        
        if not valid_entries:
            pytest.skip("No valid PO entries found in the input file.")
        
        return random.sample(valid_entries, k=min(1, len(valid_entries)))
    except Exception as e:
        pytest.fail(f"Failed to read or process the Excel file for E2E test: {e}")


def test_random_po_download_e2e(e2e_downloader, po_sample):
    """
    Performs an end-to-end test on a random PO from the input file.
    """
    display_po, po_number = po_sample[0]
    print(f"\nRunning E2E test for random PO: {display_po}")

    download_dir = Config.DOWNLOAD_FOLDER
    os.makedirs(download_dir, exist_ok=True)
    initial_files = set(os.listdir(download_dir))

    downloader = e2e_downloader
    success, message = downloader.download_attachments_for_po(po_number)

    assert success is True, f"The download process failed for {display_po} with message: {message}"

    if "No attachments found" in message:
        print("   ✅ Test PASSED: The process correctly identified no attachments.")
        assert len(os.listdir(download_dir)) == len(initial_files)
    elif "Initiated download" in message:
        print("   Verifying that new files were downloaded...")
        time.sleep(5) 
        final_files = set(os.listdir(download_dir))
        new_files = final_files - initial_files
        
        print(f"   New files found: {new_files if new_files else 'None'}")
        assert len(new_files) > 0, f"Process for {display_po} reported downloads, but no new files appeared."
        print("   ✅ Test PASSED: New files were successfully downloaded.")

        print("   Cleaning up downloaded files...")
        for file in new_files:
            try:
                os.remove(os.path.join(download_dir, file))
                print(f"      Removed: {file}")
            except OSError as e:
                print(f"      Error removing file {file}: {e}")
    else:
        pytest.fail(f"The process for {display_po} returned an unexpected message: {message}")
