"""
Core protocols for CoupaDownloads.

Defines formal interfaces (Protocols) for various system components,
allowing for Dependency Inversion and easier testing/substitution.
"""

from typing import Protocol, Any, Dict, List, Optional, Callable, runtime_checkable
from .status import StatusLevel

@runtime_checkable
class BrowserProvider(Protocol):
    """Interface for browser session management."""
    def initialize_driver(self, headless: bool = False) -> Any: ...
    def cleanup(self) -> None: ...
    def update_download_directory(self, new_dir: str) -> None: ...
    def is_browser_responsive(self) -> bool: ...

@runtime_checkable
class Downloader(Protocol):
    """Interface for PO attachment downloading."""
    def download_attachments_for_po(
        self, 
        po_number: str, 
        on_attachments_found: Optional[Callable[[Dict[str, Any]], str]] = None
    ) -> Dict[str, Any]: ...

@runtime_checkable
class TelemetryEmitter(Protocol):
    """Interface for emitting telemetry events."""
    def emit_status(self, level: StatusLevel, message: str, progress: Optional[int] = None) -> None: ...
    def emit_progress(self, current: int, total: int, message: str = "") -> None: ...

@runtime_checkable
class StorageManager(Protocol):
    """Interface for persisting results (e.g., CSV)."""
    def is_initialized(self) -> bool: ...
    def update_record(self, po_number: str, updates: Dict[str, Any]) -> bool: ...

@runtime_checkable
class FolderManager(Protocol):
    """Interface for hierarchical folder creation and management."""
    def create_folder_path(
        self, 
        po_data: Dict[str, Any], 
        hierarchy_cols: List[str], 
        has_hierarchy: bool,
        supplier_name: Optional[str] = None,
        create_dir: bool = True
    ) -> str: ...
    
    def finalize_folder(self, folder_path: str, status_code: str) -> str: ...
    def format_attachment_names(self, names: List[str]) -> str: ...

@runtime_checkable
class Messenger(Protocol):
    """Interface for inter-process communication."""
    def send_metric(self, metric_dict: Dict[str, Any]) -> None: ...
