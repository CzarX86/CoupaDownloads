#!/usr/bin/env python3
"""Utilities for bridging `review.csv` with Label Studio PDF annotation projects."""
from __future__ import annotations

import html
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import pandas as pd

from server.pdf_training_app.fields import (
    ALLOWED_STATUSES,
    METADATA_COLUMNS,
    PRETTY_TO_NORMALIZED,
)
from tools.feedback_utils import (
    read_review_csv,
    write_review_csv,
)

METADATA_COLS = METADATA_COLUMNS

try:  # Optional dependency – only needed for thumbnails
    import fitz  # type: ignore
except ImportError:  # pragma: no cover - handled at runtime
    fitz = None  # type: ignore

_STATUS_ORDER = ["OK", "CORRECTED", "NEW", "MISSING", "REJECTED"]


@dataclass
class FieldSpec:
    pretty: str
    normalized: str
    pred_col: str
    gold_col: str
    status_col: str


def _slugify(label: str) -> str:
    slug = re.sub(r"[^0-9a-zA-Z]+", "_", label.strip().lower())
    slug = slug.strip("_")
    return slug or "field"


def _safe_text(value: object) -> str:
    if isinstance(value, float) and pd.isna(value):
        return ""
    if value is None:
        return ""
    text = str(value)
    return text.strip()


def _format_html_value(value: str) -> str:
    if not value:
        return "<em>—</em>"
    return html.escape(value).replace("\n", "<br/>")


def _normalize_status(value: str) -> str:
    candidate = _safe_text(value).upper()
    if candidate in ALLOWED_STATUSES:
        return candidate
    return ""


def _row_label(df: pd.DataFrame, row_idx: int) -> str:
    if "row_id" in df.columns:
        rid = _safe_text(df.at[row_idx, "row_id"])
        if rid:
            return rid
    return str(row_idx + 1)


def _resolve_row_id(raw: object, fallback_index: int) -> int:
    text = _safe_text(raw)
    if not text:
        return fallback_index + 1
    try:
        return int(float(text))
    except ValueError:
        return fallback_index + 1


def _resolve_pdf_path(
    source_file: str,
    pdf_root: Optional[Path],
    cache: Dict[str, Optional[Path]],
) -> Optional[Path]:
    if not source_file:
        return None
    if source_file in cache:
        return cache[source_file]
    if not pdf_root:
        cache[source_file] = None
        return None
    direct = pdf_root / source_file
    if direct.exists():
        cache[source_file] = direct
        return direct
    try:
        match = next(pdf_root.rglob(source_file))
        cache[source_file] = match
        return match
    except StopIteration:
        cache[source_file] = None
        return None


def _export_thumbnail(pdf_path: Path, dest_path: Path) -> Tuple[Optional[Path], Optional[int]]:
    if fitz is None:
        return None, None
    try:
        with fitz.open(pdf_path) as doc:  # type: ignore[attr-defined]
            page_count = doc.page_count
            if page_count == 0:
                return None, page_count
            page = doc.load_page(0)
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            pix.save(dest_path)
            return dest_path, page_count
    except Exception:
        return None, None
    return None, None


def _build_field_specs(df: pd.DataFrame) -> List[FieldSpec]:
    specs: List[FieldSpec] = []
    used_norms: Dict[str, int] = {}
    for col in df.columns:
        if not col.endswith("_pred"):
            continue
        pretty = col[:-5]
        normalized = PRETTY_TO_NORMALIZED.get(pretty, _slugify(pretty))
        base = normalized
        counter = used_norms.get(base, 0)
        if counter:
            normalized = f"{base}_{counter + 1}"
        used_norms[base] = counter + 1
        gold_col = f"{pretty}_gold"
        status_col = f"{pretty}_status"
        if gold_col not in df.columns:
            df[gold_col] = ""
        if status_col not in df.columns:
            df[status_col] = ""
        specs.append(
            FieldSpec(
                pretty=pretty,
                normalized=normalized,
                pred_col=col,
                gold_col=gold_col,
                status_col=status_col,
            )
        )
    specs.sort(key=lambda item: item.pretty.lower())
    return specs


def _build_meta_html(
    row: pd.Series,
    pdf_display: str,
    page_count: Optional[int],
) -> str:
    items: List[str] = []
    row_id = _safe_text(row.get("row_id"))
    if row_id:
        items.append(f"<li><strong>row_id</strong>: {_format_html_value(row_id)}</li>")
    items.append(f"<li><strong>PDF</strong>: {_format_html_value(pdf_display)}</li>")
    if page_count is not None:
        items.append(f"<li><strong>Pages</strong>: {_format_html_value(str(page_count))}</li>")
    for col in METADATA_COLS:
        val = _safe_text(row.get(col, ""))
        if val:
            items.append(f"<li><strong>{html.escape(col)}</strong>: {_format_html_value(val)}</li>")
    if not items:
        items.append("<li><em>No metadata available</em></li>")
    return "<div class=\"meta-block\"><h4>Document details</h4><ul>" + "".join(items) + "</ul></div>"


