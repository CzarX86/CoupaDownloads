"""FastAPI router exposing the database-backed PDF training workflow."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Response
from fastapi.responses import FileResponse
from sqlalchemy import select, func

from server.db import repository
from server.db.models import AsyncJob
from server.db.session import async_session

from .models import (
    AnnotationCreateRequest,
    AnnotationDetail,
    AnnotationUpdateRequest,
    DocumentDetail,
    DocumentSummary,
    DocumentListResponse,
    DocumentUploadRequest,
    Entity,
    ErrorResponse,
    HealthResponse,
    JobDetail,
    JobListResponse,
    JobResponse,
    SystemStatusResponse,
    TrainingRunCreateRequest,
    FeedbackRequest,
)
from .services import (
    create_annotation,
    create_document,
    create_training_run,
    delete_annotation,
    get_document_detail,
    get_document_content_path,
    get_training_run_dataset,
    get_training_run_model_path,
    get_job,
    ingest_annotation_export,
    list_documents,
    list_training_runs,
    list_jobs,
    start_analysis,
    get_document_entities,
    update_annotation,
    trigger_model_feedback,
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


@router.get("/documents/{document_id}/content")
async def get_document_content_endpoint(document_id: str) -> FileResponse:
    try:
        file_path = await get_document_content_path(document_id)
        return FileResponse(file_path, media_type="application/pdf")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/documents/{document_id}/entities", response_model=List[Entity])
async def get_document_entities_endpoint(document_id: str) -> List[Entity]:
    try:
        return await get_document_entities(document_id)
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


@router.post(
    "/documents/{document_id}/annotations",
    response_model=AnnotationDetail,
    status_code=201,
)
async def create_annotation_endpoint(
    document_id: str,
    payload: AnnotationCreateRequest,
) -> AnnotationDetail:
    try:
        return await create_annotation(document_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/annotations/{annotation_id}", response_model=AnnotationDetail)
async def update_annotation_endpoint(
    annotation_id: str,
    payload: AnnotationUpdateRequest,
) -> AnnotationDetail:
    try:
        return await update_annotation(annotation_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/annotations/{annotation_id}", status_code=204)
async def delete_annotation_endpoint(annotation_id: str) -> Response:
    try:
        await delete_annotation(annotation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


@router.post("/training-runs", response_model=JobResponse)
async def create_training_run_endpoint(payload: TrainingRunCreateRequest) -> JobResponse:
    return await create_training_run(payload.document_ids, payload.triggered_by)


@router.post(
    "/documents/{document_id}/feedback",
    response_model=JobResponse,
    status_code=202,
)
async def trigger_feedback_endpoint(
    document_id: str,
    payload: FeedbackRequest | None = None,
) -> JobResponse:
    try:
        return await trigger_model_feedback(document_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/training-runs", response_model=List[JobDetail])
async def list_training_runs_endpoint() -> List[JobDetail]:
    runs = await list_training_runs()
    return runs


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
    try:
        job = await get_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
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
