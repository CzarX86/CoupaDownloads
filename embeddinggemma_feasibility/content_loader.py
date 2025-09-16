from __future__ import annotations

"""
Multi-format content loader for the advanced extractor.

Supports: PDF, DOCX, TXT/MD, HTML, MSG/EML, images (OCR) when libraries are available.
Returns a dict with: { 'text': str, 'metadata': {...} }
"""

from pathlib import Path
from typing import Dict, Any


def _read_text_file(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return p.read_text(errors="replace")


def _read_pdf(p: Path) -> str:
    try:
        import pdfplumber  # type: ignore
        text = []
        with pdfplumber.open(str(p)) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                if t:
                    text.append(t)
        return "\n".join(text)
    except Exception:
        try:
            import PyPDF2  # type: ignore
            reader = PyPDF2.PdfReader(str(p))
            out = []
            for page in reader.pages:
                out.append(page.extract_text() or "")
            return "\n".join(out)
        except Exception:
            return ""


def _read_docx(p: Path) -> str:
    try:
        import docx  # type: ignore
        d = docx.Document(str(p))
        return "\n".join((para.text or "") for para in d.paragraphs)
    except Exception:
        return ""


def _read_html(p: Path) -> str:
    try:
        from bs4 import BeautifulSoup  # type: ignore
        content = _read_text_file(p)
        soup = BeautifulSoup(content, "lxml")
        return soup.get_text(" ", strip=True)
    except Exception:
        return ""


def _read_msg(p: Path) -> str:
    try:
        import extract_msg  # type: ignore
        m = extract_msg.Message(str(p))
        parts = [m.subject or "", m.body or ""]
        return "\n".join(parts)
    except Exception:
        return ""


def _read_eml(p: Path) -> str:
    try:
        from email import policy
        from email.parser import BytesParser
        data = p.read_bytes()
        msg = BytesParser(policy=policy.default).parsebytes(data)
        text = []
        if msg.get_body(preferencelist=('plain',)):
            text.append(msg.get_body(preferencelist=('plain',)).get_content())
        elif msg.get_body(preferencelist=('html',)):
            html = msg.get_body(preferencelist=('html',)).get_content()
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, "lxml")
                text.append(soup.get_text(" ", strip=True))
            except Exception:
                text.append(html)
        return "\n".join(text)
    except Exception:
        return ""


def _read_image_ocr(p: Path) -> str:
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
        img = Image.open(str(p))
        return pytesseract.image_to_string(img)
    except Exception:
        return ""


def load_text_from_path(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    ext = p.suffix.lower()
    text = ""
    if ext in {".pdf"}:
        text = _read_pdf(p)
    elif ext in {".docx"}:
        text = _read_docx(p)
    elif ext in {".txt", ".md", ".markdown"}:
        text = _read_text_file(p)
    elif ext in {".html", ".htm"}:
        text = _read_html(p)
    elif ext in {".msg"}:
        text = _read_msg(p)
    elif ext in {".eml"}:
        text = _read_eml(p)
    elif ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        text = _read_image_ocr(p)
    else:
        # fallback attempt
        try:
            text = _read_text_file(p)
        except Exception:
            text = ""

    md = {
        "source_path": str(p),
        "filename": p.name,
        "size": p.stat().st_size if p.exists() else 0,
        "ext": ext,
    }
    return {"text": text.strip(), "metadata": md}

