from __future__ import annotations

from pathlib import Path

from src.persistence_manager import CSVManager
from src.config.app_config import Config, default_app_state_dir


class _FakeSQLiteHandler:
    def close(self) -> None:
        pass


class _FakeCSVHandler:
    def __init__(self, csv_path: Path, sqlite_db_path: str):
        self.csv_path = csv_path
        self.sqlite_db_path = sqlite_db_path
        self.sqlite_handler = _FakeSQLiteHandler()


def test_default_app_state_dir_uses_xdg_state_home(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state-home"))
    monkeypatch.setattr("src.config.app_config.os.name", "posix")
    monkeypatch.setattr("src.config.app_config.os.uname", lambda: type("UName", (), {"sysname": "Linux"})())

    state_dir = default_app_state_dir()

    assert state_dir == tmp_path / "state-home" / "CoupaDownloads"


def test_initialize_csv_handler_stores_sqlite_in_application_state(monkeypatch, tmp_path: Path):
    csv_input = tmp_path / "input.csv"
    csv_input.write_text("PO_NUMBER\nPO1\n", encoding="utf-8")

    state_dir = tmp_path / "app-state"
    Config.application_state_dir = state_dir
    Config.sqlite_session_dir = None

    def fake_create_handler(csv_path, enable_incremental_updates=True, sqlite_db_path=None, backup_dir=None):
        assert sqlite_db_path is not None
        Path(sqlite_db_path).parent.mkdir(parents=True, exist_ok=True)
        Path(sqlite_db_path).write_text("sqlite-placeholder", encoding="utf-8")
        return _FakeCSVHandler(csv_path, sqlite_db_path), "session-1"

    monkeypatch.setattr("src.persistence_manager.CSVHandler.create_handler", fake_create_handler)
    monkeypatch.setattr("src.persistence_manager.CSVHandler.get_backup_path", lambda csv_path: csv_input.parent / "backups" / "backup_session-1.csv")

    manager = CSVManager()
    session_id = manager.initialize_csv_handler(csv_input)

    assert session_id == "session-1"
    assert manager.sqlite_db_path is not None
    sqlite_path = Path(manager.sqlite_db_path)
    assert sqlite_path.parent == state_dir / "sqlite"
    assert sqlite_path.exists()

    manager.shutdown_csv_handler(cleanup_sqlite=True)

    assert sqlite_path.exists()


def test_initialize_csv_handler_honors_sqlite_session_dir_override(monkeypatch, tmp_path: Path):
    csv_input = tmp_path / "input.csv"
    csv_input.write_text("PO_NUMBER\nPO1\n", encoding="utf-8")

    override_dir = tmp_path / "custom-sqlite"
    Config.application_state_dir = tmp_path / "app-state"
    Config.sqlite_session_dir = override_dir

    def fake_create_handler(csv_path, enable_incremental_updates=True, sqlite_db_path=None, backup_dir=None):
        Path(sqlite_db_path).parent.mkdir(parents=True, exist_ok=True)
        Path(sqlite_db_path).write_text("sqlite-placeholder", encoding="utf-8")
        return _FakeCSVHandler(csv_path, sqlite_db_path), "session-2"

    monkeypatch.setattr("src.persistence_manager.CSVHandler.create_handler", fake_create_handler)
    monkeypatch.setattr("src.persistence_manager.CSVHandler.get_backup_path", lambda csv_path: csv_input.parent / "backups" / "backup_session-2.csv")

    manager = CSVManager()
    manager.initialize_csv_handler(csv_input)

    assert manager.sqlite_db_path is not None
    assert Path(manager.sqlite_db_path).parent == override_dir
