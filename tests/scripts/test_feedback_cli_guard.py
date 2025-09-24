from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "tools" / "feedback_cli.py"), *args],
        capture_output=True,
        text=True,
    )


def test_prepare_command_is_decommissioned():
    result = run_cli(
        "prepare",
        "--pred-csv",
        "reports/feedback/review.csv",
        "--out",
        "out.csv",
    )
    assert result.returncode != 0
    assert "The CSV-based feedback workflow has been removed" in result.stdout or result.stderr
