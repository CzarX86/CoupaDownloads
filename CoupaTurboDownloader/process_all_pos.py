import os
import sys
import asyncio
import time
import argparse
import json
from datetime import datetime
from pathlib import Path, PurePosixPath
import pandas as pd
from src.db.session_db import SessionDB
from src.engine.crawler import CoupaCrawler
from src.engine.authenticator import load_cached_cookies, validate_cookies_detailed, get_coupa_cookies
from src.engine.msg_converter import find_msg_files, MsgToPdfConverter

# CSV alongside this script (or override via INPUT_CSV env var)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_CSV = os.environ.get("INPUT_CSV", os.path.join(_SCRIPT_DIR, "input.csv"))
DOWNLOAD_DIR = os.path.expanduser("~/Downloads/CoupaAttachments")
DB_PATH = os.path.expanduser("~/.coupa_turbo/cli_sessions.db")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process Coupa POs and download attachments")
    parser.add_argument(
        "--retry-last-errors",
        action="store_true",
        help="Create a new session with only ERROR rows from latest session",
    )
    parser.add_argument(
        "--download-root",
        default=DOWNLOAD_DIR,
        help="Base download directory (default: ~/Downloads/CoupaAttachments)",
    )
    parser.add_argument(
        "--run-dir",
        default=None,
        help="Use this exact run directory instead of creating a timestamped directory",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="Concurrent downloads (1-8, default: 4)",
    )
    parser.add_argument(
        "--retry-attempts",
        type=int,
        default=None,
        help="Total attempts per PO (1-3; GUI settings may override)",
    )
    parser.add_argument(
        "--retry-session-id",
        type=int,
        default=None,
        help="Optional source session id for retry mode (uses latest with ERROR if omitted)",
    )
    parser.add_argument(
        "--retry-po",
        default=None,
        help="Retry one PO in a new session, preserving valid files",
    )
    parser.add_argument(
        "--retry-in-place-po",
        default=None,
        help="Retry one PO without creating a new session id",
    )
    parser.add_argument(
        "--retry-in-place-errors",
        action="store_true",
        help="Retry ERROR/SKIPPED rows in the existing session",
    )
    parser.add_argument(
        "--provisional-retry",
        action="store_true",
        help="Run an edited PO in staging until the GUI commits or discards it",
    )
    parser.add_argument(
        "--retry-attempt-id",
        type=int,
        default=None,
        help="Provisional retry attempt id",
    )
    parser.add_argument(
        "--retry-staging-dir",
        default=None,
        help="Temporary directory for provisional retry files",
    )
    parser.add_argument(
        "--retry-incomplete-session-id",
        type=int,
        default=None,
        help="Retry only PENDING+ERROR rows from a specific interrupted session",
    )
    parser.add_argument(
        "--disable-circuit-breaker",
        action="store_true",
        help="Disable company-level circuit breaker and process 100%% of rows",
    )
    parser.add_argument(
        "--skip-msg-to-pdf",
        action="store_true",
        help="Skip automatic conversion of downloaded .msg files into .pdf",
    )
    parser.add_argument(
        "--overwrite-msg-pdf",
        action="store_true",
        help="Overwrite existing generated PDF files for .msg conversion",
    )
    parser.add_argument(
        "--msg-processing",
        choices=["disabled", "convert", "convert_extract"],
        default=None,
        help="MSG handling: disabled, convert to PDF, or convert and extract attachments",
    )
    parser.add_argument(
        "--deduplicate-files",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Identify identical files by SHA-256 and create hard-link/reference duplicates",
    )
    parser.add_argument(
        "--execution-type",
        choices=["AUTO", "PROD", "TEST"],
        default="AUTO",
        help="Session classification for retention policy (default: AUTO)",
    )
    return parser.parse_args()


def _detect_execution_type_from_name(name: str) -> str:
    text = (name or "").lower()
    test_tokens = ["test", "sample", "random", "probe", "debug"]
    return "TEST" if any(token in text for token in test_tokens) else "PROD"


def resolve_execution_type(args: argparse.Namespace, input_name: str, source_session_id: int | None = None, db: SessionDB | None = None) -> str:
    choice = (args.execution_type or "AUTO").upper()
    if choice in {"PROD", "TEST"}:
        return choice

    if source_session_id and db is not None:
        return db.get_session_execution_type(source_session_id)

    return _detect_execution_type_from_name(input_name)


