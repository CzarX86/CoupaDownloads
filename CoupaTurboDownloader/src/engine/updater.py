import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

import httpx

GITHUB_API = "https://api.github.com/repos/juliocezar/CoupaTurboDownloader/releases/latest"
VERSION_FILE = os.path.join(os.path.dirname(__file__), "..", "..", ".version")


def _current_version() -> str:
    if os.path.exists(VERSION_FILE):
        return Path(VERSION_FILE).read_text().strip()
    return "0.0.0"


def _get_executable_path() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "main.py"))


async def check_for_update() -> Optional[Dict[str, Any]]:
    """Check GitHub Releases for newer version. Returns release info or None."""
    current = _current_version()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                GITHUB_API,
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            resp.raise_for_status()
            release = resp.json()
            latest = release["tag_name"].lstrip("v")
            if latest == current:
                return None

            # Find binary asset for current platform
            asset = _find_platform_asset(release.get("assets", []))
            if not asset:
                return None

            return {
                "version": latest,
                "current": current,
                "download_url": asset["browser_download_url"],
                "checksum": _sha256_for_asset(release.get("assets", [])),
                "size": asset["size"],
                "release_notes": release.get("body", ""),
            }
    except Exception:
        return None


def _find_platform_asset(assets: list) -> Optional[dict]:
    if sys.platform == "darwin":
        suffix = "macos"
    elif sys.platform == "win32":
        suffix = "windows.exe"
    else:
        return None

    for asset in assets:
        name = asset.get("name", "")
        if suffix in name.lower():
            return asset
    return None


def _sha256_for_asset(assets: list) -> Optional[str]:
    """Extract SHA256 if a .sha256 file is bundled."""
    for asset in assets:
        if asset.get("name", "").endswith(".sha256"):
            return None  # URL would be fetched separately; skip for now
    return None


async def download_update(download_url: str, dest_dir: str) -> str:
    """Download the new binary and return the path to the downloaded file."""
    dest_path = os.path.join(dest_dir, "CoupaTurboDownloader_new")
    async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
        async with client.stream("GET", download_url) as resp:
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                async for chunk in resp.aiter_bytes(1024 * 1024):
                    f.write(chunk)
    os.chmod(dest_path, 0o755)
    return dest_path


def apply_update_and_restart(new_binary: str) -> None:
    """
    Replace current executable with the new one and restart.
    Uses a platform-specific atomic replace script.
    """
    exe_path = _get_executable_path()

    if sys.platform == "darwin":
        script = f"""#!/bin/bash
sleep 1
mv "{new_binary}" "{exe_path}"
chmod +x "{exe_path}"
open "{exe_path}"
rm "$0"
"""
    elif sys.platform == "win32":
        script = f"""@echo off
timeout /t 2 /nobreak >nul
move /Y "{new_binary}" "{exe_path}"
start "" "{exe_path}"
del "%~f0"
"""
    else:
        raise OSError(f"Unsupported platform: {sys.platform}")

    script_path = os.path.join(tempfile.gettempdir(), "coupa_updater")
    if sys.platform == "win32":
        script_path += ".bat"
    else:
        script_path += ".sh"

    with open(script_path, "w") as f:
        f.write(script)
    os.chmod(script_path, 0o755)

    # Detach updater script from this process
    if sys.platform == "darwin":
        subprocess.Popen(
            ["/bin/bash", script_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    elif sys.platform == "win32":
        subprocess.Popen(
            f'cmd /c "{script_path}"',
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS,
        )

    sys.exit(0)
