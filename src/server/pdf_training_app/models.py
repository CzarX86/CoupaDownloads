"""Pydantic schemas for the PDF training API."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class AnnotationDetail(BaseModel):
    id: str
    status: str
    reviewer: Optional[str] = None
    notes: Optional[str] = None
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

    @field_validator("document_ids")
    @classmethod
    def _validate_document_ids(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return None
        cleaned: List[str] = []
        for doc_id in value:
            if not isinstance(doc_id, str):
                raise TypeError("document_ids must contain string identifiers")
            stripped = doc_id.strip()
            if not stripped:
                raise ValueError("document_ids cannot include empty identifiers")
            cleaned.append(stripped)
        return cleaned


class LLMSupportRequest(BaseModel):
    fields: Optional[List[str]] = Field(default=None, description="Optional subset of normalized field names to critique")
    provider: Optional[str] = Field(default=None, description="LLM provider identifier (e.g. deepseek, openai)")
    model: Optional[str] = Field(default=None, description="Model name to use for the LLM helper")
    dry_run: Optional[bool] = Field(default=None, description="Force dry-run mode regardless of environment settings")


class LLMFieldSuggestion(BaseModel):
    field: str
    decision: str
    suggested: Optional[str] = None
    rationale: Optional[str] = None
    confidence: Optional[float] = None


class LLMSupportRow(BaseModel):
    row_id: str
    suggestions: List[LLMFieldSuggestion]
    usage: Optional[Dict[str, Any]] = None
    cost_usd: Optional[float] = None


class LLMSupportResponse(BaseModel):
    document_id: str
    generated_at: datetime
    provider: str
    model: str
    dry_run: bool
    fields: List[str]
    rows: List[LLMSupportRow]


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
