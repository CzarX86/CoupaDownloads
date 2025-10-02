"""
Non-network parallel smoke test for EXPERIMENTAL.

This script reads `EXPERIMENTAL/test_parallel_batch.csv`, spawns a small
ProcessPool to simulate processing 10 POs in parallel and writes placeholder
download artifacts into `EXPERIMENTAL/test_output/` so official Download folder
is not touched.
"""

from __future__ import annotations

import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from random import randint


TEST_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "test_output"
# test_parallel_batch.csv lives in EXPERIMENTAL/ root
TEST_CSV = Path(__file__).resolve().parents[1] / "test_parallel_batch.csv"



def load_pos(csv_path: Path):
    pos = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            po = (row.get("po_number") or "").strip()
            if not po:
                continue
            pos.append({
                "po_number": po,
                "supplier": (row.get("supplier") or "").strip(),
                "url": (row.get("coupa_url") or "").strip(),
            })
    return pos


def simulate_process_po(po: dict, output_dir: Path) -> dict:
    """Simulate processing a PO and write placeholder files."""
    time.sleep(randint(1, 3))
    po_dir = output_dir / f"{po['po_number']}_SIM"
    po_dir.mkdir(parents=True, exist_ok=True)
    # create a placeholder downloaded file
    (po_dir / f"{po['po_number']}_attachment.pdf").write_text("placeholder")
    # create a small metadata file
    (po_dir / "meta.txt").write_text(f"supplier={po['supplier']}\nurl={po['url']}\n")
    return {"po_number": po['po_number'], "status": "COMPLETED", "path": str(po_dir)}


def main():
    TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pos = load_pos(TEST_CSV)
    if not pos:
        print("No POs found in test_parallel_batch.csv")
        return

    results = []
    with ProcessPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(simulate_process_po, p, TEST_OUTPUT_DIR): p for p in pos}
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as e:
                p = futures[fut]
                results.append({"po_number": p['po_number'], "status": "FAILED", "error": str(e)})

    print("Parallel smoke finished. Results:")
    for r in results:
        print(f" - {r['po_number']}: {r.get('status')} -> {r.get('path', r.get('error'))}")


if __name__ == "__main__":
    main()
