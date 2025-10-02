#!/usr/bin/env python3
"""
EdgeDriver download test: ensure we download to a temp directory and extract only the driver binary.
This script safely backs up any local drivers in 'drivers/' to force an auto-download, then restores them.
"""

import os
import sys
import time
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))


def main() -> None:
    print("🧪 Testing EdgeDriver download and extraction (temp dir)...")
    print("=" * 60)

    from core.driver_manager import DriverManager

    dm = DriverManager()
    print(f"🖥️ Platform: {dm.platform}")
    print(f"📁 Project root: {dm.project_root}")
    print(f"📁 Drivers dir: {dm.drivers_dir}")

    backups: list[tuple[str, str]] = []

    try:
        # Backup any existing local drivers so we force an auto-download to temp
        candidates = dm._scan_local_drivers()
        if candidates:
            print(f"🔍 Found {len(candidates)} local driver candidate(s); backing up temporarily to force download...")
        # Move candidates into a backup subdirectory so they are not detected by the scanner
        backup_dir = Path(dm.drivers_dir) / "_backup_for_test"
        backup_dir.mkdir(parents=True, exist_ok=True)
        for path in candidates:
            src = Path(path)
            backup = str(backup_dir / src.name)
            try:
                os.replace(str(src), backup)
                backups.append((str(src), backup))
                print(f"   📦 Moved to backup: {src.name}")
            except Exception as e:
                print(f"   ⚠️ Could not backup {path}: {e}")

        # Trigger auto-download
        start = time.time()
        driver_path = dm.get_driver_path()
        elapsed = time.time() - start
        print(f"\n✅ get_driver_path() returned in {elapsed:.1f}s")
        print(f"📍 Driver path: {driver_path}")

        # Validate location: should be inside drivers/tmp/
        expected_fragment = str(Path(dm.drivers_dir) / "tmp")
        if expected_fragment in driver_path:
            print("✅ Confirmed driver is in a temp subfolder under drivers/tmp/")
        else:
            print("⚠️ Driver path is not under drivers/tmp; check logic or environment overrides")

        # Check extracted contents: only the driver should exist in the temp dir
        temp_dir = Path(driver_path).parent
        files = list(temp_dir.iterdir())
        driver_files = [f for f in files if "msedgedriver" in f.name.lower()]
        other_files = [f for f in files if "msedgedriver" not in f.name.lower()]
        print(f"📂 Temp dir contains {len(files)} file(s)")
        print(f"   • Driver files: {len(driver_files)}")
        print(f"   • Other files: {len(other_files)}")
        if len(driver_files) == 1 and len(other_files) == 0:
            print("✅ Only the driver binary was extracted")
        else:
            print(f"⚠️ Unexpected extra files present: {[f.name for f in other_files]}")

        # Verify the driver binary works
        print("\n🧪 Verifying driver binary...")
        if dm.verify_driver(driver_path):
            print("✅ Driver verification PASSED")
        else:
            print("❌ Driver verification FAILED")

    except KeyboardInterrupt:
        print("\n⏸️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Restore any backed-up drivers
        if backups:
            print("\n🔄 Restoring local driver backups...")
        for original, backup in backups:
            try:
                if os.path.exists(backup):
                    # Move back from backup folder to original location
                    os.replace(backup, original)
                    print(f"   ✅ Restored: {Path(original).name}")
            except Exception as e:
                print(f"   ⚠️ Restore failed for {original}: {e}")

        print("\n🏁 Test completed")


if __name__ == "__main__":
    main()