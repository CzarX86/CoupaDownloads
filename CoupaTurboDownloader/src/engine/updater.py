from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
import shlex
from pathlib import Path
from typing import Optional, Dict, Any

import httpx

GITHUB_REPOSITORY = os.environ.get("COUPA_UPDATE_REPO", "CzarX86/CoupaPilot")
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
VERSION_FILE = os.path.join(os.path.dirname(__file__), "..", "..", ".version")


def _version_path() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / ".version"
    return Path(VERSION_FILE).resolve()


def _current_version() -> str:
    try:
        value = _version_path().read_text(encoding="utf-8").strip()
        return value.lstrip("v") or "0.0.0"
    except OSError:
        return "0.0.0"


def _version_key(value: str) -> tuple[int, ...]:
    numbers = re.findall(r"\d+", value or "0")
    return tuple(int(number) for number in numbers[:4]) or (0,)


def _python_portable_root() -> Optional[Path]:
    if os.environ.get("COUPA_PYTHON_PORTABLE") != "1":
        return None
    candidate = Path(sys.executable).resolve().parent.parent
    return candidate if (candidate / "portable-python.json").is_file() else None


def _find_platform_asset(assets: list) -> Optional[dict]:
    if sys.platform == "darwin":
        tokens = ("macos", "darwin")
    elif sys.platform == "win32":
        tokens = ("windows", "win32")
    else:
        return None

    candidates = [asset for asset in assets if any(token in asset.get("name", "").lower() for token in tokens)]
    if sys.platform == "win32":
        wants_python_portable = _python_portable_root() is not None
        matching_edition = [
            asset
            for asset in candidates
            if ("python-portable" in asset.get("name", "").lower()) == wants_python_portable
        ]
        candidates = matching_edition
    for asset in candidates:
        name = asset.get("name", "").lower()
        if name.endswith((".zip", ".exe", ".app")):
            return asset
    return candidates[0] if candidates else None


def _find_checksum_asset(assets: list) -> Optional[dict]:
    for asset in assets:
        name = asset.get("name", "").lower()
        if name.endswith((".sha256", "sha256sums.txt", "checksums.txt")):
            return asset
    return None


async def check_for_update() -> Optional[Dict[str, Any]]:
    """Return a newer GitHub Release for the current platform, if available."""
    current = _current_version()
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(GITHUB_API, headers={"Accept": "application/vnd.github+json"})
            response.raise_for_status()
            release = response.json()
            latest = str(release.get("tag_name", "")).lstrip("v")
            if not latest or _version_key(latest) <= _version_key(current):
                return None

            asset = _find_platform_asset(release.get("assets", []))
            if not asset:
                return None
            checksum_asset = _find_checksum_asset(release.get("assets", []))
            return {
                "version": latest,
                "current": current,
                "name": release.get("name") or f"Coupa Turbo Downloader {latest}",
                "download_url": asset["browser_download_url"],
                "asset_name": asset.get("name", "update.zip"),
                "checksum_url": checksum_asset.get("browser_download_url") if checksum_asset else None,
                "size": asset.get("size", 0),
                "release_notes": release.get("body", ""),
                "release_url": release.get("html_url", ""),
            }
    except Exception:
        # Startup updates are optional and must never prevent the app from opening.
        return None


def _checksum_from_manifest(manifest: str, asset_name: str) -> Optional[str]:
    for line in manifest.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and Path(parts[-1].lstrip("*\"")).name == Path(asset_name).name:
            return parts[0].lower()
    return None


async def download_update(
    download_url: str,
    dest_dir: str,
    asset_name: str = "update.zip",
    checksum_url: Optional[str] = None,
) -> str:
    """Download a release asset and verify it when a checksum manifest exists."""
    parsed = httpx.URL(download_url)
    if parsed.host not in {"github.com", "objects.githubusercontent.com"}:
        raise ValueError("Update URL is not a trusted GitHub host.")

    target_dir = Path(dest_dir).expanduser()
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(asset_name).name or "update.zip"
    target = target_dir / safe_name

    async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
        async with client.stream("GET", download_url) as response:
            response.raise_for_status()
            with target.open("wb") as output:
                async for chunk in response.aiter_bytes(1024 * 1024):
                    output.write(chunk)

        if checksum_url:
            checksum_response = await client.get(checksum_url)
            checksum_response.raise_for_status()
            expected = _checksum_from_manifest(checksum_response.text, safe_name)
            if expected:
                digest = hashlib.sha256(target.read_bytes()).hexdigest().lower()
                if digest != expected:
                    target.unlink(missing_ok=True)
                    raise ValueError("Downloaded update failed SHA-256 verification.")

    return str(target)


def _get_executable_path() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "main.py"))


def _safe_extract_update(package_path: Path, destination: Path) -> Path:
    """Extract a trusted release zip without allowing path traversal."""
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package_path) as archive:
        root = destination.resolve()
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if target != root and root not in target.parents:
                raise ValueError("Update archive contains an unsafe path.")
        archive.extractall(destination)
    return destination


