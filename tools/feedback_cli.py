#!/usr/bin/env python3
"""
CLI for the feedback loop (HITL): prepare review CSVs, ingest annotations,
evaluate metrics, optional fine-tune of Sentence Transformers, and export
simple tasks for Label Studio.

Legacy CLI entrypoints for the feedback workflow.

The CSV-based commands have been retired in favour of the database-backed
pipeline. Invocations now exit with a guidance message that points to the
`scripts/migrate_review_csv.py` utility and the new UI.
"""
from __future__ import annotations

import argparse
import asyncio
import glob
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

try:  # Rich powers the gamified review; degrade gracefully if missing.
    from rich.align import Align
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
except ImportError:  # pragma: no cover - handled during runtime
    Console = None  # type: ignore

from server.pdf_training_app import services as training_services
from tools.feedback_utils import (
    NORMALIZED_TO_PRETTY,
    export_labelstudio_tasks,
    evaluate_review_csv,
    ingest_review_csv,
    make_review_csv,
    read_review_csv,
    write_review_csv,
)
from tools.pdf_annotation import (
    ingest_pdf_annotation_export,
    prepare_pdf_annotation_project,
)
CSV_REMOVAL_MESSAGE = (
    "The CSV-based feedback workflow has been removed. "
    "Run `poetry run python scripts/migrate_review_csv.py` to migrate legacy datasets "
    "and use the database-first pipeline exposed by the server and SPA."
)


def _csv_workflow_removed(command: str) -> None:
    raise SystemExit(f"{command}: {CSV_REMOVAL_MESSAGE}")


# ---------------------------------------------------------------------------
# LLM helper session (optional)
# ---------------------------------------------------------------------------


@dataclass
class SuggestionQuest:
    """Container for one suggestion that can be reviewed in the CLI."""

    row_id: Optional[int]
    row_index: int
    normalized_field: str
    pretty_field: str
    current_value: str
    suggested_value: str
    rationale: str
    confidence: Optional[float]
    provider: Optional[str]
    model: Optional[str]
    cost_usd: Optional[float]

    @property
    def quest_label(self) -> str:
        sid = self.row_id if self.row_id is not None else self.row_index + 1
        return f"Row {sid} — {self.pretty_field}"


