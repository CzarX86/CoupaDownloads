import os
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin
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

    def _extract_supplier_name(self) -> Optional[str]:
        """Best-effort supplier name extraction using configured selectors.

        Tries multiple CSS selectors, then XPATH as fallback. Returns cleaned text
        or None if not found.
        """
        try:
            # Try CSS selectors first
            for sel in getattr(Config, 'SUPPLIER_NAME_CSS_SELECTORS', []) or []:
                try:
                    els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                except Exception:
                    els = []
                for el in els:
                    try:
                        txt = (el.text or '').strip()
                    except Exception:
                        txt = ''
                    if txt:
                        return txt
            # Fallback to XPATH
            xpath = getattr(Config, 'SUPPLIER_NAME_XPATH', '')
            if xpath:
                try:
                    el = self.driver.find_element(By.XPATH, xpath)
                    txt = (el.text or '').strip()
                    if txt:
                        return txt
                except Exception:
                    pass
        except Exception:
            pass
        return None

    def _extract_filename_from_element(
        self,
        attachment: WebElement,
    ) -> Optional[str]:
        """
        Extract a filename using prioritized attributes and sanitize result.
        Order: download -> title -> aria-label -> visible text -> href basename.
        """
        def to_anchor(el: WebElement) -> WebElement:
            try:
                return el.find_element(By.XPATH, './ancestor-or-self::a[1]')
            except Exception:
                return el

        def sanitize(name: str) -> str:
            import re
            cleaned = re.sub(r'[<>:"/\\|?*\s]+', '_', name).strip('_').rstrip('._')
            return cleaned[:150]

        el = to_anchor(attachment)
        # 1) download/title/aria-label attributes
        for source in ('download', 'title', 'aria-label'):
            try:
                val = (el.get_attribute(source) or '').strip()
            except Exception:
                val = ''
            if val:
                name = sanitize(val)
                if name:
                    return name

        # 2) visible text
        try:
            txt = (el.text or '').strip()
        except Exception:
            txt = ''
        if txt:
            name = sanitize(txt)
            if name:
                return name

        # 3) href basename (without filtering extensions)
        try:
            href = (el.get_attribute('href') or '').strip()
        except Exception:
            href = ''
        if href and href not in ('#', ''):
            base = os.path.basename(href)
            name = sanitize(base)
            if name:
                return name
        return None

    def _find_attachments(self) -> List[WebElement]:
        """
        Find attachment candidates combining the existing base selector with
        additional robust fallbacks; deduplicate by href/id.
        """
        candidates: List[WebElement] = []
        # 0) Original base selector with wait
        try:
            WebDriverWait(self.driver, Config.ATTACHMENT_WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, Config.ATTACHMENT_SELECTOR))
            )
            candidates.extend(
                self.driver.find_elements(By.CSS_SELECTOR, Config.ATTACHMENT_SELECTOR)
            )
        except TimeoutException:
            print("   ⚠ Timed out on base selector. Trying extended selectors…")

        try:
            # 1) Âncoras diretas (padrões comuns Coupa)
            direct_css = [
                "a[href*='attachment_file']",
                "a[href*='attachment']",
                "a[href*='download']",
            ]
            # 2) Fallback por extensão no href
            ext_css = [
                "a[href$='.pdf']", "a[href$='.docx']", "a[href$='.xlsx']",
                "a[href$='.msg']", "a[href$='.eml']", "a[href$='.zip']", "a[href$='.jpg']", "a[href$='.png']",
            ]
            for sel in direct_css + ext_css:
                try:
                    candidates.extend(self.driver.find_elements(By.CSS_SELECTOR, sel))
                except Exception:
                    pass

            # 3) XPath de reforço
            xpath_expr = (
                "//a[contains(@href,'attachment') or contains(@href,'download') or "
                "contains(@href,'.pdf') or contains(@href,'.docx') or contains(@href,'.xlsx') or "
                "contains(@href,'.msg') or contains(@href,'.eml') or contains(@href,'.zip') or contains(@href,'.jpg') or contains(@href,'.png')]"
            )
            try:
                candidates.extend(self.driver.find_elements(By.XPATH, xpath_expr))
            except Exception:
                pass

            # Deduplicar por href + id
            seen = set()
            unique: List[WebElement] = []
            for el in candidates:
                try:
                    href = (el.get_attribute('href') or '').strip()
                except Exception:
                    href = ''
                key = (href, getattr(el, 'id', id(el)))
                if key in seen:
                    continue
                seen.add(key)
                unique.append(el)
            print(f"   ─ Found {len(unique)} potential attachment candidate(s).")
            return unique
        except Exception as e:
            print(f"   ⚠ Attachment discovery fallback failed: {e}")
            return []

    def _short_exception(self, exc: Exception) -> str:
        """Return a brief, human-friendly description of an exception."""
        try:
            message = str(exc).strip()
        except Exception:
            message = ''
        if not message:
            message = exc.__class__.__name__
        if len(message) > 150:
            message = message[:147] + '...'
        return message

    @staticmethod
    def _summarize_download_errors(errors: List[dict], limit: int = 3) -> str:
        if not errors:
            return ''
        fragments = []
        for entry in errors[:limit]:
            name = entry.get('filename') or 'attachment'
            reason = entry.get('reason') or 'unknown issue'
            fragments.append(f"{name}: {reason}")
        remaining = len(errors) - limit
        if remaining > 0:
            fragments.append(f"+{remaining} more")
        summary = '; '.join(fragments)
        if len(summary) > 200:
            summary = summary[:197] + '...'
        return summary

    @staticmethod
    def _attachments_include_pdf(candidates: Optional[List[WebElement]]) -> bool:
        """Check whether any attachment candidate looks like a PDF file."""
        if not candidates:
            return False
        for element in candidates:
            if element is None:
                continue
            for attr in ('href', 'download', 'title', 'aria-label'):
                try:
                    payload = (element.get_attribute(attr) or '').lower()
                except Exception:
                    payload = ''
                if '.pdf' in payload:
                    return True
            try:
                text_value = (element.text or '').lower()
            except Exception:
                text_value = ''
            if '.pdf' in text_value:
                return True
        return False

    @staticmethod
    def _truncate_text(text: str, limit: int = 220) -> str:
        if not text:
            return ''
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + '...'

    def _download_attachment(self, attachment: WebElement, filename: str) -> Tuple[bool, Optional[str]]:
        """Trigger a download using several fallback strategies.

        Returns:
            Tuple (success, error_message). On success the error_message is None.
        """

        def attempt(label: str, action) -> bool:
            try:
                action()
                time.sleep(Config.PAGE_DELAY)
                return True
            except ElementClickInterceptedException as exc:
                msg = self._short_exception(exc)
                print(f"         ⚠ {label} intercepted: {msg}")
                errors.append(f"{label}: click intercepted")
            except Exception as exc:
                msg = self._short_exception(exc)
                print(f"         ⚠ {label} failed: {msg}")
                errors.append(f"{label}: {msg}")
            return False

        errors: List[str] = []
        print(f"      ⬇ Attempting download for '{filename}'...")

        if attempt('Direct click', lambda: attachment.click()):
            return True, None

        # Strategy 2: Scroll into view and retry
        def scroll_and_click() -> None:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});",
                attachment,
            )
            time.sleep(0.4)
            attachment.click()

        if attempt('Scroll + click', scroll_and_click):
            return True, None

        # Strategy 3: JavaScript click
        if attempt('JavaScript click', lambda: self.driver.execute_script("arguments[0].click();", attachment)):
            return True, None

        # Strategy 4: Temporarily hide floating toolbar that blocks clicks
        def hide_and_click() -> None:
            floating_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                ".page_buttons_right.orderHeaderShowFloatingSection.floatingSectionOnTop",
            )
            if not floating_elements:
                raise Exception('floating toolbar not found')
            target = floating_elements[0]
            self.driver.execute_script("arguments[0].style.display = 'none';", target)
            try:
                time.sleep(0.3)
                attachment.click()
            finally:
                self.driver.execute_script("arguments[0].style.display = 'block';", target)

        if attempt('Hide floating toolbar + click', hide_and_click):
            return True, None

        # Strategy 5: ActionChains fallback
        def action_chain_click() -> None:
            from selenium.webdriver.common.action_chains import ActionChains

            actions = ActionChains(self.driver)
            actions.move_to_element(attachment).click().perform()

        if attempt('ActionChains click', action_chain_click):
            return True, None

        summary = '; '.join(errors) or 'All click strategies exhausted'
        if len(summary) > 180:
            summary = summary[:177] + '...'
        print(f"      ❌ Failed to trigger download for '{filename}'. Reason: {summary}")
        return False, summary

    def _wait_for_dom_ready(self, timeout: Optional[float] = None) -> bool:
        """Wait until the document reports readyState == 'complete'."""
        wait_timeout = timeout or Config.PAGE_LOAD_TIMEOUT
        try:
            WebDriverWait(self.driver, wait_timeout).until(
                lambda drv: drv.execute_script("return document.readyState") == "complete"
            )
            return True
        except TimeoutException:
            print("   ⚠ Page did not reach readyState='complete' within timeout.")
            return False
        except Exception as exc:
            print(f"   ⚠ Error while waiting for DOM ready: {self._short_exception(exc)}")
            return False

    @staticmethod
    def _find_marker_in_text(text: str, markers: List[str]) -> Optional[str]:
        payload = (text or '').lower()
        if not payload:
            return None
        for marker in markers:
            if not marker:
                continue
            if marker.lower() in payload:
                return marker
        return None

    def _locate_error_marker(self, driver, markers: List[str]) -> Optional[dict]:
        try:
            page_marker = self._find_marker_in_text(driver.page_source, markers)
            if page_marker:
                return {'marker': page_marker, 'source': 'page_source'}
        except Exception:
            pass

        try:
            title_marker = self._find_marker_in_text(driver.title, markers)
            if title_marker:
                return {'marker': title_marker, 'source': 'title'}
        except Exception:
            pass

        selectors_css = getattr(Config, 'ERROR_PAGE_CSS_SELECTORS', []) or []
        for sel in selectors_css:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, sel)
            except Exception:
                elements = []
            for el in elements:
                marker = self._find_marker_in_text(getattr(el, 'text', ''), markers)
                if marker:
                    return {'marker': marker, 'source': f'css::{sel}'}
                if getattr(el, 'text', '').strip():
                    # Even when the full marker is not present, presence of element hints error layout
                    return {'marker': getattr(el, 'text', '').strip(), 'source': f'css::{sel}'}

        selectors_xpath = getattr(Config, 'ERROR_PAGE_XPATH_SELECTORS', []) or []
        for xp in selectors_xpath:
            try:
                elements = driver.find_elements(By.XPATH, xp)
            except Exception:
                elements = []
            for el in elements:
                marker = self._find_marker_in_text(getattr(el, 'text', ''), markers)
                if marker:
                    return {'marker': marker, 'source': f'xpath::{xp}'}
                if getattr(el, 'text', '').strip():
                    return {'marker': getattr(el, 'text', '').strip(), 'source': f'xpath::{xp}'}

        return None

    def _locate_pr_link(self, driver) -> Optional[Dict[str, str]]:
        css_selectors = getattr(Config, 'PR_LINK_CSS_SELECTORS', []) or []
        for sel in css_selectors:
            try:
                candidates = driver.find_elements(By.CSS_SELECTOR, sel)
            except Exception:
                candidates = []
            for el in candidates:
                try:
                    href = (el.get_attribute('href') or '').strip()
                except Exception:
                    href = ''
                if not href:
                    continue
                text = ''
                try:
                    text = (el.text or '').strip()
                except Exception:
                    text = ''
                return {
                    'href': href,
                    'text': text,
                    'source': f'css::{sel}'
                }

        xpath_selectors = getattr(Config, 'PR_LINK_XPATH_CANDIDATES', []) or []
        for xp in xpath_selectors:
            try:
                candidates = driver.find_elements(By.XPATH, xp)
            except Exception:
                candidates = []
            for el in candidates:
                try:
                    href = (el.get_attribute('href') or '').strip()
                except Exception:
                    href = ''
                if not href:
                    continue
                text = ''
                try:
                    text = (el.text or '').strip()
                except Exception:
                    text = ''
                return {
                    'href': href,
                    'text': text,
                    'source': f'xpath::{xp}'
                }

        link_texts = getattr(Config, 'PR_LINK_TEXT_CANDIDATES', []) or []
        for snippet in link_texts:
            try:
                candidates = driver.find_elements(By.PARTIAL_LINK_TEXT, snippet)
            except Exception:
                candidates = []
            for el in candidates:
                try:
                    href = (el.get_attribute('href') or '').strip()
                except Exception:
                    href = ''
                if not href:
                    continue
                text = ''
                try:
                    text = (el.text or '').strip()
                except Exception:
                    text = ''
                return {
                    'href': href,
                    'text': text,
                    'source': f'partial_link::{snippet}'
                }
        return None

    def _navigate_to_pr_from_po(self, order_number: str) -> Dict[str, Optional[str]]:
        info: Dict[str, Optional[str]] = {
            'status': 'not_attempted',
            'url': '',
            'href': '',
            'text': '',
            'source': '',
            'elapsed': None,
            'error': None,
            'order_number': order_number,
        }
        print("   🔁 Attempting PR fallback navigation...")

        timeout = getattr(Config, 'PR_FALLBACK_LINK_TIMEOUT', 4.0)
        poll = getattr(Config, 'PR_FALLBACK_LINK_POLL', 0.2)
        start = time.perf_counter()

        try:
            link_info = WebDriverWait(
                self.driver,
                timeout,
                poll_frequency=poll,
            ).until(lambda drv: self._locate_pr_link(drv))
        except TimeoutException:
            info['status'] = 'timeout'
            info['elapsed'] = round(time.perf_counter() - start, 3)
            print("   ⚠ PR fallback link not found within timeout window.")
            return info
        except Exception as exc:
            info['status'] = 'error'
            info['elapsed'] = round(time.perf_counter() - start, 3)
            info['error'] = self._short_exception(exc)
            print(f"   ⚠ Error while locating PR fallback link: {info['error']}")
            return info

        if not link_info:
            info['status'] = 'not_found'
            info['elapsed'] = round(time.perf_counter() - start, 3)
            print("   ⚠ No PR link candidates matched the configured selectors.")
            return info

        href = (link_info.get('href') or '').strip()
        if not href:
            info['status'] = 'missing_href'
            info['elapsed'] = round(time.perf_counter() - start, 3)
            print("   ⚠ PR link located but href attribute is empty.")
            return info

        target_url = urljoin(f"{Config.BASE_URL}/", href)
        info.update({
            'status': 'navigated',
            'href': href,
            'url': target_url,
            'text': (link_info.get('text') or '').strip(),
            'source': link_info.get('source') or '',
        })

        print(
            "   🔁 Navigating to PR page: "
            f"{target_url} (source={info['source'] or 'unknown'})"
        )

        try:
            self.driver.get(target_url)
        except Exception as exc:
            info['status'] = 'navigation_error'
            info['error'] = self._short_exception(exc)
            info['elapsed'] = round(time.perf_counter() - start, 3)
            print(f"   ⚠ Error navigating to PR page: {info['error']}")
            return info

        ready_timeout = getattr(Config, 'PR_FALLBACK_READY_TIMEOUT', 0)
        if ready_timeout and ready_timeout > 0:
            self._wait_for_dom_ready(timeout=ready_timeout)
        else:
            self._wait_for_dom_ready()

        info['elapsed'] = round(time.perf_counter() - start, 3)
        return info

    def _detect_error_page(self, phase: str, timeout: Optional[float] = None) -> Optional[dict]:
        markers = getattr(Config, 'ERROR_PAGE_MARKERS', []) or []
        poll = getattr(Config, 'ERROR_PAGE_WAIT_POLL', 0.2)
        wait_timeout = timeout or getattr(Config, 'ERROR_PAGE_CHECK_TIMEOUT', 2.0)
        start = time.perf_counter()

        try:
            info = WebDriverWait(
                self.driver,
                wait_timeout,
                poll_frequency=poll,
            ).until(lambda drv: self._locate_error_marker(drv, markers))
        except TimeoutException:
            return None
        except Exception as exc:
            print(f"   ⚠ Error during error-page detection ({phase}): {self._short_exception(exc)}")
            return None

        if not info:
            return None

        info['phase'] = phase
        info['elapsed'] = round(time.perf_counter() - start, 3)
        return info

    def download_attachments_for_po(self, po_number: str) -> dict:
        """
        Main workflow to find and download all attachments for a specific PO.
        Returns a dict with success, message, supplier_name, counts, url, and names.
        """
        # Remove "PO" or "PM" prefix (case-insensitive) to get the correct order number
        up = (po_number or "").upper()
        order_number = po_number[2:] if up.startswith(("PO", "PM")) else po_number
        url = f"{Config.BASE_URL}/order_headers/{order_number}"
        print(f"\nProcessing PO #{po_number}")
        print(f"   Navigating to: {url}")
        self.driver.get(url)

        early_error = self._detect_error_page('early')
        error_info = early_error
        if not error_info:
            self._wait_for_dom_ready()
            ready_timeout = getattr(Config, 'ERROR_PAGE_READY_CHECK_TIMEOUT', 1.0)
            error_info = self._detect_error_page('post_ready', timeout=ready_timeout)

        if error_info:
            marker_raw = (error_info.get('marker') or 'Coupa error page').strip()
            marker_text = self._truncate_text(marker_raw, 150)
            msg = self._truncate_text(f"Coupa displayed an error page: {marker_text}")
            print(
                "   ❌ "
                f"{msg} (phase={error_info.get('phase')}, source={error_info.get('source')}, "
                f"{error_info.get('elapsed', 0)}s)"
            )
            return {
                'success': False,
                'status_code': 'PO_NOT_FOUND',
                'status_reason': 'COUPA_ERROR_PAGE',
                'message': msg,
                'supplier_name': '',
                'attachments_found': 0,
                'attachments_downloaded': 0,
                'coupa_url': url,
                'attachment_names': [],
                'errors': [{'filename': '', 'reason': marker_text}],
                'error_info': error_info,
                'fallback_attempted': False,
                'fallback_used': False,
                'fallback_details': {},
                'source_page': 'PO',
                'initial_url': url,
            }

        initial_url = url
        attachments = self._find_attachments()
        supplier = self._extract_supplier_name()
        fallback_attempted = False
        fallback_used = False
        fallback_details: Dict[str, Optional[str]] = {}
        fallback_trigger_reason = ''
        fallback_enabled = getattr(Config, 'PR_FALLBACK_ENABLED', True)

        attachments_missing = len(attachments) == 0 if attachments is not None else True
        no_pdf_on_po = False
        if not attachments_missing:
            no_pdf_on_po = not self._attachments_include_pdf(attachments)

        if attachments_missing or no_pdf_on_po:
            fallback_trigger_reason = 'po_without_attachments' if attachments_missing else 'po_without_pdf'

            if attachments_missing and not fallback_enabled:
                msg = "No attachments found on PO page (fallback disabled)."
                print(f"   📭 {msg}")
                return {
                    'success': True,
                    'status_code': 'NO_ATTACHMENTS',
                    'status_reason': 'FALLBACK_DISABLED',
                    'message': msg,
                    'supplier_name': supplier or '',
                    'attachments_found': 0,
                    'attachments_downloaded': 0,
                    'coupa_url': url,
                    'attachment_names': [],
                    'errors': [],
                    'fallback_attempted': False,
                    'fallback_used': False,
                    'fallback_details': {'status': 'disabled', 'trigger_reason': fallback_trigger_reason},
                    'fallback_trigger_reason': fallback_trigger_reason,
                    'source_page': 'PO',
                    'initial_url': initial_url,
                }

            if attachments_missing:
                print("   📭 No attachments found on PO page. Evaluating PR fallback...")
            elif no_pdf_on_po and fallback_enabled:
                print("   📄 No PDF attachments found on PO page. Triggering PR fallback...")
            elif no_pdf_on_po and not fallback_enabled:
                print("   📄 No PDF attachments found on PO page. PR fallback disabled; continuing with available attachments.")
                fallback_trigger_reason = ''

            if fallback_enabled and (attachments_missing or no_pdf_on_po):
                fallback_attempted = True
                fallback_details = self._navigate_to_pr_from_po(order_number) or {}
                if isinstance(fallback_details, dict):
                    fallback_details.setdefault('trigger_reason', fallback_trigger_reason)

                status = fallback_details.get('status') if isinstance(fallback_details, dict) else None
                fallback_url = fallback_details.get('url') if isinstance(fallback_details, dict) else ''
                if status != 'navigated' or not fallback_url:
                    prefix = "No attachments found on PO page" if attachments_missing else "No PDF attachments found on PO page"
                    if status == 'timeout':
                        msg = f"{prefix}; PR link search timed out."
                    elif status == 'navigation_error':
                        msg = f"{prefix}; navigation to PR failed."
                    elif status == 'error':
                        msg = f"{prefix}; PR lookup failed."
                    elif status == 'missing_href':
                        msg = f"{prefix}; PR link missing href attribute."
                    else:
                        msg = f"{prefix}; PR link unavailable."
                    print(f"   📭 {msg}")
                    return {
                        'success': True,
                        'status_code': 'NO_ATTACHMENTS',
                        'status_reason': 'PR_LINK_NOT_FOUND',
                        'message': msg,
                        'supplier_name': supplier or '',
                        'attachments_found': 0,
                        'attachments_downloaded': 0,
                        'coupa_url': url,
                        'attachment_names': [],
                        'errors': [],
                        'fallback_attempted': True,
                        'fallback_used': False,
                        'fallback_details': fallback_details or {'trigger_reason': fallback_trigger_reason},
                        'fallback_trigger_reason': fallback_trigger_reason,
                        'source_page': 'PO',
                        'initial_url': initial_url,
                    }

                fallback_used = True
                url = fallback_url

                pr_error_info = self._detect_error_page('pr_fallback_early')
                if not pr_error_info:
                    ready_timeout = getattr(Config, 'ERROR_PAGE_READY_CHECK_TIMEOUT', 1.0)
                    pr_error_info = self._detect_error_page('pr_fallback_post_ready', timeout=ready_timeout)

                if pr_error_info:
                    marker_raw = (pr_error_info.get('marker') or 'Coupa error page').strip()
                    marker_text = self._truncate_text(marker_raw, 150)
                    msg = self._truncate_text(f"PR fallback landed on an error page: {marker_text}")
                    print(
                        "   ❌ "
                        f"{msg} (phase={pr_error_info.get('phase')}, source={pr_error_info.get('source')}, "
                        f"{pr_error_info.get('elapsed', 0)}s)"
                    )
                    return {
                        'success': False,
                        'status_code': 'PR_NOT_ACCESSIBLE',
                        'status_reason': 'PR_FALLBACK_ERROR_PAGE',
                        'message': msg,
                        'supplier_name': '',
                        'attachments_found': 0,
                        'attachments_downloaded': 0,
                        'coupa_url': url,
                        'attachment_names': [],
                        'errors': [{'filename': '', 'reason': marker_text}],
                        'error_info': pr_error_info,
                        'fallback_attempted': True,
                        'fallback_used': True,
                        'fallback_details': fallback_details or {'trigger_reason': fallback_trigger_reason},
                        'fallback_trigger_reason': fallback_trigger_reason,
                        'source_page': 'PR',
                        'initial_url': initial_url,
                    }

                supplier = self._extract_supplier_name() or supplier
                attachments = self._find_attachments()
                if not attachments:
                    msg = "No attachments found on PR page after fallback."
                    if fallback_trigger_reason == 'po_without_pdf':
                        msg = "No PDF attachments available on PO page and PR page returned no attachments."
                    print(f"   📭 {msg}")
                    return {
                        'success': True,
                        'status_code': 'NO_ATTACHMENTS',
                        'status_reason': 'PO_AND_PR_WITHOUT_ATTACHMENTS',
                        'message': msg,
                        'supplier_name': supplier or '',
                        'attachments_found': 0,
                        'attachments_downloaded': 0,
                        'coupa_url': url,
                        'attachment_names': [],
                        'errors': [],
                        'fallback_attempted': True,
                        'fallback_used': True,
                        'fallback_details': fallback_details or {'trigger_reason': fallback_trigger_reason},
                        'fallback_trigger_reason': fallback_trigger_reason,
                        'source_page': 'PR',
                        'initial_url': initial_url,
                    }


        total_attachments = len(attachments or [])
        print(f"   Processing {total_attachments} attachments...")
        downloaded_count = 0
        names_list: List[str] = []
        download_errors: List[dict] = []

        for i, attachment in enumerate(attachments):
            filename = self._extract_filename_from_element(attachment)
            if not filename:
                placeholder = f"attachment_{i + 1}"
                print(f"      ⚠ Could not determine filename for attachment {i+1}, skipping.")
                download_errors.append({
                    'filename': placeholder,
                    'reason': 'filename not available',
                })
                continue
            names_list.append(filename)

            success, error_reason = self._download_attachment(attachment, filename)
            if success:
                downloaded_count += 1
            else:
                download_errors.append({
                    'filename': filename,
                    'reason': self._truncate_text(error_reason or 'unknown error', 160),
                })

        origin_label = 'PR fallback' if fallback_used else 'PO page'
        if downloaded_count == total_attachments:
            base_msg = f"Downloaded {downloaded_count} attachment(s) from {origin_label}."
            msg = self._truncate_text(base_msg)
            print(f"   ✅ {msg}")
            status_code = 'COMPLETED'
            status_reason = 'PR_FALLBACK_COMPLETED' if fallback_used else 'ALL_ATTACHMENTS_DOWNLOADED'
        elif downloaded_count > 0:
            summary = self._summarize_download_errors(download_errors)
            base_msg = (
                f"Partial download from {origin_label}: {downloaded_count} of {total_attachments} attachment(s)."
            )
            if summary:
                base_msg += f" Issues: {summary}"
            msg = self._truncate_text(base_msg)
            print(f"   ⚠ {msg}")
            status_code = 'PARTIAL'
            status_reason = 'PR_FALLBACK_PARTIAL' if fallback_used else 'PARTIAL_DOWNLOAD'
        else:
            summary = self._summarize_download_errors(download_errors)
            base_msg = f"Failed to download {total_attachments} attachment(s) from {origin_label}."
            if summary:
                base_msg += f" Issues: {summary}"
            msg = self._truncate_text(base_msg)
            print(f"   ❌ {msg}")
            status_code = 'FAILED'
            status_reason = 'PR_FALLBACK_FAILED' if fallback_used else 'DOWNLOADS_FAILED'

        return {
            'success': downloaded_count == total_attachments,
            'status_code': status_code,
            'status_reason': status_reason,
            'message': msg,
            'supplier_name': supplier or '',
            'attachments_found': total_attachments,
            'attachments_downloaded': downloaded_count,
            'coupa_url': url,
            'attachment_names': names_list,
            'errors': download_errors,
            'fallback_attempted': fallback_attempted,
            'fallback_used': fallback_used,
            'fallback_details': fallback_details or {},
            'fallback_trigger_reason': (
                (fallback_details or {}).get('trigger_reason')
                or fallback_trigger_reason
            ),
            'source_page': 'PR' if fallback_used else 'PO',
            'initial_url': initial_url,
        }
