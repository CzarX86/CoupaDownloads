from __future__ import annotations

from typing import Iterable, List


def split_text(text: str, max_chars: int = 1200, overlap: int = 120) -> List[str]:
    """Simple, token-agnostic splitter by character length with overlap.

    This avoids external tokenizers and keeps the ingestion offline-friendly.
    """
    if not text:
        return []
    max_chars = max(200, int(max_chars))
    overlap = max(0, min(int(overlap), max_chars // 2))

    chunks: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        end = min(i + max_chars, n)
        chunk = text[i:end]
        chunks.append(chunk)
        if end >= n:
            break
        i = end - overlap
    return chunks


def batched(iterable: Iterable[str], size: int) -> Iterable[list[str]]:
    batch: list[str] = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch

