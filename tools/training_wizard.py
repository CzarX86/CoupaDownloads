#!/usr/bin/env python3
"""Interactive wizard for feedback and training workflows."""
from __future__ import annotations

import argparse
import shlex
import textwrap
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

MenuHandler = Callable[[argparse.Namespace], None]


@dataclass
class WizardOption:
    """Definition of a wizard action available from the main menu."""

    key: str
    title: str
    description: str
    collector: Callable[[], Tuple[argparse.Namespace, Sequence[str]]]


def run_wizard(handlers: Dict[str, MenuHandler]) -> None:
    """Launch the interactive wizard.

    Parameters
    ----------
    handlers:
        Mapping of command keys (``prepare``, ``ingest``, etc.) to the
        corresponding handler functions defined in ``feedback_cli``.
    """
    print("\n=== Feedback & Training Wizard ===\n")
    print(
        textwrap.fill(
            "This wizard guides common workflows step by step. You will provide "
            "the minimum required information, review the equivalent CLI command, "
            "and confirm before execution.",
            width=88,
        )
    )
    print()

    options = _build_options()

    while True:
        _render_menu(options)
        choice = _prompt_choice(len(options) + 1)
        if choice == len(options) + 1:
            print("Goodbye!")
            return

        option = options[choice - 1]
        handler = handlers.get(option.key)
        if handler is None:
            print(f"Handler for '{option.key}' not provided. Returning to menu.\n")
            continue

        _execute_option(option, handler)


# ---------------------------------------------------------------------------
# Menu plumbing
# ---------------------------------------------------------------------------


def _build_options() -> List[WizardOption]:
    return [
        WizardOption(
            key="prepare",
            title="Prepare review CSV",
            description="Merge predictions into a sampled review spreadsheet.",
            collector=_collect_prepare,
        ),
        WizardOption(
            key="ingest",
            title="Ingest reviewed CSV",
            description="Convert reviewer edits into datasets and analysis outputs.",
            collector=_collect_ingest,
        ),
        WizardOption(
            key="eval",
            title="Evaluate predictions",
            description="Compute accuracy metrics against reviewed ground truth.",
            collector=_collect_eval,
        ),
        WizardOption(
            key="train-st",
            title="Train Sentence Transformers",
            description="Fine-tune embeddings with optional LLM-assisted review.",
            collector=_collect_train,
        ),
        WizardOption(
            key="export-labelstudio",
            title="Export Label Studio tasks",
            description="Generate JSON tasks for lightweight external annotation.",
            collector=_collect_export,
        ),
    ]


def _render_menu(options: Sequence[WizardOption]) -> None:
    print("Select a workflow:\n")
    for idx, option in enumerate(options, start=1):
        print(f" {idx}. {option.title}")
        print(f"    {option.description}")
    print(f" {len(options) + 1}. Exit wizard\n")


# ---------------------------------------------------------------------------
# Collectors for each workflow
# ---------------------------------------------------------------------------


def _collect_prepare() -> Tuple[argparse.Namespace, Sequence[str]]:
    print("\n>>> Prepare review CSV")
    print(
        textwrap.fill(
            "Gather predictions and build a spreadsheet for reviewers. Provide at "
            "least one CSV path or glob pattern.",
            width=88,
        )
    )

    pred_default = "reports/advanced_*.csv"
    pred_csv = _prompt_list(
        label="Prediction CSV path(s) or glob pattern(s)",
        help_text="Comma-separated values such as reports/advanced_*.csv",
        default=pred_default,
        required=True,
    )
    out_path = _prompt_text(
        label="Output review CSV path",
        default="reports/feedback/review.csv",
        required=True,
    )
    fields_default = "contract_name,contract_type,sow_value_eur,pwo_number,managed_by"
    fields = _prompt_text(
        label="Fields to include",
        help_text="Leave empty to use project defaults (contract_name, contract_type, ...)",
        default=fields_default,
    )
    sample = _prompt_int(
        label="Number of rows to sample",
        help_text="Press Enter to include all rows.",
    )

    namespace = argparse.Namespace(
        pred_csv=pred_csv,
        out=out_path,
        fields=fields,
        sample=sample,
    )

    command = [
        "python",
        "tools/feedback_cli.py",
        "prepare",
        "--pred-csv",
        *pred_csv,
        "--out",
        out_path,
    ]
    if fields:
        command.extend(["--fields", fields])
    if sample is not None:
        command.extend(["--sample", str(sample)])

    return namespace, command


