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
import pandas as pd

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
from tools.feedback_utils import write_review_csv
from tools.pdf_annotation import prepare_pdf_annotation_project

from . import datasets
from .jobs import job_manager
from .fields import METADATA_COLUMNS, NORMALIZED_TO_PRETTY, normalized_to_pretty
from .models import (
    AnnotationDetail,
    DocumentDetail,
    DocumentSummary,
    JobDetail,
    JobResponse,
    JobStatus as ApiJobStatus,
    JobType as ApiJobType,
    Entity,
    EntityLocation,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _build_default_review_dataframe(document_filename: str) -> pd.DataFrame:
    row: Dict[str, Any] = {
        "row_id": 1,
        "Source File": document_filename,
        "annotator": "",
        "notes": "",
        "timestamp": "",
    }
    for column in METADATA_COLUMNS:
        row[column] = ""

    seen_pretty: set[str] = set()
    for normalized, pretty in NORMALIZED_TO_PRETTY.items():
        if pretty in seen_pretty:
            continue
        seen_pretty.add(pretty)
        row[f"{pretty}_pred"] = ""
        row[f"{pretty}_gold"] = ""
        row[f"{pretty}_status"] = ""
    return pd.DataFrame([row])


def _prepare_analysis_assets(document_path: Path, annotation_id: str) -> Dict[str, Any]:
    analysis_dir = annotation_analysis_dir(annotation_id)
    review_csv_path = analysis_dir / "review.csv"
    dataframe = _build_default_review_dataframe(document_path.name)
    write_review_csv(dataframe, str(review_csv_path))
    project_info = prepare_pdf_annotation_project(
        review_csv=str(review_csv_path),
        out_dir=str(analysis_dir),
        pdf_root=str(document_path.parent),
    )
    project_info.update(
        {
            "analysis_dir": str(analysis_dir),
            "review_csv": str(review_csv_path),
        }
    )
    # Ensure payload is JSON-serialisable
    return {key: (value if not isinstance(value, Path) else str(value)) for key, value in project_info.items()}


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


def _stringify_prediction_value(value: Any) -> str | None:
    """Normalize raw prediction values to a string representation."""

    if value is None:
        return None

    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, (list, tuple)):
        flattened = [str(item).strip() for item in value if item not in (None, "")]
        if not flattened:
            return None
        return ", ".join(flattened)

    return str(value)


def _parse_entity_location(payload: Any) -> EntityLocation | None:
    """Build an EntityLocation instance if payload resembles a bounding box."""

    if payload is None:
        return None

    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return None

    page: int | None = None
    bbox: list[float] | None = None

    if isinstance(payload, dict):
        page_candidate = payload.get("page_num") or payload.get("page") or payload.get("pageNumber")
        if page_candidate is not None:
            try:
                page = int(page_candidate)
            except (TypeError, ValueError):
                page = None

        bbox_raw = (
            payload.get("bbox")
            or payload.get("box")
            or payload.get("coordinates")
            or payload.get("rect")
        )

        if isinstance(bbox_raw, str):
            try:
                bbox_raw = json.loads(bbox_raw)
            except json.JSONDecodeError:
                bbox_raw = None

        if isinstance(bbox_raw, dict):
            keys = ["x1", "y1", "x2", "y2"]
            if all(key in bbox_raw for key in keys):
                bbox = [float(bbox_raw[key]) for key in keys]
                if page is None:
                    page = int(bbox_raw.get("page") or bbox_raw.get("page_num") or 1)
        elif isinstance(bbox_raw, (list, tuple)) and len(bbox_raw) == 4:
            bbox = [float(coord) for coord in bbox_raw]

    elif isinstance(payload, (list, tuple)) and len(payload) == 4:
        bbox = [float(coord) for coord in payload]

    if bbox is None:
        return None

    if page is None:
        page = 1

    return EntityLocation(page_num=page, bbox=bbox)


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
        try:
            tasks_data = await asyncio.to_thread(
                lambda: json.loads(tasks_json_path.read_text(encoding="utf-8"))
            )
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid tasks JSON at {tasks_json_path}") from exc

        entities: List[Entity] = []
        if isinstance(tasks_data, list):
            for task in tasks_data:
                task_data = task.get("data") if isinstance(task, dict) else None
                if not isinstance(task_data, dict):
                    continue

                for key, raw_value in task_data.items():
                    if not key.endswith("_pred"):
                        continue
                    normalized_name = key[:-5]
                    value = _stringify_prediction_value(raw_value)
                    if not value:
                        continue

                    pretty_name = NORMALIZED_TO_PRETTY.get(normalized_name) or normalized_to_pretty(normalized_name)
                    location_payload = (
                        task_data.get(f"{normalized_name}_bbox")
                        or task_data.get(f"{normalized_name}_location")
                    )
                    location = _parse_entity_location(location_payload)
                    entities.append(Entity(type=pretty_name, value=value, location=location))

        return entities


<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
# This maps the internal database status enums to the string values the SPA frontend expects.
# This is necessary to fix a data contract mismatch identified during integration.
STATUS_MAP = {
    AnnotationStatus.pending.value: AnnotationStatus.pending.value,
    AnnotationStatus.in_review.value: AnnotationStatus.in_review.value,
    AnnotationStatus.completed.value: AnnotationStatus.completed.value,
}


=======
>>>>>>> theirs
=======
=======
>>>>>>> theirs
# This maps the internal database status enums to the string values the SPA frontend expects.
# This is necessary to fix a data contract mismatch identified during integration.
STATUS_MAP = {
    AnnotationStatus.pending.value: "new",
    AnnotationStatus.in_review.value: "reviewing",
    AnnotationStatus.completed.value: "completed",
}


<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
def build_document_summary(document: Document) -> DocumentSummary:
    latest_annotation: Optional[Annotation] = None
    if document.annotations:
        latest_annotation = max(document.annotations, key=lambda ann: ann.updated_at)

    db_status = latest_annotation.status.value if latest_annotation else AnnotationStatus.pending.value
    api_status = STATUS_MAP.get(db_status, db_status)  # Fallback to original value if not in map
    return DocumentSummary(
        id=document.id,
        filename=document.filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        status=api_status,
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
    async def task(job_id: str) -> Dict[str, Any]:
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
                    "config_path": project_info.get("config"),
                    "tasks_path": project_info.get("tasks_path"),
                    "review_csv": project_info.get("review_csv"),
                    "copied_pdfs": project_info.get("copied_pdfs"),
                    "missing_pdfs": project_info.get("missing_pdfs"),
                },
            )
            await session.commit()

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

    return AnnotationDetail(
        id=annotation.id,
        status=annotation.status.value,
        reviewer=annotation.reviewer,
        notes=annotation.notes,
        updated_at=annotation.updated_at,
    )


async def list_jobs() -> List[JobDetail]:
    return await job_manager.list()


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
