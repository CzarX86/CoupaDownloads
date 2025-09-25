"""Integration tests for the PDF training API endpoints."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Generator

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

import pytest
from fastapi.testclient import TestClient
from starlette.datastructures import Headers, UploadFile


def _reload_modules() -> SimpleNamespace:
    """Reload server modules after tweaking environment variables."""
    for name in list(sys.modules):
        if name.startswith("server.db") or name.startswith("server.pdf_training_app"):
            sys.modules.pop(name)

    from server.db import models
    from server.db import session as db_session
    from server.pdf_training_app import api, services
    from server.pdf_training_app import jobs as jobs_module

    async def _create_schema() -> None:
        async with db_session._engine.begin() as conn:  # type: ignore[attr-defined]
            await conn.run_sync(models.Base.metadata.create_all)

    asyncio.run(_create_schema())

    return SimpleNamespace(
        models=models,
        db_session=db_session,
        api=api,
        services=services,
        job_manager=jobs_module.job_manager,
    )


def _wait_for_document_jobs(
    client: TestClient,
    api_context: SimpleNamespace,
    document_id: str,
    *,
    timeout: float = 15.0,
) -> None:
    async def _wait() -> None:
        jobs = await api_context.job_manager.list(resource_type="document", resource_id=document_id)
        for job in jobs:
            await api_context.job_manager.wait_until_complete(job.id, timeout=timeout)

    asyncio.run(_wait())


@pytest.fixture(scope="function")
def api_context() -> Generator[SimpleNamespace, None, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        storage_root = base_path / "storage"
        db_path = base_path / "app.db"
        os.environ["PDF_TRAINING_STORAGE_ROOT"] = str(storage_root)
        os.environ["PDF_TRAINING_DB_URL"] = f"sqlite+aiosqlite:///{db_path}"
        os.environ["PDF_TRAINING_FORCE_SYNC_JOBS"] = "1"

        ctx = _reload_modules()
        try:
            yield SimpleNamespace(
                **ctx.__dict__,
                base_path=base_path,
                storage_root=storage_root,
            )
        finally:
            os.environ.pop("PDF_TRAINING_FORCE_SYNC_JOBS", None)
            asyncio.run(ctx.db_session.close_engine())


@pytest.fixture
def client(api_context: SimpleNamespace) -> Generator[TestClient, None, None]:
    """Create a test client for the API."""
    from server.pdf_training_app import app

    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        asyncio.run(api_context.job_manager.drain(timeout=15.0))
        test_client.close()


def _make_upload_file(content: bytes, filename: str, content_type: str) -> UploadFile:
    headers = Headers({"content-type": content_type})
    return UploadFile(file=BytesIO(content), filename=filename, headers=headers)


def _create_test_pdf() -> bytes:
    """Create a minimal PDF file for testing."""
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n180\n%%EOF"


def _create_label_studio_export() -> bytes:
    """Create a minimal Label Studio export for testing."""
    export_data = [
        {
            "data": {
                "row_id": 1,
                "Source File": "test.pdf"
            },
            "annotations": [
                {
                    "result": [
                        {
                            "from_name": "contract_name_gold",
                            "to_name": "text",
                            "type": "textarea",
                            "value": {"text": ["Test Contract"]}
                        }
                    ]
                }
            ]
        }
    ]
    return json.dumps(export_data).encode("utf-8")


class TestHealthEndpoints:
    """Test health and system status endpoints."""
    
    def test_health_endpoint(self, client: TestClient):
        """Test the health endpoint returns healthy status."""
        response = client.get("/api/pdf-training/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_system_status_endpoint(self, client: TestClient):
        """Test the system status endpoint returns database status."""
        response = client.get("/api/pdf-training/system-status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert data["database"] in ["connected", "disconnected"]
        assert "document_count" in data
        assert "job_count" in data
        assert "timestamp" in data


class TestDocumentEndpoints:
    """Test document-related endpoints."""
    
    def test_upload_document_success(self, client: TestClient):
        """Test successful document upload."""
        pdf_content = _create_test_pdf()
        metadata = json.dumps({"ingested_by": "test", "source": "api_test"})
        
        response = client.post(
            "/api/pdf-training/documents",
            files={"file": ("test.pdf", pdf_content, "application/pdf")},
            data={"metadata": metadata}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["document"]["filename"] == "test.pdf"
        assert data["document"]["content_type"] == "application/pdf"
        assert data["document"]["size_bytes"] == len(pdf_content)
        assert len(data["versions"]) == 1
        assert len(data["annotations"]) == 1

    def test_upload_document_invalid_metadata(self, client: TestClient):
        """Test document upload with invalid JSON metadata."""
        pdf_content = _create_test_pdf()
        
        response = client.post(
            "/api/pdf-training/documents",
            files={"file": ("test.pdf", pdf_content, "application/pdf")},
            data={"metadata": "invalid json"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid JSON metadata" in data["detail"]

    def test_list_documents_empty(self, client: TestClient):
        """Test listing documents when none exist."""
        response = client.get("/api/pdf-training/documents")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_documents_with_data(self, client: TestClient):
        """Test listing documents after uploading one."""
        # First upload a document
        pdf_content = _create_test_pdf()
        client.post(
            "/api/pdf-training/documents",
            files={"file": ("test.pdf", pdf_content, "application/pdf")}
        )
        
        response = client.get("/api/pdf-training/documents")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["filename"] == "test.pdf"

    def test_get_document_not_found(self, client: TestClient):
        """Test getting a non-existent document."""
        response = client.get("/api/pdf-training/documents/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "Document not found" in data["detail"]

    def test_get_document_success(self, client: TestClient):
        """Test getting an existing document."""
        # First upload a document
        pdf_content = _create_test_pdf()
        upload_response = client.post(
            "/api/pdf-training/documents",
            files={"file": ("test.pdf", pdf_content, "application/pdf")}
        )
        document_id = upload_response.json()["document"]["id"]

        response = client.get(f"/api/pdf-training/documents/{document_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["document"]["id"] == document_id
        assert data["document"]["filename"] == "test.pdf"

    def test_get_document_content_success(self, client: TestClient):
        """Document content endpoint returns the stored PDF bytes."""
        pdf_content = _create_test_pdf()
        upload_response = client.post(
            "/api/pdf-training/documents",
            files={"file": ("test.pdf", pdf_content, "application/pdf")}
        )
        document_id = upload_response.json()["document"]["id"]

        response = client.get(f"/api/pdf-training/documents/{document_id}/content")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content == pdf_content

    def test_get_document_content_not_found(self, client: TestClient):
        """Document content endpoint returns 404 when the document is missing."""
        response = client.get("/api/pdf-training/documents/missing-id/content")
        assert response.status_code == 404
        assert "Document not found" in response.json()["detail"]


class TestAnalysisEndpoints:
    """Test analysis-related endpoints."""
    
    def test_analyze_document_not_found(self, client: TestClient):
        """Test analyzing a non-existent document."""
        response = client.post("/api/pdf-training/documents/nonexistent/analyze")
        assert response.status_code == 404
        data = response.json()
        assert "Document not found" in data["detail"]

    def test_analyze_document_success(self, client: TestClient, api_context: SimpleNamespace):
        """Test successful document analysis."""
        # First upload a document
        pdf_content = _create_test_pdf()
        upload_response = client.post(
            "/api/pdf-training/documents",
            files={"file": ("test.pdf", pdf_content, "application/pdf")}
        )
        document_id = upload_response.json()["document"]["id"]

        _wait_for_document_jobs(client, api_context, document_id)

        response = client.post(f"/api/pdf-training/documents/{document_id}/analyze")
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) == {"job_id", "job_type", "status"}

        asyncio.run(
            api_context.job_manager.wait_until_complete(data["job_id"], timeout=10)
        )


class TestLLMSupportEndpoints:
    """Ensure the LLM helper support endpoints behave as expected."""

    def test_llm_support_flow(self, client: TestClient, api_context: SimpleNamespace):
        pdf_content = _create_test_pdf()
        upload_response = client.post(
            "/api/pdf-training/documents",
            files={"file": ("support.pdf", pdf_content, "application/pdf")},
        )
        assert upload_response.status_code == 200
        document_id = upload_response.json()["document"]["id"]

        async def _prepare_payload() -> None:
            analysis_job = await api_context.services.start_analysis(document_id)
            await api_context.job_manager.wait_until_complete(analysis_job.job_id, timeout=30)
            support_job = await api_context.services.start_llm_support(document_id, dry_run=True)
            await api_context.job_manager.wait_until_complete(support_job.job_id, timeout=30)

        asyncio.run(_prepare_payload())

        payload_response = client.get(f"/api/pdf-training/documents/{document_id}/support/llm")
        assert payload_response.status_code == 200
        payload = payload_response.json()
        assert payload["document_id"] == document_id
        assert isinstance(payload["rows"], list)

    def test_llm_support_missing_document(self, client: TestClient):
        response = client.post("/api/pdf-training/documents/missing/support/llm")
        assert response.status_code == 404
        assert "Document not found" in response.json()["detail"]


class TestAnnotationEndpoints:
    """Test annotation-related endpoints."""
    
    def test_ingest_annotation_document_not_found(self, client: TestClient):
        """Test ingesting annotations for a non-existent document."""
        export_content = _create_label_studio_export()
        
        response = client.post(
            "/api/pdf-training/documents/nonexistent/annotations/ingest",
            files={"export_json": ("export.json", export_content, "application/json")}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Annotation record not found" in data["detail"]

    def test_ingest_annotation_invalid_json(self, client: TestClient):
        """Test ingesting invalid JSON export."""
        # First upload a document
        pdf_content = _create_test_pdf()
        upload_response = client.post(
            "/api/pdf-training/documents",
            files={"file": ("test.pdf", pdf_content, "application/pdf")}
        )
        document_id = upload_response.json()["document"]["id"]
        
        response = client.post(
            f"/api/pdf-training/documents/{document_id}/annotations/ingest",
            files={"export_json": ("export.json", b"invalid json", "application/json")}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid Label Studio export JSON" in data["detail"]


class TestTrainingEndpoints:
    """Test training-related endpoints."""
    
    def test_create_training_run_empty_documents(self, client: TestClient, api_context: SimpleNamespace):
        """Test creating a training run with no documents."""
        payload = {
            "document_ids": [],
            "triggered_by": "test"
        }
        
        response = client.post("/api/pdf-training/training-runs", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["job_type"] == "TRAINING"
        assert data["status"] == "PENDING"

        asyncio.run(
            api_context.job_manager.wait_until_complete(data["job_id"], timeout=10)
        )

    def test_create_training_run_with_documents(self, client: TestClient, api_context: SimpleNamespace):
        """Test creating a training run with specific documents."""
        # First upload a document
        pdf_content = _create_test_pdf()
        upload_response = client.post(
            "/api/pdf-training/documents",
            files={"file": ("test.pdf", pdf_content, "application/pdf")}
        )
        document_id = upload_response.json()["document"]["id"]

        _wait_for_document_jobs(client, api_context, document_id)

        payload = {
            "document_ids": [document_id],
            "triggered_by": "test",
        }
        
        response = client.post("/api/pdf-training/training-runs", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["job_type"] == "TRAINING"
        assert data["status"] == "PENDING"

        asyncio.run(
            api_context.job_manager.wait_until_complete(data["job_id"], timeout=10)
        )


class TestJobEndpoints:
    """Test job-related endpoints."""
    
    def test_list_jobs_empty(self, client: TestClient):
        """Test listing jobs when none exist."""
        response = client.get("/api/pdf-training/jobs")
        assert response.status_code == 200
        data = response.json()
        assert data["jobs"] == []

    def test_get_job_not_found(self, client: TestClient):
        """Test getting a non-existent job."""
        response = client.get("/api/pdf-training/jobs/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "Job not found" in data["detail"]

    def test_job_lifecycle(self, client: TestClient):
        """Test the complete job lifecycle."""
        # Create a training run to generate a job
        payload = {
            "document_ids": [],
            "triggered_by": "test"
        }
        create_response = client.post("/api/pdf-training/training-runs", json=payload)
        job_id = create_response.json()["job_id"]
        
        # List jobs
        list_response = client.get("/api/pdf-training/jobs")
        assert list_response.status_code == 200
        list_data = list_response.json()
        assert len(list_data["jobs"]) == 1
        assert list_data["jobs"][0]["id"] == job_id
        
        # Get specific job
        get_response = client.get(f"/api/pdf-training/jobs/{job_id}")
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["id"] == job_id
        assert get_data["job_type"] == "TRAINING"