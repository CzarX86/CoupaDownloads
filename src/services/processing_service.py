"""
Processing service for PO operations.

Handles the logic for processing individual POs and coordinating
different execution modes (Selenium, Playwright, Direct HTTP).
"""

import os
import time
import threading
from typing import Dict, Any, List, Optional
from pathlib import Path

from ..lib.browser import BrowserManager
from ..lib.folder_hierarchy import FolderHierarchyManager
from ..lib.models import ExecutionMode, HeadlessConfiguration
from ..lib.config import Config
from ..core.telemetry import TelemetryProvider
from ..core.status import StatusLevel
from ..csv_manager import CSVManager
from ..ui_controller import UIController

# Utility functions from core.utils
from ..core.utils import (
    _wait_for_downloads_complete,
    _derive_status_label,
    _legacy_rename_folder_with_status,
    _humanize_exception,
    _compose_csv_message
)

from ..core.protocols import (
    BrowserProvider,
    FolderManager,
    StorageManager,
    TelemetryEmitter
)

class ProcessingService:
    """
    Service that encapsulates the logic for processing POs.
    """
    
    def __init__(
        self,
        browser_manager: BrowserProvider,
        folder_hierarchy: FolderManager,
        storage_manager: StorageManager,
        telemetry: TelemetryEmitter,
        ui_controller: Optional[UIController] = None
    ):
        self.browser_manager = browser_manager
        self.folder_hierarchy = folder_hierarchy
        self.storage_manager = storage_manager
        self.telemetry = telemetry
        self.ui_controller = ui_controller
        self.lock = threading.Lock()
        self.driver = None
        self._headless_config: Optional[HeadlessConfiguration] = None

    def set_headless_configuration(self, config: HeadlessConfiguration):
        self._headless_config = config

    def _get_headless_setting(self) -> bool:
        if self._headless_config:
            return self._headless_config.get_effective_headless_mode()
        return True

    def process_single_po(
        self,
        po_data: Dict[str, Any],
        hierarchy_cols: List[str],
        has_hierarchy_data: bool,
        index: int,
        total: int,
        execution_mode: ExecutionMode = ExecutionMode.STANDARD
    ) -> bool:
        """Process a single PO and return success status."""
        from ..lib.downloader import Downloader
        from selenium.common.exceptions import InvalidSessionIdException, NoSuchWindowException
        
        mode_str = getattr(execution_mode, 'value', str(execution_mode))
        display_po = po_data['po_number']
        po_number = po_data['po_number']
        
        current_po_start_time = time.perf_counter()
        
        progress = int((index / total) * 100)
        self.telemetry.emit_progress(index, total, f"Processing PO {index}/{total}: {display_po}")
        self.telemetry.emit_status(StatusLevel.INFO, f"Current PO: {display_po} [Mode: {mode_str.upper()}]", progress=progress)

        try:
            # Create hierarchical folder structure
            folder_path = self.folder_hierarchy.create_folder_path(
                po_data, hierarchy_cols, has_hierarchy_data
            )

            # Define internal update helper for UI consistency
            def _update_seq_worker(status: str, attachments_found: int = 0, attachments_downloaded: int = 0) -> None:
                if not self.ui_controller:
                    return
                    
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
                worker_state["duration"] = max(0.0, time.perf_counter() - current_po_start_time)
                self.ui_controller.update_display()

            def _emit_progress(payload: Dict[str, Any]) -> None:
                _update_seq_worker(
                    status=payload.get("status", "PROCESSING"),
                    attachments_found=payload.get("attachments_found", 0),
                    attachments_downloaded=payload.get("attachments_downloaded", 0),
                )

            _update_seq_worker("STARTED")

            result_payload = None

            if mode_str in ("filtered", "no_js"):
                from ..lib.playwright_manager import PlaywrightManager
                from ..lib.playwright_downloader import PlaywrightDownloader
                
                pw_manager = PlaywrightManager()
                try:
                    page = pw_manager.start(
                        headless=self._get_headless_setting(), 
                        execution_mode=execution_mode,
                        profile_dir=Config.EDGE_PROFILE_DIR
                    )
                    def _on_findings(findings): return folder_path
                    pw_downloader = PlaywrightDownloader(page, progress_callback=_emit_progress)
                    result_payload = pw_downloader.download_attachments_for_po(po_number, on_attachments_found=_on_findings)
                finally:
                    pw_manager.cleanup()
            
            elif mode_str == "direct_http":
                from ..lib.direct_http_downloader import DirectHTTPDownloader
                
                with self.lock:
                    if not self.driver or not self.browser_manager.is_browser_responsive():
                        self.browser_manager.cleanup()
                        self.browser_manager.initialize_driver(headless=self._get_headless_setting())
                        self.driver = self.browser_manager.driver
                    
                    cookies = {c['name']: c['value'] for c in self.driver.get_cookies()}
                
                def _on_findings(findings): return folder_path
                http_downloader = DirectHTTPDownloader(cookies, progress_callback=_emit_progress)
                result_payload = http_downloader.download_attachments_for_po(po_number, on_attachments_found=_on_findings)
                http_downloader.close()
            
            else:
                # Standard Selenium
                with self.lock:
                    if not self.driver or not self.browser_manager.is_browser_responsive():
                        self.browser_manager.cleanup()
                        self.browser_manager.initialize_driver(headless=self._get_headless_setting())
                        self.driver = self.browser_manager.driver

                    self.browser_manager.update_download_directory(folder_path)
                    downloader = Downloader(self.driver, self.browser_manager, progress_callback=_emit_progress)
                    try:
                        result_payload = downloader.download_attachments_for_po(po_number)
                    except (InvalidSessionIdException, NoSuchWindowException) as e:
                        # Simple recovery
                        self.browser_manager.cleanup()
                        self.browser_manager.initialize_driver(headless=self._get_headless_setting())
                        self.driver = self.browser_manager.driver
                        downloader = Downloader(self.driver, self.browser_manager, progress_callback=_emit_progress)
                        result_payload = downloader.download_attachments_for_po(po_number)

            # finalize
            _wait_for_downloads_complete(folder_path, expected_count=result_payload.get('attachments_downloaded'))
            status_code = _derive_status_label(result_payload)
            final_folder = self.folder_hierarchy.finalize_folder(folder_path, status_code)
            
            csv_message = _compose_csv_message(result_payload)
            if self.storage_manager.is_initialized():
                formatted_names = self.folder_hierarchy.format_attachment_names(result_payload.get('attachment_names', []))
                self.storage_manager.update_record(display_po, {
                    'STATUS': status_code,
                    'SUPPLIER': result_payload.get('supplier_name', ''),
                    'ATTACHMENTS_FOUND': result_payload.get('attachments_found', 0),
                    'ATTACHMENTS_DOWNLOADED': result_payload.get('attachments_downloaded', 0),
                    'AttachmentName': formatted_names,
                    'ERROR_MESSAGE': csv_message,
                    'DOWNLOAD_FOLDER': final_folder,
                    'COUPA_URL': result_payload.get('coupa_url', ''),
                })

            _update_seq_worker(
                status=status_code,
                attachments_found=result_payload.get('attachments_found', 0),
                attachments_downloaded=result_payload.get('attachments_downloaded', 0),
            )
            
            # Log result via telemetry
            emoji = {
                'COMPLETED': '✅',
                'NO_ATTACHMENTS': '📭',
                'PARTIAL': '⚠️',
                'FAILED': '❌',
                'PO_NOT_FOUND': '🚫',
            }.get(status_code, 'ℹ️')
            self.telemetry.emit_status(StatusLevel.SUCCESS if status_code in ('COMPLETED', 'NO_ATTACHMENTS') else StatusLevel.WARNING,
                                    f"{emoji} {display_po}: {status_code}")
                                    
            return status_code in {'COMPLETED', 'NO_ATTACHMENTS'}

        except Exception as e:
            friendly = _humanize_exception(e)
            self.telemetry.emit_status(StatusLevel.ERROR, f"Error processing {display_po}: {friendly}")
            if self.storage_manager.is_initialized():
                self.storage_manager.update_record(display_po, {'STATUS': 'FAILED', 'ERROR_MESSAGE': friendly})
            return False
