import asyncio
import hashlib
import os
import re
import shutil
import time
from urllib.parse import unquote
from typing import Optional, List, Dict, Any

import httpx

from src.db.session_db import SessionDB
from src.engine.parser import CoupaParser
from src.engine.rate_limiter import RateLimiter


class CoupaCrawler:
    def __init__(
        self,
        db: SessionDB,
        session_id: int,
        base_download_dir: str,
        base_url: str = "https://unilever.coupahost.com",
        cookies: Optional[Dict[str, str]] = None,
        concurrency: int = 11,
        request_delay: float = 0.03,
        timeout: float = 10.0,
        enable_circuit_breaker: Optional[bool] = None,
    ):
        self.db = db
        self.session_id = session_id
        self.base_download_dir = base_download_dir
        self.base_url = base_url.rstrip("/")
        self.concurrency = concurrency
        self.request_delay = request_delay
        self.timeout = timeout
        if enable_circuit_breaker is None:
            disable_env = os.environ.get("COUPA_DISABLE_CIRCUIT_BREAKER", "").strip().lower()
            self.enable_circuit_breaker = disable_env not in {"1", "true", "yes", "on"}
        else:
            self.enable_circuit_breaker = bool(enable_circuit_breaker)
        self.semaphore = asyncio.Semaphore(concurrency)
        self.rate_limiter = RateLimiter(base_delay=request_delay)

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.cookies = cookies or {}

        limits = httpx.Limits(max_keepalive_connections=concurrency, max_connections=concurrency * 2)
        self.client = httpx.AsyncClient(
            http2=True,
            cookies=self.cookies,
            headers=self.headers,
            limits=limits,
            follow_redirects=True,
            timeout=httpx.Timeout(timeout),
        )

    def _po_url(self, po_number: str) -> str:
        order_number = po_number[2:] if po_number.upper().startswith(("PO", "PM")) else po_number
        return f"{self.base_url}/order_headers/{order_number}"

    def _po_url_candidates(self, po_number: str) -> List[str]:
        primary = self._po_url(po_number)
        original = f"{self.base_url}/order_headers/{po_number}"
        if original == primary:
            return [primary]
        # Prefer the original PO/PM identifier first; stripping the prefix can
        # resolve to a different valid page with unrelated content.
        return [original, primary]

    async def _fetch_html(self, url: str, label: str = "") -> str:
        t0 = time.monotonic()
        async with self.semaphore:
            t_sem = time.monotonic()
            await self.rate_limiter.wait()
            t_rl = time.monotonic()
            response = await self.client.get(url)
            t_http = time.monotonic()
            if response.status_code == 429:
                self.rate_limiter.report_429()
                raise RateLimitError(f"Rate limited on {label or url}")
            self.rate_limiter.report_success()
            response.raise_for_status()
            final_url = str(response.url)
            if (
                "sessions/login" in final_url
                or "oauth" in final_url.lower()
                or "openid" in final_url.lower()
                or ("order_headers" not in final_url and "requisition_headers" not in final_url and "attachment" not in final_url.lower())
            ):
                raise AuthError(f"Auth failed on {label or url} — redirected to {final_url[:120]}")
            elapsed_total = (t_http - t0) * 1000
            if elapsed_total > 2000:
                print(f"[TIMING] _fetch_html {label}: total={elapsed_total:.0f}ms sem_wait={(t_sem - t0)*1000:.0f}ms rl_wait={(t_rl - t_sem)*1000:.0f}ms http={(t_http - t_rl)*1000:.0f}ms")
            return response.text

    async def _download_attachment(self, url: str, dest_path: str) -> None:
        t0 = time.monotonic()
        async with self.semaphore:
            t_sem = time.monotonic()
            await self.rate_limiter.wait()
            t_rl = time.monotonic()
            response = await self.client.get(url)
            t_http = time.monotonic()
            if response.status_code == 429:
                self.rate_limiter.report_429()
                raise RateLimitError(f"Rate limited on download {url}")
            self.rate_limiter.report_success()
            response.raise_for_status()

            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            elapsed_total = (t_http - t0) * 1000
            if elapsed_total > 2000:
                print(f"[TIMING] _download: total={elapsed_total:.0f}ms sem_wait={(t_sem - t0)*1000:.0f}ms rl_wait={(t_rl - t_sem)*1000:.0f}ms http={(t_http - t_rl)*1000:.0f}ms")

            final_path = dest_path
            header_name = self._filename_from_content_disposition(response.headers.get("content-disposition", ""))
            if header_name:
                safe_header_name = self._safe_attachment_filename(header_name, url)
                if safe_header_name:
                    final_path = os.path.join(os.path.dirname(dest_path), safe_header_name)

            # Avoid accidental overwrite when two attachments resolve to same final name.
            if os.path.exists(final_path):
                base, ext = os.path.splitext(final_path)
                idx = 2
                while os.path.exists(f"{base}_{idx}{ext}"):
                    idx += 1
                final_path = f"{base}_{idx}{ext}"

            await asyncio.to_thread(self._write_file, final_path, response.content)

    @staticmethod
    def _write_file(path: str, content: bytes) -> None:
        with open(path, "wb") as f:
            f.write(content)

    @staticmethod
    def _safe_attachment_filename(raw_name: str, download_url: str, max_component_len: int = 180) -> str:
        """Return a filesystem-safe filename with bounded length.

        Some Coupa pages render concatenated attachment text, producing names that exceed
        filesystem component limits on macOS (Errno 63). We keep a readable prefix,
        preserve extension when possible, and append a short hash for uniqueness.
        """
        sanitized = re.sub(r'[<>:"/\\|?*\s]+', '_', (raw_name or "")).strip("_")
        if not sanitized:
            sanitized = os.path.basename(download_url.split("?")[0]) or "attachment"
            sanitized = re.sub(r'[<>:"/\\|?*\s]+', '_', sanitized).strip("_") or "attachment"

        base, ext = os.path.splitext(sanitized)
        # Accept only short, simple extensions (.pdf, .xlsx, etc.).
        if not re.fullmatch(r"\.[A-Za-z0-9]{1,8}", ext or ""):
            ext = ""

        if not ext:
            url_base = os.path.basename(download_url.split("?")[0])
            _, url_ext = os.path.splitext(url_base)
            if re.fullmatch(r"\.[A-Za-z0-9]{1,8}", url_ext or ""):
                ext = url_ext

        if len(sanitized) <= max_component_len:
            return sanitized

        digest = hashlib.sha1(sanitized.encode("utf-8")).hexdigest()[:10]
        suffix = f"_{digest}{ext}"
        keep = max(16, max_component_len - len(suffix))
        truncated_base = (base or "attachment")[:keep].rstrip("_")
        return f"{truncated_base}{suffix}"

    @staticmethod
    def _filename_from_content_disposition(content_disposition: str) -> str:
        if not content_disposition:
            return ""

        # RFC 5987 filename*=UTF-8''encoded-name.ext
        match_star = re.search(r"filename\*=([^;]+)", content_disposition, flags=re.IGNORECASE)
        if match_star:
            value = match_star.group(1).strip().strip('"')
            if "''" in value:
                _, value = value.split("''", 1)
            decoded = unquote(value)
            if decoded:
                return decoded

        # Legacy filename="name.ext"
        match_plain = re.search(r"filename=\"?([^\";]+)\"?", content_disposition, flags=re.IGNORECASE)
        if match_plain:
            return match_plain.group(1).strip()

        return ""

    async def process_po(self, po_number: str, company_code: str) -> Dict[str, Any]:
        """Process a single PO: check circuit breaker, fetch HTML, parse, download."""
        if self.enable_circuit_breaker:
            stats = self.db.get_company_stats(self.session_id, company_code)

            # Circuit Breaker: >= 15% progress, >= 3 POs processed, 100% error rate
            if stats["total"] > 0:
                progress_ratio = stats["processed"] / stats["total"]
                if progress_ratio >= 0.15 and stats["errors"] == stats["processed"] and stats["processed"] >= 3:
                    self.db.suspend_company_code(self.session_id, company_code)

        po_record = self.db.get_po(self.session_id, po_number)
        if po_record and po_record["status"] == "SKIPPED_VERIFICATION_REQUIRED":
            return {"po": po_number, "success": False, "error": "SKIPPED_VERIFICATION_REQUIRED"}

        po_dir_parent = company_code
        if po_record and po_record.get("output_subdir"):
            po_dir_parent = po_record["output_subdir"]
        po_dir = os.path.join(self.base_download_dir, po_dir_parent, po_number)
        dir_created = False
        start_time = time.time()

        try:
            html_content = ""
            po_urls = self._po_url_candidates(po_number)
            for index, po_url in enumerate(po_urls):
                try:
                    html_content = await self._fetch_html(po_url, label=f"PO {po_number}")
                    break
                except httpx.HTTPStatusError as exc:
                    is_404 = exc.response is not None and exc.response.status_code == 404
                    is_last_candidate = index == len(po_urls) - 1
                    if not is_404 or is_last_candidate:
                        raise

            po_attachments = CoupaParser.extract_attachments(html_content, base_url=self.base_url)

            all_attachments = list(po_attachments)
            pr_urls = CoupaParser.extract_pr_links(html_content)
            for pr_url in pr_urls:
                try:
                    full_pr_url = str(httpx.URL(self.base_url).join(httpx.URL(pr_url)))
                    pr_html = await self._fetch_html(full_pr_url, label=f"PR for {po_number}")
                    # Pass full PR page URL so relative attachment links resolve correctly
                    pr_attachments = CoupaParser.extract_attachments(pr_html, base_url=full_pr_url)
                    all_attachments.extend(pr_attachments)
                except Exception:
                    # Keep processing PO attachments even when one PR link fails.
                    continue

            attachments = CoupaParser.deduplicate_attachments(all_attachments)

            if not attachments:
                self.db.update_po_status(self.session_id, po_number, "SUCCESS", None, 0, None)
                latency = time.time() - start_time
                return {"po": po_number, "success": True, "attachments": [], "latency": latency}

            os.makedirs(po_dir, exist_ok=True)
            dir_created = True

            for att in attachments:
                fallback_name = self._safe_attachment_filename(att.get("filename", ""), att.get("url", ""))
                dest_path = os.path.join(po_dir, fallback_name)
                await self._download_attachment(att["url"], dest_path)

            self.db.update_po_status(
                self.session_id, po_number, "SUCCESS", po_dir, len(attachments), None
            )
            latency = time.time() - start_time
            return {
                "po": po_number,
                "success": True,
                "attachments": attachments,
                "latency": latency,
            }

        except Exception as e:
            if dir_created and os.path.exists(po_dir):
                shutil.rmtree(po_dir, ignore_errors=True)
            error_msg = str(e)
            self.db.update_po_status(self.session_id, po_number, "ERROR", None, 0, error_msg)
            return {"po": po_number, "success": False, "error": error_msg, "latency": time.time() - start_time}

    async def process_batch(self, pos: List[tuple]) -> List[Dict[str, Any]]:
        """Process multiple POs concurrently. Each item is (po_number, company_code)."""
        tasks = [self.process_po(po, company) for po, company in pos]
        return await asyncio.gather(*tasks)

    async def close(self) -> None:
        await self.client.aclose()


class RateLimitError(Exception):
    pass


class AuthError(Exception):
    pass
