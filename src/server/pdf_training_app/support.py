"""LLM helper integration for the PDF-first annotation workflow."""
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from server.db import repository
from server.db.models import JobType as DbJobType
from server.db.session import async_session
from server.db.storage import annotation_analysis_dir

from .jobs import job_manager
from .models import JobResponse, JobStatus as ApiJobStatus, JobType as ApiJobType

try:
    from tools import llm_critique
except ImportError as exc:  # pragma: no cover - tooling requirement
    raise RuntimeError(
        "LLM helpers require the optional tooling dependencies. Install the project with tooling extras."
    ) from exc


@dataclass
class _LLMConfig:
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


def _parse_fields(fields: Optional[Iterable[str]]) -> List[str]:
    if fields is None:
        raw = os.getenv("PDF_TRAINING_LLM_FIELDS")
        if raw:
            fields = [item.strip() for item in raw.split(",") if item.strip()]
    return llm_critique._normalise_fields(fields)


def _load_config(
    *,
    fields: Optional[Iterable[str]] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    dry_run: Optional[bool] = None,
    api_key: Optional[str] = None,
) -> _LLMConfig:
    resolved_fields = _parse_fields(fields)
    resolved_provider = provider or os.getenv("PDF_TRAINING_LLM_PROVIDER", "deepseek")
    resolved_model = model or os.getenv("PDF_TRAINING_LLM_MODEL", "deepseek-chat")
    resolved_temperature = float(os.getenv("PDF_TRAINING_LLM_TEMPERATURE", "0.0"))
    resolved_top_p = float(os.getenv("PDF_TRAINING_LLM_TOP_P", "0.9"))
    resolved_timeout = float(os.getenv("PDF_TRAINING_LLM_TIMEOUT", "30.0"))
    resolved_dry_run = dry_run if dry_run is not None else _env_bool("PDF_TRAINING_LLM_DRY_RUN", True)
    resolved_api_key = api_key or os.getenv("PDF_TRAINING_LLM_API_KEY")
    return _LLMConfig(
        provider=resolved_provider,
        model=resolved_model,
        temperature=resolved_temperature,
        top_p=resolved_top_p,
        timeout=resolved_timeout,
        fields=resolved_fields,
        dry_run=resolved_dry_run,
        api_key=resolved_api_key,
    )


async def _read_review_dataframe(review_csv: Path) -> pd.DataFrame:
    return await asyncio.to_thread(pd.read_csv, review_csv)


def _row_label(row: pd.Series, index: int | tuple[int, ...]) -> str:
    value = row.get("row_id")
    if value is None:
        return _format_index(index)
    try:
        text = str(value).strip()
        if not text:
            return _format_index(index)
        return text
    except Exception:  # pragma: no cover - defensive
        return _format_index(index)


def _format_index(index: int | tuple[int, ...]) -> str:
    if isinstance(index, tuple):
        try:
            index = index[0]
        except IndexError:  # pragma: no cover - defensive
            return "1"
    try:
        return str(int(index) + 1)
    except Exception:  # pragma: no cover - defensive
        return str(index)


def _run_llm_prompt(prompt: str, config: _LLMConfig) -> Dict[str, Any]:
    if config.dry_run:
        return llm_critique._simulate_response(config.fields)
    key = config.api_key
    if not key:
        try:
            key = llm_critique._resolve_api_key(config.provider, explicit=None)
        except SystemExit as exc:  # pragma: no cover - converted to runtime error
            raise RuntimeError(str(exc)) from exc
    return llm_critique._call_llm(
        config.provider,
        config.model,
        key,
        prompt,
        config.temperature,
        config.top_p,
        config.timeout,
    )


async def _write_support_payload(path: Path, payload: Dict[str, Any]) -> None:
    def _writer() -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    await asyncio.to_thread(_writer)


async def _generate_llm_support(
    document_id: str,
    config: _LLMConfig,
    job_id: str,
) -> Dict[str, Any]:
    async def _record(detail: str, payload: Optional[Dict[str, Any]] = None) -> None:
        async with async_session() as session:
            await repository.update_job_detail(session, job_id, detail=detail, payload=payload)
            await session.commit()

    await _record("Loading document context")
    async with async_session() as session:
        document = await repository.get_document(session, document_id)
        if not document:
            raise ValueError("Document not found")
        if not document.annotations:
            raise ValueError("Annotation record not found for document")
        annotation = document.annotations[0]
        analysis_dir = annotation_analysis_dir(annotation.id)
        review_csv = analysis_dir / "review.csv"
        if not review_csv.exists():
            raise ValueError("Review CSV not found. Run preprocessing first.")

    df = await _read_review_dataframe(review_csv)

    support_path = analysis_dir / "llm_support.json"

    if df.empty:
        payload: Dict[str, Any] = {
            "document_id": document_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "provider": config.provider,
            "model": config.model,
            "dry_run": config.dry_run,
            "fields": config.fields,
            "rows": [],
            "support_path": str(support_path),
        }
        await _write_support_payload(support_path, payload)
        await _record("Review CSV was empty; recorded placeholder payload.", payload)
        return payload

    results: List[Dict[str, Any]] = []
    for idx, row in df.iterrows():
        label = _row_label(row, idx)
        prompt = llm_critique._build_prompt(row, config.fields, label)
        response = await asyncio.to_thread(_run_llm_prompt, prompt, config)
        results.append(
            {
                "row_id": label,
                "suggestions": response.get("fields", []),
                "usage": response.get("usage"),
                "cost_usd": response.get("cost_usd"),
            }
        )
        await _record(
            f"Processed row {label}",
            payload={"row_id": label, "dry_run": config.dry_run},
        )

    support_payload = {
        "document_id": document_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": config.provider,
        "model": config.model,
        "dry_run": config.dry_run,
        "fields": config.fields,
        "rows": results,
        "support_path": str(support_path),
    }

    await _write_support_payload(support_path, support_payload)

    async with async_session() as session:
        await repository.append_annotation_event(
            session,
            annotation_id=annotation.id,
            event_type="LLM_SUPPORT_READY",
            payload={"path": str(support_path)},
        )
        await session.commit()

    await _record(
        "LLM helper suggestions ready",
        payload={"document_id": document_id, "support_path": str(support_path)},
    )
    return support_payload


async def run_llm_support(
    document_id: str,
    *,
    fields: Optional[Iterable[str]] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    dry_run: Optional[bool] = None,
    api_key: Optional[str] = None,
) -> JobResponse:
    config = _load_config(
        fields=fields,
        provider=provider,
        model=model,
        dry_run=dry_run,
        api_key=api_key,
    )

    async def _task(job_id: str) -> Dict[str, Any]:
        return await _generate_llm_support(document_id, config, job_id)

    job_id = await job_manager.submit(
        job_type=DbJobType.annotation,
        coro_factory=_task,
        resource_type="document",
        resource_id=document_id,
    )
    return JobResponse(job_id=job_id, job_type=ApiJobType.annotation, status=ApiJobStatus.pending)


async def load_llm_support(document_id: str) -> Dict[str, Any]:
    async with async_session() as session:
        annotation = await repository.get_annotation_by_document(session, document_id)
        if not annotation:
            raise ValueError("Annotation record not found for document")
        analysis_dir = annotation_analysis_dir(annotation.id)
        support_path = analysis_dir / "llm_support.json"
        if not support_path.exists():
            raise ValueError("LLM support payload not found for document")

    def _reader() -> Dict[str, Any]:
        text = support_path.read_text(encoding="utf-8")
        return json.loads(text)

    return await asyncio.to_thread(_reader)

