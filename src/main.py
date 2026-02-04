"""
Módulo principal do sistema CoupaDownloads.

Este módulo contém a classe MainApp, responsável por orquestrar o processamento de POs,
gerenciamento de UI, CSV e workers paralelos para download de anexos no Coupa.
"""

import os
import sys
import time
import threading
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Callable
from enum import Enum
import pandas as pd
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

from rich.live import Live
from .lib.browser import BrowserManager
from .lib.config import Config as ExperimentalConfig
from .lib.downloader import Downloader
from .lib.excel_processor import ExcelProcessor
from .lib.folder_hierarchy import FolderHierarchyManager
from .lib.models import HeadlessConfiguration, InteractiveSetupSession

# Import new managers
from .setup_manager import SetupManager
from .worker_manager import WorkerManager, ProcessingSession, _wait_for_downloads_complete, _legacy_rename_folder_with_status, _derive_status_label
from .ui_controller import UIController
from .core.communication_manager import CommunicationManager
from .processing_controller import ProcessingController
from .csv_manager import CSVManager
from .core.resource_assessor import ResourceAssessor

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
        self.ui_controller = UIController()
        self.processing_controller = ProcessingController(self.worker_manager, self.ui_controller)
        self.csv_manager = CSVManager()
        self.communication_manager = CommunicationManager()
        self.driver = None
        self.lock = threading.Lock()  # Thread safety for browser operations
        self._run_start_time: float | None = None
        self._current_po_start_time: float | None = None
        self._completed_po_count = 0
        self._total_po_count = 0
        self._accumulated_po_seconds = 0.0
        self._headless_config: HeadlessConfiguration | None = None

    def set_headless_configuration(self, headless_config: HeadlessConfiguration) -> None:
        """Set the headless configuration for this MainApp instance."""
        self._headless_config = headless_config
        print(f"[MainApp] 🎯 Headless configuration set: {headless_config}")
    
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
        """Format duration in seconds to HH:MM string."""
        if seconds is None or seconds < 0:
            return "--:--"
        total_minutes = int(seconds // 60)
        hours, minutes = divmod(total_minutes, 60)
        return f"{hours:02d}:{minutes:02d}"

    def _progress_snapshot(self) -> tuple[str, str, str]:
        """Get current progress snapshot as (elapsed, remaining, eta)."""
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
        """Build progress line string for current PO processing."""
        elapsed, remaining, eta = self._progress_snapshot()
        return (
            f"📋 Processing PO {index + 1}/{total} – "
            f"Elapsed Time: {elapsed}, Remaining Time: {remaining}, "
            f"Estimated Completion: {eta}"
        )

    def _register_po_completion(self) -> None:
        """Register completion of a PO for timing statistics."""
        if self._current_po_start_time is None:
            return

        duration = max(0.0, time.perf_counter() - self._current_po_start_time)
        self._accumulated_po_seconds += duration
        if self._total_po_count > 0:
            self._completed_po_count = min(self._completed_po_count + 1, self._total_po_count)
        else:
            self._completed_po_count += 1
        self._current_po_start_time = None


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
        """Compose error message for CSV from result payload."""
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

            def _update_seq_worker(status: str, attachments_found: int = 0, attachments_downloaded: int = 0) -> None:
                if not self.ui_controller.worker_states:
                    self.ui_controller.worker_states = [{
                        "worker_id": "Worker 1",
                        "current_po": "Idle",
                        "status": "Idle",
                        "attachments_found": 0,
                        "attachments_downloaded": 0,
                        "duration": 0.0,
                    }]
                worker_state = self.ui_controller.worker_states[0]
                worker_state["current_po"] = display_po
                worker_state["status"] = status
                worker_state["attachments_found"] = attachments_found
                worker_state["attachments_downloaded"] = attachments_downloaded
                if self._current_po_start_time:
                    worker_state["duration"] = max(0.0, time.perf_counter() - self._current_po_start_time)
                self.ui_controller.update_display()

            def _emit_progress(payload: Dict[str, Any]) -> None:
                _update_seq_worker(
                    status=payload.get("status", "PROCESSING"),
                    attachments_found=payload.get("attachments_found", 0),
                    attachments_downloaded=payload.get("attachments_downloaded", 0),
                )

            _update_seq_worker("STARTED")

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
                downloader = Downloader(self.driver, self.browser_manager, progress_callback=_emit_progress)
                try:
                    result_payload = downloader.download_attachments_for_po(po_number)
                except (InvalidSessionIdException, NoSuchWindowException) as e:
                    # Session/tab was lost. Try to recover once.
                    print(f"   ⚠️ Session issue detected ({type(e).__name__}). Recovering driver and retrying once...")
                    self.browser_manager.cleanup()
                    self.browser_manager.initialize_driver(headless=self._get_headless_setting())
                    self.driver = self.browser_manager.driver
                    downloader = Downloader(self.driver, self.browser_manager, progress_callback=_emit_progress)
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
                if self.csv_manager.is_initialized():
                    try:
                        self.csv_manager.update_record(display_po, {
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
                _update_seq_worker(
                    status=status_code,
                    attachments_found=result_payload.get('attachments_found', 0),
                    attachments_downloaded=result_payload.get('attachments_downloaded', 0),
                )
                return status_code in {'COMPLETED', 'NO_ATTACHMENTS'}

        except Exception as e:
            friendly = _humanize_exception(e)
            print(f"   ❌ Error processing {display_po}: {friendly}")
            # Use unified FAILED status on exceptions in sequential mode
            if self.csv_manager.is_initialized():
                try:
                    self.csv_manager.update_record(display_po, {
                        'STATUS': 'FAILED',
                        'ERROR_MESSAGE': friendly,
                    })
                except Exception as e:
                    print(f"[seq] ⚠️ Failed incremental CSV update (failed path): {e}")

            # Persist to CSV if handler is initialized
            if self.csv_manager.is_initialized():
                failed_result = {
                    'po_number': po_number,
                    'po_number_display': display_po,
                    'status_code': 'FAILED',
                    'message': friendly,
                    'supplier_name': vendor_hint,
                }
                if self.csv_manager.is_initialized():
                    try:
                        self.csv_manager.update_record(display_po, {
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
        if csv_input_path.suffix.lower() == '.csv':
            self.csv_manager.initialize_csv_handler(csv_input_path)
            
            # Seed SQLite if used (high performance persistence for parallel processes)
            if self.csv_manager.sqlite_handler:
                try:
                    df_seed = pd.DataFrame(po_entries)
                    self.csv_manager.seed_sqlite(df_seed)
                except Exception as e:
                    print(f"⚠️ Failed to seed SQLite database: {e}")

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

        # Resource-Aware Scaling Assessment
        if getattr(ExperimentalConfig, 'RESOURCE_AWARE_SCALING', True):
            print(f"🔍 Performing Resource-Aware Risk Assessment (Target: {configured_workers_raw} workers)...")
            min_free_ram = float(getattr(ExperimentalConfig, 'MIN_FREE_RAM_GB', 0.3))
            configured_workers, report = ResourceAssessor.calculate_safe_worker_count(configured_workers_raw, min_free_ram_gb=min_free_ram)
            print(ResourceAssessor.get_risk_message(report))
            
            if report["is_throttled"]:
                print(f"⚠️ Worker count adjusted: {configured_workers_raw} -> {configured_workers}")
            
            # Use suggested stagger delay to mitigate startup spikes
            stagger_delay = report.get("stagger_delay", 0.5)
            if hasattr(self.worker_manager, 'stagger_delay'):
                self.worker_manager.stagger_delay = stagger_delay
        else:
            cap = int(getattr(ExperimentalConfig, 'PROC_WORKERS_CAP', 0) or 0)
            if cap > 0:
                configured_workers = max(1, min(configured_workers_raw, cap))
            else:
                configured_workers = max(1, configured_workers_raw)
            print(f"ℹ️ Resource-Aware Scaling disabled. Using configured cap: {configured_workers}")

        self.max_workers = configured_workers
        self.worker_manager.max_workers = self.max_workers

        if use_process_pool and not self.enable_parallel:
            self.enable_parallel = True

        # Set initial global stats
        self.ui_controller.global_stats["total"] = len(po_data_list)
        self._run_start_time = time.perf_counter()
        self.processing_controller.set_run_start_time(self._run_start_time)

        # Initialize worker states
        self.ui_controller.worker_states = [
            {
                "worker_id": f"Worker {i+1}",
                "current_po": "Idle",
                "status": "Idle",
                "attachments_found": 0,
                "attachments_downloaded": 0,
                "duration": 0.0
            } for i in range(self.max_workers)
        ]

        # Start Live display with initial Group
        initial_renderable = self.ui_controller.get_initial_renderable()
        with Live(initial_renderable, console=self.ui_controller.console, refresh_per_second=1) as live:
            self.ui_controller.live = live
            
            # Start a thread to update elapsed time every second
            def update_timer():
                while self.ui_controller.live:
                    time.sleep(1)
                    if self._run_start_time:
                        elapsed_seconds = time.perf_counter() - self._run_start_time
                        minutes, seconds = divmod(int(elapsed_seconds), 60)
                        self.ui_controller.global_stats["elapsed"] = f"{minutes}m {seconds}s"
                        # Update worker elapsed
                        for worker in self.ui_controller.worker_states:
                            worker["elapsed"] = self.ui_controller.global_stats["elapsed"]
                        # Update display with new elapsed time
                        try:
                            self.ui_controller.update_display()
                        except:
                            break  # Live closed
            
            timer_thread = threading.Thread(target=update_timer, daemon=True)
            timer_thread.start()

            if use_process_pool and self.enable_parallel:
                self.ui_controller.start_live_updates(self.communication_manager, update_interval=0.5)
            
            # Process POs directly without UI
            if self._headless_config is None:
                raise RuntimeError("Headless configuration not set.")
                
            try:
                successful, failed = self.processing_controller.process_po_entries(
                    po_data_list,
                    hierarchy_cols,
                    has_hierarchy_data,
                    use_process_pool,
                    self._headless_config,
                    self.enable_parallel,
                    self.max_workers,
                    self.csv_manager.csv_handler,
                    self.folder_hierarchy,
                    self.initialize_browser_once,
                    self._prepare_progress_tracking,
                    self.process_single_po,
                    communication_manager=self.communication_manager if use_process_pool and self.enable_parallel else None,
                    sqlite_db_path=self.csv_manager.sqlite_db_path,
                )
            finally:
                if use_process_pool and self.enable_parallel:
                    self.ui_controller.stop_live_updates()

        # Shutdown CSV handler to ensure all data is persisted
        self.csv_manager.shutdown_csv_handler()

        print("-" * 60)
        print("🎉 Processing complete!")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Total: {successful + failed}")

    def close(self, emergency: bool = False):
        """Close the browser properly and stop all active components."""
        if emergency:
            print("\n🚨 Accelerated shutdown initiated...")

        # 1. Stop UI live updates if running
        if hasattr(self, 'ui_controller'):
            try:
                self.ui_controller.stop_live_updates()
            except Exception:
                pass

        # 2. Stop worker manager sessions
        if hasattr(self, 'worker_manager'):
            try:
                if hasattr(self.worker_manager, 'active_session') and self.worker_manager.active_session:
                    print(f"🔄 Stopping active processing session (emergency={emergency})...")
                    self.worker_manager.active_session.stop_processing(emergency=emergency)
            except Exception as e:
                print(f"⚠️ Error stopping worker session: {e}")

        # 3. Shutdown CSV handler to ensure all data is persisted
        if hasattr(self, 'csv_manager'):
            try:
                self.csv_manager.shutdown_csv_handler()
            except Exception:
                pass
            
        # 4. Cleanup browser manager
        if self.driver:
            print("🔄 Closing browser...")
            try:
                self.browser_manager.cleanup()
            except Exception:
                pass
            self.driver = None
            print("✅ Browser closed successfully")


class SessionStatus(Enum):
    """Status enumeration for processing sessions."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


def main() -> None:
    """Run the experimental UI workflow."""
    import signal
    
    try:
        configured_workers = int(ExperimentalConfig.MAX_PARALLEL_WORKERS)
    except (TypeError, ValueError):
        configured_workers = 4
    # Removed previous hard cap of 8
    max_workers = max(1, configured_workers)

    app = MainApp(enable_parallel=True, max_workers=max_workers)
    
    # Interrupt handling state to allow for graceful then forced exit
    shutdown_initiated = False
    
    def signal_handler(sig, frame):
        nonlocal shutdown_initiated
        if shutdown_initiated:
            print("\n🚨 Second interrupt received. Force quitting...")
            os._exit(1)
            
        print("\n🛑 Interrupt received! Initiating graceful shutdown...")
        shutdown_initiated = True
        
        # Trigger the app shutdown
        try:
            app.close(emergency=True)
        except Exception as e:
            print(f"⚠️ Error during app shutdown: {e}")
            
        print("✅ Shutdown sequence completed. Exiting.")
        # Standard exit code for SIGINT is 130
        os._exit(130)

    # Register for SIGINT (Ctrl+C) and SIGTERM
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        app.run()
    except KeyboardInterrupt:
        # Fallback for some thread/environment cases
        if not shutdown_initiated:
            signal_handler(signal.SIGINT, None)
    except Exception as e:
        print(f"❌ Application error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Standard cleanup if finished normally
        if not shutdown_initiated:
            app.close()


if __name__ == "__main__":
    main()