def build_run_download_dir(download_root: str, mode: str, run_dir: str | None = None) -> str:
    if run_dir:
        resolved = os.path.abspath(os.path.expanduser(run_dir))
        os.makedirs(resolved, exist_ok=True)
        return resolved
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    resolved = os.path.join(os.path.expanduser(download_root), f"run_{stamp}_{mode}")
    os.makedirs(resolved, exist_ok=True)
    return resolved


def _detect_csv_encoding(filepath: str) -> str:
    raw = Path(filepath).read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            raw.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    return "latin-1"


def _read_csv_text(filepath: str) -> str:
    path = Path(filepath)
    return path.read_bytes().decode(_detect_csv_encoding(filepath), errors="replace")


def detect_separator(filepath: str) -> str:
    sample = _read_csv_text(filepath)[:4096]
    return ";" if sample.count(";") > sample.count(",") else ","


def read_input_dataframe(filepath: str) -> pd.DataFrame:
    """Read the same CSV/XLSX input in the CLI and GUI workflows."""
    path = Path(filepath)
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
        return pd.read_excel(path, dtype=str).fillna("")
    if suffix == ".xls":
        return pd.read_excel(path, dtype=str).fillna("")
    return pd.read_csv(
        path,
        sep=detect_separator(str(path)),
        dtype=str,
        encoding=_detect_csv_encoding(str(path)),
    ).fillna("")


def _clean_folder_part(value: str) -> str:
    cleaned = str(value or "").strip()
    if cleaned.lower() in {"", "nan", "none"}:
        cleaned = "Unknown"
    cleaned = cleaned.replace("/", "_").replace("\\", "_")
    cleaned = "_".join(cleaned.split())
    cleaned = cleaned.strip("._")
    return cleaned or "Unknown"


def _extract_hierarchy_columns(
    df: pd.DataFrame,
    requested_order: list[str] | None = None,
) -> tuple[list[str], bool]:
    sep_col = None
    for c in df.columns:
        if str(c).strip() == "<|>":
            sep_col = c
            break
    if sep_col is None:
        return [], False

    cols = list(df.columns)
    sep_idx = cols.index(sep_col)
    hierarchy_cols = cols[sep_idx + 1 :]
    if requested_order:
        requested = [str(column) for column in requested_order if str(column) in hierarchy_cols]
        hierarchy_cols = requested + [column for column in hierarchy_cols if column not in requested]
    if not hierarchy_cols:
        return [], False

    for col in hierarchy_cols:
        series = df[col].fillna("").astype(str).str.strip()
        series = series[(series != "") & (series.str.lower() != "nan")]
        if not series.empty:
            return hierarchy_cols, True
    return hierarchy_cols, False


def _build_output_subdir(row: pd.Series, supplier: str, hierarchy_cols: list[str], has_hierarchy_data: bool) -> str:
    if has_hierarchy_data and hierarchy_cols:
        parts = [_clean_folder_part(row.get(col, "")) for col in hierarchy_cols]
    else:
        parts = [str(supplier).strip() or "Unknown"]
    return PurePosixPath(*parts).as_posix()


def build_output_subdir_map_from_csv(input_csv: str) -> dict[str, str]:
    if not input_csv or not os.path.exists(input_csv):
        return {}

    df = read_input_dataframe(input_csv)
    hierarchy_cols, has_hierarchy_data = _extract_hierarchy_columns(df)
    po_to_subdir: dict[str, str] = {}

    for _, row in df.iterrows():
        po = str(row.get("PO_NUMBER", "")).strip()
        supplier = str(row.get("SUPPLIER", "")).strip()
        if po and po.lower() != "nan" and supplier and supplier.lower() != "nan":
            po_to_subdir[po] = _build_output_subdir(row, supplier, hierarchy_cols, has_hierarchy_data)
    return po_to_subdir


def list_attachment_names(download_folder: str) -> str:
    if not isinstance(download_folder, (str, os.PathLike)):
        return ""
    if not download_folder or not os.path.isdir(download_folder):
        return ""
    names = [
        name
        for name in sorted(os.listdir(download_folder))
        if os.path.isfile(os.path.join(download_folder, name))
    ]
    return " | ".join(names)


