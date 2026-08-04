"""Column schema helpers shared by the GUI and the canonical CLI pipeline.

These functions are pure and deterministic: they normalize column names,
detect the required PO/Supplier columns from a list of headers, and resolve
an explicit user mapping on top of auto-detection.
"""

from __future__ import annotations

import csv
import json
import os
import re
from statistics import median
from typing import Any, Dict, List, Optional


PLACEHOLDER_PO_VALUES = frozenset({"", "-", "--", "N/A", "NA", "NONE", "NULL", "UNKNOWN", "UNK", "TBD", "TEST"})
PLACEHOLDER_SUPPLIER_VALUES = frozenset({"", "-", "--", "n/a", "na", "none", "null", "unknown", "unk", "tbd", "test"})
SUPPORTED_INPUT_SUFFIXES = frozenset({".csv", ".xlsx", ".xls", ".xlsm"})
CSV_DELIMITERS = ",;\\t|"
PO_PREFIX_PATTERN = re.compile(r"(?i)(?<![A-Za-z0-9])(PO|PM)(?=[A-Za-z0-9]|$)")
PO_CANONICAL_PATTERN = re.compile(r"^(PO|PM)[0-9]+$")


def clean_scalar(value: Any) -> str:
    """Return a stable text representation for scalar input cells."""
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.casefold() in {"nan", "none", "nat", "<na>"} else text


def canonicalize_po_value(value: Any) -> str:
    """Return the strict PO representation used by validation and import."""
    text = clean_scalar(value).upper()
    return "".join(character for character in text if "A" <= character <= "Z" or "0" <= character <= "9")


def normalize_po_value(value: Any) -> str:
    """Canonical PO key used for validation, import and database deduplication."""
    return canonicalize_po_value(value)


def normalize_supplier_value(value: Any) -> str:
    """Canonical supplier key used only for semantic comparisons."""
    return " ".join(clean_scalar(value).split()).casefold()


def is_valid_canonical_po(value: Any) -> bool:
    return bool(PO_CANONICAL_PATTERN.fullmatch(canonicalize_po_value(value)))


def detect_po_parts(value: Any) -> Dict[str, Any]:
    """Detect multiple PO prefixes before destructive character cleanup."""
    raw = clean_scalar(value)
    matches = list(PO_PREFIX_PATTERN.finditer(raw))
    parts: list[Dict[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        segment = raw[match.start():end].strip()
        canonical = canonicalize_po_value(segment)
        parts.append({"raw": segment, "canonical": canonical})

    ambiguous = False
    if len(parts) == 1:
        segment = parts[0]["raw"]
        # A separator followed by a second unprefixed token is not safe to
        # guess: PO123 - 456 may be one malformed PO or two identifiers.
        ambiguous = bool(re.search(r"[A-Za-z0-9]\s+(?:/|[-])\s+[A-Za-z0-9]", segment))
    return {"parts": parts, "multiple": len(parts) > 1, "ambiguous": ambiguous}


def detect_csv_separator(sample: str) -> str:
    """Detect a CSV delimiter with quote-aware Sniffer and consistency fallback."""
    text = sample or ""
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=CSV_DELIMITERS)
        candidate = dialect.delimiter
        rows = list(csv.reader(text.splitlines()[:30], delimiter=candidate))
        widths = [len(row) for row in rows if any(cell.strip() for cell in row)]
        if candidate in CSV_DELIMITERS and widths and max(widths) == min(widths) and widths[0] > 1:
            return candidate
    except (csv.Error, ValueError):
        pass

    best = (1, 0.0, ",")
    for candidate in CSV_DELIMITERS:
        try:
            rows = list(csv.reader(text.splitlines()[:50], delimiter=candidate))
        except csv.Error:
            continue
        widths = [len(row) for row in rows if any(cell.strip() for cell in row)]
        if not widths:
            continue
        consistency = sum(width == max(widths) for width in widths) / len(widths)
        score = (max(widths), consistency, candidate)
        if score[:2] > best[:2]:
            best = score
    return best[2]


def profile_required_columns(frame, columns: List[Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Rank PO/Supplier candidates using headers and sampled cell semantics."""
    profiles: Dict[str, List[Dict[str, Any]]] = {"po": [], "supplier": []}
    for column in columns:
        values = [clean_scalar(value) for value in frame[column].tolist()]
        nonempty = [value for value in values if value]
        sample = list(dict.fromkeys(nonempty))[:5]
        po_valid = sum(is_valid_canonical_po(value) for value in nonempty)
        po_multi = sum(detect_po_parts(value)["multiple"] for value in nonempty)
        po_placeholders = sum(is_placeholder_po(value) for value in nonempty)
        po_ratio = po_valid / len(nonempty) if nonempty else 0.0
        normalized_header = normalize_column_name(column)
        po_header = any(alias in normalized_header for alias in PO_KEYS)
        supplier_header = any(alias in normalized_header for alias in SUPPLIER_KEYS)
        po_score = min(100, round((po_ratio * 65) + (25 if po_header else 0) - (po_multi * 10) - (po_placeholders * 5)))
        supplier_ratio = 1 - (po_valid / len(nonempty) if nonempty else 1.0)
        supplier_score = min(100, round((supplier_ratio * 45) + (35 if supplier_header else 0) + (10 if nonempty else 0)))
        for role, score in (("po", po_score), ("supplier", supplier_score)):
            profiles[role].append({
                "column": str(column),
                "confidence": max(0, score),
                "examples": sample,
                "nonempty": len(nonempty),
                "multiple_po_values": po_multi,
            })
    for role in profiles:
        profiles[role].sort(key=lambda item: (-item["confidence"], item["column"]))
    return profiles


def resolve_data_mapping(frame, columns: List[Any], mapping: Optional[Dict[str, Any]] = None) -> tuple[Dict[str, Optional[str]], Dict[str, List[Dict[str, Any]]]]:
    """Resolve aliases plus high-confidence value-based PO/Supplier candidates."""
    resolved = resolve_mapping(columns, mapping)
    suggestions = profile_required_columns(frame, columns)
    used = {resolved.get("po"), resolved.get("supplier")}
    for role, threshold in (("po", 60), ("supplier", 60)):
        if resolved.get(role):
            continue
        for candidate in suggestions[role]:
            if candidate["confidence"] >= threshold and candidate["column"] not in used:
                resolved[role] = candidate["column"]
                used.add(candidate["column"])
                break
    return resolved, suggestions


def header_comparison_key(column: Any) -> str:
    """Normalize headers and tolerate pandas' duplicate suffixes (``.1``)."""
    raw = str(column or "").strip()
    raw = re.sub(r"\.\d+$", "", raw)
    return normalize_column_name(raw)


def is_placeholder_po(value: Any) -> bool:
    return normalize_po_value(value) in PLACEHOLDER_PO_VALUES


def is_placeholder_supplier(value: Any) -> bool:
    return normalize_supplier_value(value) in PLACEHOLDER_SUPPLIER_VALUES


def is_excel_numeric_coercion(value: Any) -> bool:
    """Detect values commonly produced when Excel coerces PO identifiers."""
    text = clean_scalar(value)
    return bool(re.fullmatch(r"[+-]?\d+\.0+", text) or re.search(r"[eE][+-]?\d+", text))

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
