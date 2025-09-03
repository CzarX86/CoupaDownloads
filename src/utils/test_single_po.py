#!/usr/bin/env python3
"""
Focused test for a single PO page to validate attachment discovery and download start.

Usage:
  VERBOSE_OUTPUT=true python src/utils/test_single_po.py 16928033
"""

import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from core.config import Config
from core.browser import BrowserManager
from core.downloader import DownloadManager, LoginManager


def run_single_po_test(po_number: str) -> None:
    print(f"\n🧪 Testing single PO: {po_number}")
    browser_manager = BrowserManager()
    driver = browser_manager.initialize_driver()
    login = LoginManager(driver)
    downloader = DownloadManager(driver)

    try:
        # Ensure logged in if needed
        login.ensure_logged_in()

        clean_po = po_number.replace("PO", "").replace("PM", "")
        url = Config.BASE_URL.format(clean_po)
        print(f"🌐 Navigating to: {url}")
        driver.get(url)

        # Wait for full load and open attachments section
        downloader._wait_for_page_complete()
        downloader._ensure_attachments_section_open()

        # Find attachments (with combined strategies)
        attachments = downloader._wait_until_attachments_ready()
        print(f"🔎 Attachments found: {len(attachments)}")
        for i, a in enumerate(attachments, 1):
            try:
                tag = a.tag_name
                href = a.get_attribute("href")
                aria = a.get_attribute("aria-label")
                text = (a.text or "").strip()
                print(f"  {i:02d}: <{tag}> href={href} aria={aria} text={text[:80]}")
            except Exception:
                pass

        if not attachments:
            print("❌ No attachments detected on this page.")
            return

        # Trigger all downloads
        print("📥 Clicking all attachments to trigger downloads...")
        for idx, el in enumerate(attachments):
            downloader._download_attachment_simple(el, idx, len(attachments))

        # Confirm downloads started via .crdownload
        print("⏳ Waiting up to 15s for downloads to start...")
        started = downloader._wait_for_downloads_to_start(attachments, timeout=15)
        if started:
            print("✅ Downloads started successfully.")
        else:
            # Show any .crdownload files to aid debugging
            try:
                crd = [f for f in os.listdir(Config.DOWNLOAD_FOLDER) if f.endswith('.crdownload')]
                print(f"⚠️ Downloads not confirmed. .crdownload present: {crd}")
            except Exception:
                print("⚠️ Downloads not confirmed and could not list download folder.")

    finally:
        # Keep browser if configured
        if Config.CLOSE_BROWSER_AFTER_EXECUTION:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    arg_po = sys.argv[1] if len(sys.argv) > 1 else "16928033"
    run_single_po_test(arg_po)


