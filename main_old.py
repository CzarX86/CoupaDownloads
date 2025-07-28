import os
import re
import shutil  # For file renaming
import signal
import subprocess
import sys
import time

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Configuration
BASE_URL = "https://unilever.coupahost.com/order_headers/{}"
DOWNLOAD_FOLDER = os.path.expanduser("~/Downloads/CoupaDownloads")
ALLOWED_EXTENSIONS = [".pdf", ".msg", ".docx"]
PAGE_DELAY = float(os.environ.get("PAGE_DELAY", "0"))  # NEW: debug delay
EDGE_PROFILE_DIR = os.environ.get("EDGE_PROFILE_DIR")  # NEW: profile reuse
LOGIN_TIMEOUT = int(os.environ.get("LOGIN_TIMEOUT", "60"))  # Login timeout in seconds

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Set up Edge options
options = EdgeOptions()
options.add_argument("--disable-extensions")
options.add_argument("--start-maximized")
options.add_experimental_option(
    "prefs",
    {
        "download.default_directory": DOWNLOAD_FOLDER,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    },
)
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

# NEW: Real-profile reuse
if EDGE_PROFILE_DIR:
    options.add_argument(f"--user-data-dir={EDGE_PROFILE_DIR}")
    options.add_argument("--profile-directory=Default")

# Use local WebDriver version 138
DRIVER_PATH = os.path.join(os.path.dirname(__file__), "drivers", "edgedriver_138")

# Global driver variable for cleanup
driver = None

def cleanup_browser_processes():
    """Kill all Edge browser processes to ensure clean shutdown"""
    try:
        if sys.platform == "darwin":  # macOS
            subprocess.run(["pkill", "-f", "Microsoft Edge"], capture_output=True)
            subprocess.run(["pkill", "-f", "msedge"], capture_output=True)
        elif sys.platform == "win32":  # Windows
            subprocess.run(["taskkill", "/f", "/im", "msedge.exe"], capture_output=True)
        else:  # Linux
            subprocess.run(["pkill", "-f", "microsoft-edge"], capture_output=True)
            subprocess.run(["pkill", "-f", "msedge"], capture_output=True)
        print("🧹 Cleaned up Edge browser processes")
    except Exception as e:
        print(f"⚠️ Warning: Could not clean up Edge processes: {e}")

def check_and_kill_existing_edge_processes():
    """Check for existing Edge processes and kill them before starting"""
    try:
        if sys.platform == "darwin":  # macOS
            result = subprocess.run(["pgrep", "-f", "Microsoft Edge"], capture_output=True)
            if result.returncode == 0:
                print("🔍 Found existing Edge processes. Cleaning up...")
                cleanup_browser_processes()
                time.sleep(2)  # Give processes time to close
        elif sys.platform == "win32":  # Windows
            result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq msedge.exe"], capture_output=True)
            if "msedge.exe" in result.stdout.decode():
                print("🔍 Found existing Edge processes. Cleaning up...")
                cleanup_browser_processes()
                time.sleep(2)
        else:  # Linux
            result = subprocess.run(["pgrep", "-f", "microsoft-edge"], capture_output=True)
            if result.returncode == 0:
                print("🔍 Found existing Edge processes. Cleaning up...")
                cleanup_browser_processes()
                time.sleep(2)
    except Exception as e:
        print(f"⚠️ Warning: Could not check for existing Edge processes: {e}")

def signal_handler(signum, frame):
    """Handle interrupt signals for graceful shutdown"""
    print(f"\n🛑 Received signal {signum}. Shutting down gracefully...")
    cleanup_browser_processes()
    if driver:
        try:
            driver.quit()
        except:
            pass
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Check if local driver exists
if not os.path.exists(DRIVER_PATH):
    print(f"Local WebDriver not found at: {DRIVER_PATH}")
    print("Please ensure edgedriver_138 is available in the drivers folder.")
    raise FileNotFoundError(f"WebDriver not found at {DRIVER_PATH}")

def initialize_driver():
    """Initialize the WebDriver with proper error handling"""
    global driver
    try:
        service = EdgeService(executable_path=DRIVER_PATH)
        driver = webdriver.Edge(service=service, options=options)
        print(f"Using local Edge WebDriver: {DRIVER_PATH}")
        return driver
    except Exception as e:
        print(f"Driver initialization failed: {e}")
        raise


def ensure_logged_in(driver):
    """Detect Coupa login page and automatically monitor for successful login."""
    if (
        "login" in driver.current_url
        or "sign_in" in driver.current_url
        or "Log in" in driver.title
    ):
        print("Detected login page. Please log in manually...")
        
        # Monitor for successful login indicators
        max_wait_time = LOGIN_TIMEOUT  # Maximum time to wait for login
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                # Check for indicators of successful login
                current_url = driver.current_url
                page_title = driver.title
                
                # Success indicators (URLs that indicate logged-in state)
                success_indicators = [
                    "order_headers",  # PO pages
                    "dashboard",      # Dashboard
                    "home",          # Home page
                    "profile",       # Profile page
                    "settings"       # Settings page
                ]
                
                # Check if we're on a logged-in page
                if any(indicator in current_url for indicator in success_indicators):
                    print("✅ Login detected automatically!")
                    return
                
                # Check if we're still on login page
                if "login" in current_url or "sign_in" in current_url:
                    print("⏳ Waiting for login completion...", end="\r")
                    time.sleep(1)
                    continue
                
                # If we're not on login page and not on a known success page,
                # assume login was successful
                if "login" not in current_url and "sign_in" not in current_url:
                    print("✅ Login detected automatically!")
                    return
                    
            except Exception as e:
                print(f"⚠️ Error checking login status: {e}")
                time.sleep(1)
                continue
        
        # If we reach here, login timeout occurred
        print(f"\n❌ Login timeout after {max_wait_time} seconds.")
        print("Please ensure you've logged in and the page has loaded.")
        raise TimeoutException("Login timeout - please try again")
    
    # If not on login page, assume already logged in
    print("✅ Already logged in or not on login page.")