def export_original_like_excel_report(
    db: SessionDB,
    session_id: int,
    report_path: str,
    input_csv: str | None = None,
) -> str:
    cursor = db.conn.cursor()
    rows = cursor.execute(
        """
        SELECT po_number, company_code, status, attachment_count, error_message, remarks, download_folder, updated_at
        FROM po_downloads
        WHERE session_id = ?
        ORDER BY id ASC
        """,
        (session_id,),
    ).fetchall()

    db_df = pd.DataFrame([dict(r) for r in rows])
    if db_df.empty:
        db_df = pd.DataFrame(
            columns=[
                "po_number",
                "company_code",
                "status",
                "attachment_count",
                "error_message",
                "remarks",
                "download_folder",
                "updated_at",
            ]
        )

    db_df["attachment_count"] = db_df["attachment_count"].fillna(0).astype(int)
    db_df["AttachmentName"] = db_df["download_folder"].apply(list_attachment_names)
    db_df["ATTACHMENTS_FOUND"] = db_df["attachment_count"]
    db_df["ATTACHMENTS_DOWNLOADED"] = db_df.apply(
        lambda r: r["attachment_count"] if str(r["status"]).upper() == "SUCCESS" else 0,
        axis=1,
    )
    db_df["STATUS"] = db_df["status"]
    db_df["ERROR_MESSAGE"] = db_df["error_message"].fillna("")
    db_df["REMARKS"] = db_df["remarks"].fillna("")
    db_df["DOWNLOAD_FOLDER"] = db_df["download_folder"].fillna("")
    db_df["LAST_PROCESSED"] = db_df["updated_at"].fillna("")
    db_df["COUPA_URL"] = db_df["po_number"].apply(
        lambda po: f"https://unilever.coupahost.com/order_headers/{str(po)[2:]}"
        if str(po).upper().startswith(("PO", "PM"))
        else f"https://unilever.coupahost.com/order_headers/{po}"
    )

    report_cols = {
        "po_number": "PO_NUMBER",
        "company_code": "SUPPLIER",
        "STATUS": "STATUS",
        "ATTACHMENTS_FOUND": "ATTACHMENTS_FOUND",
        "ATTACHMENTS_DOWNLOADED": "ATTACHMENTS_DOWNLOADED",
        "AttachmentName": "AttachmentName",
        "LAST_PROCESSED": "LAST_PROCESSED",
        "ERROR_MESSAGE": "ERROR_MESSAGE",
        "REMARKS": "REMARKS",
        "DOWNLOAD_FOLDER": "DOWNLOAD_FOLDER",
        "COUPA_URL": "COUPA_URL",
    }
    mapped = db_df[list(report_cols.keys())].rename(columns=report_cols)

    if input_csv and os.path.exists(input_csv):
        source_df = read_input_dataframe(input_csv)
        if "PO_NUMBER" in source_df.columns:
            source_df["PO_NUMBER"] = source_df["PO_NUMBER"].astype(str).str.strip()

        merged = source_df.merge(
            mapped,
            on="PO_NUMBER",
            how="left",
            suffixes=("", "_NEW"),
        )

        for col in [
            "STATUS",
            "ATTACHMENTS_FOUND",
            "ATTACHMENTS_DOWNLOADED",
            "AttachmentName",
            "LAST_PROCESSED",
            "ERROR_MESSAGE",
            "REMARKS",
            "DOWNLOAD_FOLDER",
            "COUPA_URL",
        ]:
            new_col = f"{col}_NEW"
            if new_col in merged.columns:
                merged[col] = merged[new_col].fillna(merged.get(col, ""))
                merged = merged.drop(columns=[new_col])

        if "SUPPLIER_NEW" in merged.columns:
            if "SUPPLIER" in merged.columns:
                merged["SUPPLIER"] = merged["SUPPLIER"].replace("", pd.NA).fillna(merged["SUPPLIER_NEW"])
                merged["SUPPLIER"] = merged["SUPPLIER"].fillna("")
            merged = merged.drop(columns=["SUPPLIER_NEW"])

        out_df = merged
    else:
        out_df = mapped.copy()
        out_df.insert(3, "Legal Entity", out_df["SUPPLIER"])
        out_df["<|>"] = ""

    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    out_df.to_excel(report_path, index=False)
    return report_path


