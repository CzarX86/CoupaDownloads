"""FastAPI router exposing the database-backed PDF training workflow."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from sqlalchemy import select, func

from server.db import repository
from server.db.models import AsyncJob
from server.db.session import async_session

from .models import (
    AnnotationDetail,
    DocumentDetail,
    DocumentListResponse,
    DocumentUploadRequest,
    ErrorResponse,
    HealthResponse,
    JobDetail,
    JobListResponse,
    JobResponse,
    SystemStatusResponse,
    TrainingRunCreateRequest,
)
from .services import (
    create_document,
    create_training_run,
    get_document_detail,
    get_job,
    ingest_annotation_export,
    list_documents,
    list_jobs,
    start_analysis,
)

router = APIRouter()


@router.post("/documents", response_model=DocumentDetail)
async def upload_document(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None),
) -> DocumentDetail:
    metadata_payload = None
    if metadata:
        try:
            metadata_payload = json.loads(metadata)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON metadata") from exc
    return await create_document(file, metadata_payload)


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents_endpoint() -> DocumentListResponse:
    documents = await list_documents()
    return DocumentListResponse(items=documents)


@router.get("/documents/{document_id}", response_model=DocumentDetail)
async def get_document_endpoint(document_id: str) -> DocumentDetail:
    try:
        return await get_document_detail(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/documents/{document_id}/analyze", response_model=JobResponse)
async def analyze_document_endpoint(document_id: str) -> JobResponse:
    try:
        return await start_analysis(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/documents/{document_id}/annotations/ingest",
    response_model=AnnotationDetail,
)
async def ingest_annotation_endpoint(
    document_id: str,
    export_json: UploadFile = File(...),
) -> AnnotationDetail:
    try:
        return await ingest_annotation_export(document_id, export_json)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/training-runs", response_model=JobResponse)
async def create_training_run_endpoint(payload: TrainingRunCreateRequest) -> JobResponse:
    return await create_training_run(payload.document_ids, payload.triggered_by)


@router.get("/training-runs/{run_id}/dataset")
async def get_training_run_dataset_endpoint(run_id: str):
    try:
        dataset = await get_training_run_dataset(run_id)
        return dataset
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/training-runs/{run_id}/model")
async def get_training_run_model_endpoint(run_id: str):
    try:
        model_path = await get_training_run_model_path(run_id)
        if not model_path or not model_path.exists():
            raise HTTPException(status_code=404, detail="Model artifact not found")
        return FileResponse(model_path, filename=model_path.name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs_endpoint() -> JobListResponse:
    jobs = await list_jobs()
    return JobListResponse(jobs=jobs)


@router.get("/jobs/{job_id}", response_model=JobDetail)
async def get_job_endpoint(job_id: str) -> JobDetail:
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint for SPA polling."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@router.get("/system-status", response_model=SystemStatusResponse)
async def system_status() -> SystemStatusResponse:
    """System status endpoint with detailed service health information."""
    try:
        async with async_session() as session:
            # Check database connectivity with simple query
            document_count = await repository.count_documents(session)
            job_count_result = await session.execute(select(func.count()).select_from(AsyncJob))
            job_count = job_count_result.scalar_one()
            
            return SystemStatusResponse(
                status="healthy",
                database="connected",
                document_count=document_count,
                job_count=job_count,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
    except Exception as exc:
        return SystemStatusResponse(
            status="degraded",
            database="disconnected",
            document_count=0,
            job_count=0,
            error=str(exc),
            timestamp=datetime.now(timezone.utc).isoformat()
        )
