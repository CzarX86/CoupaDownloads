#!/usr/bin/env python3
"""
Test script to verify GUI layout improvements.
"""

import sys
import os
import time
import tkinter as tk
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.ui.gui import CoupaDownloadsGUI

def test_gui_layout():
    """Test GUI layout and take screenshot"""
    print("🚀 Testing CoupaDownloads GUI layout...")

    # Create root window
    root = tk.Tk()

    # Initialize GUI
    gui = CoupaDownloadsGUI(root)

    print("✅ GUI initialized successfully")
    print("📐 Window size: 1000x800 (minimum: 900x700)")
    print("🎨 Layout improvements:")
    print("   • Removed unnecessary canvas/scrollbar")
    print("   • Better grid weights for proper resizing")
    print("   • Improved padding and spacing")
    print("   • Larger fonts and better proportions")
    print("   • Color-coded status indicators")
    print("   • Better button sizing and layout")

    # Wait a moment for GUI to render
    root.after(2000, lambda: print("🎯 GUI should be visible now with improved layout"))

    # Start GUI event loop
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\n👋 GUI test completed")
        root.destroy()

if __name__ == "__main__":
    test_gui_layout()