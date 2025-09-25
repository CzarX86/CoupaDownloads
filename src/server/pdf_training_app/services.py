"""Business logic for the PDF training workflow (database-backed)."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

from fastapi import UploadFile
from server.db import repository
from server.db.models import (
    Annotation,
    AnnotationStatus,
    Document,
    JobStatus as DbJobStatus,
    JobType as DbJobType,
    TrainingRunStatus,
)
from server.db.session import async_session
from server.db.storage import (
    annotation_analysis_dir,
    annotation_blob_path,
    document_blob_path,
    model_blob_path,
)

from . import datasets
from .jobs import job_manager
from .fields import METADATA_COLUMNS, NORMALIZED_TO_PRETTY
from .models import (
    AnnotationDetail,
    DocumentDetail,
    DocumentSummary,
    JobDetail,
    JobResponse,
    JobStatus as ApiJobStatus,
    JobType as ApiJobType,
    Entity,
)
from .support import load_llm_support as _load_llm_support_payload
from .support import run_llm_support as _run_llm_support


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_default_annotation_row(document_filename: str) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "row_id": "1",
        "Source File": document_filename,
        "annotator": "",
        "notes": "",
        "timestamp": "",
    }
    for column in METADATA_COLUMNS:
        if column == "Source File":
            continue
        row[column] = ""

    seen_pretty: set[str] = set()
    for normalized, pretty in NORMALIZED_TO_PRETTY.items():
        if pretty in seen_pretty:
            continue
        seen_pretty.add(pretty)
        row[pretty] = ""
        row[f"{pretty}_pred"] = ""
        row[f"{pretty}_gold"] = ""
        row[f"{pretty}_status"] = ""
    return row


def _prepare_analysis_assets(document_path: Path, annotation_id: str) -> Dict[str, Any]:
    analysis_dir = annotation_analysis_dir(annotation_id)
    analysis_dir.mkdir(parents=True, exist_ok=True)

    row = _build_default_annotation_row(document_path.name)
    tasks = [{"id": row["row_id"], "data": row}]
    fields = [
        {
            "normalized": normalized,
            "label": pretty,
        }
        for normalized, pretty in NORMALIZED_TO_PRETTY.items()
    ]

    manifest = {
        "annotation_id": annotation_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "document_filename": document_path.name,
        "fields": fields,
        "metadata_columns": METADATA_COLUMNS,
        "rows": [row],
    }

    config = {
        "fields": fields,
        "metadata_columns": METADATA_COLUMNS,
    }

    tasks_path = analysis_dir / "tasks.json"
    manifest_path = analysis_dir / "analysis.json"
    config_path = analysis_dir / "config.json"

    _write_json(tasks_path, tasks)
    _write_json(manifest_path, manifest)
    _write_json(config_path, config)

    return {
        "analysis_dir": str(analysis_dir),
        "tasks_path": str(tasks_path),
        "manifest_path": str(manifest_path),
        "config_path": str(config_path),
    }


def _apply_annotation_to_manifest(annotation_id: str, annotation_payload: Any) -> None:
    analysis_dir = annotation_analysis_dir(annotation_id)
    manifest_path = analysis_dir / "analysis.json"
    if not manifest_path.exists():
        return
    manifest = _load_json(manifest_path)
    rows = manifest.get("rows", [])
    if not isinstance(rows, list):
        rows = []
    _merge_annotation_payload(rows, annotation_payload)
    manifest["rows"] = rows
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    _write_json(manifest_path, manifest)


def _merge_annotation_payload(rows: List[Dict[str, Any]], annotation_payload: Any) -> None:
    if not annotation_payload or not isinstance(annotation_payload, list):
        return

    row_lookup: Dict[str, Dict[str, Any]] = {}
    for index, row in enumerate(rows):
        key = str(row.get("row_id") or index + 1)
        row_lookup[key] = row

    for item in annotation_payload:
        if not isinstance(item, dict):
            continue
        data = item.get("data") or {}
        raw_row_id = data.get("row_id", item.get("id"))
        if raw_row_id is None:
            continue
        row = row_lookup.get(str(raw_row_id))
        if row is None:
            continue
        annotations = item.get("annotations") or []
        for annotation in annotations:
            results = annotation.get("result") or []
            for result in results:
                from_name = result.get("from_name")
                value = result.get("value") or {}
                if not from_name:
                    continue
                if from_name.endswith("_gold"):
                    texts = value.get("text")
                    if isinstance(texts, list):
                        text_value = " ".join(text.strip() for text in texts if text).strip()
                    elif texts is None:
                        text_value = ""
                    else:
                        text_value = str(texts).strip()
                    row[from_name] = text_value
                    base = from_name[:-5]
                    if base and base not in row:
                        row[base] = text_value
                elif from_name.endswith("_status"):
                    choices = value.get("choices") or []
                    row[from_name] = choices[0] if choices else row.get(from_name, "")


async def create_document(file: UploadFile, metadata: Optional[Dict[str, Any]]) -> DocumentDetail:
    file_bytes = await file.read()
    checksum = hashlib.sha256(file_bytes).hexdigest()
    document_id = uuid4().hex
    storage_path = document_blob_path(document_id, file.filename or f"document-{document_id}.pdf")
    storage_path.write_bytes(file_bytes)
    size_bytes = len(file_bytes)

    async with async_session() as session:
        await repository.create_document(
            session,
            document_id=document_id,
            filename=file.filename or storage_path.name,
            content_type=file.content_type,
            storage_path=str(storage_path),
            checksum=checksum,
            size_bytes=size_bytes,
            extra_metadata=metadata,
        )
        await session.commit()

    # Kick off background analysis so the UI can display progress immediately.
    try:
        await start_analysis(document_id)
    except ValueError:
        # If the analysis cannot be started (e.g. annotation missing), fall back to
        # returning the document detail without blocking the upload flow.
        pass

    return await get_document_detail(document_id)


async def list_documents() -> List[DocumentSummary]:
    async with async_session() as session:
        documents = await repository.list_documents(session)
    return [build_document_summary(doc) for doc in documents]


async def get_document_detail(document_id: str) -> DocumentDetail:
    async with async_session() as session:
        document = await repository.get_document(session, document_id)
    if not document:
        raise ValueError("Document not found")
    return build_document_detail(document)


async def get_document_content_path(document_id: str) -> Path:
    async with async_session() as session:
        document = await repository.get_document(session, document_id)
    if not document:
        raise ValueError("Document not found")
    
    file_path = Path(document.storage_path)
    if not file_path.exists():
        raise ValueError("PDF file not found")
    
    return file_path


async def get_document_entities(document_id: str) -> List[Entity]:
    async with async_session() as session:
        document = await repository.get_document(session, document_id)
        if not document:
            raise ValueError(f"Document with ID {document_id} not found.")

        if not document.versions:
            return [] # No versions, no entities

        # Get the latest document version
        latest_version = max(document.versions, key=lambda v: v.created_at)

        if not latest_version.extractions:
            return [] # No extractions, no entities

        # Get the latest extraction for this version
        latest_extraction = max(latest_version.extractions, key=lambda e: e.created_at)

        # The predictions field contains a dictionary with 'tasks_path'
        predictions_payload = latest_extraction.predictions
        tasks_json_path_str = predictions_payload.get("tasks_path")

        if not tasks_json_path_str:
            return [] # No tasks_path in predictions, cannot find entities

        tasks_json_path = Path(tasks_json_path_str)
        if not tasks_json_path.exists():
            raise ValueError(f"Tasks JSON file not found at {tasks_json_path}")

        # Read the tasks.json file
        tasks_data = await asyncio.to_thread(lambda: json.loads(tasks_json_path.read_text(encoding="utf-8")))

        entities: List[Entity] = []
        if tasks_data and isinstance(tasks_data, list):
            # Assuming there's only one task per document for now, or we take the first one
            # The design doc implies a single document context for this endpoint
            if tasks_data:
                first_task_data = tasks_data[0].get("data", {})
                for key, value in first_task_data.items():
                    if key.endswith("_pred") and value:
                        pretty_name = key.replace("_pred", "")
                        # Use NORMALIZED_TO_PRETTY to get the original pretty name if needed
                        # For now, we'll use the pretty_name directly from the key
                        entities.append(Entity(type=pretty_name, value=str(value)))
        return entities


def build_document_summary(document: Document) -> DocumentSummary:
    latest_annotation: Optional[Annotation] = None
    if document.annotations:
        latest_annotation = max(document.annotations, key=lambda ann: ann.updated_at)

    status_value = latest_annotation.status.value if latest_annotation else AnnotationStatus.pending.value
    return DocumentSummary(
        id=document.id,
        filename=document.filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        status=status_value,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def build_document_detail(document: Document) -> DocumentDetail:
    summary = build_document_summary(document)
    from .models import DocumentVersionInfo

    versions = [
        DocumentVersionInfo(
            id=version.id,
            ordinal=version.ordinal,
            source_storage_path=version.source_storage_path,
            created_at=version.created_at,
            updated_at=version.updated_at,
        )
        for version in sorted(document.versions, key=lambda v: v.ordinal)
    ]
    annotations = [
        AnnotationDetail(
            id=annotation.id,
            status=annotation.status.value,
            reviewer=annotation.reviewer,
            notes=annotation.notes,
            updated_at=annotation.updated_at,
        )
        for annotation in sorted(document.annotations, key=lambda ann: ann.updated_at, reverse=True)
    ]
    return DocumentDetail(document=summary, versions=versions, annotations=annotations)


async def start_analysis(document_id: str) -> JobResponse:
    async with async_session() as session:
        document = await repository.get_document(session, document_id)
    if not document:
        raise ValueError("Document not found")

    async def task(job_id: str) -> Dict[str, Any]:
        async def _record_progress(message: str, *, payload: Optional[Dict[str, Any]] = None) -> None:
            async with async_session() as session:
                await repository.update_job_detail(
                    session,
                    job_id,
                    detail=message,
                    payload=payload,
                )
                await session.commit()

        await _record_progress("Loading document metadata")
        async with async_session() as session:
            document = await repository.get_document(session, document_id)
            if not document:
                raise ValueError("Document not found")
            if not document.versions:
                raise ValueError("Document has no versions to analyse")
            latest_version = max(document.versions, key=lambda v: v.ordinal)
            annotation = document.annotations[0] if document.annotations else None
            if not annotation:
                raise ValueError("Annotation record not found for document")
            document_path = Path(latest_version.source_storage_path)
            annotation_id = annotation.id
            latest_version_id = latest_version.id

        await _record_progress("Preparing annotation manifest")
        project_info = await asyncio.to_thread(
            _prepare_analysis_assets,
            document_path,
            annotation_id,
        )

        async with async_session() as session:
            await repository.create_extraction(
                session,
                document_version_id=latest_version_id,
                extractor_name="auto-analysis",
                predictions={"tasks_path": project_info.get("tasks_path")},
                confidence_summary=None,
            )
            await repository.update_annotation_status(
                session,
                annotation_id=annotation_id,
                status=AnnotationStatus.in_review,
                latest_payload={},
                locked=True,
            )
            await repository.append_annotation_event(
                session,
                annotation_id=annotation_id,
                event_type="ANALYSIS_READY",
                payload={
                    "job_id": job_id,
                    "analysis_dir": project_info.get("analysis_dir"),
                    "config_path": project_info.get("config_path"),
                    "tasks_path": project_info.get("tasks_path"),
                    "manifest_path": project_info.get("manifest_path"),
                },
            )
            await session.commit()

        await _record_progress(
            "Annotation manifest ready",
            payload={
                "document_id": document_id,
                "manifest_path": project_info.get("manifest_path"),
            },
        )
        return {"document_id": document_id, "analysis": project_info}

    job_id = await job_manager.submit(
        job_type=DbJobType.analysis,
        coro_factory=task,
        resource_type="document",
        resource_id=document_id,
    )
    return JobResponse(job_id=job_id, job_type=ApiJobType.analysis, status=ApiJobStatus.pending)


async def ingest_annotation_export(document_id: str, export_file: UploadFile) -> AnnotationDetail:
    raw_bytes = await export_file.read()
    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid Label Studio export JSON") from exc

    async with async_session() as session:
        annotation = await repository.get_annotation_by_document(session, document_id)
        if not annotation:
            raise ValueError("Annotation record not found for document")
        export_path = annotation_blob_path(annotation.id)
        export_path.write_bytes(raw_bytes)
        await repository.update_annotation_status(
            session,
            annotation_id=annotation.id,
            status=AnnotationStatus.completed,
            latest_payload=payload,
            locked=False,
        )
        await repository.append_annotation_event(
            session,
            annotation_id=annotation.id,
            event_type="LABEL_STUDIO_EXPORT",
            payload={"path": str(export_path)}
        )
        await session.commit()
        await session.refresh(annotation)

    _apply_annotation_to_manifest(annotation.id, payload)

    return AnnotationDetail(
        id=annotation.id,
        status=annotation.status.value,
        reviewer=annotation.reviewer,
        notes=annotation.notes,
        updated_at=annotation.updated_at,
    )


async def list_jobs(
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
) -> List[JobDetail]:
    return await job_manager.list(
        resource_type=resource_type,
        resource_id=resource_id,
    )


async def list_training_runs() -> List[JobDetail]:
    """Lists all jobs that are training runs."""
    all_jobs = await job_manager.list()
    return [job for job in all_jobs if job.job_type == ApiJobType.training]


async def get_job(job_id: str) -> JobDetail:
    job = await job_manager.get(job_id)
    if not job:
        raise ValueError("Job not found")
    return job


async def create_training_run(document_ids: Optional[Iterable[str]], triggered_by: Optional[str]) -> JobResponse:
    doc_ids = list(document_ids or [])

    async def task(job_id: str) -> Dict[str, Any]:
        async with async_session() as session:
            run = await repository.create_training_run(
                session,
                training_run_id=job_id,
                triggered_by=triggered_by,
                parameters={"document_ids": doc_ids},
            )
            if doc_ids:
                await repository.attach_training_documents(
                    session, training_run_id=run.id, document_ids=doc_ids
                )
            await repository.update_job_resource(
                session,
                job_id=job_id,
                resource_type="training_run",
                resource_id=run.id,
            )
            await session.commit()

        async with async_session() as session:
            await repository.set_training_run_status(
                session,
                training_run_id=job_id,
                status=TrainingRunStatus.running,
                started_at=_utcnow(),
            )
            await session.commit()

        # Placeholder training logic – to be replaced in Plan 41
        artifact_path = model_blob_path(job_id)
        artifact_path.write_text("Placeholder model artifact\n", encoding="utf-8")

        async with async_session() as session:
            await repository.create_model_version(
                session,
                training_run_id=job_id,
                artifact_path=str(artifact_path),
                model_name="placeholder",
                version_tag="v0",
            )
            await repository.create_metric(
                session,
                training_run_id=job_id,
                name="status",
                value=None,
                payload={"message": "Training pipeline pending implementation"},
            )
            await repository.set_training_run_status(
                session,
                training_run_id=job_id,
                status=TrainingRunStatus.succeeded,
                completed_at=_utcnow(),
            )
            await session.commit()
        return {
            "training_run_id": job_id,
            "model_artifact_path": str(artifact_path),
            "metrics": {"message": "Training pipeline pending implementation"},
        }

    job_id = await job_manager.submit(
        job_type=DbJobType.training,
        coro_factory=task,
        resource_type="training_run",
        resource_id=None,
    )
    return JobResponse(job_id=job_id, job_type=ApiJobType.training, status=ApiJobStatus.pending)


async def build_training_datasets(training_run_id: str):
    async with async_session() as session:
        dataset_builder = datasets.DatasetBuilder(session)
        records = await dataset_builder.build_from_annotations()
    return records


async def get_training_run_dataset(training_run_id: str) -> list[dict]:
    """Builds and returns the dataset for a given training run."""
    async with async_session() as session:
        # In the future, this could be enhanced to build a dataset
        # specific to the documents in the training run.
        dataset_builder = datasets.DatasetBuilder(session)
        records = await dataset_builder.build_from_annotations()
        return records


async def get_training_run_model_path(training_run_id: str) -> Optional[Path]:
    """Returns the path to the model artifact for a given training run."""
    async with async_session() as session:
        run = await repository.get_training_run(session, training_run_id)
        if not run or not run.model_version:
            return None
        return Path(run.model_version.artifact_path)


async def start_llm_support(
    document_id: str,
    *,
    fields: Optional[Iterable[str]] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    dry_run: Optional[bool] = None,
) -> JobResponse:
    """Trigger the LLM helper to generate suggestions for a document."""

    return await _run_llm_support(
        document_id,
        fields=fields,
        provider=provider,
        model=model,
        dry_run=dry_run,
    )


async def get_llm_support_payload(document_id: str) -> Dict[str, Any]:
    """Return the cached LLM support payload for a document."""

    return await _load_llm_support_payload(document_id)
