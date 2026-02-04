"""
Módulo ProcessingController.

Coordena o processamento de entradas de PO, integrando WorkerManager, UIController e CSVHandler
para execução paralela e feedback em tempo real.
"""

from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import time
import threading
import multiprocessing as mp

from .worker_manager import WorkerManager
from .ui_controller import UIController
from .core.csv_handler import CSVHandler, WriteQueue
from .lib.models import HeadlessConfiguration


class ProcessingController:
    """Controller for PO processing logic, extracted from MainApp."""

    def __init__(self, worker_manager: WorkerManager, ui_controller: UIController):
        self.worker_manager = worker_manager
        self.ui_controller = ui_controller
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
        """Progress callback for ProcessingSession parallel processing."""
        try:
            total = progress.get('total_tasks', 0)
            completed = progress.get('completed_tasks', 0)
            failed = progress.get('failed_tasks', 0)
            active = progress.get('active_tasks', 0)

            # Update global stats
            self.ui_controller.global_stats["total"] = total
            self.ui_controller.global_stats["completed"] = completed
            self.ui_controller.global_stats["failed"] = failed
            self.ui_controller.global_stats["active"] = active

            # Calculate elapsed time
            if self._run_start_time:
                elapsed_seconds = time.perf_counter() - self._run_start_time
                minutes, seconds = divmod(int(elapsed_seconds), 60)
                self.ui_controller.global_stats["elapsed"] = f"{minutes}m {seconds}s"

                # Estimate ETA global
                if completed > 0:
                    avg_time_per_po = elapsed_seconds / completed
                    remaining_pos = total - completed - failed
                    eta_seconds = avg_time_per_po * remaining_pos
                    eta_minutes, eta_seconds = divmod(int(eta_seconds), 60)
                    self.ui_controller.global_stats["eta_global"] = f"{eta_minutes}m {eta_seconds}s"
                else:
                    self.ui_controller.global_stats["eta_global"] = "⏳"

                # Calculate global efficiency
                if elapsed_seconds > 0:
                    global_efficiency = (completed / elapsed_seconds) * 60  # POs per minute
                    self.ui_controller.global_stats["global_efficiency"] = f"{global_efficiency:.1f} POs/min"
                else:
                    self.ui_controller.global_stats["global_efficiency"] = "⏳"

            # Update worker states with individual efficiency estimates
            completed_per_worker = completed // self.worker_manager.max_workers
            failed_per_worker = failed // self.worker_manager.max_workers
            active_per_worker = active // self.worker_manager.max_workers
            total_per_worker = total // self.worker_manager.max_workers
            self.ui_controller.worker_states = []
            for i in range(self.worker_manager.max_workers):
                worker_id = f"Worker {i+1}"
                progress_str = f"{completed_per_worker}/{total_per_worker} POs"
                elapsed_worker = self.ui_controller.global_stats["elapsed"]
                eta_worker = self.ui_controller.global_stats["eta_global"]

                # Estimate individual worker efficiency based on distributed workload
                # Assuming even distribution of completed tasks among workers
                worker_completed_estimate = completed_per_worker
                if elapsed_seconds > 0 and worker_completed_estimate > 0:
                    worker_efficiency = (worker_completed_estimate / elapsed_seconds) * 60
                    efficiency = f"{worker_efficiency:.1f} POs/min"
                else:
                    efficiency = "⏳"

                self.ui_controller.worker_states.append({
                    "worker_id": worker_id,
                    "progress": progress_str,
                    "elapsed": elapsed_worker,
                    "eta": eta_worker,
                    "efficiency": efficiency
                })

            # Update live with Group
            self.ui_controller.update_display()

        except Exception as e:
            print(f"Error in progress callback: {e}")

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
    ) -> Tuple[int, int]:
        """
        Process PO entries with automatic parallel mode selection.
        
        Enhanced to support ProcessingSession for intelligent parallel processing.
        Falls back to original implementation for backward compatibility.
        """
        # Check if parallel processing is enabled and beneficial
        if enable_parallel and len(po_data_list) > 1 and use_process_pool:
            if communication_manager:
                manager = mp.Manager()
                try:
                    po_queue = manager.Queue()
                    for po_data in po_data_list:
                        po_queue.put(po_data)

                    successful, failed, _session_report = self.worker_manager.process_parallel_with_reusable_workers(
                        po_queue=po_queue,
                        hierarchy_cols=hierarchy_cols,
                        has_hierarchy_data=has_hierarchy_data,
                        headless_config=headless_config,
                        communication_manager=communication_manager,
                        queue_size=len(po_data_list),
                        csv_handler=csv_handler,
                        folder_hierarchy=folder_hierarchy,
                    )
                    return successful, failed
                finally:
                    try:
                        manager.shutdown()
                    except Exception:
                        pass
            try:
                # Use WorkerManager for ProcessingSession approach
                successful, failed, session_report = self.worker_manager.process_parallel_with_session(
                    po_data_list, hierarchy_cols, has_hierarchy_data, headless_config,
                    csv_handler=csv_handler, folder_hierarchy=folder_hierarchy
                )
                
                # self._last_parallel_report = session_report  # TODO: handle this
                return successful, failed
                
            except Exception as e:
                print(f"⚠️  ProcessingSession failed, falling back to legacy processing: {e}")
                # Fall through to legacy implementation

        # Legacy implementation (backward compatibility)
        if use_process_pool:
            # Use WorkerManager for legacy ProcessPoolExecutor approach
            successful, failed = self.worker_manager.process_parallel_legacy(
                po_data_list, hierarchy_cols, has_hierarchy_data, headless_config,
                csv_handler=csv_handler, folder_hierarchy=folder_hierarchy
            )
            return successful, failed
        else:
            print("📊 Using in-process mode (single WebDriver, sequential)")
            initialize_browser_once()
            prepare_progress_tracking(len(po_data_list))
            successful = 0
            failed = 0
            for i, po_data in enumerate(po_data_list):
                ok = process_single_po(po_data, hierarchy_cols, has_hierarchy_data, i, len(po_data_list))
                if ok:
                    successful += 1
                    self.ui_controller.global_stats["completed"] += 1
                else:
                    failed += 1
                    self.ui_controller.global_stats["failed"] += 1
                # Update active count (decrement as we complete)
                self.ui_controller.global_stats["active"] = max(0, len(po_data_list) - (successful + failed))
                
                # Calculate elapsed time and ETA
                if self._run_start_time:
                    elapsed_seconds = time.perf_counter() - self._run_start_time
                    minutes, seconds = divmod(int(elapsed_seconds), 60)
                    self.ui_controller.global_stats["elapsed"] = f"{minutes}m {seconds}s"
                    
                    # Estimate ETA global
                    if successful > 0:
                        avg_time_per_po = elapsed_seconds / successful
                        remaining_pos = len(po_data_list) - successful - failed
                        eta_seconds = avg_time_per_po * remaining_pos
                        eta_minutes, eta_seconds = divmod(int(eta_seconds), 60)
                        self.ui_controller.global_stats["eta_global"] = f"{eta_minutes}m {eta_seconds}s"
                    else:
                        self.ui_controller.global_stats["eta_global"] = "⏳"
                    
                    # Calculate global efficiency
                    if elapsed_seconds > 0:
                        global_efficiency = (successful / elapsed_seconds) * 60  # POs per minute
                        self.ui_controller.global_stats["global_efficiency"] = f"{global_efficiency:.1f} POs/min"
                    else:
                        self.ui_controller.global_stats["global_efficiency"] = "⏳"
                
                # Update worker progress for single worker
                self.ui_controller.worker_states[0]["progress"] = f"{successful + failed}/{len(po_data_list)} POs"
                self.ui_controller.worker_states[0]["elapsed"] = self.ui_controller.global_stats["elapsed"]
                self.ui_controller.worker_states[0]["eta"] = self.ui_controller.global_stats["eta_global"]
                efficiency = f"{(successful / max(1, elapsed_seconds)) * 60:.1f} POs/min" if elapsed_seconds > 0 else "⏳"
                self.ui_controller.worker_states[0]["efficiency"] = efficiency
                
                # Update live display
                self.ui_controller.update_display()

        return successful, failed

    def set_run_start_time(self, start_time: float):
        """Set the run start time for progress calculations."""
        self._run_start_time = start_time
