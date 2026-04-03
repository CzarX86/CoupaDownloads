"""
Premium Textual UI for CoupaDownloads.

Provides a modern, reactive terminal interface with real-time graphs,
system monitoring, and smooth animations.
"""

import os
import time
import psutil
from datetime import datetime
from typing import Dict, List, Any, Optional

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer, Static, RichLog
from textual.reactive import reactive
from textual.binding import Binding

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

    def update_snapshot(self, *, cpu_percent: float, mem_percent: float) -> None:
        """Apply the latest resource snapshot already collected by the runtime."""
        self.cpu_percent = cpu_percent
        self.mem_percent = mem_percent


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
    message_override = reactive("")

    def watch_worker_entries(self) -> None:
        """Force a layout pass when the number of rendered lines changes."""
        self.refresh(layout=True)

    def watch_message_override(self) -> None:
        """Ensure override messages become visible without waiting for resize."""
        self.refresh(layout=True)

    def render(self) -> str:
        if self.message_override:
            return self.message_override
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
                "STARTING": "bold yellow",
                "FAILED": "bold red",
                "ERROR": "bold red",
                "IDLE": "dim white",
                "READY": "dim white",
            }.get(status.upper(), "white")
            
            efficiency_score = w.get("efficiency_score", 0.0)
            eff_color = "green" if efficiency_score > 80 else "yellow" if efficiency_score > 50 else "red"
            
            lines.append(
                f"{wid:<10} | {po:<12} | [{status_style}]{status:^10}[/] | "
                f"{progress} | [{eff_color}]{efficiency_score:>5.1f}%[/] | "
                f"TP:{tasks_processed} F:{tasks_failed}"
            )

            # Per-file sub-rows — shown when the folder watcher has state
            file_downloads = w.get("file_downloads") or []
            for idx, fd in enumerate(file_downloads):
                is_last = idx == len(file_downloads) - 1
                branch = "└─" if is_last else "├─"
                raw_name = fd.get("filename") or f"attachment_{idx + 1}"
                name = raw_name if len(raw_name) <= 32 else raw_name[:29] + "..."
                state = fd.get("state", "found")
                bytes_done = fd.get("bytes_done")
                error_reason = fd.get("error_reason") or ""

                # Build a 10-segment bar.
                # For downloading: bytes are capped at 10 MB for display
                # (total size is unknown for browser-managed downloads).
                # For done: full bar. For queued: empty bar.
                _BAR_LEN = 10
                _MAX_BYTES = 10 * 1024 * 1024  # 10 MB cap

                if state == "done":
                    bar = "█" * _BAR_LEN
                    sub = f"   {branch} [green]✓[/] {name}  [green][{bar}][/]"
                elif state == "failed":
                    reason_text = f"  {error_reason[:40]}" if error_reason else ""
                    sub = f"   {branch} [red]✗[/] {name}[red]{reason_text}[/]"
                elif state == "downloading":
                    if bytes_done is not None:
                        filled = int(min(bytes_done / _MAX_BYTES, 1.0) * _BAR_LEN)
                        # Always show at least 1 filled segment so the bar looks active
                        filled = max(filled, 1)
                        bar = "█" * filled + "░" * (_BAR_LEN - filled)
                        if bytes_done >= 1_048_576:
                            size_str = f"{bytes_done / 1_048_576:.1f} MB"
                        elif bytes_done >= 1024:
                            size_str = f"{bytes_done / 1024:.0f} KB"
                        else:
                            size_str = f"{bytes_done} B"
                        sub = f"   {branch} [yellow]↓[/] {name}  [yellow][{bar}] {size_str}[/]"
                    else:
                        bar = "░" * _BAR_LEN
                        sub = f"   {branch} [yellow]↓[/] {name}  [yellow][{bar}] downloading\u2026[/]"
                else:  # found / queued
                    bar = "░" * _BAR_LEN
                    sub = f"   {branch} {name}  [dim][{bar}] queued[/]"

                lines.append(sub)
            
        return "\n".join(lines)


