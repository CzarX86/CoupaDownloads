import os
import sys
import shutil
import tempfile
import random
import re
import time
import threading
import multiprocessing as mp
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Callable
from enum import Enum
from selenium.common.exceptions import (
    InvalidSessionIdException,
    NoSuchWindowException,
    TimeoutException,
)
# Add the project root to Python path for local execution
project_root = Path(__file__).resolve().parents[2]
project_root_str = str(project_root)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

# Add EXPERIMENTAL directory to path for local corelib imports
experimental_root = Path(__file__).resolve().parents[1]
experimental_root_str = str(experimental_root)
if experimental_root_str not in sys.path:
    sys.path.insert(0, experimental_root_str)

from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.layout import Layout
from rich.live import Live
from rich.console import Console, Group

from .lib.browser import BrowserManager
from .lib.config import Config as ExperimentalConfig
from .lib.downloader import Downloader
from .lib.excel_processor import ExcelProcessor
from .lib.folder_hierarchy import FolderHierarchyManager
from .lib.models import HeadlessConfiguration, InteractiveSetupSession

# Import worker pool for parallel processing
from .workers.persistent_pool import PersistentWorkerPool

# Import CSV handler for incremental persistence
from .core.csv_handler import CSVHandler, WriteQueue
from .workers.models import PoolConfig

# Import new managers
from .setup_manager import SetupManager
from .worker_manager import WorkerManager, _wait_for_downloads_complete, _legacy_rename_folder_with_status, _derive_status_label

# Enable interactive UI mode (set to True to enable interactive prompts)
ENABLE_INTERACTIVE_UI = os.environ.get('ENABLE_INTERACTIVE_UI', 'True').strip().lower() == 'true'


