"""Shared constants for PDF training datasets."""
from __future__ import annotations

from typing import Dict, List

from src.config.feedback_constants import (
    NORMALIZED_TO_PRETTY,
    PRETTY_TO_NORMALIZED,
    METADATA_COLUMNS,
    ALLOWED_STATUSES,
    CATEGORICAL_ST_FIELDS,
)


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
