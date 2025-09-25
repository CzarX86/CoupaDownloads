"""Core orchestration logic for LLM helper jobs."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from server.db import repository
from server.db.models import JobType as DbJobType
from server.db.session import async_session
from server.db.storage import annotation_analysis_dir

from ..jobs import job_manager
from ..models import JobResponse, JobStatus as ApiJobStatus, JobType as ApiJobType
from .config import LLMConfig, load_config
from .payloads import placeholder_payload, read_review_dataframe, row_label, write_support_payload

try:
    from tools import llm_critique
except ImportError as exc:  # pragma: no cover - tooling requirement
    raise RuntimeError(
        "LLM helpers require the optional tooling dependencies. Install the project with tooling extras."
    ) from exc


def _run_llm_prompt(prompt: str, config: LLMConfig) -> Dict[str, Any]:
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


async def _record_job_detail(job_id: str, detail: str, payload: Optional[Dict[str, Any]] = None) -> None:
    async with async_session() as session:
        await repository.update_job_detail(session, job_id, detail=detail, payload=payload)
        await session.commit()


async def _load_review_context(document_id: str) -> tuple[Path, Dict[str, Any]]:
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
    return review_csv, {"annotation": annotation, "analysis_dir": analysis_dir}


async def _generate_llm_support(document_id: str, config: LLMConfig, job_id: str) -> Dict[str, Any]:
    await _record_job_detail(job_id, "Loading document context")
    review_csv, context = await _load_review_context(document_id)
    annotation = context["annotation"]
    analysis_dir: Path = context["analysis_dir"]
    df = await read_review_dataframe(review_csv)
    support_path = analysis_dir / "llm_support.json"

    if df.empty:
        payload = placeholder_payload(
            document_id,
            provider=config.provider,
            model=config.model,
            dry_run=config.dry_run,
            fields=config.fields,
            support_path=support_path,
        )
        await write_support_payload(support_path, payload)
        await _record_job_detail(job_id, "Review CSV was empty; recorded placeholder payload.", payload)
        return payload

    results: List[Dict[str, Any]] = []
    for idx, row in df.iterrows():
        label = row_label(row, idx)
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
        await _record_job_detail(
            job_id,
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

    await write_support_payload(support_path, support_payload)

    async with async_session() as session:
        await repository.append_annotation_event(
            session,
            annotation_id=annotation.id,
            event_type="LLM_SUPPORT_READY",
            payload={"path": str(support_path)},
        )
        await session.commit()

    await _record_job_detail(
        job_id,
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
    """Submit an asynchronous job that generates LLM support suggestions."""

    config = load_config(
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
    """Load the cached LLM support payload for a document."""

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
