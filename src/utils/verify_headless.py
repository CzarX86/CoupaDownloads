#!/usr/bin/env python3
"""
Headless verification probe (offline):
- Forces headless WebDriver launch
- Checks UA via CDP Browser.getVersion (contains 'Headless')
- Opens a local HTML page with a data: download link and verifies file creation

Does not require internet. Safe to run locally.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.core.browser import BrowserManager
from src.core.config import Config


def _print_env_and_versions(driver) -> None:
    try:
        res = driver.execute_cdp_cmd("Browser.getVersion", {})
        ua = res.get("userAgent", "")
        print(f"UserAgent: {ua}")
        print(f"UA contains 'Headless': {'Headless' in ua}")
        print(json.dumps(res, indent=2))
    except Exception as e:
        print(f"⚠️ Could not query Browser.getVersion: {e}")


def _prepare_download_dir() -> str:
    dl = os.path.join(Config.PROJECT_ROOT, "data", "headless_test_downloads")
    os.makedirs(dl, exist_ok=True)
    return dl


def _test_download(driver, download_dir: str) -> bool:
    asset = Path(__file__).resolve().parent / "assets" / "headless_download_test.html"
    url = f"file://{asset}"
    driver.get(url)
    time.sleep(0.3)
    try:
        el = driver.find_element("id", "dl")
        before = set(os.listdir(download_dir))
        el.click()
        # wait for file to appear
        deadline = time.time() + 5
        while time.time() < deadline:
            now = set(os.listdir(download_dir))
            added = list(now - before)
            if any(name.endswith((".txt", ".crdownload")) for name in added) or "sample.txt" in now:
                return True
            time.sleep(0.2)
    except Exception as e:
        print(f"⚠️ Download click failed: {e}")
    return False


def main() -> None:
    print("=== Headless Verification Probe ===")
    bm = BrowserManager()
    # Force headless
    os.environ["HEADLESS"] = "true"
    dl_dir = _prepare_download_dir()
    print(f"Download directory: {dl_dir}")
    try:
        drv = bm.start(headless=True)
        _print_env_and_versions(drv)
        bm.update_download_directory(dl_dir)
        ok = _test_download(drv, dl_dir)
        print(f"Download triggered in headless: {ok}")
    except Exception as e:
        print(f"❌ Headless probe error: {e}")
    finally:
        try:
            bm.cleanup()
        except Exception:
            pass


if __name__ == "__main__":
    main()

