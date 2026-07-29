"""Build a transparent Windows bundle using the official embedded Python runtime.

The resulting directory is portable: it does not require Python installation and
avoids the self-extracting PyInstaller bootloader used by the single-file build.
This script must run on Windows so uv resolves Windows wheels.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tomllib
import urllib.request
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DIST_DIR = PROJECT_ROOT / "dist"
BUNDLE_NAME = "CoupaTurboDownloader-python-portable"
BUNDLE_DIR = DIST_DIR / BUNDLE_NAME
RUNTIME_DIR = BUNDLE_DIR / "runtime"
APP_DIR = BUNDLE_DIR / "app"
PYTHON_VERSION = "3.12.10"
PYTHON_EMBED_URL = (
    f"https://www.python.org/ftp/python/{PYTHON_VERSION}/"
    f"python-{PYTHON_VERSION}-embed-amd64.zip"
)
PYTHON_EMBED_SHA256 = "4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_runtime(cache_path: Path) -> None:
    if cache_path.exists() and _sha256(cache_path) == PYTHON_EMBED_SHA256:
        return
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading official Python {PYTHON_VERSION} embedded runtime...")
    urllib.request.urlretrieve(PYTHON_EMBED_URL, cache_path)
    actual = _sha256(cache_path)
    if actual != PYTHON_EMBED_SHA256:
        cache_path.unlink(missing_ok=True)
        raise RuntimeError(
            f"Embedded Python checksum mismatch: expected {PYTHON_EMBED_SHA256}, got {actual}"
        )


def _project_dependencies() -> list[str]:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as stream:
        data = tomllib.load(stream)
    return list(data["project"]["dependencies"])


def _configure_runtime() -> None:
    pth_files = list(RUNTIME_DIR.glob("python*._pth"))
    if len(pth_files) != 1:
        raise RuntimeError("Could not identify the embedded Python ._pth file")
    pth_files[0].write_text(
        "python312.zip\n.\nLib\nLib\\site-packages\n..\\app\nimport site\n",
        encoding="utf-8",
    )
    (RUNTIME_DIR / "Lib" / "site-packages").mkdir(parents=True, exist_ok=True)


def _install_dependencies() -> None:
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError("uv is required to assemble the portable dependency directory")
    command = [
        uv,
        "pip",
        "install",
        "--target",
        str(RUNTIME_DIR / "Lib" / "site-packages"),
        "--python-version",
        "3.12",
        *_project_dependencies(),
    ]
    print("Installing Windows dependencies into the portable runtime...")
    subprocess.check_call(command, cwd=PROJECT_ROOT)


def _copy_application() -> None:
    shutil.copytree(
        PROJECT_ROOT / "src",
        APP_DIR / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    shutil.copy2(PROJECT_ROOT / "process_all_pos.py", APP_DIR / "process_all_pos.py")
    shutil.copy2(PROJECT_ROOT / ".version", APP_DIR / ".version")


def _write_launchers() -> None:
    (BUNDLE_DIR / "Start-CoupaTurbo.cmd").write_text(
        "@echo off\r\n"
        "setlocal\r\n"
        "set \"COUPA_PYTHON_PORTABLE=1\"\r\n"
        "cd /d \"%~dp0\"\r\n"
        "start \"Coupa Turbo Downloader\" \"%~dp0runtime\\pythonw.exe\" \"%~dp0app\\src\\main.py\"\r\n",
        encoding="ascii",
    )
    (BUNDLE_DIR / "Run-Diagnostics.cmd").write_text(
        "@echo off\r\n"
        "setlocal\r\n"
        "set \"COUPA_PYTHON_PORTABLE=1\"\r\n"
        "cd /d \"%~dp0\"\r\n"
        "\"%~dp0runtime\\python.exe\" -c \"import src.main, process_all_pos; print('Portable runtime OK')\"\r\n"
        "pause\r\n",
        encoding="ascii",
    )
    (BUNDLE_DIR / "portable-python.json").write_text(
        json.dumps(
            {
                "format": 1,
                "application": "CoupaTurboDownloader",
                "python": PYTHON_VERSION,
                "architecture": "x86_64",
                "automatic_update_check_default": False,
                "manual_updates": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (BUNDLE_DIR / "PORTABLE_README.txt").write_text(
        "Coupa Turbo Downloader - Python portable edition\n"
        "=================================================\n\n"
        "1. Extract the complete folder.\n"
        "2. Run Start-CoupaTurbo.cmd.\n"
        "3. Keep runtime/ and app/ beside the launcher.\n\n"
        "Python installation and administrator privileges are not required.\n"
        "The runtime/python.exe and runtime/pythonw.exe files come from the\n"
        "official Python Software Foundation embedded distribution.\n\n"
        "Automatic update checks are disabled by default in this edition.\n"
        "Use Settings > Updates > Check now for a manual verified update.\n"
        "Application data and downloads remain outside this folder.\n",
        encoding="utf-8",
    )


def _write_manifest() -> None:
    manifest = BUNDLE_DIR / "MANIFEST.sha256"
    lines = []
    for path in sorted(BUNDLE_DIR.rglob("*")):
        if path.is_file() and path != manifest:
            relative = path.relative_to(BUNDLE_DIR).as_posix()
            lines.append(f"{_sha256(path)}  {relative}")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _smoke_test() -> None:
    python = RUNTIME_DIR / "python.exe"
    subprocess.check_call(
        [
            str(python),
            "-c",
            (
                "import bs4, extract_msg, httpx, lxml, openpyxl, pandas, selenium, webview; "
                "import src.main, process_all_pos; "
                "print('Portable import smoke test passed')"
            ),
        ],
        cwd=BUNDLE_DIR,
    )


def build() -> Path:
    if not sys.platform.startswith("win"):
        raise SystemExit("[ERROR] The Python portable bundle must be built on Windows")

    shutil.rmtree(BUNDLE_DIR, ignore_errors=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    cache = PROJECT_ROOT / ".cache" / Path(PYTHON_EMBED_URL).name
    _download_runtime(cache)
    with zipfile.ZipFile(cache) as archive:
        archive.extractall(RUNTIME_DIR)
    _configure_runtime()
    _install_dependencies()
    _copy_application()
    _write_launchers()
    _smoke_test()
    _write_manifest()
    print(f"[OK] Python portable bundle created at {BUNDLE_DIR}")
    return BUNDLE_DIR


if __name__ == "__main__":
    build()
