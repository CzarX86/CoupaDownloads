#!/usr/bin/env python3
"""Minimal sidecar backend for the Tauri unsigned test.

Represents the ContractDownloader backend architecture:
  - one-shot JSON protocol: `python sidecar.py <command> <json_args>`
  - stdout is always a single JSON document
  - pandas for spreadsheet/PO processing
  - Power BI dataset access through the Fabric CLI (`fab`), with an offline
    mock fallback when the CLI is not installed or not authenticated.

The real app mirrors these patterns in ContractDownloader/src (gui/api.py,
engine/*.py, powerbi_provider.py).
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

APP_NAME = "tauri-unsigned-test"
FAB_VERSION = "1.6.1"
# Representative dataset ids (the real app uses these in powerbi_provider.py).
GRIR_DATASET_ID = "45f78e7b-bb55-42f4-a5e3-8b790e6dfbb3"
INVOICE_DATASET_ID = "2cbe0c63-e1da-416e-b765-a87fd33d5ebe"


def _report(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.write("\n")
    sys.stdout.flush()


def _fail(error: str) -> None:
    _report({"ok": False, "error": error})


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def cmd_ping(_args: dict) -> dict:
    pandas_version = None
    try:
        import pandas  # noqa: F401

        pandas_version = pandas.__version__
    except Exception:
        pass
    return {
        "ok": True,
        "app": APP_NAME,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "pandas": pandas_version,
    }


def cmd_process_csv(_args: dict) -> dict:
    """Read sample PO data with pandas and return summary statistics."""
    try:
        import pandas as pd
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "error": f"pandas is not installed: {exc}"}
    csv_path = Path(__file__).resolve().parent / "sample_data.csv"
    if not csv_path.exists():
        return {"ok": False, "error": f"sample_data.csv not found at {csv_path}"}
    started = time.perf_counter()
    df = pd.read_csv(csv_path)
    summary = {
        "rows": int(len(df)),
        "columns": list(df.columns),
        "po_count": int(df["po_number"].nunique()),
        "total_amount": round(float(df["amount"].sum()), 2),
        "currency": str(df["currency"].iloc[0]) if len(df) else None,
        "by_status": {str(k): round(float(v), 2) for k, v in df.groupby("status")["amount"].sum().items()},
        "suppliers": sorted(df["supplier"].unique().tolist()),
    }
    summary["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)
    return {"ok": True, "summary": summary}


def _fab_command() -> list[str] | None:
    """Resolve the Fabric CLI like the real PowerBIProvider does."""
    import os

    configured = os.environ.get("COUPAPILOT_FAB_COMMAND", "").strip()
    if configured:
        return configured.split()
    fab = shutil.which("fab")
    if fab:
        return [fab]
    uv = shutil.which("uv")
    if uv:
        return [uv, "tool", "run", "--from", f"ms-fabric-cli=={FAB_VERSION}", "fab"]
    return None


def _fab_run(arguments: list[str], timeout: float = 20.0) -> subprocess.CompletedProcess[str] | None:
    command = _fab_command()
    if command is None:
        return None
    try:
        return subprocess.run(
            command + arguments,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception:
        return None


def cmd_powerbi_status(_args: dict) -> dict:
    """Mirror of PowerBIProvider.auth_status()."""
    result = _fab_run(["auth", "status"], timeout=15)
    if result is None:
        return {
            "ok": True,
            "mock": True,
            "authenticated": False,
            "message": "Fabric CLI not available — mock mode (install ms-fabric-cli for real access)",
        }
    authenticated = "logged in: true" in (result.stdout or "").lower()
    message = (result.stdout or result.stderr or "").strip().splitlines()
    return {
        "ok": True,
        "mock": False,
        "authenticated": authenticated,
        "message": message[-1] if message else f"fab exited {result.returncode}",
    }


def cmd_powerbi_query(args: dict) -> dict:
    """Mirror of PowerBIProvider._execute_dataset_query() with mock fallback.

    Real path: write the DAX payload to a temp JSON file and run
    `fab api -A powerbi datasets/<id>/executeQueries -X post -i file`.
    """
    dataset = str(args.get("dataset", "grir"))
    dax = str(args.get("dax", ""))
    dataset_id = GRIR_DATASET_ID if dataset == "grir" else INVOICE_DATASET_ID
    payload = {
        "queries": [{"query": dax or "EVALUATE ROW(\"status\", \"ok\")"}],
        "serializerSettings": {"includeNulls": True},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", encoding="utf-8", delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False)
        temp_path = handle.name
    try:
        result = _fab_run(
            [
                "api",
                "-A",
                "powerbi",
                f"datasets/{dataset_id}/executeQueries",
                "-X",
                "post",
                "-H",
                "content-type=application/json",
                "-i",
                temp_path,
            ],
            timeout=30,
        )
    finally:
        try:
            Path(temp_path).unlink()
        except OSError:
            pass

    if result is None:
        # Offline mock: simulated GRIR rows from the Power BI dataset.
        return {
            "ok": True,
            "mock": True,
            "dataset": dataset,
            "rows": [
                {"po_number": "PO-45001234", "supplier": "Accenture", "grir_amount": 125400.0, "status": "Posted"},
                {"po_number": "PO-45009876", "supplier": "Infosys", "grir_amount": 87320.5, "status": "Open"},
                {"po_number": "PO-45005511", "supplier": "Deloitte", "grir_amount": 64100.0, "status": "Posted"},
            ],
            "message": "mock dataset (Fabric CLI not available)",
        }
    if result.returncode != 0:
        return {
            "ok": False,
            "mock": False,
            "error": (result.stderr or result.stdout or f"fab exited {result.returncode}").strip()[-400:],
        }
    start = result.stdout.find("{")
    end = result.stdout.rfind("}")
    try:
        parsed = json.loads(result.stdout[start : end + 1]) if start >= 0 and end > start else {"raw": result.stdout}
    except json.JSONDecodeError:
        parsed = {"raw": result.stdout[-400:]}
    return {"ok": True, "mock": False, "dataset": dataset, "response": parsed}


COMMANDS = {
    "ping": cmd_ping,
    "process_csv": cmd_process_csv,
    "powerbi_status": cmd_powerbi_status,
    "powerbi_query": cmd_powerbi_query,
}


def main() -> None:
    if len(sys.argv) < 2:
        _fail("usage: sidecar.py <command> [json_args]")
        return
    command = sys.argv[1]
    args = {}
    if len(sys.argv) >= 3:
        try:
            args = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            _fail(f"invalid JSON arguments: {sys.argv[2]}")
            return
    handler = COMMANDS.get(command)
    if handler is None:
        _fail(f"unknown command: {command}")
        return
    try:
        _report(handler(args))
    except Exception as exc:  # noqa: BLE001 - report any sidecar failure
        _fail(f"{type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
