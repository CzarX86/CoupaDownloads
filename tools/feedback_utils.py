#!/usr/bin/env python3
"""
Feedback utilities for Human-in-the-Loop (HITL) review, ingestion, dataset
creation, and evaluation. Designed to be lightweight and dependency-minimal.

Conventions:
- Review CSV uses triplets per field: <Pretty Field>_pred, _gold, _status
- Status allowed: OK | CORRECTED | NEW | MISSING | REJECTED (free text tolerated)
- Metadata preserved: Source File, Extraction Confidence, Extraction Method, NLP Libraries Used

This module avoids new heavy deps; relies on pandas and stdlib only.
"""
from __future__ import annotations

import json
import os
import random
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd


# Mapping between normalized keys (snake_case) and CSV pretty headers
NORMALIZED_TO_PRETTY: Dict[str, str] = {
    "remarks": "Remarks",
    "supporting_information": "Supporting Information",
    "procurement_negotiation_strategy": "Procurement Negotiation Strategy",
    "opportunity_available": "Opportunity Available",
    "inflation_percent": "Inflation %",
    "minimum_commitment_value": "Minimum Commitment Value",
    "contractual_commercial_model": "Contractual Commercial Model",
    "user_based_license": "User Based License",
    "type_of_contract_l2": "Type of Contract - L2",
    "type_of_contract_l1": "Type of Contract - L1",
    "sow_value_eur": "SOW Value in EUR",
    "fx": "FX",
    "sow_currency": "SOW Currency",
    "sow_value_lc": "SOW Value in LC",
    "managed_by": "Managed By",
    "contract_end_date": "Contract End Date",
    "contract_start_date": "Contract Start Date",
    "contract_type": "Contract Type",
    "contract_name": "Contract Name",
    "high_level_scope": "High Level Scope",
    "platform_technology": "Platform/Technology",
    "pwo_number": "PWO#",
}

PRETTY_TO_NORMALIZED: Dict[str, str] = {v: k for k, v in NORMALIZED_TO_PRETTY.items()}

METADATA_COLS = [
    "Source File",
    "Extraction Confidence",
    "Extraction Method",
    "NLP Libraries Used",
]

ALLOWED_STATUSES = {"OK", "CORRECTED", "NEW", "MISSING", "REJECTED"}


def _coalesce_header(df: pd.DataFrame, pretty: str) -> str | None:
    """Find a column in df matching the 'pretty' header (case-insensitive fallback)."""
    if pretty in df.columns:
        return pretty
    lower = pretty.lower()
    for col in df.columns:
        if col.lower() == lower:
            return col
    return None


def _normalize_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def make_review_csv(
    pred_csv: str | Path,
    out_csv: str | Path,
    fields: Iterable[str] | None = None,
    sample: int | None = None,
) -> str:
    """Create a review CSV from a pipeline CSV with triplets per selected field.

    - fields: normalized keys (snake_case) as in NORMALIZED_TO_PRETTY; if None, use a default critical set.
    - sample: optional max number of rows to include (random sample); if None, include all.
    """
    df = pd.read_csv(pred_csv)

    # Default critical fields
    if not fields:
        fields = [
            "contract_name",
            "contract_type",
            "sow_value_eur",
            "pwo_number",
            "managed_by",
        ]

    fields = [f for f in fields if f in NORMALIZED_TO_PRETTY]
    if not fields:
        raise ValueError("No valid fields provided for review.")

    if sample is not None and sample > 0 and sample < len(df):
        df = df.sample(n=sample, random_state=42).reset_index(drop=True)

    # Build review frame
    review_cols = []
    # Always include a simple identifier
    df.insert(0, "row_id", range(1, len(df) + 1))
    review_cols.append("row_id")

    # Metadata
    for m in METADATA_COLS:
        col = _coalesce_header(df, m)
        if col is None:
            # Create empty column if missing in source
            df[m] = ""
            col = m
        review_cols.append(col)

    # Triplets per field
    for fkey in fields:
        pretty = NORMALIZED_TO_PRETTY[fkey]
        src_col = _coalesce_header(df, pretty)
        pred_series = df[src_col] if src_col else ""
        df[f"{pretty}_pred"] = pred_series
        df[f"{pretty}_gold"] = ""
        df[f"{pretty}_status"] = ""
        review_cols.extend([f"{pretty}_pred", f"{pretty}_gold", f"{pretty}_status"])

    # Optional reviewer helpers
    for aux in ("annotator", "timestamp", "notes"):
        df[aux] = ""
        review_cols.append(aux)

    # Persist (UTF-8 BOM, \n, QUOTE_MINIMAL handled by pandas defaults mostly)
    out_path = Path(out_csv)
    _ensure_dir(out_path.parent)
    df.to_csv(out_path, index=False, encoding="utf-8-sig", line_terminator="\n")
    return str(out_path)


