"""
Playwright-based Downloader for optimized execution modes.
"""

import os
import time
from typing import Dict, List, Optional, Tuple, Callable, Any
from playwright.sync_api import Page, ElementHandle, Download

from ..config.app_config import Config

class PlaywrightDownloader:
    """
    Handles downloading attachments using Playwright.
    Optimized for speed and resource blocking.
    """

    def __init__(
        self,
        page: Page,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.page = page
        self._progress_callback = progress_callback

    def _emit_progress(
        self,
        status: str,
        attachments_found: int,
        attachments_downloaded: int,
        message: str = "",
    ) -> None:
        if not self._progress_callback:
            return
        try:
            self._progress_callback({
                'status': status,
                'attachments_found': attachments_found,
                'attachments_downloaded': attachments_downloaded,
                'message': message,
            })
        except Exception:
            pass

    def _extract_supplier_name(self) -> Optional[str]:
        """Extract supplier name using selectors."""
        for sel in Config.SUPPLIER_NAME_CSS_SELECTORS or []:
            try:
                el = self.page.query_selector(sel)
                if el:
                    txt = (el.inner_text() or '').strip()
                    if txt:
                        return txt
            except Exception:
                pass
        return None

    def _find_attachments(self) -> List[ElementHandle]:
        """Find attachment candidates."""
        candidates = []
        try:
            # Base selector
            self.page.wait_for_selector(Config.ATTACHMENT_SELECTOR, timeout=Config.ATTACHMENT_WAIT_TIMEOUT * 1000)
            candidates.extend(self.page.query_selector_all(Config.ATTACHMENT_SELECTOR))
        except Exception:
            pass

        # Robust fallbacks
        selectors = [
            "a[href*='attachment']",
            "a[href*='download']",
            "a[download]",
            "[aria-label*='attachment']",
        ]
        for sel in selectors:
            try:
                candidates.extend(self.page.query_selector_all(sel))
            except Exception:
                pass
        
        # Deduplication
        seen = set()
        unique = []
        for el in candidates:
            try:
                href = (el.get_attribute("href") or "").strip()
                # Use handle as key if href not available
                key = href if href else str(el)
                if key not in seen:
                    seen.add(key)
                    unique.append(el)
            except Exception:
                pass
        return unique

    def download_attachments_for_po(
        self, 
        po_number: str, 
        on_attachments_found: Optional[Callable[[Dict[str, Any]], str]] = None
    ) -> dict:
        """Main workflow for Playwright download."""
        up = (po_number or "").upper()
        order_number = po_number[2:] if up.startswith(("PO", "PM")) else po_number
        url = f"{Config.BASE_URL}/order_headers/{order_number}"
        
        print(f"\nProcessing PO #{po_number} (Playwright)")
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=Config.PAGE_LOAD_TIMEOUT * 1000)
        except Exception as e:
             print(f"      ❌ Page load failed for {po_number}: {e}")
             return {
                 'success': False, 
                 'status_code': 'FAILED', 
                 'message': f"Page load timeout/error: {str(e)}",
                 'coupa_url': url
             }

        
        # Check for error pages
        # (Simplified error detection for now)
        if "order_headers" not in self.page.url:
             return {'success': False, 'status_code': 'PO_NOT_FOUND', 'message': 'Possible error page'}

        attachments = self._find_attachments()
        supplier = self._extract_supplier_name()
        
        found_count = len(attachments)
        download_path = ""
        if on_attachments_found:
            download_path = on_attachments_found({
                'supplier_name': supplier or '',
                'attachments_found': found_count,
                'status_code': 'PROCESSING' if found_count > 0 else 'NO_ATTACHMENTS',
                'po_number': po_number
            })

        if found_count == 0:
            return {
                'success': True,
                'status_code': 'NO_ATTACHMENTS',
                'supplier_name': supplier or '',
                'attachments_found': 0,
                'coupa_url': url,
            }

        # Ensure we always have an absolute save directory before the download loop.
        # A bare filename (no directory) would cause Playwright to save into the process
        # working directory instead of the PO folder — silently dropping files outside
        # any PO subfolder.
        if not download_path:
            try:
                from ..config.app_config import Config as _Cfg
                _fallback = _Cfg.DOWNLOAD_FOLDER
            except Exception:
                _fallback = None
            download_path = os.path.abspath(os.path.expanduser(
                _fallback or os.path.join(os.path.expanduser('~'), 'Downloads', 'CoupaDownloads')
            ))
            os.makedirs(download_path, exist_ok=True)
            print(f"      ⚠️ [playwright] No PO folder from callback; using fallback: {download_path}")

        # Download logic
        downloaded = 0
        names = []
        for i, att in enumerate(attachments):
            try:
                # Trigger download and wait for it
                with self.page.expect_download() as download_info:
                    att.click()
                download = download_info.value
                
                filename = download.suggested_filename or f"attachment_{i+1}"
                save_path = os.path.join(download_path, filename)
                download.save_as(save_path)
                
                downloaded += 1
                names.append(filename)
                print(f"      ✅ Downloaded: {filename} ({i+1}/{found_count})")
                
                self._emit_progress("PROCESSING", found_count, downloaded, f"Downloaded {downloaded}/{found_count}")
            except Exception as e:
                print(f"      ❌ Failed to download attachment {i+1}: {e}")

        return {
            'success': downloaded == found_count,
            'status_code': 'COMPLETED' if downloaded == found_count else 'PARTIAL',
            'message': f"Downloaded {downloaded}/{found_count} attachments",
            'supplier_name': supplier or '',
            'attachments_found': found_count,
            'attachments_downloaded': downloaded,
            'attachment_names': names,
            'coupa_url': url,
        }