def _find_update_payload(extracted: Path) -> Path:
    if sys.platform == "darwin":
        candidates = list(extracted.rglob("*.app"))
        if candidates:
            return candidates[0]
    elif sys.platform == "win32":
        portable_roots = [marker.parent for marker in extracted.rglob("portable-python.json")]
        if _python_portable_root() is not None and portable_roots:
            return portable_roots[0]
        candidates = [path for path in extracted.rglob("*.exe") if path.name.lower() != "uninstall.exe"]
        if candidates:
            return candidates[0]
    raise FileNotFoundError("The update package does not contain a compatible application.")


def prepare_update(package_path: str) -> str:
    """Extract a downloaded release and return its platform payload path."""
    package = Path(package_path).expanduser().resolve()
    if not package.is_file():
        raise FileNotFoundError(f"Update package not found: {package}")
    staging = Path(tempfile.mkdtemp(prefix="coupa-update-"))
    try:
        if zipfile.is_zipfile(package):
            extracted = _safe_extract_update(package, staging / "payload")
            return str(_find_update_payload(extracted))
        return str(package)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def apply_update_and_restart(new_payload: str) -> None:
    """Schedule replacement of the installed app/executable and restart it."""
    payload = Path(new_payload).expanduser().resolve()
    if not payload.exists():
        raise FileNotFoundError(f"Update payload not found: {payload}")

    if sys.platform == "darwin":
        current_app = Path(sys.executable).resolve().parents[2]
        if current_app.suffix != ".app":
            raise OSError("The macOS update can only be applied to an installed .app bundle.")
        target = current_app
        backup = target.with_name(f".{target.stem}.backup")
        script = "\n".join([
            "#!/bin/bash",
            "set -u",
            "sleep 2",
            f"target={shlex.quote(str(target))}",
            f"payload={shlex.quote(str(payload))}",
            f"backup={shlex.quote(str(backup))}",
            "rm -rf \"$backup\"",
            "mv \"$target\" \"$backup\"",
            "if ! /usr/bin/ditto \"$payload\" \"$target\"; then",
            "  mv \"$backup\" \"$target\"",
            "  exit 1",
            "fi",
            "rm -rf \"$backup\" \"$(dirname \"$payload\")\"",
            f"/usr/bin/open {shlex.quote(str(target))}",
            "rm -f \"$0\"",
            "",
        ])
        script_path = Path(tempfile.gettempdir()) / "coupa_updater.sh"
        script_path.write_text(script, encoding="utf-8")
        os.chmod(script_path, 0o755)
        subprocess.Popen(["/bin/bash", str(script_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return

    if sys.platform == "win32":
        portable_root = _python_portable_root()
        if portable_root is not None:
            if not (payload / "portable-python.json").is_file():
                raise OSError("The update is not a Python portable package.")
            target = portable_root
            backup = target.with_name(f".{target.name}.backup")
            launcher = target / "Start-CoupaTurbo.cmd"
            staging = payload.parent
            script = "\n".join([
                "@echo off",
                "setlocal",
                "cd /d %TEMP%",
                "timeout /t 2 /nobreak >nul",
                f"set \"payload={payload}\"",
                f"set \"target={target}\"",
                f"set \"backup={backup}\"",
                "if exist \"%backup%\" rmdir /S /Q \"%backup%\"",
                "move /Y \"%target%\" \"%backup%\" >nul",
                "if errorlevel 1 goto rollback",
                "robocopy \"%payload%\" \"%target%\" /E /COPY:DAT /R:2 /W:1 >nul",
                "if errorlevel 8 goto rollback",
                f"start \"\" \"{launcher}\"",
                "rmdir /S /Q \"%backup%\"",
                f"rmdir /S /Q \"{staging}\"",
                "del \"%~f0\"",
                "exit /b 0",
                ":rollback",
                "if exist \"%target%\" rmdir /S /Q \"%target%\"",
                "if exist \"%backup%\" move /Y \"%backup%\" \"%target%\" >nul",
                "exit /b 1",
                "",
            ])
            script_path = Path(tempfile.gettempdir()) / "coupa_python_portable_updater.bat"
            script_path.write_text(script, encoding="utf-8")
            subprocess.Popen(
                ["cmd", "/c", str(script_path)],
                cwd=tempfile.gettempdir(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "DETACHED_PROCESS", 0x00000008),
            )
            return

        current_exe = Path(sys.executable).resolve()
        script = "\n".join([
            "@echo off",
            "setlocal",
            "timeout /t 2 /nobreak >nul",
            f"set \"payload={payload}\"",
            f"set \"target={current_exe}\"",
            ":retry",
            "move /Y \"%payload%\" \"%target%\" >nul 2>&1",
            "if errorlevel 1 (timeout /t 1 /nobreak >nul & goto retry)",
            "start \"\" \"%target%\"",
            "del \"%~f0\"",
            "",
        ])
        script_path = Path(tempfile.gettempdir()) / "coupa_updater.bat"
        script_path.write_text(script, encoding="utf-8")
        subprocess.Popen(
            ["cmd", "/c", str(script_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0x00000008),
        )
        return

    raise OSError(f"Unsupported platform: {sys.platform}")
