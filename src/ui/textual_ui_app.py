"""
Premium Textual UI for CoupaDownloads.

Provides a modern, reactive terminal interface with real-time graphs,
system monitoring, and smooth animations.
"""

import time
import psutil
from datetime import datetime
from typing import Dict, List, Any, Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import Header, Footer, Static, DataTable, Label, Digits
from textual.reactive import reactive
from textual import work
from textual.message import Message

from src.core.communication_manager import CommunicationManager


class SystemMetrics(Static):
    """Widget to display CPU and Memory metrics."""
    
    cpu_percent = reactive(0.0)
    mem_percent = reactive(0.0)

    def render(self) -> str:
        cpu_color = "green" if self.cpu_percent < 60 else "yellow" if self.cpu_percent < 85 else "red"
        mem_color = "green" if self.mem_percent < 70 else "yellow" if self.mem_percent < 90 else "red"
        
        return (
            f"[bold cyan]SYSTEM HEALTH[/]\n"
            f"CPU: [{cpu_color}]{self.cpu_percent:>5.1f}%[/]\n"
            f"MEM: [{mem_color}]{self.mem_percent:>5.1f}%[/]"
        )

    def on_mount(self) -> None:
        self.set_interval(2.0, self.update_metrics)

    def update_metrics(self) -> None:
        self.cpu_percent = psutil.cpu_percent()
        self.mem_percent = psutil.virtual_memory().percent


class PerformanceGraph(Static):
    """A sparkline-style graph for POs/min."""
    
    history = reactive([])
    
    def render(self) -> str:
        if not self.history:
            return "[dim]No performance data...[/]"
            
        # Braille sparkline logic
        min_v = min(self.history)
        max_v = max(self.history)
        range_v = max_v - min_v or 1
        
        # Simple vertical blocks for now
        blocks = " ▂▃▄▅▆▇█"
        graph = ""
        for v in self.history[-30:]:
            idx = int((v - min_v) / range_v * (len(blocks) - 1))
            graph += blocks[idx]
            
        return f"[bold magenta]PERFORMANCE (POs/min)[/]\n[bold green]{graph}[/]"


class WorkerStatusGrid(Static):
    """Widget to display detailed worker status."""
    
    worker_entries = reactive([])

    def render(self) -> str:
        if not self.worker_entries:
            return "[dim]Waiting for workers...[/]"
        
        lines = ["[bold blue]WORKER STATUS[/]"]
        for w in self.worker_entries:
            wid = w.get("worker_id", "N/A")
            po = w.get("current_po", "Idle")
            status = w.get("status", "Idle")
            found = w.get("attachments_found", 0)
            downloaded = w.get("attachments_downloaded", 0)
            tasks_processed = w.get("tasks_processed", 0)
            tasks_failed = w.get("tasks_failed", 0)
            
            # Progress bar
            if found > 0:
                pct = int((downloaded / found) * 100)
                bar_filled = int(pct / 10)
                bar = "█" * bar_filled + "░" * (10 - bar_filled)
                progress = f"[{bar}] {downloaded}/{found}"
            else:
                progress = "[dim]No progress[/]"
                
            status_style = {
                "COMPLETED": "bold green",
                "SUCCESS": "bold green",
                "PROCESSING": "bold yellow",
                "STARTED": "bold yellow",
                "FAILED": "bold red",
                "ERROR": "bold red",
                "IDLE": "dim white",
            }.get(status.upper(), "white")
            
            efficiency_score = w.get("efficiency_score", 0.0)
            eff_color = "green" if efficiency_score > 80 else "yellow" if efficiency_score > 50 else "red"
            
            lines.append(
                f"{wid:<10} | {po:<12} | [{status_style}]{status:^10}[/] | "
                f"{progress} | [{eff_color}]{efficiency_score:>5.1f}%[/] | "
                f"TP:{tasks_processed} F:{tasks_failed}"
            )
            
        return "\n".join(lines)


