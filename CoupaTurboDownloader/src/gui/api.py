import os
import time
import asyncio
import threading
import pandas as pd
from typing import Dict, Any, List
from src.db.session_db import SessionDB, PODownload
from src.engine.crawler import CoupaCrawler


class AppAPI:
    def __init__(self, db: SessionDB, default_download_dir: str):
        self.db = db
        self.default_download_dir = default_download_dir
        self._runtime_lock = threading.Lock()
        self._runtime: Dict[int, Dict[str, Any]] = {}

    def _set_session_status(self, session_id: int, status: str):
        cursor = self.db.conn.cursor()
        cursor.execute(
            "UPDATE sessions SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, session_id),
        )
        self.db.conn.commit()

    def _append_log(self, session_id: int, log_type: str, message: str):
        with self._runtime_lock:
            runtime = self._runtime.get(session_id)
            if not runtime:
                return
            runtime["latest_logs"].append({"type": log_type, "message": message})
            runtime["latest_logs"] = runtime["latest_logs"][-30:]

    async def _run_session_async(self, session_id: int, download_dir: str):
        cursor = self.db.conn.cursor()
        cursor.execute(
            "SELECT po_number, company_code FROM po_downloads WHERE session_id = ? AND status = 'PENDING' ORDER BY id ASC",
            (session_id,),
        )
        rows = cursor.fetchall()

        concurrency = self._runtime.get(session_id, {}).get("concurrency", 11)
        crawler = CoupaCrawler(
            self.db, session_id, download_dir, concurrency=concurrency
        )
        self._set_session_status(session_id, "RUNNING")
        self._append_log(session_id, "System", f"Starting session {session_id} with {len(rows)} POs (workers={concurrency})")

        semaphore = asyncio.Semaphore(concurrency)

        async def process_one(po_number: str, company_code: str):
            async with semaphore:
                _check_runtime_stop(session_id, self._runtime, self._runtime_lock)
                await _check_runtime_pause(session_id, self._runtime, self._runtime_lock)

                self._append_log(session_id, "Info", f"Processing PO {po_number} ({company_code})")
                await crawler.process_po(po_number, company_code)

                po_row = self.db.get_po(session_id, po_number)
                with self._runtime_lock:
                    runtime = self._runtime.get(session_id)
                    if runtime:
                        runtime["processed"] += 1
                        if po_row and po_row.get("status") == "ERROR":
                            runtime["errors"] += 1
                            runtime["status"] = "RUNNING"
                            self._append_log(session_id, "Error", f"PO {po_number} failed: {po_row.get('error_message')}")
                        else:
                            self._append_log(session_id, "Success", f"PO {po_number} completed")

        try:
            tasks = [
                process_one(row["po_number"], row["company_code"])
                for row in rows
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, SessionStoppedError):
                    self._append_log(session_id, "System", f"Session {session_id} stopped by user")
                    return
                if isinstance(r, Exception) and not isinstance(r, SessionStoppedError):
                    self._append_log(session_id, "Error", f"Task error: {r}")
                    with self._runtime_lock:
                        runtime = self._runtime.get(session_id)
                        if runtime:
                            runtime["errors"] += 1

            with self._runtime_lock:
                runtime = self._runtime.get(session_id)
                if runtime:
                    runtime["status"] = "ERROR" if runtime["errors"] > 0 else "SUCCESS"
                    final_status = runtime["status"]
                else:
                    final_status = "SUCCESS"
            self._set_session_status(session_id, final_status)
            self._append_log(session_id, "System", f"Session {session_id} finished with status: {final_status}")

        finally:
            await crawler.close()

    def _run_session_thread(self, session_id: int, download_dir: str):
        try:
            asyncio.run(self._run_session_async(session_id, download_dir))
        except Exception as e:
            with self._runtime_lock:
                runtime = self._runtime.get(session_id)
                if runtime:
                    runtime["status"] = "ERROR"
                    runtime["errors"] += 1
            self._set_session_status(session_id, "ERROR")
            self._append_log(session_id, "Error", f"Fatal session error: {e}")

    def select_directory(self) -> str:
        os.makedirs(self.default_download_dir, exist_ok=True)
        return self.default_download_dir

    def start_download(self, session_id: int, download_dir: str, concurrency: int = 11) -> Dict[str, Any]:
        try:
            session_id = int(session_id)
            download_dir = (download_dir or self.default_download_dir).strip() or self.default_download_dir
            os.makedirs(download_dir, exist_ok=True)
            self.default_download_dir = download_dir

            cursor = self.db.conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as total FROM po_downloads WHERE session_id = ? AND status = 'PENDING'",
                (session_id,),
            )
            total = int(cursor.fetchone()["total"])

            with self._runtime_lock:
                existing = self._runtime.get(session_id)
                if existing and existing.get("status") in {"RUNNING", "PAUSED"}:
                    return {"success": False, "error": "Session already running."}

                self._runtime[session_id] = {
                    "status": "RUNNING",
                    "started_at": time.time(),
                    "processed": 0,
                    "total": total,
                    "errors": 0,
                    "paused": False,
                    "stop_requested": False,
                    "concurrency": concurrency,
                    "latest_logs": [],
                }

            worker = threading.Thread(
                target=self._run_session_thread,
                args=(session_id, download_dir),
                daemon=True,
            )
            with self._runtime_lock:
                self._runtime[session_id]["thread"] = worker

            worker.start()
            return {"success": True, "session_id": session_id, "total": total}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_active_session_status(self, session_id: int) -> Dict[str, Any]:
        session_id = int(session_id)
        with self._runtime_lock:
            runtime = self._runtime.get(session_id)

        if runtime:
            elapsed = max(time.time() - runtime.get("started_at", time.time()), 0.1)
            processed = int(runtime.get("processed", 0))
            total = int(runtime.get("total", 0))
            errors = int(runtime.get("errors", 0))
            speed = (processed / elapsed) * 60.0 if processed > 0 else 0.0
            remaining = max(total - processed, 0)
            eta_seconds = int((remaining / speed) * 60) if speed > 0 else 0
            eta = time.strftime("%M:%S", time.gmtime(eta_seconds)) if speed > 0 else "--:--"

            with self._runtime_lock:
                latest_logs = list(runtime.get("latest_logs", []))
                runtime["latest_logs"] = []
                status = runtime.get("status", "PENDING")

            return {
                "status": status,
                "total": total,
                "processed": processed,
                "speed": speed,
                "eta": eta,
                "errors": errors,
                "latest_logs": latest_logs,
            }

        cursor = self.db.conn.cursor()
        cursor.execute("SELECT status FROM sessions WHERE id = ?", (session_id,))
        session_row = cursor.fetchone()
        session_status = session_row["status"] if session_row else "UNKNOWN"

        cursor.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status != 'PENDING' THEN 1 ELSE 0 END) as processed,
                SUM(CASE WHEN status = 'ERROR' THEN 1 ELSE 0 END) as errors
            FROM po_downloads
            WHERE session_id = ?
            """,
            (session_id,),
        )
        stats = cursor.fetchone()
        total = int(stats["total"] or 0)
        processed = int(stats["processed"] or 0)
        errors = int(stats["errors"] or 0)

        return {
            "status": session_status,
            "total": total,
            "processed": processed,
            "speed": 0.0,
            "eta": "--:--",
            "errors": errors,
            "latest_logs": [],
        }

    def pause_download(self, session_id: int) -> Dict[str, Any]:
        try:
            session_id = int(session_id)
            with self._runtime_lock:
                runtime = self._runtime.get(session_id)
                if not runtime:
                    return {"success": False, "error": "Session not active."}
                runtime["paused"] = True
                runtime["status"] = "PAUSED"
            self._set_session_status(session_id, "PAUSED")
            self._append_log(session_id, "System", "Session paused")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def resume_download(self, session_id: int) -> Dict[str, Any]:
        try:
            session_id = int(session_id)
            with self._runtime_lock:
                runtime = self._runtime.get(session_id)
                if not runtime:
                    return {"success": False, "error": "Session not active."}
                runtime["paused"] = False
                runtime["status"] = "RUNNING"
            self._set_session_status(session_id, "RUNNING")
            self._append_log(session_id, "System", "Session resumed")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop_download(self, session_id: int) -> Dict[str, Any]:
        try:
            session_id = int(session_id)
            with self._runtime_lock:
                runtime = self._runtime.get(session_id)
                if not runtime:
                    return {"success": False, "error": "Session not active."}
                runtime["stop_requested"] = True
            self._append_log(session_id, "System", "Stop requested by user")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def import_file(self, filepath: str) -> Dict[str, Any]:
        import re
        try:
            if not os.path.exists(filepath):
                return {'success': False, 'error': f"File not found: {filepath}"}

            _, ext = os.path.splitext(filepath.lower())
            if ext == '.csv':
                with open(filepath, encoding='utf-8') as f:
                    sample = f.read(4096)
                sep = ';' if sample.count(';') > sample.count(',') else ','
                df = pd.read_csv(filepath, sep=sep, dtype=str)
            elif ext in ['.xls', '.xlsx']:
                df = pd.read_excel(filepath, dtype=str)
            else:
                return {'success': False, 'error': "Unsupported file format. Use XLSX or CSV."}

            def clean_folder_part(value: Any) -> str:
                text = str(value or '').strip()
                if text.lower() in {'', 'nan', 'none'}:
                    text = 'Unknown'
                text = text.replace('/', '_').replace('\\', '_')
                text = '_'.join(text.split())
                text = text.strip('._')
                return text or 'Unknown'

            def extract_hierarchy_columns(frame: pd.DataFrame) -> tuple[list[str], bool]:
                sep_col = None
                for c in frame.columns:
                    if str(c).strip() == '<|>':
                        sep_col = c
                        break
                if sep_col is None:
                    return [], False

                cols = list(frame.columns)
                hierarchy_cols = cols[cols.index(sep_col) + 1:]
                if not hierarchy_cols:
                    return [], False

                for col in hierarchy_cols:
                    series = frame[col].fillna('').astype(str).str.strip()
                    series = series[(series != '') & (series.str.lower() != 'nan')]
                    if not series.empty:
                        return hierarchy_cols, True
                return hierarchy_cols, False

            hierarchy_cols, has_hierarchy_data = extract_hierarchy_columns(df)

            def norm(col):
                return re.sub(r'[^a-z0-9]+', '', str(col).lower().strip())
            norm_cols = {norm(col): col for col in df.columns}

            po_keys = ['ponumber', 'po', 'pedido']
            company_keys = ['legalentity', 'companycode', 'empresa', 'supplier']

            po_col = None
            for key in po_keys:
                if key in norm_cols:
                    po_col = norm_cols[key]
                    break

            company_col = None
            for key in company_keys:
                if key in norm_cols:
                    company_col = norm_cols[key]
                    break

            if not po_col:
                return {'success': False, 'error': f"Could not find PO Number column. Found columns: {list(df.columns)}"}
            if not company_col:
                return {'success': False, 'error': f"Could not find Company Code/Legal Entity/Supplier column. Found columns: {list(df.columns)}"}

            session_id = self.db.create_session(os.path.basename(filepath))

            df = df.dropna(subset=[po_col, company_col])
            df = df.drop_duplicates(subset=[po_col, company_col])
            df = df.sort_values(by=company_col, kind='stable')

            total_pos = 0
            for _, row in df.iterrows():
                po_val = str(row[po_col]).strip()
                company_val = str(row[company_col]).strip()
                if po_val and po_val.lower() != 'nan' and company_val and company_val.lower() != 'nan':
                    if has_hierarchy_data and hierarchy_cols:
                        parts = [clean_folder_part(row.get(col, '')) for col in hierarchy_cols]
                        output_subdir = os.path.join(*parts)
                    else:
                        output_subdir = company_val

                    self.db.add_po(PODownload(
                        session_id=session_id,
                        po_number=po_val,
                        company_code=company_val,
                        output_subdir=output_subdir,
                        status="PENDING"
                    ))
                    total_pos += 1

            return {
                'success': True,
                'session_id': session_id,
                'total_pos': total_pos
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_session_history(self) -> List[Dict[str, Any]]:
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM sessions ORDER BY id DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_session_details(self, session_id: int) -> Dict[str, Any]:
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM po_downloads WHERE session_id = ?", (session_id,))
        pos = [dict(row) for row in cursor.fetchall()]
        session = self.db.get_session(session_id)
        return {
            'session': session,
            'pos': pos
        }

    def confirm_and_retry_company(self, session_id: int, company_code: str) -> Dict[str, Any]:
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''
                UPDATE po_downloads
                SET status = 'PENDING', updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ? AND company_code = ? AND status = 'SKIPPED_VERIFICATION_REQUIRED'
            ''', (session_id, company_code))
            self.db.conn.commit()
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def export_session_report(self, session_id: int, dest_filepath: str) -> Dict[str, Any]:
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''
                SELECT po_number, company_code, status, download_folder, attachment_count, error_message, updated_at
                FROM po_downloads
                WHERE session_id = ?
            ''', (session_id,))
            rows = cursor.fetchall()
            df = pd.DataFrame([dict(r) for r in rows])

            df.to_excel(dest_filepath, index=False)
            return {'success': True, 'filepath': dest_filepath}
        except Exception as e:
            return {'success': False, 'error': str(e)}


def _check_runtime_stop(
    session_id: int,
    runtime: Dict[int, Dict[str, Any]],
    lock: threading.Lock,
) -> None:
    with lock:
        rt = runtime.get(session_id)
        if rt and rt.get("stop_requested"):
            rt["status"] = "STOPPED"
            raise SessionStoppedError(session_id)


async def _check_runtime_pause(
    session_id: int,
    runtime: Dict[int, Dict[str, Any]],
    lock: threading.Lock,
) -> None:
    while True:
        with lock:
            rt = runtime.get(session_id)
            if not rt:
                return
            if rt.get("stop_requested"):
                rt["status"] = "STOPPED"
                raise SessionStoppedError(session_id)
            if not rt.get("paused", False):
                return
        await asyncio.sleep(0.2)


class SessionStoppedError(Exception):
    def __init__(self, session_id: int):
        self.session_id = session_id
        super().__init__(f"Session {session_id} stopped by user")
