from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from pathlib import Path
import shutil
from typing import Any, Optional


@dataclass
class MsgConversionResult:
    source: Path
    target: Path
    status: str
    error: Optional[str] = None


def find_msg_files(download_root: Path) -> list[Path]:
    if not download_root or not download_root.exists():
        return []
    return [p for p in download_root.rglob("*.msg") if p.is_file()]


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        for encoding in ("utf-8", "utf-8-sig", "cp1252", "cp1254"):
            try:
                return value.decode(encoding)
            except Exception:
                continue
        return value.decode("latin-1", errors="replace")
    if isinstance(value, str):
        return value
    return str(value)


def _strip_html(html: str) -> str:
    if not html:
        return ""
    text = unescape(html)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _clean_for_pdf(value: Any, preserve_unicode: bool = False) -> str:
    text = _to_text(value)
    text = text.replace("\t", "    ")
    text = "".join(ch if ch in ("\n", "\r") or ord(ch) >= 32 else " " for ch in text)
    if preserve_unicode:
        return text
    try:
        return text.encode("latin-1", errors="replace").decode("latin-1")
    except Exception:
        return text


def _find_unicode_font_path() -> Optional[Path]:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists() and path.is_file():
            return path
    return None


def _setup_pdf_font(pdf: Any) -> tuple[str, bool]:
    font_path = _find_unicode_font_path()
    if font_path:
        try:
            pdf.add_font("CoupaUnicode", "", str(font_path))
            return "CoupaUnicode", True
        except Exception:
            pass
    return "Helvetica", False


def _set_font(pdf: Any, family: str, size: int, unicode_font: bool, bold: bool = False) -> None:
    style = "" if unicode_font else ("B" if bold else "")
    pdf.set_font(family, style, size)


def _safe_fs_name(name: str, fallback: str = "attachment") -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1F]+', "_", (name or "")).strip(" ._")
    return cleaned or fallback


def _collect_saved_paths(save_result: Any) -> list[Path]:
    if not isinstance(save_result, tuple) or len(save_result) < 2:
        return []
    payload = save_result[1]
    if isinstance(payload, str):
        return [Path(payload)]
    if isinstance(payload, list):
        return [Path(p) for p in payload if isinstance(p, str)]
    return []


def _is_inline_attachment(att: Any) -> bool:
    """Heuristic to ignore inline resources (logos/signatures) from HTML emails."""
    hidden = bool(getattr(att, "hidden", False))
    cid = _to_text(getattr(att, "cid", "") or getattr(att, "contentId", "")).strip()
    mimetype = _to_text(getattr(att, "mimetype", "")).lower().strip()
    name = _to_text(
        getattr(att, "longFilename", "")
        or getattr(att, "shortFilename", "")
        or getattr(att, "filename", "")
    ).lower()

    image_ext = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
    looks_like_inline_image = mimetype.startswith("image/") or name.endswith(image_ext)
    return hidden and bool(cid) and looks_like_inline_image


def _extract_attachments_to_subfolder(message: Any, msg_path: Path) -> list[Path]:
    attachment_dir = msg_path.parent / f"{msg_path.stem}_attachments"
    if attachment_dir.exists():
        shutil.rmtree(attachment_dir, ignore_errors=True)

    attachments = list(getattr(message, "attachments", []) or [])
    attachments = [att for att in attachments if not _is_inline_attachment(att)]
    if not attachments:
        # Keep folder absent when there are no true attachments.
        if attachment_dir.exists():
            shutil.rmtree(attachment_dir, ignore_errors=True)
        return []

    attachment_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[Path] = []
    for idx, att in enumerate(attachments, start=1):
        raw_name = (
            getattr(att, "longFilename", "")
            or getattr(att, "shortFilename", "")
            or getattr(att, "filename", "")
        )
        safe_name = _safe_fs_name(_to_text(raw_name), fallback=f"attachment_{idx}")

        # Primary path: use attachment's own save implementation.
        try:
            result = att.save(customPath=str(attachment_dir), customFilename=safe_name)
            extracted = _collect_saved_paths(result)
            if extracted:
                saved_paths.extend(extracted)
                continue
        except Exception:
            pass

        # Fallback path: write raw bytes directly when available.
        data = getattr(att, "data", None)
        if isinstance(data, bytes):
            target = attachment_dir / safe_name
            if target.exists():
                stem, suffix = target.stem, target.suffix
                k = 2
                while True:
                    candidate = attachment_dir / f"{stem}_{k}{suffix}"
                    if not candidate.exists():
                        target = candidate
                        break
                    k += 1
            target.write_bytes(data)
            saved_paths.append(target)

    if not saved_paths:
        # Do not leave empty folders when extraction failed or no physical payload exists.
        try:
            attachment_dir.rmdir()
        except Exception:
            pass
    return saved_paths


def _section_title(pdf: Any, family: str, title: str, unicode_font: bool) -> None:
    pdf.ln(2)
    pdf.set_fill_color(240, 245, 252)
    pdf.set_draw_color(210, 220, 236)
    _set_font(pdf, family, 11, unicode_font=unicode_font, bold=True)
    pdf.cell(0, 8, title, ln=1, fill=True, border=1)
    pdf.ln(1)


def _metadata_row(pdf: Any, family: str, label: str, value: str, unicode_font: bool) -> None:
    safe_value = value.strip() or "-"
    label_text = f"{label}:"
    _set_font(pdf, family, 10, unicode_font=unicode_font, bold=True)
    pdf.cell(28, 6, label_text, border=0)
    _set_font(pdf, family, 10, unicode_font=unicode_font)
    _write_multiline(pdf, safe_value, h=6)


