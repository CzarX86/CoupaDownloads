"""Integration-style tests for the PDF training backend services."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_PATH = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

import pytest
from starlette.datastructures import Headers, UploadFile


def _reload_modules() -> SimpleNamespace:
    """Reload server modules after tweaking environment variables."""

    for name in list(sys.modules):
        if name.startswith("server.db") or name.startswith("server.pdf_training_app"):
            sys.modules.pop(name)

    from server.db import models
    from server.db import repository
    from server.db import session as db_session
    from server.pdf_training_app import jobs as jobs_module
    from server.pdf_training_app import services

    async def _create_schema() -> None:
        async with db_session._engine.begin() as conn:  # type: ignore[attr-defined]
            await conn.run_sync(models.Base.metadata.create_all)

    asyncio.run(_create_schema())

    return SimpleNamespace(
        models=models,
        repository=repository,
        db_session=db_session,
        services=services,
        job_manager=jobs_module.job_manager,
    )


@pytest.fixture(scope="module")
def service_context() -> SimpleNamespace:
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


def _make_upload_file(content: bytes, filename: str, content_type: str) -> UploadFile:
    headers = Headers({"content-type": content_type})
    return UploadFile(file=BytesIO(content), filename=filename, headers=headers)


def _build_export_payload(tasks: List[Dict[str, object]]) -> List[Dict[str, object]]:
    first_task = tasks[0]
    data = first_task.get("data", {})
    row_id = data.get("row_id", 1)
    return [
        {
            "data": data,
            "annotations": [
                {
                    "result": [
                        {
                            "from_name": "contract_name_gold",
                            "value": {"text": ["Updated contract name"]},
                        },
                        {
                            "from_name": "contract_name_status",
                            "value": {"choices": ["CORRECTED"]},
                        },
                    ]
                }
            ],
            "id": row_id,
        }
    ]


@pytest.mark.asyncio
async def test_dataset_builder(service_context: SimpleNamespace) -> None:
    repository = service_context.repository
    services = service_context.services
    models = service_context.models

    async with service_context.db_session.async_session() as session:
        doc = await repository.create_document(
            session,
            document_id="doc1",
            filename="test.pdf",
            content_type="application/pdf",
            storage_path="/test/path",
            checksum="abc",
            size_bytes=123,
            extra_metadata={},
        )
        annotation = await repository.get_annotation_by_document(session, "doc1")
        await repository.update_annotation_status(
            session,
            annotation_id=annotation.id,
            status=models.AnnotationStatus.completed,
            latest_payload={"field": "value"},
        )
        await session.commit()

    async with service_context.db_session.async_session() as session:
        builder = services.datasets.DatasetBuilder(session)
        records = await builder.build_from_annotations()

    assert len(records) == 1
    assert records[0]["document_id"] == "doc1"
    assert records[0]["payload"] == {"field": "value"}


@pytest.mark.asyncio
async def test_document_flow_end_to_end(service_context: SimpleNamespace) -> None:
    services = service_context.services
    job_manager = service_context.job_manager
    repository = service_context.repository

    upload = _make_upload_file(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n", "sample.pdf", "application/pdf")
    document_detail = await services.create_document(upload, {"ingested_by": "test"})

    assert document_detail.document.filename == "sample.pdf"
    version_path = Path(document_detail.versions[0].source_storage_path)
    assert version_path.exists()

    analysis_job = await services.start_analysis(document_detail.document.id)
    assert analysis_job.job_type == "ANALYSIS"

    completed_analysis = await job_manager.wait_until_complete(analysis_job.job_id, timeout=5)
    assert completed_analysis.status == "SUCCEEDED"
    analysis_payload = completed_analysis.payload or {}
    analysis_info = analysis_payload.get("analysis") or {}
    tasks_path = Path(analysis_info.get("tasks_path"))
    assert tasks_path.exists()
    config_path = Path(analysis_info.get("config"))
    assert config_path.exists()

    tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
    export_payload = _build_export_payload(tasks)
    export_upload = _make_upload_file(
        json.dumps(export_payload).encode("utf-8"),
        "export.json",
        "application/json",
    )

    annotation_detail = await services.ingest_annotation_export(
        document_detail.document.id,
        export_upload,
    )
    assert annotation_detail.status == "COMPLETED"

    training_job = await services.create_training_run(
        [document_detail.document.id],
        triggered_by="test-suite",
    )
    assert training_job.job_type == "TRAINING"

    completed_training = await job_manager.wait_until_complete(training_job.job_id, timeout=5)
    assert completed_training.status == "SUCCEEDED"
    training_payload = completed_training.payload or {}
    model_artifact = Path(training_payload.get("model_artifact_path"))
    assert model_artifact.exists()

    training_run_id = training_payload.get("training_run_id")
    async with service_context.db_session.async_session() as session:
        document = await repository.get_document(session, document_detail.document.id)
        assert document is not None
        annotation = document.annotations[0]
        assert annotation.status.value == "COMPLETED"
        run = await session.get(service_context.models.TrainingRun, training_run_id)
        assert run is not None and run.status.value == "SUCCEEDED"

    documents = await services.list_documents()
    assert any(doc.id == document_detail.document.id and doc.status == "COMPLETED" for doc in documents)

    jobs = await services.list_jobs()
    job_types = {job.job_type for job in jobs}
    assert {"ANALYSIS", "TRAINING"}.issubset(job_types)


@pytest.mark.asyncio
async def test_get_document_entities_returns_predictions(service_context: SimpleNamespace) -> None:
    services = service_context.services
    job_manager = service_context.job_manager

    upload = _make_upload_file(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n", "entities.pdf", "application/pdf")
    document_detail = await services.create_document(upload, {"ingested_by": "entities-test"})

    analysis_job = await services.start_analysis(document_detail.document.id)
    completed_analysis = await job_manager.wait_until_complete(analysis_job.job_id, timeout=5)
    analysis_payload = completed_analysis.payload or {}
    analysis_info = analysis_payload.get("analysis") or {}
    tasks_path_str = analysis_info.get("tasks_path")
    assert tasks_path_str, "Expected analysis to provide a tasks.json path"
    tasks_path = Path(tasks_path_str)

    tasks_payload = [
        {
            "id": 1,
            "data": {
                "row_id": 1,
                "po_number_pred": "PO-99999",
                "amount_pred": "$123.45",
                "amount_bbox": {"page_num": 1, "bbox": [10, 20, 30, 40]},
            },
        }
    ]
    tasks_path.write_text(json.dumps(tasks_payload), encoding="utf-8")

    entities = await services.get_document_entities(document_detail.document.id)
    assert len(entities) == 2
    entity_map = {entity.type: entity for entity in entities}
    assert entity_map["PO Number"].value == "PO-99999"
    amount_entity = entity_map["Amount"]
    assert amount_entity.value == "$123.45"
    assert amount_entity.location is not None
    assert amount_entity.location.page_num == 1
    assert amount_entity.location.bbox == [10.0, 20.0, 30.0, 40.0]
