"""Interactive Textual UI for the PO download CLI."""
from __future__ import annotations

import threading
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Sequence

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Static, Tree
from textual.widgets.tree import TreeNode

__all__ = [
    "DownloadCLIController",
    "PODescriptor",
    "calculate_progress",
    "calculate_elapsed",
    "calculate_remaining",
    "calculate_eta",
    "update_status",
]


@dataclass
class PODescriptor:
    """Basic metadata required to render a PO in the UI."""

    po_number: str
    vendor: str = ""
    link: str = ""


@dataclass
class LogEntry:
    """Represents a single log entry for a PO."""

    timestamp: datetime
    message: str
    kind: str = "info"  # info | warning | error | result
    style: Optional[str] = None

    def formatted(self) -> Text:
        time_part = self.timestamp.strftime("%H:%M:%S")
        style = self.style or {
            "info": "",  # default terminal colour
            "warning": "yellow",
            "error": "red",
            "result": "bold cyan",
        }.get(self.kind, "")
        prefix_style = "dim"
        text = Text(f"[{time_part}] ", style=prefix_style)
        text.append(self.message, style=style)
        return text


STATUS_ICONS: Dict[str, tuple[str, str]] = {
    "COMPLETED": ("🟢", "green"),
    "IN_PROGRESS": ("🟡", "yellow"),
    "NOT_FOUND": ("🔴", "red"),
    "FAILED": ("🔴", "red"),
    "PO_NOT_FOUND": ("🔴", "red"),
    "NO_ATTACHMENTS": ("⚪", "bright_white"),
    "PENDING": ("🔵", "blue"),
    "PARTIAL": ("🟢", "green"),
}

SUMMARY_ORDER = [
    "COMPLETED",
    "IN_PROGRESS",
    "NOT_FOUND",
    "NO_ATTACHMENTS",
    "PENDING",
]
SUMMARY_LABELS = {
    "COMPLETED": "Completed",
    "IN_PROGRESS": "In Progress",
    "NOT_FOUND": "Not Found",
    "NO_ATTACHMENTS": "No Attach",
    "PENDING": "Pending",
}
SUMMARY_ICONS = {
    "COMPLETED": "🟢",
    "IN_PROGRESS": "🟡",
    "NOT_FOUND": "🔴",
    "NO_ATTACHMENTS": "⚪",
    "PENDING": "🔵",
}
TERMINAL_STATUS_GROUP = {"COMPLETED", "NO_ATTACHMENTS", "NOT_FOUND"}
TERMINAL_STATUSES = {
    "COMPLETED",
    "NO_ATTACHMENTS",
    "NOT_FOUND",
    "FAILED",
    "PO_NOT_FOUND",
    "PARTIAL",
}


@dataclass
class PORecord:
    """Internal mutable representation of a PO for progress tracking."""

    po_number: str
    vendor: str = ""
    link: str = ""
    status: str = "PENDING"
    logs: List[LogEntry] = field(default_factory=list)
    started_at: Optional[float] = None
    completed: bool = False

    def copy_for_view(self) -> "PORecordView":
        return PORecordView(
            po_number=self.po_number,
            vendor=self.vendor,
            link=self.link,
            status=self.status,
            logs=list(self.logs),
        )


@dataclass
class PORecordView:
    """Snapshot representation used by the UI renderer."""

    po_number: str
    vendor: str
    link: str
    status: str
    logs: List[LogEntry]


@dataclass
class ProgressSnapshot:
    """Immutable snapshot for rendering."""

    processed: int
    total: int
    percent: float
    elapsed: float
    remaining: float
    eta: Optional[datetime]
    status_summary: Dict[str, int]
    records: List[PORecordView]