def create_session_from_csv(
    db: SessionDB,
    input_csv: str,
    execution_type: str = "PROD",
    hierarchy_order: list[str] | None = None,
) -> tuple[int, int]:
    cursor = db.conn.cursor()
    df = read_input_dataframe(input_csv)
    hierarchy_cols, has_hierarchy_data = _extract_hierarchy_columns(df, hierarchy_order)
    session_id = db.create_session(os.path.basename(input_csv), execution_type=execution_type)

    count = 0
    for _, row in df.iterrows():
        po = str(row.get("PO_NUMBER", "")).strip()
        company = str(row.get("SUPPLIER", "")).strip()
        if po and po.lower() != "nan" and company and company.lower() != "nan":
            output_subdir = _build_output_subdir(row, company, hierarchy_cols, has_hierarchy_data)
            cursor.execute(
                "INSERT OR IGNORE INTO po_downloads (session_id, po_number, company_code, output_subdir, status) VALUES (?, ?, ?, ?, 'PENDING')",
                (session_id, po, company, output_subdir),
            )
            count += 1
    db.conn.commit()
    return session_id, count


def create_retry_session_from_last_errors(
    db: SessionDB,
    input_csv: str | None = None,
    source_session_id: int | None = None,
    execution_type: str = "PROD",
) -> tuple[int, int, int]:
    cursor = db.conn.cursor()

    if source_session_id is None:
        latest_row = cursor.execute(
            """
            SELECT s.id
            FROM sessions s
            WHERE EXISTS (
                SELECT 1 FROM po_downloads p
                WHERE p.session_id = s.id AND p.status = 'ERROR'
            )
            ORDER BY s.id DESC
            LIMIT 1
            """
        ).fetchone()
    else:
        latest_row = cursor.execute(
            """
            SELECT s.id
            FROM sessions s
            WHERE s.id = ?
            """,
            (source_session_id,),
        ).fetchone()
    if not latest_row:
        return 0, 0, 0

    source_session_id = int(latest_row["id"])
    error_rows = cursor.execute(
        "SELECT po_number, company_code, output_subdir FROM po_downloads WHERE session_id = ? AND status = 'ERROR' ORDER BY id ASC",
        (source_session_id,),
    ).fetchall()
    if not error_rows:
        return source_session_id, 0, 0

    po_to_subdir = build_output_subdir_map_from_csv(input_csv) if input_csv else {}

    session_id = db.create_session(f"retry_errors_from_{source_session_id}", execution_type=execution_type)
    for row in error_rows:
        output_subdir = row["output_subdir"]
        if (not output_subdir) and po_to_subdir:
            output_subdir = po_to_subdir.get(str(row["po_number"]).strip(), "")
        cursor.execute(
            "INSERT OR IGNORE INTO po_downloads (session_id, po_number, company_code, output_subdir, status) VALUES (?, ?, ?, ?, 'PENDING')",
            (session_id, row["po_number"], row["company_code"], output_subdir),
        )
    db.conn.commit()
    return source_session_id, session_id, len(error_rows)


def prepare_in_place_retry(
    db: SessionDB,
    session_id: int,
    po_number: str | None = None,
    errors_only: bool = False,
) -> int:
    cursor = db.conn.cursor()
    if po_number:
        rows = cursor.execute(
            "SELECT po_number, status FROM po_downloads WHERE session_id = ? AND po_number = ?",
            (session_id, str(po_number).strip()),
        ).fetchall()
    else:
        statuses = ("ERROR", "SKIPPED_VERIFICATION_REQUIRED") if errors_only else ("PENDING", "ERROR", "SKIPPED_VERIFICATION_REQUIRED")
        placeholders = ",".join("?" for _ in statuses)
        rows = cursor.execute(
            f"SELECT po_number, status FROM po_downloads WHERE session_id = ? AND status IN ({placeholders})",
            (session_id, *statuses),
        ).fetchall()
    for row in rows:
        cursor.execute(
            "INSERT INTO retry_events (session_id, po_number, status_before) VALUES (?, ?, ?)",
            (session_id, row["po_number"], row["status"]),
        )
        cursor.execute(
            "UPDATE po_downloads SET status = 'PENDING', error_message = NULL, updated_at = strftime('%Y-%m-%d %H:%M:%f', 'now') WHERE session_id = ? AND po_number = ?",
            (session_id, row["po_number"]),
        )
    db.conn.commit()
    return len(rows)


