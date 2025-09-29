"""
Test fixtures for browser automation and EXPERIMENTAL subproject testing.

This module provides shared fixtures for:
- Browser WebDriver setup/teardown
- Headless mode configuration testing
- Test environment isolation
- Common test data and mocks
"""

import os
import pytest
from pathlib import Path
from typing import Generator, Dict, Any
from unittest.mock import Mock, patch
import tempfile

# Add EXPERIMENTAL to Python path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "EXPERIMENTAL"))

try:
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.webdriver.edge.service import Service as EdgeService
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


@pytest.fixture(scope="session")
def test_environment():
    """Session-scoped fixture to set up test environment."""
    # Store original environment
    original_env = dict(os.environ)
    
    # Set test-specific environment variables
    os.environ['PYTEST_CURRENT_TEST'] = 'true'
    
    yield {
        'is_test': True,
        'original_env': original_env,
        'test_data_dir': Path(__file__).parent / "test_data"
    }
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def headless_config():
    """Fixture providing test headless configuration objects."""
    return {
        'enabled_config': {
            'enabled': True,
            'source': 'interactive_setup',
            'retry_attempted': False,
            'fallback_to_visible': False
        },
        'disabled_config': {
            'enabled': False,
            'source': 'interactive_setup',
            'retry_attempted': False,
            'fallback_to_visible': False
        },
        'retry_config': {
            'enabled': True,
            'source': 'interactive_setup',
            'retry_attempted': True,
            'fallback_to_visible': False
        },
        'fallback_config': {
            'enabled': True,
            'source': 'interactive_setup',
            'retry_attempted': True,
            'fallback_to_visible': True
        }
    }


@pytest.fixture
def browser_options():
    """Fixture providing Edge browser options for testing."""
    if not SELENIUM_AVAILABLE:
        pytest.skip("Selenium not available for browser testing")
    
    options = EdgeOptions()
    
    # Default test options
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    
    # Use headless mode unless explicitly disabled
    if not os.getenv('PYTEST_VISIBLE'):
        options.add_argument("--headless=new")
    
    return options


@pytest.fixture
def mock_browser_manager():
    """Mock BrowserManager for unit testing without actual browser."""
    with patch('EXPERIMENTAL.corelib.browser.BrowserManager') as mock:
        manager_instance = Mock()
        manager_instance.initialize_driver.return_value = Mock(spec=webdriver.Edge)
        manager_instance.start.return_value = None
        manager_instance.quit.return_value = None
        mock.return_value = manager_instance
        yield manager_instance


@pytest.fixture
def browser_driver(browser_options):
    """
    Fixture providing actual Edge WebDriver for integration tests.
    
    Requires Edge browser and msedgedriver to be installed.
    Skips if browser automation is not available.
    """
    if not SELENIUM_AVAILABLE:
        pytest.skip("Selenium not available for browser testing")
    
    # Check if Edge driver exists
    driver_path = Path(__file__).parent.parent / "drivers" / "msedgedriver"
    if not driver_path.exists():
        driver_path = driver_path.with_suffix(".exe")  # Windows
    
    if not driver_path.exists():
        pytest.skip("Edge WebDriver not found. Run download_drivers script.")
    
    # Create service
    service = EdgeService(executable_path=str(driver_path))
    
    # Create driver
    driver = None
    try:
        driver = webdriver.Edge(service=service, options=browser_options)
        driver.implicitly_wait(10)  # 10 second default wait
        yield driver
    except Exception as e:
        pytest.skip(f"Failed to initialize Edge WebDriver: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass  # Ignore cleanup errors


@pytest.fixture
def temp_download_dir():
    """Temporary download directory for testing file operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def interactive_setup_mock():
    """Mock for interactive setup to avoid actual user input during tests."""
    with patch('builtins.input') as mock_input:
        mock_input.side_effect = ['y']  # Default to yes for headless mode
        yield mock_input


@pytest.fixture
def sample_po_data():
    """Sample PO data for testing process workers."""
    return {
        'po_number': 'TEST-PO-001',
        'supplier': 'Test Supplier',
        'amount': 1000.00,
        'status': 'Approved',
        'attachments': ['test_invoice.pdf', 'test_receipt.pdf']
    }


@pytest.fixture(autouse=True)
def isolate_environment():
    """Automatically isolate test environment for each test."""
    # Store current working directory
    original_cwd = os.getcwd()
    original_env = dict(os.environ)
    
    yield
    
    # Restore environment
    os.chdir(original_cwd)
    
    # Remove test-specific environment variables
    test_vars = [k for k in os.environ.keys() if k.startswith('TEST_')]
    for var in test_vars:
        os.environ.pop(var, None)
    
    # Don't restore full environment as it may break pytest itself
    # Just ensure no test contamination


# Pytest hooks for better test organization

def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers", "browser: mark test as requiring browser automation"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add automatic markers."""
    for item in items:
        # Auto-mark browser tests
        if "browser" in item.nodeid or "selenium" in str(item.function):
            item.add_marker(pytest.mark.browser)
        
        # Auto-mark slow tests (integration and browser tests)
        if "integration" in item.nodeid or "browser_automation" in item.nodeid:
            item.add_marker(pytest.mark.slow)


def pytest_runtest_setup(item):
    """Setup hook to handle test requirements."""
    # Skip browser tests if explicitly disabled
    if item.get_closest_marker("browser") and os.getenv('SKIP_BROWSER_TESTS'):
        pytest.skip("Browser tests disabled by SKIP_BROWSER_TESTS")
    
    # Skip slow tests if explicitly disabled
    if item.get_closest_marker("slow") and os.getenv('SKIP_SLOW_TESTS'):
        pytest.skip("Slow tests disabled by SKIP_SLOW_TESTS")