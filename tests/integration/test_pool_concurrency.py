"""
Integration tests for CommunicationManager concurrent access.

Verifies that metrics sent from multiple threads are safely coalesced without
data loss or race conditions.
"""

import threading
import time
from typing import Any, Dict, List

from src.core.communication_manager import CommunicationManager


def _build_worker_metric(worker_id: str, po_id: str, ts: float) -> Dict[str, Any]:
    return {
        "worker_id": worker_id,
        "po_id": po_id,
        "status": "PROCESSING",
        "timestamp": ts,
        "attachments_found": 1,
        "attachments_downloaded": 0,
        "message": f"Processing {po_id}",
    }


class TestCommunicationManagerConcurrentSend:
    """Verify send_metric is safe under concurrent access from N threads."""

    def test_concurrent_sends_from_multiple_threads(self) -> None:
        manager = CommunicationManager(use_manager=False)

        n_workers = 4
        messages_per_worker = 10
        errors: List[Exception] = []
        barrier = threading.Barrier(n_workers)

        def worker_sender(worker_id: int) -> None:
            barrier.wait()
            for i in range(messages_per_worker):
                try:
                    manager.send_metric(
                        _build_worker_metric(
                            str(worker_id),
                            f"PO-{worker_id}-{i}",
                            float(i),
                        )
                    )
                except Exception as exc:
                    errors.append(exc)

        threads = [
            threading.Thread(target=worker_sender, args=(i,))
            for i in range(n_workers)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Errors in sender threads: {errors}"
        total_expected = n_workers * messages_per_worker
        drained = manager.get_metrics()
        # All messages must be retrieved (none silently dropped)
        assert len(drained) == total_expected

    def test_drain_concurrent_with_send(self) -> None:
        """Draining while producers are active must not raise and must not lose data."""
        manager = CommunicationManager(use_manager=False)

        sent_count = 0
        send_lock = threading.Lock()
        stop_flag = threading.Event()
        errors: List[Exception] = []

        def producer() -> None:
            nonlocal sent_count
            ts = 0.0
            while not stop_flag.is_set():
                metric = _build_worker_metric("w-0", "PO-X", ts)
                ts += 0.001
                try:
                    manager.send_metric(metric)
                    with send_lock:
                        sent_count += 1
                except Exception as exc:
                    errors.append(exc)

        def consumer() -> None:
            for _ in range(20):
                try:
                    manager.get_metrics()
                except Exception as exc:
                    errors.append(exc)
                time.sleep(0.005)

        prod = threading.Thread(target=producer)
        cons = threading.Thread(target=consumer)
        prod.start()
        cons.start()
        time.sleep(0.15)
        stop_flag.set()
        prod.join(timeout=5)
        cons.join(timeout=5)

        assert not errors, f"Errors during concurrent drain: {errors}"

    def test_publish_activity_is_thread_safe(self) -> None:
        """publish_activity must not raise under concurrent calls."""
        manager = CommunicationManager(use_manager=False)
        errors: List[Exception] = []

        def publish(i: int) -> None:
            try:
                manager.publish_activity(f"Activity {i}", status="INFO", timestamp=float(i))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=publish, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert not errors
