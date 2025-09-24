"""Integration tests for the PDF training API endpoints."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from io import BytesIO
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Generator

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_PATH = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
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

    async def _create_schema() -> None:
        async with db_session._engine.begin() as conn:  # type: ignore[attr-defined]
            await conn.run_sync(models.Base.metadata.create_all)

    asyncio.run(_create_schema())

    return SimpleNamespace(
        models=models,
        db_session=db_session,
        api=api,
        services=services,
    )


@pytest.fixture(scope="function")
def api_context() -> Generator[SimpleNamespace, None, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)
        storage_root = base_path / "storage"
        db_path = base_path / "app.db"
        os.environ["PDF_TRAINING_STORAGE_ROOT"] = str(storage_root)
        os.environ["PDF_TRAINING_DB_URL"] = f"sqlite+aiosqlite:///{db_path}"

        ctx = _reload_modules()
        try:
            yield SimpleNamespace(
                **ctx.__dict__,
                base_path=base_path,
                storage_root=storage_root,
            )
        finally:
            asyncio.run(ctx.db_session.close_engine())


@pytest.fixture
def client(api_context: SimpleNamespace) -> TestClient:
    """Create a test client for the API."""
    from server.pdf_training_app import app
    return TestClient(app)


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
        assert data["items"] == []

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
        assert len(data["items"]) == 1
        assert data["items"][0]["filename"] == "test.pdf"

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

<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
    def test_get_document_entities_not_found(self, client: TestClient):
        """Document entities endpoint returns 404 for unknown documents."""
        response = client.get("/api/pdf-training/documents/unknown/entities")
        assert response.status_code == 404

    def test_get_document_entities_success(
        self,
        client: TestClient,
        api_context: SimpleNamespace,
    ) -> None:
        """Entities endpoint returns preprocessed predictions."""

        pdf_content = _create_test_pdf()
        upload_response = client.post(
            "/api/pdf-training/documents",
            files={"file": ("test.pdf", pdf_content, "application/pdf")},
        )
        document_id = upload_response.json()["document"]["id"]

        tasks_path = api_context.storage_root / "analysis" / f"{document_id}_tasks.json"
        tasks_path.parent.mkdir(parents=True, exist_ok=True)
        tasks_payload = [
            {
                "id": 1,
                "data": {
                    "row_id": 1,
                    "po_number_pred": "PO-00001",
                    "amount_pred": "$250.00",
                    "amount_bbox": {"page_num": 2, "bbox": [15, 25, 35, 45]},
                },
            }
        ]
        tasks_path.write_text(json.dumps(tasks_payload), encoding="utf-8")

        async def _seed_extraction() -> None:
            async with api_context.db_session.async_session() as session:
                document = await api_context.services.repository.get_document(session, document_id)
                assert document is not None
                latest_version = max(
                    document.versions,
                    key=lambda version: version.created_at or datetime.min,
                )
                await api_context.services.repository.create_extraction(
                    session,
                    document_version_id=latest_version.id,
                    extractor_name="unit-test",
                    predictions={"tasks_path": str(tasks_path)},
                    confidence_summary=None,
                )
                await session.commit()

        asyncio.run(_seed_extraction())

        response = client.get(
            f"/api/pdf-training/documents/{document_id}/entities"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        entity_map = {item["type"]: item for item in data}
        assert entity_map["PO Number"]["value"] == "PO-00001"
        amount_entity = entity_map["Amount"]
        assert amount_entity["value"] == "$250.00"
        assert amount_entity["location"]["page_num"] == 2
        assert amount_entity["location"]["bbox"] == [15.0, 25.0, 35.0, 45.0]
=======
=======
>>>>>>> theirs
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
<<<<<<< ours
>>>>>>> theirs

=======
>>>>>>> theirs
=======

>>>>>>> theirs
=======
>>>>>>> theirs

class TestAnalysisEndpoints:
    """Test analysis-related endpoints."""
    
    def test_analyze_document_not_found(self, client: TestClient):
        """Test analyzing a non-existent document."""
        response = client.post("/api/pdf-training/documents/nonexistent/analyze")
        assert response.status_code == 404
        data = response.json()
        assert "Document not found" in data["detail"]

    def test_analyze_document_success(self, client: TestClient):
        """Test successful document analysis."""
        # First upload a document
        pdf_content = _create_test_pdf()
        upload_response = client.post(
            "/api/pdf-training/documents",
            files={"file": ("test.pdf", pdf_content, "application/pdf")}
        )
        document_id = upload_response.json()["document"]["id"]
        
        response = client.post(f"/api/pdf-training/documents/{document_id}/analyze")
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["job_type"] == "ANALYSIS"
        assert data["status"] == "PENDING"


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
    
    def test_create_training_run_empty_documents(self, client: TestClient):
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

    def test_create_training_run_with_documents(self, client: TestClient):
        """Test creating a training run with specific documents."""
        # First upload a document
        pdf_content = _create_test_pdf()
        upload_response = client.post(
            "/api/pdf-training/documents",
            files={"file": ("test.pdf", pdf_content, "application/pdf")}
        )
        document_id = upload_response.json()["document"]["id"]
        
        payload = {
            "document_ids": [document_id],
            "triggered_by": "test"
        }
        
        response = client.post("/api/pdf-training/training-runs", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["job_type"] == "TRAINING"
        assert data["status"] == "PENDING"


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