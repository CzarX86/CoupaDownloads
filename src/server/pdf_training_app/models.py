"""Pydantic schemas for the PDF training API."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, validator


class JobStatus(str, Enum):
    pending = "PENDING"
    running = "RUNNING"
    succeeded = "SUCCEEDED"
    failed = "FAILED"


class JobType(str, Enum):
    analysis = "ANALYSIS"
    annotation = "ANNOTATION"
    training = "TRAINING"


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    status: str
    created_at: datetime
    updated_at: datetime


class DocumentVersionInfo(BaseModel):
    id: str
    ordinal: int
    source_storage_path: str
    created_at: datetime
    updated_at: datetime


class AnnotationStatusEnum(str, Enum):
    pending = "PENDING"
    in_review = "IN_REVIEW"
    completed = "COMPLETED"


class AnnotationBase(BaseModel):
    type: Optional[str] = None
    value: Optional[str] = None
    location: Optional[EntityLocation] = None
    reviewer: Optional[str] = None
    notes: Optional[str] = None


class AnnotationCreateRequest(AnnotationBase):
    type: str
    value: str
    status: Optional[AnnotationStatusEnum] = Field(
        default=AnnotationStatusEnum.in_review,
        description="Initial status for the annotation",
    )


class AnnotationUpdateRequest(AnnotationBase):
    status: Optional[AnnotationStatusEnum] = Field(
        default=None,
        description="Updated status for the annotation",
    )


class AnnotationDetail(AnnotationBase):
    id: str
    document_id: str
    status: AnnotationStatusEnum
    created_at: datetime
    updated_at: datetime


class EntityLocation(BaseModel):
    page_num: int
    bbox: List[float] # [x1, y1, x2, y2]

class Entity(BaseModel):
    type: str
    value: str
    location: Optional[EntityLocation] = None


class DocumentDetail(BaseModel):
    document: DocumentSummary
    versions: List[DocumentVersionInfo]
    annotations: List[AnnotationDetail]


class DocumentListResponse(BaseModel):
    items: List[DocumentSummary]


class JobDetail(BaseModel):
    id: str
    job_type: JobType
    status: JobStatus
    detail: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class JobResponse(BaseModel):
    job_id: str
    job_type: JobType
    status: JobStatus


class JobListResponse(BaseModel):
    jobs: List[JobDetail]


class TrainingRunCreateRequest(BaseModel):
    document_ids: Optional[List[str]] = Field(default=None, description="Subset of document IDs to include in the run")
    triggered_by: Optional[str] = Field(default=None, description="Identifier for the user/process triggering the run")

    @validator('document_ids')
    def validate_document_ids(cls, v):
        if v is None:
            return v

        cleaned = [doc_id for doc_id in v if doc_id]
        if not cleaned:
            return None

        for doc_id in cleaned:
            if not isinstance(doc_id, str) or len(doc_id) != 32:
                raise ValueError(f'Invalid document ID format: {doc_id}')
        return cleaned


class HealthResponse(BaseModel):
    status: str
    timestamp: str


class SystemStatusResponse(BaseModel):
    status: str
    database: str
    document_count: int
    job_count: int
    timestamp: str
    error: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: str


class DocumentUploadRequest(BaseModel):
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata for the document")


class AnnotationIngestRequest(BaseModel):
    export_format: str = Field(default="label_studio", description="Format of the annotation export")


class FeedbackRequest(BaseModel):
    annotation_ids: Optional[List[str]] = Field(
        default=None,
        description="Subset of annotation IDs to include in the feedback job",
    )
    triggered_by: Optional[str] = Field(
        default=None,
        description="Identifier for the actor triggering the feedback",
    )
