"""Pure extraction of report metadata from Coupa PO HTML pages.

The extractor has no network, database, or filesystem responsibilities. This
keeps Coupa markup changes and report persistence independently testable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag


HTML_PARSER = "lxml"
_CURRENCY_RE = re.compile(r"^[A-Za-z]{3}$")
_CRG_RE = re.compile(r"^R?(\d{4})(?:\b|[-\s])", re.IGNORECASE)


@dataclass(frozen=True)
class CoupaLineMetadata:
    line_number: int
    crg_code: Optional[str] = None
    crg_raw: Optional[str] = None
    currency_code: Optional[str] = None


@dataclass(frozen=True)
class CoupaPOMetadata:
    po_number: str
    company_code: Optional[str] = None
    ship_to_user: Optional[str] = None
    payment_term: Optional[str] = None
    source_url: Optional[str] = None
    metadata_status: str = "PARTIAL"
    metadata_error: Optional[str] = None
    lines: tuple[CoupaLineMetadata, ...] = ()


class CoupaMetadataExtractor:
    """Extract the first reportable Coupa metadata slice from PO HTML."""

    @staticmethod
    def _normalise(value: Any) -> str:
        return " ".join(str(value or "").split())

    @classmethod
    def _label_text(cls, label: Tag) -> str:
        return cls._normalise(cls._normalise(label.get_text(" ", strip=True)).replace("*", ""))

    @classmethod
    def _group_value(cls, group: Tag) -> str:
        label = group.select_one(":scope > .group_label")
        parts: list[str] = []
        for child in group.children:
            if isinstance(child, NavigableString):
                text = cls._normalise(child)
                if text:
                    parts.append(text)
                continue
            if not isinstance(child, Tag) or child is label:
                continue
            if child.name == "input" and child.get("type") == "hidden":
                continue
            text = cls._normalise(child.get_text(" ", strip=True))
            if text:
                parts.append(text)
        return cls._normalise(" ".join(parts))

    @classmethod
    def _find_group_value(cls, root: Optional[Tag], field_name: str) -> Optional[str]:
        if root is None:
            return None
        target = cls._normalise(field_name).casefold()
        for group in root.select(".form_element"):
            label = group.select_one(":scope > .group_label")
            if label is None or cls._label_text(label).casefold() != target:
                continue
            return cls._group_value(group) or None
        return None

    @classmethod
    def _extract_currency(cls, row: Tag) -> Optional[str]:
        candidates = [
            element.get("title")
            for element in row.select(".orderLinePrice [title], .orderLineTotal [title]")
        ]
        candidates.extend(element.get_text(" ", strip=True) for element in row.select(".currency"))
        for candidate in candidates:
            value = cls._normalise(candidate).upper()
            if _CURRENCY_RE.fullmatch(value):
                return value
        return None

    @classmethod
    def _extract_line_number(cls, row: Tag, fallback: int) -> int:
        line_number = row.select_one(".line_num")
        value = cls._normalise(line_number.get_text(" ", strip=True)) if line_number else ""
        if not value and line_number:
            value = cls._normalise(line_number.get("aria-label", "")).split()[-1]
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    @classmethod
    def _extract_account_crg(cls, row: Tag) -> tuple[Optional[str], Optional[str]]:
        raw_value: Optional[str] = None
        for item in row.select(".billing_tooltip li"):
            text = cls._normalise(item.get_text(" ", strip=True))
            if text.casefold().startswith("cc funca:"):
                raw_value = text.split(":", 1)[1].strip() or None
                break

        if raw_value is None:
            account = row.select_one(".account-wrapper")
            account_text = cls._normalise(account.get_text(" ", strip=True)) if account else ""
            match = re.search(r"CC FuncA:\s*(.*?)(?=\s+CC FncID:|$)", account_text, re.IGNORECASE)
            raw_value = cls._normalise(match.group(1)) if match else None

        if not raw_value:
            return None, None
        match = _CRG_RE.match(raw_value)
        return (match.group(1) if match else None), raw_value

    @classmethod
    def extract(cls, html_content: str, po_number: str, source_url: str = "") -> CoupaPOMetadata:
        soup = BeautifulSoup(html_content or "", HTML_PARSER)
        top_form = soup.select_one("#topForm") or soup
        shipping = soup.select_one("#shipTo")

        company_code = cls._find_group_value(shipping, "Company Code")
        ship_to_user = cls._find_group_value(top_form, "Ship To User")
        payment_term = cls._find_group_value(top_form, "Payment Term")

        lines: list[CoupaLineMetadata] = []
        seen_line_numbers: set[int] = set()
        for fallback, row in enumerate(soup.select('tr[id^="order_line_row_"]'), start=1):
            line_number = cls._extract_line_number(row, fallback)
            if line_number in seen_line_numbers:
                line_number = fallback
            seen_line_numbers.add(line_number)
            crg_code, crg_raw = cls._extract_account_crg(row)
            lines.append(
                CoupaLineMetadata(
                    line_number=line_number,
                    crg_code=crg_code,
                    crg_raw=crg_raw,
                    currency_code=cls._extract_currency(row),
                )
            )

        has_metadata = any((company_code, ship_to_user, payment_term)) or bool(lines)
        status = "EXTRACTED" if has_metadata else "PARTIAL"
        return CoupaPOMetadata(
            po_number=str(po_number),
            company_code=company_code,
            ship_to_user=ship_to_user,
            payment_term=payment_term,
            source_url=source_url or None,
            metadata_status=status,
            lines=tuple(lines),
        )
