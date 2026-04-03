from src.core.communication_manager import CommunicationManager
from src.ui.textual_ui_app import CoupaTextualUI


def test_ui_prefers_runtime_resource_snapshot_over_local_psutil(monkeypatch):
    app = CoupaTextualUI(CommunicationManager(use_manager=False), total_pos=10)

    monkeypatch.setattr("src.ui.textual_ui_app.psutil.cpu_percent", lambda interval=None: 99.0)
    monkeypatch.setattr(
        "src.ui.textual_ui_app.psutil.virtual_memory",
        lambda: type("VM", (), {"percent": 99.0, "available": 1 * (1024 ** 3)})(),
    )

    cpu_percent, memory_percent, available_ram_gb = app._resolve_resource_metrics(
        {
            "cpu_percent": 18.0,
            "memory_percent": 42.0,
            "available_ram_gb": 7.5,
        }
    )

    assert (cpu_percent, memory_percent, available_ram_gb) == (18.0, 42.0, 7.5)