class MainApp:
    def __init__(self, enable_parallel: bool = True, max_workers: int = 4):
        """
        Initialize MainApp with optional parallel processing support.
        
        Args:
            enable_parallel: Whether to enable parallel processing for multiple POs
            max_workers: Maximum number of parallel workers (>=1). No implicit hard cap.
        """
        # Validate parallel processing parameters
        if not isinstance(enable_parallel, bool):
            raise TypeError("enable_parallel must be a boolean")
        
        if not (isinstance(max_workers, int) and max_workers >= 1):
            raise ValueError(f"max_workers must be a positive integer, got {max_workers}")
        
        # Parallel processing configuration
        self.enable_parallel = enable_parallel
        self.max_workers = max_workers
        self._last_parallel_report: Optional[Dict[str, Any]] = None
        
        # Original initialization
        self.excel_processor = ExcelProcessor()
        self.browser_manager = BrowserManager()
        self.folder_hierarchy = FolderHierarchyManager()
        self.setup_manager = SetupManager()
        self.worker_manager = WorkerManager(enable_parallel=self.enable_parallel, max_workers=self.max_workers)
        self.driver = None
        self.lock = threading.Lock()  # Thread safety for browser operations
        self._run_start_time: float | None = None
        self._current_po_start_time: float | None = None
        
        # CSV handler for incremental persistence
        self.csv_handler: CSVHandler | None = None
        self._csv_write_queue: WriteQueue | None = None
        self._csv_session_id: str | None = None
        self._completed_po_count = 0
        self._total_po_count = 0
        self._accumulated_po_seconds = 0.0
        self._headless_config: HeadlessConfiguration | None = None

        # Rich UI components
        self.console = Console()
        self.live: Optional[Live] = None

        # Global stats for header
        self.global_stats = {
            "total": 0,
            "completed": 0,
            "failed": 0,
            "active": 0,
            "elapsed": "0m 0s",
            "eta_global": "N/A",
            "global_efficiency": "⏳"
        }

        # Worker states for table
        self.worker_states: List[Dict[str, Any]] = []

    def set_headless_configuration(self, headless_config: HeadlessConfiguration) -> None:
        """Set the headless configuration for this MainApp instance."""
        self._headless_config = headless_config
        print(f"[MainApp] 🎯 Headless configuration set: {headless_config}")

    def _build_progress_table(self) -> Table:
        table = Table(title="Worker Progress")
        table.add_column("Worker ID", style="blue", no_wrap=True)
        table.add_column("Progress", style="cyan")
        table.add_column("Tempo Transcorrido", style="yellow")
        table.add_column("ETA Restante", style="green")
        table.add_column("Eficiência", style="magenta")
        for worker in self.worker_states:
            table.add_row(
                worker["worker_id"],
                worker["progress"],
                worker["elapsed"],
                worker["eta"],
                worker["efficiency"]
            )
        return table

    def _update_header(self) -> Group:
        """Update the header with KPI cards."""
        time_card = Panel(
            f"⏱️ Tempo Global\n{self.global_stats['elapsed']}\nETA: {self.global_stats['eta_global']}",
            title="Tempo", border_style="blue"
        )
        total_card = Panel(
            f"📊 Total POs\n{self.global_stats['total']}\nAtivos: {self.global_stats['active']}",
            title="Total", border_style="cyan"
        )
        efficiency_card = Panel(
            f"⚡ Eficiência Global\n{self.global_stats['global_efficiency']}",
            title="Performance", border_style="yellow"
        )
        completed_card = Panel(
            f"✅ Concluídos\n{self.global_stats['completed']}",
            title="Sucesso", border_style="green"
        )
        failed_card = Panel(
            f"❌ Falhas\n{self.global_stats['failed']}",
            title="Erros", border_style="red"
        )
        
        # All cards in a single row
        return Columns([time_card, total_card, efficiency_card, completed_card, failed_card], equal=True, expand=True)
    
    def _parallel_progress_callback(self, progress: Dict[str, Any]) -> None:
        """Progress callback for ProcessingSession parallel processing."""
        try:
            total = progress.get('total_tasks', 0)
            completed = progress.get('completed_tasks', 0)
            failed = progress.get('failed_tasks', 0)
            active = progress.get('active_tasks', 0)

            # Update global stats
            self.global_stats["total"] = total
            self.global_stats["completed"] = completed
            self.global_stats["failed"] = failed
            self.global_stats["active"] = active

            # Calculate elapsed time
            if self._run_start_time:
                elapsed_seconds = time.perf_counter() - self._run_start_time
                minutes, seconds = divmod(int(elapsed_seconds), 60)
                self.global_stats["elapsed"] = f"{minutes}m {seconds}s"

                # Estimate ETA global
                if completed > 0:
                    avg_time_per_po = elapsed_seconds / completed
                    remaining_pos = total - completed - failed
                    eta_seconds = avg_time_per_po * remaining_pos
                    eta_minutes, eta_seconds = divmod(int(eta_seconds), 60)
                    self.global_stats["eta_global"] = f"{eta_minutes}m {eta_seconds}s"
                else:
                    self.global_stats["eta_global"] = "⏳"
                
                # Calculate global efficiency
                if elapsed_seconds > 0:
                    global_efficiency = (completed / elapsed_seconds) * 60  # POs per minute
                    self.global_stats["global_efficiency"] = f"{global_efficiency:.1f} POs/min"
                else:
                    self.global_stats["global_efficiency"] = "⏳"

            # Update worker states with individual efficiency estimates
            completed_per_worker = completed // self.max_workers
            failed_per_worker = failed // self.max_workers
            active_per_worker = active // self.max_workers
            total_per_worker = total // self.max_workers
            self.worker_states = []
            for i in range(self.max_workers):
                worker_id = f"Worker {i+1}"
                progress_str = f"{completed_per_worker}/{total_per_worker} POs"
                elapsed_worker = self.global_stats["elapsed"]
                eta_worker = self.global_stats["eta_global"]
                
                # Estimate individual worker efficiency based on distributed workload
                # Assuming even distribution of completed tasks among workers
                worker_completed_estimate = completed_per_worker
                if elapsed_seconds > 0 and worker_completed_estimate > 0:
                    worker_efficiency = (worker_completed_estimate / elapsed_seconds) * 60
                    efficiency = f"{worker_efficiency:.1f} POs/min"
                else:
                    efficiency = "⏳"
                
                self.worker_states.append({
                    "worker_id": worker_id,
                    "progress": progress_str,
                    "elapsed": elapsed_worker,
                    "eta": eta_worker,
                    "efficiency": efficiency
                })

            # Update live with Group
            if self.live:
                self.live.update(Group(self._update_header(), "", self._build_progress_table()))

        except Exception as e:
            print(f"Error in progress callback: {e}")

    # ---- UI helpers ---------------------------------------------------------------------



    # (Deprecated) _rename_folder_with_status removed in favor of folder_hierarchy.finalize_folder

    def initialize_browser_once(self):
        """Initialize browser once and keep it open for all POs."""
        if not self.driver:
            print("🚀 Initializing browser for sequential processing...")
            self.browser_manager.initialize_driver(headless=self._headless_config.get_effective_headless_mode())
            self.driver = self.browser_manager.driver
            print("✅ Browser initialized successfully")

    def _prepare_progress_tracking(self, total_pos: int) -> None:
        """Reset telemetry accumulators before sequential PO processing."""
        self._total_po_count = max(0, total_pos)
        self._completed_po_count = 0
        self._accumulated_po_seconds = 0.0
        self._current_po_start_time = None
        self._run_start_time = time.perf_counter()

    def _format_duration(self, seconds: float | None) -> str:
        if seconds is None or seconds < 0:
            return "--:--"
        total_minutes = int(seconds // 60)
        hours, minutes = divmod(total_minutes, 60)
        return f"{hours:02d}:{minutes:02d}"

    def _progress_snapshot(self) -> tuple[str, str, str]:
        if self._run_start_time is None:
            return "--:--", "--:--", "--"

        elapsed_seconds = max(0.0, time.perf_counter() - self._run_start_time)
        elapsed = self._format_duration(elapsed_seconds)

        if self._completed_po_count <= 0 or self._accumulated_po_seconds <= 0.0:
            return elapsed, "--:--", "--"

        remaining_pos = max(self._total_po_count - self._completed_po_count, 0)
        if remaining_pos <= 0:
            eta_time = datetime.now()
            return elapsed, "00:00", eta_time.strftime("%Y-%m-%d %H:%M")

        average = self._accumulated_po_seconds / self._completed_po_count
        remaining_seconds = max(0.0, average * remaining_pos)
        remaining = self._format_duration(remaining_seconds)
        eta = (datetime.now() + timedelta(seconds=remaining_seconds)).strftime("%Y-%m-%d %H:%M")
        return elapsed, remaining, eta

    def _build_progress_line(self, index: int, total: int) -> str:
        elapsed, remaining, eta = self._progress_snapshot()
        return (
            f"📋 Processing PO {index + 1}/{total} – "
            f"Elapsed Time: {elapsed}, Remaining Time: {remaining}, "
            f"Estimated Completion: {eta}"
        )

    def _register_po_completion(self) -> None:
        if self._current_po_start_time is None:
            return

        duration = max(0.0, time.perf_counter() - self._current_po_start_time)
        self._accumulated_po_seconds += duration
        if self._total_po_count > 0:
            self._completed_po_count = min(self._completed_po_count + 1, self._total_po_count)
        else:
            self._completed_po_count += 1
        self._current_po_start_time = None

    def _initialize_csv_handler(self, csv_path: Path) -> None:
        """Instantiate CSV handler, backup current CSV, and boot write queue."""
        import uuid
        try:
            backup_dir = csv_path.parent.parent / 'backup'
            backup_dir.mkdir(parents=True, exist_ok=True)
            self.csv_handler = CSVHandler(csv_path=csv_path, backup_dir=backup_dir)
            self._csv_session_id = uuid.uuid4().hex[:8]
            backup_path = self.csv_handler.create_session_backup(self._csv_session_id)
            print(f"🛡️ CSV backup created at: {backup_path}")
            self._csv_write_queue = WriteQueue(self.csv_handler)
            self._csv_write_queue.start_writer_thread()
        except Exception as handler_error:
            self.csv_handler = None
            self._csv_write_queue = None
            self._csv_session_id = None
            print(f"⚠️ Failed to initialize CSV handler: {handler_error}")

    def _shutdown_csv_handler(self) -> None:
        """Gracefully stop write queue threads."""
        if self._csv_write_queue:
            self._csv_write_queue.stop_writer_thread(timeout=15.0)
        self._csv_write_queue = None


    @staticmethod
    def _build_csv_updates(result: Dict[str, Any]) -> Dict[str, Any]:
        """Translate a processing result into CSV column updates."""
        status_code = (result.get('status_code') or '').upper() or 'FAILED'
        attachment_names = result.get('attachment_names') or []
        if isinstance(attachment_names, str):
            attachment_names = [name for name in attachment_names.split(';') if name]

        error_message = ''
        success = result.get('success')
        if success is None:
            success = status_code in {'COMPLETED', 'NO_ATTACHMENTS', 'PARTIAL'}
        if not success:
            error_message = result.get('message', '') or result.get('error', '')

        updates: Dict[str, Any] = {
            'STATUS': status_code,
            'ATTACHMENTS_FOUND': result.get('attachments_found', 0),
            'ATTACHMENTS_DOWNLOADED': result.get('attachments_downloaded', 0),
            'AttachmentName': attachment_names,
            'DOWNLOAD_FOLDER': result.get('final_folder', ''),
            'COUPA_URL': result.get('coupa_url', ''),
            'ERROR_MESSAGE': error_message,
        }

        supplier_name = result.get('supplier_name')
        if supplier_name:
            updates['SUPPLIER'] = supplier_name

        last_processed = result.get('last_processed')
        if isinstance(last_processed, datetime):
            updates['LAST_PROCESSED'] = last_processed.isoformat()
        elif isinstance(last_processed, str) and last_processed:
            updates['LAST_PROCESSED'] = last_processed

        return updates

    def _compose_csv_message(self, result_payload: dict) -> str:
        status_code = (result_payload.get('status_code') or '').upper()
        status_reason = result_payload.get('status_reason', '') or ''
        fallback_used = bool(result_payload.get('fallback_used'))
        fallback_details = result_payload.get('fallback_details') or {}
        trigger_reason = (
            result_payload.get('fallback_trigger_reason')
            or fallback_details.get('trigger_reason')
            or ''
        )
        message = result_payload.get('message', '') or ''

        if fallback_used:
            parts: list[str] = []
            if message:
                parts.append(message)

            if trigger_reason == 'po_without_pdf':
                parts.append('PO page did not expose PDF attachments.')
            elif trigger_reason == 'po_without_attachments':
                parts.append('PO page did not expose attachments.')

            source = (fallback_details.get('source') or '').strip()
            if source:
                friendly_source = source.replace('::', ' via ')
                parts.append(f"PR link source: {friendly_source}")

            pr_url = (fallback_details.get('url') or '').strip()
            if pr_url:
                parts.append(f"PR URL: {pr_url}")

            if not parts:
                parts.append('PR fallback used to retrieve documents.')
            return ' — '.join(parts)

        if status_code == 'COMPLETED':
            return ''
        if message:
            return message
        if status_code == 'NO_ATTACHMENTS':
            return status_reason.replace('_', ' ').title() if status_reason else 'No attachments found.'
        if status_reason:
            return status_reason.replace('_', ' ').title()
        return ''

    def process_single_po(self, po_data, hierarchy_cols, has_hierarchy_data, index, total):
        """Process a single PO using the existing browser window (no extra tabs)."""
        display_po = po_data['po_number']
        po_number = po_data['po_number']
        if self._run_start_time is None:
            self._prepare_progress_tracking(total)

        self._current_po_start_time = time.perf_counter()
        vendor_hint = po_data.get('supplier') or po_data.get('vendor') or ''
        print(self._build_progress_line(index, total))
        print(f"   Current PO: {display_po}")

        try:
            # Create hierarchical folder structure
            folder_path = self.folder_hierarchy.create_folder_path(
                po_data, hierarchy_cols, has_hierarchy_data
            )
            print(f"   📁 Folder: {folder_path}")

            # Process entirely under lock to avoid Selenium races (single window)
            with self.lock:
                # Ensure driver exists and is responsive
                if not self.browser_manager.is_browser_responsive():
                    print("   ⚠️ Browser not responsive. Reinitializing driver...")
                    self.browser_manager.cleanup()
                    self.browser_manager.initialize_driver(headless=self._get_headless_setting())
                    self.driver = self.browser_manager.driver

                # Ensure downloads for this PO go to the right folder
                self.browser_manager.update_download_directory(folder_path)

                # Create downloader and attempt processing
                downloader = Downloader(self.driver, self.browser_manager)
                try:
                    result_payload = downloader.download_attachments_for_po(po_number)
                except (InvalidSessionIdException, NoSuchWindowException) as e:
                    # Session/tab was lost. Try to recover once.
                    print(f"   ⚠️ Session issue detected ({type(e).__name__}). Recovering driver and retrying once...")
                    self.browser_manager.cleanup()
                    self.browser_manager.initialize_driver(headless=self._get_headless_setting())
                    self.driver = self.browser_manager.driver
                    downloader = Downloader(self.driver, self.browser_manager)
                    result_payload = downloader.download_attachments_for_po(po_number)

                message = result_payload.get('message', '')

                # Wait for downloads to complete before finalizing folder name
                _wait_for_downloads_complete(folder_path)

                # Derive unified status and rename folder with standardized suffix
                status_code = _derive_status_label(result_payload)
                try:
                    final_folder = self.folder_hierarchy.finalize_folder(folder_path, status_code)
                except Exception:
                    final_folder = _legacy_rename_folder_with_status(folder_path, status_code)
                status_reason = result_payload.get('status_reason', '')
                errors = result_payload.get('errors', [])

                # Update status with the final folder path and enriched fields
                formatted_names = self.folder_hierarchy.format_attachment_names(
                    result_payload.get('attachment_names', [])
                )
                csv_message = self._compose_csv_message(result_payload)
                if self.csv_handler:
                    try:
                        self.csv_handler.update_record(display_po, {
                            'STATUS': status_code,
                            'SUPPLIER': result_payload.get('supplier_name', ''),
                            'ATTACHMENTS_FOUND': result_payload.get('attachments_found', 0),
                            'ATTACHMENTS_DOWNLOADED': result_payload.get('attachments_downloaded', 0),
                            'AttachmentName': formatted_names,
                            'ERROR_MESSAGE': csv_message,
                            'DOWNLOAD_FOLDER': final_folder,
                            'COUPA_URL': result_payload.get('coupa_url', ''),
                        })
                    except Exception as e:
                        print(f"[seq] ⚠️ Failed incremental CSV update: {e}")

                # (Legacy note) Incremental CSVHandler não é usado no modo sequencial aqui.
                # Persistência incremental já coberta por excel_processor.update_po_status acima.

                emoji = {
                    'COMPLETED': '✅',
                    'NO_ATTACHMENTS': '📭',
                    'PARTIAL': '⚠️',
                    'FAILED': '❌',
                    'PO_NOT_FOUND': '🚫',
                }.get(status_code, 'ℹ️')
                log_message = message or status_reason or status_code
                print(f"   {emoji} {display_po}: {log_message}")
                return status_code in {'COMPLETED', 'NO_ATTACHMENTS'}

        except Exception as e:
            friendly = _humanize_exception(e)
            print(f"   ❌ Error processing {display_po}: {friendly}")
            # Use unified FAILED status on exceptions in sequential mode
            if self.csv_handler:
                try:
                    self.csv_handler.update_record(display_po, {
                        'STATUS': 'FAILED',
                        'ERROR_MESSAGE': friendly,
                    })
                except Exception as e:
                    print(f"[seq] ⚠️ Failed incremental CSV update (failed path): {e}")

            # Persist to CSV if handler is initialized
            if self.csv_handler:
                failed_result = {
                    'po_number': po_number,
                    'po_number_display': display_po,
                    'status_code': 'FAILED',
                    'message': friendly,
                    'supplier_name': vendor_hint,
                }
                if self.csv_handler:
                    try:
                        self.csv_handler.update_record(display_po, {
                            'STATUS': 'FAILED',
                            'ERROR_MESSAGE': friendly,
                        })
                    except Exception as e:
                        print(f"[seq-exception] ⚠️ Failed incremental CSV update: {e}")

            # Clean up browser state: close any extra tabs and return to main tab
            try:
                with self.lock:
                    # Skip cleanup if driver doesn't exist
                    if self.driver is None:
                        print("   ⚠️ Driver is None - skipping cleanup")
                        return False
                    
                    # Attempt to close extra tabs if they exist
                    try:
                        if len(self.driver.window_handles) > 1:
                            self.driver.close()
                            self.driver.switch_to.window(self.driver.window_handles[0])
                    except (NoSuchWindowException, InvalidSessionIdException) as e:
                        print(f"   ⚠️ Tab cleanup error: {str(e)}")
            except Exception as unexpected_error:
                print(f"   ⚠️ Unexpected cleanup error: {str(unexpected_error)}")
            
            # Always attempt browser recovery after errors
            try:
                with self.lock:
                    if self.driver is None or not self.browser_manager.is_browser_responsive():
                        print("   ⚠️ Attempting browser recovery")
                        self.browser_manager.cleanup()
                        self.browser_manager.initialize_driver(headless=self._get_headless_setting())
                        self.driver = self.browser_manager.driver
            except Exception as recovery_error:
                print(f"   🔴 Browser recovery failed: {str(recovery_error)}")

            return False
        finally:
            self._register_po_completion()

    def _process_po_entries(
        self,
        po_data_list: list[dict],
        hierarchy_cols: list[str],
        has_hierarchy_data: bool,
        use_process_pool: bool,
        headless_config: HeadlessConfiguration,
    ) -> tuple[int, int]:
        """
        Process PO entries with automatic parallel mode selection.
        
        Enhanced to support ProcessingSession for intelligent parallel processing.
        Falls back to original implementation for backward compatibility.
        """
        # Check if parallel processing is enabled and beneficial
        if self.enable_parallel and len(po_data_list) > 1 and use_process_pool:
            try:
                # Use WorkerManager for ProcessingSession approach
                successful, failed, session_report = self.worker_manager.process_parallel_with_session(
                    po_data_list, hierarchy_cols, has_hierarchy_data, headless_config,
                    csv_handler=self.csv_handler, folder_hierarchy=self.folder_hierarchy
                )
                
                self._last_parallel_report = session_report
                return successful, failed
                
            except Exception as e:
                print(f"⚠️  ProcessingSession failed, falling back to legacy processing: {e}")
                # Fall through to legacy implementation

        # Legacy implementation (backward compatibility)
        if use_process_pool:
            # Use WorkerManager for legacy ProcessPoolExecutor approach
            successful, failed = self.worker_manager.process_parallel_legacy(
                po_data_list, hierarchy_cols, has_hierarchy_data, headless_config,
                csv_handler=self.csv_handler, folder_hierarchy=self.folder_hierarchy
            )
            return successful, failed
        else:
            print("📊 Using in-process mode (single WebDriver, sequential)")
            self.initialize_browser_once()
            self._prepare_progress_tracking(len(po_data_list))
            successful = 0
            failed = 0
            for i, po_data in enumerate(po_data_list):
                ok = self.process_single_po(po_data, hierarchy_cols, has_hierarchy_data, i, len(po_data_list))
                if ok:
                    successful += 1
                    self.global_stats["completed"] += 1
                else:
                    failed += 1
                    self.global_stats["failed"] += 1
                # Update active count (decrement as we complete)
                self.global_stats["active"] = max(0, len(po_data_list) - (successful + failed))
                
                # Calculate elapsed time and ETA
                if self._run_start_time:
                    elapsed_seconds = time.perf_counter() - self._run_start_time
                    minutes, seconds = divmod(int(elapsed_seconds), 60)
                    self.global_stats["elapsed"] = f"{minutes}m {seconds}s"
                    
                    # Estimate ETA global
                    if successful > 0:
                        avg_time_per_po = elapsed_seconds / successful
                        remaining_pos = len(po_data_list) - successful - failed
                        eta_seconds = avg_time_per_po * remaining_pos
                        eta_minutes, eta_seconds = divmod(int(eta_seconds), 60)
                        self.global_stats["eta_global"] = f"{eta_minutes}m {eta_seconds}s"
                    else:
                        self.global_stats["eta_global"] = "⏳"
                    
                    # Calculate global efficiency
                    if elapsed_seconds > 0:
                        global_efficiency = (successful / elapsed_seconds) * 60  # POs per minute
                        self.global_stats["global_efficiency"] = f"{global_efficiency:.1f} POs/min"
                    else:
                        self.global_stats["global_efficiency"] = "⏳"
                
                # Update worker progress for single worker
                self.worker_states[0]["progress"] = f"{successful + failed}/{len(po_data_list)} POs"
                self.worker_states[0]["elapsed"] = self.global_stats["elapsed"]
                self.worker_states[0]["eta"] = self.global_stats["eta_global"]
                efficiency = f"{(successful / max(1, elapsed_seconds)) * 60:.1f} POs/min" if elapsed_seconds > 0 else "⏳"
                self.worker_states[0]["efficiency"] = efficiency
                
                # Update live display
                if self.live:
                    self.live.update(Group(self._update_header(), "", self._build_progress_table()))

        return successful, failed

    def run(self) -> None:
        """
        Main execution loop for processing POs.
        """
        # Interactive or non-interactive configuration
        # Re-evaluate ENABLE_INTERACTIVE_UI at runtime to allow dynamic control
        enable_interactive = os.environ.get('ENABLE_INTERACTIVE_UI', 'True').strip().lower() == 'true'
        
        if enable_interactive:
            setup_session = self.setup_manager.interactive_setup()
            headless_config = HeadlessConfiguration(enabled=setup_session.headless_preference)
        else:
            print("⚙️ Applying environment configuration")
            config = self.setup_manager.apply_env_overrides()
            headless_config = HeadlessConfiguration(enabled=config["headless_preference"])
        
        self.set_headless_configuration(headless_config)

        os.makedirs(ExperimentalConfig.INPUT_DIR, exist_ok=True)
        os.makedirs(ExperimentalConfig.DOWNLOAD_FOLDER, exist_ok=True)

        try:
            excel_path = self.excel_processor.get_excel_file_path()
            # Inform which input file will be processed (CSV or Excel)
            _, ext = os.path.splitext(excel_path.lower())
            file_kind = "CSV" if ext == ".csv" else "Excel"
            print(f"📄 Processing input file: {excel_path} ({file_kind})")
            po_entries, original_cols, hierarchy_cols, has_hierarchy_data = self.excel_processor.read_po_numbers_from_excel(excel_path)
            valid_entries = self.excel_processor.process_po_numbers(po_entries)
        except Exception as e:
            print(f"❌ Failed to read or process input file: {e}")
            return

        if not valid_entries:
            print("No valid PO entries found to process.")
            return

        print(f"📊 CSV Reading Results:")
        print(f"  - Total entries read: {len(po_entries)}")
        print(f"  - Valid POs after processing: {len(valid_entries)}")
        print(f"  - PO numbers: {[entry[0] for entry in valid_entries[:10]]}{'...' if len(valid_entries) > 10 else ''}")

        # Initialize CSV handler if input file is CSV
        csv_input_path = Path(excel_path)
        if csv_input_path.suffix.lower() == '.csv' and not self.csv_handler:
            self._initialize_csv_handler(csv_input_path)

        # Convert to list of PO data
        po_data_list = []
        for display_po, po_number in valid_entries:
            for entry in po_entries:
                if entry['po_number'] == display_po:
                    po_data_list.append(entry)
                    break

        print(f"📋 PO Data Conversion:")
        print(f"  - Valid entries: {len(valid_entries)}")
        print(f"  - Po_data_list created: {len(po_data_list)}")
        print(f"  - Sample PO data: {po_data_list[0] if po_data_list else 'None'}")
        print(f"🚀 Starting processing with {len(po_data_list)} POs...")
        use_process_pool = bool(getattr(ExperimentalConfig, 'USE_PROCESS_POOL', False))  # Derived from worker count

        requested_workers = getattr(ExperimentalConfig, 'PROC_WORKERS', self.max_workers)
        try:
            configured_workers_raw = int(requested_workers)
        except (TypeError, ValueError):
            configured_workers_raw = self.max_workers
        cap = int(getattr(ExperimentalConfig, 'PROC_WORKERS_CAP', 0) or 0)
        if cap > 0:
            configured_workers = max(1, min(configured_workers_raw, cap))
        else:
            configured_workers = max(1, configured_workers_raw)
        self.max_workers = configured_workers

        if use_process_pool and not self.enable_parallel:
            self.enable_parallel = True

        # Set initial global stats
        self.global_stats["total"] = len(po_data_list)
        self._run_start_time = time.perf_counter()

        # Initialize worker states
        self.worker_states = [
            {
                "worker_id": f"Worker {i+1}",
                "progress": "0/0 POs",
                "elapsed": "0m 0s",
                "eta": "⏳",
                "efficiency": "⏳"
            } for i in range(self.max_workers)
        ]

        # Start Live display with initial Group
        initial_renderable = Group(self._update_header(), "", self._build_progress_table())
        with Live(initial_renderable, console=self.console, refresh_per_second=1) as live:
            self.live = live
            
            # Start a thread to update elapsed time every second
            def update_timer():
                while self.live:
                    time.sleep(1)
                    if self._run_start_time:
                        elapsed_seconds = time.perf_counter() - self._run_start_time
                        minutes, seconds = divmod(int(elapsed_seconds), 60)
                        self.global_stats["elapsed"] = f"{minutes}m {seconds}s"
                        # Update worker elapsed
                        for worker in self.worker_states:
                            worker["elapsed"] = self.global_stats["elapsed"]
                        try:
                            self.live.update(Group(self._update_header(), "", self._build_progress_table()))
                        except:
                            break  # Live closed
            
            timer_thread = threading.Thread(target=update_timer, daemon=True)
            timer_thread.start()
            
            # Process POs directly without UI
            if self._headless_config is None:
                raise RuntimeError("Headless configuration not set.")
                
            successful, failed = self._process_po_entries(
                po_data_list,
                hierarchy_cols,
                has_hierarchy_data,
                use_process_pool,
                self._headless_config,
            )

        # Shutdown CSV handler to ensure all data is persisted
        if self.csv_handler:
            self._shutdown_csv_handler()

        print("-" * 60)
        print("🎉 Processing complete!")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Total: {successful + failed}")

    def close(self):
        """Close the browser properly."""
        # Shutdown CSV handler first
        if self.csv_handler:
            self._shutdown_csv_handler()
            
        if self.driver:
            print("🔄 Closing browser...")
            self.browser_manager.cleanup()
            self.driver = None
            print("✅ Browser closed successfully")


class SessionStatus(Enum):
    """Status enumeration for processing sessions."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingSession:
    """
    High-level processing session that manages PO batch processing with automatic mode selection.
    
    This class implements the ProcessingSession API contract for T026 and T027.
    """
    
    def __init__(
        self,
        headless_config: HeadlessConfiguration,
        enable_parallel: bool = True,
        max_workers: int = 4,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        hierarchy_columns: Optional[List[str]] = None,
        has_hierarchy_data: bool = False,
    ):
        """Initialize processing session for PO batch processing."""
        # Validate parameters
        if not isinstance(headless_config, HeadlessConfiguration):
            raise TypeError("headless_config must be HeadlessConfiguration instance")
        
        if not (isinstance(max_workers, int) and max_workers >= 1):
            raise ValueError(f"max_workers must be a positive integer, got {max_workers}")
        
        # Configuration
        self.headless_config = headless_config
        self.enable_parallel = enable_parallel
        self.max_workers = max_workers
        self.progress_callback = progress_callback
        self.hierarchy_columns = hierarchy_columns
        self.has_hierarchy_data = has_hierarchy_data
        
        # Session state
        self.status = SessionStatus.IDLE
        self.worker_pool: Optional[PersistentWorkerPool] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        # Processing metrics
        self.total_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.active_tasks = 0
        self.processing_mode = "sequential"

        # Progress tracking
        self._progress_lock = threading.Lock()
        self._last_progress_update = datetime.now()
        self.last_results: List[Dict[str, Any]] = []
        
        # CSV handler support
        self.csv_path: Optional[str] = None
    
    def set_csv_path(self, csv_path: str) -> None:
        """Set CSV path for worker processes."""
        self.csv_path = csv_path
    
    def process_pos(self, po_list: List[dict]) -> Tuple[int, int, Dict[str, Any]]:
        """Process list of POs with automatic mode selection."""
        try:
            self.status = SessionStatus.RUNNING
            self.start_time = datetime.now()
            self.total_tasks = len(po_list)
            self.last_results = []
            
            # Determine processing mode
            self.processing_mode = self.get_processing_mode(len(po_list))
            
            print(f"🚀 Starting {self.processing_mode} processing of {len(po_list)} POs")
            
            if self.processing_mode == "parallel":
                return self._process_parallel(po_list)
            else:
                return self._process_sequential(po_list)
                
        except Exception as e:
            self.status = SessionStatus.FAILED
            print(f"❌ Processing failed: {e}")
            return 0, len(po_list), {"error": str(e)}
        
        finally:
            self.end_time = datetime.now()
            if self.status == SessionStatus.RUNNING:
                self.status = SessionStatus.COMPLETED
    
    def get_processing_mode(self, po_count: int) -> str:
        """Determine processing mode based on configuration and PO count."""
        # Decision criteria for parallel processing
        if not self.enable_parallel:
            return "sequential"
        
        if po_count <= 1:
            return "sequential"
        
        # Check system resources (simplified check)
        if self._check_system_resources():
            return "parallel"
        
        return "sequential"
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current processing progress and status."""
        with self._progress_lock:
            elapsed_time = 0.0
            if self.start_time:
                end_time = self.end_time or datetime.now()
                elapsed_time = (end_time - self.start_time).total_seconds()
            
            # Calculate estimated remaining time
            estimated_remaining = None
            if self.completed_tasks > 0 and self.total_tasks > self.completed_tasks:
                avg_time_per_task = elapsed_time / self.completed_tasks
                remaining_tasks = self.total_tasks - self.completed_tasks
                estimated_remaining = avg_time_per_task * remaining_tasks
            
            progress = {
                'session_status': self.status.value,
                'total_tasks': self.total_tasks,
                'completed_tasks': self.completed_tasks,
                'failed_tasks': self.failed_tasks,
                'active_tasks': self.active_tasks,
                'elapsed_time': elapsed_time,
                'estimated_remaining': estimated_remaining,
                'processing_mode': self.processing_mode,
                'worker_details': []
            }
            
            # Add worker details if parallel processing
            if self.worker_pool and self.processing_mode == "parallel":
                status = self.worker_pool.get_status()
                progress['worker_details'] = status.get('workers', {})
            
            return progress
    
    def stop_processing(self) -> bool:
        """Stop current processing session."""
        if self.status != SessionStatus.RUNNING:
            return True
        
        try:
            if self.worker_pool:
                # Run async shutdown in sync context
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Create task for shutdown
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(asyncio.run, self.worker_pool.shutdown())
                            future.result(timeout=60)  # 1 minute timeout
                    else:
                        loop.run_until_complete(self.worker_pool.shutdown())
                except RuntimeError:
                    asyncio.run(self.worker_pool.shutdown())
                
                self.worker_pool = None
                return True
            
            self.status = SessionStatus.COMPLETED
            return True
            
        except Exception as e:
            print(f"Error stopping processing: {e}")
            self.status = SessionStatus.FAILED
            return False
    
    # Private helper methods
    
    def _process_parallel(self, po_list: List[dict]) -> Tuple[int, int, Dict[str, Any]]:
        """Process POs using parallel worker pool."""
        # Check if profiles are disabled - if so, fall back to ProcessPoolExecutor
        from .lib.config import Config as _Cfg
        if not _Cfg.USE_PROFILE:
            print("🔄 Profiles disabled, using ProcessPoolExecutor instead of PersistentWorkerPool")
            return self._process_parallel_with_processpool(po_list)
        
        import asyncio
        
        async def _async_process():
            try:
                # Create PoolConfig with profile support
                base_profile_path = _Cfg.EDGE_PROFILE_DIR or ""
                if not base_profile_path:
                    raise ValueError("Profile path required for PersistentWorkerPool, but none configured")
                
                download_root = os.path.abspath(os.path.expanduser(_Cfg.DOWNLOAD_FOLDER))
                print(f"🏗️ Creating worker pool with download_root: {download_root}")

                config = PoolConfig(
                    worker_count=min(self.max_workers, len(po_list)),
                    headless_mode=self.headless_config.get_effective_headless_mode(),
                    base_profile_path=base_profile_path,
                    base_profile_name=ExperimentalConfig.EDGE_PROFILE_NAME or "Default",
                    hierarchy_columns=self.hierarchy_columns,
                    has_hierarchy_data=self.has_hierarchy_data,
                    download_root=download_root,
                )
                
                print(f"🔧 PoolConfig created with download_root: {config.download_root}")
                
                # Create and start worker pool
                csv_handler = None
                if hasattr(self, 'csv_path') and self.csv_path:
                    try:
                        from csv_handler import CSVHandler
                        from pathlib import Path
                        csv_handler = CSVHandler(Path(self.csv_path))
                        print(f"[PersistentWorkerPool] CSV handler created for: {self.csv_path}")
                    except Exception as e:
                        print(f"[PersistentWorkerPool] Failed to create CSV handler: {e}")
                self.worker_pool = PersistentWorkerPool(config, csv_handler=csv_handler)
                await self.worker_pool.start()
                
                # Start progress monitoring thread
                import threading
                monitor_thread = threading.Thread(target=self._monitor_parallel_progress, daemon=True)
                monitor_thread.start()
                
                # Submit tasks
                po_numbers = [po['po_number'] for po in po_list]
                handles = self.worker_pool.submit_tasks(po_list)

                # Wait for completion
                await self.worker_pool.wait_for_completion(timeout=600)  # 10 minute timeout

                # Collect results
                successful = 0
                failed = 0
                collected_results: List[Dict[str, Any]] = []

                for handle in handles:
                    try:
                        result = handle.wait_for_completion(timeout=120)
                        if not isinstance(result, dict):
                            result = {'success': False, 'status_code': 'FAILED', 'message': str(result)}
                        if 'po_number' not in result:
                            result['po_number'] = handle.po_number
                        if 'po_number_display' not in result:
                            result['po_number_display'] = result.get('po_number', handle.po_number)

                        collected_results.append(result)

                        status_code = result.get('status_code', 'FAILED')
                        if status_code in {'COMPLETED', 'NO_ATTACHMENTS'}:
                            successful += 1
                        else:
                            failed += 1
                    except Exception as e:
                        print(f"Error getting result for {handle.po_number}: {e}")
                        collected_results.append({
                            'po_number': handle.po_number,
                            'po_number_display': handle.po_number,
                            'status_code': 'FAILED',
                            'message': str(e),
                            'errors': [{'filename': '', 'reason': str(e)}],
                            'success': False,
                            'attachment_names': [],
                            'attachments_found': 0,
                            'attachments_downloaded': 0,
                            'final_folder': '',
                        })
                        failed += 1

                # Get performance data from status
                status = self.worker_pool.get_status()
                performance_data = {
                    'memory_usage': status.get('memory', {}),
                    'worker_stats': status.get('workers', {}),
                    'task_queue_stats': status.get('task_queue', {})
                }

                # Shutdown
                await self.worker_pool.shutdown()
                self.worker_pool = None

                # Process results for CSV persistence (workers should handle this individually)
                # Note: CSV persistence is handled by individual workers in process_po_worker function

                session_report = {
                    'processing_mode': 'parallel',
                    'worker_count': config.worker_count,
                    'performance_data': performance_data,
                    'session_duration': (self.end_time - self.start_time).total_seconds() if self.end_time and self.start_time else 0,
                    'results': collected_results,
                }

                self.last_results = collected_results
                
                return successful, failed, session_report
                
            except Exception as e:
                if self.worker_pool:
                    try:
                        await self.worker_pool.shutdown()
                    except:
                        pass
                    self.worker_pool = None
                raise e
        
        # Run async processing in sync context
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If there's already a running loop, we need to handle this differently
                # For now, create a new thread with its own event loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, _async_process())

                    return future.result(timeout=900)  # 15 minute timeout
            else:
                return loop.run_until_complete(_async_process())
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(_async_process())
    
    def _process_sequential(self, po_list: List[dict]) -> Tuple[int, int, Dict[str, Any]]:
        """Process POs using sequential processing with real downloads (single WebDriver)."""
        from .lib.browser import BrowserManager
        from .lib.po_processing import process_single_po

        successful = 0
        failed = 0
        results: List[Dict[str, Any]] = []

        browser_manager = BrowserManager()
        driver = None
    # Folder manager usage is encapsulated inside process_single_po

        try:
            # Initialize a single browser instance for all POs
            browser_manager.initialize_driver(headless=self.headless_config.get_effective_headless_mode())
            driver = browser_manager.driver

            for i, po in enumerate(po_list):
                po_number = po.get('po_number', '')
                display_po = po_number
                folder_path = ''
                try:
                    # Progress bookkeeping
                    self.completed_tasks = i  # completed so far
                    self.active_tasks = 1
                    self._update_progress()

                    # Process single PO using shared utility
                    result_entry = process_single_po(
                        po_number=po_number,
                        po_data=po,
                        driver=driver,
                        browser_manager=browser_manager,
                        hierarchy_columns=self.hierarchy_columns or [],
                        has_hierarchy_data=bool(self.has_hierarchy_data),
                    )
                    results.append(result_entry)

                    if result_entry['success']:
                        successful += 1
                    else:
                        failed += 1

                except Exception as e:
                    # On error, mark failed and continue
                    results.append({
                        'po_number': po_number,
                        'po_number_display': display_po or po_number,
                        'status_code': 'FAILED',
                        'message': str(e),
                        'final_folder': '',
                        'errors': [{'filename': '', 'reason': str(e)}],
                        'success': False,
                        'attachment_names': [],
                        'attachments_found': 0,
                        'attachments_downloaded': 0,
                    })
                    failed += 1

                finally:
                    # Update per-item progress
                    self.completed_tasks = i + 1
                    self.active_tasks = 0
                    self._update_progress()

        finally:
            try:
                if driver is not None:
                    browser_manager.cleanup()
            except Exception:
                pass

        session_report = {
            'processing_mode': 'sequential',
            'worker_count': 1,
            'session_duration': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            'results': results,
        }

        self.last_results = results
        return successful, failed, session_report
    
    def _process_parallel_with_processpool(self, po_list: List[dict]) -> Tuple[int, int, Dict[str, Any]]:
        """Process POs using ProcessPoolExecutor when profiles are disabled."""
        successful = 0
        failed = 0
        results: List[Dict[str, Any]] = []
        
        # Use ProcessPoolExecutor similar to MainApp._process_po_entries
        import multiprocessing as mp
        from concurrent.futures import ProcessPoolExecutor, as_completed
        
        # Calculate workers
        default_workers = min(2, len(po_list))
        proc_workers = max(1, min(self.max_workers, len(po_list)))
        print(f"📊 Using {proc_workers} ProcessPoolExecutor worker(s) (profiles disabled)")
        
        # Get download root for workers
        from .lib.config import Config
        download_root = os.path.abspath(os.path.expanduser(getattr(Config, 'DOWNLOAD_FOLDER', ExperimentalConfig.DOWNLOAD_FOLDER)))
        
        with ProcessPoolExecutor(max_workers=proc_workers, mp_context=mp.get_context("spawn")) as executor:
            future_map: dict = {}
            
            # Convert po_list to expected format and submit tasks
            for po_data in po_list:
                # Determine CSV path for worker (ProcessingSession doesn't have direct CSV handler access)
                csv_path = None
                # Try to get CSV path from environment or current working directory
                try:
                    if hasattr(self, 'csv_path') and self.csv_path:
                        csv_path = str(self.csv_path)
                except:
                    pass
                
                # Ensure po_data has the right format for process_po_worker
                task_args = (
                    po_data, 
                    self.hierarchy_columns or [], 
                    bool(self.has_hierarchy_data), 
                    self.headless_config,
                    download_root,
                    csv_path
                )
                
                future = executor.submit(process_po_worker, task_args)
                future_map[future] = po_data
                
                # Update progress
                self.total_tasks = len(po_list)
                self._update_progress()
            
            # Collect results
            for future in as_completed(future_map):
                po_data = future_map[future]
                po_number = po_data.get('po_number', '')
                
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result.get('success', False) or result.get('status_code') in {'COMPLETED', 'NO_ATTACHMENTS'}:
                        successful += 1
                    else:
                        failed += 1
                        
                except Exception as exc:
                    # Handle worker exceptions
                    error_result = {
                        'po_number': po_number,
                        'po_number_display': po_number,
                        'status_code': 'FAILED',
                        'message': str(exc),
                        'final_folder': '',
                        'errors': [{'filename': '', 'reason': str(exc)}],
                        'success': False,
                        'attachment_names': [],
                        'attachments_found': 0,
                        'attachments_downloaded': 0,
                    }
                    results.append(error_result)
                    failed += 1
                
                # Update progress after each completion
                self.completed_tasks = successful + failed
                self._update_progress()
        
        # Create session report
        session_report = {
            'processing_mode': 'parallel_processpool',
            'worker_count': proc_workers,
            'session_duration': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            'results': results,
        }
        
        self.last_results = results
        return successful, failed, session_report
    
    def _monitor_parallel_progress(self):
        """Monitor progress of parallel processing."""
        while self.status == SessionStatus.RUNNING and self.worker_pool:
            try:
                # Get status from task queue
                queue_stats = self.worker_pool.task_queue.get_queue_status()
                
                self.completed_tasks = queue_stats.get('completed_tasks', 0)
                self.failed_tasks = queue_stats.get('failed_tasks', 0)
                self.active_tasks = queue_stats.get('processing_tasks', 0)
                
                self._update_progress()
                
                # Check if processing is complete
                total_processed = self.completed_tasks + self.failed_tasks
                if total_processed >= self.total_tasks:
                    break
                
                time.sleep(1)  # Update every second
                
            except Exception as e:
                print(f"Error monitoring progress: {e}")
                break
    
    def _update_progress(self):
        """Update progress via callback if configured."""
        if self.progress_callback:
            try:
                progress = self.get_progress()
                self.progress_callback(progress)
            except Exception as e:
                print(f"Error in progress callback: {e}")
    
    def _check_system_resources(self) -> bool:
        """Check if system has adequate resources for parallel processing."""
        # Simplified resource check
        try:
            cpu_count = mp.cpu_count()
            # Use parallel processing if we have enough CPU cores
            return cpu_count >= 2
        except:
            return False


def main() -> None:
    """Run the experimental UI workflow."""
    try:
        configured_workers = int(ExperimentalConfig.MAX_PARALLEL_WORKERS)
    except (TypeError, ValueError):
        configured_workers = 4
    # Removed previous hard cap of 8
    max_workers = max(1, configured_workers)

    app = MainApp(enable_parallel=True, max_workers=max_workers)
    try:
        app.run()
    finally:
        app.close()


if __name__ == "__main__":
    main()
