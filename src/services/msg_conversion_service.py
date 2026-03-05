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
from typing import List, Optional

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
            subject = getattr(message, "subject", "") or ""
            sender = getattr(message, "sender", "") or getattr(message, "sender_email", "")
            to_list = getattr(message, "to", []) or []
            cc_list = getattr(message, "cc", []) or []
            to = ", ".join(to_list) if isinstance(to_list, list) else str(to_list)
            cc = ", ".join(cc_list) if isinstance(cc_list, list) else str(cc_list)
            date = getattr(message, "date", "") or ""
            body = getattr(message, "body", "") or ""
            if not body and hasattr(message, "htmlBody"):
                body = _strip_html(getattr(message, "htmlBody") or "")

            attachments: List[str] = []
            try:
                for att in getattr(message, "attachments", []) or []:
                    name = getattr(att, "longFilename", "") or getattr(att, "shortFilename", "") or getattr(att, "filename", "")
                    if name:
                        attachments.append(str(name))
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
            pdf.cell(0, 10, _coerce_latin1("Message Summary"), ln=1)

            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(30, 8, _coerce_latin1("From:"), ln=0)
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 8, _coerce_latin1(sender or ""))

            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(30, 8, _coerce_latin1("To:"), ln=0)
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 8, _coerce_latin1(to or ""))

            if cc:
                pdf.set_font("Helvetica", "B", 11)
                pdf.cell(30, 8, _coerce_latin1("Cc:"), ln=0)
                pdf.set_font("Helvetica", "", 11)
                pdf.multi_cell(0, 8, _coerce_latin1(cc))

            if date:
                pdf.set_font("Helvetica", "B", 11)
                pdf.cell(30, 8, _coerce_latin1("Date:"), ln=0)
                pdf.set_font("Helvetica", "", 11)
                pdf.multi_cell(0, 8, _coerce_latin1(str(date)))

            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(30, 8, _coerce_latin1("Subject:"), ln=0)
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 8, _coerce_latin1(subject or ""))

            if attachments:
                pdf.set_font("Helvetica", "B", 11)
                pdf.cell(0, 8, _coerce_latin1("Attachments:"), ln=1)
                pdf.set_font("Helvetica", "", 11)
                for att in attachments:
                    pdf.multi_cell(0, 6, f"- {_coerce_latin1(att)}")

            # Body
            if body:
                pdf.ln(4)
                pdf.set_font("Helvetica", "B", 12)
                pdf.cell(0, 8, _coerce_latin1("Body"), ln=1)
                pdf.set_font("Helvetica", "", 11)
                pdf.multi_cell(0, 6, _coerce_latin1(body))

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
