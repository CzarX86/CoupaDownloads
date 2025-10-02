"""
Non-interactive sequential smoke test for EXPERIMENTAL.

Reads a small CSV of POs and processes one PO sequentially using ProcessingSession
without invoking the interactive wizard or UI.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path

from EXPERIMENTAL.core.main import ProcessingSession
from EXPERIMENTAL.corelib.models import create_headless_configuration
from EXPERIMENTAL.corelib.config import Config as ExperimentalConfig


def load_pos_from_csv(csv_path: str) -> list[dict]:
    pos: list[dict] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            po_number = (row.get("po_number") or "").strip()
            if not po_number:
                continue
            pos.append({
                "po_number": po_number,
                "supplier": (row.get("supplier") or "").strip(),
                "url": (row.get("coupa_url") or "").strip(),
            })
    return pos


def main() -> None:
    # Ensure download folder exists
    os.makedirs(ExperimentalConfig.DOWNLOAD_FOLDER, exist_ok=True)

    csv_path = str(Path(__file__).resolve().parents[1] / "test_real_pos.csv")
    po_list = load_pos_from_csv(csv_path)
    if not po_list:
        print("No POs found in test_real_pos.csv")
        return

    # Limit to 1 to force sequential path via ProcessingSession
    po_list = po_list[:1]

    headless_config = create_headless_configuration(True)
    session = ProcessingSession(
        headless_config=headless_config,
        enable_parallel=False,
        max_workers=1,
        progress_callback=None,
        hierarchy_columns=[],
        has_hierarchy_data=False,
    )

    success, failed, report = session.process_pos(po_list)
    print("-" * 60)
    print("Sequential smoke finished")
    print(f"Success: {success}, Failed: {failed}")
    if report and isinstance(report, dict):
        results = report.get("results") or []
        for r in results:
            pn = r.get("po_number_display") or r.get("po_number")
            sc = r.get("status_code")
            msg = r.get("message") or r.get("status_reason") or ""
            print(f"  -> {pn}: {sc} — {msg}")


if __name__ == "__main__":
    main()