def _load_llm_suggestions(jsonl_path: str | Path, limit: Optional[int] = None) -> List[SuggestionQuest]:
    suggestions: List[SuggestionQuest] = []
    path = Path(jsonl_path)
    if not path.exists():
        raise SystemExit(f"LLM suggestions file not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue

            row = payload.get("row", {})
            provider = payload.get("provider")
            model = payload.get("model")
            cost = payload.get("cost_usd")
            for item in payload.get("suggestions", []):
                field_key = item.get("field")
                if field_key not in NORMALIZED_TO_PRETTY:
                    continue
                pretty = NORMALIZED_TO_PRETTY[field_key]
                quest = SuggestionQuest(
                    row_id=row.get("row_id"),
                    row_index=int(row.get("row_index", i)),
                    normalized_field=field_key,
                    pretty_field=pretty,
                    current_value=str(item.get("current", "")),
                    suggested_value=str(item.get("suggested", "")),
                    rationale=str(item.get("rationale", "")),
                    confidence=(
                        float(item.get("confidence"))
                        if item.get("confidence") not in (None, "")
                        else None
                    ),
                    provider=provider,
                    model=model,
                    cost_usd=(float(cost) if cost not in (None, "") else None),
                )
                suggestions.append(quest)
                if limit and len(suggestions) >= limit:
                    return suggestions

    return suggestions


def _apply_suggestion_to_review(df: pd.DataFrame, quest: SuggestionQuest) -> None:
    pretty = quest.pretty_field
    gold_col = f"{pretty}_gold"
    status_col = f"{pretty}_status"
    if gold_col not in df.columns:
        df[gold_col] = ""
    if status_col not in df.columns:
        df[status_col] = ""

    if "row_id" in df.columns and quest.row_id is not None:
        matches = df[df["row_id"] == quest.row_id]
        if not matches.empty:
            target_index = matches.index[0]
        else:
            target_index = quest.row_index if quest.row_index < len(df) else df.index[-1]
    else:
        target_index = quest.row_index if quest.row_index < len(df) else df.index[-1]

    df.at[target_index, gold_col] = quest.suggested_value
    if not str(df.at[target_index, status_col]).strip():
        df.at[target_index, status_col] = "CORRECTED"


def _render_card(console: Console, quest: SuggestionQuest, progress: Tuple[int, int], score: Dict[str, float]) -> None:
    table = Table.grid(padding=(0, 1))
    table.add_column(justify="right", style="cyan", no_wrap=True)
    table.add_column(style="white")

    table.add_row("Current", quest.current_value or "<empty>")
    table.add_row("Suggested", quest.suggested_value or "<empty>")
    table.add_row("Confidence", f"{quest.confidence:.2f}" if quest.confidence is not None else "n/a")
    table.add_row("Provider", f"{quest.provider or 'n/a'} :: {quest.model or 'n/a'}")
    if quest.cost_usd is not None:
        table.add_row("Cost", f"${quest.cost_usd:.4f}")
    table.add_row("Rationale", quest.rationale or "(no rationale provided)")

    header = Text(quest.quest_label, style="bold magenta")
    subtitle = Text(
        f"Quest {progress[0]} / {progress[1]}  •  Score {int(score['points'])}  •  Accepted {score['accepted']}  •  Tokens ${score['cost']:.4f}",
        style="green",
    )

    panel = Panel.fit(
        Align.center(table, vertical="middle"),
        title=header,
        subtitle=subtitle,
        border_style="bright_blue",
    )
    console.clear()
    console.print(panel)
    console.print("Accept [Y], Reject [N], Details [D], Quit [Q]", style="yellow")


def _show_details(console: Console, quest: SuggestionQuest) -> None:
    detail_table = Table(title="Prompt Details", show_header=False)
    detail_table.add_column("Field", style="cyan", ratio=1)
    detail_table.add_column("Value", ratio=3)
    detail_table.add_row("Row id", str(quest.row_id or quest.row_index + 1))
    detail_table.add_row("Normalized field", quest.normalized_field)
    detail_table.add_row("Pretty field", quest.pretty_field)
    detail_table.add_row("Current", quest.current_value or "<empty>")
    detail_table.add_row("Suggested", quest.suggested_value or "<empty>")
    detail_table.add_row("Rationale", quest.rationale or "(empty)")
    detail_table.add_row("Confidence", f"{quest.confidence}" if quest.confidence is not None else "n/a")
    console.print(detail_table)
    console.print("Press Enter to continue…", style="cyan")
    input()


def _run_gamified_session(
    suggestions_path: str,
    review_csv: str,
    output_review: Optional[str],
    session_log: Optional[str],
    limit: Optional[int] = None,
) -> Dict[str, object]:
    if Console is None:
        raise SystemExit("rich is required for the gamified session; install project dependencies.")

    console = Console()
    suggestions = _load_llm_suggestions(suggestions_path, limit=limit)
    if not suggestions:
        console.print("No LLM suggestions to review.", style="yellow")
        return {"accepted": 0, "rejected": 0, "updated_review_csv": review_csv}

    review_df = read_review_csv(review_csv)
    accepted: List[SuggestionQuest] = []
    rejected: List[SuggestionQuest] = []
    spent = 0.0

    for idx, quest in enumerate(suggestions, start=1):
        score = {
            "points": len(accepted) * 80 + len(rejected) * 10,
            "accepted": len(accepted),
            "cost": spent,
        }
        _render_card(console, quest, (idx, len(suggestions)), score)

        while True:
            choice = console.input("[bold white]Your move[/]: ").strip().lower()
            if choice in {"y", "n", "d", "q"}:
                break
        if choice == "q":
            break
        if choice == "d":
            _show_details(console, quest)
            # Re-render card after details view
            _render_card(console, quest, (idx, len(suggestions)), score)
            choice = console.input("[bold white]Your move[/]: ").strip().lower()
            if choice not in {"y", "n"}:
                continue

        if quest.cost_usd:
            spent += float(quest.cost_usd)

        if choice == "y":
            _apply_suggestion_to_review(review_df, quest)
            accepted.append(quest)
        else:
            rejected.append(quest)

    # Persist updated review CSV (do not overwrite automatically unless requested)
    if output_review:
        target = Path(output_review)
    else:
        review_path = Path(review_csv)
        target = review_path.with_name(review_path.stem + "_llm_applied.csv")
    write_review_csv(review_df, target)

    if session_log:
        log_path = Path(session_log)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "accepted": [quest.__dict__ for quest in accepted],
            "rejected": [quest.__dict__ for quest in rejected],
            "created_at": datetime.utcnow().isoformat(),
            "updated_review_csv": str(target),
        }
        with open(log_path, "w", encoding="utf-8") as log_file:
            json.dump(payload, log_file, indent=2, ensure_ascii=False)

    console.print(
        f"Review complete — accepted {len(accepted)} suggestions, rejected {len(rejected)}.",
        style="green",
    )
    console.print(f"Updated review saved to: {target}", style="cyan")

    return {
        "accepted": len(accepted),
        "rejected": len(rejected),
        "updated_review_csv": str(target),
    }


