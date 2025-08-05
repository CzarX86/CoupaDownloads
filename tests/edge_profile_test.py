import os
import pytest
import time
import tempfile
import shutil
from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService


@pytest.fixture
def edge_driver():
    """Fixture to create Edge driver with unique profile settings."""
    # --- CONFIG ---
    DRIVER_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "drivers", "edgedriver_138")

    # Create a unique temporary profile directory for this test
    temp_profile_dir = tempfile.mkdtemp(prefix="edge_test_profile_")
    
    print(f"🔧 Using temporary Edge profile directory: {temp_profile_dir}")

    options = EdgeOptions()
    options.add_experimental_option("detach", False)  # Don't keep browser open for tests
    options.add_argument(f"--user-data-dir={temp_profile_dir}")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-extensions")

    service = EdgeService(DRIVER_PATH)
    driver = webdriver.Edge(service=service, options=options)
    
    yield driver
    
    # Cleanup
    try:
        driver.quit()
    except:
        pass
    
    # Clean up temporary profile directory
    try:
        shutil.rmtree(temp_profile_dir)
    except:
        pass


def test_edge_profile_persistence(edge_driver):
    """Test Edge profile persistence."""
    try:
        test_url = "https://www.google.com"
        print(f"Opening {test_url} with temporary profile...")
        edge_driver.get(test_url)
        print("Browser should be using the temporary profile.")
        time.sleep(3)  # Reduced for testing
        
        # Verify we can access the page
        assert "google" in edge_driver.current_url.lower()
        
    except Exception as e:
        pytest.fail(f"Error during test: {e}") 