from __future__ import annotations

import re
from typing import Dict


def parse_filename_metadata(filename: str) -> Dict[str, str]:
    """Extract structured hints from a filename.

    Tries to recover PWO number, PO number patterns, project names and dates.
    Returns a dict with optional keys like: pwo_number, po_number, project_name, date.
    """
    base = filename.rsplit("/", 1)[-1]
    name = base.rsplit(".", 1)[0]

    out: Dict[str, str] = {}

    # PWO patterns: PWO123456, PWO_123456, PWO#123456, or bare 6+ digits after 'PWO'
    m = re.search(r"(?:PWO[#_\s-]*)?(\d{6,})", name, flags=re.IGNORECASE)
    if m:
        out["pwo_number"] = m.group(1)

    # PO patterns: PO16799866 etc.
    po = re.search(r"PO\s*[-_#]?\s*(\d{6,})", name, flags=re.IGNORECASE)
    if po:
        out["po_number"] = po.group(1)

    # Date-like tokens: 2025-09-15, 15-09-2025, 15092025, 20250915
    date = re.search(r"(\d{4}[-_/]?\d{2}[-_/]?\d{2}|\d{2}[-_/]?\d{2}[-_/]?\d{4})", name)
    if date:
        out["date_hint"] = date.group(1)

    # Project name heuristic: take alnum words around PWO/PO tokens
    # This is intentionally simple; refined in future iterations.
    tokens = re.split(r"[-_. ]+", name)
    words = [t for t in tokens if t and not re.fullmatch(r"\d+", t) and t.upper() not in {"PO", "PWO", "V", "V2", "V3"}]
    if words:
        out["project_name_hint"] = " ".join(words[:6])

    return out

