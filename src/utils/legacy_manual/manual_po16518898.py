#!/usr/bin/env python3
"""Legacy duplicate-handling check using the modern downloader.

This module supersedes the old ``test_po16518898_main.py`` utility. It is
kept as a **manual** diagnostic helper to confirm that filename deduplication
continues to work for PO16518898 (or any other PO).  It no longer depends on
the removed ``DownloadManager`` class and therefore does not run inside the
pytest suite.

Usage (from the project root)::

    python -m src.utils.legacy_manual.manual_po16518898 --po PO16518898

Optionally pass ``--download-dir`` to force a temporary folder so you can
inspect the downloaded files afterwards.
"""

from __future__ import annotations

import argparse
import os
import time
from collections import Counter
from typing import Optional

from src.core.browser import BrowserManager
from src.core.config import Config
from src.core.downloader import Downloader


def _prompt_for_manual_login(driver) -> None:
    try:
        current = (driver.current_url or '').lower()
    except Exception:
        current = ''
    if any(token in current for token in ('login', 'sign_in', 'identity')):
        input('🔐 Complete the Coupa login in the browser and press Enter to continue…')


def run_duplicate_check(po_number: str, download_dir: Optional[str] = None,
                        wait_after_login: float = 2.0) -> None:
    print(f"
🧪 Checking duplicate handling for {po_number}")
    browser_manager = BrowserManager()
    if download_dir:
        os.makedirs(download_dir, exist_ok=True)
        driver = browser_manager.initialize_driver_with_download_dir(download_dir)
    else:
        driver = browser_manager.initialize_driver()
    downloader = Downloader(driver, browser_manager)

    try:
        print('🌐 Opening Coupa landing page to check authentication…')
        driver.get(Config.BASE_URL)
        time.sleep(wait_after_login)
        _prompt_for_manual_login(driver)

        result = downloader.download_attachments_for_po(po_number)
        names = result.get('attachment_names') or []

        print('
📋 Downloader summary:')
        for key in (
            'success', 'message', 'supplier_name',
            'attachments_found', 'attachments_downloaded', 'coupa_url'
        ):
            print(f'  • {key}: {result.get(key)}')

        if not names:
            print('ℹ️ No attachment names returned by the downloader.')
            return

        counts = Counter(names)
        duplicates = {name: count for name, count in counts.items() if count > 1}

        print('
📎 Attachment names:')
        for idx, name in enumerate(names, 1):
            suffix = f' (x{counts[name]})' if counts[name] > 1 else ''
            print(f'  {idx:02d}. {name}{suffix}')

        if duplicates:
            print('
⚠️ Duplicate filenames detected:')
            for name, count in duplicates.items():
                print(f'  • {name}: {count} occurrences')
        else:
            print('
✅ All attachment names are unique.')

    finally:
        if Config.CLOSE_BROWSER_AFTER_EXECUTION:
            try:
                browser_manager.cleanup()
            except Exception:
                pass


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Legacy duplicate-handling diagnostic helper.')
    parser.add_argument('--po', dest='po_number', default='PO16518898',
                        help='PO number to fetch (default: %(default)s)')
    parser.add_argument('--download-dir', dest='download_dir', default=None,
                        help='Optional directory where downloads should be stored')
    parser.add_argument('--wait', dest='wait_after_login', type=float, default=2.0,
                        help='Seconds to wait after opening Coupa before prompting for login')
    return parser.parse_args(argv)


if __name__ == '__main__':
    args = _parse_args()
    run_duplicate_check(args.po_number, download_dir=args.download_dir,
                        wait_after_login=args.wait_after_login)
