from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from .splitters import split_text


SUPPORTED_EXTS = {".txt", ".md", ".pdf"}


def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        # Best-effort: try latin-1
        return path.read_text(encoding="latin-1", errors="ignore")


def _read_pdf(path: Path) -> str:
    try:
        import pdfplumber
    except Exception as e:
        raise RuntimeError(
            "pdfplumber is required to extract text from PDFs. Install it first."
        ) from e

    text_parts: List[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            try:
                txt = page.extract_text() or ""
                text_parts.append(txt)
            except Exception:
                continue
    return "\n".join(text_parts)


def load_documents(source_dir: Path, max_chars: int = 1200, overlap: int = 120) -> Tuple[List[str], List[dict]]:
    """Load and split documents from a directory.

    Returns
    -------
    texts : list[str]
        Chunked texts.
    metadatas : list[dict]
        Metadata dicts with keys: source_path, chunk_idx.
    """
    source_dir = Path(source_dir)
    if not source_dir.exists() or not source_dir.is_dir():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    texts: List[str] = []
    metadatas: List[dict] = []

    for p in sorted(source_dir.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix.lower() not in SUPPORTED_EXTS:
            continue

        if p.suffix.lower() == ".pdf":
            raw = _read_pdf(p)
        else:
            raw = _read_text_file(p)

        chunks = split_text(raw, max_chars=max_chars, overlap=overlap)
        for i, ch in enumerate(chunks):
            texts.append(ch)
            metadatas.append({"source_path": str(p), "chunk_idx": i})

    if not texts:
        raise RuntimeError(f"No supported documents found in {source_dir}")

    return texts, metadatas

