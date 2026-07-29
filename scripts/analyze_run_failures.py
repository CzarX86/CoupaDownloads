#!/usr/bin/env python3
"""Analyze CoupaPilot runtime logs and summarize failure root causes.

Usage:
  python scripts/analyze_run_failures.py path/to/run.log
  python scripts/analyze_run_failures.py path/to/run.log --json
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


PO_RE = re.compile(r"\bPO\d{5,}\b", re.IGNORECASE)
PROCESSING_PO_RE = re.compile(r"Processing PO\s*#?(PO\d{5,})", re.IGNORECASE)


@dataclass(frozen=True)
class CauseRule:
    cause: str
    patterns: Tuple[re.Pattern[str], ...]


CAUSE_RULES: Tuple[CauseRule, ...] = (
    CauseRule(
        "SESSION_AUTH",
        (
            re.compile(r"session\s+expired", re.IGNORECASE),
            re.compile(r"not\s+authenticated", re.IGNORECASE),
            re.compile(r"failed\s+to\s+authenticate", re.IGNORECASE),
            re.compile(r"login\s+page", re.IGNORECASE),
            re.compile(r"okta", re.IGNORECASE),
            re.compile(r"invalid\s+session", re.IGNORECASE),
        ),
    ),
    CauseRule(
        "ACCESS_DENIED",
        (
            re.compile(r"access\s+denied", re.IGNORECASE),
            re.compile(r"not\s+authorized", re.IGNORECASE),
            re.compile(r"forbidden\b", re.IGNORECASE),
        ),
    ),
    CauseRule(
        "RATE_LIMIT",
        (
            re.compile(r"rate\s*limit", re.IGNORECASE),
            re.compile(r"too\s+many\s+requests", re.IGNORECASE),
            re.compile(r"http\s*429", re.IGNORECASE),
        ),
    ),
    CauseRule(
        "TIMEOUT",
        (
            re.compile(r"timed?\s*out", re.IGNORECASE),
            re.compile(r"timeout", re.IGNORECASE),
            re.compile(r"wait timeout", re.IGNORECASE),
        ),
    ),
    CauseRule(
        "DRIVER_BROWSER_CRASH",
        (
            re.compile(r"msedgedriver", re.IGNORECASE),
            re.compile(r"driver\.quit\(\) timed out", re.IGNORECASE),
            re.compile(r"no\s+window\s+handles", re.IGNORECASE),
            re.compile(r"invalid\s*session\s*id", re.IGNORECASE),
            re.compile(r"web\s*driver.*failed", re.IGNORECASE),
        ),
    ),
    CauseRule(
        "NETWORK",
        (
            re.compile(r"connection\s+reset", re.IGNORECASE),
            re.compile(r"connection\s+refused", re.IGNORECASE),
            re.compile(r"dns", re.IGNORECASE),
            re.compile(r"temporary\s+failure", re.IGNORECASE),
            re.compile(r"name\s+or\s+service\s+not\s+known", re.IGNORECASE),
        ),
    ),
    CauseRule(
        "PO_NOT_FOUND",
        (
            re.compile(r"po[_\s-]*not[_\s-]*found", re.IGNORECASE),
            re.compile(r"couldn['’]?t\s+find\s+what\s+you\s+wanted", re.IGNORECASE),
        ),
    ),
)


def classify_line(line: str) -> Optional[str]:
    lower = line.lower()
    if "po_number;status;" in lower:
        return None
    if "error_message;download_folder" in lower:
        return None
    if line.startswith("(.venv)"):
        return None

    for rule in CAUSE_RULES:
        if any(pattern.search(line) for pattern in rule.patterns):
            return rule.cause

    strong_failure_markers = (
        "[error",
        "traceback",
        "❌",
        "failed to",
        "startup failed",
        "runtimeerror",
        "exception",
    )
    if any(marker in lower for marker in strong_failure_markers):
        return "UNKNOWN_FAILURE"
    return None


def extract_po(line: str, current_po: Optional[str]) -> Optional[str]:
    processing_match = PROCESSING_PO_RE.search(line)
    if processing_match:
        return processing_match.group(1).upper()

    direct_match = PO_RE.search(line)
    if direct_match:
        return direct_match.group(0).upper()

    return current_po


def analyze_lines(lines: Iterable[str]) -> Dict[str, object]:
    cause_counts: Counter[str] = Counter()
    po_cause_counts: Dict[str, Counter[str]] = defaultdict(Counter)
    examples: Dict[str, List[str]] = defaultdict(list)

    current_po: Optional[str] = None
    processed_pos: set[str] = set()

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        current_po = extract_po(line, current_po)
        if current_po:
            processed_pos.add(current_po)

        cause = classify_line(line)
        if not cause:
            continue

        cause_counts[cause] += 1
        po_key = current_po or "UNKNOWN_PO"
        po_cause_counts[po_key][cause] += 1

        if len(examples[cause]) < 5:
            examples[cause].append(line[:280])

    top_pos = sorted(
        (
            {
                "po": po,
                "total_failure_signals": sum(counter.values()),
                "top_cause": counter.most_common(1)[0][0] if counter else "UNKNOWN",
                "cause_breakdown": dict(counter.most_common()),
            }
            for po, counter in po_cause_counts.items()
        ),
        key=lambda item: item["total_failure_signals"],
        reverse=True,
    )

    return {
        "processed_po_candidates": len(processed_pos),
        "failure_signals_total": int(sum(cause_counts.values())),
        "cause_ranking": dict(cause_counts.most_common()),
        "top_pos": top_pos[:25],
        "examples": dict(examples),
    }


def print_human_summary(result: Dict[str, object], source: Path) -> None:
    print(f"SOURCE_LOG: {source}")
    print(f"PO_CANDIDATES: {result['processed_po_candidates']}")
    print(f"FAILURE_SIGNALS: {result['failure_signals_total']}")

    ranking = result["cause_ranking"]
    print("CAUSE_RANKING:")
    if not ranking:
        print("  (no failure signals found)")
    else:
        for cause, count in ranking.items():
            print(f"  {cause}: {count}")

    print("TOP_POS:")
    top_pos = result["top_pos"]
    if not top_pos:
        print("  (none)")
    else:
        for item in top_pos[:10]:
            po = item["po"]
            total = item["total_failure_signals"]
            top = item["top_cause"]
            print(f"  {po}: {total} signals (top={top})")

    print("EXAMPLES:")
    examples = result["examples"]
    if not examples:
        print("  (none)")
    else:
        for cause, lines in examples.items():
            print(f"  {cause}:")
            for line in lines[:2]:
                print(f"    - {line}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze CoupaPilot runtime failure causes from logs")
    parser.add_argument("log_file", type=Path, help="Path to runtime log file")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.log_file.exists():
        print(f"ERROR: log file not found: {args.log_file}")
        return 2

    with args.log_file.open("r", encoding="utf-8", errors="replace") as fh:
        result = analyze_lines(fh)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human_summary(result, args.log_file)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
