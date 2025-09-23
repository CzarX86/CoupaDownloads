#!/usr/bin/env python3
"""Optional helper to critique prediction CSVs with an external LLM.

The script is intentionally side-car: it never mutates datasets in place and
only runs when a provider API key is present. Results are written under the
target output directory as JSONL (one object per reviewed row) plus a merged
CSV that keeps the original columns alongside ``<Field>_llm_suggested``
helpers. A human still approves the suggestions inside the feedback CLI.

Usage (DeepSeek default)::

    poetry run python tools/llm_critique.py --pred-csv reports/advanced_*.csv \
        --out-dir reports/llm_critique/ --max-rows 25

Usage (OpenAI fallback)::

    poetry run python tools/llm_critique.py --pred-csv reports/advanced.csv \
        --provider openai --model gpt-4o-mini

Dry-run mode is available to exercise the pipeline without making any API
calls::

    poetry run python tools/llm_critique.py --pred-csv reports/advanced.csv --dry-run

The script prefers the following environment variables when no ``--api-key``
argument is supplied:

* ``DEEPSEEK_API_KEY`` (for ``provider=deepseek``, the default)
* ``OPENAI_API_KEY`` (for ``provider=openai``)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd

try:
    import httpx
except ImportError as exc:  # pragma: no cover - tooling requirement
    raise SystemExit(
        "httpx is required to use LLM helpers. Install project dependencies first."
    ) from exc

from tools.feedback_utils import NORMALIZED_TO_PRETTY, read_review_csv


DEFAULT_FIELDS: List[str] = [
    "contract_name",
    "contract_type",
    "sow_value_eur",
    "pwo_number",
    "managed_by",
]


def _ensure_out_dir(path: str | Path) -> Path:
    out = Path(path)
    out.mkdir(parents=True, exist_ok=True)
    return out


def _resolve_api_key(provider: str, explicit: str | None) -> str:
    if explicit:
        return explicit
    env_key = "DEEPSEEK_API_KEY" if provider == "deepseek" else "OPENAI_API_KEY"
    key = os.getenv(env_key)
    if not key:
        raise SystemExit(
            f"Missing API key. Provide --api-key or set {env_key}."
        )
    return key


def _normalise_fields(fields: Iterable[str] | None) -> List[str]:
    if not fields:
        return list(DEFAULT_FIELDS)
    valid = []
    for field in fields:
        key = field.strip().lower()
        if key in NORMALIZED_TO_PRETTY:
            valid.append(key)
    if not valid:
        raise SystemExit("No valid normalized field names were provided.")
    return valid


def _build_prompt(row: pd.Series, fields: List[str], row_label: str) -> str:
    lines = [
        "You are reviewing extracted procurement data.",
        "For each field decide whether to keep the prediction or suggest",
        "a corrected value. Return strict JSON with this schema:",
        '{"fields": [{"field": "contract_name", "decision": "keep|change",',
        '"suggested": "...", "rationale": "...", "confidence": 0.0}]}.',
        "Confidence is 0 to 1. Use 'keep' when the prediction appears correct",
        "and leave 'suggested' empty in that case.",
        "",
        f"Context for row {row_label}:",
    ]
    for fkey in fields:
        pretty = NORMALIZED_TO_PRETTY[fkey]
        pred_val = row.get(pretty)
        if pred_val is None:
            pred_val = row.get(f"{pretty}_pred")
        gold_val = row.get(f"{pretty}_gold")
        status = row.get(f"{pretty}_status")
        lines.append(
            f"- {pretty}: prediction='{pred_val or ''}' | gold='{gold_val or ''}' | status='{status or ''}'"
        )
    return "\n".join(lines)


def _simulate_response(fields: List[str]) -> Dict[str, object]:
    rng = random.Random(42)
    suggestions = []
    for f in fields:
        decision = rng.choice(["keep", "change"])
        suggestion = (
            f"{f.replace('_', ' ').title()} (LLM suggestion)"
            if decision == "change"
            else ""
        )
        suggestions.append(
            {
                "field": f,
                "decision": decision,
                "suggested": suggestion,
                "rationale": "Simulated response (dry-run).",
                "confidence": round(rng.uniform(0.6, 0.9), 2),
            }
        )
    return {
        "fields": suggestions,
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "cost_usd": 0.0,
    }


def _call_llm(
    provider: str,
    model: str,
    api_key: str,
    prompt: str,
    temperature: float,
    top_p: float,
    timeout: float,
) -> Dict[str, object]:
    if provider == "deepseek":
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    else:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = {
        "model": model,
        "temperature": temperature,
        "top_p": top_p,
        "messages": [
            {"role": "system", "content": "You are a precise data quality reviewer that responds with JSON only."},
            {"role": "user", "content": prompt},
        ],
    }

    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    message = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    usage = data.get("usage", {})

    try:
        parsed = json.loads(message)
    except json.JSONDecodeError:
        parsed = {"fields": [], "raw": message}

    parsed["usage"] = {
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
    }

    # Cost guardrails are caller responsibility; we simply surface metadata.
    if provider == "deepseek" and usage:
        # (R1) approx pricing $0.14 / $0.28 per 1M prompt/completion tokens.
        prompt_cost = (usage.get("prompt_tokens", 0) or 0) / 1_000_000 * 0.14
        completion_cost = (usage.get("completion_tokens", 0) or 0) / 1_000_000 * 0.28
        parsed["cost_usd"] = round(prompt_cost + completion_cost, 6)
    elif provider == "openai" and usage:
        # gpt-4o-mini approx $0.60 / $0.3 per 1M tokens
        prompt_cost = (usage.get("prompt_tokens", 0) or 0) / 1_000_000 * 0.6
        completion_cost = (usage.get("completion_tokens", 0) or 0) / 1_000_000 * 0.3
        parsed["cost_usd"] = round(prompt_cost + completion_cost, 6)
    else:
        parsed.setdefault("cost_usd", None)

    return parsed


def _load_dataframe(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"Input file not found: {p}")
    return read_review_csv(p)


def _match_review_row(review_df: pd.DataFrame, row_meta: Dict[str, object]) -> Optional[pd.Series]:
    if review_df is None:
        return None
    if "row_id" in review_df.columns and row_meta.get("row_id") is not None:
        matches = review_df[review_df["row_id"] == row_meta["row_id"]]
        if not matches.empty:
            return matches.iloc[0]
    # fallback to positional index
    idx = row_meta.get("row_index")
    if idx is not None and idx < len(review_df):
        return review_df.iloc[int(idx)]
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Optional external LLM critique helper")
    parser.add_argument("--pred-csv", required=True, help="Prediction CSV (from advanced extractor)")
    parser.add_argument("--review-csv", help="Optional reviewed CSV to enrich the prompt context")
    parser.add_argument("--out-dir", default="reports/llm_critique", help="Directory for outputs")
    parser.add_argument(
        "--fields",
        help="Comma-separated normalized field names (defaults to core fields)",
    )
    parser.add_argument("--provider", choices=["deepseek", "openai"], default="deepseek")
    parser.add_argument("--model", help="Model identifier for the selected provider")
    parser.add_argument("--api-key", help="Explicit API key (otherwise environment variable is used)")
    parser.add_argument("--max-rows", type=int, help="Optional cap on the number of rows to critique")
    parser.add_argument("--rate-limit", type=float, default=0.0, help="Seconds to sleep between API calls")
    parser.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout per request (seconds)")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--dry-run", action="store_true", help="Skip API calls and emit synthetic suggestions")

    args = parser.parse_args()

    fields = _normalise_fields(args.fields.split(",") if args.fields else None)
    pred_df = _load_dataframe(args.pred_csv)
    review_df = _load_dataframe(args.review_csv) if args.review_csv else None

    out_dir = _ensure_out_dir(args.out_dir)
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    jsonl_path = out_dir / f"llm_critique_{timestamp}.jsonl"
    merged_csv_path = out_dir / f"llm_critique_merged_{timestamp}.csv"
    summary_path = out_dir / f"llm_critique_summary_{timestamp}.json"

    provider = args.provider
    model = args.model or ("deepseek-reasoner" if provider == "deepseek" else "gpt-4o-mini")

    if not args.dry_run:
        api_key = _resolve_api_key(provider, args.api_key)
    else:
        api_key = ""

    accepted_rows = []
    merged_df = review_df.copy() if review_df is not None else pred_df.copy()

    total_cost = 0.0
    processed = 0

    with open(jsonl_path, "w", encoding="utf-8") as jsonl_file:
        for idx, (_, row) in enumerate(pred_df.iterrows()):
            if args.max_rows is not None and processed >= args.max_rows:
                break

            row_meta = {
                "row_index": idx,
                "row_id": row.get("row_id") if "row_id" in row else None,
                "source_file": row.get("Source File"),
            }

            review_row = _match_review_row(review_df, row_meta) if review_df is not None else None
            prompt_row = row.copy()
            if review_row is not None:
                for col in review_row.index:
                    prompt_row[col] = review_row[col]

            prompt = _build_prompt(prompt_row, fields, row_label=row_meta.get("row_id") or idx + 1)

            if args.dry_run:
                result = _simulate_response(fields)
            else:
                try:
                    result = _call_llm(
                        provider=provider,
                        model=model,
                        api_key=api_key,
                        prompt=prompt,
                        temperature=args.temperature,
                        top_p=args.top_p,
                        timeout=args.timeout,
                    )
                except Exception as exc:  # noqa: BLE001
                    result = {
                        "fields": [],
                        "error": str(exc),
                        "usage": {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None},
                        "cost_usd": None,
                    }

            if result.get("cost_usd"):
                total_cost += result["cost_usd"]

            enriched_suggestions = []
            for suggestion in result.get("fields", []):
                field_key = suggestion.get("field")
                if field_key in NORMALIZED_TO_PRETTY:
                    pretty = NORMALIZED_TO_PRETTY[field_key]
                    current_val = prompt_row.get(pretty)
                    if current_val is None:
                        current_val = prompt_row.get(f"{pretty}_pred")
                    suggestion.setdefault("suggested", "")
                    suggestion.setdefault("rationale", "")
                    suggestion.setdefault("decision", "change" if suggestion.get("suggested") else "keep")
                    suggestion["current"] = current_val or ""
                enriched_suggestions.append(suggestion)

            entry = {
                "row": row_meta,
                "provider": provider,
                "model": model,
                "timestamp": datetime.utcnow().isoformat(),
                "suggestions": enriched_suggestions,
                "usage": result.get("usage"),
                "cost_usd": result.get("cost_usd"),
                "error": result.get("error"),
                "prompt": prompt,
            }
            jsonl_file.write(json.dumps(entry, ensure_ascii=False) + "\n")

            # Merge into helper CSV
            if merged_df is not None:
                target_idx = idx
                if "row_id" in merged_df.columns and row_meta.get("row_id") is not None:
                    matches = merged_df[merged_df["row_id"] == row_meta["row_id"]]
                    if not matches.empty:
                        target_idx = matches.index[0]
                for suggestion in entry["suggestions"]:
                    field_key = suggestion.get("field")
                    if field_key not in NORMALIZED_TO_PRETTY:
                        continue
                    pretty = NORMALIZED_TO_PRETTY[field_key]
                    merged_df.loc[target_idx, f"{pretty}_llm_suggested"] = suggestion.get("suggested", "")
                    merged_df.loc[target_idx, f"{pretty}_llm_rationale"] = suggestion.get("rationale", "")
                    merged_df.loc[target_idx, f"{pretty}_llm_confidence"] = suggestion.get("confidence")

            accepted_rows.append(entry)
            processed += 1

            if args.rate_limit:
                time.sleep(args.rate_limit)

    if merged_df is not None:
        merged_df.to_csv(merged_csv_path, index=False, encoding="utf-8-sig", lineterminator="\n")

    summary = {
        "input_csv": str(Path(args.pred_csv).resolve()),
        "review_csv": str(Path(args.review_csv).resolve()) if args.review_csv else None,
        "out_jsonl": str(jsonl_path.resolve()),
        "merged_csv": str(merged_csv_path.resolve()) if merged_df is not None else None,
        "rows_processed": processed,
        "provider": provider,
        "model": model,
        "total_cost_estimate_usd": round(total_cost, 6),
        "dry_run": args.dry_run,
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"✅ Suggestions JSONL: {jsonl_path}")
    if merged_df is not None:
        print(f"✅ Merged helper CSV: {merged_csv_path}")
    print(f"ℹ️  Summary: {summary_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:  # pragma: no cover - interactive convenience
        sys.exit(130)