def ingest_review_csv(review_csv: str | Path, out_dir: str | Path) -> Dict[str, str]:
    """Ingest a reviewed CSV and emit datasets and analysis files.

    Outputs in out_dir:
    - supervised.jsonl
    - st_pairs.jsonl
    - training_analysis.json (via ContractDataTrainer)
    """
    outp = _ensure_dir(out_dir)
    df = pd.read_csv(review_csv)

    # Discover fields from *_gold columns
    gold_cols = [c for c in df.columns if c.endswith("_gold")]
    bases: List[str] = [c[:-5] for c in gold_cols]

    # Build supervised.jsonl
    supervised_path = outp / "supervised.jsonl"
    with open(supervised_path, "w", encoding="utf-8") as f:
        for _, row in df.iterrows():
            labels: Dict[str, str] = {}
            status_map: Dict[str, str] = {}
            for base in bases:
                gold = _normalize_text(row.get(f"{base}_gold", ""))
                status = _normalize_text(row.get(f"{base}_status", ""))
                if not gold:
                    continue
                # Accept only actionable statuses if provided
                if status and status.upper() not in ALLOWED_STATUSES:
                    # still include the label; store status as-is
                    pass
                pretty = base
                norm_key = PRETTY_TO_NORMALIZED.get(pretty, pretty.lower().replace("/", "_").replace(" ", "_"))
                labels[norm_key] = gold
                status_map[norm_key] = status.upper() if status else ""

            if not labels:
                continue
            rec = {
                "source_file": row.get("Source File", ""),
                "labels": labels,
                "status": status_map,
                "meta": {
                    "confidence": row.get("Extraction Confidence", None),
                    "method": row.get("Extraction Method", None),
                },
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # Build ST pairs from selected categorical fields
    st_pairs_path = outp / "st_pairs.jsonl"
    cat_pretty_fields = [
        NORMALIZED_TO_PRETTY["contract_type"],
        NORMALIZED_TO_PRETTY["managed_by"],
        NORMALIZED_TO_PRETTY["sow_currency"],
        NORMALIZED_TO_PRETTY["platform_technology"],
        NORMALIZED_TO_PRETTY["type_of_contract_l1"],
        NORMALIZED_TO_PRETTY["type_of_contract_l2"],
    ]

    # Collect values per field
    field_values: Dict[str, List[str]] = {}
    for base in bases:
        if base not in cat_pretty_fields:
            continue
        vals = df[f"{base}_gold"].dropna().map(_normalize_text)
        vals = vals[vals != ""]
        if not vals.empty:
            # ensure some multiplicity
            field_values[base] = vals.tolist()

    # Generate simple positive/negative pairs within each field
    with open(st_pairs_path, "w", encoding="utf-8") as f:
        rnd = random.Random(42)
        for base, vals in field_values.items():
            uniq = list({v for v in vals})
            # positives: pairs of identical values sampled by duplication across rows (limited)
            if len(vals) >= 2:
                for _ in range(min(50, len(vals))):
                    v = rnd.choice(vals)
                    w = rnd.choice(vals)
                    label = 1.0 if v == w else 0.0
                    f.write(json.dumps({"text1": v, "text2": w, "label": label, "field": base}, ensure_ascii=False) + "\n")
            # negatives across different unique values for the same field
            if len(uniq) >= 2:
                for _ in range(min(50, len(uniq))):
                    v, w = rnd.sample(uniq, 2)
                    f.write(json.dumps({"text1": v, "text2": w, "label": 0.0, "field": base}, ensure_ascii=False) + "\n")

    # Produce training_analysis.json via existing trainer
    try:
        from embeddinggemma_feasibility.contract_data_trainer import ContractDataTrainer

        analysis_path = outp / "training_analysis.json"
        trainer = ContractDataTrainer(str(review_csv))
        if trainer.load_data():
            trainer.analyze_field_patterns()
            trainer.save_training_data(str(analysis_path))
    except Exception as e:
        # Non-fatal; analysis is optional
        with open(outp / "training_analysis.error.txt", "w", encoding="utf-8") as ef:
            ef.write(str(e))

    return {
        "supervised_jsonl": str(supervised_path),
        "st_pairs_jsonl": str(st_pairs_path),
        "training_analysis_json": str((outp / "training_analysis.json")),
    }


def _cmp_norm(a: str, b: str) -> bool:
    return _normalize_text(a).casefold() == _normalize_text(b).casefold()


def evaluate_review_csv(review_csv: str | Path, report_dir: str | Path) -> Dict[str, str]:
    """Compute simple per-field metrics comparing *_pred vs *_gold.

    Produces metrics.json and metrics.md in report_dir.
    """
    outp = _ensure_dir(report_dir)
    df = pd.read_csv(review_csv)
    gold_cols = [c for c in df.columns if c.endswith("_gold")]
    bases: List[str] = [c[:-5] for c in gold_cols]

    metrics = {"fields": {}, "summary": {}}
    total_rows = len(df)

    acc_values = []
    coverage_values = []

    for base in bases:
        pred_col = f"{base}_pred"
        gold_col = f"{base}_gold"
        if pred_col not in df.columns:
            continue
        preds = df[pred_col].fillna("")
        golds = df[gold_col].fillna("")
        eligible = golds != ""
        denom = int(eligible.sum()) if eligible.any() else 0
        if denom == 0:
            field_acc = None
        else:
            correct = sum(_cmp_norm(p, g) for p, g in zip(preds[eligible], golds[eligible]))
            field_acc = correct / denom if denom else None
            acc_values.append(field_acc)
        coverage = (preds != "").mean() if total_rows else 0.0
        coverage_values.append(coverage)
        metrics["fields"][base] = {
            "rows": total_rows,
            "labeled": denom,
            "accuracy": field_acc,
            "coverage": coverage,
        }

    # Summary
    metrics["summary"] = {
        "rows": total_rows,
        "avg_accuracy": (sum(acc_values) / len(acc_values)) if acc_values else None,
        "avg_coverage": (sum(coverage_values) / len(coverage_values)) if coverage_values else 0.0,
    }

    # Persist JSON
    json_path = outp / "metrics.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    # Persist Markdown
    md_path = outp / "metrics.md"
    lines = ["# Feedback Metrics", "", f"- Rows: {total_rows}",
             f"- Avg accuracy: {metrics['summary']['avg_accuracy']}",
             f"- Avg coverage: {metrics['summary']['avg_coverage']}", "", "## Per field"]
    for base, m in metrics["fields"].items():
        lines.append(f"- {base}: labeled={m['labeled']}, accuracy={m['accuracy']}, coverage={m['coverage']}")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return {"metrics_json": str(json_path), "metrics_md": str(md_path)}


def export_labelstudio_tasks(review_csv: str | Path, out_json: str | Path) -> str:
    """Export a minimal set of tasks for Label Studio import.

    Each task includes source_file and field predictions as initial data.
    """
    df = pd.read_csv(review_csv)
    gold_cols = [c for c in df.columns if c.endswith("_gold")]
    bases: List[str] = [c[:-5] for c in gold_cols]

    tasks = []
    for i, row in df.iterrows():
        data = {"source_file": row.get("Source File", "")}
        fields = {}
        for base in bases:
            fields[base] = {
                "pred": row.get(f"{base}_pred", ""),
                "gold": row.get(f"{base}_gold", ""),
                "status": row.get(f"{base}_status", ""),
            }
        data["fields"] = fields
        tasks.append({"id": int(row.get("row_id", i + 1)), "data": data})

    outp = Path(out_json)
    _ensure_dir(outp.parent)
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)
    return str(outp)