def cmd_prepare(args: argparse.Namespace) -> None:
    _csv_workflow_removed("prepare")
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
    _csv_workflow_removed("ingest")
    outputs = ingest_review_csv(args.review_csv, args.out_dir)
    for k, v in outputs.items():
        print(f"✅ {k}: {v}")


def cmd_eval(args: argparse.Namespace) -> None:
    _csv_workflow_removed("eval")
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
    _csv_workflow_removed("train-st")
    try:
        from sentence_transformers import SentenceTransformer, InputExample, losses
        from torch.utils.data import DataLoader
    except Exception as e:
        raise SystemExit("sentence-transformers and torch are required for train-st.\n" + str(e))

    dataset_path = args.dataset

    if args.enable_llm_helpers:
        if not args.review_csv or not args.llm_jsonl:
            raise SystemExit(
                "--enable-llm-helpers requires --review-csv and --llm-jsonl."
            )
        session_log = args.llm_session_log or "reports/llm_critique/session.log.json"
        session = _run_gamified_session(
            suggestions_path=args.llm_jsonl,
            review_csv=args.review_csv,
            output_review=args.llm_review_out,
            session_log=session_log,
            limit=args.llm_limit,
        )
        updated_review = session["updated_review_csv"]
        ingest_out_dir = args.datasets_out or "datasets"
        ingest_outputs = ingest_review_csv(updated_review, ingest_out_dir)
        dataset_path = ingest_outputs.get("st_pairs_jsonl")
        if not dataset_path:
            raise SystemExit(
                "Failed to build ST pairs after applying LLM suggestions."
            )
        print(f"✅ Updated review CSV: {updated_review}")
        print(f"✅ Regenerated dataset directory: {ingest_out_dir}")
        print(f"✅ Using dataset for training: {dataset_path}")

    if not dataset_path:
        raise SystemExit("--dataset is required when LLM helpers are disabled.")

    pairs = _load_st_pairs(dataset_path)
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
    _csv_workflow_removed("export-labelstudio")
    out = export_labelstudio_tasks(args.review_csv, args.out)
    print(f"✅ Label Studio tasks: {out}")


def cmd_annotate_pdf_prepare(args: argparse.Namespace) -> None:
    _csv_workflow_removed("annotate-pdf prepare")
    result = prepare_pdf_annotation_project(
        review_csv=args.review_csv,
        out_dir=args.out_dir,
        pdf_root=args.pdf_root,
    )
    print(f"✅ Tasks directory: {result['out_dir']}")
    print(f"✅ Config: {result['config']}")
    print(f"✅ Tasks JSON: {result['tasks_path']}")
    if result.get("readme_path"):
        print(f"📄 Quickstart: {result['readme_path']}")
    print(f"✅ Copied PDFs: {result['copied_pdfs']}")
    if result.get("missing_pdfs"):
        missing = ", ".join(result["missing_pdfs"][:5])
        print(f"⚠️ Missing PDFs ({len(result['missing_pdfs'])}): {missing}")
    if not result.get("thumbnails_enabled", True):
        print("ℹ️ Install `pymupdf` (annotation extras) to enable thumbnails.")
    print("➡️ Next: run `label-studio start`, import `config.xml` and `tasks.json`, then connect the `pdfs/` folder via Local Storage.")


def cmd_annotate_pdf_ingest(args: argparse.Namespace) -> None:
    _csv_workflow_removed("annotate-pdf ingest")
    result = ingest_pdf_annotation_export(
        export_json=args.export_json,
        review_csv=args.review_csv,
        out_csv=args.out,
    )
    print(f"✅ Updated review CSV: {result['updated_review_csv']}")
    print(f"✅ Annotated rows merged: {result['annotated_rows']}")
    if result.get("tasks_without_match"):
        print(
            f"⚠️ Tasks without CSV match: {result['tasks_without_match']} (check row_id/source file)"
        )
    warnings = result.get("warnings") or []
    if warnings:
        print("⚠️ Review warnings detected:")
        for item in warnings[:10]:
            print(f"   - {item}")
        if len(warnings) > 10:
            print(f"   … plus {len(warnings) - 10} more. See JSON export for details.")

