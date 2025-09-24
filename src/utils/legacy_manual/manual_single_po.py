#!/usr/bin/env python3
"""Legacy helper to exercise the modern downloader for a single PO.

This script is kept for manual diagnostics only. It mirrors the
functionality of the old ``test_single_po.py`` utility but relies on the
current ``src.core`` modules instead of the removed ``DownloadManager`` /
``LoginManager`` classes. Because it drives a real browser session it is
**not** part of the automated pytest suite anymore.

Usage (from the project root)::

    python -m src.utils.legacy_manual.manual_single_po --po PO123456

The script launches Edge, prompts for authentication if needed and then
invokes :meth:`Downloader.download_attachments_for_po` to gather
attachments.
"""

from __future__ import annotations

import argparse
import time
from typing import Optional

from src.core.browser import BrowserManager
from src.core.config import Config
from src.core.downloader import Downloader


def _prompt_for_manual_login(driver) -> None:
    """Pause the run if the current page looks like a login screen."""
    try:
        current = (driver.current_url or "").lower()
    except Exception:
        current = ""
    if any(token in current for token in ("login", "sign_in", "identity")):
        input("🔐 Complete the Coupa login in the browser and press Enter to continue…")


def run_single_po(po_number: str, wait_after_login: float = 2.0) -> None:
    """Download attachments for ``po_number`` and print a short summary."""
    print(f"
🧪 Exercising downloader for {po_number}")
    browser_manager = BrowserManager()
    driver = browser_manager.initialize_driver()
    downloader = Downloader(driver, browser_manager)

    try:
        print("🌐 Opening Coupa landing page to check authentication…")
        driver.get(Config.BASE_URL)
        time.sleep(wait_after_login)
        _prompt_for_manual_login(driver)

        result = downloader.download_attachments_for_po(po_number)
        print("
📋 Downloader summary:")
        for key in (
            "success",
            "message",
            "supplier_name",
            "attachments_found",
            "attachments_downloaded",
            "coupa_url",
        ):
            print(f"  • {key}: {result.get(key)}")

        names = result.get("attachment_names") or []
        if names:
            print("
📎 Attachment names:")
            for idx, name in enumerate(names, 1):
                print(f"  {idx:02d}. {name}")

            duplicates = len(names) != len(set(names))
            if duplicates:
                print("⚠️ Duplicate filenames detected. Review counter suffix behaviour.")
            else:
                print("✅ All attachment names are unique.")
        else:
            print("ℹ️ No attachment names were returned by the downloader.")

    finally:
        if Config.CLOSE_BROWSER_AFTER_EXECUTION:
            try:
                browser_manager.cleanup()
            except Exception:
                pass


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Legacy single-PO diagnostic helper.")
    parser.add_argument("--po", dest="po_number", required=False, default="PO16928033",
                        help="PO number to load (default: %(default)s)")
    parser.add_argument("--wait", dest="wait_after_login", type=float, default=2.0,
                        help="Seconds to wait after landing on Coupa before checking login")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    run_single_po(args.po_number, wait_after_login=args.wait_after_login)
