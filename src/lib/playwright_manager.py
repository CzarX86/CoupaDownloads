"""
Playwright management module for advanced execution modes.
Provides resource blocking and efficient browser automation.
"""

import os
from typing import Optional, List, Dict, Any
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext

from ..config.app_config import Config
from .folder_hierarchy import FolderHierarchyManager

class PlaywrightManager:
    """
    Manages Playwright browser lifecycle and optimized configurations.
    """
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
    def start(self, headless: bool = True, execution_mode: str = "standard", profile_dir: Optional[str] = None) -> Page:
        """Start Playwright browser with optimized settings and authentication."""
        self.playwright = sync_playwright().start()
        
        # Determine profile directory
        edge_profile_dir = profile_dir or Config.EDGE_PROFILE_DIR
        
        # Use Edge channel (msedge) instead of Chromium to maintain cookie compatibility
        # Edge cookies are encrypted with Edge-specific keys, so we must use actual Edge
        channel = "msedge"
        
        # Launch browser with persistent context if profile is available
        if edge_profile_dir and os.path.exists(edge_profile_dir):
            print(f"🔐 Using persistent Edge profile: {edge_profile_dir}")
            # Launch persistent context with Edge channel (maintains cookies/session)
            self.context = self.playwright.chromium.launch_persistent_context(
                user_data_dir=edge_profile_dir,
                channel=channel,
                headless=headless,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
                accept_downloads=True,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        else:
            # Fallback to non-persistent context (will require login)
            print("⚠️ No Edge profile found. Using non-persistent context (may require login).")
            self.browser = self.playwright.chromium.launch(
                channel=channel,
                headless=headless,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            
            self.context = self.browser.new_context(
                accept_downloads=True,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            self.page = self.context.new_page()
        
        # Apply resource blocking if in filtered or no_js mode
        mode_str = getattr(execution_mode, 'value', str(execution_mode))
        if mode_str in ("filtered", "no_js"):
            self._setup_resource_blocking(mode_str)
            
        return self.page
    
    def _setup_resource_blocking(self, mode: str) -> None:
        """Configure resource interception to block heavy assets."""
        blocked_types = ["image", "font", "media"]
        if mode == "filtered":
            blocked_types.append("stylesheet")
        
        print(f"🛡️ Setting up resource blocking for mode: {mode}")
        print(f"   Blocking types: {blocked_types}")
            
        blocked_patterns = [
            "google-analytics.com",
            "doubleclick.net",
            "facebook.net",
            "segment.io",
            "hotjar.com",
            "sentry.io",
        ]
        
        blocked_count = [0]  # Use list to allow mutation in closure
        
        def intercept(route):
            request = route.request
            resource_type = request.resource_type
            
            # Block by type
            if resource_type in blocked_types:
                blocked_count[0] += 1
                if blocked_count[0] <= 5:  # Log first 5 blocks
                    print(f"   🚫 Blocked {resource_type}: {request.url[:80]}...")
                route.abort()
                return
            
            # Block by URL pattern (analytics, etc)
            url = request.url.lower()
            if any(pattern in url for pattern in blocked_patterns):
                blocked_count[0] += 1
                route.abort()
                return
                
            # Block scripts if in no_js mode
            if mode == "no_js" and resource_type == "script":
                blocked_count[0] += 1
                route.abort()
                return
                
            route.continue_()
        
        # Apply to context for persistent contexts, or page otherwise
        if self.context:
            self.context.route("**/*", intercept)
            print(f"🛡️ Resource blocking enabled on CONTEXT for mode: {mode}")
        else:
            self.page.route("**/*", intercept)
            print(f"🛡️ Resource blocking enabled on PAGE for mode: {mode}")

    def process_po(self, po_number: str, po_data: Dict[str, Any], hierarchy_cols: List[str], has_hierarchy: bool) -> Dict[str, Any]:
        """Process a single PO using Playwright."""
        if not self.page:
            raise RuntimeError("Playwright page not initialized")
            
        print(f"⚡ Processing PO {po_number} with Playwright")
        
        # Setup folder structure
        folder_manager = FolderHierarchyManager()
        try:
            base_path = folder_manager.create_folder_path(
                po_data, hierarchy_cols, has_hierarchy
            )
        except Exception:
             base_path = os.path.join(Config.DOWNLOAD_FOLDER, po_number or "PO")
        
        folder_path = f"{base_path}__WORK"
        os.makedirs(folder_path, exist_ok=True)
        
        # Navigate to PO using the same route pattern as Selenium/HTTP paths.
        # Coupa order pages are consistently resolved via /order_headers/{id}.
        up = (po_number or "").upper()
        order_number = po_number[2:] if up.startswith(("PO", "PM")) else po_number
        po_url = f"{Config.BASE_URL}/order_headers/{order_number}"
        try:
            self.page.goto(po_url, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            return {
                "success": False,
                "error": f"Navigation failed: {str(e)}",
                "po_number": po_number,
                "status_code": "FAILED"
            }
            
        # Check for access denied or not found
        content = self.page.content()
        if "Access Denied" in content or "Not Found" in content:
             return {
                "success": False,
                "error": "Access Denied or Not Found",
                "po_number": po_number,
                "status_code": "PO_NOT_FOUND"
            }

        # Find attachments
        attachments = []
        try:
            # Common selectors for attachments
            selectors = [
                Config.ATTACHMENT_SELECTOR,
                "a[href*='/attachments/']",
                ".associated-file",
                "a[href*='download']",
                "a[download]",
            ]
            
            for selector in selectors:
                elements = self.page.locator(selector).all()
                for el in elements:
                    if el.is_visible():
                        attachments.append(el)
                        
            # Remove duplicates based on href
            seen_hrefs = set()
            unique_attachments = []
            for el in attachments:
                href = el.get_attribute("href")
                if href and href not in seen_hrefs:
                    seen_hrefs.add(href)
                    unique_attachments.append(el)
            attachments = unique_attachments
            
        except Exception as e:
            print(f"Error finding attachments: {e}")
            
        print(f"   Found {len(attachments)} attachments")
        
        downloaded = 0
        download_errors = []
        
        # Download attachments
        for i, attachment in enumerate(attachments):
            try:
                with self.page.expect_download(timeout=30000) as download_info:
                    attachment.click()
                download = download_info.value
                
                # Save to folder
                filename = download.suggested_filename
                save_path = os.path.join(folder_path, filename)
                download.save_as(save_path)
                downloaded += 1
                print(f"   Downloaded: {filename}")
                
            except Exception as e:
                print(f"   Failed to download attachment {i}: {e}")
                download_errors.append(str(e))
                
        # Finalize status
        status_code = "COMPLETED"
        if len(attachments) == 0:
            status_code = "NO_ATTACHMENTS"
        elif downloaded < len(attachments):
            status_code = "PARTIAL"
        elif downloaded == 0 and len(attachments) > 0:
            status_code = "FAILED"
            
        # Finalize folder name according to status
        final_folder = folder_manager.finalize_folder(folder_path, status_code)
        
        return {
            "success": status_code in ("COMPLETED", "PARTIAL", "NO_ATTACHMENTS"),
            "po_number": po_number,
            "status_code": status_code,
            "attachments_found": len(attachments),
            "attachments_downloaded": downloaded,
            "final_folder": final_folder,
            "download_folder": final_folder,
            "message": f"Processed with Playwright. Found {len(attachments)}, Downloaded {downloaded}",
            "coupa_url": po_url 
        }


    def cleanup(self) -> None:
        """Close browser and stop Playwright."""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        print("✅ Playwright browser closed.")
