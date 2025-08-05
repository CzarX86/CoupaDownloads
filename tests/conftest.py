import os
import sys
import tempfile
import pytest
import shutil
import csv
import json
from unittest.mock import Mock, patch, MagicMock
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from datetime import datetime, timedelta
import pandas as pd

# Add the src directory to the Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture(scope="session")
def test_data_dir():
    """Create a test data directory for the session"""
    test_dir = tempfile.mkdtemp(prefix="coupa_test_data_")
    yield test_dir
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture
def temp_download_folder(test_data_dir):
    """Create a temporary download folder for testing"""
    temp_dir = os.path.join(test_data_dir, f"downloads_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(temp_dir, exist_ok=True)
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_csv_file(test_data_dir):
    """Create a temporary CSV file for testing"""
    temp_file = os.path.join(test_data_dir, f"test_input_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    
    # Create sample CSV content
    sample_data = [
        {
            'PO_NUMBER': 'PO15826591',
            'STATUS': 'PENDING',
            'SUPPLIER': '',
            'ATTACHMENTS_FOUND': 0,
            'ATTACHMENTS_DOWNLOADED': 0,
            'LAST_PROCESSED': '',
            'ERROR_MESSAGE': '',
            'DOWNLOAD_FOLDER': '',
            'COUPA_URL': ''
        },
        {
            'PO_NUMBER': 'PO15873456',
            'STATUS': 'COMPLETED',
            'SUPPLIER': 'Test_Supplier_Inc',
            'ATTACHMENTS_FOUND': 3,
            'ATTACHMENTS_DOWNLOADED': 3,
            'LAST_PROCESSED': '2024-01-15 14:30:25',
            'ERROR_MESSAGE': '',
            'DOWNLOAD_FOLDER': 'Test_Supplier_Inc/',
            'COUPA_URL': 'https://coupa.company.com/requisition_lines/15873456'
        },
        {
            'PO_NUMBER': 'PO15873457',
            'STATUS': 'PENDING',
            'SUPPLIER': '',
            'ATTACHMENTS_FOUND': 0,
            'ATTACHMENTS_DOWNLOADED': 0,
            'LAST_PROCESSED': '',
            'ERROR_MESSAGE': '',
            'DOWNLOAD_FOLDER': '',
            'COUPA_URL': ''
        }
    ]
    
    with open(temp_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=sample_data[0].keys())
        writer.writeheader()
        writer.writerows(sample_data)
    
    yield temp_file
    
    # Cleanup
    if os.path.exists(temp_file):
        os.unlink(temp_file)


@pytest.fixture
def temp_excel_file(test_data_dir):
    """Create a temporary Excel file for testing"""
    temp_file = os.path.join(test_data_dir, f"test_input_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    
    # Create sample Excel data
    sample_data = [
        {
            'PO_NUMBER': 'PO15826591',
            'STATUS': 'PENDING',
            'SUPPLIER': '',
            'ATTACHMENTS_FOUND': 0,
            'ATTACHMENTS_DOWNLOADED': 0,
            'LAST_PROCESSED': '',
            'ERROR_MESSAGE': '',
            'DOWNLOAD_FOLDER': '',
            'COUPA_URL': ''
        },
        {
            'PO_NUMBER': 'PO15873456',
            'STATUS': 'COMPLETED',
            'SUPPLIER': 'Test_Supplier_Inc',
            'ATTACHMENTS_FOUND': 3,
            'ATTACHMENTS_DOWNLOADED': 3,
            'LAST_PROCESSED': '2024-01-15 14:30:25',
            'ERROR_MESSAGE': '',
            'DOWNLOAD_FOLDER': 'Test_Supplier_Inc/',
            'COUPA_URL': 'https://coupa.company.com/requisition_lines/15873456'
        }
    ]
    
    df = pd.DataFrame(sample_data)
    df.to_excel(temp_file, index=False, sheet_name='PO_Data')
    
    yield temp_file
    
    # Cleanup
    if os.path.exists(temp_file):
        os.unlink(temp_file)


@pytest.fixture
def mock_driver():
    """Mock Selenium WebDriver with comprehensive functionality"""
    driver = Mock()
    
    # Mock current URL and title
    driver.current_url = "https://unilever.coupahost.com/order_headers/12345"
    driver.title = "Coupa PO Page"
    
    # Mock WebDriverWait
    driver.implicitly_wait = Mock()
    driver.set_page_load_timeout = Mock()
    
    # Mock find_elements to return mock attachment elements
    def mock_find_elements(by, value):
        if "attachment" in value.lower() or "file" in value.lower():
            elements = []
            for i in range(3):  # Return 3 mock attachment elements
                element = Mock(spec=WebElement)
                element.get_attribute.return_value = f"invoice_{i+1}.pdf file attachment"
                element.click = Mock()
                elements.append(element)
            return elements
        return []
    
    driver.find_elements = Mock(side_effect=mock_find_elements)
    
    # Mock other common methods
    driver.get = Mock()
    driver.quit = Mock()
    driver.close = Mock()
    
    return driver


@pytest.fixture
def mock_attachment_element():
    """Mock attachment element with realistic behavior"""
    element = Mock(spec=WebElement)
    element.get_attribute.return_value = "invoice.pdf file attachment"
    element.click = Mock()
    element.is_displayed.return_value = True
    element.is_enabled.return_value = True
    element.text = "invoice.pdf"
    return element


@pytest.fixture
def mock_webdriver_wait():
    """Mock WebDriverWait for testing timeouts and conditions"""
    wait = Mock()
    
    def mock_until(condition):
        # Simulate successful condition check
        return True
    
    wait.until = Mock(side_effect=mock_until)
    return wait


@pytest.fixture
def mock_selenium_webdriver():
    """Mock selenium webdriver module"""
    with patch('selenium.webdriver.Edge') as mock_driver_class:
        mock_driver = Mock()
        mock_driver_class.return_value = mock_driver
        yield mock_driver_class


@pytest.fixture
def mock_local_driver():
    """Mock local driver path"""
    with patch('os.path.exists') as mock_exists:
        mock_exists.return_value = True
        yield mock_exists


@pytest.fixture
def mock_config():
    """Mock configuration settings"""
    with patch('config.Config') as mock_config_class:
        mock_config_class.DOWNLOAD_FOLDER = "/tmp/test_downloads"
        mock_config_class.ALLOWED_EXTENSIONS = [".pdf", ".msg", ".docx"]
        mock_config_class.BASE_URL = "https://test.coupahost.com/order_headers/{}"
        mock_config_class.PAGE_LOAD_TIMEOUT = 15
        mock_config_class.ATTACHMENT_WAIT_TIMEOUT = 10
        mock_config_class.DOWNLOAD_WAIT_TIMEOUT = 30
        yield mock_config_class


@pytest.fixture
def sample_po_data():
    """Sample PO data for testing"""
    return [
        {
            'po_number': 'PO15826591',
            'status': 'PENDING',
            'supplier': '',
            'attachments_found': 0,
            'attachments_downloaded': 0,
            'last_processed': '',
            'error_message': '',
            'download_folder': '',
            'coupa_url': ''
        },
        {
            'po_number': 'PO15873456',
            'status': 'COMPLETED',
            'supplier': 'Test_Supplier_Inc',
            'attachments_found': 3,
            'attachments_downloaded': 3,
            'last_processed': '2024-01-15 14:30:25',
            'error_message': '',
            'download_folder': 'Test_Supplier_Inc/',
            'coupa_url': 'https://coupa.company.com/requisition_lines/15873456'
        }
    ]


@pytest.fixture
def mock_file_system(temp_download_folder):
    """Mock file system operations"""
    with patch('os.path.exists') as mock_exists, \
         patch('os.makedirs') as mock_makedirs, \
         patch('os.rename') as mock_rename, \
         patch('os.listdir') as mock_listdir:
        
        # Configure mocks
        mock_exists.return_value = True
        mock_makedirs.return_value = None
        mock_rename.return_value = None
        mock_listdir.return_value = ['test_file.pdf', 'test_file.docx']
        
        yield {
            'exists': mock_exists,
            'makedirs': mock_makedirs,
            'rename': mock_rename,
            'listdir': mock_listdir
        }


@pytest.fixture
def mock_time():
    """Mock time operations for consistent testing"""
    with patch('time.sleep') as mock_sleep, \
         patch('time.time') as mock_time_func:
        
        mock_sleep.return_value = None
        mock_time_func.return_value = 1640995200.0  # Fixed timestamp
        
        yield {
            'sleep': mock_sleep,
            'time': mock_time_func
        }


@pytest.fixture
def mock_requests():
    """Mock requests for HTTP operations"""
    with patch('requests.get') as mock_get, \
         patch('requests.post') as mock_post:
        
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b"test content"
        mock_post.return_value.status_code = 200
        
        yield {
            'get': mock_get,
            'post': mock_post
        }


@pytest.fixture
def test_logger():
    """Test logger for capturing log output"""
    import logging
    
    # Create a test logger
    logger = logging.getLogger('test_logger')
    logger.setLevel(logging.DEBUG)
    
    # Create a handler that captures log messages
    log_capture = []
    
    class CaptureHandler(logging.Handler):
        def emit(self, record):
            log_capture.append(self.format(record))
    
    handler = CaptureHandler()
    handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(handler)
    
    yield logger, log_capture
    
    # Cleanup
    logger.removeHandler(handler)


@pytest.fixture
def mock_environment():
    """Mock environment variables"""
    with patch.dict('os.environ', {
        'PAGE_DELAY': '0',
        'EDGE_PROFILE_DIR': '/tmp/test_profile',
        'EDGE_PROFILE_NAME': 'TestProfile',
        'LOGIN_TIMEOUT': '60',
        'HEADLESS': 'false',
        'PROCESS_MAX_POS': '10'
    }):
        yield


@pytest.fixture
def performance_timer():
    """Timer fixture for performance testing"""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
        
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return 0
    
    return Timer() 