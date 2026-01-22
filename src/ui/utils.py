# Tkinter UI utilities and common imports

"""
Common imports and utilities for the Tkinter UI components.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional, Callable, Any
import threading
import queue
import logging

# Configure logging for UI components
logger = logging.getLogger(__name__)

# Thread-safe queue for GUI updates
gui_queue = queue.Queue()

def safe_tkinter_call(func: Callable) -> Callable:
    """
    Decorator to ensure Tkinter calls happen in the main thread.

    Args:
        func: Function that may contain Tkinter calls

    Returns:
        Wrapped function that queues Tkinter calls safely
    """
    def wrapper(*args, **kwargs):
        # If we're in the main thread, call directly
        if threading.current_thread() is threading.main_thread():
            try:
                return func(*args, **kwargs)
            except RuntimeError:
                # Tkinter not initialized, queue the call
                pass

        # Otherwise, queue the call for the main thread
        gui_queue.put((func, args, kwargs))

    return wrapper

class GUIError(Exception):
    """Base exception for GUI-related errors"""
    pass

class ConfigurationError(GUIError):
    """Raised when configuration validation fails"""
    pass