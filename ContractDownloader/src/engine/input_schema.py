"""Column schema helpers shared by the GUI and the canonical CLI pipeline.

These functions are pure and deterministic: they normalize column names,
detect the required PO/Supplier columns from a list of headers, and resolve
an explicit user mapping on top of auto-detection.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

# Aliases accepted for the two mandatory fields, in detection priority order.
PO_KEYS = ("ponumber", "po", "pedido", "purchaseordernumber", "ordernumber")
SUPPLIER_KEYS = ("supplier", "fornecedor", "legalentity", "companycode", "empresa", "vendor")

REQUIRED_FIELDS = ("po", "supplier")


def normalize_column_name(column: Any) -> str:
    """Normalize a header for alias comparison: lowercase, alnum only."""
    return re.sub(r"[^a-z0-9]+", "", str(column or "").lower().strip())


def detect_required_columns(columns: List[Any]) -> Dict[str, Optional[str]]:
    """Return {'po': ..., 'supplier': ...} with detected header names.

    Auto-detection uses the alias lists above. A header is matched by its
    normalized name; the original display name is returned.
    """
    normalized = {normalize_column_name(column): str(column) for column in columns}
    detected: Dict[str, Optional[str]] = {"po": None, "supplier": None}
    for key in PO_KEYS:
        if key in normalized:
            detected["po"] = normalized[key]
            break
    for key in SUPPLIER_KEYS:
        if key in normalized:
            detected["supplier"] = normalized[key]
            break
    return detected


def resolve_mapping(
    columns: List[Any],
    mapping: Optional[Dict[str, Any]] = None,
) -> Dict[str, Optional[str]]:
    """Resolve an explicit mapping on top of auto-detection.

    ``mapping`` may contain 'po' and/or 'supplier' keys whose values are
    header names present in ``columns``. Auto-detection fills whatever the
    mapping does not provide; an explicit mapping wins over detection when
    both are available.
    """
    detected = detect_required_columns(columns)
    resolved = dict(detected)
    if not mapping:
        return resolved

    available = {normalize_column_name(column): str(column) for column in columns}
    for field in REQUIRED_FIELDS:
        value = mapping.get(field)
        if not value:
            continue
        key = normalize_column_name(value)
        if key in available:
            resolved[field] = available[key]
        elif str(value) in {str(c) for c in columns}:
            resolved[field] = str(value)
    return resolved


def parse_mapping_env(environ: Optional[Dict[str, str]] = None) -> Optional[Dict[str, str]]:
    """Read COUPA_COLUMN_MAPPING from the environment (used by the CLI worker)."""
    env = environ if environ is not None else os.environ
    raw = env.get("COUPA_COLUMN_MAPPING")
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(parsed, dict):
        return None
    mapping = {}
    for field in REQUIRED_FIELDS:
        value = parsed.get(field)
        if isinstance(value, str) and value.strip():
            mapping[field] = value.strip()
    return mapping or None


def columns_of_dataframe(frame) -> List[Any]:
    """Return the display names of a pandas DataFrame's columns."""
    return [str(column) for column in frame.columns]
