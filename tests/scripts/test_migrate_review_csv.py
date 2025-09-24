from __future__ import annotations

import importlib
import os
import sys
import asyncio
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _reload_modules() -> None:
    for name in list(sys.modules):
        if name.startswith("server.db") or name.startswith("scripts.migrate_review_csv"):
            sys.modules.pop(name)


def _write_sample_csv(csv_path: Path, pdf_name: str) -> None:
    df = pd.DataFrame(
        [
            {
                "row_id": 1,
                "Source File": pdf_name,
                "document_name": "contract.pdf",
                "contract_name_pred": "ACME Corp",
                "contract_name_gold": "ACME Corporation",
                "contract_name_status": "CORRECTED",
                "notes": "Migrated row",
            }
        ]
    )
    df.to_csv(csv_path, index=False)


@pytest.fixture()
def runner(tmp_path, monkeypatch):
    monkeypatch.setenv("PDF_TRAINING_DB_URL", f"sqlite+aiosqlite:///{tmp_path/'app.db'}")
    monkeypatch.setenv("PDF_TRAINING_STORAGE_ROOT", str(tmp_path/'storage'))
    _reload_modules()
    module = importlib.import_module("scripts.migrate_review_csv")
    return CliRunner(), module


def test_dry_run_reports_summary(tmp_path, runner):
    cli, module = runner
    pdf_path = tmp_path / "source.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF")
    csv_path = tmp_path / "review.csv"
    _write_sample_csv(csv_path, pdf_path.name)

    result = cli.invoke(
        module.app,
        [
            str(csv_path),
            "--training-run",
            "legacy-import",
            "--dry-run",
            "--pdf-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Documents migrated: 0" in result.stdout
    assert "dry-run" in result.stdout


def test_commit_creates_documents(tmp_path, runner):
    cli, module = runner
    pdf_path = tmp_path / "source.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF")
    csv_path = tmp_path / "review.csv"
    _write_sample_csv(csv_path, pdf_path.name)

    result = cli.invoke(
        module.app,
        [
            str(csv_path),
            "--training-run",
            "legacy-import",
            "--pdf-root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert "Documents migrated: 1" in result.stdout

    from sqlalchemy import select

    from server.db import repository
    from server.db.models import TrainingRun
    from server.db.session import async_session, close_engine

    async def _assertions() -> None:
        async with async_session() as session:
            documents = await repository.list_documents(session)
            assert len(documents) == 1
            document = documents[0]
            assert Path(document.storage_path).exists()
            annotation = document.annotations[0]
            assert annotation.status.value == "COMPLETED"
            assert annotation.latest_payload["fields"]

            run_result = await session.execute(select(TrainingRun))
            training_runs = run_result.scalars().all()
            assert training_runs
            run = training_runs[0]
            assert run.status.value == "SUCCEEDED"

    asyncio.run(_assertions())
    asyncio.run(close_engine())
