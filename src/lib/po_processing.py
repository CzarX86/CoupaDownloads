"""
Shared PO processing utilities for EXPERIMENTAL pipeline.

Provides a single function `process_single_po` that encapsulates the common
steps to process one PO using an existing WebDriver session and BrowserManager:

- Create/download folder path (hierarchy-aware with fallback)
- Point browser downloads to the folder
- Invoke Downloader to collect attachments/metadata
- Wait for active downloads to settle
- Derive status and rename the folder accordingly
- Return a normalized result dictionary
"""

from __future__ import annotations

import os
import time
from typing import Any, Callable, Dict, Optional, Sequence

from .downloader import Downloader
from .folder_hierarchy import FolderHierarchyManager
from ..core.utils import (
    _has_active_downloads,
    _wait_for_downloads_complete,
    _derive_status_label,
    _humanize_exception,
    _parse_counts_from_message,
    _suffix_for_status,
)


# Helper functions moved to core/utils.py


def process_single_po(
    po_number: str,
    po_data: Dict[str, Any],
    driver: Any,
    browser_manager: Any,
    hierarchy_columns: Optional[Sequence[str]] = None,
    has_hierarchy_data: bool = False,
    base_download_dir: Optional[str] = None,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    skip_finalization: bool = False,
) -> Dict[str, Any]:
    """
    Process a single PO using the provided WebDriver/browser manager.

    Returns a normalized result dict containing status, folders, and payload data.
    """
    display_po = po_data.get("po_number", po_number)
    folder_manager = FolderHierarchyManager()
    
    # State to track the folder created via callback
    context = {
        "folder_path": None,
        "is_work_folder": False
    }

    def on_attachments_found(data: Dict[str, Any]) -> str:
        """Just-In-Time callback to create the folder only when needed.

        May be called more than once for the same PO (e.g. first with
        NO_ATTACHMENTS on the PO page, then with PROCESSING after a PR
        fallback discovers files).  When upgrading to PROCESSING the
        previously-created empty status folder is removed.
        """
        status_code = data.get('status_code', 'PROCESSING')
        previous_path = context.get("folder_path")

        # Build base folder path WITHOUT creating it yet — we choose which
        # concrete directory to create below, depending on status_code.
        try:
            supplier_name = data.get('supplier_name')
            path = folder_manager.create_folder_path(
                po_data, list(hierarchy_columns or []), bool(has_hierarchy_data),
                supplier_name=supplier_name,
                create_dir=False,
            )
        except Exception:
            try:
                from ..config.app_config import Config
                base_dir = base_download_dir or str(Config.DOWNLOAD_FOLDER)
            except Exception:
                base_dir = base_download_dir or os.path.expanduser("~/Downloads/CoupaDownloads")
            os.makedirs(base_dir, exist_ok=True)
            path = os.path.join(base_dir, po_number or "PO")

        path = os.path.expanduser(path)

        # Determine suffix and whether this is a temporary work folder
        if status_code == 'PROCESSING':
            # Ensure path ends in exactly one __WORK suffix then create it.
            if not path.endswith("__WORK"):
                path += "__WORK"
            os.makedirs(path, exist_ok=True)
            context["is_work_folder"] = True

            # If an earlier call created a non-work status folder (e.g.
            # _NO_ATTACHMENTS) that is now superseded, remove it to avoid
            # leaving orphaned empty directories.
            if previous_path and previous_path != path and os.path.isdir(previous_path):
                try:
                    if not os.listdir(previous_path):
                        os.rmdir(previous_path)
                except OSError:
                    pass
        else:
            # Strip the __WORK suffix that create_folder_path adds so we don't
            # produce names like "PO123__WORK_PO_NOT_FOUND".
            if path.endswith("__WORK"):
                path = path[: -len("__WORK")]
            suffix = _suffix_for_status(status_code)
            if not path.endswith(suffix):
                path += suffix
            os.makedirs(path, exist_ok=True)
            context["is_work_folder"] = False

        context["folder_path"] = path
        return path

    # Run downloader with JIT callback
    downloader = Downloader(driver, browser_manager, progress_callback=progress_callback)
    result_payload = downloader.download_attachments_for_po(
        po_number, 
        on_attachments_found=on_attachments_found
    )
    
    folder_path = context["folder_path"]
    status_code = _derive_status_label(result_payload)

    # If no folder was created by callback (unlikely but safe), we create one now
    if not folder_path:
        folder_path = on_attachments_found({'status_code': status_code})

    # Finalize folder logic
    final_folder = folder_path
    if context["is_work_folder"]:
        # Wait for downloads to settle
        _wait_for_downloads_complete(folder_path, expected_count=result_payload.get("attachments_downloaded"))
        
        if not skip_finalization:
            # Use the robust finalize_folder from FolderHierarchyManager
            final_folder = folder_manager.finalize_folder(folder_path, status_code)
        else:
            # When skipping finalization for batching, we stay in the __WORK folder
            # The background process will handle the rename later
            final_folder = folder_path
    
    # Assemble normalized result
    result = {
        "po_number": po_number,
        "po_number_display": display_po,
        "status_code": status_code,
        "message": result_payload.get("message", ""),
        "final_folder": final_folder,
        "supplier_name": result_payload.get("supplier_name", ""),
        "attachments_found": result_payload.get("attachments_found", 0),
        "attachments_downloaded": result_payload.get("attachments_downloaded", 0),
        "coupa_url": result_payload.get("coupa_url") or result_payload.get("initial_url", ""),
        "attachment_names": result_payload.get("attachment_names", []),
        "status_reason": result_payload.get("status_reason", ""),
        "success": status_code in {"COMPLETED", "NO_ATTACHMENTS", "PARTIAL"},
        "files": result_payload.get("files", []),
        "data": result_payload,
        "download_folder": final_folder,
    }

    return result
