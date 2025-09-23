"""Declarative models for the AI Builder-style workflow."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


class AnnotationStatus(str, enum.Enum):
    pending = "PENDING"
    in_review = "IN_REVIEW"
    completed = "COMPLETED"


class JobStatus(str, enum.Enum):
    pending = "PENDING"
    running = "RUNNING"
    succeeded = "SUCCEEDED"
    failed = "FAILED"


class JobType(str, enum.Enum):
    analysis = "ANALYSIS"
    annotation = "ANNOTATION"
    training = "TRAINING"


class TrainingRunStatus(str, enum.Enum):
    pending = "PENDING"
    running = "RUNNING"
    succeeded = "SUCCEEDED"
    failed = "FAILED"


training_run_documents = Table(
    "training_run_documents",
    Base.metadata,
    Column("training_run_id", String(36), ForeignKey("training_runs.id", ondelete="CASCADE"), primary_key=True),
    Column("document_id", String(36), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
)


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    extra_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    versions: Mapped[list["DocumentVersion"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="DocumentVersion.created_at"
    )
    annotations: Mapped[list["Annotation"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    training_runs: Mapped[list["TrainingRun"]] = relationship(
        secondary=training_run_documents, back_populates="documents"
    )


class DocumentVersion(Base, TimestampMixin):
    __tablename__ = "document_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped[Document] = relationship(back_populates="versions")
    extractions: Mapped[list["Extraction"]] = relationship(
        back_populates="document_version", cascade="all, delete-orphan"
    )


class Extraction(Base, TimestampMixin):
    __tablename__ = "extractions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False
    )
    extractor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    predictions: Mapped[dict] = mapped_column(JSON, nullable=False)
    confidence_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document_version: Mapped[DocumentVersion] = relationship(back_populates="extractions")
    annotations: Mapped[list["Annotation"]] = relationship(back_populates="source_extraction")


class Annotation(Base, TimestampMixin):
    __tablename__ = "annotations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_extraction_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("extractions.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[AnnotationStatus] = mapped_column(
        Enum(AnnotationStatus), default=AnnotationStatus.pending, nullable=False
    )
    reviewer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    latest_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    document: Mapped[Document] = relationship(back_populates="annotations")
    source_extraction: Mapped[Extraction | None] = relationship(back_populates="annotations")
    events: Mapped[list["AnnotationEvent"]] = relationship(
        back_populates="annotation", cascade="all, delete-orphan", order_by="AnnotationEvent.created_at"
    )


class AnnotationEvent(Base, TimestampMixin):
    __tablename__ = "annotation_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    annotation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("annotations.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    annotation: Mapped[Annotation] = relationship(back_populates="events")


class TrainingRun(Base, TimestampMixin):
    __tablename__ = "training_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    status: Mapped[TrainingRunStatus] = mapped_column(
        Enum(TrainingRunStatus), default=TrainingRunStatus.pending, nullable=False
    )
    triggered_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    model_version: Mapped[ModelVersion | None] = relationship(
        back_populates="training_run", uselist=False, cascade="all, delete-orphan"
    )
    metrics: Mapped[list["Metric"]] = relationship(
        back_populates="training_run", cascade="all, delete-orphan"
    )
    documents: Mapped[list[Document]] = relationship(
        secondary=training_run_documents, back_populates="training_runs"
    )


class ModelVersion(Base, TimestampMixin):
    __tablename__ = "model_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    training_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("training_runs.id", ondelete="CASCADE"), nullable=False
    )
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version_tag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    artifact_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    config_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    training_run: Mapped[TrainingRun] = relationship(back_populates="model_version")


class Metric(Base, TimestampMixin):
    __tablename__ = "metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    training_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("training_runs.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[float | None] = mapped_column(nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    training_run: Mapped[TrainingRun] = relationship(back_populates="metrics")


class AsyncJob(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_type: Mapped[JobType] = mapped_column(Enum(JobType), nullable=False)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), nullable=False, default=JobStatus.pending)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    resource_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