def create_retry_session_for_po(
    db: SessionDB,
    po_number: str,
    source_session_id: int | None = None,
    input_csv: str | None = None,
    execution_type: str = "PROD",
) -> tuple[int, int, int]:
    cursor = db.conn.cursor()
    normalized_po = str(po_number or "").strip()
    if source_session_id is None:
        source_row = cursor.execute(
            "SELECT session_id FROM po_downloads WHERE po_number = ? ORDER BY session_id DESC LIMIT 1",
            (normalized_po,),
        ).fetchone()
    else:
        source_row = cursor.execute(
            "SELECT session_id FROM po_downloads WHERE session_id = ? AND po_number = ?",
            (source_session_id, normalized_po),
        ).fetchone()
    if not source_row:
        return 0, 0, 0

    source_session_id = int(source_row["session_id"])
    row = cursor.execute(
        "SELECT po_number, company_code, output_subdir FROM po_downloads WHERE session_id = ? AND po_number = ?",
        (source_session_id, normalized_po),
    ).fetchone()
    if not row:
        return source_session_id, 0, 0

    output_subdir = row["output_subdir"]
    if not output_subdir and input_csv:
        output_subdir = build_output_subdir_map_from_csv(input_csv).get(normalized_po, "")
    session_id = db.create_session(
        f"retry_po_{normalized_po}_from_{source_session_id}",
        execution_type=execution_type,
    )
    cursor.execute(
        "INSERT INTO po_downloads (session_id, po_number, company_code, output_subdir, status) VALUES (?, ?, ?, ?, 'PENDING')",
        (session_id, row["po_number"], row["company_code"], output_subdir),
    )
    db.conn.commit()
    return source_session_id, session_id, 1


def create_retry_session_from_incomplete(
    db: SessionDB,
    source_session_id: int,
    input_csv: str | None = None,
    execution_type: str = "PROD",
) -> tuple[int, int, int]:
    cursor = db.conn.cursor()

    exists = cursor.execute("SELECT 1 FROM sessions WHERE id = ?", (source_session_id,)).fetchone()
    if not exists:
        return 0, 0, 0

    rows = cursor.execute(
        """
        SELECT po_number, company_code, output_subdir
        FROM po_downloads
        WHERE session_id = ? AND status IN ('PENDING', 'ERROR')
        ORDER BY id ASC
        """,
        (source_session_id,),
    ).fetchall()
    if not rows:
        return source_session_id, 0, 0

    po_to_subdir = build_output_subdir_map_from_csv(input_csv) if input_csv else {}
    session_id = db.create_session(f"retry_incomplete_from_{source_session_id}", execution_type=execution_type)
    for row in rows:
        output_subdir = row["output_subdir"]
        if (not output_subdir) and po_to_subdir:
            output_subdir = po_to_subdir.get(str(row["po_number"]).strip(), "")
        cursor.execute(
            "INSERT OR IGNORE INTO po_downloads (session_id, po_number, company_code, output_subdir, status) VALUES (?, ?, ?, ?, 'PENDING')",
            (session_id, row["po_number"], row["company_code"], output_subdir),
        )
    db.conn.commit()
    return source_session_id, session_id, len(rows)