class LogFeed(Static):
    """A scrolling log feed for recent activity."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logs: List[str] = []

    def set_logs(self, logs: List[str]) -> None:
        self.logs = logs
        self.refresh()

    def render(self) -> str:
        if not self.logs:
            return "[dim]Awaiting activity...[/]"
        return "[bold yellow]RECENT ACTIVITY[/]\n" + "\n".join(self.logs[-8:])


class CoupaTextualUI(App):
    """Main Textual Application for Coupa Downloads."""
    
    CSS = """
    Screen {
        background: #0f172a; /* Deep blue-black */
    }

    #main-container {
        layout: grid;
        grid-size: 2 2;
        grid-columns: 3fr 1fr;
        grid-rows: 1fr 12;
    }

    .panel {
        border: tall #1e293b;
        padding: 1;
        margin: 0;
        background: #1e293b 10%;
    }

    .panel:focus {
        border: tall #6366f1;
    }

    #worker-panel {
        column-span: 1;
        row-span: 1;
    }

    #sidebar {
        column-span: 1;
        row-span: 2;
        layout: vertical;
        background: #0f172a;
        border-left: solid #334155;
    }

    #log-panel {
        column-span: 1;
        row-span: 1;
    }

    #header-stats {
        height: 3;
        background: #1e293b;
        border-bottom: tall #6366f1;
        content-align: center middle;
        color: #e2e8f0;
    }

    .stat-label {
        color: #94a3b8;
        text-style: bold;
    }

    .stat-value {
        color: #22d3ee;
        text-style: bold;
    }

    PerformanceGraph {
        height: 8;
        margin-top: 1;
    }

    SystemMetrics {
        height: 6;
        margin-top: 1;
    }

    LogFeed {
        color: #cbd5e1;
    }
    """

    def __init__(self, comm_manager: CommunicationManager, total_pos: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.comm_manager = comm_manager
        self.total_pos = total_pos
        self.start_time = time.time()
        self.worker_data = []
        self.perf_history = []
        self.last_perf_update = 0
        self._recent_logs: List[str] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(id="header-stats")
        with Container(id="main-container"):
            with Container(id="worker-panel", classes="panel"):
                yield WorkerStatusGrid(id="worker-grid")
            with Container(id="sidebar", classes="panel"):
                yield SystemMetrics(id="metrics")
                yield PerformanceGraph(id="perf-graph")
            with Container(id="log-panel", classes="panel"):
                yield LogFeed(id="log-feed")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Coupa Downloads Premium"
        self.sub_title = "v2.0 Beta (Textual Edition)"
        self.set_interval(1.0, self.update_data)

    def update_data(self) -> None:
        """Poll metrics from communication manager and update UI."""
        try:
            # Drain all pending metrics and get current aggregated state
            metrics = self.comm_manager.get_metrics()
            agg = self.comm_manager.get_aggregated_metrics()
            
            # Update workers using persistent worker_states from manager
            worker_grid = self.query_one("#worker-grid", WorkerStatusGrid)
            worker_states = agg.get("workers_status", {})
            
            displayed_workers = []
            # Sort by worker_id (handle both int and str)
            def sort_key(k):
                if isinstance(k, int): return k
                if isinstance(k, str) and k.startswith('worker-'):
                    try: return int(k.split('-')[1])
                    except: return float('inf')
                return str(k)
            
            for wid in sorted(worker_states.keys(), key=sort_key):
                m = worker_states[wid]
                
                # Robust display ID generation
                display_id = str(wid)
                if isinstance(wid, int):
                    display_id = f"Worker {wid + 1}"
                elif isinstance(wid, str) and wid.startswith('worker-'):
                    try:
                        num = wid.split('-')[1]
                        display_id = f"Worker {num}"
                    except:
                        pass
                
                displayed_workers.append({
                    "worker_id": display_id,
                    "current_po": m.get("po_id", "Idle"),
                    "status": m.get("status", "Idle"),
                    "attachments_found": m.get("attachments_found", 0),
                    "attachments_downloaded": m.get("attachments_downloaded", 0),
                    "efficiency_score": m.get("efficiency_score", 0.0)
                })
            
            if displayed_workers:
                worker_grid.worker_entries = displayed_workers
            
            # Update logs from recent metrics (best-effort; keep UI alive on errors)
            try:
                log_feed = self.query_one("#log-feed", LogFeed)
                metric_source = metrics or agg.get("recent_metrics", [])
                new_logs = []
                for m in metric_source:
                    if m.get("message"):
                        timestamp = datetime.fromtimestamp(m.get("timestamp", time.time())).strftime("%H:%M:%S")
                        new_logs.append(f"[{timestamp}] {m['message']}")

                if new_logs:
                    # Avoid showing exact duplicates in the feed if they arrive closely
                    unique_new_logs = []
                    last_logs = self._recent_logs[-5:] if self._recent_logs else []
                    for nl in new_logs:
                        if nl not in last_logs and nl not in unique_new_logs:
                            unique_new_logs.append(nl)

                    if unique_new_logs:
                        self._recent_logs = self._recent_logs + unique_new_logs
                        if len(self._recent_logs) > 50:
                            self._recent_logs = self._recent_logs[-50:]
                        log_feed.set_logs(self._recent_logs)
            except Exception:
                pass
 

            # Update Efficiency / Perf Graph
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                # Use dynamic rate from tracker if available, else fallback to average
                throughput = agg.get("throughput", {})
                efficiency = throughput.get("dynamic_rate_per_minute", 0.0)
                
                # Fallback if metrics aren't populated yet
                if efficiency == 0.0:
                    processed_count = agg.get("total_successful", 0) + agg.get("total_failed", 0)
                    efficiency = (processed_count / elapsed) * 60
                
                if time.time() - self.last_perf_update >= 5:
                    perf_graph = self.query_one("#perf-graph", PerformanceGraph)
                    perf_graph.history = perf_graph.history + [efficiency]
                    if len(perf_graph.history) > 50:
                        perf_graph.history = perf_graph.history[-50:]
                    self.last_perf_update = time.time()

            # Update Header Stats
            header_stats = self.query_one("#header-stats", Static)
            total_goal = self.total_pos
            success = agg.get("total_successful", 0)
            failed = agg.get("total_failed", 0)
            processed = success + failed
            active = agg.get("active_count", 0)
            started = agg.get("total_seen", 0)
            
            runtime = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
            progress_display = f"{processed}/{total_goal}"
            if active > 0:
                progress_display = f"{processed}/{total_goal} (+{active} active)"
            elif started > processed:
                progress_display = f"{processed}/{total_goal} (+{started - processed} started)"
            
            header_stats.update(
                f" [stat-label]Runtime:[/] [stat-value]{runtime}[/] | "
                f"[stat-label]Progress:[/] [stat-value]{progress_display}[/] | "
                f"[stat-label]Success:[/] [stat-value]{success}[/] | "
                f"[stat-label]Failed:[/] [stat-value]{failed}[/] | "
                f"[stat-label]Efficiency:[/] [stat-value]{efficiency:.1f} POs/min[/]"
            )
        except Exception as e:
            # Silent catch to prevent UI freeze, but log for debugging
            import os
            try:
                with open(os.path.join(os.path.expanduser("~"), "textual_ui_error.log"), "a") as f:
                    f.write(f"[{datetime.now()}] UI update failed: {e}\n")
            except:
                pass

if __name__ == "__main__":
    # Test stub
    comm = CommunicationManager()
    app = CoupaTextualUI(comm)
    app.run()
