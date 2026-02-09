#!/usr/bin/env python3
"""
Command-line interface for CoupaDownloads.

Supports both traditional CLI mode and GUI mode via --ui flag.
"""

import argparse
import sys
import logging
import os
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

def run_cli():
    """Run traditional CLI mode."""
    try:
        # Import and run the core system
        # In this project, MainApp in src/main.py is the main orchestrator
        from src.main import main as run_main
        run_main()

    except Exception as e:
        print(f"Error running CoupaDownloads: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='CoupaDownloads - Download attachments from Coupa POs',
        prog='coupadownloads'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    # Parse arguments
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Launch CLI (which now handles the TUI inside MainApp)
    run_cli()


if __name__ == '__main__':
    main()