import os
import time
import winreg

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def get_edge_version():
    """Detect installed Edge version using Windows registry"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Edge\BLBeacon"
        )
        version, _ = winreg.QueryValueEx(key, "version")
        winreg.CloseKey(key)
        return version
    except OSError:
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\WOW6432Node\Microsoft\Edge\BLBeacon",
            )
            version, _ = winreg.QueryValueEx(key, "version")
            winreg.CloseKey(key)
            return version
        except OSError as e:
            raise Exception("Failed to detect Edge version from registry") from e


def setup_driver():
    """Configure and return Edge WebDriver"""
    options = EdgeOptions()
    options.add_argument("--disable-extensions")
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    edge_version = get_edge_version()
    driver_path = os.path.join("drivers", f"edgedriver_{edge_version}.exe")

    if not os.path.exists(driver_path):
        raise FileNotFoundError(
            f"EdgeDriver {edge_version} not found in drivers directory.\n"
            "Please download manually from:\n"
            "https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/\n"
            f"and save as: {os.path.basename(driver_path)}"
        )

    return webdriver.Edge(service=Service(driver_path), options=options)


def debug_po_page(user_input):
    """Debug a PO page and capture diagnostics"""
    # Use original input for display/filenames, cleaned version for URL
    display_po = user_input
    url_po = user_input.replace("PO", "").strip()

    driver = setup_driver()
    debug_dir = f"debug_{display_po}"
    os.makedirs(debug_dir, exist_ok=True)

    try:
        # Navigate to PO page
        url = f"https://unilever.coupahost.com/order_headers/{url_po}"
        print(f"Debugging PO #{display_po} at URL: {url}")
        driver.get(url)

        # Wait for page load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Capture page source
        page_source = driver.page_source
        with open(
            os.path.join(debug_dir, f"{po_number}_source.html"), "w", encoding="utf-8"
        ) as f:
            f.write(page_source)

        # Capture screenshot
        driver.save_screenshot(os.path.join(debug_dir, f"{po_number}_screenshot.png"))

        # Find and log attachments
        attachment_spans = driver.find_elements(
            By.CSS_SELECTOR, "span[aria-label*='file attachment']"
        )
        print(f"Found {len(attachment_spans)} attachment elements")

        # Log attachment details
        with open(os.path.join(debug_dir, f"{display_po}_elements.txt"), "w") as f:
            for i, span in enumerate(attachment_spans):
                aria_label = span.get_attribute("aria-label")
                f.write(f"Attachment {i+1}:\n")
                f.write(f"  Aria-label: {aria_label}\n")
                f.write(f"  Outer HTML: {span.get_attribute('outerHTML')}\n\n")

        print(f"Debug data saved to {debug_dir}/ directory")

    except Exception as e:
        print(f"Debug failed: {e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    user_input = input("Enter PO number to debug: ").strip()
    debug_po_page(user_input)
    po_number = user_input.replace("PO", "")
    debug_po_page(po_number)