class POProgressModel:
    """Thread-safe model holding PO progress information."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: Dict[str, PORecord] = {}
        self._status_counts: Counter[str] = Counter()
        self._start_time: Optional[float] = None
        self._durations = deque(maxlen=10)

    def initialise(self, descriptors: Sequence[PODescriptor]) -> None:
        with self._lock:
            self._records = {
                descriptor.po_number: PORecord(
                    po_number=descriptor.po_number,
                    vendor=descriptor.vendor,
                    link=descriptor.link,
                )
                for descriptor in descriptors
            }
            self._status_counts = Counter()
            for record in self._records.values():
                group = _status_group(record.status)
                self._status_counts[group] += 1
            self._start_time = time.monotonic()
            self._durations.clear()

    def ensure_metadata(self, po_number: str, vendor: str | None, link: str | None) -> None:
        with self._lock:
            record = self._records.get(po_number)
            if not record:
                record = PORecord(po_number=po_number)
                self._records[po_number] = record
                self._status_counts[_status_group("PENDING")] += 1
            if vendor:
                record.vendor = vendor
            if link:
                record.link = link

    def start_po(self, po_number: str) -> None:
        self.ensure_metadata(po_number, None, None)
        with self._lock:
            record = self._records[po_number]
            if record.started_at is None:
                record.started_at = time.monotonic()
            _apply_status_change(self, po_number, "IN_PROGRESS")

    def append_log(
        self,
        po_number: str,
        message: str,
        kind: str = "info",
        *,
        style: Optional[str] = None,
    ) -> None:
        self.ensure_metadata(po_number, None, None)
        entry = LogEntry(timestamp=datetime.now(), message=message, kind=kind, style=style)
        with self._lock:
            self._records[po_number].logs.append(entry)

    def complete_po(self, po_number: str, status: str) -> None:
        self.ensure_metadata(po_number, None, None)
        with self._lock:
            record = self._records[po_number]
            if record.started_at is not None:
                duration = max(time.monotonic() - record.started_at, 0.0)
                if duration > 0:
                    self._durations.append(duration)
            record.started_at = None
            record.completed = True
            _apply_status_change(self, po_number, status)
            result_style = _result_log_style(status)
            record.logs.append(
                LogEntry(
                    timestamp=datetime.now(),
                    message=f"Result: {status.replace('_', ' ').title()}",
                    kind="result",
                    style=result_style,
                )
            )

    def snapshot(self) -> ProgressSnapshot:
        with self._lock:
            total = len(self._records)
            processed = sum(
                self._status_counts.get(group, 0)
                for group in TERMINAL_STATUS_GROUP
            )
            percent = calculate_progress(processed, total)[2]
            elapsed = calculate_elapsed(self._start_time)
            remaining = calculate_remaining(
                self._start_time,
                processed,
                total,
                list(self._durations),
            )
            eta = calculate_eta(datetime.now(), remaining) if remaining > 0 else None
            summary = {key: self._status_counts.get(key, 0) for key in SUMMARY_ORDER}
            records = [record.copy_for_view() for record in self._records.values()]
        return ProgressSnapshot(
            processed=processed,
            total=total,
            percent=percent,
            elapsed=elapsed,
            remaining=remaining,
            eta=eta,
            status_summary=summary,
            records=records,
        )

    def status_counts(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._status_counts)


def _status_group(status: str) -> str:
    status_upper = (status or "PENDING").upper()
    if status_upper in {"FAILED", "PO_NOT_FOUND", "NOT_FOUND"}:
        return "NOT_FOUND"
    if status_upper in {"COMPLETED", "PARTIAL"}:
        return "COMPLETED"
    if status_upper == "NO_ATTACHMENTS":
        return "NO_ATTACHMENTS"
    if status_upper == "IN_PROGRESS":
        return "IN_PROGRESS"
    if status_upper == "PENDING":
        return "PENDING"
    return status_upper


def _apply_status_change(model: POProgressModel, po_number: str, new_status: str) -> None:
    record = model._records[po_number]
    old_group = _status_group(record.status)
    new_group = _status_group(new_status)
    if old_group != new_group:
        model._status_counts[old_group] -= 1
        if model._status_counts[old_group] < 0:
            model._status_counts[old_group] = 0
        model._status_counts[new_group] += 1
    record.status = new_status.upper()


def _result_log_style(status: str) -> str:
    status_upper = (status or "PENDING").upper()
    if status_upper in {"COMPLETED"}:
        return "bold green"
    if status_upper in {"PARTIAL", "IN_PROGRESS"}:
        return "bold yellow"
    if status_upper == "NO_ATTACHMENTS":
        return "bold bright_white"
    if status_upper in {"NOT_FOUND", "FAILED", "PO_NOT_FOUND"}:
        return "bold red"
    if status_upper == "PENDING":
        return "bold blue"
    return "bold cyan"


# Public helper functions requested in the specification ---------------------------------------

def update_status(model: POProgressModel, po_id: str, new_status: str) -> None:
    """Update counters and the individual status for a PO."""
    with model._lock:
        if po_id not in model._records:
            model._records[po_id] = PORecord(po_number=po_id)
            model._status_counts[_status_group("PENDING")] += 1
        _apply_status_change(model, po_id, new_status)


def calculate_progress(processed: int, total: int) -> tuple[int, int, float]:
    """Return processed count, total count and percentage."""
    if total <= 0:
        return 0, 0, 0.0
    percent = (processed / total) * 100 if total else 0.0
    return processed, total, percent


def calculate_elapsed(start_time: Optional[float]) -> float:
    """Return elapsed time in seconds from the provided start time."""
    if not start_time:
        return 0.0
    return max(time.monotonic() - start_time, 0.0)


def calculate_remaining(
    start_time: Optional[float],
    processed: int,
    total: int,
    samples: Optional[Sequence[float]] = None,
) -> float:
    """Estimate remaining seconds using moving average when available."""
    if not start_time or total <= 0:
        return 0.0
    remaining_units = max(total - processed, 0)
    if remaining_units <= 0:
        return 0.0
    elapsed = calculate_elapsed(start_time)
    average: Optional[float] = None
    if samples:
        valid_samples = [sample for sample in samples if sample > 0]
        if valid_samples:
            average = sum(valid_samples) / len(valid_samples)
    if average is None:
        if processed <= 0:
            return 0.0
        average = elapsed / processed if processed else 0.0
    return max(average * remaining_units, 0.0)


def calculate_eta(now: datetime, remaining_seconds: float) -> datetime:
    """Return the estimated completion datetime based on remaining seconds."""
    return now + timedelta(seconds=max(remaining_seconds, 0.0))


# Rendering helpers ----------------------------------------------------------------------------

class HeaderRenderer:
    """Renderer for the fixed header component."""

    @staticmethod
    def render(snapshot: ProgressSnapshot) -> Panel:
        processed, total, percent = snapshot.processed, snapshot.total, snapshot.percent
        elapsed_str = _format_duration(snapshot.elapsed)
        remaining_str = _format_duration(snapshot.remaining)
        eta_str = snapshot.eta.strftime("%Y-%m-%d %H:%M:%S") if snapshot.eta else "--"
        progress_line = f"Processed: {processed}/{total} ({percent:.1f}%)"

        summary_line = "Status: " + " | ".join(
            f"{SUMMARY_ICONS[key]} {snapshot.status_summary.get(key, 0)} {SUMMARY_LABELS[key]}"
            for key in SUMMARY_ORDER
        )

        table = Table.grid(padding=(0, 2))
        table.add_row(progress_line, f"Elapsed: {elapsed_str}", f"Remaining: {remaining_str}", f"ETA: {eta_str}")
        table.add_row(summary_line)
        return Panel(table, title="PO Download Progress", border_style="cyan", padding=(1, 2))


class POListRenderer:
    """Renderer for the collapsible PO list."""

    @staticmethod
    def build_label(record: PORecordView) -> Text:
        icon, colour = STATUS_ICONS.get(record.status, ("🔵", "blue"))
        status_text = record.status.replace("_", " ").title()
        text = Text()
        text.append(f"{icon} ")
        text.append(f"PO {record.po_number}", style="bold")
        text.append(" | ")
        text.append(status_text, style=colour)
        if record.vendor:
            text.append(" | Vendor: ")
            text.append(record.vendor, style="italic")
        if record.link:
            text.append(" | Link: ")
            text.append(record.link, style="underline blue")
        return text


class LogRenderer:
    """Renderer for log entries."""

    @staticmethod
    def build(entry: LogEntry) -> Text:
        return entry.formatted()


class HeaderView(Static):
    """Static widget that displays the header panel."""

    def update_from_snapshot(self, snapshot: ProgressSnapshot) -> None:
        self.update(HeaderRenderer.render(snapshot))


class POListView(Tree[None]):
    """Tree widget showing each PO with collapsible logs."""

    def __init__(self) -> None:
        super().__init__("Purchase Orders")
        self.show_root = False
        self.show_guides = True
        self._nodes: Dict[str, TreeNode] = {}

    def update_from_snapshot(self, snapshot: ProgressSnapshot) -> None:
        desired = {record.po_number for record in snapshot.records}
        # Remove nodes that are no longer present
        for po_number in list(self._nodes.keys()):
            if po_number not in desired:
                node = self._nodes.pop(po_number)
                node.remove()

        # Update / insert nodes
        for record in snapshot.records:
            node = self._nodes.get(record.po_number)
            label = POListRenderer.build_label(record)
            if node is None:
                node = self.root.add(label, data=None)
                node.allow_expand = True
                self._nodes[record.po_number] = node
            else:
                node.set_label(label)
            was_expanded = node.is_expanded
            node.remove_children()
            for log_entry in record.logs:
                log_node = node.add(LogRenderer.build(log_entry))
                log_node.allow_expand = False
            if was_expanded:
                node.expand()


class DownloadInteractiveApp(App[None]):
    """Textual application responsible for rendering the interactive CLI."""

    CSS = """
    Screen {
        layout: vertical;
        background: $surface;
        color: $text;
    }

    #layout {
        padding: 1 2;
        height: 100%;
        background: transparent;
    }

    #header {
        margin-bottom: 1;
        padding: 1 2;
        background: $boost;
        border: round $accent;
    }

    #po-tree {
        height: 1fr;
        padding: 0 0 1 0;
    }

    Tree > .tree--label {
        text-style: bold;
    }

    Tree > .tree--guides {
        color: $accent;
    }
    """

    BINDINGS = [Binding("q", "quit", "Quit", show=True)]

    def __init__(self, model: POProgressModel) -> None:
        super().__init__()
        self._model = model
        self._startup_event = threading.Event()

    def compose(self) -> ComposeResult:
        header = HeaderView()
        header.id = "header"
        tree = POListView()
        tree.id = "po-tree"
        container = Vertical(header, tree)
        container.id = "layout"
        yield container

    async def on_mount(self) -> None:
        self._startup_event.set()
        await self.refresh_from_model()

    async def refresh_from_model(self) -> None:
        snapshot = self._model.snapshot()
        header = self.query_one("#header", HeaderView)
        tree = self.query_one("#po-tree", POListView)
        header.update_from_snapshot(snapshot)
        tree.update_from_snapshot(snapshot)

    def render_snapshot(self, snapshot: ProgressSnapshot) -> None:
        header = self.query_one("#header", HeaderView)
        tree = self.query_one("#po-tree", POListView)
        header.update_from_snapshot(snapshot)
        tree.update_from_snapshot(snapshot)

    def wait_until_ready(self, timeout: float = 5.0) -> bool:
        return self._startup_event.wait(timeout=timeout)


class DownloadCLIController:
    """Facade used by the processing pipeline to communicate with the UI."""

    def __init__(self) -> None:
        self._model = POProgressModel()
        self._app: Optional[DownloadInteractiveApp] = None
        self._thread: Optional[threading.Thread] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._worker_error: Optional[BaseException] = None
        self._shutdown_event = threading.Event()
        self._enabled = False

    def start(self, descriptors: Sequence[PODescriptor]) -> None:
        if self._enabled:
            return
        self._model.initialise(descriptors)
        app = DownloadInteractiveApp(self._model)
        self._app = app
        self._worker_error = None
        self._shutdown_event.clear()
        thread = threading.Thread(target=app.run, kwargs={"headless": False}, daemon=True)
        thread.start()
        if not app.wait_until_ready():
            raise RuntimeError("Interactive UI failed to start in time.")
        self._thread = thread
        self._enabled = True
        self.refresh()

    def refresh(self) -> None:
        if not self._enabled or not self._app:
            return
        snapshot = self._model.snapshot()
        try:
            self._app.call_from_thread(self._app.render_snapshot, snapshot)
        except RuntimeError:
            # App thread is already shutting down; ignore late refreshes.
            pass

    def stop(self) -> None:
        if not self._enabled:
            return
        self._shutdown_event.set()
        if self._app:
            try:
                self._app.call_from_thread(self._app.exit)
            except RuntimeError:
                pass
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)
            self._worker_thread = None
        self._enabled = False
        self._app = None

    def po_started(self, descriptor: PODescriptor) -> None:
        if not self._enabled:
            return
        self._model.ensure_metadata(descriptor.po_number, descriptor.vendor, descriptor.link)
        self._model.start_po(descriptor.po_number)
        self.refresh()

    def log(
        self,
        po_number: str,
        message: str,
        level: str = "info",
        *,
        style: Optional[str] = None,
    ) -> None:
        if not self._enabled:
            return
        self._model.append_log(po_number, message, kind=level, style=style)
        self.refresh()

    def po_completed(self, po_number: str, status: str) -> None:
        if not self._enabled:
            return
        self._model.complete_po(po_number, status)
        self.refresh()

    def update_metadata(self, po_number: str, vendor: Optional[str], link: Optional[str]) -> None:
        if not self._enabled:
            return
        self._model.ensure_metadata(po_number, vendor, link)
        self.refresh()

    # Foreground session orchestration -------------------------------------------------------

    def run_with_worker(
        self,
        descriptors: Sequence[PODescriptor],
        worker: Callable[["DownloadCLIController"], None],
        *,
        headless: bool = False,
    ) -> None:
        """Run the Textual app on the current thread and execute ``worker`` in background.

        Args:
            descriptors: PO metadata used to seed the progress model.
            worker: Callable that receives this controller instance and performs
                the processing pipeline. The callable may call ``stop`` to end
                early. Any exception raised will be re-raised after the UI exits.
            headless: Forwarded to ``App.run`` for testing scenarios.
        """

        if self._enabled:
            raise RuntimeError("Interactive UI session already running")

        self._model.initialise(descriptors)
        app = DownloadInteractiveApp(self._model)
        self._app = app
        self._enabled = True
        self._worker_error = None
        self._shutdown_event.clear()

        def worker_wrapper() -> None:
            app_ref = self._app
            try:
                if app_ref and not app_ref.wait_until_ready(timeout=10.0):
                    raise RuntimeError("Interactive UI failed to start in time.")
                worker(self)
            except BaseException as exc:  # noqa: BLE001 - need to propagate base exceptions
                self._worker_error = exc
            finally:
                self._shutdown_event.set()
                if self._app:
                    try:
                        self._app.call_from_thread(self._app.exit)
                    except RuntimeError:
                        pass

        worker_thread = threading.Thread(
            target=worker_wrapper,
            name="download-cli-worker",
            daemon=True,
        )
        self._worker_thread = worker_thread
        worker_thread.start()

        try:
            app.run(headless=headless)
        finally:
            self._shutdown_event.set()
            self._enabled = False
            self._app = None
            if self._worker_thread:
                self._worker_thread.join()
                self._worker_thread = None
        if self._worker_error:
            error = self._worker_error
            self._worker_error = None
            raise error

    def should_stop(self) -> bool:
        """Indicate whether the controller has been asked to shut down."""

        return self._shutdown_event.is_set()


# Utility helpers ------------------------------------------------------------------------------

def _format_duration(seconds: float) -> str:
    if seconds <= 0:
        return "--:--"
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
