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
from .fields import METADATA_COLUMNS, NORMALIZED_TO_PRETTY
from .models import (
    AnnotationDetail,
    DocumentDetail,
    DocumentSummary,
    JobDetail,
    JobResponse,
    JobStatus as ApiJobStatus,
    JobType as ApiJobType,
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


def build_document_summary(document: Document) -> DocumentSummary:
    latest_annotation: Optional[Annotation] = document.annotations[0] if document.annotations else None
    if document.annotations:
        latest_annotation = max(document.annotations, key=lambda ann: ann.updated_at)
    status = (latest_annotation.status.value if latest_annotation else AnnotationStatus.pending.value)
    return DocumentSummary(
        id=document.id,
        filename=document.filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        status=status,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def build_document_detail(document: Document) -> DocumentDetail:
    summary = build_document_summary(document)
    versions = [
        {
            "id": version.id,
            "ordinal": version.ordinal,
            "source_storage_path": version.source_storage_path,
            "created_at": version.created_at,
            "updated_at": version.updated_at,
        }
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


async def build_training_datasets(training_run_id: str) -> datasets.DatasetBundle:
    async with async_session() as session:
        bundle = await datasets.build_dataset_bundle(session, training_run_id)
    return bundle


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
