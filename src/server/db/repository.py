"""Async repository helpers for database interactions."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Optional, Sequence

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    Annotation,
    AnnotationEvent,
    AnnotationStatus,
    AsyncJob,
    Document,
    DocumentVersion,
    Extraction,
    JobStatus,
    JobType,
    Metric,
    ModelVersion,
    TrainingRun,
    TrainingRunStatus,
    training_run_documents,
)


async def create_document(
    session: AsyncSession,
    *,
    document_id: str,
    filename: str,
    content_type: Optional[str],
    storage_path: str,
    checksum: Optional[str],
    size_bytes: Optional[int],
    extra_metadata: Optional[dict],
) -> Document:
    document = Document(
        id=document_id,
        filename=filename,
        content_type=content_type,
        storage_path=storage_path,
        checksum=checksum,
        size_bytes=size_bytes,
        extra_metadata=extra_metadata,
    )
    version = DocumentVersion(
        document=document,
        ordinal=1,
        source_storage_path=storage_path,
    )
    annotation = Annotation(document=document, status=AnnotationStatus.pending)
    session.add_all([document, version, annotation])
    await session.flush()
    return document


async def list_documents(session: AsyncSession) -> Sequence[Document]:
    stmt = (
        select(Document)
        .options(
            selectinload(Document.annotations),
            selectinload(Document.versions),
        )
        .order_by(Document.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().unique().all()


async def get_document(session: AsyncSession, document_id: str) -> Optional[Document]:
    stmt = (
        select(Document)
        .where(Document.id == document_id)
        .options(
            selectinload(Document.annotations).selectinload(Annotation.events),
            selectinload(Document.versions).selectinload(DocumentVersion.extractions),
        )
    )
    result = await session.execute(stmt)
    return result.scalars().unique().first()


async def create_extraction(
    session: AsyncSession,
    *,
    document_version_id: str,
    extractor_name: str,
    predictions: dict,
    confidence_summary: Optional[dict] = None,
) -> Extraction:
    extraction = Extraction(
        document_version_id=document_version_id,
        extractor_name=extractor_name,
        predictions=predictions,
        confidence_summary=confidence_summary,
        completed_at=datetime.now(timezone.utc),
    )
    session.add(extraction)
    await session.flush()
    return extraction


async def update_annotation_status(
    session: AsyncSession,
    *,
    annotation_id: str,
    status: AnnotationStatus,
    reviewer: Optional[str] = None,
    latest_payload: Optional[dict] = None,
    locked: Optional[bool] = None,
) -> None:
    values = {
        "status": status,
        "updated_at": datetime.now(timezone.utc),
    }
    if reviewer is not None:
        values["reviewer"] = reviewer
    if latest_payload is not None:
        values["latest_payload"] = latest_payload
    if locked is not None:
        values["locked"] = locked
    await session.execute(
        update(Annotation).where(Annotation.id == annotation_id).values(**values)
    )


async def append_annotation_event(
    session: AsyncSession,
    *,
    annotation_id: str,
    event_type: str,
    actor: Optional[str] = None,
    payload: Optional[dict] = None,
) -> AnnotationEvent:
    event = AnnotationEvent(
        annotation_id=annotation_id,
        event_type=event_type,
        actor=actor,
        payload=payload,
    )
    session.add(event)
    await session.flush()
    return event


async def get_annotation_by_document(
    session: AsyncSession, document_id: str
) -> Optional[Annotation]:
    stmt = (
        select(Annotation)
        .where(Annotation.document_id == document_id)
        .order_by(Annotation.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().first()


async def create_job(
    session: AsyncSession,
    *,
    job_id: str,
    job_type: JobType,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
) -> AsyncJob:
    job = AsyncJob(
        id=job_id,
        job_type=job_type,
        status=JobStatus.pending,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    session.add(job)
    await session.flush()
    return job


async def mark_job_running(session: AsyncSession, job_id: str) -> None:
    await session.execute(
        update(AsyncJob)
        .where(AsyncJob.id == job_id)
        .values(status=JobStatus.running, started_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    )


async def mark_job_succeeded(
    session: AsyncSession, job_id: str, payload: Optional[dict]
) -> None:
    await session.execute(
        update(AsyncJob)
        .where(AsyncJob.id == job_id)
        .values(
            status=JobStatus.succeeded,
            payload=payload,
            finished_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    )


async def mark_job_failed(
    session: AsyncSession, job_id: str, detail: str
) -> None:
    await session.execute(
        update(AsyncJob)
        .where(AsyncJob.id == job_id)
        .values(
            status=JobStatus.failed,
            detail=detail,
            finished_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    )


async def update_job_resource(
    session: AsyncSession,
    *,
    job_id: str,
    resource_type: str,
    resource_id: str,
) -> None:
    await session.execute(
        update(AsyncJob)
        .where(AsyncJob.id == job_id)
        .values(resource_type=resource_type, resource_id=resource_id, updated_at=datetime.now(timezone.utc))
    )


async def get_job(session: AsyncSession, job_id: str) -> Optional[AsyncJob]:
    stmt = select(AsyncJob).where(AsyncJob.id == job_id)
    result = await session.execute(stmt)
    return result.scalars().first()


async def list_jobs(session: AsyncSession) -> Sequence[AsyncJob]:
    stmt = select(AsyncJob).order_by(AsyncJob.created_at.desc())
    result = await session.execute(stmt)
    return result.scalars().all()


async def create_training_run(
    session: AsyncSession,
    *,
    training_run_id: str,
    triggered_by: Optional[str],
    parameters: Optional[dict],
) -> TrainingRun:
    run = TrainingRun(
        id=training_run_id,
        status=TrainingRunStatus.pending,
        triggered_by=triggered_by,
        parameters=parameters,
    )
    session.add(run)
    await session.flush()
    return run


async def set_training_run_status(
    session: AsyncSession,
    *,
    training_run_id: str,
    status: TrainingRunStatus,
    notes: Optional[str] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
) -> None:
    values = {
        "status": status,
        "updated_at": datetime.now(timezone.utc),
    }
    if notes is not None:
        values["notes"] = notes
    if started_at is not None:
        values["started_at"] = started_at
    if completed_at is not None:
        values["completed_at"] = completed_at
    await session.execute(
        update(TrainingRun)
        .where(TrainingRun.id == training_run_id)
        .values(**values)
    )


async def attach_training_documents(
    session: AsyncSession,
    *,
    training_run_id: str,
    document_ids: Iterable[str],
) -> None:
    rows = [
        {
            "training_run_id": training_run_id,
            "document_id": document_id,
        }
        for document_id in document_ids
    ]
    if rows:
        await session.execute(training_run_documents.insert(), rows)


async def create_metric(
    session: AsyncSession,
    *,
    training_run_id: str,
    name: str,
    value: Optional[float],
    payload: Optional[dict],
) -> Metric:
    metric = Metric(
        training_run_id=training_run_id,
        name=name,
        value=value,
        payload=payload,
    )
    session.add(metric)
    await session.flush()
    return metric


async def create_model_version(
    session: AsyncSession,
    *,
    training_run_id: str,
    artifact_path: str,
    model_name: Optional[str] = None,
    version_tag: Optional[str] = None,
    config_payload: Optional[dict] = None,
) -> ModelVersion:
    model = ModelVersion(
        training_run_id=training_run_id,
        artifact_path=artifact_path,
        model_name=model_name,
        version_tag=version_tag,
        config_payload=config_payload,
    )
    session.add(model)
    await session.flush()
    return model


async def count_documents(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(Document))
    return result.scalar_one()
