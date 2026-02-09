"""
Telemetry and event monitoring for CoupaDownloads.

Provides a robust observer pattern for status updates, progress reporting,
and processing statistics, replacing ad-hoc print-based monitoring.
"""

from typing import List, Callable, Optional, Any, Dict
from dataclasses import dataclass, field
import threading
import time

from .status import StatusMessage, StatusLevel

class TelemetryListener:
    """Protocol-like base for telemetry listeners."""
    def on_status(self, message: StatusMessage) -> None:
        pass

    def on_progress(self, current: int, total: int, message: str = "") -> None:
        pass

    def on_stats_update(self, successful: int, failed: int, total: int) -> None:
        pass


class TelemetryProvider:
    """
    Central coordinator for system events and status updates.
    
    Threads can post updates here WITHOUT causing recursion or blocking.
    """
    
    def __init__(self):
        self._listeners: List[TelemetryListener] = []
        self._lock = threading.Lock()
        
    def add_listener(self, listener: TelemetryListener) -> None:
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)
                
    def remove_listener(self, listener: TelemetryListener) -> None:
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)
                
    def emit_status(self, level: StatusLevel, message: str, progress: Optional[int] = None, operation_id: Optional[str] = None) -> None:
        """Emit a standardized status message to all listeners."""
        # Clean message to avoid recursion issues if something still prints
        clean_msg = str(message)[:450] 
        
        # Using factory methods to ensure datetime is set correctly
        if level == StatusLevel.INFO:
            msg = StatusMessage.info(clean_msg, operation_id, progress)
        elif level == StatusLevel.SUCCESS:
            msg = StatusMessage.success(clean_msg, operation_id, progress)
        elif level == StatusLevel.WARNING:
            msg = StatusMessage.warning(clean_msg, operation_id, progress)
        elif level == StatusLevel.ERROR:
            msg = StatusMessage.error(clean_msg, operation_id, progress)
        else:
            # Fallback
            from datetime import datetime
            msg = StatusMessage(datetime.now(), level, clean_msg, operation_id, progress)

        with self._lock:
            for listener in self._listeners:
                try:
                    listener.on_status(msg)
                except Exception:
                    pass # Listeners should not crash the provider

    def emit_progress(self, current: int, total: int, message: str = "") -> None:
        with self._lock:
            for listener in self._listeners:
                try:
                    listener.on_progress(current, total, message)
                except Exception:
                    pass

    def emit_stats(self, successful: int, failed: int, total: int) -> None:
        with self._lock:
            for listener in self._listeners:
                try:
                    listener.on_stats_update(successful, failed, total)
                except Exception:
                    pass

class FunctionalTelemetryListener(TelemetryListener):
    """Adapter to use simple functions as listeners."""
    def __init__(self, on_status_fn: Optional[Callable[[StatusMessage], None]] = None):
        self._on_status_fn = on_status_fn
        
    def on_status(self, message: StatusMessage) -> None:
        if self._on_status_fn:
            self._on_status_fn(message)


class ConsoleTelemetryListener(TelemetryListener):
    """Listener that prints status updates to the console."""
    def on_status(self, message: StatusMessage) -> None:
        emoji_map = {
            StatusLevel.INFO: "ℹ️",
            StatusLevel.WARNING: "⚠️",
            StatusLevel.ERROR: "❌",
            StatusLevel.SUCCESS: "✅"
        }
        emoji = emoji_map.get(message.level, "")
        prog_str = f" [{message.progress}%]" if message.progress is not None else ""
        print(f"{emoji} {message.message}{prog_str}", flush=True)

    def on_progress(self, current: int, total: int, message: str = "") -> None:
        # Avoid showing every single progress if it's too spammy
        # But for base implementation, let's keep it simple
        print(f"📊 Progress: {current}/{total} {message}", flush=True)
