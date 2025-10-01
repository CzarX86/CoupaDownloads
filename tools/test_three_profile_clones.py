#!/usr/bin/env python3
"""
Open 3 Microsoft Edge windows with cloned Default profiles (simple demo).

This script:
  1) Detects your base Edge user data directory and the 'Default' profile
  2) Creates N separate clone directories with essential files (no heavy caches)
  3) Launches N Edge windows via Selenium, each bound to a different clone

Requirements:
  - Microsoft Edge installed
  - msedgedriver available (in PATH or at ./drivers/msedgedriver)
  - pip install selenium

Usage examples:
  python tools/test_three_profile_clones.py
  python tools/test_three_profile_clones.py --count 3 --keep-open 45
  python tools/test_three_profile_clones.py --base-user-data-dir "~/Library/Application Support/Microsoft Edge" --profile-name Default

Notes:
  - On macOS, the base user data dir is usually: ~/Library/Application Support/Microsoft Edge
  - On Windows, it's usually: %LOCALAPPDATA%/Microsoft/Edge/User Data
  - We copy 'Local State' and the profile folder (e.g., 'Default') but skip large cache folders
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from selenium.webdriver import Edge
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


SKIP_DIRS = {
    'Cache', 'Code Cache', 'GPUCache', 'Service Worker', 'Session Storage',
    'Local Storage', 'IndexedDB', 'logs', 'GrShaderCache', 'Crashpad', 'ShaderCache'
}


def detect_base_user_data_dir() -> Path:
    # ENV overrides
    env = os.environ.get("EDGE_USER_DATA_DIR") or os.environ.get("EDGE_PROFILE_DIR")
    if env:
        return Path(os.path.expanduser(env)).resolve()

    if os.name == 'nt':
        localapp = os.environ.get('LOCALAPPDATA') or os.environ.get('USERPROFILE')
        if not localapp:
            raise RuntimeError("Could not determine %LOCALAPPDATA% on Windows")
        return Path(localapp) / 'Microsoft' / 'Edge' / 'User Data'
    else:
        # macOS/Linux
        return Path('~/Library/Application Support/Microsoft Edge').expanduser()


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def copy_root_essentials(source_root: Path, dest_root: Path) -> None:
    # Copy "Local State" if present
    src = source_root / 'Local State'
    if src.exists():
        try:
            shutil.copy2(str(src), str(dest_root / 'Local State'))
        except Exception as e:
            print(f"[warn] Could not copy 'Local State': {e}")


def copy_profile_folder(src_profile: Path, dst_profile: Path) -> None:
    ensure_dir(dst_profile)
    try:
        for item in os.listdir(src_profile):
            if item in SKIP_DIRS:
                continue
            s = src_profile / item
            d = dst_profile / item
            try:
                if s.is_dir():
                    shutil.copytree(str(s), str(d), dirs_exist_ok=True)
                else:
                    shutil.copy2(str(s), str(d))
            except Exception as e:
                print(f"[warn] Skipping '{item}': {e}")
    except FileNotFoundError:
        print(f"[warn] Source profile folder not found: {src_profile}")


def create_clone(base_user_data_dir: Path, profile_name: str, clone_root: Path) -> Path:
    ensure_dir(clone_root)
    # 1) Copy root essentials
    copy_root_essentials(base_user_data_dir, clone_root)
    # 2) Copy profile folder
    src_profile = base_user_data_dir / profile_name
    dst_profile = clone_root / profile_name
    copy_profile_folder(src_profile, dst_profile)
    return clone_root


def find_msedgedriver() -> Optional[Path]:
    # Prefer local drivers folder
    candidates = [
        Path(__file__).resolve().parent.parent / 'drivers' / 'msedgedriver',
        Path(__file__).resolve().parent.parent / 'drivers' / 'msedgedriver.exe',
    ]
    for c in candidates:
        if c.exists():
            return c
    # Fallback: rely on PATH
    return None


def launch_edge_with_profile(user_data_dir: Path, profile_name: str, start_url: str = 'edge://version') -> Edge:
    opts = EdgeOptions()
    opts.add_argument(f"--user-data-dir={str(user_data_dir)}")
    opts.add_argument(f"--profile-directory={profile_name}")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    # Prevent automation banners if possible
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])  # type: ignore
    opts.add_experimental_option("useAutomationExtension", False)  # type: ignore

    driver_path = find_msedgedriver()
    if driver_path is not None:
        # Ensure it's executable on Unix systems
        try:
            if os.name != 'nt':
                os.chmod(driver_path, 0o755)
        except Exception:
            pass
        try:
            service = EdgeService(executable_path=str(driver_path))
            driver = Edge(service=service, options=opts)
        except Exception as e:
            print(f"[warn] Local msedgedriver failed ('{driver_path}'): {e}. Falling back to Selenium Manager...")
            driver = Edge(options=opts)
    else:
        driver = Edge(options=opts)

    try:
        driver.get(start_url)
    except Exception:
        # Some internal pages may be restricted—fallback to a neutral URL
        driver.get("https://www.microsoft.com/edge")
    return driver


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Open N Edge windows with cloned Default profile")
    p.add_argument("--count", type=int, default=3, help="Number of windows to open (default: 3)")
    p.add_argument("--base-user-data-dir", type=str, default=None, help="Path to base Edge user data dir")
    p.add_argument("--profile-name", type=str, default=os.environ.get("EDGE_PROFILE_NAME", "Default"), help="Profile folder name to clone (default: Default)")
    p.add_argument("--keep-open", type=int, default=45, help="How many seconds to keep windows open before quitting (default: 45)")
    p.add_argument("--no-copy", action="store_true", help="Do not copy profile data; open blank profiles in fresh user-data-dirs")
    p.add_argument("--tmp-root", type=str, default=None, help="Custom temp root for clones (defaults to system temp)")
    return p.parse_args()


def _launch_edge_worker(barrier: threading.Barrier, clone_dir: Path, profile_name: str, start_url: str) -> Optional[Edge]:
    # Ensure all workers start nearly simultaneously
    try:
        barrier.wait(timeout=15)
    except threading.BrokenBarrierError:
        pass
    try:
        return launch_edge_with_profile(clone_dir, profile_name, start_url=start_url)
    except Exception as e:
        print(f"[error] Failed to launch Edge for {clone_dir}: {e}")
        return None


def main() -> int:
    args = parse_args()

    base_ud = Path(args.base_user_data_dir).expanduser().resolve() if args.base_user_data_dir else detect_base_user_data_dir()
    profile_name = args.profile_name

    if not base_ud.exists():
        print(f"[error] Base user data dir not found: {base_ud}")
        return 2

    print(f"Base user data dir: {base_ud}")
    print(f"Profile to clone:   {profile_name}")

    tmp_root = Path(args.tmp_root).expanduser().resolve() if args.tmp_root else Path(tempfile.gettempdir()) / "edge_profile_clones"
    ensure_dir(tmp_root)
    session_dir = tmp_root / datetime.now().strftime("%Y%m%d_%H%M%S")
    ensure_dir(session_dir)

    # Create N clones first
    clones: List[Path] = []

    for i in range(1, args.count + 1):
        clone_dir = session_dir / f"clone_{i:02d}"
        ensure_dir(clone_dir)
        if args.no_copy:
            print(f"[info] Creating empty user-data-dir for window {i}: {clone_dir}")
        else:
            print(f"[info] Cloning profile for window {i}: {clone_dir}")
            try:
                create_clone(base_ud, profile_name, clone_dir)
            except Exception as e:
                print(f"[warn] Clone failed for window {i}: {e}. Continuing with empty profile.")
        clones.append(clone_dir)

    # Launch all windows concurrently so they open at the same time
    drivers: List[Edge] = []
    start_url = 'edge://version'
    print(f"[info] Launching {len(clones)} Edge windows simultaneously...")
    barrier = threading.Barrier(parties=len(clones)) if clones else None
    if barrier is None:
        print("[error] No clones prepared.")
        return 3
    with ThreadPoolExecutor(max_workers=len(clones)) as executor:
        future_map = {
            executor.submit(_launch_edge_worker, barrier, c, profile_name, start_url): c for c in clones
        }
        for fut in as_completed(future_map):
            cdir = future_map[fut]
            drv = fut.result()
            if drv is not None:
                drivers.append(drv)
                print(f"[ok] Launched Edge with user-data-dir = {cdir}")

    if not drivers:
        print("[error] No windows were launched. Check msedgedriver and Edge installation.")
        return 3

    print(f"Keeping {len(drivers)} windows open for {args.keep_open} seconds...")
    try:
        time.sleep(args.keep_open)
    except KeyboardInterrupt:
        print("Interrupted by user.")

    # Teardown
    for d in drivers:
        try:
            d.quit()
        except Exception:
            pass

    print("All windows closed.")
    print("Clone directories (not deleted):")
    for c in clones:
        print(f"  - {c}")
    print("You can delete these folders manually when done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