def _collect_ingest() -> Tuple[argparse.Namespace, Sequence[str]]:
    print("\n>>> Ingest reviewed CSV")
    print(
        textwrap.fill(
            "Transform reviewer corrections into structured datasets and reports.",
            width=88,
        )
    )

    review_csv = _prompt_text(
        label="Reviewed CSV path",
        default="reports/feedback/review.csv",
        required=True,
    )
    out_dir = _prompt_text(
        label="Output directory for datasets",
        default="datasets",
        required=True,
    )

    namespace = argparse.Namespace(
        review_csv=review_csv,
        out_dir=out_dir,
    )
    command = [
        "python",
        "tools/feedback_cli.py",
        "ingest",
        "--review-csv",
        review_csv,
        "--out-dir",
        out_dir,
    ]
    return namespace, command


def _collect_eval() -> Tuple[argparse.Namespace, Sequence[str]]:
    print("\n>>> Evaluate predictions")
    print(
        textwrap.fill(
            "Compare predictions to gold labels and emit accuracy metrics.",
            width=88,
        )
    )

    review_csv = _prompt_text(
        label="Reviewed CSV path",
        default="reports/feedback/review.csv",
        required=True,
    )
    report_dir = _prompt_text(
        label="Metrics output directory",
        default="reports/feedback",
        required=True,
    )

    namespace = argparse.Namespace(
        review_csv=review_csv,
        report_dir=report_dir,
    )
    command = [
        "python",
        "tools/feedback_cli.py",
        "eval",
        "--review-csv",
        review_csv,
        "--report-dir",
        report_dir,
    ]
    return namespace, command


def _collect_train() -> Tuple[argparse.Namespace, Sequence[str]]:
    print("\n>>> Train Sentence Transformers")
    print(
        textwrap.fill(
            "Fine-tune embeddings using the prepared sentence pairs. You can enable "
            "an optional LLM-assisted review loop before training.",
            width=88,
        )
    )

    enable_helpers = _prompt_confirmation(
        label="Enable interactive LLM helpers",
        default=False,
        help_text="If yes, the wizard will walk through applying LLM suggestions before training.",
    )

    if enable_helpers:
        llm_jsonl = _prompt_text(
            label="LLM suggestions JSONL path",
            default="reports/feedback/llm_suggestions.jsonl",
            required=True,
        )
        review_csv = _prompt_text(
            label="Original review CSV for updates",
            default="reports/feedback/review.csv",
            required=True,
        )
        llm_review_out = _prompt_text(
            label="Updated review CSV output",
            default="reports/feedback/review_llm_applied.csv",
        )
        llm_session_log = _prompt_text(
            label="LLM session log path",
            default="reports/feedback/llm_session.json",
        )
        llm_limit = _prompt_int(
            label="Limit number of suggestions to review",
            help_text="Press Enter to review them all.",
        )
        datasets_out = _prompt_text(
            label="Datasets output directory",
            default="datasets",
        )
        dataset = None
    else:
        dataset = _prompt_text(
            label="Sentence pair dataset (st_pairs.jsonl)",
            default="datasets/st_pairs.jsonl",
            required=True,
        )
        llm_jsonl = None
        review_csv = None
        llm_review_out = None
        llm_session_log = None
        llm_limit = None
        datasets_out = None

    output_dir = _prompt_text(
        label="Model output directory",
        default="embeddinggemma_feasibility/models/st_custom_v1",
        required=True,
    )
    batch_size = _prompt_int(
        label="Batch size",
        default=16,
    )
    epochs = _prompt_int(
        label="Epochs",
        default=2,
    )

    namespace = argparse.Namespace(
        dataset=dataset,
        output=output_dir,
        batch_size=batch_size or 16,
        epochs=epochs or 2,
        enable_llm_helpers=enable_helpers,
        llm_jsonl=llm_jsonl,
        review_csv=review_csv,
        llm_review_out=llm_review_out,
        llm_session_log=llm_session_log,
        llm_limit=llm_limit,
        datasets_out=datasets_out,
    )

    command = [
        "python",
        "tools/feedback_cli.py",
        "train-st",
        "--output",
        output_dir,
        "--batch-size",
        str(namespace.batch_size),
        "--epochs",
        str(namespace.epochs),
    ]
    if enable_helpers:
        command.append("--enable-llm-helpers")
        command.extend(["--llm-jsonl", llm_jsonl])
        command.extend(["--review-csv", review_csv])
        if llm_review_out:
            command.extend(["--llm-review-out", llm_review_out])
        if llm_session_log:
            command.extend(["--llm-session-log", llm_session_log])
        if llm_limit is not None:
            command.extend(["--llm-limit", str(llm_limit)])
        if datasets_out:
            command.extend(["--datasets-out", datasets_out])
    else:
        command.extend(["--dataset", dataset])

    return namespace, command