def _write_multiline(pdf: Any, text: str, h: int = 7) -> None:
    pdf.set_x(pdf.l_margin)
    try:
        pdf.multi_cell(0, h, text, new_x="LMARGIN", new_y="NEXT")
    except TypeError:
        pdf.multi_cell(0, h, text)
        pdf.set_x(pdf.l_margin)


class MsgToPdfConverter:
    def __init__(self, overwrite: bool = False):
        self.overwrite = overwrite

    def convert(self, msg_path: Path) -> MsgConversionResult:
        target = msg_path.with_suffix(".pdf")
        if target.exists() and not self.overwrite:
            return MsgConversionResult(source=msg_path, target=target, status="skipped", error="pdf_exists")

        try:
            import extract_msg  # type: ignore
            from fpdf import FPDF  # type: ignore
        except Exception as exc:
            return MsgConversionResult(source=msg_path, target=target, status="failed", error=f"dependency missing: {exc}")

        try:
            message = extract_msg.Message(str(msg_path))
            subject = _to_text(getattr(message, "subject", "") or "")
            sender = _to_text(getattr(message, "sender", "") or getattr(message, "sender_email", ""))
            to = _to_text(getattr(message, "to", "") or "")
            cc = _to_text(getattr(message, "cc", "") or "")
            date = _to_text(getattr(message, "date", "") or "")
            body = _to_text(getattr(message, "body", "") or "")
            if not body and hasattr(message, "htmlBody"):
                body = _strip_html(_to_text(getattr(message, "htmlBody") or ""))

            attachment_names: list[str] = []
            for att in getattr(message, "attachments", []) or []:
                if _is_inline_attachment(att):
                    continue
                name = getattr(att, "longFilename", "") or getattr(att, "shortFilename", "") or getattr(att, "filename", "")
                if name:
                    attachment_names.append(_to_text(name))

            extracted_attachment_paths = _extract_attachments_to_subfolder(message, msg_path)
        except Exception as exc:
            return MsgConversionResult(source=msg_path, target=target, status="failed", error=str(exc))

        try:
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            font_family, unicode_font = _setup_pdf_font(pdf)
            pdf.set_draw_color(220, 220, 220)
            pdf.set_text_color(20, 20, 20)

            pdf.set_fill_color(230, 238, 250)
            _set_font(pdf, font_family, 16, unicode_font=unicode_font, bold=True)
            pdf.cell(0, 12, "Message Summary", ln=1, fill=True, border=1)

            _set_font(pdf, font_family, 9, unicode_font=unicode_font)
            generated_from = _clean_for_pdf(str(msg_path.name), preserve_unicode=unicode_font)
            pdf.set_text_color(90, 90, 90)
            pdf.cell(0, 6, f"Source: {generated_from}", ln=1)
            pdf.set_text_color(20, 20, 20)

            _section_title(pdf, font_family, "Metadata", unicode_font)
            _metadata_row(
                pdf,
                font_family,
                "From",
                _clean_for_pdf(sender, preserve_unicode=unicode_font),
                unicode_font,
            )
            _metadata_row(
                pdf,
                font_family,
                "To",
                _clean_for_pdf(to, preserve_unicode=unicode_font),
                unicode_font,
            )

            if cc:
                _metadata_row(
                    pdf,
                    font_family,
                    "Cc",
                    _clean_for_pdf(cc, preserve_unicode=unicode_font),
                    unicode_font,
                )
            if date:
                _metadata_row(
                    pdf,
                    font_family,
                    "Date",
                    _clean_for_pdf(date, preserve_unicode=unicode_font),
                    unicode_font,
                )
            _metadata_row(
                pdf,
                font_family,
                "Subject",
                _clean_for_pdf(subject, preserve_unicode=unicode_font),
                unicode_font,
            )

            if attachment_names:
                _section_title(pdf, font_family, "Attachments", unicode_font)
                _set_font(pdf, font_family, 11, unicode_font=unicode_font)
                for idx, name in enumerate(attachment_names, start=1):
                    display_name = _clean_for_pdf(name, preserve_unicode=unicode_font)
                    _write_multiline(pdf, f"{idx}. {display_name}", h=6)

                if extracted_attachment_paths:
                    pdf.ln(1)
                    _set_font(pdf, font_family, 10, unicode_font=unicode_font, bold=True)
                    pdf.cell(0, 6, "Extracted Files:", ln=1)
                    _set_font(pdf, font_family, 10, unicode_font=unicode_font)
                    for saved in extracted_attachment_paths:
                        _write_multiline(
                            pdf,
                            _clean_for_pdf(f"- {saved.name}", preserve_unicode=unicode_font),
                            h=5,
                        )

            if body:
                _section_title(pdf, font_family, "Body", unicode_font)
                pdf.set_fill_color(250, 250, 250)
                pdf.set_draw_color(225, 225, 225)
                body_text = _clean_for_pdf(body, preserve_unicode=unicode_font)
                _set_font(pdf, font_family, 11, unicode_font=unicode_font)
                pdf.multi_cell(0, 6, body_text, border=1, fill=True)

            target.parent.mkdir(parents=True, exist_ok=True)
            pdf.output(str(target))
        except Exception as exc:
            return MsgConversionResult(source=msg_path, target=target, status="failed", error=str(exc))

        return MsgConversionResult(source=msg_path, target=target, status="converted")

    def convert_all(self, msg_files: list[Path]) -> dict:
        summary = {"total": len(msg_files), "converted": 0, "skipped": 0, "failed": 0, "errors": []}
        for msg_path in msg_files:
            result = self.convert(msg_path)
            if result.status == "converted":
                summary["converted"] += 1
            elif result.status == "skipped":
                summary["skipped"] += 1
            else:
                summary["failed"] += 1
                if result.error:
                    summary["errors"].append({"file": str(msg_path), "error": result.error})
        return summary
