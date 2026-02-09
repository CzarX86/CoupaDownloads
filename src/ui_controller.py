"""
Módulo UIController.

Controla a interface do usuário usando Rich, incluindo tabelas de progresso,
layouts e atualizações em tempo real durante o processamento.
"""

from typing import Optional, List, Dict, Any
import time
import threading
import psutil
from datetime import datetime
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.console import Console, Group
from rich.text import Text
from rich.align import Align
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn, TaskProgressColumn
from rich.columns import Columns
from rich.style import Style


class UIController:
    # Premium Color Palette (HEX)
    COLORS = {
        "primary": "#6200EE",     # Deep Purple
        "secondary": "#03DAC6",   # Teal / Neon Cyan
        "success": "#00C853",     # Emerald Green
        "warning": "#FFD600",     # Vivid Yellow
        "error": "#CF6679",       # Soft Red/Coral
        "background": "#121212",  # Dark Surface
        "surface": "#1E1E1E",     # Elevated Surface
        "text_primary": "#FFFFFF",
        "text_secondary": "#B0B0B0",
        "accent": "#BB86FC"       # Light Purple
    }

    def __init__(self):
        """Initialize UI controller with Rich components."""
        self.console = Console()
        self.live: Optional[Live] = None
        self._run_start_time: Optional[float] = None
        self._updating = False
        self._render_lock = threading.Lock()
        self._live_owned = False
        self.update_thread: Optional[threading.Thread] = None

        # Global stats for header
        self.global_stats = {
            "total": 0,
            "completed": 0,
            "failed": 0,
            "active": 0,
            "elapsed": "0m 0s",
            "eta_global": "N/A",
            "global_efficiency": "⏳"
        }

        # Worker states for table
        self.worker_states: List[Dict[str, Any]] = []
        
        # Recent logs for footer feed
        self.recent_logs: List[str] = []
        self._max_logs = 10  # Increased for new layout
        
        # Performance history for line graph
        self.perf_history: List[float] = []
        self._max_perf_history = 20  # Visible window
        self._last_perf_update = 0.0

    def _create_layout(self) -> Layout:
        """Create the screen layout with dynamic sizing and sidebar."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="middle"),
            Layout(name="footer", size=6),
        )
        layout["middle"].split_row(
            Layout(name="main", ratio=3),
            Layout(name="sidebar", ratio=1),
        )
        return layout

    def _build_progress_table(self) -> Table:
        """Build the worker progress table."""
        table = Table(
            expand=True,
            border_style=f"bold {self.COLORS['accent']}",
            header_style=f"bold {self.COLORS['secondary']}",
            show_lines=True,
            box=None,
            padding=(0, 1)
        )
        table.add_column("Worker", style=self.COLORS["secondary"], no_wrap=True, width=12)
        table.add_column("PO Number", style=self.COLORS["primary"], no_wrap=True, width=15)
        table.add_column("Status", justify="center", width=14)
        table.add_column("Progress Visualization", ratio=1)
        table.add_column("Runtime", justify="right", style=self.COLORS["warning"], width=10)

        if not self.worker_states:
            table.add_row("[dim]Searching for tasks...[/dim]", "", "", "[dim]Waiting for assignment[/dim]", "")
            return table

        for worker in self.worker_states:
            found = worker.get("attachments_found", 0)
            downloaded = worker.get("attachments_downloaded", 0)
            
            # Premium Progress Visualization
            if found > 0:
                progress_pct = min(100, int((downloaded / found) * 100))
                filled_len = int((progress_pct / 100) * 20)
                bar = "█" * filled_len + "░" * (20 - filled_len)
                color = self.COLORS["success"] if downloaded == found else self.COLORS["accent"]
                progress_viz = f"[{color}]{bar}[/] [dim]{downloaded}/{found}[/]"
            else:
                progress_viz = "[dim]No attachments yet[/dim]"

            table.add_row(
                worker.get("worker_id", "N/A"),
                str(worker.get("current_po", "Idle"))[:15],
                self._format_status(worker.get("status", "Idle")),
                progress_viz,
                f"{worker.get('duration', 0.0):.1f}s"
            )
        return table

    def _format_status(self, status: str) -> str:
        """Apply colors and icons to status strings with capsule style."""
        status_upper = str(status).upper()
        if status_upper in {"COMPLETED", "SUCCESS", "DONE"}:
            return f"[black on {self.COLORS['success']}] SUCCESS [/]"
        if status_upper in {"PROCESSING", "STARTED", "WORKING"}:
            return f"[black on {self.COLORS['warning']}] WORKING [/]"
        if status_upper in {"FAILED", "ERROR"}:
            return f"[white on {self.COLORS['error']}]  ERROR  [/]"
        if status_upper == "IDLE":
            return f"[dim white on #333333]  IDLE   [/]"
        return f"[dim]{status}[/dim]"

    def _update_header(self) -> Panel:
        """Update the header with a modern, clean design."""
        title = Text.assemble(
            ("COUPA", f"bold {self.COLORS['primary']}"),
            ("DOWNLOADS", f"bold {self.COLORS['secondary']}"),
            (" ∞ ", f"bold {self.COLORS['accent']}"),
            ("v2.0", "dim")
        )
        
        info = Text.assemble(
            ("Runtime: ", f"bold {self.COLORS['text_secondary']}"),
            (f"{self.global_stats['elapsed']}", self.COLORS["secondary"]),
            (" | ", "dim"),
            ("Status: ", f"bold {self.COLORS['text_secondary']}"),
            ("ACTIVE", self.COLORS["success"] if self._updating else "dim red"),
            (" | ", "dim"),
            ("Mode: ", f"bold {self.COLORS['text_secondary']}"),
            (f"{getattr(self, 'execution_mode', 'N/A').upper()}", self.COLORS["accent"])
        )

        grid = Table.grid(expand=True)
        grid.add_column(justify="left")
        grid.add_column(justify="right")
        grid.add_row(title, info)

        return Panel(
            grid,
            border_style=self.COLORS["primary"],
            padding=(0, 1)
        )

    def _draw_perf_sparkline(self, data: List[float]) -> Text:
        """Draw a single-line Braille sparkline for performance history."""
        if not data:
            return Text("N/A", style="dim")
        
        # Braille dots mapping (2x4 grid per char)
        # We'll use a simpler version: 1-dot wide, 4-dot high resolution per char
        # to show a smooth line in 1 text line.
        # Braille dots 1-2-3-7 (left) and 4-5-6-8 (right)
        # For a single column (left side of char), we use dots 1, 2, 3, 7
        braille_levels = [0x00, 0x40, 0x04, 0x02, 0x01] # Empty, dot 7, dot 3, dot 2, dot 1 (bottom to top)
        # Actually, let's just use the standard vertical blocks for simplicity 
        # but if we want a LINE look, we can use:
        # Dots 1, 2, 3, 7 are the vertical column.
        # But wait, Braille is 2 columns. We can pack 2 data points per character!
        
        width = 24 # characters (48 data points)
        display_data = data[-(width*2):]
        # Pad with 0s if needed to make it even
        if len(display_data) % 2 != 0:
            display_data = [display_data[0]] + display_data
            
        min_v = min(data)
        max_v = max(data)
        range_v = max_v - min_v
        
        def get_dot_mask(val, col_type): # col_type 0=left, 1=right
            if range_v == 0:
                level = 2 # middle
            else:
                level = int((val - min_v) / range_v * 3) # 0 to 3 (4 levels)
            
            # Braille dots: 1(L1), 2(L2), 3(L3), 4(R1), 5(R2), 6(R3), 7(L4), 8(R4)
            # We use 4 vertical levels. 
            # Level 0 (bottom): Dot 7 (L) or 8 (R)
            # Level 1: Dot 3 (L) or 6 (R)
            # Level 2: Dot 2 (L) or 5 (R)
            # Level 3 (top): Dot 1 (L) or 4 (R)
            if col_type == 0: # Left column
                masks = [0x40, 0x04, 0x02, 0x01]
            else: # Right column
                masks = [0x80, 0x20, 0x10, 0x08]
            return masks[level]

        spark_chars = []
        for i in range(0, len(display_data), 2):
            v_left = display_data[i]
            v_right = display_data[i+1]
            
            char_code = 0x2800 # Base Braille
            char_code |= get_dot_mask(v_left, 0)
            char_code |= get_dot_mask(v_right, 1)
            spark_chars.append(chr(char_code))
            
        avg_v = sum(data) / len(data)
        last_v = data[-1]
        color = self.COLORS["success"] if last_v >= avg_v else self.COLORS["warning"]
        
        return Text("".join(spark_chars), style=color)

    def _update_sidebar(self) -> Panel:
        """Update the sidebar with system health and global stats."""
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
        except:
            cpu, mem = 0, 0

        def _get_metric_color(val, threshold1, threshold2):
            if val < threshold1: return self.COLORS["success"]
            if val < threshold2: return self.COLORS["warning"]
            return self.COLORS["error"]

        cpu_color = _get_metric_color(cpu, 60, 85)
        mem_color = _get_metric_color(mem, 70, 90)

        stats_group = Group(
            Text("[STATS]", style=f"bold {self.COLORS['accent']}"),
            Text(f"CPU: {cpu}% | MEM: {mem}%", style=self.COLORS["secondary"]),
            Text(f"Progress: {self.global_stats['completed']}/{self.global_stats['total']}", style=self.COLORS["secondary"]),
            Text(f"Rem: {self.global_stats['active']} | ETA: {self.global_stats.get('eta_global', '...')}", style=self.COLORS["warning"]),
            Text(f"S: {self.global_stats['completed']} | F: {self.global_stats['failed']}", style=self.COLORS["success"]),
            
            Text(f"\n[PERFORMANCE]", style=f"bold {self.COLORS['accent']}"),
            Text(f"Eff: {self.global_stats['global_efficiency']}", style=self.COLORS["secondary"]),
            self._draw_perf_sparkline(self.perf_history),
            Text("Eixo X: tempo (5s/ponto)", style="dim italic")
        )

        return Panel(
            stats_group,
            title="[bold]Metrics[/bold]",
            border_style=f"bold {self.COLORS['secondary']}",
            padding=(0, 1)
        )

    def _update_footer(self) -> Panel:
        """Update the footer with a clean high-density log feed."""
        log_lines = self.recent_logs[-self._max_logs:] if self.recent_logs else []
        
        styled_logs = []
        for log in log_lines:
            if "❌" in log or "FAIL" in log or "Error" in log:
                style = self.COLORS["error"]
            elif "✅" in log or "SUCCESS" in log:
                style = self.COLORS["success"]
            elif "WORKING" in log or "STARTED" in log:
                style = self.COLORS["secondary"]
            else:
                style = self.COLORS["text_secondary"]
            
            styled_logs.append(Text(f"› {log}", style=style))

        return Panel(
            Group(*styled_logs) if styled_logs else Text("Awaiting system signals...", style="dim"),
            title="[bold blue]Recent Activity[/bold blue]",
            border_style=f"dim {self.COLORS['primary']}",
            padding=(0, 1)
        )

    def _build_renderable(self) -> Layout:
        """Build the complete renderable layout with sidebar integration."""
        layout = self._create_layout()
        layout["header"].update(self._update_header())
        layout["main"].update(self._build_progress_table())
        layout["sidebar"].update(self._update_sidebar())
        layout["footer"].update(self._update_footer())
        return layout

    def get_initial_renderable(self) -> Layout:
        """Get the initial renderable for Live display."""
        return self._build_renderable()

    def update_display(self) -> None:
        """Update the live display if active."""
        if not (self.live and self._updating):
            return
            
        # Recalculate efficiency and history before rendering
        self._update_efficiency_stats()
        
        with self._render_lock:
            try:
                # Use refresh=True to force re-render with current terminal dimensions
                self.live.update(self._build_renderable(), refresh=True)
            except Exception:
                pass  # Ignore rendering errors

    def add_log(self, message: str) -> None:
        """Add a log message to the footer feed."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        self.recent_logs.append(log_msg)
        # Keep only recent logs
        if len(self.recent_logs) > self._max_logs * 2:
            self.recent_logs = self.recent_logs[-self._max_logs:]

    def _update_efficiency_stats(self) -> None:
        """Update global efficiency and performance history based on current stats."""
        if not self._run_start_time:
            return

        elapsed_seconds = max(0.0, time.time() - self._run_start_time)
        minutes, seconds = divmod(int(elapsed_seconds), 60)
        self.global_stats['elapsed'] = f"{minutes}m {seconds}s"
        
        if elapsed_seconds > 0:
            # Always calculate current efficiency for the text readout
            efficiency = 0.0
            if self.global_stats['completed'] > 0:
                efficiency = (self.global_stats['completed'] / elapsed_seconds) * 60
            
            self.global_stats['global_efficiency'] = f"{efficiency:.1f} POs/min"
            
            # Sampling logic: Update history every 5 seconds for the time-series graph
            now = time.time()
            if now - self._last_perf_update >= 5.0:
                self.perf_history.append(efficiency)
                if len(self.perf_history) > self._max_perf_history:
                    self.perf_history.pop(0)
                self._last_perf_update = now

            total = self.global_stats.get('total', 0)
            completed_failed = self.global_stats.get('completed', 0) + self.global_stats.get('failed', 0)
            self.global_stats['active'] = max(0, total - completed_failed)
            
            remaining = self.global_stats['active']
            # Only show ETA after at least 2 POs or 30s to have a stable baseline
            if remaining > 0 and (self.global_stats['completed'] >= 2 or elapsed_seconds >= 30):
                avg_time = elapsed_seconds / self.global_stats['completed']
                eta_sec = avg_time * remaining
                em, es = divmod(int(eta_sec), 60)
                self.global_stats['eta_global'] = f"{em}m {es}s"
            elif remaining == 0:
                self.global_stats['eta_global'] = "0m 0s"
            else:
                self.global_stats['eta_global'] = "Calculando..."
        elif elapsed_seconds > 10:
            self.global_stats['global_efficiency'] = "Calculando..."

    def update_with_metrics(self, communication_manager) -> None:
        """Update display with metrics from communication manager."""
        if not communication_manager:
            self.update_display()
            return

        metrics = communication_manager.get_metrics()
        
        # Add messages from metrics to logs (limit to avoid spam)
        for m in metrics[-5:]:  # Only last 5 metrics
            msg = m.get("message")
            if msg and msg not in [log.split("] ", 1)[-1] for log in self.recent_logs[-3:]]:
                self.add_log(msg[:80])  # Truncate long messages

        # Update worker states
        worker_metrics = {}
        progress_updates = []
        for metric in metrics:
            if metric.get('po_id') == 'PROGRESS_UPDATE':
                # Special progress update
                progress_updates.append(metric)
                continue
            worker_id = metric.get('worker_id', 0)
            if worker_id not in worker_metrics:
                worker_metrics[worker_id] = []
            worker_metrics[worker_id].append(metric)

        # Process progress updates
        if progress_updates:
            latest_progress = progress_updates[-1]  # Get the most recent progress update
            self.global_stats['total'] = latest_progress.get('total_tasks', self.global_stats.get('total', 0))
            self.global_stats['completed'] = latest_progress.get('completed_tasks', 0)
            self.global_stats['failed'] = latest_progress.get('failed_tasks', 0)
            self.global_stats['active'] = latest_progress.get('active_tasks', 0)

        def _normalize_worker_id(raw_worker_id: Any) -> str:
            try:
                idx = int(raw_worker_id)
            except (TypeError, ValueError):
                return str(raw_worker_id)
            return f"Worker {idx + 1}"

        current_worker_states = {ws['worker_id']: ws for ws in self.worker_states if 'worker_id' in ws}

        for worker_id, worker_metric_list in worker_metrics.items():
            latest_metric = worker_metric_list[-1] if worker_metric_list else {}
            worker_key = _normalize_worker_id(worker_id)
            existing_state = current_worker_states.get(worker_key, {})

            started_at = latest_metric.get('timestamp') or existing_state.get('started_at') or time.time()

            worker_state = {
                'worker_id': worker_key,
                'current_po': latest_metric.get('po_id', existing_state.get('current_po', 'Idle')),
                'status': latest_metric.get('status', existing_state.get('status', 'Idle')),
                'attachments_found': latest_metric.get('attachments_found', existing_state.get('attachments_found', 0)),
                'attachments_downloaded': latest_metric.get('attachments_downloaded', existing_state.get('attachments_downloaded', 0)),
                'duration': latest_metric.get('duration', existing_state.get('duration', 0.0)),
                'started_at': started_at,
            }
            current_worker_states[worker_key] = worker_state

        self.worker_states = sorted(current_worker_states.values(), key=lambda x: x['worker_id'])

        # Update live durations
        now = time.time()
        for worker_state in self.worker_states:
            status = worker_state.get('status')
            started_at = worker_state.get('started_at')
            if status in {'STARTED', 'PROCESSING'} and started_at:
                worker_state['duration'] = max(0.0, now - started_at)

        # Global stats
        agg_metrics = communication_manager.get_aggregated_metrics()
        if not self.global_stats.get('total'):
            self.global_stats['total'] = agg_metrics.get('total_processed', 0)
        self.global_stats['completed'] = agg_metrics.get('total_successful', 0)
        self.global_stats['failed'] = agg_metrics.get('total_failed', 0)
        
        self.update_display()

    def start_live_updates(self, communication_manager, update_interval: float = 0.5):
        """Start live updates from communication manager."""
        if self._run_start_time is None:
            self._run_start_time = time.time()

        if self.update_thread and self.update_thread.is_alive():
            return

        def update_loop_existing():
            while self._updating and self.live:
                try:
                    self.update_with_metrics(communication_manager)
                except Exception:
                    pass
                time.sleep(update_interval)

        def update_loop_owned():
            # Use screen=True for full window mode
            with Live(
                self.get_initial_renderable(),
                console=self.console,
                refresh_per_second=4,
                screen=True,  # Full screen mode
                auto_refresh=False  # Manual refresh for proper resize handling
            ) as live:
                self._live_owned = True
                self.live = live
                while self._updating:
                    try:
                        self.update_with_metrics(communication_manager)
                    except Exception:
                        pass
                    time.sleep(update_interval)
            self._live_owned = False
            self.live = None

        self._updating = True
        if self.live:
            self.update_thread = threading.Thread(target=update_loop_existing, daemon=True)
        else:
            self.update_thread = threading.Thread(target=update_loop_owned, daemon=True)
        self.update_thread.start()

    def stop_live_updates(self):
        """Stop live updates."""
        self._updating = False
        if self.update_thread:
            self.update_thread.join(timeout=2.0)
            self.update_thread = None
        if self._live_owned:
            self.live = None
            self._live_owned = False
