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

def is_gui_available():
    """Check if GUI is available on this system."""
    # Check for DISPLAY environment variable (Linux/Unix)
    if os.name != 'nt' and not os.environ.get('DISPLAY'):
        return False

    # Check if tkinter can be imported and initialized
    try:
        import tkinter as tk
        # Try to create a root window (this will fail in headless environments)
        root = tk.Tk()
        root.withdraw()  # Hide the window
        root.destroy()
        return True
    except Exception:
        return False


def launch_gui(force=False):
    """Launch the GUI application in a separate process."""
    # Check if GUI is available (unless forced)
    if not force and not is_gui_available():
        print("Error: GUI is not available on this system.", file=sys.stderr)
        print("This could be because:", file=sys.stderr)
        print("  - No display is available (headless environment)", file=sys.stderr)
        print("  - Tkinter is not properly installed", file=sys.stderr)
        print("  - Running in a container without X11 forwarding", file=sys.stderr)
        print("", file=sys.stderr)
        print("To run the GUI, ensure you have a graphical desktop environment.", file=sys.stderr)
        print("Or use --force-ui to attempt launch anyway (may fail).", file=sys.stderr)
        sys.exit(1)

    try:
        import subprocess

        # Launch GUI in separate process to avoid blocking CLI
        cmd = [sys.executable, "-c", f"""
import sys
import os
# Add the current directory and src to path
current_dir = r"{os.getcwd()}"
src_path = os.path.join(current_dir, "src")
sys.path.insert(0, current_dir)
sys.path.insert(0, src_path)

try:
    import tkinter as tk
    from src.ui.gui import CoupaDownloadsGUI

    # Create root window
    root = tk.Tk()

    # Create and run GUI
    app = CoupaDownloadsGUI(root)
    app.run()

except Exception as e:
    print(f"GUI Error: {{e}}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""]

        # Launch as separate process
        process = subprocess.Popen(cmd, cwd=os.path.dirname(__file__))

        # Wait for process to complete (non-blocking for CLI)
        try:
            process.wait()
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            process.terminate()
            process.wait()
            print("\nGUI terminated by user")
            sys.exit(0)

        # Check process exit code
        if process.returncode != 0:
            print(f"GUI process exited with error code: {process.returncode}", file=sys.stderr)
            sys.exit(process.returncode)

    except FileNotFoundError:
        print("Error: Python executable not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error launching GUI: {e}", file=sys.stderr)
        sys.exit(1)


def run_cli():
    """Run traditional CLI mode."""
    try:
        # Import and run the core system
        from src.core.interfaces import get_core_system

        core_system = get_core_system()

        # For now, this is a placeholder - the actual CLI logic
        # would be implemented based on the existing core system
        print("CLI mode not yet implemented. Use --ui for GUI mode.")
        print("See quickstart.md for more information.")

    except Exception as e:
        print(f"Error running CLI: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='CoupaDownloads - Download attachments from Coupa POs',
        prog='coupadownloads'
    )

    parser.add_argument(
        '--ui',
        action='store_true',
        help='Launch graphical user interface'
    )

    parser.add_argument(
        '--force-ui',
        action='store_true',
        help='Force GUI launch even in headless environment (for testing)'
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

    # Launch appropriate mode
    if args.ui or args.force_ui:
        launch_gui(force=args.force_ui)
    else:
        run_cli()


if __name__ == '__main__':
    main()