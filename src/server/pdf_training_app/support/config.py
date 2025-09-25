"""Configuration helpers for LLM support orchestration."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, List, Optional

try:
    from tools import llm_critique
except ImportError as exc:  # pragma: no cover - tooling requirement
    raise RuntimeError(
        "LLM helpers require the optional tooling dependencies. Install the project with tooling extras."
    ) from exc


@dataclass
class LLMConfig:
    """Resolved configuration for invoking the LLM helper."""

    provider: str
    model: str
    temperature: float
    top_p: float
    timeout: float
    fields: List[str]
    dry_run: bool
    api_key: Optional[str]


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def parse_fields(fields: Optional[Iterable[str]]) -> List[str]:
    """Resolve the list of fields to critique."""

    if fields is None:
        if raw := os.getenv("PDF_TRAINING_LLM_FIELDS"):
            fields = [item.strip() for item in raw.split(",") if item.strip()]
    return llm_critique._normalise_fields(fields)


def load_config(
    *,
    fields: Optional[Iterable[str]] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    dry_run: Optional[bool] = None,
    api_key: Optional[str] = None,
) -> LLMConfig:
    """Assemble an :class:`LLMConfig` from explicit arguments and environment defaults."""

    resolved_fields = parse_fields(fields)
    resolved_provider = provider or os.getenv("PDF_TRAINING_LLM_PROVIDER", "deepseek")
    resolved_model = model or os.getenv("PDF_TRAINING_LLM_MODEL", "deepseek-chat")
    resolved_temperature = float(os.getenv("PDF_TRAINING_LLM_TEMPERATURE", "0.0"))
    resolved_top_p = float(os.getenv("PDF_TRAINING_LLM_TOP_P", "0.9"))
    resolved_timeout = float(os.getenv("PDF_TRAINING_LLM_TIMEOUT", "30.0"))
    resolved_dry_run = dry_run if dry_run is not None else _env_bool("PDF_TRAINING_LLM_DRY_RUN", True)
    resolved_api_key = api_key or os.getenv("PDF_TRAINING_LLM_API_KEY")

    return LLMConfig(
        provider=resolved_provider,
        model=resolved_model,
        temperature=resolved_temperature,
        top_p=resolved_top_p,
        timeout=resolved_timeout,
        fields=resolved_fields,
        dry_run=resolved_dry_run,
        api_key=resolved_api_key,
    )
