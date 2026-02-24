"""
Módulo principal do sistema CoupaDownloads.

Este módulo contém a classe MainApp, responsável por orquestrar o processamento de POs,
gerenciamento de UI, CSV e workers paralelos para download de anexos no Coupa.
"""

import os
import sys
import time
import threading
import logging
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

# Project corelib imports are handled via relative imports within the src package.

from .lib.browser import BrowserManager
from .lib.config import Config as ExperimentalConfig
from .lib.downloader import Downloader
from .lib.excel_processor import ExcelProcessor
from .lib.folder_hierarchy import FolderHierarchyManager
from .lib.models import HeadlessConfiguration, InteractiveSetupSession

# Import new managers
from .setup_manager import SetupManager
from .worker_manager import WorkerManager, ProcessingSession
from .core.communication_manager import CommunicationManager
from .processing_controller import ProcessingController
from .csv_manager import CSVManager
from .core.resource_assessor import ResourceAssessor
from .core.telemetry import TelemetryProvider, ConsoleTelemetryListener
from .core.status import StatusLevel
from .services.processing_service import ProcessingService
from .core.utils import _humanize_exception, _wait_for_downloads_complete, _derive_status_label
from .orchestrators import BrowserOrchestrator, ResultAggregator

# Module logger
logger = logging.getLogger(__name__)