class LogFeed(RichLog):
    """A scrollable log feed for recent activity."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("markup", True)
        kwargs.setdefault("wrap", True)
        super().__init__(*args, **kwargs)
        self.logs: List[str] = []
        self.can_focus = True

    def on_mount(self) -> None:
        self.border_title = "Recent Activity"
        if not self.logs:
            self.write("[dim]Awaiting activity...[/]", scroll_end=False)

    def set_logs(self, logs: List[str]) -> None:
        was_at_end = self.is_vertical_scroll_end
        self.logs = logs
        self.clear()
        if not self.logs:
            self.write("[dim]Awaiting activity...[/]", scroll_end=False)
            return
        for line in self.logs:
            self.write(line, scroll_end=False)
        if was_at_end:
            self.scroll_end(animate=False)


class FinalSummaryPanel(Static):
    """Panel showing final run state and available actions."""

    summary = reactive({})
    run_state = reactive("idle")

    def watch_summary(self) -> None:
        self.refresh(layout=True)

    def watch_run_state(self) -> None:
        self.refresh(layout=True)

    @staticmethod
    def build_summary_text(run_state: str, summary: Dict[str, Any]) -> str:
        state = (run_state or "idle").strip().lower()
        status_title = {
            "running": "[bold yellow]RUNNING[/]",
            "finalizing": "[bold yellow]FINALIZING[/]",
            "completed": "[bold green]COMPLETED[/]",
            "failed": "[bold red]FAILED[/]",
            "interrupted": "[bold red]INTERRUPTED[/]",
        }.get(state, "[dim]WAITING[/]")

        if state not in {"finalizing", "completed", "failed", "interrupted"}:
            return (
                "[bold green]FINAL SUMMARY[/]\n"
                "[dim]Session still in progress. The summary will appear here when processing ends.[/]"
            )

        duration = float(summary.get("duration_seconds", 0.0) or 0.0)
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        worker_count = int(summary.get("worker_count", 0) or 0)
        download_root = summary.get("download_root", "") or "-"
        msg_files = int(summary.get("msg_files_available", 0) or 0)
        report_available = "yes" if summary.get("report_available") else "no"
        error = summary.get("error") or summary.get("message") or ""

        lines = [
            "[bold green]FINAL SUMMARY[/]",
            f"State: {status_title}",
            f"Processed: [bold]{summary.get('processed', 0)}[/] | Success: [bold green]{summary.get('successful', 0)}[/] | Failed: [bold red]{summary.get('failed', 0)}[/]",
            f"Duration: [bold]{minutes}m {seconds}s[/] | Workers: [bold]{worker_count}[/]",
            f"Download root: [cyan]{download_root}[/]",
            f"MSG files available: [bold]{msg_files}[/] | Report available: [bold]{report_available}[/]",
            "[bold green]No downloads in progress.[/]",
        ]
        if error:
            lines.append(f"[bold red]Message:[/] {error}")

        lines.extend([
            "",
            "",
        ])

        post_process = summary.get("post_process") or {}
        if post_process:
            stage = post_process.get("stage") or ""
            status_message = post_process.get("status_message") or ""
            if status_message:
                lines.append(f"Post-processing: [bold yellow]{status_message}[/]")
            elif stage:
                lines.append(f"Post-processing stage: [bold yellow]{stage}[/]")
            msg_conversion = post_process.get("msg_conversion") or {}
            report_path = post_process.get("report_path")
            if msg_conversion.get("executed"):
                lines.append(
                    "MSG to PDF: "
                    f"[bold]{msg_conversion.get('converted', 0)}[/] converted, "
                    f"[bold]{msg_conversion.get('skipped', 0)}[/] skipped, "
                    f"[bold]{msg_conversion.get('failed', 0)}[/] failed"
                )
            elif msg_conversion:
                lines.append(f"MSG to PDF: [dim]{msg_conversion.get('reason', 'skipped')}[/]")
            if report_path:
                lines.append(f"Final report: [cyan]{report_path}[/]")
            else:
                lines.append("Final report: [dim]not generated[/]")

        lines.extend([
            "",
            "[bold yellow]Action[/]",
            "[bold]Q[/] Exit",
        ])
        return "\n".join(lines)

    def render(self) -> str:
        return self.build_summary_text(self.run_state, self.summary)


class CoupaTextualUI(App):
    """Main Textual Application for Coupa Downloads."""

    BINDINGS = [Binding("q", "quit_flow", "Exit", show=False)]
    
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
        height: 5;
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

    FinalSummaryPanel {
        color: #e2e8f0;
    }
    """

    def __init__(self, comm_manager: CommunicationManager, total_pos: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.comm_manager = comm_manager
        self.total_pos = total_pos
        self.comm_manager.configure_total_pos(total_pos)
        self.start_time = time.time()
        self.worker_data = []
        self.perf_history = []
        self.last_perf_update = 0
        self._recent_logs: List[str] = []
        self._ui_refresh_seconds = float(os.environ.get("COUPA_UI_REFRESH_SECONDS", "1.0"))

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
                yield FinalSummaryPanel(id="final-summary")
                yield LogFeed(id="log-feed")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Coupa Downloads Premium"
        self.sub_title = "v2.0 Beta (Textual Edition)"
        self.set_interval(self._ui_refresh_seconds, self.update_data)

    def _is_terminal_run_state(self, run_state: str) -> bool:
        return run_state in {"completed", "failed", "interrupted"}

    def _can_accept_final_action(self) -> bool:
        return self._is_terminal_run_state(self.comm_manager.get_run_state().get("state", "idle"))

    def _format_header_line(self, parts: List[str]) -> str:
        """Join header KPI segments while skipping empty items."""
        return "  |  ".join(part for part in parts if part)

    def _build_header_block(self, *rows: List[str]) -> str:
        """Render the header in logical KPI rows."""
        return "\n".join(self._format_header_line(row) for row in rows if row)

    def _resolve_resource_metrics(self, resources: Dict[str, Any]) -> tuple[float, float, float]:
        """Prefer pool snapshots and only fall back to local psutil when unavailable."""
        if resources:
            cpu_percent = float(resources.get("cpu_percent", 0.0) or 0.0)
            memory_percent = float(resources.get("memory_percent", 0.0) or 0.0)
            available_ram_gb = float(resources.get("available_ram_gb", 0.0) or 0.0)
            if cpu_percent or memory_percent or available_ram_gb:
                return cpu_percent, memory_percent, available_ram_gb

        vm = psutil.virtual_memory()
        return (
            float(psutil.cpu_percent(interval=None) or 0.0),
            float(vm.percent or 0.0),
            float(vm.available / (1024 ** 3)),
        )

    def action_quit_flow(self) -> None:
        if self._can_accept_final_action():
            self.exit(result="quit")

    def update_data(self) -> None:
        """Poll metrics from communication manager and update UI."""
        try:
            # Drain all pending metrics and get current aggregated state
            metrics = self.comm_manager.get_metrics()
            agg = self.comm_manager.get_aggregated_metrics()
            run_info = agg.get("run", {})
            run_state = run_info.get("state", "idle")
            run_summary = run_info.get("summary", {}) or {}

            # Update workers using persistent worker_states from manager
            try:
                worker_grid = self.query_one("#worker-grid", WorkerStatusGrid)
                worker_states = agg.get("workers_status", {})

                displayed_workers = []
                # Sort by worker_id (handle both int and str, always return int)
                def sort_key(k):
                    if isinstance(k, int):
                        return k
                    if isinstance(k, str):
                        if k.startswith('worker-'):
                            try:
                                return int(k.split('-')[1])
                            except (ValueError, IndexError):
                                pass
                        # Try to parse any numeric string
                        try:
                            return int(k)
                        except (ValueError, TypeError):
                            pass
                    # Fallback: use a large int so unknown keys sort last
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
                    
                    # Robust display ID generation: always derive a human-friendly label
                    numeric_id = sort_key(wid)
                    if numeric_id != 999999:
                        display_id = f"Worker {numeric_id}"
                    else:
                        display_id = str(wid)
                    
                    displayed_workers.append({
                        "worker_id": display_id,
                        "current_po": m.get("po_id", "Idle"),
                        "status": m.get("status", "Idle"),
                        "attachments_found": m.get("attachments_found", 0),
                        "attachments_downloaded": m.get("attachments_downloaded", 0),
                        "efficiency_score": m.get("efficiency_score", 0.0),
                        "tasks_processed": m.get("tasks_processed", 0),
                        "tasks_failed": m.get("tasks_failed", 0),
                        "file_downloads": m.get("file_downloads") or [],
                    })

                resources = agg.get("resources", {})
                current_workers = int(resources.get("worker_count", len(displayed_workers)) or 0)
                known_worker_ids = {entry["worker_id"] for entry in displayed_workers}
                for index in range(1, current_workers + 1):
                    display_id = f"Worker {index}"
                    if display_id in known_worker_ids:
                        continue
                    displayed_workers.append({
                        "worker_id": display_id,
                        "current_po": "Idle",
                        "status": "READY",
                        "attachments_found": 0,
                        "attachments_downloaded": 0,
                        "efficiency_score": 0.0,
                        "tasks_processed": 0,
                        "tasks_failed": 0,
                    })

                displayed_workers.sort(
                    key=lambda entry: sort_key(str(entry.get("worker_id", "")).replace("Worker ", "worker-"))
                )
                
                if run_state == "finalizing":
                    status_message = ((run_summary.get("post_process") or {}).get("status_message") or "").strip()
                    if status_message:
                        worker_grid.message_override = f"[bold yellow]{status_message}[/]"
                    else:
                        worker_grid.message_override = "[bold yellow]Finalizing folders and consolidating results...[/]"
                elif self._is_terminal_run_state(run_state):
                    worker_grid.message_override = "[bold green]Processing finished. Review the summary and choose an action.[/]"
                elif displayed_workers:
                    worker_grid.message_override = ""
                    worker_grid.worker_entries = displayed_workers
                else:
                    worker_grid.message_override = ""
                    worker_grid.worker_entries = []
            except Exception:
                pass  # Worker grid update failed; continue with other sections

            try:
                final_summary = self.query_one("#final-summary", FinalSummaryPanel)
                final_summary.run_state = run_state
                final_summary.summary = run_summary
                final_summary.display = run_state in {"finalizing", "completed", "failed", "interrupted"}
            except Exception:
                pass

            # Update logs from recent metrics (best-effort; keep UI alive on errors)
            try:
                log_feed = self.query_one("#log-feed", LogFeed)
                metric_source = metrics or agg.get("recent_metrics", [])
                new_logs = []
                for m in metric_source:
                    # Skip resource telemetry — it updates internal state only, not an activity event
                    if m.get("resource_snapshot") or m.get("status", "").upper() == "RESOURCE":
                        continue
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
                log_feed.display = not self._is_terminal_run_state(run_state)
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

            resources = agg.get("resources", {})
            cpu_percent, memory_percent, available_ram_gb = self._resolve_resource_metrics(resources)
            try:
                metrics_widget = self.query_one("#metrics", SystemMetrics)
                metrics_widget.update_snapshot(cpu_percent=cpu_percent, mem_percent=memory_percent)
            except Exception:
                pass

            # Update Header Stats
            header_stats = self.query_one("#header-stats", Static)
            total_goal = self.total_pos
            success = agg.get("total_successful", 0)
            failed = agg.get("total_failed", 0)
            processed = success + failed
            active = agg.get("active_count", 0)
            started = agg.get("total_seen", 0)
            eta_info = agg.get("eta", {})
            eta_display = eta_info.get("display", "calculating")
            current_workers = int(resources.get("worker_count", len(agg.get("workers_status", {}))) or 0)
            target_workers = int(resources.get("target_worker_count", current_workers) or current_workers)
            autoscaling_enabled = bool(resources.get("autoscaling_enabled", False))
            worker_mode = f"{current_workers} active / {target_workers} target"
            if autoscaling_enabled:
                worker_mode = f"{worker_mode} (auto)"
            elif target_workers:
                worker_mode = f"{worker_mode} (fixed)"
            resource_display = f"{cpu_percent:.0f}% CPU  {memory_percent:.0f}% RAM  {available_ram_gb:.1f} GB free"
            
            runtime = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
            progress_display = f"{processed}/{total_goal}"
            if active > 0:
                progress_display = f"{processed}/{total_goal} (+{active} active)"
            elif started > processed:
                progress_display = f"{processed}/{total_goal} (+{started - processed} started)"
            
            if self._is_terminal_run_state(run_state):
                header_stats.update(self._build_header_block([
                    f"[stat-label]Status:[/] [stat-value]{run_state.upper()}[/]",
                    f"[stat-label]Runtime:[/] [stat-value]{runtime}[/]",
                ], [
                    f"[stat-label]Processed:[/] [stat-value]{success + failed}/{total_goal}[/]",
                    f"[stat-label]Progress:[/] [stat-value]{processed}/{total_goal}[/]",
                    f"[stat-label]Success:[/] [stat-value]{success}[/]",
                    f"[stat-label]Failed:[/] [stat-value]{failed}[/]",
                ], [
                    f"[stat-label]Workers:[/] [stat-value]{worker_mode}[/]",
                    f"[stat-label]Resources:[/] [stat-value]{resource_display}[/]",
                    f"[stat-label]Action:[/] [stat-value]Q[/]",
                ]))
            elif run_state == "finalizing":
                post_status = ((run_summary.get("post_process") or {}).get("status_message") or "settling").strip()
                header_stats.update(self._build_header_block([
                    f"[stat-label]Status:[/] [stat-value]FINALIZING[/]",
                    f"[stat-label]Runtime:[/] [stat-value]{runtime}[/]",
                ], [
                    f"[stat-label]Step:[/] [stat-value]{post_status}[/]",
                    f"[stat-label]Progress:[/] [stat-value]{processed}/{total_goal}[/]",
                ], [
                    f"[stat-label]Success:[/] [stat-value]{success}[/]",
                    f"[stat-label]Failed:[/] [stat-value]{failed}[/]",
                    f"[stat-label]Workers:[/] [stat-value]{worker_mode}[/]",
                    f"[stat-label]Resources:[/] [stat-value]{resource_display}[/]",
                ]))
            else:
                header_stats.update(self._build_header_block([
                    f"[stat-label]Status:[/] [stat-value]RUNNING[/]",
                    f"[stat-label]Runtime:[/] [stat-value]{runtime}[/]",
                    f"[stat-label]ETA:[/] [stat-value]{eta_display}[/]",
                ], [
                    f"[stat-label]Progress:[/] [stat-value]{progress_display}[/]",
                    f"[stat-label]Success:[/] [stat-value]{success}[/]",
                    f"[stat-label]Failed:[/] [stat-value]{failed}[/]",
                    f"[stat-label]Efficiency:[/] [stat-value]{efficiency:.1f} POs/min[/]",
                ], [
                    f"[stat-label]Workers:[/] [stat-value]{worker_mode}[/]",
                    f"[stat-label]Resources:[/] [stat-value]{resource_display}[/]",
                ]))
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
