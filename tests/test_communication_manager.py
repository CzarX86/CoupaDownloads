from src.core.communication_manager import CommunicationManager
from src.core.status import StatusLevel
from src.main import MainApp


def test_run_state_transitions_are_persisted() -> None:
    manager = CommunicationManager(use_manager=False)

    manager.set_run_state("running", summary={"processed": 0}, timestamp=10.0)
    manager.set_run_state("finalizing", summary={"processed": 3}, timestamp=20.0)
    manager.set_run_state("completed", summary={"processed": 3}, timestamp=30.0)

    run_state = manager.get_run_state()

    assert run_state["state"] == "completed"
    assert run_state["started_at"] == 10.0
    assert run_state["finished_at"] == 30.0
    assert run_state["summary"]["processed"] == 3


def test_terminal_po_status_is_not_reopened_by_late_progress_metric() -> None:
    manager = CommunicationManager(use_manager=False)

    manager.send_metric(
        {
            "worker_id": 1,
            "po_id": "PO-1",
            "status": "COMPLETED",
            "timestamp": 1.0,
        }
    )
    manager.get_aggregated_metrics()

    manager.send_metric(
        {
            "worker_id": 1,
            "po_id": "PO-1",
            "status": "PROCESSING",
            "timestamp": 2.0,
        }
    )
    aggregated = manager.get_aggregated_metrics()

    assert aggregated["total_successful"] == 1
    assert aggregated["active_count"] == 0
    assert aggregated["workers_status"][1]["status"] == "COMPLETED"


def test_publish_activity_is_available_in_recent_metrics() -> None:
    manager = CommunicationManager(use_manager=False)

    manager.publish_activity("Startup: validating PO entries", status="INFO", timestamp=5.0)
    manager.get_metrics()
    aggregated = manager.get_aggregated_metrics()

    recent_messages = [item.get("message") for item in aggregated["recent_metrics"]]
    assert "Startup: validating PO entries" in recent_messages


def test_main_app_forwards_telemetry_status_to_recent_activity() -> None:
    app = MainApp()
    app.communication_manager = CommunicationManager(use_manager=False)

    app._forward_status_to_recent_activity(
        type(
            "StatusStub",
            (),
            {
                "message": "Startup: locating input workbook",
                "level": StatusLevel.INFO,
                "timestamp": type("TimestampStub", (), {"timestamp": staticmethod(lambda: 12.0)})(),
                "operation_id": None,
                "progress": None,
            },
        )()
    )

    app.communication_manager.get_metrics()
    aggregated = app.communication_manager.get_aggregated_metrics()
    recent_messages = [item.get("message") for item in aggregated["recent_metrics"]]
    assert "Startup: locating input workbook" in recent_messages
