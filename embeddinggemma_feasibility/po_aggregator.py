from __future__ import annotations

from typing import List, Dict, Any

from .filename_signals import parse_filename_metadata


def _score_value(field: str, value: str) -> float:
    if not value or not str(value).strip():
        return 0.0
    v = str(value).strip()
    # Field-specific heuristics
    if field in {"contract_start_date", "contract_end_date"}:
        # prefer strings with digits and separators
        return 2.0 if any(c.isdigit() for c in v) else 0.5
    if field in {"sow_value_eur", "sow_value_lc", "fx", "minimum_commitment_value"}:
        return 2.0 if any(c.isdigit() for c in v) else 0.5
    if field in {"pwo_number"}:
        return 3.0 if any(c.isdigit() for c in v) else 0.0
    if field in {"managed_by", "contract_type", "platform_technology"}:
        return 1.5
    return 1.0


def aggregate_extractions_by_po(extractions: List[Any], use_filename_clues: bool = True) -> List[Any]:
    """Aggregate per PWO across multiple document-level extractions.

    - Groups rows by `pwo_number` when present.
    - Optionally uses filename signals to fill missing values.
    - Picks best value per field by simple scoring heuristics.
    Returns a list of CoupaFieldExtraction-like objects (one per PWO or per file when PWO missing).
    """
    if not extractions:
        return []

    # Build key → list of entries
    buckets: Dict[str, List[Any]] = {}
    unkeyed: List[Any] = []
    for ex in extractions:
        pwo = getattr(ex, "pwo_number", None) or ""
        if pwo and str(pwo).strip():
            buckets.setdefault(str(pwo).strip(), []).append(ex)
        else:
            unkeyed.append(ex)

    aggregated: List[Any] = []

    # Helper: choose best value per field
    def choose_best(field: str, values: List[str]) -> str:
        best_v = ""
        best_s = -1.0
        for v in values:
            s = _score_value(field, v)
            if s > best_s:
                best_v, best_s = v, s
        return best_v

    # Aggregate keyed
    for pwo, items in buckets.items():
        # Create a shallow clone based on first item
        base = items[0]
        fields = [
            "remarks", "supporting_information", "procurement_negotiation_strategy",
            "opportunity_available", "inflation_percent", "minimum_commitment_value",
            "contractual_commercial_model", "user_based_license", "type_of_contract_l2",
            "type_of_contract_l1", "sow_value_eur", "fx", "sow_currency",
            "sow_value_lc", "managed_by", "contract_end_date", "contract_start_date",
            "contract_type", "contract_name", "high_level_scope", "platform_technology", "pwo_number",
        ]
        merged: Dict[str, Any] = {f: getattr(base, f, "") for f in fields}

        # Merge best evidence
        for f in fields:
            vals = [getattr(x, f, "") for x in items if getattr(x, f, "").strip()]
            if vals:
                merged[f] = choose_best(f, [str(v) for v in vals])
        merged["pwo_number"] = pwo

        # Filename clues if enabled and missing
        if use_filename_clues:
            for x in items:
                hints = parse_filename_metadata(getattr(x, "source_file", ""))
                if not merged.get("pwo_number") and hints.get("pwo_number"):
                    merged["pwo_number"] = hints["pwo_number"]
                if not merged.get("contract_name") and hints.get("project_name_hint"):
                    merged["contract_name"] = hints["project_name_hint"]

        # Build a new object of same class
        obj = type(base)(
            source_file=f"PWO_{pwo}",
            extraction_method="aggregated_by_po",
            extraction_confidence=getattr(base, "extraction_confidence", 0.0),
            nlp_libraries_used=getattr(base, "nlp_libraries_used", []) or [],
            **{k: merged.get(k, "") for k in fields}
        )
        aggregated.append(obj)

    # Items without PWO remain as-is
    aggregated.extend(unkeyed)
    return aggregated

