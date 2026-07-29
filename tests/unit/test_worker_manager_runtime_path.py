from src.lib.models import HeadlessConfiguration
from src.worker_manager import WorkerManager


def test_worker_manager_process_pos_uses_processing_session_path(monkeypatch):
    manager = WorkerManager(enable_parallel=True, max_workers=4)
    delegated = {}

    def _delegate(**kwargs):
        delegated.update(kwargs)
        return 3, 1, {"processing_mode": "parallel"}

    monkeypatch.setattr(manager, "process_parallel_with_session", _delegate)

    successful, failed, report = manager.process_pos(
        po_data_list=[{"po_number": "PO-1"}, {"po_number": "PO-2"}],
        hierarchy_cols=["Business Unit"],
        has_hierarchy_data=True,
        headless_config=HeadlessConfiguration(enabled=True),
        storage_manager="csv-handler",
        folder_manager="folder-manager",
        messenger="messenger",
        sqlite_db_path="/tmp/runtime.db",
        execution_mode="standard",
    )

    assert (successful, failed) == (3, 1)
    assert report["processing_mode"] == "parallel"
    assert delegated["po_data_list"][0]["po_number"] == "PO-1"
    assert delegated["csv_handler"] == "csv-handler"
    assert delegated["folder_hierarchy"] == "folder-manager"
    assert delegated["communication_manager"] == "messenger"
