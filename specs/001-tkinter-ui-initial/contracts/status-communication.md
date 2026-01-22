# Status Communication Contract

**Contract ID**: STATUS-UI-001
**Date**: 2025-11-12
**Type**: Communication Contract
**Components**: Core Process ↔ UI Process

## Overview

Defines the real-time communication mechanism between the download core processes and the UI for status updates and progress reporting.

## Communication Architecture

### Inter-Process Communication

**Mechanism**: `multiprocessing.Queue`
**Direction**: Core → UI (one-way)
**Purpose**: Real-time status updates without blocking operations

**Setup**:
```python
import multiprocessing as mp

# In core process
status_queue = mp.Queue()

# Pass to UI process
ui_process = mp.Process(target=launch_ui, args=(status_queue,))
ui_process.start()
```

## Message Format

### Status Message Structure

```python
StatusMessage = {
    "timestamp": str,      # ISO datetime: "2025-11-12T10:30:00Z"
    "level": str,          # "info" | "warning" | "error" | "success"
    "message": str,        # Human-readable text, max 200 chars
    "operation_id": str    # Optional UUID for grouping related messages
}
```

### Message Types

#### Operation Status Messages
- **Starting downloads**: `{"level": "info", "message": "Starting download operations..."}`
- **Download progress**: `{"level": "info", "message": "Processing batch 1 of 5"}`
- **Completion**: `{"level": "success", "message": "All downloads completed successfully"}`
- **Errors**: `{"level": "error", "message": "Failed to download file: connection timeout"}`

#### System Status Messages
- **Ready**: `{"level": "info", "message": "System ready"}`
- **Stopping**: `{"level": "warning", "message": "Stopping operations..."}`
- **Configuration loaded**: `{"level": "info", "message": "Configuration loaded from file"}`

## Interface Definition

### Status Publisher (Core Side)

**Function**: `publish_status(queue, level, message, operation_id=None)`
**Location**: Core process utilities

```python
def publish_status(queue: mp.Queue, level: str, message: str, operation_id: str = None) -> None:
    """Publish status message to UI queue.

    Args:
        queue: Multiprocessing queue for UI communication
        level: Message severity ("info", "warning", "error", "success")
        message: Human-readable status text
        operation_id: Optional operation identifier
    """
    if len(message) > 200:
        message = message[:197] + "..."

    status_msg = {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": message,
        "operation_id": operation_id
    }

    try:
        queue.put(status_msg, timeout=1)  # Non-blocking with timeout
    except:
        # Queue full or other error - silently drop message
        pass
```

### Status Consumer (UI Side)

**Class**: `StatusMonitor`
**Location**: `src/ui/main_window.py`

```python
class StatusMonitor:
    def __init__(self, queue: mp.Queue, status_callback: callable):
        self.queue = queue
        self.status_callback = status_callback
        self.monitoring = True

    def start_monitoring(self):
        """Start background monitoring thread."""
        thread = threading.Thread(target=self._monitor_loop, daemon=True)
        thread.start()

    def stop_monitoring(self):
        """Stop monitoring."""
        self.monitoring = False

    def _monitor_loop(self):
        """Monitor queue for status messages."""
        while self.monitoring:
            try:
                message = self.queue.get(timeout=1)
                self.status_callback(message)
            except queue.Empty:
                continue
```

## Error Handling

### Queue Communication Errors
- **Queue full**: Drop message silently (UI shouldn't block core operations)
- **Queue timeout**: Continue operation (temporary UI disconnection)
- **Invalid message format**: Log error but continue processing

### UI Responsiveness
- **Message processing**: Must complete within 100ms to avoid UI freezing
- **Queue backlog**: Drop oldest messages if queue grows beyond reasonable size
- **Thread safety**: All UI updates must be scheduled on main thread

## Performance Requirements

- **Message latency**: <1 second from core to UI display
- **Queue size**: Maximum 100 messages (drop oldest when exceeded)
- **Memory usage**: <10MB for message storage
- **CPU overhead**: <5% additional CPU usage in core process

## Testing Requirements

- **Message delivery**: All published messages reach UI within timeout
- **Message ordering**: Messages delivered in FIFO order
- **Error resilience**: System continues operating when UI is disconnected
- **Performance**: Status updates don't impact download throughput
- **Thread safety**: No race conditions in UI updates