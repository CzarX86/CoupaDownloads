"""
Módulo ProcessingController.

Coordena o processamento de entradas de PO, integrando WorkerManager e CSVHandler
para execução paralela e feedback em tempo real.
"""

from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import time
import threading
import multiprocessing as mp

from .worker_manager import WorkerManager
from .core.csv_handler import CSVHandler, WriteQueue
from .lib.models import HeadlessConfiguration
from .core.output import maybe_print as print


class ProcessingController:
    """Controller for PO processing logic, extracted from MainApp."""

    def __init__(self, worker_manager: WorkerManager):
        self.worker_manager = worker_manager
        self.csv_handler: Optional[CSVHandler] = None
        self._csv_write_queue: Optional[WriteQueue] = None
        self._csv_session_id: Optional[str] = None
        self._run_start_time: Optional[float] = None

    def set_csv_handler(self, csv_handler: CSVHandler, write_queue: WriteQueue, session_id: str):
        """Set CSV handler for incremental updates."""
        self.csv_handler = csv_handler
        self._csv_write_queue = write_queue
        self._csv_session_id = session_id

    def _shutdown_csv_handler(self):
        """Shutdown CSV handler to ensure all data is persisted."""
        if self.csv_handler:
            self.csv_handler.shutdown()
            self.csv_handler = None
            self._csv_write_queue = None

    def _parallel_progress_callback(self, progress: Dict[str, Any]) -> None:
        """Progress callback (minimal version)."""
        pass

    def process_po_entries(
        self,
        po_data_list: List[Dict[str, Any]],
        hierarchy_cols: List[str],
        has_hierarchy_data: bool,
        use_process_pool: bool,
        headless_config: HeadlessConfiguration,
        enable_parallel: bool,
        max_workers: int,
        csv_handler: Optional[CSVHandler],
        folder_hierarchy: Any,
        initialize_browser_once: callable,
        prepare_progress_tracking: callable,
        process_single_po: callable,
        communication_manager: Optional[Any] = None,
        sqlite_db_path: Optional[str] = None,
        execution_mode: Any = None,
    ) -> Tuple[int, int]:
        """
        Process PO entries with automatic parallel mode selection.
        
        Enhanced to support ProcessingSession for intelligent parallel processing.
        Falls back to original implementation for backward compatibility.
        """
        from .lib.models import ExecutionMode
        execution_mode = execution_mode or ExecutionMode.STANDARD
        mode_val = execution_mode.value if hasattr(execution_mode, 'value') else str(execution_mode)
        print(f"🚀 Execution Mode: {mode_val.upper()}")


        # Use unified processing engine for all parallel cases
        if enable_parallel and len(po_data_list) > 1 and use_process_pool:
            print(f"🚀 Using Unified Processing Engine with {self.worker_manager.max_workers} workers")
            try:
                successful, failed, session_report = self.worker_manager.process_pos(
                    po_data_list=po_data_list,
                    hierarchy_cols=hierarchy_cols,
                    has_hierarchy_data=has_hierarchy_data,
                    headless_config=headless_config,
                    storage_manager=csv_handler,
                    folder_manager=folder_hierarchy,
                    messenger=communication_manager,
                    sqlite_db_path=sqlite_db_path,
                    execution_mode=execution_mode,
                )
                return successful, failed
            except Exception as e:
                print(f"⚠️ Unified engine failed: {e}")
                raise
        
        # Sequential processing (single worker, in-process)
        if not use_process_pool or not enable_parallel:

            mode_display = getattr(execution_mode, 'value', str(execution_mode)).upper()
            print(f"📊 Using in-process mode (single WebDriver, sequential) - Mode: {mode_display}")
            initialize_browser_once()
            if prepare_progress_tracking:
                prepare_progress_tracking(len(po_data_list))
            successful = 0
            failed = 0
            for i, po_data in enumerate(po_data_list):
                if communication_manager:
                    try:
                        po_number = po_data.get('po_number', '')
                        communication_manager.send_metric({
                            'worker_id': 0,
                            'po_id': po_number,
                            'status': 'STARTED',
                            'timestamp': time.time(),
                            'attachments_found': 0,
                            'attachments_downloaded': 0,
                            'message': f"Started {po_number}" if po_number else "Started PO",
                        })
                    except Exception:
                        pass
                ok = process_single_po(po_data, hierarchy_cols, has_hierarchy_data, i, len(po_data_list), execution_mode=execution_mode)
                if ok:
                    successful += 1
                else:
                    failed += 1
                if communication_manager:
                    try:
                        po_number = po_data.get('po_number', '')
                        communication_manager.send_metric({
                            'worker_id': 0,
                            'po_id': po_number,
                            'status': 'COMPLETED' if ok else 'FAILED',
                            'timestamp': time.time(),
                            'attachments_found': 0,
                            'attachments_downloaded': 0,
                            'message': f"{'Completed' if ok else 'Failed'} {po_number}" if po_number else ('Completed PO' if ok else 'Failed PO'),
                        })
                    except Exception:
                        pass
                
                # Sequential logging
                print(f"📊 Progress: {successful + failed}/{len(po_data_list)} (Success: {successful}, Failed: {failed})")

        return successful, failed

    def set_run_start_time(self, start_time: float):
        """Set the run start time for progress calculations."""
        self._run_start_time = start_time
