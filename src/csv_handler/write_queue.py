"""Write queue implementation for thread-safe CSV operations."""

from __future__ import annotations

import threading
import time
import uuid
from datetime import datetime
from queue import Queue, Empty
from typing import Any, Dict, Optional

from .models import WriteOperation, QueueStatus


class WriteQueue:
    """Serialize write operations to avoid concurrent CSV access."""

    def __init__(self, csv_handler: Any, max_retries: int = 3, queue_size: int = 1000) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")

        self.csv_handler = csv_handler
        self.max_retries = max_retries
        self.queue: Queue[WriteOperation] = Queue(maxsize=queue_size)
        self._writer_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._status = QueueStatus()

    def submit_write(self, po_number: str, updates: Dict[str, Any]) -> str:
        """Submit a write operation to the queue."""
        operation_id = uuid.uuid4().hex
        operation = WriteOperation(
            operation_id=operation_id,
            po_number=po_number,
            updates=updates,
            timestamp=datetime.utcnow(),
            max_retries=self.max_retries,
        )

        self.queue.put(operation, block=True)
        with self._lock:
            self._status.pending += 1
            self._status.queue_size = self.queue.qsize()
            self._status.total_operations += 1

        return operation_id

    def start_writer_thread(self) -> None:
        """Start the background thread that processes write operations."""
        if self._writer_thread and self._writer_thread.is_alive():
            return

        self._stop_event.clear()
        self._writer_thread = threading.Thread(target=self._process_queue, name="CSVWriteQueue", daemon=True)
        self._writer_thread.start()
        with self._lock:
            self._status.writer_active = True

    def stop_writer_thread(self, timeout: float = 30.0) -> bool:
        """Signal the writer thread to stop and wait for completion."""
        if not self._writer_thread:
            return True

        self._stop_event.set()
        self.queue.put_nowait(
            WriteOperation(
                operation_id="__shutdown__",
                po_number="",
                updates={},
                timestamp=datetime.utcnow(),
                max_retries=0,
            )
        )
        self._writer_thread.join(timeout=timeout)
        stopped = not self._writer_thread.is_alive()
        self._writer_thread = None
        return stopped

    def get_queue_status(self) -> Dict[str, Any]:
        """Return current queue statistics."""
        with self._lock:
            snapshot = self._status.to_dict()
            snapshot['queue_size'] = self.queue.qsize()
            snapshot['pending'] = max(snapshot['pending'], self.queue.qsize())
            snapshot['writer_active'] = bool(self._writer_thread and self._writer_thread.is_alive())
        return snapshot

    def _process_queue(self) -> None:
        """Continuously process write operations in FIFO order."""
        while not self._stop_event.is_set():
            try:
                operation = self.queue.get(timeout=0.5)
            except Empty:
                continue

            if operation.operation_id == "__shutdown__":
                break

            success = self._execute_operation(operation)

            with self._lock:
                if success:
                    self._status.completed += 1
                else:
                    self._status.failed += 1
                self._status.pending = max(self._status.pending - 1, 0)
                self._status.queue_size = self.queue.qsize()
                self._status.last_write_time = datetime.utcnow()

        with self._lock:
            self._status.writer_active = False

    def _execute_operation(self, operation: WriteOperation) -> bool:
        """Execute a write operation with retry handling."""
        backoff_seconds = 0.5
        while True:
            try:
                self.csv_handler.update_record(operation.po_number, operation.updates)
                return True
            except Exception as exc:  # pragma: no cover - defensive logging
                operation.increment_retry(str(exc))
                if not operation.has_retries_left:
                    return False
                time.sleep(backoff_seconds)
                backoff_seconds *= 2
