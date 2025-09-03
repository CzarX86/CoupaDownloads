import os
import time
from typing import List, Optional, Tuple
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException

from .browser import BrowserManager
from .config import Config


class Downloader:
    """
    Handles downloading attachments for a given PO number.
    This simplified version uses direct clicks and robust waits, based on
    successful test implementations.
    """

    def __init__(self, driver, browser_manager: BrowserManager):
        self.driver = driver
        self.browser_manager = browser_manager

    def _extract_filename_from_element(
        self,
        attachment: WebElement,
    ) -> Optional[str]:
        """
        Extracts a filename from a Selenium WebElement using multiple strategies.
        This version is corrected to handle more edge cases.
        """
        # Strategy 1: Check text content for a filename with a valid extension
        text_content = attachment.text.strip()
        if text_content and any(
            ext in text_content.lower() for ext in Config.ALLOWED_EXTENSIONS
        ):
            return text_content

        # Strategy 2: Check 'aria-label' for descriptive text
        aria_label = attachment.get_attribute("aria-label")
        if aria_label and "file attachment" in aria_label:
            filename = aria_label.split("file attachment")[0].strip()
            if filename:  # Ensure it's not empty
                return filename

        # Strategy 3: Check 'title' attribute
        title = attachment.get_attribute("title")
        if title:
            # Check if title itself could be a filename
            if any(ext in title.lower() for ext in Config.ALLOWED_EXTENSIONS):
                return title

        # Strategy 4: Check 'href' for a downloadable link
        href = attachment.get_attribute("href")
        if href and href.strip() not in ("#", ""):
            # Check if the href contains something that looks like a file
            basename = os.path.basename(href)
            if "." in basename:  # A simple check for an extension
                return basename

        return None

    def _find_attachments(self) -> List[WebElement]:
        """
        Waits for and finds all attachment elements on the page using a robust
        WebDriverWait as proven effective in tests.
        """
        try:
            WebDriverWait(self.driver, Config.ATTACHMENT_WAIT_TIMEOUT).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, Config.ATTACHMENT_SELECTOR)
                )
            )
            attachments = self.driver.find_elements(
                By.CSS_SELECTOR, Config.ATTACHMENT_SELECTOR
            )
            print(f"   ─ Found {len(attachments)} potential attachment(s).")
            return attachments
        except TimeoutException:
            print("   ⚠ Timed out waiting for attachments to appear.")
            return []

    def _download_attachment(self, attachment: WebElement, filename: str) -> bool:
        """
        Performs a click on the attachment element with multiple fallback strategies
        to handle element click interception issues.
        """
        try:
            print(f"      ⬇ Clicking to download '{filename}'...")
            
            # Strategy 1: Try direct click first
            try:
                attachment.click()
                time.sleep(Config.PAGE_DELAY)
                return True
            except ElementClickInterceptedException:
                print(f"         ⚠ Element click intercepted, trying fallback strategies...")
                
                # Strategy 2: Scroll element into view and try again
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", attachment)
                    time.sleep(0.5)  # Brief pause for scroll to complete
                    attachment.click()
                    time.sleep(Config.PAGE_DELAY)
                    return True
                except ElementClickInterceptedException:
                    print(f"         ⚠ Still intercepted after scroll, trying JavaScript click...")
                    
                    # Strategy 3: Use JavaScript click
                    try:
                        self.driver.execute_script("arguments[0].click();", attachment)
                        time.sleep(Config.PAGE_DELAY)
                        return True
                    except Exception as js_error:
                        print(f"         ⚠ JavaScript click failed: {js_error}")
                        
                        # Strategy 4: Try to hide the floating element temporarily
                        try:
                            # Hide the floating buttons that might be intercepting
                            floating_elements = self.driver.find_elements(
                                By.CSS_SELECTOR, 
                                ".page_buttons_right.orderHeaderShowFloatingSection.floatingSectionOnTop"
                            )
                            if floating_elements:
                                self.driver.execute_script(
                                    "arguments[0].style.display = 'none';", 
                                    floating_elements[0]
                                )
                                time.sleep(0.3)
                                attachment.click()
                                time.sleep(Config.PAGE_DELAY)
                                # Restore the floating element
                                self.driver.execute_script(
                                    "arguments[0].style.display = 'block';", 
                                    floating_elements[0]
                                )
                                return True
                        except Exception as hide_error:
                            print(f"         ⚠ Hide strategy failed: {hide_error}")
                            
                            # Strategy 5: Final attempt with coordinates
                            try:
                                # Get element location and click at a specific point
                                location = attachment.location
                                size = attachment.size
                                # Click in the center of the element
                                x = location['x'] + size['width'] // 2
                                y = location['y'] + size['height'] // 2
                                
                                from selenium.webdriver.common.action_chains import ActionChains
                                actions = ActionChains(self.driver)
                                actions.move_to_element(attachment).click().perform()
                                time.sleep(Config.PAGE_DELAY)
                                return True
                            except Exception as coord_error:
                                print(f"         ⚠ Coordinate click failed: {coord_error}")
                                return False
                                
        except Exception as e:
            print(f"      ❌ Failed to click on attachment '{filename}'. Reason: {e}")
            return False

    def download_attachments_for_po(self, po_number: str) -> Tuple[bool, str]:
        """
        Main workflow to find and download all attachments for a specific PO.
        Returns a tuple of (success_status, message).
        """
        # Remove "PO" prefix if present to get the correct order number
        order_number = po_number.replace("PO", "") if po_number.startswith("PO") else po_number
        url = f"{Config.BASE_URL}/order_headers/{order_number}"
        print(f"\nProcessing PO #{po_number}")
        print(f"   Navigating to: {url}")
        self.driver.get(url)

        # Check for error page, a useful feature from the recent changes
        if "Oops! We couldn't find what you wanted" in self.driver.page_source:
            msg = "PO not found or page error detected."
            print(f"   ❌ {msg}")
            return False, msg

        attachments = self._find_attachments()
        if not attachments:
            msg = "No attachments found."
            print(f"   ✅ {msg}")
            return True, msg

        total_attachments = len(attachments)
        print(f"   Processing {total_attachments} attachments...")
        downloaded_count = 0

        for i, attachment in enumerate(attachments):
            filename = self._extract_filename_from_element(attachment)
            if not filename:
                print(
                    f"      ⚠ Could not determine filename for attachment {i+1}, skipping."
                )
                continue

            # The browser will handle duplicate downloads automatically
            # (e.g., file.pdf, file (1).pdf). The old complex logic is removed.
            if self._download_attachment(attachment, filename):
                downloaded_count += 1

        if downloaded_count > 0:
            msg = (
                f"Initiated download for {downloaded_count}/{total_attachments} "
                "attachments."
            )
            print(f"   ✅ {msg}")
            return True, msg
        else:
            msg = f"Failed to download any of the {total_attachments} attachments."
            print(f"   ❌ {msg}")
            return False, msg
