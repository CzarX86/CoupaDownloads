import os
import re
from typing import Optional, List, Dict

import httpx
from bs4 import BeautifulSoup

HTML_PARSER = "html.parser"


class CoupaParser:
    @staticmethod
    def _normalize_attachment_label(label: str) -> str:
        text = (label or "").strip()
        if not text:
            return ""

        # Some Coupa screens render concatenated labels joined by long separators.
        if "====" in text:
            text = text.split("====", 1)[0].strip(" -_=|")

        # Collapse excessive whitespace/newlines from rich UI elements.
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def _is_probable_filename(text: str) -> bool:
        candidate = CoupaParser._normalize_attachment_label(text)
        if not candidate:
            return False

        # Treat only labels that look like real filenames as valid names.
        return re.search(r"\.[A-Za-z0-9]{2,8}$", candidate) is not None

    @staticmethod
    def _filename_from_url(url: str) -> str:
        if not url:
            return ""

        parsed = httpx.URL(url)
        for key in ("filename", "file", "name"):
            value = parsed.params.get(key)
            if value and CoupaParser._is_probable_filename(value):
                return CoupaParser._normalize_attachment_label(value)

        return CoupaParser._normalize_attachment_label(os.path.basename(parsed.path))

    @staticmethod
    def _is_probable_download_url(url: str) -> bool:
        if not url:
            return False

        lower = url.strip().lower()
        if lower in {"#", ""} or lower.startswith(("javascript:", "mailto:")):
            return False

        parsed = httpx.URL(url)
        path = parsed.path.lower()

        # Generic attachment show routes often redirect back to the PO/PR page.
        # Prefer explicit file routes (e.g. /attachment/attachment_file/type/...).
        if re.fullmatch(r"/attachments/\d+/?", path):
            return False

        if "/attachments/" in path or "/attachment/" in path:
            return True

        if "/download" in path and not (
            "/order_headers/" in path or "/requisition_headers/" in path or "/purchase_orders/" in path
        ):
            return True

        for key in ("filename", "file", "name"):
            value = parsed.params.get(key)
            if value and CoupaParser._is_probable_filename(value):
                return True

        disposition = (parsed.params.get("disposition") or "").lower()
        if disposition == "attachment":
            return True

        return False

    @staticmethod
    def _looks_like_attachment_label(text: str) -> bool:
        value = (text or "").strip().lower()
        if not value:
            return False
        return "file attachment" in value or CoupaParser._is_probable_filename(value)

    @staticmethod
    def _extract_candidate_url(el) -> str:
        # Search direct and ancestor attributes that commonly hold attachment URLs.
        attr_candidates = ["data-url", "data-href", "href", "data-download-url"]

        current = el
        for _ in range(4):
            if current is None:
                break
            for attr in attr_candidates:
                value = current.get(attr)
                if value:
                    return value

            onclick = current.get("onclick") or ""
            match = re.search(r"['\"](/[^'\"]*(?:attachment|download)[^'\"]*)['\"]", onclick, flags=re.IGNORECASE)
            if match:
                return match.group(1)

            current = getattr(current, "parent", None)

        return ""

    @staticmethod
    def extract_authenticity_token(html_content: str) -> Optional[str]:
        soup = BeautifulSoup(html_content, HTML_PARSER)
        token_input = soup.find("input", {"name": "authenticity_token"})
        if token_input and token_input.has_attr("value"):
            return token_input["value"]
        return None

    @staticmethod
    def extract_attachments(html_content: str, base_url: str = "") -> List[Dict[str, str]]:
        """
        Two-pass HTML parser for Coupa attachment extraction:
        1. data-url attributes in any element (spans, divs, etc.)
        2. href attributes in anchor tags with attachment/download patterns
        """
        soup = BeautifulSoup(html_content, "lxml")
        attachments = []

        # Pass 1: data-url attributes
        for el in soup.find_all(attrs={"data-url": True}):
            data_url = el.get("data-url")
            if not data_url:
                continue
            if CoupaParser._is_probable_download_url(data_url):
                title_el = el.select_one("[title], [aria-label]")
                name = ""
                if title_el:
                    name = title_el.get("title") or title_el.get("aria-label") or ""
                if not name:
                    name = el.get_text(strip=True) or os.path.basename(data_url.split("?")[0])
                attachments.append({"filename": CoupaParser._sanitize_filename(name), "url": data_url})

        # Pass 2: href in anchor tags
        for a in soup.select("a[href], a[download]"):
            href = a.get("href")
            if not href:
                continue
            if not CoupaParser._is_probable_download_url(href) and not a.has_attr("download"):
                continue

            # Prefer explicit metadata before rendered text, which may contain
            # concatenated labels from complex tables.
            download_attr = a.get("download") or ""
            title = _strip_download_prefix(a.get("title") or "")
            aria = a.get("aria-label") or ""
            text_label = a.get_text(" ", strip=True)

            candidates = [download_attr, title, aria, text_label]
            name = ""
            for candidate in candidates:
                normalized = CoupaParser._normalize_attachment_label(candidate)
                if CoupaParser._is_probable_filename(normalized):
                    name = normalized
                    break
            if not name:
                name = CoupaParser._filename_from_url(href)
            if not name:
                continue
            attachments.append({"filename": CoupaParser._sanitize_filename(name), "url": href})

        # Pass 3: non-anchor attachment widgets (e.g., span role=button with file attachment label)
        widget_selector = "[aria-label*='file attachment' i], [title*='file attachment' i], [role='button'][title], [role='button'][aria-label]"
        for el in soup.select(widget_selector):
            label = el.get("title") or el.get("aria-label") or el.get_text(" ", strip=True)
            if not CoupaParser._looks_like_attachment_label(label):
                continue

            candidate_url = CoupaParser._extract_candidate_url(el)
            if not candidate_url or not CoupaParser._is_probable_download_url(candidate_url):
                continue

            normalized = CoupaParser._normalize_attachment_label(_strip_download_prefix(label))
            filename = normalized if CoupaParser._is_probable_filename(normalized) else CoupaParser._filename_from_url(candidate_url)
            if not filename:
                continue
            attachments.append({"filename": CoupaParser._sanitize_filename(filename), "url": candidate_url})

        # Resolve relative URLs
        if base_url:
            for att in attachments:
                if not att["url"].startswith(("http://", "https://")):
                    att["url"] = str(httpx.URL(base_url).join(httpx.URL(att["url"])))

        return CoupaParser.deduplicate_attachments(attachments)

    @staticmethod
    def extract_pr_links(html_content: str) -> List[str]:
        soup = BeautifulSoup(html_content, HTML_PARSER)
        links: List[str] = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if "/requisition_headers/" in href:
                links.append(href)
        # Preserve order while removing duplicates
        return list(dict.fromkeys(links))

    @staticmethod
    def extract_pr_link(html_content: str) -> Optional[str]:
        links = CoupaParser.extract_pr_links(html_content)
        return links[0] if links else None

    @staticmethod
    def deduplicate_attachments(attachments: List[Dict[str, str]]) -> List[Dict[str, str]]:
        unique = []
        seen_urls = set()
        seen_filenames = set()

        for att in attachments:
            url_key = att.get("url", "").strip().lower()
            filename_key = att.get("filename", "").strip().lower()
            if (url_key and url_key in seen_urls) or (filename_key and filename_key in seen_filenames):
                continue
            unique.append(att)
            if url_key:
                seen_urls.add(url_key)
            if filename_key:
                seen_filenames.add(filename_key)
        return unique

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        return re.sub(r'[<>:"/\\|?*\s]+', '_', name).strip('_')


def _strip_download_prefix(title: str) -> str:
    if title.lower().startswith("download "):
        return title[9:].strip()
    return title.strip()
