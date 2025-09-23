"""Shared constants for PDF training datasets."""
from __future__ import annotations

from typing import Dict, List

# Mapping between normalized keys (snake_case) and the human-friendly labels
NORMALIZED_TO_PRETTY: Dict[str, str] = {
    "remarks": "Remarks",
    "supporting_information": "Supporting Information",
    "procurement_negotiation_strategy": "Procurement Negotiation Strategy",
    "opportunity_available": "Opportunity Available",
    "inflation_percent": "Inflation %",
    "minimum_commitment_value": "Minimum Commitment Value",
    "contractual_commercial_model": "Contractual Commercial Model",
    "user_based_license": "User Based License",
    "type_of_contract_l2": "Type of Contract - L2",
    "type_of_contract_l1": "Type of Contract - L1",
    "sow_value_eur": "SOW Value in EUR",
    "fx": "FX",
    "sow_currency": "SOW Currency",
    "sow_value_lc": "SOW Value in LC",
    "managed_by": "Managed By",
    "contract_end_date": "Contract End Date",
    "contract_start_date": "Contract Start Date",
    "contract_type": "Contract Type",
    "contract_name": "Contract Name",
    "high_level_scope": "High Level Scope",
    "platform_technology": "Platform/Technology",
    "pwo_number": "PWO#",
}

PRETTY_TO_NORMALIZED: Dict[str, str] = {value: key for key, value in NORMALIZED_TO_PRETTY.items()}

# Metadata columns present in review CSVs/tasks
METADATA_COLUMNS: List[str] = [
    "Source File",
    "Extraction Confidence",
    "Extraction Method",
    "NLP Libraries Used",
]

# Review statuses accepted during annotation
ALLOWED_STATUSES = {"OK", "CORRECTED", "NEW", "MISSING", "REJECTED"}

# Normalized fields that generate contrastive pairs for ST training
CATEGORICAL_ST_FIELDS: List[str] = [
    "contract_type",
    "managed_by",
    "sow_currency",
    "platform_technology",
    "type_of_contract_l1",
    "type_of_contract_l2",
]


def normalized_to_pretty(normalized: str) -> str:
    """Return a human-friendly label for a normalized field name."""

    pretty = NORMALIZED_TO_PRETTY.get(normalized)
    if pretty:
        return pretty
    # Fallback: replace underscores with spaces and title-case
    return normalized.replace("_", " ").title()


def pretty_to_normalized(pretty: str) -> str:
    """Return the normalized key for a pretty label (best-effort)."""

    if pretty in PRETTY_TO_NORMALIZED:
        return PRETTY_TO_NORMALIZED[pretty]
    fallback = pretty.strip().lower().replace("/", "_").replace(" ", "_")
    return fallback
