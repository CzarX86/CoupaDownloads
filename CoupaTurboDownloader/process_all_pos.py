import os
import sys
import asyncio
import time
import argparse
from datetime import datetime
from pathlib import Path
import pandas as pd
from src.db.session_db import SessionDB
from src.engine.crawler import CoupaCrawler
from src.engine.authenticator import load_cached_cookies, validate_cookies, get_coupa_cookies
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
        "--concurrency",
        type=int,
        default=11,
        help="Concurrent workers (default: 11)",
    )
    parser.add_argument(
        "--retry-session-id",
        type=int,
        default=None,
        help="Optional source session id for retry mode (uses latest with ERROR if omitted)",
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
        help="Disable company-level circuit breaker and process 100% of rows",
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


def build_run_download_dir(download_root: str, mode: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(os.path.expanduser(download_root), f"run_{stamp}_{mode}")
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def detect_separator(filepath: str) -> str:
    with open(filepath, encoding="utf-8") as f:
        sample = f.read(4096)
    return ";" if sample.count(";") > sample.count(",") else ","


def _clean_folder_part(value: str) -> str:
    cleaned = str(value or "").strip()
    if cleaned.lower() in {"", "nan", "none"}:
        cleaned = "Unknown"
    cleaned = cleaned.replace("/", "_").replace("\\", "_")
    cleaned = "_".join(cleaned.split())
    cleaned = cleaned.strip("._")
    return cleaned or "Unknown"


def _extract_hierarchy_columns(df: pd.DataFrame) -> tuple[list[str], bool]:
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
    return os.path.join(*parts)


def build_output_subdir_map_from_csv(input_csv: str) -> dict[str, str]:
    if not input_csv or not os.path.exists(input_csv):
        return {}

    sep = detect_separator(input_csv)
    df = pd.read_csv(input_csv, sep=sep, dtype=str)
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
        SELECT po_number, company_code, status, attachment_count, error_message, download_folder, updated_at
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
        "DOWNLOAD_FOLDER": "DOWNLOAD_FOLDER",
        "COUPA_URL": "COUPA_URL",
    }
    mapped = db_df[list(report_cols.keys())].rename(columns=report_cols)

    if input_csv and os.path.exists(input_csv):
        sep = detect_separator(input_csv)
        source_df = pd.read_csv(input_csv, sep=sep, dtype=str).fillna("")
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


def create_session_from_csv(db: SessionDB, input_csv: str, execution_type: str = "PROD") -> tuple[int, int]:
    cursor = db.conn.cursor()
    sep = detect_separator(input_csv)
    df = pd.read_csv(input_csv, sep=sep, dtype=str)
    hierarchy_cols, has_hierarchy_data = _extract_hierarchy_columns(df)
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

    if not args.retry_last_errors and not os.path.exists(INPUT_CSV):
        print(f"[ERRO] Arquivo nao encontrado: {INPUT_CSV}")
        sys.exit(1)

    # --- Autenticacao ---
    cookies = load_cached_cookies()
    if cookies:
        print("[AUTH] Cookies carregados do cache. Validando...")
        if await validate_cookies(cookies):
            print("[AUTH] Cookies validos.\n")
        else:
            print("[AUTH] Cookies expirados. Reautenticacao necessaria.")
            cookies = None

    if not cookies:
        cookies = await get_coupa_cookies(load_from_file=False)

    db = SessionDB(DB_PATH)

    mode = "full"
    report_source_csv = INPUT_CSV
    if args.retry_incomplete_session_id is not None:
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
            print(f"[ERRO] Sessao {args.retry_incomplete_session_id} nao encontrada.")
            db.close()
            sys.exit(1)
        if session_id == 0 or count == 0:
            print(f"[INFO] Sessao {source_session_id} nao possui PENDING/ERROR para retomar.")
            db.close()
            return
        mode = "retry_incomplete"
        report_source_csv = None
        print(f"[INFO] Retry incomplete mode: sessao origem={source_session_id}, pendentes+erros={count}, nova sessao={session_id}, tipo={run_type}")
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
            print("[ERRO] Nenhuma sessao anterior encontrada para retry.")
            db.close()
            sys.exit(1)
        if session_id == 0 or count == 0:
            print(f"[INFO] Sessao {source_session_id} nao possui erros para retry.")
            db.close()
            return
        mode = "retry_errors"
        report_source_csv = None
        print(f"[INFO] Retry mode: sessao origem={source_session_id}, erros isolados={count}, nova sessao={session_id}, tipo={run_type}")
    else:
        print(f"[INFO] Importando {INPUT_CSV}...")
        run_type = resolve_execution_type(args, input_name=os.path.basename(INPUT_CSV))
        session_id, count = create_session_from_csv(db, INPUT_CSV, execution_type=run_type)
        print(f"[INFO] {count} POs importadas. Iniciando processamento...")
        print(f"[INFO] Tipo da sessao: {run_type}")

    run_download_dir = build_run_download_dir(args.download_root, mode)
    print(f"[INFO] Pasta desta execucao: {run_download_dir}")
    if args.disable_circuit_breaker:
        print("[INFO] Circuit breaker desabilitado: processando 100% das linhas")

    cursor = db.conn.cursor()

    # --- Processar ---
    crawler = CoupaCrawler(
        db, session_id, run_download_dir,
        cookies=cookies,
        concurrency=args.concurrency,
        request_delay=0.03,
        enable_circuit_breaker=not args.disable_circuit_breaker,
    )

    rows = cursor.execute(
        "SELECT po_number, company_code FROM po_downloads WHERE session_id = ? AND status = 'PENDING'",
        (session_id,),
    ).fetchall()

    pos_list = [(r["po_number"], r["company_code"]) for r in rows]
    print(f"[INFO] Processando {len(pos_list)} POs com {crawler.concurrency} workers...\n")

    counters = {"done": 0, "ok": 0, "err": 0, "files": 0}
    total = len(pos_list)
    start_ts = time.time()

    async def process_one(po_number, company_code):
        result = await crawler.process_po(po_number, company_code)
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

    success = counters["ok"]
    failed = counters["err"]
    total_attachments = counters["files"]
    auth_fails = sum(1 for r in results if "Auth" in str(r.get("error", "")))
    rate_limits = sum(1 for r in results if "429" in str(r.get("error", "")))
    downloaded_files = sum(
        1 for r in results
        if r.get("success") and len(r.get("attachments", [])) > 0
    )

    print(f"\n{'=' * 60}")
    print(f"  RESULTADO")
    print(f"  Success: {success} | Failed: {failed}")
    print(f"  POs com anexos: {downloaded_files}")
    print(f"  Total de anexos: {total_attachments}")
    if auth_fails:
        print(f"  [AVISO] {auth_fails} falhas de autenticacao")
    if rate_limits:
        print(f"  [AVISO] {rate_limits} rate limits (429)")
    print(f"  Downloads: {run_download_dir}")
    print(f"{'=' * 60}")

    if not args.skip_msg_to_pdf:
        try:
            msg_files = find_msg_files(Path(run_download_dir))
            if msg_files:
                converter = MsgToPdfConverter(overwrite=args.overwrite_msg_pdf)
                summary = converter.convert_all(msg_files)
                print(
                    "[MSG2PDF] "
                    f"total={summary['total']} converted={summary['converted']} "
                    f"skipped={summary['skipped']} failed={summary['failed']}"
                )
                if summary["failed"]:
                    first_error = summary["errors"][0]
                    print(f"[MSG2PDF][WARN] Exemplo de falha: {first_error['file']} -> {first_error['error']}")
            else:
                print("[MSG2PDF] Nenhum arquivo .msg encontrado para conversao")
        except Exception as e:
            print(f"[MSG2PDF][WARN] Falha na conversao .msg -> .pdf: {e}")

    report_path = os.path.join(run_download_dir, f"report_session_{session_id}.xlsx")
    try:
        saved_report = export_original_like_excel_report(
            db=db,
            session_id=session_id,
            report_path=report_path,
            input_csv=report_source_csv,
        )
        print(f"[REPORT] Excel gerado: {saved_report}")
    except Exception as e:
        print(f"[REPORT][ERRO] Falha ao gerar Excel: {e}")

    await crawler.close()
    db.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Execucao interrompida pelo usuario (Ctrl+C).")
