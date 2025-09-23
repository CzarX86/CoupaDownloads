"""Dataset builders for the database-backed training pipeline."""
from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from server.db.models import Annotation, AnnotationStatus, TrainingRun
from server.pdf_training_app.fields import (
    ALLOWED_STATUSES,
    CATEGORICAL_ST_FIELDS,
    METADATA_COLUMNS,
    NORMALIZED_TO_PRETTY,
    normalized_to_pretty,
)


@dataclass
class FieldSlice:
    normalized: str
    prediction: str
    gold: str
    status: str
    pretty: str


@dataclass
class ReviewRow:
    annotation_id: str
    document_id: str
    row_id: str
    source_file: str
    annotator: str
    notes: str
    timestamp: str
    document_filename: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    fields: Dict[str, FieldSlice] = field(default_factory=dict)


@dataclass
class DatasetBundle:
    training_run_id: str
    training_run: TrainingRun
    rows: List[ReviewRow]
    dataframe: pd.DataFrame
    supervised_records: List[Dict[str, Any]]
    st_pairs: List[Dict[str, Any]]
    summary: Dict[str, Any]
    empty_annotations: List[str]


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    return str(value).strip()


def _normalize_status(value: Any) -> str:
    status = _as_text(value).upper()
    if status in ALLOWED_STATUSES:
        return status
    return ""


def _ensure_field(container: Dict[str, FieldSlice], normalized: str) -> FieldSlice:
    if normalized not in container:
        pretty = normalized_to_pretty(normalized)
        container[normalized] = FieldSlice(
            normalized=normalized,
            prediction="",
            gold="",
            status="",
            pretty=pretty,
        )
    return container[normalized]


def _extract_rows_from_annotation(annotation: Annotation) -> List[ReviewRow]:
    payload = annotation.latest_payload or []
    if isinstance(payload, dict):
        payload = [payload]
    rows: List[ReviewRow] = []

    for idx, task in enumerate(payload):
        if not isinstance(task, dict):
            continue
        data = task.get("data") or {}
        if not isinstance(data, dict):
            continue
        row_id_raw = data.get("row_id") or data.get("row") or data.get("id")
        row_index = data.get("row_index")
        row_id = _as_text(row_id_raw)
        if not row_id:
            numeric_idx = None
            text_index = _as_text(row_index)
            if text_index.isdigit():
                numeric_idx = text_index
            else:
                numeric_idx = str(idx + 1)
            row_id = numeric_idx
        annotator = _as_text(data.get("annotator"))
        notes = _as_text(data.get("notes"))
        timestamp = _as_text(data.get("timestamp"))
        source_file = _as_text(data.get("source_file"))
        metadata = {col: _as_text(data.get(col)) for col in METADATA_COLUMNS}
        metadata["document_checksum"] = _as_text(annotation.document.checksum)
        metadata["document_content_type"] = _as_text(annotation.document.content_type)
        metadata["document_extra"] = annotation.document.extra_metadata or {}

        fields: Dict[str, FieldSlice] = {}
        for key, value in data.items():
            if not isinstance(key, str) or not key.endswith("_pred"):
                continue
            normalized = key[:-5]
            field_slice = _ensure_field(fields, normalized)
            field_slice.prediction = _as_text(value)
            existing_gold = _as_text(data.get(f"{normalized}_gold"))
            existing_status = _normalize_status(data.get(f"{normalized}_status"))
            if existing_gold and not field_slice.gold:
                field_slice.gold = existing_gold
            if existing_status and not field_slice.status:
                field_slice.status = existing_status

        latest_annotation = None
        annotations = task.get("annotations")
        if isinstance(annotations, list):
            for ann in reversed(annotations):
                if ann and isinstance(ann, dict) and ann.get("result"):
                    latest_annotation = ann
                    break
        if latest_annotation:
            results = latest_annotation.get("result")
            if isinstance(results, list):
                for result in results:
                    if not isinstance(result, dict):
                        continue
                    from_name = result.get("from_name")
                    value = result.get("value") or {}
                    if not isinstance(value, dict):
                        continue
                    if isinstance(from_name, str) and from_name.endswith("_gold"):
                        normalized = from_name[:-5]
                        field_slice = _ensure_field(fields, normalized)
                        texts = value.get("text") or []
                        text_value = "\n".join(
                            _as_text(item) for item in texts if isinstance(item, (str, int, float))
                        ).strip()
                        if text_value:
                            field_slice.gold = text_value
                    elif isinstance(from_name, str) and from_name.endswith("_status"):
                        normalized = from_name[:-7]
                        field_slice = _ensure_field(fields, normalized)
                        choices = value.get("choices") or []
                        choice = ""
                        for candidate in choices:
                            candidate_text = _as_text(candidate).upper()
                            if candidate_text:
                                choice = candidate_text
                                break
                        status = _normalize_status(choice)
                        if status:
                            field_slice.status = status
                    elif from_name == "notes":
                        texts = value.get("text") or []
                        text_value = "\n".join(
                            _as_text(item) for item in texts if isinstance(item, (str, int, float))
                        ).strip()
                        if text_value:
                            notes = text_value
                    elif from_name == "annotator":
                        texts = value.get("text") or []
                        text_value = "\n".join(
                            _as_text(item) for item in texts if isinstance(item, (str, int, float))
                        ).strip()
                        if text_value:
                            annotator = text_value

        if not fields:
            continue
        row = ReviewRow(
            annotation_id=annotation.id,
            document_id=annotation.document_id,
            row_id=row_id,
            source_file=source_file,
            annotator=annotator,
            notes=notes,
            timestamp=timestamp,
            document_filename=_as_text(annotation.document.filename),
            metadata=metadata,
            fields=fields,
        )
        rows.append(row)
    return rows


