"""Utilities to manage session storage for the PDF training workflow."""
from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from fastapi import UploadFile

from tools.feedback_utils import read_review_csv, write_review_csv

from .models import SessionInfo

BASE_DIR = Path("storage/pdf_training").resolve()


def _session_dir(session_id: str) -> Path:
    return BASE_DIR / session_id


def init_storage() -> None:
    BASE_DIR.mkdir(parents=True, exist_ok=True)


def create_session() -> SessionInfo:
    session_id = uuid.uuid4().hex
    created_at = datetime.utcnow()
    info = SessionInfo(session_id=session_id, created_at=created_at)
    path = _session_dir(session_id)
    path.mkdir(parents=True, exist_ok=True)
    _write_session(info)
    return info


def store_review_csv(session: SessionInfo, file: UploadFile) -> SessionInfo:
    target_dir = _session_dir(session.session_id) / "raw"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_csv = target_dir / "review.csv"
    content = file.file.read()
    target_csv.write_bytes(content)
    session.review_csv = str(target_csv)
    session.stage = "analyze"
    _write_session(session)
    return session


def store_pdfs(session: SessionInfo, files: Iterable[UploadFile]) -> SessionInfo:
    target_dir = _session_dir(session.session_id) / "pdfs"
    target_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for up in files:
        if not up.filename:
            continue
        dest = target_dir / up.filename
        dest.write_bytes(up.file.read())
        count += 1
    if count:
        session.pdf_root = str(target_dir)
        _write_session(session)
    return session


def load_session(session_id: str) -> Optional[SessionInfo]:
    meta_path = _session_dir(session_id) / "session.json"
    if not meta_path.exists():
        return None
    data = json.loads(meta_path.read_text(encoding="utf-8"))
    data["created_at"] = datetime.fromisoformat(data["created_at"])
    return SessionInfo(**data)


def update_session(session: SessionInfo, **updates: str) -> SessionInfo:
    for key, value in updates.items():
        setattr(session, key, value)
    _write_session(session)
    return session


def _write_session(session: SessionInfo) -> None:
    payload = session.model_dump()
    payload["created_at"] = session.created_at.isoformat()
    meta_path = _session_dir(session.session_id) / "session.json"
    meta_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def copy_review_to_stage(session: SessionInfo, stage: str) -> Path:
    base = _session_dir(session.session_id)
    review_path = Path(session.review_csv)
    target_dir = base / stage
    target_dir.mkdir(parents=True, exist_ok=True)
    target_csv = target_dir / review_path.name
    shutil.copy2(review_path, target_csv)
    return target_csv


def save_review_dataframe(session: SessionInfo, df_path: Path, stage: str) -> Path:
    base = _session_dir(session.session_id)
    target_dir = base / stage
    target_dir.mkdir(parents=True, exist_ok=True)
    target_csv = target_dir / df_path.name
    shutil.copy2(df_path, target_csv)
    session.stage = stage
    session.review_csv = str(target_csv)
    update_session(session)
    return target_csv


def record_annotation_project(session: SessionInfo, manifest_path: Path) -> SessionInfo:
    session.annotation_project = str(manifest_path)
    session.stage = "review"
    return update_session(session)


def record_annotated_csv(session: SessionInfo, annotated_csv: Path, warnings: Optional[List[str]] = None) -> SessionInfo:
    session.annotated_csv = str(annotated_csv)
    session.stage = "retrain"
    session.last_warnings = warnings or []
    return update_session(session)


def record_model_artifacts(session: SessionInfo, model_dir: Path, metrics_path: Optional[Path]) -> SessionInfo:
    session.model_output_dir = str(model_dir)
    session.metrics_path = str(metrics_path) if metrics_path else None
    session.stage = "complete"
    return update_session(session)
