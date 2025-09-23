"""Filesystem helpers for blob storage referenced by the database."""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_BLOB_SUBDIR = "blobs"
_STORAGE_ROOT_ENV = "PDF_TRAINING_STORAGE_ROOT"


def _resolve_storage_root() -> Path:
    custom_root = os.getenv(_STORAGE_ROOT_ENV)
    if custom_root:
        return Path(custom_root).resolve()
    return Path("storage/pdf_training").resolve()


def storage_root() -> Path:
    root = _resolve_storage_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def blobs_root() -> Path:
    root = storage_root() / DEFAULT_BLOB_SUBDIR
    root.mkdir(parents=True, exist_ok=True)
    return root


def document_blob_dir(document_id: str) -> Path:
    doc_dir = blobs_root() / "documents" / document_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    return doc_dir


def document_blob_path(document_id: str, filename: str) -> Path:
    return document_blob_dir(document_id) / filename


def annotation_assets_dir(annotation_id: str) -> Path:
    ann_dir = blobs_root() / "annotations" / annotation_id
    ann_dir.mkdir(parents=True, exist_ok=True)
    return ann_dir


def annotation_analysis_dir(annotation_id: str) -> Path:
    analysis_dir = annotation_assets_dir(annotation_id) / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    return analysis_dir


def annotation_blob_path(annotation_id: str, suffix: str = "json") -> Path:
    return annotation_assets_dir(annotation_id) / f"export.{suffix}"


def training_run_blob_path(training_run_id: str, filename: str) -> Path:
    run_dir = blobs_root() / "training_runs" / training_run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir / filename


def model_blob_path(training_run_id: str, filename: str = "model.bin") -> Path:
    return training_run_blob_path(training_run_id, filename)
