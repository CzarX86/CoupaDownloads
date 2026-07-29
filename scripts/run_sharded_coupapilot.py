#!/usr/bin/env python3
"""Run CoupaPilot in resumable shards with consolidated outputs.

Workflow:
1. Split a large input CSV into N shard CSV files.
2. Run CoupaPilot for each shard (non-interactive mode).
3. Resume safely after failures by skipping already processed POs.
4. Consolidate downloaded artifacts into a single folder tree.
5. Build a final consolidated Excel report for all input POs.

This script is intentionally operational and self-contained so it can be run
multiple times with the same --run-dir to continue from where it stopped.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


REPORT_GLOB = "CoupaPilot_Report_*.xlsx"
STATE_FILE = "state.json"
TELEMETRY_FILE = "telemetry.json"
SUMMARY_FILE = "summary.csv"


@dataclass
class ShardState:
    shard_id: int
    shard_dir: str
    input_path: str
    resume_input_path: str
    download_dir: str
    report_path: str
    status: str
    attempts: int
    last_exit_code: int
    started_at: str
    finished_at: str
    processed_non_pending: int
    pending_count: int
    command: str


@dataclass
class RunState:
    version: int
    created_at: str
    updated_at: str
    run_dir: str
    source_input: str
    shard_count: int
    max_workers: int
    use_process_pool: bool
    shards: list[ShardState]


@dataclass
class TelemetryEvent:
    timestamp: str
    level: str
    event: str
    details: dict[str, Any]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def read_csv_auto(path: Path) -> tuple[pd.DataFrame, str, str]:
    encodings = ["utf-8", "utf-8-sig", "latin1", "cp1252", "iso-8859-1", "windows-1252"]
    last_err: Exception | None = None
    for enc in encodings:
        try:
            with path.open("r", encoding=enc, errors="ignore") as f:
                header = f.readline()
            sep = ";" if header.count(";") > header.count(",") else ","
            df = pd.read_csv(path, sep=sep, encoding=enc, index_col=False, header=0, dtype=str, na_filter=False)
            return df, sep, enc
        except Exception as exc:
            last_err = exc
            continue
    raise RuntimeError(f"Failed to read CSV {path}: {last_err}")


def find_col(df: pd.DataFrame, target: str) -> str | None:
    if target in df.columns:
        return target
    low = {str(c).strip().lower().replace("\ufeff", ""): str(c) for c in df.columns}
    return low.get(target.lower())


def normalize_po(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip()


def load_state(path: Path) -> RunState | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    shards = [ShardState(**item) for item in payload.get("shards", [])]
    return RunState(
        version=payload["version"],
        created_at=payload["created_at"],
        updated_at=payload["updated_at"],
        run_dir=payload["run_dir"],
        source_input=payload["source_input"],
        shard_count=payload["shard_count"],
        max_workers=payload["max_workers"],
        use_process_pool=payload["use_process_pool"],
        shards=shards,
    )


def save_state(path: Path, state: RunState) -> None:
    state.updated_at = now_iso()
    payload = asdict(state)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def append_telemetry(run_dir: Path, event: TelemetryEvent) -> None:
    telemetry_path = run_dir / TELEMETRY_FILE
    rows = []
    if telemetry_path.exists():
        rows = json.loads(telemetry_path.read_text(encoding="utf-8"))
    rows.append(asdict(event))
    telemetry_path.write_text(json.dumps(rows, indent=2, ensure_ascii=True), encoding="utf-8")


def split_input_into_shards(source_input: Path, shard_count: int, run_dir: Path) -> list[ShardState]:
    df, sep, enc = read_csv_auto(source_input)
    po_col = find_col(df, "PO_NUMBER")
    if not po_col:
        raise RuntimeError("Column PO_NUMBER not found in input CSV")

    total = len(df)
    if total == 0:
        raise RuntimeError("Input CSV has no rows")

    shards_dir = run_dir / "shards"
    shards_dir.mkdir(parents=True, exist_ok=True)

    blocks = []
    base_size = total // shard_count
    remainder = total % shard_count
    start = 0
    for idx in range(1, shard_count + 1):
        size = base_size + (1 if idx <= remainder else 0)
        end = start + size
        blocks.append((idx, start, end))
        start = end

    shards: list[ShardState] = []
    for shard_id, start, end in blocks:
        shard_dir = shards_dir / f"shard_{shard_id:02d}"
        shard_dir.mkdir(parents=True, exist_ok=True)

        shard_input = shard_dir / "input.csv"
        shard_resume = shard_dir / "resume_input.csv"
        shard_download = shard_dir / "download"
        shard_download.mkdir(parents=True, exist_ok=True)

        chunk = df.iloc[start:end].copy()
        chunk.to_csv(shard_input, index=False, sep=sep, encoding=enc)

        shards.append(
            ShardState(
                shard_id=shard_id,
                shard_dir=str(shard_dir),
                input_path=str(shard_input),
                resume_input_path=str(shard_resume),
                download_dir=str(shard_download),
                report_path="",
                status="pending",
                attempts=0,
                last_exit_code=0,
                started_at="",
                finished_at="",
                processed_non_pending=0,
                pending_count=len(chunk),
                command="",
            )
        )

    append_telemetry(
        run_dir,
        TelemetryEvent(
            timestamp=now_iso(),
            level="INFO",
            event="split_completed",
            details={"rows": total, "shards": shard_count, "separator": sep, "encoding": enc},
        ),
    )
    return shards


def find_latest_report(download_dir: Path) -> Path | None:
    candidates = sorted(download_dir.glob(REPORT_GLOB), key=lambda p: p.stat().st_mtime)
    return candidates[-1] if candidates else None


def summarize_report(report_path: Path) -> tuple[int, int, int]:
    df = pd.read_excel(report_path, sheet_name=0, engine="openpyxl")
    status_col = find_col(df, "STATUS")
    if not status_col:
        return 0, 0, len(df)
    statuses = df[status_col].fillna("").astype(str).str.strip()
    non_pending = int((statuses != "PENDING").sum())
    pending = int((statuses == "PENDING").sum())
    total = int(len(df))
    return non_pending, pending, total


def get_effective_download_root(shard: ShardState) -> Path:
    """Return a stable per-shard download root to prevent timestamp fan-out."""
    shard_dir = Path(shard.shard_dir)
    return shard_dir / f"download_{shard.shard_id:02d}"


def list_shard_download_roots(shard: ShardState) -> list[Path]:
    """List all known download roots for a shard, newest first."""
    roots: list[Path] = []

    stable_root = get_effective_download_root(shard)
    if stable_root.exists():
        roots.append(stable_root)

    legacy_root = Path(shard.download_dir)
    if legacy_root.exists() and legacy_root not in roots:
        roots.append(legacy_root)

    shard_dir = Path(shard.shard_dir)
    ts_roots = [p for p in shard_dir.glob("*_download") if p.is_dir()]
    ts_roots.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for p in ts_roots:
        if p not in roots:
            roots.append(p)

    return roots


def find_latest_report_for_shard(shard: ShardState) -> Path | None:
    """Find the newest report among all shard download roots."""
    candidates: list[Path] = []
    for root in list_shard_download_roots(shard):
        candidates.extend(root.glob(REPORT_GLOB))
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime)
    return candidates[-1]


def build_resume_input(shard: ShardState) -> tuple[Path, int, int]:
    input_path = Path(shard.input_path)
    resume_path = Path(shard.resume_input_path)

    original_df, sep, enc = read_csv_auto(input_path)
    po_col = find_col(original_df, "PO_NUMBER")
    if not po_col:
        raise RuntimeError(f"PO_NUMBER column missing in shard input: {input_path}")

    latest_report = find_latest_report_for_shard(shard)
    if not latest_report:
        # First attempt or no prior report
        shutil.copy2(input_path, resume_path)
        return resume_path, 0, len(original_df)

    report_df = pd.read_excel(latest_report, sheet_name=0, engine="openpyxl")
    report_po_col = find_col(report_df, "PO_NUMBER")
    report_status_col = find_col(report_df, "STATUS")

    if not report_po_col or not report_status_col:
        shutil.copy2(input_path, resume_path)
        return resume_path, 0, len(original_df)

    done_pos = set(
        normalize_po(
            report_df.loc[
                report_df[report_status_col].fillna("").astype(str).str.strip() != "PENDING",
                report_po_col,
            ]
        ).tolist()
    )

    if not done_pos:
        shutil.copy2(input_path, resume_path)
        return resume_path, 0, len(original_df)

    src_pos = normalize_po(original_df[po_col])
    pending_df = original_df.loc[~src_pos.isin(done_pos)].copy()
    pending_df.to_csv(resume_path, index=False, sep=sep, encoding=enc)

    return resume_path, len(done_pos), len(pending_df)


def run_single_shard(
    shard: ShardState,
    run_dir: Path,
    max_workers: int,
    use_process_pool: bool,
    dry_run: bool,
) -> ShardState:
    shard.started_at = now_iso()

    resume_input, already_done, pending_rows = build_resume_input(shard)
    shard.pending_count = pending_rows

    if pending_rows == 0:
        shard.status = "completed"
        shard.finished_at = now_iso()
        latest = find_latest_report_for_shard(shard)
        shard.report_path = str(latest) if latest else ""
        shard.processed_non_pending = already_done
        shard.last_exit_code = 0
        append_telemetry(
            run_dir,
            TelemetryEvent(
                timestamp=now_iso(),
                level="INFO",
                event="shard_skipped_already_complete",
                details={"shard_id": shard.shard_id, "already_done": already_done},
            ),
        )
        return shard

    if dry_run:
        shard.status = "dry_run"
        shard.finished_at = now_iso()
        shard.last_exit_code = 0
        return shard

    effective_download_root = get_effective_download_root(shard)
    effective_download_root.mkdir(parents=True, exist_ok=True)
    shard.download_dir = str(effective_download_root)

    env = os.environ.copy()
    env.update(
        {
            "ENABLE_INTERACTIVE_UI": "false",
            "UI_MODE": "none",
            "EXCEL_FILE_PATH": str(resume_input),
            "DOWNLOAD_FOLDER": str(effective_download_root),
            "MAX_PARALLEL_WORKERS": str(max_workers),
            "PROC_WORKERS": str(max_workers),
            "USE_PROCESS_POOL": "true" if use_process_pool else "false",
            "PYTHONUNBUFFERED": "1",
        }
    )

    cmd = [sys.executable, "-m", "src.main"]
    shard.command = " ".join(cmd)
    shard.attempts += 1

    log_dir = run_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_log = log_dir / f"shard_{shard.shard_id:02d}_attempt_{shard.attempts:02d}.log"

    t0 = time.perf_counter()
    with stdout_log.open("w", encoding="utf-8") as f:
        proc = subprocess.run(cmd, env=env, cwd=str(Path(__file__).resolve().parents[1]), stdout=f, stderr=subprocess.STDOUT)

    elapsed = round(time.perf_counter() - t0, 2)
    shard.last_exit_code = int(proc.returncode)

    latest = find_latest_report_for_shard(shard)
    if latest:
        shard.report_path = str(latest)
        non_pending, pending, _total = summarize_report(latest)
        shard.processed_non_pending = non_pending
        shard.pending_count = pending

    if proc.returncode == 0 and shard.pending_count == 0:
        shard.status = "completed"
    elif proc.returncode == 0:
        shard.status = "partial"
    else:
        shard.status = "failed"

    shard.finished_at = now_iso()

    append_telemetry(
        run_dir,
        TelemetryEvent(
            timestamp=now_iso(),
            level="INFO" if shard.last_exit_code == 0 else "ERROR",
            event="shard_finished",
            details={
                "shard_id": shard.shard_id,
                "attempt": shard.attempts,
                "status": shard.status,
                "exit_code": shard.last_exit_code,
                "elapsed_seconds": elapsed,
                "processed_non_pending": shard.processed_non_pending,
                "pending_count": shard.pending_count,
                "log": str(stdout_log),
            },
        ),
    )

    return shard


def consolidate_downloads(state: RunState, run_dir: Path) -> Path:
    consolidated_root = run_dir / "consolidated" / "downloads"
    consolidated_root.mkdir(parents=True, exist_ok=True)

    for shard in state.shards:
        for shard_download in list_shard_download_roots(shard):
            if not shard_download.exists():
                continue

            for item in shard_download.iterdir():
                if item.name.startswith("CoupaPilot_Report_"):
                    continue

                target = consolidated_root / item.name
                if target.exists():
                    # Avoid collisions between shard outputs with same folder/file name.
                    stem = target.stem
                    suffix = target.suffix
                    counter = 2
                    while True:
                        alt = consolidated_root / f"{stem}__dup{counter}{suffix}"
                        if not alt.exists():
                            target = alt
                            break
                        counter += 1

                shutil.move(str(item), str(target))

    return consolidated_root


def build_consolidated_report(state: RunState, run_dir: Path) -> Path:
    source_input = Path(state.source_input)
    input_df, _sep, _enc = read_csv_auto(source_input)
    po_col = find_col(input_df, "PO_NUMBER")
    if not po_col:
        raise RuntimeError("PO_NUMBER column not found in source input")

    merged = input_df.copy().astype(object)

    report_frames: list[pd.DataFrame] = []
    for shard in state.shards:
        report_path = Path(shard.report_path) if shard.report_path else None
        if not report_path or not report_path.exists():
            continue
        df = pd.read_excel(report_path, sheet_name=0, engine="openpyxl")
        report_frames.append(df)

    if report_frames:
        all_reports = pd.concat(report_frames, ignore_index=True)
    else:
        all_reports = pd.DataFrame()

    if not all_reports.empty:
        report_po_col = find_col(all_reports, "PO_NUMBER")
        if report_po_col:
            all_reports[report_po_col] = normalize_po(all_reports[report_po_col])
            merged[po_col] = normalize_po(merged[po_col])

            status_col = find_col(all_reports, "STATUS")
            if status_col:
                all_reports = all_reports.loc[all_reports[status_col].fillna("").astype(str).str.strip() != "PENDING"].copy()

            all_reports = all_reports.drop_duplicates(subset=[report_po_col], keep="last")

            sync_cols = [
                "STATUS",
                "SUPPLIER",
                "ATTACHMENTS_FOUND",
                "ATTACHMENTS_DOWNLOADED",
                "AttachmentName",
                "LAST_PROCESSED",
                "ERROR_MESSAGE",
                "DOWNLOAD_FOLDER",
                "COUPA_URL",
            ]

            merged_idx = merged.set_index(po_col)
            reports_idx = all_reports.set_index(report_po_col)

            for col in sync_cols:
                target_col = find_col(merged_idx, col)
                source_col = find_col(reports_idx, col)
                if not target_col or not source_col:
                    continue
                patch = reports_idx[source_col]
                patch = patch[~patch.index.duplicated(keep="last")]
                merged_idx.loc[merged_idx.index.isin(patch.index), target_col] = patch

            merged = merged_idx.reset_index()

    report_dir = run_dir / "consolidated"
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_path = report_dir / f"CoupaPilot_Report_Consolidated_{ts}.xlsx"

    with pd.ExcelWriter(report_path, engine="openpyxl") as writer:
        merged.to_excel(writer, sheet_name="Report", index=False)

    return report_path


def write_summary(state: RunState, run_dir: Path) -> Path:
    rows = []
    for shard in state.shards:
        rows.append(
            {
                "shard_id": shard.shard_id,
                "status": shard.status,
                "attempts": shard.attempts,
                "processed_non_pending": shard.processed_non_pending,
                "pending_count": shard.pending_count,
                "last_exit_code": shard.last_exit_code,
                "input_path": shard.input_path,
                "report_path": shard.report_path,
                "download_dir": shard.download_dir,
                "started_at": shard.started_at,
                "finished_at": shard.finished_at,
            }
        )
    df = pd.DataFrame(rows)
    out = run_dir / SUMMARY_FILE
    df.to_csv(out, index=False)
    return out


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run CoupaPilot in resumable shards")
    parser.add_argument(
        "--input",
        default="data/input/input.csv",
        help="Source CSV with PO_NUMBER column",
    )
    parser.add_argument(
        "--shards",
        type=int,
        default=8,
        help="Number of shard files to create",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Workers passed to CoupaPilot for each shard",
    )
    parser.add_argument(
        "--run-dir",
        default="",
        help="Existing run dir to resume, or empty to create a new one",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue processing other shards when one shard fails",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only prepare shards/state without executing CoupaPilot",
    )
    parser.add_argument(
        "--use-process-pool",
        action="store_true",
        help="Force process pool execution for each shard",
    )
    return parser


def initialize_state(args: argparse.Namespace, project_root: Path) -> tuple[RunState, Path]:
    source_input = (project_root / args.input).resolve()
    if not source_input.exists():
        raise RuntimeError(f"Input CSV not found: {source_input}")

    if args.run_dir:
        run_dir = Path(args.run_dir).expanduser().resolve()
    else:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir = (project_root / "data" / "downloads" / f"{ts}_sharded_run").resolve()

    run_dir.mkdir(parents=True, exist_ok=True)
    state_path = run_dir / STATE_FILE

    state = load_state(state_path)
    if state:
        return state, state_path

    shards = split_input_into_shards(source_input, args.shards, run_dir)
    state = RunState(
        version=1,
        created_at=now_iso(),
        updated_at=now_iso(),
        run_dir=str(run_dir),
        source_input=str(source_input),
        shard_count=args.shards,
        max_workers=args.max_workers,
        use_process_pool=bool(args.use_process_pool),
        shards=shards,
    )
    save_state(state_path, state)
    return state, state_path


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]

    state, state_path = initialize_state(args, project_root)
    run_dir = Path(state.run_dir)

    append_telemetry(
        run_dir,
        TelemetryEvent(
            timestamp=now_iso(),
            level="INFO",
            event="run_started",
            details={
                "run_dir": state.run_dir,
                "source_input": state.source_input,
                "shards": state.shard_count,
                "max_workers": state.max_workers,
                "use_process_pool": state.use_process_pool,
                "dry_run": bool(args.dry_run),
            },
        ),
    )

    exit_code = 0
    for idx, shard in enumerate(state.shards, start=1):
        if shard.status == "completed" and Path(shard.report_path).exists():
            print(f"[{idx}/{len(state.shards)}] shard_{shard.shard_id:02d}: already completed, skipping")
            continue

        print(f"[{idx}/{len(state.shards)}] shard_{shard.shard_id:02d}: processing")
        state.shards[idx - 1] = run_single_shard(
            shard,
            run_dir=run_dir,
            max_workers=state.max_workers,
            use_process_pool=state.use_process_pool,
            dry_run=bool(args.dry_run),
        )
        save_state(state_path, state)

        s = state.shards[idx - 1]
        print(
            f"  -> status={s.status} attempt={s.attempts} "
            f"processed_non_pending={s.processed_non_pending} pending={s.pending_count} exit={s.last_exit_code}"
        )

        if s.status == "failed":
            exit_code = 1
            if not args.continue_on_error:
                print("Stopping on first failed shard. Re-run with --run-dir to resume.")
                break

    summary_path = write_summary(state, run_dir)

    # Finalization only when every shard is fully complete.
    all_completed = all(s.status == "completed" and s.pending_count == 0 for s in state.shards)
    consolidated_downloads = None
    consolidated_report = None

    if all_completed and not args.dry_run:
        consolidated_downloads = consolidate_downloads(state, run_dir)
        consolidated_report = build_consolidated_report(state, run_dir)

        append_telemetry(
            run_dir,
            TelemetryEvent(
                timestamp=now_iso(),
                level="INFO",
                event="run_consolidated",
                details={
                    "consolidated_downloads": str(consolidated_downloads),
                    "consolidated_report": str(consolidated_report),
                },
            ),
        )

    print("\nRun finished")
    print(f"Run dir: {run_dir}")
    print(f"State: {state_path}")
    print(f"Summary: {summary_path}")
    if consolidated_downloads:
        print(f"Consolidated downloads: {consolidated_downloads}")
    if consolidated_report:
        print(f"Consolidated report: {consolidated_report}")

    pending_shards = [s.shard_id for s in state.shards if not (s.status == "completed" and s.pending_count == 0)]
    if pending_shards:
        print(f"Pending shards: {pending_shards}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