async def _load_training_run(session: AsyncSession, training_run_id: str) -> TrainingRun:
    stmt = (
        select(TrainingRun)
        .where(TrainingRun.id == training_run_id)
        .options(
            selectinload(TrainingRun.documents),
            selectinload(TrainingRun.metrics),
            selectinload(TrainingRun.model_version),
        )
    )
    result = await session.execute(stmt)
    training_run = result.scalars().unique().first()
    if not training_run:
        raise ValueError(f"Training run not found: {training_run_id}")
    return training_run


async def _load_completed_annotations(
    session: AsyncSession, *, document_ids: Optional[Iterable[str]]
) -> Sequence[Annotation]:
    stmt = (
        select(Annotation)
        .where(Annotation.status == AnnotationStatus.completed)
        .options(
            selectinload(Annotation.document),
            selectinload(Annotation.events),
            selectinload(Annotation.source_extraction),
        )
        .order_by(Annotation.updated_at.desc())
    )
    if document_ids:
        stmt = stmt.where(Annotation.document_id.in_(list(document_ids)))
    result = await session.execute(stmt)
    return result.scalars().unique().all()


def _rows_to_dataframe(rows: List[ReviewRow]) -> pd.DataFrame:
    records: List[Dict[str, Any]] = []
    for row in rows:
        base: Dict[str, Any] = {
            "annotation_id": row.annotation_id,
            "document_id": row.document_id,
            "row_id": row.row_id,
            "Source File": row.source_file,
            "annotator": row.annotator,
            "notes": row.notes,
            "timestamp": row.timestamp,
            "document_filename": row.document_filename,
        }
        base.update(row.metadata)
        for normalized, field_slice in sorted(row.fields.items()):
            pretty = NORMALIZED_TO_PRETTY.get(normalized, field_slice.pretty)
            base[f"{pretty}_pred"] = field_slice.prediction
            base[f"{pretty}_gold"] = field_slice.gold
            base[f"{pretty}_status"] = field_slice.status
        records.append(base)
    if not records:
        return pd.DataFrame()
    return pd.DataFrame.from_records(records)