def _collect_export() -> Tuple[argparse.Namespace, Sequence[str]]:
    print("\n>>> Export Label Studio tasks")
    print(
        textwrap.fill(
            "Build a JSON file that can be imported into Label Studio for external "
            "annotation or validation.",
            width=88,
        )
    )

    review_csv = _prompt_text(
        label="Reviewed CSV path",
        default="reports/feedback/review.csv",
        required=True,
    )
    out_path = _prompt_text(
        label="Output JSON path",
        default="reports/feedback/tasks.json",
        required=True,
    )

    namespace = argparse.Namespace(
        review_csv=review_csv,
        out=out_path,
    )
    command = [
        "python",
        "tools/feedback_cli.py",
        "export-labelstudio",
        "--review-csv",
        review_csv,
        "--out",
        out_path,
    ]
    return namespace, command


# ---------------------------------------------------------------------------
# Execution helpers
# ---------------------------------------------------------------------------


def _execute_option(option: WizardOption, handler: MenuHandler) -> None:
    while True:
        namespace, command = option.collector()
        print("\nEquivalent CLI command:")
        print("  " + " ".join(shlex.quote(part) for part in command))
        print("\nParameters:")
        for key, value in sorted(vars(namespace).items()):
            print(f"  - {key}: {value}")
        print()

        proceed = _prompt_confirmation(
            label="Run this workflow now",
            default=True,
        )
        if proceed:
            print("\nRunning workflow...\n")
            handler(namespace)
            print("\nWorkflow finished. Returning to menu.\n")
            return

        retry = _prompt_confirmation(
            label="Edit inputs for this workflow",
            default=True,
        )
        if not retry:
            print("Returning to menu.\n")
            return


# ---------------------------------------------------------------------------
# Prompt utilities
# ---------------------------------------------------------------------------


def _prompt_choice(limit: int) -> int:
    while True:
        raw = input(f"Enter a number (1-{limit}): ").strip()
        if not raw:
            continue
        if raw.isdigit():
            value = int(raw)
            if 1 <= value <= limit:
                return value
        print("Invalid selection. Please try again.")


def _prompt_text(
    *,
    label: str,
    help_text: Optional[str] = None,
    default: Optional[str] = None,
    required: bool = False,
) -> Optional[str]:
    if help_text:
        print(textwrap.fill(help_text, width=88))
    while True:
        suffix = f" [{default}]" if default else ""
        raw = input(f"{label}{suffix}: ").strip()
        if not raw and default:
            raw = default
        if not raw:
            if required:
                print("This value is required. Please try again.")
                continue
            return None
        return raw


def _prompt_list(
    *,
    label: str,
    help_text: Optional[str] = None,
    default: Optional[str] = None,
    required: bool = False,
) -> List[str]:
    while True:
        value = _prompt_text(
            label=label,
            help_text=help_text,
            default=default,
            required=required,
        )
        items = [item.strip() for item in (value or "").split(",") if item.strip()]
        if items:
            return items
        if required:
            print("Please provide at least one entry.")
        else:
            return []


def _prompt_int(
    *,
    label: str,
    help_text: Optional[str] = None,
    default: Optional[int] = None,
) -> Optional[int]:
    if help_text:
        print(textwrap.fill(help_text, width=88))
    while True:
        suffix = f" [{default}]" if default is not None else ""
        raw = input(f"{label}{suffix}: ").strip()
        if not raw:
            return default
        try:
            return int(raw)
        except ValueError:
            print("Enter a valid integer or press Enter to skip.")


def _prompt_confirmation(
    *,
    label: str,
    default: bool = False,
    help_text: Optional[str] = None,
) -> bool:
    if help_text:
        print(textwrap.fill(help_text, width=88))
    suffix = " [Y/n]" if default else " [y/N]"
    while True:
        raw = input(f"{label}{suffix}: ").strip().lower()
        if not raw:
            return default
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("Please respond with 'y' or 'n'.")


if __name__ == "__main__":  # pragma: no cover - manual execution entrypoint
    from tools import feedback_cli

    run_wizard(
        {
            "prepare": feedback_cli.cmd_prepare,
            "ingest": feedback_cli.cmd_ingest,
            "eval": feedback_cli.cmd_eval,
            "train-st": feedback_cli.cmd_train_st,
            "export-labelstudio": feedback_cli.cmd_export_labelstudio,
        }
    )
