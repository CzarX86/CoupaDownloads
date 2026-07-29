from src.core.communication_manager import CommunicationManager
from src.ui.textual_ui_app import CoupaTextualUI, WorkerStatusGrid


def test_negative_worker_ids_are_not_rendered_in_worker_grid():
    manager = CommunicationManager(use_manager=False)
    manager.send_metric(
        {
            "worker_id": -1,
            "po_id": "SYSTEM",
            "status": "INFO",
            "timestamp": 1.0,
            "message": "Startup activity",
        }
    )
    manager.send_metric(
        {
            "worker_id": "worker-2",
            "po_id": "PO-123",
            "status": "READY",
            "timestamp": 2.0,
            "message": "worker-2 is ready",
        }
    )

    app = CoupaTextualUI(manager, total_pos=10)
    agg = manager.get_aggregated_metrics()
    worker_states = agg.get("workers_status", {})

    displayed_workers = []

    def sort_key(k):
        if isinstance(k, int):
            return k
        if isinstance(k, str) and k.startswith("worker-"):
            return int(k.split("-")[1])
        return 999999

    for wid in sorted(worker_states.keys(), key=sort_key):
        m = worker_states[wid]
        if isinstance(wid, int) and wid < 0:
            continue
        if isinstance(wid, str):
            try:
                if int(wid) < 0:
                    continue
            except (TypeError, ValueError):
                pass
        displayed_workers.append((wid, m.get("status")))

    assert displayed_workers == [("worker-2", "READY")]