# Enable interactive UI mode (set to True to enable interactive prompts)
# Default is True for local interactive use
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
        self.processing_controller = ProcessingController(self.worker_manager)
        self.csv_manager = CSVManager()
        self.telemetry = TelemetryProvider()
        # Add console listener by default for standard execution
        self.telemetry.add_listener(ConsoleTelemetryListener())
        # Use a plain multiprocessing.Queue for broader compatibility with spawn
        self.communication_manager = CommunicationManager(use_manager=True)  # Use Manager for spawn compatibility

        # Initialize orchestrators (extracted from monolithic MainApp)
        self.browser_orchestrator = BrowserOrchestrator(self.browser_manager)
        self.result_aggregator = ResultAggregator(
            csv_handler=self.csv_manager,
            telemetry=self.telemetry,
        )

        self.processing_service = ProcessingService(
            browser_manager=self.browser_manager,
            folder_hierarchy=self.folder_hierarchy,
            storage_manager=self.csv_manager,
            telemetry=self.telemetry,
        )
        # Deprecated: Use browser_orchestrator instead
        self.driver = None
        self.lock = threading.Lock()  # Thread safety for browser operations (now in browser_orchestrator)
        self._run_start_time: float | None = None
        self._current_po_start_time: float | None = None
        self._completed_po_count = 0
        self._total_po_count = 0
        self._accumulated_po_seconds = 0.0
        self._headless_config: HeadlessConfiguration | None = None

    def set_headless_configuration(self, headless_config: HeadlessConfiguration) -> None:
        """Set the headless configuration for this MainApp instance."""
        self._headless_config = headless_config
        self.processing_service.set_headless_configuration(headless_config)
        self.telemetry.emit_status(StatusLevel.INFO, f"Headless configuration set: {headless_config}")
    
    # ---- UI helpers ---------------------------------------------------------------------



    # (Deprecated) _rename_folder_with_status removed in favor of folder_hierarchy.finalize_folder

    def initialize_browser_once(self):
        """Initialize browser once and keep it open for all POs (deprecated: use browser_orchestrator)."""
        if not self.browser_orchestrator.is_initialized():
            self.browser_orchestrator.initialize_browser(headless=self._headless_config.get_effective_headless_mode())


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

    def process_single_po(self, po_data, hierarchy_cols, has_hierarchy_data, index, total, execution_mode=None):
        """Process a single PO using the processing service."""
        from .lib.models import ExecutionMode
        execution_mode = execution_mode or ExecutionMode.STANDARD
        
        # Ensure the service has the current driver/lock context from MainApp if needed
        # (Though MainApp will eventually be refactored further)
        self.processing_service.driver = self.driver
        self.processing_service.lock = self.lock
        
        try:
            return self.processing_service.process_single_po(
                po_data=po_data,
                hierarchy_cols=hierarchy_cols,
                has_hierarchy_data=has_hierarchy_data,
                index=index,
                total=total,
                execution_mode=execution_mode
            )
        finally:
            pass # _register_po_completion removed


    def run(self) -> None:
        """
        Main execution loop for processing POs.
        """
        # Interactive or non-interactive configuration
        # Re-evaluate ENABLE_INTERACTIVE_UI at runtime to allow dynamic control
        # Default is True for local interactive use
        enable_interactive = os.environ.get('ENABLE_INTERACTIVE_UI', 'True').strip().lower() == 'true'

        if enable_interactive:
            setup_session = self.setup_manager.interactive_setup()
            headless_config = HeadlessConfiguration(enabled=setup_session.headless_preference)
            self.ui_mode = setup_session.ui_mode
            self.execution_mode = setup_session.execution_mode
        else:
            self.telemetry.emit_status(StatusLevel.INFO, "Applying environment configuration")
            config = self.setup_manager.apply_env_overrides()
            headless_config = HeadlessConfiguration(enabled=config["headless_preference"])
            # Default to "premium" (Textual UI) for better visibility, use "none" for CI/automation
            if not hasattr(self, 'ui_mode') or self.ui_mode is None:
                self.ui_mode = config.get("ui_mode", "premium")  # Changed from "none" to "premium"
            if not hasattr(self, 'execution_mode') or self.execution_mode is None:
                self.execution_mode = config.get("execution_mode", "standard")
        
        self.set_headless_configuration(headless_config)

        os.makedirs(ExperimentalConfig.INPUT_DIR, exist_ok=True)
        os.makedirs(ExperimentalConfig.DOWNLOAD_FOLDER, exist_ok=True)

        try:
            excel_path = self.excel_processor.get_excel_file_path()
            # Inform which input file will be processed (CSV or Excel)
            _, ext = os.path.splitext(excel_path.lower())
            file_kind = "CSV" if ext == ".csv" else "Excel"
            self.telemetry.emit_status(StatusLevel.INFO, f"Processing input file: {excel_path} ({file_kind})")
            po_entries, original_cols, hierarchy_cols, has_hierarchy_data = self.excel_processor.read_po_numbers_from_excel(excel_path)
            valid_entries = self.excel_processor.process_po_numbers(po_entries)
        except Exception as e:
            self.telemetry.emit_status(StatusLevel.ERROR, f"Failed to read or process input file: {e}")
            return

        if not valid_entries:
            logger.warning("No valid PO entries found to process")
            return

        logger.info(
            "CSV reading completed",
            extra={
                "total_entries": len(po_entries),
                "valid_pos": len(valid_entries),
                "sample_po_numbers": [entry[0] for entry in valid_entries[:10]],
                "has_more": len(valid_entries) > 10,
            }
        )

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
                    logger.warning("Failed to seed SQLite database", extra={"error": str(e)})

        # Convert to list of PO data
        po_data_list = []
        for display_po, po_number in valid_entries:
            for entry in po_entries:
                if entry['po_number'] == display_po:
                    po_data_list.append(entry)
                    break

        self.telemetry.emit_status(StatusLevel.SUCCESS, f"PO Data Conversion complete. {len(po_data_list)} POs ready.")
        self.telemetry.emit_status(StatusLevel.INFO, f"Starting processing with {len(po_data_list)} POs...")
        use_process_pool = bool(getattr(ExperimentalConfig, 'USE_PROCESS_POOL', False))  # Derived from worker count

        requested_workers = getattr(ExperimentalConfig, 'PROC_WORKERS', self.max_workers)
        try:
            configured_workers_raw = int(requested_workers)
        except (TypeError, ValueError):
            configured_workers_raw = self.max_workers

        # Resource-Aware Scaling Assessment
        if getattr(ExperimentalConfig, 'RESOURCE_AWARE_SCALING', True):
            logger.info("Performing resource-aware risk assessment", extra={"target_workers": configured_workers_raw})
            min_free_ram = float(getattr(ExperimentalConfig, 'MIN_FREE_RAM_GB', 0.3))
            configured_workers, report = ResourceAssessor.calculate_safe_worker_count(configured_workers_raw, min_free_ram_gb=min_free_ram)
            logger.info(ResourceAssessor.get_risk_message(report))

            if report["is_throttled"]:
                logger.warning(
                    "Worker count adjusted due to resource constraints",
                    extra={"original": configured_workers_raw, "adjusted": configured_workers}
                )

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
            logger.info(
                "Resource-aware scaling disabled, using configured cap",
                extra={"workers": configured_workers}
            )

        self.max_workers = configured_workers
        self.worker_manager.max_workers = self.max_workers

        if use_process_pool and not self.enable_parallel:
            self.enable_parallel = True

        # Set initial global stats
        self._run_start_time = time.perf_counter()
        self.processing_controller.set_run_start_time(self._run_start_time)

        # Prepare processing stats
        processed_count = 0

        if self.ui_mode == "none":
            # Silent mode - no UI
            logger.info("Starting silent processing", extra={"po_count": len(po_data_list)})
            
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
                    None, # _prepare_progress_tracking removed
                    self.process_single_po,
                    communication_manager=self.communication_manager,
                    sqlite_db_path=self.csv_manager.sqlite_db_path,
                    execution_mode=getattr(self, 'execution_mode', 'standard'),
                )
            finally:
                if use_process_pool and self.enable_parallel:
                    self.worker_manager.shutdown()
        else:
            # Default to Premium UI (Textual)
            self._run_premium_ui(
                po_data_list,
                hierarchy_cols,
                has_hierarchy_data,
                use_process_pool
            )
            # Final stats after UI closes
            agg = self.communication_manager.get_aggregated_metrics()
            successful = agg.get("total_successful", 0)
            failed = agg.get("total_failed", 0)

        # Shutdown CSV handler to ensure all data is persisted
        self.csv_manager.shutdown_csv_handler()

        self.telemetry.emit_stats(successful, failed, successful + failed)
        self.telemetry.emit_status(StatusLevel.SUCCESS, f"Processing complete! {successful} successful, {failed} failed.")

    def _run_premium_ui(self, po_data_list, hierarchy_cols, has_hierarchy_data, use_process_pool):
        """Run the alternative Premium Textual UI."""
        from .ui.textual_ui_app import CoupaTextualUI
        import threading
        import os
        from .core.output import OutputSuppressor

        # Start processing in a background thread
        def run_processing():
            try:
                self.processing_controller.process_po_entries(
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
                    None,  # _prepare_progress_tracking removed
                    self.process_single_po,
                    communication_manager=self.communication_manager,
                    sqlite_db_path=self.csv_manager.sqlite_db_path,
                    execution_mode=getattr(self, 'execution_mode', 'standard'),
                )
            except Exception as e:
                print(f"Error in background processing: {e}")
                import traceback
                traceback.print_exc()

        os.environ["SUPPRESS_WORKER_OUTPUT"] = "1"
        with OutputSuppressor(enabled=True):
            proc_thread = threading.Thread(target=run_processing, daemon=True)
            proc_thread.start()

            # Run the Textual App
            app = CoupaTextualUI(self.communication_manager, total_pos=len(po_data_list))
            app.run()

    def close(self, emergency: bool = False):
        """Close the browser properly and stop all active components."""
        if emergency:
            logger.warning("Accelerated shutdown initiated")

        # 1. Shutdown active sessions

        # 2. Stop worker manager sessions
        if hasattr(self, 'worker_manager'):
            try:
                if hasattr(self.worker_manager, 'active_session') and self.worker_manager.active_session:
                    logger.info("Stopping active processing session", extra={"emergency": emergency})
                    self.worker_manager.active_session.stop_processing(emergency=emergency)
            except Exception as e:
                logger.warning("Error stopping worker session", extra={"error": str(e)})

        # 3. Shutdown CSV handler and finalize results
        if hasattr(self, 'result_aggregator'):
            try:
                self.result_aggregator.finalize()
            except Exception as e:
                logger.warning("Error finalizing results", extra={"error": str(e)})

        # 4. Cleanup browser via orchestrator
        if hasattr(self, 'browser_orchestrator'):
            try:
                self.browser_orchestrator.cleanup(emergency=emergency)
            except Exception as e:
                logger.warning("Error closing browser orchestrator", extra={"error": str(e)})
        
        # Legacy cleanup (for backward compatibility)
        if self.driver:
            try:
                self.browser_manager.cleanup()
            except Exception:
                pass
            self.driver = None


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
            logger.critical("Second interrupt received, force quitting")
            os._exit(1)

        logger.warning("Interrupt received, initiating graceful shutdown")
        shutdown_initiated = True

        # Trigger the app shutdown
        try:
            app.close(emergency=True)
        except Exception as e:
            logger.error("Error during app shutdown", extra={"error": str(e)})

        logger.info("Shutdown sequence completed")
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
        logger.error("Application error", extra={"error": str(e)}, exc_info=True)
    finally:
        # Standard cleanup if finished normally
        if not shutdown_initiated:
            app.close()



def _debug_log(msg: str):
    try:
        with open('/tmp/worker_debug.log', 'a') as f:
            ts = datetime.now().isoformat()
            f.write(f"[{ts}] [MAIN] {msg}\n")
    except:
        pass

if __name__ == "__main__":
    _debug_log("MainApp starting...")

    main()
