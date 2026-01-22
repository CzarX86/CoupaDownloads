# File and directory browse dialogs

"""
Dialog utilities for browsing files and directories in the GUI.
"""

import tkinter as tk
from tkinter import filedialog
from typing import Optional


def browse_file(title: str = "Select File", filetypes: Optional[list[tuple[str, str]]] = None) -> Optional[str]:
    """
    Browse for a file.

    Args:
        title: Dialog title
        filetypes: List of (description, pattern) tuples

    Returns:
        Selected file path, or None if cancelled
    """
    if filetypes is None:
        filetypes = [("All files", "*.*")]

    # Convert to tkinter format
    tk_filetypes = [(desc, pattern) for desc, pattern in filetypes]

    filename = filedialog.askopenfilename(
        title=title,
        filetypes=tk_filetypes
    )

    return filename if filename else None


def browse_directory(title: str = "Select Directory") -> Optional[str]:
    """
    Browse for a directory.

    Args:
        title: Dialog title

    Returns:
        Selected directory path, or None if cancelled
    """
    dirname = filedialog.askdirectory(title=title)
    return dirname if dirname else None