def download_attachments_for_po(display_po: str, clean_po: str, driver_instance) -> None:
    try:
        url = BASE_URL.format(clean_po)
        print(f"Processing PO #{display_po} (URL: {url})")
        driver_instance.get(url)
        if PAGE_DELAY:
            print(f"[DEBUG] Sleeping for {PAGE_DELAY} seconds after page load...")
            time.sleep(PAGE_DELAY)
        ensure_logged_in(driver_instance)

        # Check if page is accessible
        if "Page not found" in driver_instance.title:
            print(f"  PO #{display_po} not found. Skipping.")
            return

        # Wait for attachments to load
        try:
            WebDriverWait(driver_instance, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "span[aria-label*='file attachment']")
                )
            )
        except TimeoutException:
            print(f"  Timed out waiting for attachments on PO #{display_po}")
            return

        # Find all attachment elements
        attachments = driver_instance.find_elements(
            By.CSS_SELECTOR, "span[aria-label*='file attachment']"
        )
        if not attachments:
            print(f"  No attachments found for PO #{display_po}")
            return

        print(f"  Found {len(attachments)} attachments. Downloading...")

        # Track files before download
        before_files = set(os.listdir(DOWNLOAD_FOLDER))

        # Download each attachment individually
        for attachment in attachments:
            try:
                # Get filename from aria-label
                aria_label = attachment.get_attribute("aria-label")
                if aria_label is None:
                    filename = f"attachment_{attachments.index(attachment)+1}"
                else:
                    filename_match = re.search(r"(.+?)\\s*file attachment", aria_label)
                    filename = (
                        filename_match.group(1)
                        if filename_match
                        else f"attachment_{attachments.index(attachment)+1}"
                    )

                # Skip unsupported file types
                if not any(
                    filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS
                ):
                    print(f"    Skipping unsupported file: {filename}")
                    continue

                # Click the attachment
                driver_instance.execute_script("arguments[0].scrollIntoView();", attachment)
                attachment.click()
                print(f"    Downloading: {filename}")

                # Brief pause between downloads
                time.sleep(1)

            except Exception as e:
                print(f"    Failed to download attachment: {str(e)}")

        _wait_for_download_complete(DOWNLOAD_FOLDER, timeout=len(attachments) * 10)

        # NEW: Rename newly downloaded files
        after_files = set(os.listdir(DOWNLOAD_FOLDER))
        new_files = after_files - before_files
        for fname in new_files:
            orig_path = os.path.join(DOWNLOAD_FOLDER, fname)
            new_name = f"PO{display_po}_{fname}"
            new_path = os.path.join(DOWNLOAD_FOLDER, new_name)
            try:
                os.rename(orig_path, new_path)
                print(f"    Renamed {fname} -> {new_name}")
            except Exception as e:
                print(f"    Could not rename {fname}: {e}")

    except TimeoutException:
        print(f"  Timed out waiting for PO #{display_po} page to load. Skipping.")
    except Exception as e:
        print(f"  Error processing PO #{display_po}: {str(e)}")


def _wait_for_download_complete(directory: str, timeout: int = 30):
    """Wait for all .crdownload files to disappear"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not any(f.endswith(".crdownload") for f in os.listdir(directory)):
            return
        time.sleep(1)
    raise TimeoutException(f"Downloads not completed within {timeout} seconds")


def main() -> None:
    driver_instance = None
    try:
        import csv

        # Check and kill any existing Edge processes
        check_and_kill_existing_edge_processes()

        # Initialize the driver
        driver_instance = initialize_driver()

        # Get the directory where the script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_file = os.path.join(script_dir, "input.csv")

        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"PO input file {csv_file} not found")

        po_entries = []
        with open(csv_file, newline="") as f:
            reader = csv.reader(f)
            # Skip header if exists
            try:
                header = next(reader)
            except StopIteration:
                pass

            for row in reader:
                if row:  # Skip empty rows
                    po_entries.append(row[0].strip())  # Get first column value

        # Process PO numbers (accept "PO" prefix)
        valid_entries = []
        for po in po_entries:
            # Remove "PO" prefix if present for URL, keep original for filename
            clean_po = po.replace("PO", "").strip()
            if clean_po.isdigit():
                valid_entries.append((po, clean_po))
            else:
                print(f"⚠️ Invalid PO number format: {po}")

        if not valid_entries:
            print("❌ No valid PO numbers provided.")
            return

        print(
            f"Processing {len(valid_entries)} PO(s): {[entry[0] for entry in valid_entries]}"
        )

        for display_po, clean_po in valid_entries:
            download_attachments_for_po(display_po, clean_po, driver_instance)

    except KeyboardInterrupt:
        print("\nScript interrupted by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Clean up browser processes
        cleanup_browser_processes()
        
        # Close the driver if it exists
        if driver_instance:
            try:
                driver_instance.quit()
                print("✅ Browser closed successfully.")
            except Exception as e:
                print(f"⚠️ Warning: Could not close browser cleanly: {e}")
        else:
            print("ℹ️ No browser instance to close.")


if __name__ == "__main__":
    main()
