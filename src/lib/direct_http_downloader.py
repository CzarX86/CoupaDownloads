"""
Direct HTTP Downloader for Mach-level extraction (Turbo Mode).
Uses httpx and BeautifulSoup for maximum performance without browser overhead.
"""

import os
import httpx
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple, Callable, Any
from urllib.parse import urljoin, urlparse

from ..config.app_config import Config

class DirectHTTPDownloader:
    """
    Handles downloading attachments using direct HTTP requests.
    Requires authenticated session cookies.
    """

    def __init__(
        self,
        cookies: Dict[str, str],
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.cookies = cookies
        self._progress_callback = progress_callback
        self.client = httpx.Client(
            cookies=cookies,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
            follow_redirects=True,
            timeout=30.0
        )

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

    def download_attachments_for_po(
        self, 
        po_number: str, 
        on_attachments_found: Optional[Callable[[Dict[str, Any]], str]] = None
    ) -> dict:
        """Main workflow for Direct HTTP download."""
        up = (po_number or "").upper()
        order_number = po_number[2:] if up.startswith(("PO", "PM")) else po_number
        url = f"{Config.BASE_URL}/order_headers/{order_number}"
        
        print(f"\nProcessing PO #{po_number} (Turbo/HTTP)")
        
        try:
            response = self.client.get(url)
            response.raise_for_status()
        except Exception as e:
            return {'success': False, 'status_code': 'NETWORK_ERROR', 'message': f"HTTP request failed: {e}"}

        soup = BeautifulSoup(response.text, 'lxml')
        
        # Check for error page
        if "order_headers" not in str(response.url):
            return {'success': False, 'status_code': 'PO_NOT_FOUND', 'message': 'Redirected to non-PO page (possible error)'}

        # Extract supplier
        supplier = ""
        for sel in Config.SUPPLIER_NAME_CSS_SELECTORS or []:
            el = soup.select_one(sel)
            if el:
                supplier = el.get_text(strip=True)
                break
        
        # Find attachments
        attachment_links = []
        selector = Config.ATTACHMENT_SELECTOR
        for a in soup.select(selector):
            href = a.get('href')
            if href and href not in ('#', ''):
                attachment_links.append({
                    'url': urljoin(url, href),
                    'name': a.get('title') or a.get('aria-label') or a.get_text(strip=True) or os.path.basename(href)
                })
        
        # Deduplicate
        seen_urls = set()
        unique_links = []
        for link in attachment_links:
            if link['url'] not in seen_urls:
                seen_urls.add(link['url'])
                unique_links.append(link)

        found_count = len(unique_links)
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

        # Download logic
        downloaded = 0
        names = []
        for i, link in enumerate(unique_links):
            try:
                res = self.client.get(link['url'])
                res.raise_for_status()
                
                # Try to get filename from Content-Disposition
                cd = res.headers.get('Content-Disposition')
                filename = link['name']
                if cd and 'filename=' in cd:
                    filename = cd.split('filename=')[1].strip('"')
                
                # Sanitize filename
                import re
                filename = re.sub(r'[<>:"/\\|?*\s]+', '_', filename).strip('_')
                if not filename:
                    filename = f"attachment_{i+1}"
                
                save_path = os.path.join(download_path, filename) if download_path else filename
                with open(save_path, 'wb') as f:
                    f.write(res.content)
                
                downloaded += 1
                names.append(filename)
                print(f"      ✅ Downloaded: {filename} ({i+1}/{found_count})")
                
                self._emit_progress("PROCESSING", found_count, downloaded, f"Downloaded {downloaded}/{found_count}")
            except Exception as e:
                print(f"      ❌ Failed to download {link['url']}: {e}")

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

    def close(self):
        self.client.close()
