"""
Setup Manager Module

Handles configuration setup for the application, including interactive and environment-based configurations.
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path

from .lib.excel_processor import ExcelProcessor
from .config.app_config import Config as ExperimentalConfig
from .lib.models import InteractiveSetupSession, ExecutionMode

# Global variable to store current setup session (replaces environment variables)
_current_setup_session: Optional[Dict[str, Any]] = None


class SetupManager:
    """Manages setup and configuration for the application."""

    def __init__(self):
        self.experimental_config = ExperimentalConfig

    def interactive_setup(self) -> InteractiveSetupSession:
        """Interactive wizard to gather runtime configuration from the user."""
        print("\n=== Interactive Setup ===")
        print("(Press Enter to accept defaults shown in [brackets])")

        # 1) Input file path
        default_input = ExcelProcessor.get_excel_file_path()
        inp = input(f"Path to input CSV/XLSX [{default_input}]: ").strip() or default_input
        # Persist selection to experimental config (avoids env usage)
        self.experimental_config.EXCEL_FILE_PATH = inp

        # 2) Download folder path
        # Use value from .env as default, but expand ~ properly
        default_download = os.path.expanduser(self.experimental_config.DOWNLOAD_FOLDER)

        # If using the old default format, suggest the new timestamped format
        if "CoupaDownloads" in default_download and not any(char.isdigit() for char in os.path.basename(default_download)):
            # Generate a new timestamped folder as suggestion
            from .config.app_config import generate_timestamped_download_folder
            suggested_download = generate_timestamped_download_folder("/Users/juliocezar/Downloads")
            print(f"💡 Suggested timestamped folder: {suggested_download}")
            default_download = suggested_download

        download_path = input(f"Download folder path [{default_download}]: ").strip() or default_download
        # Expand user path and ensure it's absolute
        download_path = os.path.expanduser(download_path)
        if not os.path.isabs(download_path):
            download_path = os.path.abspath(download_path)

        # Update config and ensure folder exists
        normalized_download = os.path.abspath(os.path.expanduser(download_path))
        self.experimental_config.DOWNLOAD_FOLDER = normalized_download
        # Keep core Config in sync so browser options pick the right path on first init
        try:
            from .config.app_config import Config
            Config.DOWNLOAD_FOLDER = normalized_download
        except Exception:
            pass
        # Propagate selection so child processes inherit the correct folder
        os.environ['DOWNLOAD_FOLDER'] = normalized_download
        os.makedirs(normalized_download, exist_ok=True)
        print(f"📁 Downloads will be saved to: {download_path}")

        # 3) Worker count: 0 = automatic scaling, >=1 = fixed worker count
        default_workers = 0
        workers_raw = input(
            f"Number of workers (0=automatic; 1+=fixed parallelism) [{default_workers}]: "
        ).strip()
        try:
            workers = int(workers_raw) if workers_raw else default_workers
        except ValueError:
            workers = default_workers
        if workers < 0:
            workers = default_workers

        self.experimental_config.USE_PROCESS_POOL = True
        self.experimental_config.PROC_WORKERS = workers
        self.experimental_config.resource_aware_scaling = workers == 0
        # Treat cap as unlimited unless explicitly set elsewhere
        if getattr(self.experimental_config, 'PROC_WORKERS_CAP', None) is None:
            self.experimental_config.PROC_WORKERS_CAP = 0
        if workers == 0:
            print("⚙️  Execution mode: automatic worker scaling (starts at 1 and adapts to resources)")
        else:
            print(f"⚙️  Execution mode: fixed parallelism ({workers} worker{'s' if workers != 1 else ''})")

        # 5) Headless mode (default: Yes) - NEW: Use HeadlessConfiguration instead of env var
        headless_preference = self._prompt_bool("Run browser in headless mode?", default=True)

        # 5.1) UI Mode (Premium by default)
        ui_mode = "premium"

        # 5.2) Execution Mode (NEW)
        print("\n🚀 Choose Execution Mode:")
        print(" [1] Standard (Full Browser - Best Compatibility)")
        print(" [2] Filtered (No Images/Fonts/CSS - Faster & Lighter)")
        print(" [3] No JS (JavaScript Disabled - Maximum Performance)")
        print(" [4] Turbo (Direct HTTP - Machine Level Extraction)")
        exec_choice = input("Select execution mode [1]: ").strip()
        
        execution_mode = ExecutionMode.STANDARD
        if exec_choice == "2":
            execution_mode = ExecutionMode.FILTERED
        elif exec_choice == "3":
            execution_mode = ExecutionMode.NO_JS
        elif exec_choice == "4":
            execution_mode = ExecutionMode.DIRECT_HTTP

        # Force USE_PROFILE to True for Filtered/NoJS modes as they rely on PersistentWorkerPool
        if execution_mode in (ExecutionMode.FILTERED, ExecutionMode.NO_JS):
            self.experimental_config.USE_PROFILE = True


        # Create interactive setup session to track user preferences
        from .lib.models import InteractiveSetupSession
        setup_session = InteractiveSetupSession(
            headless_preference=headless_preference,
            ui_mode=ui_mode,
            execution_mode=execution_mode
        )

        # Log the headless mode configuration
        mode_str = "headless" if headless_preference else "visible"
        print(f"🎯 Browser mode configured: {mode_str}")
        print(f"⚡ Execution level: {execution_mode.value.upper()}")

        # 6) Suppress worker output (avoid Live UI duplication)
        suppress_output = self._prompt_bool("Suppress worker output during execution?", default=True)
        os.environ['SUPPRESS_WORKER_OUTPUT'] = '1' if suppress_output else '0'

        # Store setup session for later use (replace env var dependency)
        global _current_setup_session
        _current_setup_session = setup_session

        return setup_session

    def apply_env_overrides(self) -> Dict[str, Any]:
        """Configure runtime from environment variables."""
        # Input path
        input_path = os.environ.get('EXCEL_FILE_PATH')
        if not input_path:
            input_path = ExcelProcessor.get_excel_file_path()
        self.experimental_config.EXCEL_FILE_PATH = os.path.expanduser(input_path)

        # Execution model derived from worker count only
        try:
            workers = int(os.environ.get('PROC_WORKERS', '0'))
        except ValueError:
            workers = 0
        workers = max(0, workers)
        self.experimental_config.PROC_WORKERS = workers
        self.experimental_config.USE_PROCESS_POOL = True
        self.experimental_config.resource_aware_scaling = workers == 0
        cap_env = os.environ.get('PROC_WORKERS_CAP')
        if cap_env is not None:
            try:
                self.experimental_config.PROC_WORKERS_CAP = int(cap_env)
            except ValueError:
                self.experimental_config.PROC_WORKERS_CAP = 0
        if getattr(self.experimental_config, 'PROC_WORKERS_CAP', None) is None:
            self.experimental_config.PROC_WORKERS_CAP = 0

        # Headless
        headless_pref = os.environ.get('HEADLESS', 'true').strip().lower() == 'true'

        # UI and output settings
        # Default to 'none' for non-interactive, 'premium' for interactive
        enable_interactive = os.environ.get('ENABLE_INTERACTIVE_UI', 'True').strip().lower() == 'true'
        ui_mode = os.environ.get('UI_MODE', 'none' if not enable_interactive else 'premium').strip().lower()
        suppress_output = os.environ.get('SUPPRESS_WORKER_OUTPUT', '1').strip() == '1'

        # Download folder (apply timestamp prefix automatically)
        from datetime import datetime

        base_dl = os.path.abspath(os.path.expanduser(os.environ.get('DOWNLOAD_FOLDER', self.experimental_config.DOWNLOAD_FOLDER)))

        # Add timestamp prefix to download folder
        timestamp = datetime.now().strftime('%Y%m%d-%Hh%M')
        parent_dir = os.path.dirname(base_dl)
        base_name = os.path.basename(base_dl.rstrip('/'))
        timestamped_dl = os.path.join(parent_dir, f"{timestamp}_{base_name}")

        self.experimental_config.DOWNLOAD_FOLDER = os.path.abspath(os.path.expanduser(timestamped_dl))

        # IMPORTANT: Also update Config.DOWNLOAD_FOLDER so browser uses the correct path
        from .config.app_config import Config
        Config.DOWNLOAD_FOLDER = os.path.abspath(os.path.expanduser(timestamped_dl))
        normalized_dl = str(Config.DOWNLOAD_FOLDER)  # Convert Path to str
        os.environ['DOWNLOAD_FOLDER'] = normalized_dl
        os.makedirs(normalized_dl, exist_ok=True)

        # MSG → PDF flags
        msg_to_pdf_enabled = os.environ.get('MSG_TO_PDF_ENABLED', 'true').strip().lower() in ('1', 'true', 'yes')
        msg_to_pdf_overwrite = os.environ.get('MSG_TO_PDF_OVERWRITE', 'false').strip().lower() in ('1', 'true', 'yes')
        self.experimental_config.MSG_TO_PDF_ENABLED = msg_to_pdf_enabled
        self.experimental_config.MSG_TO_PDF_OVERWRITE = msg_to_pdf_overwrite
        os.environ['MSG_TO_PDF_ENABLED'] = 'true' if msg_to_pdf_enabled else 'false'
        os.environ['MSG_TO_PDF_OVERWRITE'] = 'true' if msg_to_pdf_overwrite else 'false'

        # Profile hints (optional)
        prof_dir = os.environ.get('EDGE_PROFILE_DIR')
        if prof_dir:
            self.experimental_config.EDGE_PROFILE_DIR = os.path.expanduser(prof_dir)
        prof_name = os.environ.get('EDGE_PROFILE_NAME')
        if prof_name:
            self.experimental_config.EDGE_PROFILE_NAME = prof_name

        # Execution Mode from env
        exec_mode_env = os.environ.get('EXECUTION_MODE', 'standard').strip().lower()
        execution_mode = ExecutionMode.STANDARD
        for m in ExecutionMode:
            if m.value == exec_mode_env:
                execution_mode = m
                break

        return {
            "headless_preference": headless_pref,
            "suppress_worker_output": suppress_output,
            "ui_mode": ui_mode,
            "execution_mode": execution_mode
        }

    @staticmethod
    def _prompt_bool(prompt: str, default: bool) -> bool:
        d = 'Y/n' if default else 'y/N'
        while True:
            ans = input(f"{prompt} [{d}]: ").strip().lower()
            if ans == '' and default is not None:
                return default
            if ans in ('y', 'yes'):
                return True
            if ans in ('n', 'no'):
                return False
            print("Please answer y or n.")
