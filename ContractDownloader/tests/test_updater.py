import json
import sys
import zipfile
from pathlib import Path

from src.engine import updater


def _portable_runtime(tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "ContractDownloader-python-portable"
    runtime = root / "runtime"
    runtime.mkdir(parents=True)
    executable = runtime / "pythonw.exe"
    executable.touch()
    (root / "contract-downloader.json").write_text(json.dumps({"format": 1}), encoding="utf-8")
    monkeypatch.setenv("COUPA_PYTHON_PORTABLE", "1")
    monkeypatch.setattr(sys, "executable", str(executable))
    monkeypatch.setattr(sys, "platform", "win32")
    return root


def test_python_portable_selects_matching_release_asset(tmp_path, monkeypatch):
    _portable_runtime(tmp_path, monkeypatch)
    assets = [
        {"name": "ContractDownloader-windows-x64.zip"},
        {"name": "ContractDownloader-windows-python-portable-x64.zip"},
    ]

    selected = updater._find_platform_asset(assets)

    assert selected["name"] == "ContractDownloader-windows-python-portable-x64.zip"


def test_python_portable_rejects_release_without_matching_edition(tmp_path, monkeypatch):
    _portable_runtime(tmp_path, monkeypatch)

    selected = updater._find_platform_asset([
        {"name": "ContractDownloader-windows-x64.zip"},
    ])

    assert selected is None


def test_regular_windows_build_does_not_select_python_portable(monkeypatch):
    monkeypatch.delenv("COUPA_PYTHON_PORTABLE", raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    assets = [
        {"name": "ContractDownloader-windows-python-portable-x64.zip"},
        {"name": "ContractDownloader-windows-x64.zip"},
    ]

    selected = updater._find_platform_asset(assets)

    assert selected["name"] == "ContractDownloader-windows-x64.zip"


def test_prepare_update_returns_portable_bundle_root(tmp_path, monkeypatch):
    _portable_runtime(tmp_path / "installed", monkeypatch)
    package = tmp_path / "update.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr(
            "ContractDownloader-python-portable/contract-downloader.json",
            '{"format": 1}',
        )
        archive.writestr(
            "ContractDownloader-python-portable/Start-ContractDownloader.cmd",
            "@echo off\n",
        )

    payload = Path(updater.prepare_update(str(package)))

    assert payload.name == "ContractDownloader-python-portable"
    assert (payload / "contract-downloader.json").is_file()
