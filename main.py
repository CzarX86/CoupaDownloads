import os
import re
import shutil
import time
import winreg
from typing import List

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Manual Driver Setup Instructions:
# 1. Determine your Edge version via edge://settings/help
# 2. Download matching driver from:
#    https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
# 3. Place driver in 'drivers' folder as: edgedriver_[VERSION].exe
#    Example: edgedriver_124.0.2478.80.exe


def get_edge_version():
    """Detect installed Edge version using Windows registry"""
    try:
        # Try Current User registry first
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Edge\BLBeacon"
        )
        version, _ = winreg.QueryValueEx(key, "version")
        winreg.CloseKey(key)
        return version
    except OSError:
        try:
            # Fallback to Local Machine registry
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\WOW6432Node\Microsoft\Edge\BLBeacon",
            )
            version, _ = winreg.QueryValueEx(key, "version")
            winreg.CloseKey(key)
            return version
        except OSError as e:
            raise Exception("Failed to detect Edge version from registry") from e


# Configuration
BASE_URL = "https://unilever.coupahost.com/order_headers/{}"
DOWNLOAD_FOLDER = r"C:\CoupaDownloads"
ALLOWED_EXTENSIONS = [".pdf", ".msg", ".docx"]

# Create download folder if it doesn't exist
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Set up Edge options for visible demonstration
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

# Initialize Edge WebDriver with local driver
try:
    edge_version = get_edge_version()
    driver_path = os.path.join("drivers", f"edgedriver_{edge_version}.exe")

    if not os.path.exists(driver_path):
        raise FileNotFoundError(
            f"EdgeDriver {edge_version} not found in drivers directory.\n"
            "Please download manually from:\n"
            "https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/\n"
            f"and save as: {os.path.basename(driver_path)}"
        )

    driver = webdriver.Edge(service=Service(driver_path), options=options)
    print(f"Using EdgeDriver: {driver_path}")

except Exception as e:
    print(f"Driver initialization failed: {e}")
    print("Refer to manual setup instructions in comments")
    raise


def download_attachments_for_po(display_po: str, clean_po: str) -> None:
    try:
        url = BASE_URL.format(clean_po)
        print(f"Processing PO #{display_po} (URL: {url})")
        driver.get(url)

        # Check if page is accessible
        if "Page not found" in driver.title:
            print(f"  PO #{display_po} not found. Skipping.")
            return

        # Wait for attachments to load
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "span[aria-label*='file attachment']")
                )
            )
        except TimeoutException:
            print(f"  Timed out waiting for attachments on PO #{display_po}")
            return

        # Find all attachment elements
        attachments = driver.find_elements(
            By.CSS_SELECTOR, "span[aria-label*='file attachment']"
        )
        if not attachments:
            print(f"  No attachments found for PO #{display_po}")
            return

        print(f"  Found {len(attachments)} attachments. Downloading...")

        # Download each attachment individually
        for attachment in attachments:
            try:
                # Get filename from aria-label
                aria_label = attachment.get_attribute("aria-label")
                filename_match = re.search(r"(.+?)\s*file attachment", aria_label)
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
                driver.execute_script("arguments[0].scrollIntoView();", attachment)
                attachment.click()
                print(f"    Downloading: {filename}")

                # Brief pause between downloads
                time.sleep(1)

            except Exception as e:
                print(f"    Failed to download attachment: {str(e)}")

        # Wait for all downloads to complete
        wait_for_download_complete(DOWNLOAD_FOLDER, timeout=len(attachments) * 10)

    except TimeoutException:
        print(f"  Timed out waiting for PO #{display_po} page to load. Skipping.")
    except Exception as e:
        print(f"  Error processing PO #{display_po}: {str(e)}")

        # Process each attachment
        for span in attachment_spans:
            try:
                aria_label = span.get_attribute("aria-label")
                # Extract filename from aria-label (e.g., "filename.pdf file attachment")
                filename_match = re.search(r"(.+?)\s*file attachment", aria_label)
                if not filename_match:
                    print(
                        f"Could not extract filename from aria-label for PO #{display_po}: {aria_label}"
                    )
                    continue
                original_filename = filename_match.group(1)

                # Check if the file has an allowed extension
                if not any(
                    original_filename.lower().endswith(ext)
                    for ext in ALLOWED_EXTENSIONS
                ):
                    print(
                        f"Skipping file with unsupported extension for PO #{display_po}: {original_filename}"
                    )
                    continue

                # Highlight and click attachment with visual feedback
                print(f"➡️ Clicking attachment: {original_filename}")
                driver.execute_script("arguments[0].style.border='3px solid red'", span)
                time.sleep(1)
                span.click()
                driver.execute_script("arguments[0].style.border=''", span)
                print(f"✔️ Clicked attachment: {original_filename}")
                time.sleep(1)  # Pause to show click effect

                # Wait for download with timeout
                print(f"Waiting for download: {original_filename}")
                downloaded_file = None
                start_time = time.time()
                while time.time() - start_time < 30:  # 30-second timeout
                    time.sleep(1)
                    # Check for browser's temporary download files
                    for file in os.listdir(DOWNLOAD_FOLDER):
                        # Match actual Edge download behavior with possible .crdownload temp files
                        if file.startswith(
                            original_filename.split(".")[0]
                        ) and not file.endswith(".crdownload"):
                            downloaded_file = file
                            break
                    if downloaded_file:
                        break
                if not downloaded_file:
                    print(f"Download timeout for {original_filename} after 30 seconds")
                    continue

                if not downloaded_file:
                    print(
                        f"File download failed for PO #{display_po}: {original_filename}"
                    )
                    continue

                # Rename and move the file
                new_filename = f"{display_po}_{original_filename}"
                new_filepath = os.path.join(DOWNLOAD_FOLDER, new_filename)
                original_filepath = os.path.join(DOWNLOAD_FOLDER, downloaded_file)

                # Handle case where file already exists
                if os.path.exists(new_filepath):
                    os.remove(new_filepath)  # Overwrite existing file
                shutil.move(original_filepath, new_filepath)
                print(f"✔️ File saved as {new_filename}")
                time.sleep(1)  # Pause to show completion

            except Exception as e:
                print(
                    f"Error processing attachment {original_filename} for PO #{display_po}: {e}"
                )
                continue

    except Exception as e:
        print(f"Error processing PO #{display_po}: {e}")


def main() -> None:
    try:
        print(
            "Paste the list of PO numbers (one per line) and press Enter twice to finish:"
        )
        po_entries = []
        while True:
            line = input()
            if line == "":
                break
            po_entries.append(line.strip())

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
            download_attachments_for_po(display_po, clean_po)

    except KeyboardInterrupt:
        print("\nScript interrupted by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        driver.quit()
        print("Browser closed.")


if __name__ == "__main__":
    main()