def main() -> None:
    parser = argparse.ArgumentParser(description="Feedback loop CLI (HITL)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_prep = sub.add_parser("prepare", help="[deprecated] Legacy CSV workflow (see scripts/migrate_review_csv.py)")
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

    p_ing = sub.add_parser("ingest", help="[deprecated] Legacy CSV workflow (see scripts/migrate_review_csv.py)")
    p_ing.add_argument("--review-csv", required=True, help="Reviewed CSV path")
    p_ing.add_argument("--out-dir", required=True, help="Output directory for datasets")
    p_ing.set_defaults(func=cmd_ingest)

    p_eval = sub.add_parser("eval", help="[deprecated] Legacy CSV workflow (see scripts/migrate_review_csv.py)")
    p_eval.add_argument("--review-csv", required=True, help="Reviewed CSV path")
    p_eval.add_argument("--report-dir", required=True, help="Output directory for metrics")
    p_eval.set_defaults(func=cmd_eval)

    p_train = sub.add_parser("train-st", help="[deprecated] Legacy CSV workflow (see scripts/migrate_review_csv.py)")
    p_train.add_argument("--dataset", help="st_pairs.jsonl (skip when using --enable-llm-helpers)")
    p_train.add_argument("--output", required=True, help="Output directory for the trained model")
    p_train.add_argument("--batch-size", type=int, default=16)
    p_train.add_argument("--epochs", type=int, default=2)
    p_train.add_argument(
        "--enable-llm-helpers",
        action="store_true",
        help="Interactive review of LLM suggestions before training",
    )
    p_train.add_argument("--llm-jsonl", help="JSONL produced by tools/llm_critique.py")
    p_train.add_argument("--review-csv", help="Original review CSV to update with accepted suggestions")
    p_train.add_argument("--llm-review-out", help="Optional path for the updated review CSV")
    p_train.add_argument("--llm-session-log", help="Where to store the acceptance log (JSON)")
    p_train.add_argument(
        "--llm-limit",
        type=int,
        help="Limit the number of LLM suggestions shown during the session",
    )
    p_train.add_argument(
        "--datasets-out",
        help="Directory for regenerated datasets when helpers are enabled (defaults to ./datasets)",
    )
    p_train.add_argument("--use-db", action="store_true", help="Use the database-backed training pipeline.")
    p_train.add_argument("--document-ids", help="Comma-separated document IDs for DB-backed training.")
    p_train.set_defaults(func=cmd_train_st)

    p_ls = sub.add_parser("export-labelstudio", help="[deprecated] Legacy CSV workflow (see scripts/migrate_review_csv.py)")
    p_ls.add_argument("--review-csv", required=True)
    p_ls.add_argument("--out", required=True)
    p_ls.set_defaults(func=cmd_export_labelstudio)

    p_wizard = sub.add_parser("wizard", help="[deprecated] Legacy CSV workflow (see scripts/migrate_review_csv.py)")
    p_wizard.set_defaults(func=lambda _args: _csv_workflow_removed("wizard"))

    p_ann = sub.add_parser("annotate-pdf", help="[deprecated] Legacy CSV workflow (see scripts/migrate_review_csv.py)")
    ann_sub = p_ann.add_subparsers(dest="annotate_cmd", required=True)

    p_ann_prep = ann_sub.add_parser("prepare", help="Create Label Studio project assets")
    p_ann_prep.add_argument("--review-csv", required=True)
    p_ann_prep.add_argument(
        "--out-dir",
        default="reports/feedback/pdf_annotation",
        help="Folder for config/tasks/pdfs",
    )
    p_ann_prep.add_argument(
        "--pdf-root",
        help="Root directory to look for the original PDFs (optional)",
    )
    p_ann_prep.set_defaults(func=cmd_annotate_pdf_prepare)

    p_ann_ing = ann_sub.add_parser("ingest", help="Merge Label Studio export back into review.csv")
    p_ann_ing.add_argument("--export-json", required=True, help="Label Studio JSON export path")
    p_ann_ing.add_argument("--review-csv", required=True, help="Original review CSV")
    p_ann_ing.add_argument(
        "--out",
        help="Updated review CSV path (defaults to <name>_annotated.csv)",
    )
    p_ann_ing.set_defaults(func=cmd_annotate_pdf_ingest)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
