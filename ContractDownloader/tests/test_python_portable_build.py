import json
from pathlib import Path

import build_python_portable as portable


def test_embedded_python_download_is_pinned():
    assert portable.PYTHON_EMBED_URL.startswith("https://www.python.org/ftp/python/")
    assert len(portable.PYTHON_EMBED_SHA256) == 64
    int(portable.PYTHON_EMBED_SHA256, 16)


def test_portable_dependencies_exclude_test_and_packaging_tools():
    dependencies = portable._project_dependencies()

    assert any(value.startswith("pywebview") for value in dependencies)
    assert any(value.startswith("truststore") for value in dependencies)
    assert not any(value.startswith("pytest") for value in dependencies)
    assert not any(value.startswith("pyinstaller") for value in dependencies)


def test_portable_launcher_uses_official_pythonw_and_manual_updates(monkeypatch, tmp_path):
    bundle = tmp_path / "portable"
    runtime = bundle / "runtime"
    app = bundle / "app"
    runtime.mkdir(parents=True)
    app.mkdir()
    monkeypatch.setattr(portable, "BUNDLE_DIR", bundle)
    monkeypatch.setattr(portable, "RUNTIME_DIR", runtime)
    monkeypatch.setattr(portable, "APP_DIR", app)

    portable._write_launchers()

    launcher = (bundle / "Start-ContractDownloader.cmd").read_text(encoding="ascii")
    python_launcher = (app / "launcher.py").read_text(encoding="utf-8")
    metadata = json.loads((bundle / "contract-downloader.json").read_text(encoding="utf-8"))
    assert "COUPA_PYTHON_PORTABLE=1" in launcher
    assert "Unblock-File" in launcher
    assert ".zone-unblocked" in launcher
    assert "runtime\\pythonw.exe" in launcher
    assert "Contract Downloader" in launcher
    assert "startup.log" in launcher
    diagnostics = (bundle / "ContractDownloader-Diagnostics.cmd").read_text(encoding="ascii")
    assert "find_spec" in diagnostics
    assert "import src.main" not in diagnostics
    assert (bundle / "LEIA-ME.txt").is_file()
    assert (bundle / "INSTRUCOES_CONTRACT_DOWNLOADER.md").is_file()
    assert "runpy.run_path" in python_launcher
    assert metadata["automatic_update_check_default"] is False
    assert metadata["manual_updates"] is True