def _build_supervised(records: List[ReviewRow]) -> List[Dict[str, Any]]:
    supervised: List[Dict[str, Any]] = []
    for row in records:
        labels: Dict[str, str] = {}
        statuses: Dict[str, str] = {}
        predictions: Dict[str, str] = {}
        for normalized, field_slice in row.fields.items():
            if field_slice.gold:
                labels[normalized] = field_slice.gold
            if field_slice.status:
                statuses[normalized] = field_slice.status
            if field_slice.prediction:
                predictions[normalized] = field_slice.prediction
        if not labels:
            continue
        meta = dict(row.metadata)
        meta.update(
            {
                "annotator": row.annotator,
                "notes": row.notes,
                "timestamp": row.timestamp,
                "document_filename": row.document_filename,
            }
        )
        supervised.append(
            {
                "annotation_id": row.annotation_id,
                "document_id": row.document_id,
                "row_id": row.row_id,
                "source_file": row.source_file,
                "labels": labels,
                "statuses": statuses,
                "predictions": predictions,
                "metadata": meta,
            }
        )
    return supervised


def _build_st_pairs(records: List[ReviewRow]) -> List[Dict[str, Any]]:
    values: Dict[str, List[str]] = {field: [] for field in CATEGORICAL_ST_FIELDS}
    for row in records:
        for field in CATEGORICAL_ST_FIELDS:
            field_slice = row.fields.get(field)
            if field_slice and field_slice.gold:
                values[field].append(field_slice.gold)
    rnd = random.Random(42)
    pairs: List[Dict[str, Any]] = []
    for field, items in values.items():
        if not items:
            continue
        uniques = list({item for item in items})
        # Positive/negative sampling with a fixed cap for determinism
        for _ in range(min(50, len(items))):
            left = rnd.choice(items)
            right = rnd.choice(items)
            label = 1.0 if left == right else 0.0
            pairs.append({"text1": left, "text2": right, "label": label, "field": field})
        if len(uniques) >= 2:
            for _ in range(min(50, len(uniques))):
                left, right = rnd.sample(uniques, 2)
                pairs.append({"text1": left, "text2": right, "label": 0.0, "field": field})
    return pairs


def _summarize(rows: List[ReviewRow], empty_annotations: List[str]) -> Dict[str, Any]:
    field_counter: Counter[str] = Counter()
    status_counter: Counter[str] = Counter()
    documents = {row.document_id for row in rows}
    annotations = {row.annotation_id for row in rows}
    for row in rows:
        for field_slice in row.fields.values():
            field_counter[field_slice.normalized] += 1
            if field_slice.status:
                status_counter[field_slice.status] += 1
    return {
        "rows": len(rows),
        "documents": len(documents),
        "annotations": len(annotations),
        "fields": dict(field_counter),
        "statuses": dict(status_counter),
        "annotations_without_payload": empty_annotations,
    }


async def build_dataset_bundle(
    session: AsyncSession, training_run_id: str
) -> DatasetBundle:
    training_run = await _load_training_run(session, training_run_id)
    document_ids = [doc.id for doc in training_run.documents]
    annotations = await _load_completed_annotations(
        session, document_ids=document_ids or None
    )

    rows: List[ReviewRow] = []
    empty_annotations: List[str] = []
    for annotation in annotations:
        parsed_rows = _extract_rows_from_annotation(annotation)
        if not parsed_rows:
            empty_annotations.append(annotation.id)
            continue
        rows.extend(parsed_rows)

    dataframe = _rows_to_dataframe(rows)
    supervised_records = _build_supervised(rows)
    st_pairs = _build_st_pairs(rows)
    summary = _summarize(rows, empty_annotations)

    return DatasetBundle(
        training_run_id=training_run_id,
        training_run=training_run,
        rows=rows,
        dataframe=dataframe,
        supervised_records=supervised_records,
        st_pairs=st_pairs,
        summary=summary,
        empty_annotations=empty_annotations,
    )
