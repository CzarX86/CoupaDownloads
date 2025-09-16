#!/usr/bin/env python3
"""
CLI for the feedback loop (HITL): prepare review CSVs, ingest annotations,
evaluate metrics, optional fine-tune of Sentence Transformers, and export
simple tasks for Label Studio.

Usage examples:
  python tools/feedback_cli.py prepare --pred-csv reports/advanced_*.csv --out review.csv \
      --fields contract_name,contract_type,sow_value_eur,pwo_number,managed_by --sample 30

  python tools/feedback_cli.py ingest --review-csv review.csv --out-dir datasets/

  python tools/feedback_cli.py eval --review-csv review.csv --report-dir reports/feedback/

  python tools/feedback_cli.py train-st --dataset datasets/st_pairs.jsonl --output embeddinggemma_feasibility/models/st_custom_v1

  python tools/feedback_cli.py export-labelstudio --review-csv review.csv --out reports/feedback/tasks.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path
from typing import List

from tools.feedback_utils import (
    NORMALIZED_TO_PRETTY,
    export_labelstudio_tasks,
    evaluate_review_csv,
    ingest_review_csv,
    make_review_csv,
)


def cmd_prepare(args: argparse.Namespace) -> None:
    # Expand globs for input CSV
    matches: List[str] = []
    for pat in args.pred_csv:
        matches.extend(glob.glob(pat))
    if not matches:
        raise SystemExit("No input CSV found for --pred-csv patterns")
    # Use the first match if multiple; reviewers can choose which to prepare
    pred_csv = matches[0]
    fields = [f.strip() for f in (args.fields or "").split(",") if f.strip()]
    out = make_review_csv(pred_csv, args.out, fields or None, sample=args.sample)
    print(f"✅ Review CSV created: {out}")


def cmd_ingest(args: argparse.Namespace) -> None:
    outputs = ingest_review_csv(args.review_csv, args.out_dir)
    for k, v in outputs.items():
        print(f"✅ {k}: {v}")


def cmd_eval(args: argparse.Namespace) -> None:
    outputs = evaluate_review_csv(args.review_csv, args.report_dir)
    for k, v in outputs.items():
        print(f"✅ {k}: {v}")


def _load_st_pairs(pairs_jsonl: str):
    pairs = []
    with open(pairs_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            try:
                pairs.append(json.loads(line))
            except Exception:
                continue
    return pairs


def cmd_train_st(args: argparse.Namespace) -> None:
    try:
        from sentence_transformers import SentenceTransformer, InputExample, losses
        from torch.utils.data import DataLoader
    except Exception as e:
        raise SystemExit("sentence-transformers and torch are required for train-st.\n" + str(e))

    pairs = _load_st_pairs(args.dataset)
    if not pairs:
        raise SystemExit("No pairs found in dataset. Run ingest first or provide a valid --dataset.")

    examples = []
    for p in pairs:
        t1 = str(p.get("text1", "")).strip()
        t2 = str(p.get("text2", "")).strip()
        label = float(p.get("label", 0.0))
        if t1 and t2:
            examples.append(InputExample(texts=[t1, t2], label=label))

    if not examples:
        raise SystemExit("Empty training examples after filtering.")

    # Lightweight default model
    model = SentenceTransformer("all-MiniLM-L6-v2")
    train_dataloader = DataLoader(examples, shuffle=True, batch_size=args.batch_size)
    train_loss = losses.CosineSimilarityLoss(model)

    print(f"🚀 Training ST on {len(examples)} pairs for {args.epochs} epochs…")
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=args.epochs,
        warmup_steps=min(100, max(10, len(examples) // 10)),
        output_path=args.output,
    )
    print(f"✅ Model saved to: {args.output}")


def cmd_export_labelstudio(args: argparse.Namespace) -> None:
    out = export_labelstudio_tasks(args.review_csv, args.out)
    print(f"✅ Label Studio tasks: {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Feedback loop CLI (HITL)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_prep = sub.add_parser("prepare", help="Create review CSV with *_pred/_gold/_status columns")
    p_prep.add_argument("--pred-csv", nargs="+", required=True, help="CSV path(s) or glob patterns from the pipeline")
    p_prep.add_argument("--out", required=True, help="Output review CSV path")
    p_prep.add_argument(
        "--fields",
        help=(
            "Comma-separated normalized field keys. Defaults to: "
            "contract_name,contract_type,sow_value_eur,pwo_number,managed_by"
        ),
    )
    p_prep.add_argument("--sample", type=int, help="Optional number of rows to sample for review")
    p_prep.set_defaults(func=cmd_prepare)

    p_ing = sub.add_parser("ingest", help="Ingest reviewed CSV and create datasets/analysis")
    p_ing.add_argument("--review-csv", required=True, help="Reviewed CSV path")
    p_ing.add_argument("--out-dir", required=True, help="Output directory for datasets")
    p_ing.set_defaults(func=cmd_ingest)

    p_eval = sub.add_parser("eval", help="Evaluate predictions vs gold and emit metrics")
    p_eval.add_argument("--review-csv", required=True, help="Reviewed CSV path")
    p_eval.add_argument("--report-dir", required=True, help="Output directory for metrics")
    p_eval.set_defaults(func=cmd_eval)

    p_train = sub.add_parser("train-st", help="Fine-tune Sentence Transformers on pair dataset")
    p_train.add_argument("--dataset", required=True, help="st_pairs.jsonl")
    p_train.add_argument("--output", required=True, help="Output directory for the trained model")
    p_train.add_argument("--batch-size", type=int, default=16)
    p_train.add_argument("--epochs", type=int, default=2)
    p_train.set_defaults(func=cmd_train_st)

    p_ls = sub.add_parser("export-labelstudio", help="Export minimal tasks JSON for Label Studio")
    p_ls.add_argument("--review-csv", required=True)
    p_ls.add_argument("--out", required=True)
    p_ls.set_defaults(func=cmd_export_labelstudio)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

