from src.core.communication_manager import CommunicationManager


def test_duplicate_worker_snapshots_are_coalesced_in_recent_metrics():
    manager = CommunicationManager(use_manager=False)

    payload = {
        "worker_id": "worker-1",
        "po_id": "PO-1",
        "status": "PROCESSING",
        "timestamp": 1.0,
        "attachments_found": 3,
        "attachments_downloaded": 1,
        "message": "Downloading attachment 1/3",
    }

    manager.send_metric(payload)
    manager.send_metric(dict(payload, timestamp=2.0))

    aggregated = manager.get_aggregated_metrics()

    assert aggregated["workers_status"]["worker-1"]["status"] == "PROCESSING"
    assert len(aggregated["recent_metrics"]) == 1


def test_system_activity_does_not_pollute_worker_states():
    manager = CommunicationManager(use_manager=False)

    manager.publish_activity("Scaled up to 2 workers", status="INFO", timestamp=5.0)
    manager.send_metric(
        {
            "worker_id": "worker-2",
            "po_id": "SYSTEM",
            "status": "READY",
            "timestamp": 6.0,
            "message": "worker-2 is ready",
        }
    )

    aggregated = manager.get_aggregated_metrics()
    recent_messages = [item.get("message") for item in aggregated["recent_metrics"]]

    assert -1 not in aggregated["workers_status"]
    assert "Scaled up to 2 workers" in recent_messages
    assert "worker-2" in aggregated["workers_status"]


def test_resource_snapshots_update_resources_without_flooding_recent_metrics():
    manager = CommunicationManager(use_manager=False)

    manager.send_metric(
        {
            "status": "RESOURCE",
            "timestamp": 7.0,
            "message": "Resource snapshot updated",
            "resource_snapshot": {
                "cpu_percent": 32.0,
                "memory_percent": 48.0,
                "available_ram_gb": 6.4,
                "worker_count": 2,
                "target_worker_count": 4,
                "autoscaling_enabled": True,
                "pending_tasks": 1,
                "processing_tasks": 2,
            },
        }
    )

    aggregated = manager.get_aggregated_metrics()

    assert aggregated["resources"]["cpu_percent"] == 32.0
    assert aggregated["recent_metrics"] == []