def _build_labelstudio_config(fields: Iterable[FieldSpec]) -> str:
    status_choices = "".join(f"      <Choice value=\"{choice}\"/>\n" for choice in _STATUS_ORDER)
    field_blocks: List[str] = []
    for spec in fields:
        pretty = html.escape(spec.pretty)
        pred_value = f"${spec.normalized}_pred"
        gold_value = f"${spec.normalized}_gold"
        status_original = f"${spec.normalized}_status_original"
        block = f"""
  <View className=\"field-block\">
    <Header value=\"{pretty}\"/>
    <Text name=\"{spec.normalized}_prediction\" value=\"Prediction: {pred_value}\"/>
    <TextArea name=\"{spec.normalized}_gold\" value=\"{gold_value}\" label=\"Corrected value\" maxSubmissions=\"1\"/>
    <Text name=\"{spec.normalized}_status_hint\" value=\"Original status: {status_original}\"/>
    <Choices name=\"{spec.normalized}_status\" choice=\"single\" showInLine=\"true\">
{status_choices}    </Choices>
  </View>"""
        field_blocks.append(block)
    blocks = "\n".join(field_blocks)
    return f"""<View>
  <Style><![CDATA[
    .meta-block {{ margin-bottom: 16px; }}
    .field-block {{
      border: 1px solid #d0d7de;
      padding: 12px;
      margin-bottom: 16px;
      border-radius: 8px;
      background: #fefefe;
    }}
    .field-block Header {{ margin-bottom: 8px; }}
  ]]></Style>
  <Header value=\"PDF annotation workflow\"/>
  <Image name=\"preview\" value=\"$thumbnail\" zoom=\"true\"/>
  <Text name=\"pdf_location\" value=\"PDF copy: $pdf_display\"/>
  <HyperText name=\"meta\" value=\"$meta_html\"/>
{blocks}
  <View className=\"field-block\">
    <Header value=\"Reviewer notes\"/>
    <TextArea name=\"notes\" value=\"$notes\" rows=\"3\"/>
  </View>
  <View className=\"field-block\">
    <Header value=\"Annotator\"/>
    <TextArea name=\"annotator\" value=\"$annotator\" rows=\"1\"/>
    <Text name=\"timestamp\" value=\"Last update: $timestamp\"/>
  </View>
</View>
"""


def _ensure_columns(df: pd.DataFrame, columns: Iterable[str]) -> None:
    for col in columns:
        if col not in df.columns:
            df[col] = ""


