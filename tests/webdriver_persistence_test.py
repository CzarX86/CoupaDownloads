import os
import pytest
import time
import tempfile
import shutil
from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


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


def test_webdriver_persistence(edge_driver):
    """Test webdriver persistence with login form."""
    try:
        coupa_login_url = "https://unilever.coupahost.com"
        email = "julio.cezar@unilever.com"
        
        print(f"Opening {coupa_login_url} ...")
        edge_driver.get(coupa_login_url)

        # Wait for email field and fill it
        print("Waiting for email field...")
        email_input = WebDriverWait(edge_driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name*='email']"))
        )
        email_input.clear()
        email_input.send_keys(email)
        print(f"Filled email: {email}")

        # Verify the email was filled
        assert email_input.get_attribute('value') == email
        
        print("Test complete. Webdriver persistence test passed.")
        
    except Exception as e:
        pytest.fail(f"Error during test: {e}") 