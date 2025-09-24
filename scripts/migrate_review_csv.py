"""Migrate legacy review.csv files into the database-backed workflow."""
from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from glob import glob
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd
import typer

from server.db import repository, models
from server.db.models import AnnotationStatus, TrainingRunStatus
from server.db.session import async_session, close_engine
from server.db.storage import document_blob_path
from tools.feedback_utils import read_review_csv

app = typer.Typer(help="Import historical review.csv annotations into the database.")


CSV_SUFFIXES = ("_pred", "_gold", "_status")


@dataclass
class FieldSnapshot:
    name: str
    predicted: Optional[str]
    gold: Optional[str]
    status: Optional[str]


@dataclass
class RowSummary:
    row_index: int
    document_id: Optional[str]
    outcome: str
    message: Optional[str] = None


@dataclass
class FileSummary:
    path: Path
    status: str
    migrated: int = 0
    skipped: int = 0
    rows: List[RowSummary] = field(default_factory=list)


@dataclass
class MigrationSummary:
    training_run_id: Optional[str]
    files: List[FileSummary]
    total_documents: int
    total_skipped: int


def _is_nan(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except Exception:
        return False


def _coerce_value(value: Any) -> Optional[str]:
    if _is_nan(value):
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _extract_fields(row: pd.Series) -> List[FieldSnapshot]:
    snapshots: Dict[str, FieldSnapshot] = {}
    for column in row.index:
        for suffix in CSV_SUFFIXES:
            if column.endswith(suffix):
                base = column[: -len(suffix)]
                if base not in snapshots:
                    snapshots[base] = FieldSnapshot(name=base, predicted=None, gold=None, status=None)
    for base, snapshot in snapshots.items():
        snapshot.predicted = _coerce_value(row.get(f"{base}_pred"))
        snapshot.gold = _coerce_value(row.get(f"{base}_gold"))
        snapshot.status = _coerce_value(row.get(f"{base}_status"))
    return list(snapshots.values())


def _resolve_annotation_status(fields: Sequence[FieldSnapshot]) -> AnnotationStatus:
    statuses = { (field.status or "").upper() for field in fields if field.status }
    if any(status in {"ACCEPTED", "CORRECTED", "APPROVED", "COMPLETED"} for status in statuses):
        return AnnotationStatus.completed
    if any("REVIEW" in status for status in statuses):
        return AnnotationStatus.in_review
    if any(field.gold for field in fields):
        return AnnotationStatus.completed
    return AnnotationStatus.pending


def _row_metadata(row: pd.Series, csv_path: Path, pdf_source: Optional[Path]) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {
        "source_csv": str(csv_path),
        "row_index": int(row.name),
    }
    if pdf_source:
        metadata["source_pdf"] = str(pdf_source)
    for key, value in row.items():
        coerced = _coerce_value(value)
        if coerced is not None:
            metadata[str(key)] = coerced
    return metadata


def _candidate_pdf_paths(row: pd.Series) -> Sequence[str]:
    keys = [
        "Source File",
        "source_file",
        "pdf_path",
        "document_path",
        "document_name",
    ]
    values: List[str] = []
    for key in keys:
        value = row.get(key)
        coerced = _coerce_value(value)
        if coerced:
            values.append(coerced)
    return values


def _resolve_pdf_path(row: pd.Series, csv_path: Path, pdf_root: Optional[Path]) -> Optional[Path]:
    candidates = _candidate_pdf_paths(row)
    if not candidates:
        return None
    parent = csv_path.parent
    for candidate in candidates:
        candidate_path = Path(candidate)
        if not candidate_path.is_absolute():
            if pdf_root:
                candidate_path = pdf_root / candidate_path
            else:
                candidate_path = parent / candidate_path
        if candidate_path.exists():
            return candidate_path.resolve()
    return None


async def _copy_pdf(document_id: str, source: Path, dry_run: bool) -> tuple[Path, Optional[str], Optional[int]]:
    target = document_blob_path(document_id, source.name)
    if dry_run:
        stat = source.stat()
        return target, None, stat.st_size
    data = await asyncio.to_thread(source.read_bytes)
    await asyncio.to_thread(target.write_bytes, data)
    checksum = hashlib.sha256(data).hexdigest()
    return target, checksum, len(data)


async def _migrate_row(
    session,
    *,
    row: pd.Series,
    csv_path: Path,
    dry_run: bool,
    pdf_root: Optional[Path],
    allow_missing_pdf: bool,
) -> RowSummary:
    fields = _extract_fields(row)
    pdf_path = _resolve_pdf_path(row, csv_path, pdf_root)
    if pdf_path is None and not allow_missing_pdf:
        return RowSummary(row_index=int(row.name), document_id=None, outcome="skipped", message="PDF file not found")

    raw_id = row.get("document_id") or row.get("row_id")
    document_id = str(raw_id) if raw_id else str(uuid.uuid4())

    filename_hint = _coerce_value(row.get("document_name")) or _coerce_value(row.get("Source File"))
    if filename_hint and not filename_hint.lower().endswith(".pdf"):
        filename_hint = f"{filename_hint}.pdf"
    if not filename_hint:
        filename_hint = f"migrated-{csv_path.stem}-{row.name}.pdf"

    storage_path: Path
    checksum: Optional[str]
    size_bytes: Optional[int]
    outcome_message: Optional[str] = None
    if pdf_path is not None:
        storage_path, checksum, size_bytes = await _copy_pdf(document_id, pdf_path, dry_run)
    else:
        storage_path = document_blob_path(document_id, filename_hint)
        checksum = None
        size_bytes = None
        outcome_message = "PDF source missing"

    metadata = _row_metadata(row, csv_path, pdf_path)
    annotation_payload = {
        "fields": [field.__dict__ for field in fields if field.predicted or field.gold],
        "migrated_from": csv_path.name,
    }
    status = _resolve_annotation_status(fields)

    if dry_run:
        return RowSummary(row_index=int(row.name), document_id=document_id, outcome="dry-run", message=outcome_message)

    await repository.create_document(
        session,
        document_id=document_id,
        filename=Path(storage_path).name,
        content_type="application/pdf",
        storage_path=str(storage_path),
        checksum=checksum,
        size_bytes=size_bytes,
        extra_metadata=metadata,
    )
    annotation = await repository.get_annotation_by_document(session, document_id)
    if annotation:
        await repository.update_annotation_status(
            session,
            annotation_id=annotation.id,
            status=status,
            latest_payload=annotation_payload,
        )
    await session.commit()
    return RowSummary(row_index=int(row.name), document_id=document_id, outcome="migrated", message=outcome_message)


async def _migrate_file(
    session,
    *,
    csv_path: Path,
    dry_run: bool,
    pdf_root: Optional[Path],
    allow_missing_pdf: bool,
) -> FileSummary:
    df = read_review_csv(csv_path)
    summary = FileSummary(path=csv_path, status="processed")
    if df.empty:
        summary.status = "skipped_empty"
        return summary

    for index, row in df.iterrows():
        row.name = index  # ensure row index is available for metadata
        result = await _migrate_row(
            session,
            row=row,
            csv_path=csv_path,
            dry_run=dry_run,
            pdf_root=pdf_root,
            allow_missing_pdf=allow_missing_pdf,
        )
        summary.rows.append(result)
        if result.outcome == "migrated":
            summary.migrated += 1
        else:
            summary.skipped += 1
    if any(row.outcome == "skipped" for row in summary.rows):
        summary.status = "partial"
    return summary


async def _run_migration(
    csv_pattern: str,
    training_run_name: str,
    *,
    dry_run: bool,
    report_dir: Optional[Path],
    pdf_root: Optional[Path],
    allow_missing_pdf: bool,
) -> MigrationSummary:
    csv_files = sorted(Path(p) for p in glob(csv_pattern, recursive=True))
    if not csv_files:
        raise typer.Exit(f"No CSV files found for pattern: {csv_pattern}")

    summaries: List[FileSummary] = []
    training_run_id: Optional[str] = None

    async with async_session() as session:
        async with session.bind.begin() as conn:  # type: ignore[union-attr]
            await conn.run_sync(models.Base.metadata.create_all)

    async with async_session() as session:
        if not dry_run:
            training_run_id = uuid.uuid4().hex
            await repository.create_training_run(
                session,
                training_run_id=training_run_id,
                triggered_by="csv-migration",
                parameters={"name": training_run_name, "source_pattern": csv_pattern},
            )
            await session.commit()

        for csv_path in csv_files:
            summary = await _migrate_file(
                session,
                csv_path=csv_path,
                dry_run=dry_run,
                pdf_root=pdf_root,
                allow_missing_pdf=allow_missing_pdf,
            )
            summaries.append(summary)

        if not dry_run and training_run_id:
            seen: Dict[str, None] = {}
            document_ids = []
            for file in summaries:
                for row in file.rows:
                    if row.document_id and row.outcome == "migrated" and row.document_id not in seen:
                        seen[row.document_id] = None
                        document_ids.append(row.document_id)
            await repository.attach_training_documents(
                session,
                training_run_id=training_run_id,
                document_ids=document_ids,
            )
            status = TrainingRunStatus.succeeded if document_ids else TrainingRunStatus.failed
            await repository.set_training_run_status(
                session,
                training_run_id=training_run_id,
                status=status,
                notes=f"Migrated {len(document_ids)} documents from legacy CSV workflow",
                completed_at=datetime.now(timezone.utc),
            )
            await session.commit()

    total_documents = sum(file.migrated for file in summaries)
    total_skipped = sum(file.skipped for file in summaries)

    if report_dir:
        report_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        report_path = report_dir / f"migration-report-{timestamp}.json"
        payload = {
            "training_run_id": training_run_id,
            "files": [
                {
                    "path": str(file.path),
                    "status": file.status,
                    "migrated": file.migrated,
                    "skipped": file.skipped,
                    "rows": [row.__dict__ for row in file.rows],
                }
                for file in summaries
            ],
            "total_documents": total_documents,
            "total_skipped": total_skipped,
        }
        report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        typer.echo(f"Detailed report written to {report_path}")

    return MigrationSummary(
        training_run_id=training_run_id,
        files=summaries,
        total_documents=total_documents,
        total_skipped=total_skipped,
    )


@app.command()
def migrate(
    csv_pattern: str = typer.Argument(..., help="Glob pattern pointing to review.csv files"),
    training_run_name: str = typer.Option(..., "--training-run", help="Name recorded on the training run created during migration"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Analyse the migration without writing to the database"),
    report_dir: Optional[Path] = typer.Option(None, "--report-dir", help="Optional directory for a JSON summary"),
    pdf_root: Optional[Path] = typer.Option(None, "--pdf-root", help="Base directory containing the original PDFs"),
    allow_missing_pdf: bool = typer.Option(False, "--allow-missing-pdf", help="Import rows even when the source PDF cannot be located"),
) -> None:
    """Execute the migration process."""

    summary = asyncio.run(
        _run_migration(
            csv_pattern,
            training_run_name,
            dry_run=dry_run,
            report_dir=report_dir,
            pdf_root=pdf_root,
            allow_missing_pdf=allow_missing_pdf,
        )
    )

    typer.echo("=== Migration summary ===")
    typer.echo(f"Training run id: {summary.training_run_id or 'n/a (dry-run)'}")
    typer.echo(f"Files processed: {len(summary.files)}")
    typer.echo(f"Documents migrated: {summary.total_documents}")
    typer.echo(f"Rows skipped: {summary.total_skipped}")
    for file_summary in summary.files:
        typer.echo(f"- {file_summary.path}: {file_summary.status} (migrated={file_summary.migrated}, skipped={file_summary.skipped})")

    asyncio.run(close_engine())


if __name__ == "__main__":
    app()
