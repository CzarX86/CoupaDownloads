"""
Setup Manager Module

Handles configuration setup for the application, including interactive and environment-based configurations.
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path

from .lib.excel_processor import ExcelProcessor
from .lib.config import Config as ExperimentalConfig
from .lib.models import InteractiveSetupSession

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
            from .lib.config import generate_timestamped_download_folder
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
            from .lib.config import Config
            Config.DOWNLOAD_FOLDER = normalized_download
        except Exception:
            pass
        # Propagate selection so child processes inherit the correct folder
        os.environ['DOWNLOAD_FOLDER'] = normalized_download
        os.makedirs(normalized_download, exist_ok=True)
        print(f"📁 Downloads will be saved to: {download_path}")

        # 3) Worker count (single question): 1 = sequential, >1 = parallel (one WebDriver per process)
        default_workers = 1
        workers_raw = input(f"Number of workers (1=sequential; >1=parallel) [{default_workers}]: ").strip()
        try:
            workers = int(workers_raw) if workers_raw else default_workers
        except ValueError:
            workers = default_workers
        if workers < 1:
            workers = 1
        self.experimental_config.USE_PROCESS_POOL = workers > 1
        self.experimental_config.PROC_WORKERS = workers if workers > 1 else 1
        # Treat cap as unlimited unless explicitly set elsewhere
        if getattr(self.experimental_config, 'PROC_WORKERS_CAP', None) is None:
            self.experimental_config.PROC_WORKERS_CAP = 0
        mode_label = "parallel" if self.experimental_config.USE_PROCESS_POOL else "sequential"
        print(f"⚙️  Execution mode: {mode_label} ({workers} worker{'s' if workers!=1 else ''})")

        # 5) Headless mode (default: Yes) - NEW: Use HeadlessConfiguration instead of env var
        headless_preference = self._prompt_bool("Run browser in headless mode?", default=True)

        # Create interactive setup session to track user preferences
        from .lib.models import InteractiveSetupSession
        setup_session = InteractiveSetupSession(headless_preference=headless_preference)

        # Log the headless mode configuration
        mode_str = "headless" if headless_preference else "visible"
        print(f"🎯 Browser mode configured: {mode_str}")

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
            workers = int(os.environ.get('PROC_WORKERS', '2'))
        except ValueError:
            workers = 2
        self.experimental_config.PROC_WORKERS = max(1, workers)
        self.experimental_config.USE_PROCESS_POOL = self.experimental_config.PROC_WORKERS > 1
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
        from .lib.config import Config
        Config.DOWNLOAD_FOLDER = os.path.abspath(os.path.expanduser(timestamped_dl))
        normalized_dl = Config.DOWNLOAD_FOLDER
        os.environ['DOWNLOAD_FOLDER'] = normalized_dl
        os.makedirs(normalized_dl, exist_ok=True)

        # Profile hints (optional)
        prof_dir = os.environ.get('EDGE_PROFILE_DIR')
        if prof_dir:
            self.experimental_config.EDGE_PROFILE_DIR = os.path.expanduser(prof_dir)
        prof_name = os.environ.get('EDGE_PROFILE_NAME')
        if prof_name:
            self.experimental_config.EDGE_PROFILE_NAME = prof_name

        suppress_output = os.environ.get('SUPPRESS_WORKER_OUTPUT', '1').strip().lower() in {'1', 'true', 'yes'}
        return {
            "headless_preference": headless_pref,
            "suppress_worker_output": suppress_output,
        }

    def scan_local_drivers(self) -> list[str]:
        """Return a list of plausible local driver paths under 'drivers/' directory."""
        candidates: list[str] = []
        base = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'drivers')
        if not os.path.isdir(base):
            return candidates
        for root, _dirs, files in os.walk(base):
            for name in files:
                if name.lower().startswith('msedgedriver'):
                    candidates.append(os.path.join(root, name))
        return sorted(candidates)

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
