#!/usr/bin/env python3
"""
GUI Launch Script for CoupaDownloads.

This script provides a convenient way to launch the CoupaDownloads GUI.
"""

import sys
import os

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import and run CLI with --ui flag
from src.cli.main import main

if __name__ == '__main__':
    # Force --ui flag
    import sys
    sys.argv.insert(1, '--ui')
    main()