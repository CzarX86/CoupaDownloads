"""I/O helpers for working with LLM support payloads."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping


def format_index(index: int | tuple[int, ...]) -> str:
    """Return a human readable identifier for a DataFrame index."""

    if isinstance(index, tuple):
        try:
            index = index[0]
        except IndexError:  # pragma: no cover - defensive
            return "1"
    try:
        return str(int(index) + 1)
    except Exception:  # pragma: no cover - defensive
        return str(index)


def row_label(row: Mapping[str, Any], index: int | tuple[int, ...]) -> str:
    """Derive the row identifier used when building prompts."""

    value = row.get("row_id")
    if value is None:
        return format_index(index)
    try:
        text = str(value).strip()
        return format_index(index) if not text else text
    except Exception:  # pragma: no cover - defensive
        return format_index(index)


async def write_support_payload(path: Path, payload: Dict[str, Any]) -> None:
    """Persist the generated payload as JSON on disk."""

    def _writer() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    await asyncio.to_thread(_writer)


def placeholder_payload(document_id: str, *, provider: str, model: str, dry_run: bool, fields: list[str], support_path: Path) -> Dict[str, Any]:
    """Build a payload structure when no review rows are available."""

    return {
        "document_id": document_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "model": model,
        "dry_run": dry_run,
        "fields": fields,
        "rows": [],
        "support_path": str(support_path),
    }
