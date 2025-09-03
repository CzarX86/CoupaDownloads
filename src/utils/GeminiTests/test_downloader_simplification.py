import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Ensure the src directory is in the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

from src.core.downloader import Downloader
from src.core.config import Config


@pytest.fixture
def mock_browser_manager():
    """Provides a mock BrowserManager and its driver."""
    mock_driver = MagicMock()
    mock_manager = MagicMock()
    mock_manager.driver = mock_driver
    return mock_manager, mock_driver


@pytest.fixture
def downloader(mock_browser_manager):
    """Provides a Downloader instance with a mock driver."""
    manager, driver = mock_browser_manager
    return Downloader(driver, manager)


# --- Tests for _extract_filename_from_element --- #

@pytest.mark.parametrize(
    "attributes, expected_filename",
    [
        # Test case 1: Filename is in the text content (highest priority)
        ({
            "text": "invoice.pdf",
            "aria-label": "some_other_name.pdf file attachment",
            "title": "some_other_name.pdf",
            "href": "/downloads/some_other_name.pdf"
        }, "invoice.pdf"),

        # Test case 2: Filename is in aria-label (second priority)
        ({
            "text": "Click here",
            "aria-label": "report.docx file attachment",
            "title": "some_other_name.docx",
            "href": "/downloads/some_other_name.docx"
        }, "report.docx"),

        # Test case 3: Filename is in the title (third priority)
        ({
            "text": "Download",
            "aria-label": "file attachment",
            "title": "archive.zip",
            "href": "/downloads/some_other_name.zip"
        }, "archive.zip"),

        # Test case 4: Filename is in the href (last resort)
        ({
            "text": "Link",
            "aria-label": "generic attachment",
            "title": "",
            "href": "/downloads/attachment_data.csv"
        }, "attachment_data.csv"),

        # Test case 5: No valid filename found
        ({
            "text": "Button",
            "aria-label": "generic attachment",
            "title": "",
            "href": "#"
        }, None),
    ]
)
def test_extract_filename_from_element(downloader, attributes, expected_filename):
    """Verify that filename extraction works correctly based on attribute priority."""
    mock_attachment = MagicMock()
    # Configure the mock to return values for attributes
    mock_attachment.text = attributes.get("text", "")
    mock_attachment.get_attribute.side_effect = lambda x: attributes.get(x, None)

    # Temporarily allow all extensions for this test
    with patch.object(Config, 'ALLOWED_EXTENSIONS', ['.pdf', '.docx', '.zip', '.csv']):
        filename = downloader._extract_filename_from_element(mock_attachment)
        assert filename == expected_filename


# --- Tests for download_attachments_for_po workflow --- #

def test_download_workflow_success(downloader, mock_browser_manager):
    """Test the main download workflow for a successful case."""
    mock_manager, mock_driver = mock_browser_manager
    po_number = "PO12345"

    # Mock the web elements to be found
    mock_attachment_1 = MagicMock()
    mock_attachment_1.text = "file1.pdf"
    mock_attachment_1.get_attribute.return_value = "file1.pdf"

    mock_attachment_2 = MagicMock()
    mock_attachment_2.text = "file2.docx"
    mock_attachment_2.get_attribute.return_value = "file2.docx"

    mock_driver.find_elements.return_value = [mock_attachment_1, mock_attachment_2]

    # Call the main method
    success, message = downloader.download_attachments_for_po(po_number)

    # Assertions
    assert success is True
    assert "Initiated download for 2/2 attachments" in message
    # The URL should use the order number without "PO" prefix
    mock_driver.get.assert_called_once_with(f"{Config.BASE_URL}/order_headers/12345")
    assert mock_attachment_1.click.call_count == 1
    assert mock_attachment_2.click.call_count == 1

def test_download_workflow_no_attachments(downloader, mock_browser_manager):
    """Test the workflow when no attachments are found."""
    mock_manager, mock_driver = mock_browser_manager
    po_number = "PO54321"

    # Mock find_elements to return an empty list
    mock_driver.find_elements.return_value = []

    # Call the main method
    success, message = downloader.download_attachments_for_po(po_number)

    # Assertions
    assert success is True
    assert message == "No attachments found."
    # The URL should use the order number without "PO" prefix
    mock_driver.get.assert_called_once_with(f"{Config.BASE_URL}/order_headers/54321")

def test_download_workflow_page_error(downloader, mock_browser_manager):
    """Test the workflow when a page error is detected."""
    mock_manager, mock_driver = mock_browser_manager
    po_number = "99999"

    # Mock the page source to contain the error message
    mock_driver.page_source = "Oops! We couldn't find what you wanted"

    # Call the main method
    success, message = downloader.download_attachments_for_po(po_number)

    # Assertions
    assert success is False
    assert message == "PO not found or page error detected."
