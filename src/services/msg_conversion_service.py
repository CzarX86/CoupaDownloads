"""
Service for converting Outlook .msg files to PDF.

Designed to run after the download pipeline finishes. Uses lightweight,
pure-Python dependencies (`extract-msg`, `fpdf2`) to parse the e-mail and
render a simple, readable PDF that preserves headers and body text.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Any, List, Optional

from ..core.protocols import TelemetryEmitter
from ..core.status import StatusLevel

logger = logging.getLogger(__name__)


@dataclass
class ConversionResult:
    """Outcome of a single .msg conversion."""

    source: Path
    target: Path
    status: str
    error: Optional[str] = None


def find_msg_files(download_root: Path) -> List[Path]:
    """Recursively find .msg files under the given root."""
    if not download_root or not download_root.exists():
        return []
    return [p for p in download_root.rglob("*.msg") if p.is_file()]


def _strip_html(html: str) -> str:
    """Lightweight HTML → text fallback to avoid extra dependencies."""
    if not html:
        return ""
    text = unescape(html)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _coerce_latin1(text: str) -> str:
    """Ensure text is compatible with core PDF fonts (latin-1)."""
    try:
        return text.encode("latin-1", errors="replace").decode("latin-1")
    except Exception:
        return text


def _to_text(value: Any) -> str:
    """Best-effort conversion from MSG fields to plain text."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except Exception:
            return value.decode("latin-1", errors="replace")
    if isinstance(value, str):
        return value
    return str(value)


def _clean_for_pdf(value: Any) -> str:
    """
    Normalize text for PDF generation.

    fpdf2 may fail when width calculations hit control chars; we strip ASCII
    controls while preserving common whitespace.
    """
    text = _to_text(value)
    # Keep tab/newline/carriage return; replace remaining control chars.
    text = "".join(ch if ch in ("\t", "\n", "\r") or ord(ch) >= 32 else " " for ch in text)
    return _coerce_latin1(text)


def _write_full_width_text(pdf: Any, text: str, h: int = 8) -> None:
    """
    Write text in a full-width multiline block and reset cursor safely.

    fpdf2 defaults can keep x-position on the right edge after `multi_cell`,
    which causes follow-up `w=0` writes to fail with width=0.
    """
    pdf.set_x(pdf.l_margin)
    try:
        pdf.multi_cell(0, h, text, new_x="LMARGIN", new_y="NEXT")
    except TypeError:
        # Compatibility fallback for older signatures.
        pdf.multi_cell(0, h, text)
        pdf.set_x(pdf.l_margin)


class MsgToPdfConverter:
    """Convert Outlook .msg files to simple PDF documents."""

    def __init__(self, overwrite: bool = False, telemetry: Optional[TelemetryEmitter] = None):
        self.overwrite = overwrite
        self.telemetry = telemetry

    def convert(self, msg_path: Path) -> ConversionResult:
        """Convert a single .msg file to PDF."""
        target = msg_path.with_suffix(".pdf")

        if target.exists() and not self.overwrite:
            return ConversionResult(source=msg_path, target=target, status="skipped", error="pdf_exists")

        try:
            import extract_msg  # type: ignore
        except Exception as exc:  # pragma: no cover - defensive guard
            return ConversionResult(source=msg_path, target=target, status="failed", error=f"extract-msg missing: {exc}")

        try:
            from fpdf import FPDF  # type: ignore
        except Exception as exc:  # pragma: no cover - defensive guard
            return ConversionResult(source=msg_path, target=target, status="failed", error=f"fpdf2 missing: {exc}")

        try:
            message = extract_msg.Message(str(msg_path))
            subject = _to_text(getattr(message, "subject", "") or "")
            sender = _to_text(getattr(message, "sender", "") or getattr(message, "sender_email", ""))
            to_list = getattr(message, "to", []) or []
            cc_list = getattr(message, "cc", []) or []
            to = ", ".join(_to_text(v) for v in to_list) if isinstance(to_list, (list, tuple)) else _to_text(to_list)
            cc = ", ".join(_to_text(v) for v in cc_list) if isinstance(cc_list, (list, tuple)) else _to_text(cc_list)
            date = _to_text(getattr(message, "date", "") or "")
            body = _to_text(getattr(message, "body", "") or "")
            if not body and hasattr(message, "htmlBody"):
                body = _strip_html(_to_text(getattr(message, "htmlBody") or ""))

            attachments: List[str] = []
            try:
                for att in getattr(message, "attachments", []) or []:
                    name = getattr(att, "longFilename", "") or getattr(att, "shortFilename", "") or getattr(att, "filename", "")
                    if name:
                        attachments.append(_to_text(name))
            except Exception:
                # Attachment listing is best-effort; continue on failure.
                pass
        except Exception as exc:
            return ConversionResult(source=msg_path, target=target, status="failed", error=str(exc))

        try:
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()

            pdf.set_font("Helvetica", "B", 14)
            pdf.cell(0, 10, "Message Summary", ln=1)

            pdf.set_font("Helvetica", "", 11)
            _write_full_width_text(pdf, _clean_for_pdf(f"From: {sender or ''}"), h=8)
            _write_full_width_text(pdf, _clean_for_pdf(f"To: {to or ''}"), h=8)

            if cc:
                _write_full_width_text(pdf, _clean_for_pdf(f"Cc: {cc}"), h=8)

            if date:
                _write_full_width_text(pdf, _clean_for_pdf(f"Date: {date}"), h=8)
            _write_full_width_text(pdf, _clean_for_pdf(f"Subject: {subject or ''}"), h=8)

            if attachments:
                pdf.set_font("Helvetica", "B", 11)
                pdf.cell(0, 8, "Attachments:", ln=1)
                pdf.set_font("Helvetica", "", 11)
                for att in attachments:
                    _write_full_width_text(pdf, _clean_for_pdf(f"- {att}"), h=6)

            # Body
            if body:
                pdf.ln(4)
                pdf.set_font("Helvetica", "B", 12)
                pdf.cell(0, 8, "Body", ln=1)
                pdf.set_font("Helvetica", "", 11)
                _write_full_width_text(pdf, _clean_for_pdf(body), h=6)

            target.parent.mkdir(parents=True, exist_ok=True)
            pdf.output(str(target))
        except Exception as exc:
            return ConversionResult(source=msg_path, target=target, status="failed", error=str(exc))

        return ConversionResult(source=msg_path, target=target, status="converted")

    def convert_all(self, msg_files: List[Path]) -> dict:
        """Convert a list of .msg files, returning an aggregated summary."""
        summary = {
            "total": len(msg_files),
            "converted": 0,
            "skipped": 0,
            "failed": 0,
            "errors": [],
        }

        for msg_path in msg_files:
            result = self.convert(msg_path)
            status = result.status
            if status == "converted":
                summary["converted"] += 1
                if self.telemetry:
                    self.telemetry.emit_status(StatusLevel.SUCCESS, f"Converted {msg_path.name} to PDF")
            elif status == "skipped":
                summary["skipped"] += 1
            else:
                summary["failed"] += 1
                if result.error:
                    summary["errors"].append({"file": str(msg_path), "error": result.error})
                    logger.warning("MSG to PDF conversion failed", extra={"file": str(msg_path), "error": result.error})
                if self.telemetry:
                    self.telemetry.emit_status(StatusLevel.WARNING, f"Failed to convert {msg_path.name}: {result.error}")

        return summary