def prepare_pdf_annotation_project(
    review_csv: str | Path,
    out_dir: str | Path,
    pdf_root: str | Path | None = None,
) -> Dict[str, object]:
    df = read_review_csv(review_csv)
    specs = _build_field_specs(df)

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    pdf_root_path = Path(pdf_root).resolve() if pdf_root else None

    pdf_dir = out_path / "pdfs"
    thumb_dir = out_path / "thumbnails"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    thumb_dir.mkdir(parents=True, exist_ok=True)

    pdf_cache: Dict[str, Optional[Path]] = {}
    copied_map: Dict[str, Path] = {}
    missing_sources: set[str] = set()
    tasks: List[Dict[str, object]] = []

    for idx, row in df.iterrows():
        row_id = _resolve_row_id(row.get("row_id"), idx)
        source_file = _safe_text(row.get("Source File"))
        pdf_path = _resolve_pdf_path(source_file, pdf_root_path, pdf_cache)
        pdf_display = ""
        page_count: Optional[int] = None
        thumbnail_rel = ""

        if pdf_path:
            key = str(pdf_path.resolve())
            if key in copied_map:
                local_pdf = copied_map[key]
            else:
                local_pdf = pdf_dir / f"{len(copied_map) + 1:04d}_{pdf_path.name}"
                local_pdf.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(pdf_path, local_pdf)
                copied_map[key] = local_pdf
            pdf_display = str(local_pdf.relative_to(out_path))
            thumb_target = thumb_dir / (local_pdf.stem + ".png")
            thumb_path, page_count = _export_thumbnail(local_pdf, thumb_target)
            if thumb_path:
                thumbnail_rel = str(thumb_path.relative_to(out_path))
        else:
            missing_sources.add(source_file)
            pdf_display = "(not found)"

        meta_html = _build_meta_html(row, pdf_display, page_count)
        data: Dict[str, object] = {
            "row_id": row_id,
            "row_index": idx,
            "source_file": source_file,
            "pdf_display": pdf_display,
            "thumbnail": thumbnail_rel,
            "meta_html": meta_html,
            "annotator": _safe_text(row.get("annotator")),
            "notes": _safe_text(row.get("notes")),
            "timestamp": _safe_text(row.get("timestamp")),
        }

        for spec in specs:
            pred_val = _safe_text(row.get(spec.pred_col))
            gold_val = _safe_text(row.get(spec.gold_col)) or pred_val
            status_val = _safe_text(row.get(spec.status_col))
            data[f"{spec.normalized}_pred"] = pred_val
            data[f"{spec.normalized}_gold"] = gold_val
            data[f"{spec.normalized}_status"] = _normalize_status(status_val) or ""
            data[f"{spec.normalized}_status_original"] = status_val or ""
        tasks.append({"id": row_id, "data": data})

    config_path = out_path / "config.xml"
    config_path.write_text(_build_labelstudio_config(specs), encoding="utf-8")

    tasks_path = out_path / "tasks.json"
    tasks_path.write_text(
        json.dumps(tasks, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    readme_path = out_path / "README.md"
    readme_content = (
        "# PDF annotation quickstart\n\n"
        "1. Ensure dependencies are installed: `poetry install` (ou `pip install label-studio-sdk pymupdf`).\n"
        "2. Start Label Studio locally (`label-studio start`).\n"
        "3. Create a project and import `config.xml` as the labeling interface.\n"
        "4. Import `tasks.json` and configure a local storage pointing to the `pdfs/` folder.\n"
        "5. Annotate the tasks, export as JSON, e.g. `export.json`.\n"
        "6. Merge back using `poetry run python tools/feedback_cli.py annotate-pdf ingest --export-json export.json --review-csv <csv>`.\n"
    )
    readme_path.write_text(readme_content, encoding="utf-8")

    return {
        "tasks": len(tasks),
        "out_dir": str(out_path),
        "config": str(config_path),
        "tasks_path": str(tasks_path),
        "readme_path": str(readme_path),
        "copied_pdfs": len(copied_map),
        "missing_pdfs": sorted(missing_sources),
        "thumbnails_enabled": fitz is not None,
    }


def ingest_pdf_annotation_export(
    export_json: str | Path,
    review_csv: str | Path,
    out_csv: str | Path | None = None,
) -> Dict[str, object]:
    export_path = Path(export_json)
    try:
        payload = json.loads(export_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - validated at runtime
        raise SystemExit(f"Invalid Label Studio export JSON: {exc}")

    if not isinstance(payload, list):
        raise SystemExit("Label Studio export must be a JSON list.")

    df = read_review_csv(review_csv)
    specs = _build_field_specs(df)
    spec_by_norm = {spec.normalized: spec for spec in specs}
    _ensure_columns(df, ["annotator", "timestamp", "notes"])

    row_by_id: Dict[str, int] = {}
    if "row_id" in df.columns:
        for idx, raw in df["row_id"].items():
            key = _safe_text(raw)
            if key and key not in row_by_id:
                row_by_id[key] = idx

    updated_rows = 0
    missing_tasks = 0
    touched_rows: Set[int] = set()
    invalid_status: Dict[int, List[str]] = {}
    gold_changed: Dict[int, Set[str]] = {}
    status_changed: Dict[int, Set[str]] = {}
    warnings: List[str] = []

    for task in payload:
        if not isinstance(task, dict):
            continue
        data = task.get("data", {})
        if not isinstance(data, dict):
            continue
        row_idx: Optional[int] = None
        row_id = _safe_text(data.get("row_id"))
        if row_id and row_id in row_by_id:
            row_idx = row_by_id[row_id]
        else:
            row_index_raw = data.get("row_index")
            row_index_text = _safe_text(row_index_raw)
            if row_index_text.isdigit():
                candidate = int(row_index_text)
                if 0 <= candidate < len(df):
                    row_idx = candidate
        if row_idx is None:
            missing_tasks += 1
            continue

        touched_rows.add(row_idx)
        annotations = task.get("annotations") or []
        if not annotations:
            continue
        annotation = None
        for ann in reversed(annotations):
            if ann and ann.get("result"):
                annotation = ann
                break
        if not annotation:
            continue

        results = annotation.get("result", [])
        if not isinstance(results, list):
            continue

        row_updated = False
        row_gold_changed: Set[str] = set()
        for result in results:
            if not isinstance(result, dict):
                continue
            from_name = result.get("from_name")
            value = result.get("value", {})
            if not isinstance(value, dict):
                continue
            if isinstance(from_name, str) and from_name.endswith("_gold"):
                norm = from_name[:-5]
                spec = spec_by_norm.get(norm)
                if not spec:
                    continue
                texts = value.get("text") or []
                text_value = "\n".join(t for t in texts if isinstance(t, str)).strip()
                original = _safe_text(df.at[row_idx, spec.gold_col])
                df.at[row_idx, spec.gold_col] = text_value
                if text_value != original:
                    row_updated = True
                    row_gold_changed.add(spec.pretty)
            elif isinstance(from_name, str) and from_name.endswith("_status"):
                norm = from_name[:-7]
                spec = spec_by_norm.get(norm)
                if not spec:
                    continue
                choices = value.get("choices") or []
                choice = ""
                for candidate in choices:
                    if isinstance(candidate, str):
                        choice = candidate.strip().upper()
                        break
                if choice:
                    normalized_choice = _normalize_status(choice)
                    if not normalized_choice:
                        invalid_status.setdefault(row_idx, []).append(f"{spec.pretty}: {choice}")
                        continue
                    current_raw_status = _safe_text(df.at[row_idx, spec.status_col])
                    current_status = _normalize_status(current_raw_status)
                    df.at[row_idx, spec.status_col] = normalized_choice
                    if normalized_choice != current_status:
                        row_updated = True
                        bucket = status_changed.setdefault(row_idx, set())
                        bucket.add(spec.pretty)
            elif from_name == "notes":
                texts = value.get("text") or []
                note = "\n".join(t for t in texts if isinstance(t, str)).strip()
                if note:
                    df.at[row_idx, "notes"] = note
                    row_updated = True
            elif from_name == "annotator":
                texts = value.get("text") or []
                name = "\n".join(t for t in texts if isinstance(t, str)).strip()
                if name:
                    df.at[row_idx, "annotator"] = name
                    row_updated = True

        if row_gold_changed:
            gold_changed[row_idx] = row_gold_changed

        if row_updated:
            updated_rows += 1
            timestamp = annotation.get("created_at") or annotation.get("updated_at")
            if timestamp:
                df.at[row_idx, "timestamp"] = _safe_text(timestamp)
            elif not _safe_text(df.at[row_idx, "timestamp"]):
                df.at[row_idx, "timestamp"] = datetime.utcnow().isoformat()

    for row_idx in sorted(touched_rows):
        row_label = _row_label(df, row_idx)
        invalid = invalid_status.get(row_idx)
        if invalid:
            warnings.append(
                f"Row {row_label}: ignored invalid status values → {', '.join(sorted(invalid))}"
            )
        changed_fields = gold_changed.get(row_idx, set())
        status_updates = status_changed.get(row_idx, set())
        missing_status_fields: List[str] = []
        ok_conflicts: List[str] = []
        status_needs_value: List[str] = []
        status_value_conflicts: List[str] = []
        for spec in specs:
            field_name = spec.pretty
            pred_val = _safe_text(df.at[row_idx, spec.pred_col])
            gold_val = _safe_text(df.at[row_idx, spec.gold_col])
            status_val = _normalize_status(df.at[row_idx, spec.status_col])
            if field_name in changed_fields and not status_val:
                missing_status_fields.append(field_name)
            if field_name in changed_fields and status_val == "OK" and gold_val and gold_val != pred_val:
                ok_conflicts.append(field_name)
            if field_name in status_updates and status_val in {"CORRECTED", "NEW"} and not gold_val:
                status_needs_value.append(f"{field_name} ({status_val})")
            if field_name in status_updates and status_val in {"MISSING", "REJECTED"} and gold_val:
                status_value_conflicts.append(f"{field_name} ({status_val})")
        if missing_status_fields:
            warnings.append(
                f"Row {row_label}: edited fields missing review status → {', '.join(sorted(missing_status_fields))}"
            )
        if ok_conflicts:
            warnings.append(
                f"Row {row_label}: fields marked OK but edited → {', '.join(sorted(ok_conflicts))}"
            )
        if status_needs_value:
            warnings.append(
                f"Row {row_label}: status requires corrected value → {', '.join(sorted(status_needs_value))}"
            )
        if status_value_conflicts:
            warnings.append(
                f"Row {row_label}: status conflicts with provided value → {', '.join(sorted(status_value_conflicts))}"
            )

    target = Path(out_csv) if out_csv else Path(review_csv).with_name(
        Path(review_csv).stem + "_annotated.csv"
    )
    write_review_csv(df, target)

    return {
        "updated_review_csv": str(target),
        "annotated_rows": updated_rows,
        "tasks_without_match": missing_tasks,
        "warnings": warnings,
    }
