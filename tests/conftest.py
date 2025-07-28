import os
import tempfile
import pytest
from unittest.mock import Mock, patch
from selenium.webdriver.edge.options import Options as EdgeOptions


@pytest.fixture
def temp_download_folder():
    """Create a temporary download folder for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_driver():
    """Mock Selenium WebDriver"""
    driver = Mock()
    driver.current_url = "https://unilever.coupahost.com/order_headers/12345"
    driver.title = "Coupa PO Page"
    return driver


@pytest.fixture
def mock_attachment_element():
    """Mock attachment element"""
    element = Mock()
    element.get_attribute.return_value = "invoice.pdf file attachment"
    return element


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing"""
    return """PO_NUMBER
PO15262984
PO15327452
PO15362783
invalid_po
PO15421343"""


@pytest.fixture
def temp_csv_file(sample_csv_content):
    """Create a temporary CSV file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(sample_csv_content)
        temp_file = f.name
    
    yield temp_file
    
    # Cleanup
    if os.path.exists(temp_file):
        os.unlink(temp_file)


@pytest.fixture
def mock_local_driver():
    """Mock local driver path"""
    with patch('os.path.exists') as mock_exists:
        mock_exists.return_value = True
        yield mock_exists


@pytest.fixture
def mock_selenium_webdriver():
    """Mock selenium webdriver"""
    with patch('selenium.webdriver.Edge') as mock_driver_class:
        mock_driver = Mock()
        mock_driver_class.return_value = mock_driver
        yield mock_driver_class 