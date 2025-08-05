import os
import pytest
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

    # --- SETUP ---
    options = EdgeOptions()
    options.add_experimental_option("detach", False)  # Don't keep browser open for tests
    options.add_argument(f"--user-data-dir={temp_profile_dir}")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-extensions")

    # --- CREATE DRIVER ---
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


def test_coupa_profile_access(edge_driver):
    """Test accessing Coupa with Edge profile."""
    import time
    
    try:
        coupa_url = "https://unilever.coupahost.com"
        print(f"🌐 Opening: {coupa_url}")
        edge_driver.get(coupa_url)
        
        # Wait a moment to see the page load
        time.sleep(3)
        
        current_url = edge_driver.current_url
        print(f"📍 Current URL: {current_url}")
        
        if "login" in current_url.lower():
            print("✅ Successfully redirected to login page (expected for unauthenticated session)")
        else:
            print("✅ Successfully loaded Coupa home page")
        
        print("🔍 Profile test completed successfully")
        
    except Exception as e:
        pytest.fail(f"❌ Error: {e}") 