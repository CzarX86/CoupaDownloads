import subprocess
import sys
import os
import argparse
import re
import csv

LOG_FILE = "download_telemetry.log"
SUMMARY_CSV = os.path.join("tests", "download_telemetry_summary.csv")
DETAILS_CSV = os.path.join("tests", "download_telemetry_details.csv")

METHOD_PATTERNS = {
    "direct": re.compile(r"Downloading directly: "),
    "right_click": re.compile(r"Right-clicking on:"),
    "temp_dir": re.compile(r"Using temporary directory:"),
}

SUCCESS_PATTERNS = {
    "direct": re.compile(r"Successfully saved: (.+)"),
    "right_click": re.compile(r"Right-click method is complex and browser-dependent"),
    "temp_dir": re.compile(r"Changed download directory to temp folder"),
}

FAIL_PATTERNS = {
    "direct": re.compile(r"Failed to download (.+) directly"),
    "right_click": re.compile(r"Could not handle Save As dialog"),
    "temp_dir": re.compile(r"Could not change download directory"),
}

PO_PATTERN = re.compile(r"Processing PO #(\w+)")
FILENAME_PATTERN = re.compile(r"Downloading directly: (.+) → (.+)")


def run_main_and_capture():
    """Run main.py and capture stdout/stderr to a log file."""
    print(f"Running main.py and capturing output to {LOG_FILE}...")
    with open(LOG_FILE, "w") as f:
        proc = subprocess.run([sys.executable, "main.py"], cwd=os.path.dirname(__file__), stdout=f, stderr=subprocess.STDOUT)
    print(f"Done. Output saved to {LOG_FILE}.")

def parse_log():
    """Parse the log file and summarize download method usage and results. Also output CSVs."""
    if not os.path.exists(LOG_FILE):
        print(f"Log file {LOG_FILE} not found.")
        return
    
    method_counts = {k: 0 for k in METHOD_PATTERNS}
    success_counts = {k: 0 for k in METHOD_PATTERNS}
    fail_counts = {k: 0 for k in METHOD_PATTERNS}
    details = []  # List of dicts: {po, filename, method, result}
    
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()
    
    current_method = None
    current_po = None
    current_filename = None
    for line in lines:
        po_match = PO_PATTERN.search(line)
        if po_match:
            current_po = po_match.group(1)
        for method, pat in METHOD_PATTERNS.items():
            if pat.search(line):
                current_method = method
                method_counts[method] += 1
        for method, pat in SUCCESS_PATTERNS.items():
            m = pat.search(line)
            if m:
                success_counts[method] += 1
                # Try to get filename for direct method
                if method == "direct":
                    filename = None
                    fn_match = FILENAME_PATTERN.search(line)
                    if fn_match:
                        filename = fn_match.group(2)
                    details.append({
                        "po": current_po,
                        "filename": filename,
                        "method": method,
                        "result": "success"
                    })
                else:
                    details.append({
                        "po": current_po,
                        "filename": None,
                        "method": method,
                        "result": "success"
                    })
        for method, pat in FAIL_PATTERNS.items():
            m = pat.search(line)
            if m:
                fail_counts[method] += 1
                # Try to get filename for direct method
                if method == "direct":
                    filename = None
                    if m.lastindex:
                        filename = m.group(1)
                    details.append({
                        "po": current_po,
                        "filename": filename,
                        "method": method,
                        "result": "fail"
                    })
                else:
                    details.append({
                        "po": current_po,
                        "filename": None,
                        "method": method,
                        "result": "fail"
                    })
    # Write summary CSV
    os.makedirs(os.path.dirname(SUMMARY_CSV), exist_ok=True)
    with open(SUMMARY_CSV, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["method", "attempts", "successes", "failures"])
        for method in METHOD_PATTERNS:
            writer.writerow([method, method_counts[method], success_counts[method], fail_counts[method]])
    print(f"Summary CSV written to {SUMMARY_CSV}")
    # Write details CSV
    with open(DETAILS_CSV, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["po", "filename", "method", "result"])
        writer.writeheader()
        for row in details:
            writer.writerow(row)
    print(f"Details CSV written to {DETAILS_CSV}")
    # Print summary
    print("\n==== Download Method Telemetry Summary ====")
    for method in METHOD_PATTERNS:
        print(f"Method: {method}")
        print(f"  Attempts: {method_counts[method]}")
        print(f"  Successes: {success_counts[method]}")
        print(f"  Failures: {fail_counts[method]}")
        print()
    print(f"Parsed log file: {LOG_FILE}")

def main():
    parser = argparse.ArgumentParser(description="Test and summarize CoupaDownloads download methods.")
    parser.add_argument("--parse-only", action="store_true", help="Only parse the log file, do not run main.py.")
    args = parser.parse_args()
    
    if not args.parse_only:
        run_main_and_capture()
    parse_log()

if __name__ == "__main__":
    main() 