async def main():
    args = parse_args()
    args.concurrency = max(1, min(8, int(args.concurrency)))
    configured_retries = os.environ.get("COUPA_RETRY_ATTEMPTS")
    args.retry_attempts = max(1, min(3, int(configured_retries or args.retry_attempts or 1)))
    args.msg_processing = args.msg_processing or os.environ.get("COUPA_MSG_PROCESSING", "convert_extract")
    args.deduplicate_files = args.deduplicate_files if args.deduplicate_files is not None else os.environ.get("COUPA_DEDUPLICATE_FILES", "1") != "0"

    if not (args.retry_last_errors or args.retry_incomplete_session_id is not None or args.retry_po or args.retry_in_place_po or args.retry_in_place_errors or args.provisional_retry) and not os.path.exists(INPUT_CSV):
        print(f"[ERROR] Input file not found: {INPUT_CSV}")
        sys.exit(1)

    # --- Authentication ---
    cookies = load_cached_cookies()
    if cookies:
        print("[AUTH] Cached cookies loaded. Validating session...")
        valid, reason = await validate_cookies_detailed(cookies)
        if valid:
            print("[AUTH] Coupa session is valid.\n")
        elif reason == "unavailable":
            print("[AUTH][WARNING] Coupa session could not be verified; keeping cached cookies and continuing.")
        else:
            print("[AUTH] Cached session expired. Sign-in is required.")
            cookies = None

    if not cookies:
        cookies = await get_coupa_cookies(load_from_file=False)

    db = SessionDB(DB_PATH)

    mode = "full"
    report_source_csv = INPUT_CSV
    source_session_id: int | None = None
    if args.provisional_retry:
        if not args.retry_attempt_id or not args.retry_session_id or not args.retry_staging_dir:
            print("[ERROR] Provisional retry requires attempt, session, and staging ids.")
            db.close()
            return
        attempt = db.conn.execute(
            "SELECT * FROM retry_attempts WHERE id = ? AND session_id = ? AND status = 'RUNNING'",
            (args.retry_attempt_id, args.retry_session_id),
        ).fetchone()
        if not attempt:
            print("[ERROR] Provisional retry attempt was not found or is no longer active.")
            db.close()
            return
        source_session_id = int(args.retry_session_id)
        session_id = source_session_id
        mode = "provisional_retry"
        run_type = resolve_execution_type(
            args,
            input_name=f"provisional_retry_{attempt['edited_po_number']}",
            source_session_id=source_session_id,
            db=db,
        )
        print(
            f"[INFO] Provisional retry: session={session_id}, "
            f"{attempt['original_po_number']} -> {attempt['edited_po_number']}, type={run_type}"
        )
    elif args.retry_in_place_po or args.retry_in_place_errors:
        source_session_id = args.retry_session_id
        if not source_session_id:
            print("[ERROR] --retry-session-id is required for in-place retry.")
            db.close()
            return
        run_type = resolve_execution_type(
            args,
            input_name=f"retry_in_place_{source_session_id}",
            source_session_id=source_session_id,
            db=db,
        )
        count = prepare_in_place_retry(
            db,
            source_session_id,
            po_number=args.retry_in_place_po,
            errors_only=args.retry_in_place_errors,
        )
        if count == 0:
            print(f"[INFO] Session {source_session_id} has no POs eligible for retry.")
            db.close()
            return
        session_id = source_session_id
        mode = "retry_in_place"
        # The report belongs to this same session and must be updated in place.
        # The archived input is selected again after the archive step below so
        # retries keep every original column in the existing workbook.
        print(f"[INFO] In-place retry: session={session_id}, POs={count}, type={run_type}")
    elif args.retry_po:
        run_type = resolve_execution_type(
            args,
            input_name=f"retry_po_{args.retry_po}",
            source_session_id=args.retry_session_id,
            db=db,
        )
        source_session_id, session_id, count = create_retry_session_for_po(
            db,
            po_number=args.retry_po,
            source_session_id=args.retry_session_id,
            input_csv=INPUT_CSV,
            execution_type=run_type,
        )
        if source_session_id == 0 or session_id == 0 or count == 0:
            print(f"[ERROR] PO {args.retry_po} was not found in the source session.")
            db.close()
            return
        mode = "retry_po"
        # Legacy CLI retry sessions still use the source schema for reporting;
        # the GUI uses the in-place path above to update the original workbook.
        print(f"[INFO] Single-PO retry: source_session={source_session_id}, PO={args.retry_po}, new_session={session_id}, type={run_type}")
    elif args.retry_incomplete_session_id is not None:
        run_type = resolve_execution_type(
            args,
            input_name=f"retry_incomplete_from_{args.retry_incomplete_session_id}",
            source_session_id=args.retry_incomplete_session_id,
            db=db,
        )
        source_session_id, session_id, count = create_retry_session_from_incomplete(
            db,
            source_session_id=args.retry_incomplete_session_id,
            input_csv=INPUT_CSV,
            execution_type=run_type,
        )
        if source_session_id == 0:
            print(f"[ERROR] Session {args.retry_incomplete_session_id} was not found.")
            db.close()
            sys.exit(1)
        if session_id == 0 or count == 0:
            print(f"[INFO] Session {source_session_id} has no pending or failed POs to resume.")
            db.close()
            return
        mode = "retry_incomplete"
        # Keep the source schema available when producing the retry report.
        print(f"[INFO] Incomplete-session retry: source_session={source_session_id}, pending_or_failed={count}, new_session={session_id}, type={run_type}")
    elif args.retry_last_errors:
        run_type = resolve_execution_type(
            args,
            input_name=f"retry_errors_from_{args.retry_session_id or 'latest'}",
            source_session_id=args.retry_session_id,
            db=db,
        )
        source_session_id, session_id, count = create_retry_session_from_last_errors(
            db,
            input_csv=INPUT_CSV,
            source_session_id=args.retry_session_id,
            execution_type=run_type,
        )
        if source_session_id == 0:
            print("[ERROR] No previous session was found for retry.")
            db.close()
            sys.exit(1)
        if session_id == 0 or count == 0:
            print(f"[INFO] Session {source_session_id} has no failed POs to retry.")
            db.close()
            return
        mode = "retry_errors"
        # Keep the source schema available when producing the retry report.
        print(f"[INFO] Failed-PO retry: source_session={source_session_id}, failed={count}, new_session={session_id}, type={run_type}")
    else:
        print(f"[INFO] Reading input: {INPUT_CSV}")
        run_type = resolve_execution_type(args, input_name=os.path.basename(INPUT_CSV))
        hierarchy_order = None
        if os.environ.get("COUPA_HIERARCHY_ORDER"):
            try:
                hierarchy_order = json.loads(os.environ["COUPA_HIERARCHY_ORDER"])
            except json.JSONDecodeError:
                hierarchy_order = None
        session_id, count = create_session_from_csv(
            db,
            INPUT_CSV,
            execution_type=run_type,
            hierarchy_order=hierarchy_order,
        )
        print(f"[INFO] {count} POs imported and queued for processing.")
        print(f"[INFO] Session type: {run_type}")

    run_download_dir = build_run_download_dir(args.download_root, mode, args.run_dir)
    db.conn.execute("UPDATE sessions SET concurrency = ? WHERE id = ?", (args.concurrency, session_id))
    db.conn.commit()
    archive_suffix = Path(INPUT_CSV).suffix or ".csv"
    archive_path = os.path.join(run_download_dir, f"input_source_{session_id}{archive_suffix}")
    if not args.provisional_retry:
        if os.path.exists(INPUT_CSV):
            db.archive_session_input(session_id, INPUT_CSV, archive_path)
        elif source_session_id:
            db.clone_session_input(source_session_id, session_id, archive_path)

    # Always build the workbook from the archived snapshot. For an in-place
    # retry this is the same session's source and the report path below is the
    # existing report, so the retry updates it instead of creating a reduced
    # second workbook.
    if os.path.exists(archive_path):
        report_source_csv = archive_path
    print(f"[INFO] Run folder: {run_download_dir}")
    if args.disable_circuit_breaker:
        print("[INFO] Circuit breaker disabled; processing every row.")

    cursor = db.conn.cursor()

    # --- Processing ---
    crawler = CoupaCrawler(
        db, session_id, run_download_dir,
        cookies=cookies,
        concurrency=args.concurrency,
        request_delay=0.03,
        enable_circuit_breaker=not args.disable_circuit_breaker,
        preserve_existing_files=bool(args.retry_po or args.retry_in_place_po or args.retry_in_place_errors),
    )

    rows = cursor.execute(
        "SELECT po_number, company_code FROM po_downloads WHERE session_id = ? AND status = 'PENDING'",
        (session_id,),
    ).fetchall()

    pos_list = [(r["po_number"], r["company_code"]) for r in rows]
    print(f"[INFO] Processing {len(pos_list)} POs with {crawler.concurrency} concurrent workers...\n")

    counters = {"done": 0, "ok": 0, "err": 0, "files": 0}
    total = len(pos_list)
    start_ts = time.time()

    async def process_one(po_number, company_code):
        result = {"po": po_number, "success": False, "error": "No attempt completed"}
        for attempt in range(args.retry_attempts):
            result = await crawler.process_po(po_number, company_code)
            if result.get("success") or attempt == args.retry_attempts - 1:
                break
            await asyncio.sleep(min(5.0, 1.0 * (attempt + 1)))
        counters["done"] += 1
        if result.get("success"):
            counters["ok"] += 1
            counters["files"] += len(result.get("attachments", []))
        else:
            counters["err"] += 1
        done = counters["done"]
        if done % 25 == 0 or done == total:
            elapsed = time.time() - start_ts
            speed = done / elapsed * 60 if elapsed > 0 else 0
            remaining = total - done
            eta = int(remaining / (done / elapsed)) if done > 0 else 0
            print(
                f"[{done:>4}/{total}] ok={counters['ok']} err={counters['err']} "
                f"files={counters['files']}  speed={speed:.0f}/min  eta={eta//60}m{eta%60:02d}s",
                flush=True,
            )
        return result

    sem = asyncio.Semaphore(crawler.concurrency)

    async def bounded(po, co):
        async with sem:
            return await process_one(po, co)

    results = await asyncio.gather(*[bounded(po, co) for po, co in pos_list], return_exceptions=True)
    results = [r for r in results if not isinstance(r, BaseException)]
    if args.retry_in_place_po or args.retry_in_place_errors:
        for result in results:
            po_value = str(result.get("po", ""))
            db.conn.execute(
                """
                UPDATE retry_events
                SET completed_at = CURRENT_TIMESTAMP,
                    status_after = (SELECT status FROM po_downloads WHERE session_id = ? AND po_number = ?),
                    error_message = ?
                WHERE id = (
                    SELECT id FROM retry_events
                    WHERE session_id = ? AND po_number = ? AND completed_at IS NULL
                    ORDER BY id DESC LIMIT 1
                )
                """,
                (session_id, po_value, result.get("error"), session_id, po_value),
            )
        db.conn.commit()

    success = counters["ok"]
    failed = counters["err"]
    total_attachments = counters["files"]
    auth_fails = sum(1 for r in results if "Auth" in str(r.get("error", "")))
    rate_limits = sum(1 for r in results if "429" in str(r.get("error", "")))
    downloaded_files = sum(
        1 for r in results
        if r.get("success") and len(r.get("attachments", [])) > 0
    )

    if args.provisional_retry:
        attempt_status = "SUCCESS" if failed == 0 and success > 0 else "FAILED"
        first_error = next((str(r.get("error", "")) for r in results if not r.get("success")), None)
        db.conn.execute(
            "UPDATE retry_attempts SET status = ?, error_message = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (attempt_status, first_error, args.retry_attempt_id),
        )
        db.conn.commit()
        print(f"[INFO] Provisional retry finished with status: {attempt_status}")
        await crawler.close()
        db.close()
        return

    print(f"\n{'=' * 60}")
    print("  RESULT")
    print(f"  Success: {success} | Failed: {failed}")
    print(f"  POs with attachments: {downloaded_files}")
    print(f"  Total attachments: {total_attachments}")
    if auth_fails:
        print(f"  [WARNING] Authentication failures: {auth_fails}")
    if rate_limits:
        print(f"  [WARNING] Coupa rate limits (429): {rate_limits}")
    print(f"  Downloads: {run_download_dir}")
    print(f"{'=' * 60}")

    if not args.skip_msg_to_pdf and args.msg_processing != "disabled":
        try:
            msg_files = find_msg_files(Path(run_download_dir))
            if msg_files:
                converter = MsgToPdfConverter(
                    overwrite=args.overwrite_msg_pdf,
                    extract_attachments=args.msg_processing == "convert_extract",
                )
                summary = converter.convert_all(msg_files)
                print(
                    "[MSG2PDF] "
                    f"total={summary['total']} converted={summary['converted']} "
                    f"skipped={summary['skipped']} failed={summary['failed']}"
                )
                if summary["failed"]:
                    first_error = summary["errors"][0]
                    print(f"[MSG2PDF][WARNING] Example failure: {first_error['file']} -> {first_error['error']}")
            else:
                print("[MSG2PDF] No .msg files found for conversion")
        except Exception as e:
            print(f"[MSG2PDF][WARNING] MSG-to-PDF conversion failed: {e}")
    else:
        print("[MSG2PDF] MSG conversion disabled")

    if args.deduplicate_files:
        try:
            from src.engine.file_deduplicator import FileDeduplicator
            dedup_summary = FileDeduplicator().process_tree(Path(run_download_dir))
            print(
                "[DEDUP] "
                f"scanned={dedup_summary['scanned']} duplicates={dedup_summary['duplicates']} "
                f"hardlinks={dedup_summary['hardlinks']} references={dedup_summary['references']}"
            )
            if dedup_summary["errors"]:
                print(f"[DEDUP][WARNING] File-level failures: {len(dedup_summary['errors'])}")
        except Exception as e:
            print(f"[DEDUP][WARNING] Deduplication failed: {e}")

    report_path = os.path.join(run_download_dir, f"report_session_{session_id}.xlsx")
    try:
        saved_report = export_original_like_excel_report(
            db=db,
            session_id=session_id,
            report_path=report_path,
            input_csv=report_source_csv,
        )
        print(f"[REPORT] Excel report generated: {saved_report}")
    except Exception as e:
        print(f"[REPORT][ERROR] Excel report generation failed: {e}")

    db.conn.execute(
        "UPDATE sessions SET duration_seconds = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (max(0.0, time.time() - start_ts), session_id),
    )
    db.conn.commit()
    await crawler.close()
    db.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Run interrupted by the user (Ctrl+C).")
