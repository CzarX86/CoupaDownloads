#!/usr/bin/env python3
"""Generate synthetic supervision pairs using an external LLM.

The helper ingests a supervised dataset (``supervised.jsonl``) or the
Sentence Transformers pair dataset (``st_pairs.jsonl``) and asks the LLM to
produce paraphrases/synonyms for categorical values. The resulting pairs are
compatible with ``feedback_cli.py train-st`` and are meant to be reviewed or
combined with the existing dataset.

Example (DeepSeek default)::

    poetry run python tools/self_augment.py --input datasets/supervised.jsonl \
        --out datasets/st_pairs_aug.jsonl --fields contract_type,managed_by

Run in dry mode to preview the flow without API calls::

    poetry run python tools/self_augment.py --input datasets/supervised.jsonl --out tmp.jsonl --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

try:
    import httpx
except ImportError as exc:  # pragma: no cover - tooling requirement
    raise SystemExit(
        "httpx is required to use self-augmentation helpers. Install project dependencies first."
    ) from exc

from tools.feedback_utils import NORMALIZED_TO_PRETTY


DEFAULT_FIELDS = (
    "contract_type",
    "managed_by",
    "sow_currency",
    "platform_technology",
    "type_of_contract_l1",
    "type_of_contract_l2",
)


def _ensure_path(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


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


def _load_values(path: str | Path, fields: Iterable[str]) -> Dict[str, List[str]]:
    values: Dict[str, set[str]] = {f: set() for f in fields}
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"Input file not found: {p}")

    with open(p, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            labels = record.get("labels") or {}
            field = record.get("field")
            if labels:
                for key in fields:
                    if key in labels and labels[key]:
                        values[key].add(str(labels[key]).strip())
            if field and field in fields:
                text1 = record.get("text1")
                text2 = record.get("text2")
                for val in (text1, text2):
                    if val:
                        values[field].add(str(val).strip())
    return {k: sorted(v) for k, v in values.items() if v}


def _batched(iterable: Iterable[str], size: int) -> Iterable[List[str]]:
    batch: List[str] = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def _simulate(field: str, originals: List[str], per_value: int) -> Dict[str, List[str]]:
    rng = random.Random(1337)
    augmented: Dict[str, List[str]] = {}
    for value in originals:
        suggestions = []
        for i in range(per_value):
            suffix = rng.choice(["pro", "alt", "v2", "beta", "prime"])
            suggestions.append(f"{value} {suffix}")
        augmented[value] = suggestions
    return augmented


def _call_llm(
    provider: str,
    model: str,
    api_key: str,
    field: str,
    originals: List[str],
    per_value: int,
    temperature: float,
    top_p: float,
    timeout: float,
) -> Dict[str, List[str]]:
    if provider == "deepseek":
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    else:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    prompt = (
        "You generate synthetic training data. For each value listed return a JSON object "
        "with key 'augmented' mapping each original string to an array of up to "
        f"{per_value} paraphrases appropriate for the business field '{field}'. "
        "Do not introduce personally identifiable information. Output strictly JSON.\n"
    )
    prompt += "Original values:" + "\n".join(f"- {value}" for value in originals)

    payload = {
        "model": model,
        "temperature": temperature,
        "top_p": top_p,
        "messages": [
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": prompt},
        ],
    }

    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    message = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    try:
        parsed = json.loads(message)
    except json.JSONDecodeError:
        return {}

    return parsed.get("augmented", {})


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate LLM-based ST augmentation pairs")
    parser.add_argument("--input", required=True, help="supervised.jsonl or st_pairs.jsonl")
    parser.add_argument("--out", required=True, help="Output JSONL with augmented pairs")
    parser.add_argument("--fields", help="Comma-separated normalized field names (defaults to categorical core)")
    parser.add_argument("--provider", choices=["deepseek", "openai"], default="deepseek")
    parser.add_argument("--model", help="Model identifier (provider specific)")
    parser.add_argument("--api-key", help="Explicit API key; otherwise env var is used")
    parser.add_argument("--per-value", type=int, default=3, help="Number of paraphrases per value")
    parser.add_argument("--batch-size", type=int, default=8, help="Values per LLM call")
    parser.add_argument("--temperature", type=float, default=0.6)
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--rate-limit", type=float, default=0.0)
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    fields = [f.strip().lower() for f in (args.fields.split(",") if args.fields else DEFAULT_FIELDS)]
    fields = [f for f in fields if f in NORMALIZED_TO_PRETTY]
    if not fields:
        raise SystemExit("No valid fields provided.")

    values = _load_values(args.input, fields)
    if not values:
        raise SystemExit("No values found for the selected fields.")

    provider = args.provider
    model = args.model or ("deepseek-reasoner" if provider == "deepseek" else "gpt-4o-mini")
    if not args.dry_run:
        api_key = _resolve_api_key(provider, args.api_key)
    else:
        api_key = ""

    out_path = _ensure_path(args.out)
    rng = random.Random(2024)
    generated_pairs = 0
    stats = {
        "provider": provider,
        "model": model,
        "fields": {},
        "dry_run": args.dry_run,
        "timestamp": datetime.utcnow().isoformat(),
    }

    with open(out_path, "w", encoding="utf-8") as fh:
        for field, field_values in values.items():
            field_stats = {"original_values": len(field_values), "augmented": 0}
            augmented: Dict[str, List[str]] = defaultdict(list)
            batches = list(_batched(field_values, args.batch_size))
            for batch in batches:
                if args.dry_run:
                    batch_aug = _simulate(field, batch, args.per_value)
                else:
                    try:
                        batch_aug = _call_llm(
                            provider=provider,
                            model=model,
                            api_key=api_key,
                            field=field,
                            originals=batch,
                            per_value=args.per_value,
                            temperature=args.temperature,
                            top_p=args.top_p,
                            timeout=args.timeout,
                        )
                    except Exception as exc:  # noqa: BLE001
                        batch_aug = {}
                        field_stats.setdefault("errors", []).append(str(exc))
                for original, suggestions in batch_aug.items():
                    for suggestion in suggestions[: args.per_value]:
                        suggestion = suggestion.strip()
                        if not suggestion:
                            continue
                        fh.write(
                            json.dumps(
                                {
                                    "text1": original,
                                    "text2": suggestion,
                                    "label": 1.0,
                                    "field": field,
                                    "source": "llm_self_augment",
                                    "created_at": datetime.utcnow().isoformat(),
                                },
                                ensure_ascii=False,
                            )
                            + "\n"
                        )
                        augmented[original].append(suggestion)
                        generated_pairs += 1
                if args.rate_limit:
                    time.sleep(args.rate_limit)

            field_stats["augmented"] = sum(len(v) for v in augmented.values())
            stats["fields"][field] = field_stats

    stats["generated_pairs"] = generated_pairs
    stats_path = out_path.with_suffix(".meta.json")
    with open(stats_path, "w", encoding="utf-8") as meta:
        json.dump(stats, meta, indent=2, ensure_ascii=False)

    print(f"✅ Augmented pairs: {out_path} ({generated_pairs} records)")
    print(f"ℹ️  Metadata: {stats_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:  # pragma: no cover
        sys.exit(130)
