"""
Módulo UIController.

Controla a interface do usuário usando Rich, incluindo tabelas de progresso,
layouts e atualizações em tempo real durante o processamento.
"""

from typing import Optional, List, Dict, Any
import time
import psutil
from datetime import datetime
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.console import Console, Group
from rich.text import Text
from rich.align import Align


class UIController:
    def __init__(self):
        """Initialize UI controller with Rich components."""
        self.console = Console()
        self.live: Optional[Live] = None
        self._run_start_time: Optional[float] = None
        self._updating = False

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
        self._max_logs = 5

    def _create_layout(self) -> Layout:
        """Create the screen layout with dynamic sizing."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=6, minimum_size=6),   # Priority: always 6 lines
            Layout(name="main", ratio=1, minimum_size=3),    # Flexible, min 3
            Layout(name="footer", size=6),                   # Reduced from 8 to 6
        )
        return layout

    def _build_progress_table(self) -> Table:
        """Build the worker progress table."""
        table = Table(
            title="[bold blue]Worker Progress[/bold blue]", 
            expand=True,
            border_style="bright_black",
            header_style="bold cyan",
            show_lines=False
        )
        table.add_column("Worker", style="blue", no_wrap=True, width=10)
        table.add_column("PO", style="cyan", no_wrap=True, width=15)
        table.add_column("Status", style="yellow", width=12)
        # Progress column takes remaining space
        table.add_column("Progress", ratio=1, justify="center")
        table.add_column("Time", justify="right", style="red", width=8)

        if not self.worker_states:
            table.add_row("[dim]No workers active[/dim]", "", "", "", "")
            return table

        for worker in self.worker_states:
            found = worker.get("attachments_found", 0)
            downloaded = worker.get("attachments_downloaded", 0)
            
            # Create progress bar
            if found > 0:
                progress_pct = min(100, int((downloaded / found) * 100))
                # Dynamic bar length based on simple math, but in a ratio column likely fine
                # We'll use a slightly safer fixed visualization or just text if it's too small
                # Simple ASCII bar
                bar_len = 20
                filled = int((progress_pct / 100) * bar_len)
                color = "green" if downloaded == found else "magenta"
                bar = "━" * filled + "─" * (bar_len - filled)
                progress_bar = f"[{color}]{downloaded}/{found}[/{color}]  [{color}]{bar}[/{color}]"
            else:
                progress_bar = "[dim]Waiting...[/dim]"

            table.add_row(
                str(worker.get("worker_id", "N/A")),
                str(worker.get("current_po", "Idle"))[:15],
                self._format_status(worker.get("status", "Idle")),
                progress_bar,
                f"{worker.get('duration', 0.0):.1f}s"
            )
        return table

    def _format_status(self, status: str) -> str:
        """Apply colors and icons to status strings."""
        status_upper = str(status).upper()
        if status_upper in {"COMPLETED", "SUCCESS", "DONE"}:
            return "[green]✅ DONE[/green]"
        if status_upper in {"PROCESSING", "STARTED", "WORKING"}:
            return "[yellow]⚙️  WORK[/yellow]"
        if status_upper in {"FAILED", "ERROR"}:
            return "[red]❌ FAIL[/red]"
        if status_upper == "IDLE":
            return "[dim]⏸️  IDLE[/dim]"
        return f"[dim]{status}[/dim]"

    def _update_header(self) -> Panel:
        """Update the header with a single unified dashboard panel."""
        # Create a grid for the content inside the single panel
        grid = Table.grid(expand=True, padding=(0, 2))
        grid.add_column(justify="center", ratio=1, no_wrap=True)
        grid.add_column(justify="center", ratio=1, no_wrap=True)
        grid.add_column(justify="center", ratio=1, no_wrap=True)
        grid.add_column(justify="center", ratio=1, no_wrap=True)
        grid.add_column(justify="center", ratio=1, no_wrap=True)

        grid.add_row(
            f"[bold blue]{self.global_stats['elapsed']}[/bold blue]\n[dim]ETA: {self.global_stats['eta_global']}[/dim]",
            f"[bold cyan]{self.global_stats['total']}[/bold cyan]\n[dim]Ativos: {self.global_stats['active']}[/dim]",
            f"[bold yellow]{self.global_stats['global_efficiency']}[/bold yellow]",
            f"[bold green]{self.global_stats['completed']}[/bold green]",
            f"[bold red]{self.global_stats['failed']}[/bold red]"
        )
        
        # Add labels row
        grid.add_row(
            "[dim]⏱️ Tempo[/dim]",
            "[dim]📊 Total[/dim]",
            "[dim]⚡ Performance[/dim]",
            "[dim]✅ Sucesso[/dim]",
            "[dim]❌ Falhas[/dim]"
        )

        return Panel(
            grid,
            title="[bold]Dashboard[/bold]",
            border_style="bright_blue",
            padding=(0, 1)
        )

    def _update_footer(self) -> Panel:
        """Update the footer with system metrics and recent logs."""
        try:
            cpu = psutil.cpu_percent(interval=None)  # Non-blocking
            mem = psutil.virtual_memory().percent
        except:
            cpu, mem = 0, 0
        
        metrics_text = Text.assemble(
            ("System: ", "dim"),
            (f"CPU {cpu:.0f}%", "green" if cpu < 70 else "red"),
            (" | ", "dim"),
            (f"MEM {mem:.0f}%", "green" if mem < 80 else "red"),
            (" | ", "dim"),
            (f"{datetime.now().strftime('%H:%M:%S')}", "cyan")
        )

        # Show more logs if space permits, but footer is fixed height
        # Keeping 5 lines is safe
        log_lines = self.recent_logs[-self._max_logs:] if self.recent_logs else []
        log_content = "\n".join([f"[dim]›[/dim] {log}" for log in log_lines])
        
        content = Group(
            metrics_text,
            "",
            Panel(
                log_content if log_content else "[dim]Aguardando atividade...[/dim]", 
                title="[bright_black]Atividade Recente[/bright_black]", 
                border_style="bright_black",
                padding=(0, 1)
            )
        )
        
        return Panel(content, border_style="bright_black", padding=(0, 1))

    def _build_renderable(self) -> Layout:
        """Build the complete renderable layout."""
        layout = self._create_layout()
        layout["header"].update(self._update_header())
        layout["main"].update(self._build_progress_table())
        layout["footer"].update(self._update_footer())
        return layout

    def get_initial_renderable(self) -> Layout:
        """Get the initial renderable for Live display."""
        return self._build_renderable()

    def update_display(self) -> None:
        """Update the live display if active."""
        if self.live and self._updating:
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
        for metric in metrics:
            worker_id = metric.get('worker_id', 0)
            if worker_id not in worker_metrics:
                worker_metrics[worker_id] = []
            worker_metrics[worker_id].append(metric)

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
        total = self.global_stats.get('total', 0)
        self.global_stats['active'] = max(0, total - self.global_stats['completed'] - self.global_stats['failed'])

        if self._run_start_time:
            elapsed_seconds = max(0.0, time.time() - self._run_start_time)
            minutes, seconds = divmod(int(elapsed_seconds), 60)
            self.global_stats['elapsed'] = f"{minutes}m {seconds}s"
            
            if elapsed_seconds > 0 and self.global_stats['completed'] > 0:
                efficiency = (self.global_stats['completed'] / elapsed_seconds) * 60
                self.global_stats['global_efficiency'] = f"{efficiency:.1f} POs/min"
                
                remaining = self.global_stats['active']
                if remaining > 0:
                    avg_time = elapsed_seconds / self.global_stats['completed']
                    eta_sec = avg_time * remaining
                    em, es = divmod(int(eta_sec), 60)
                    self.global_stats['eta_global'] = f"{em}m {es}s"
                else:
                    self.global_stats['eta_global'] = "0m 0s"
            elif elapsed_seconds > 10:
                self.global_stats['global_efficiency'] = "Calculando..."

        self.update_display()

    def start_live_updates(self, communication_manager, update_interval: float = 0.5):
        """Start live updates from communication manager."""
        import threading
        
        if self._run_start_time is None:
            self._run_start_time = time.time()

        def update_loop():
            # Use screen=True for full window mode
            with Live(
                self.get_initial_renderable(), 
                console=self.console, 
                refresh_per_second=4,
                screen=True,  # Full screen mode
                auto_refresh=False  # Manual refresh for proper resize handling
            ) as live:
                self.live = live
                while self._updating:
                    try:
                        self.update_with_metrics(communication_manager)
                        time.sleep(update_interval)
                    except Exception:
                        time.sleep(update_interval)

        self._updating = True
        self.update_thread = threading.Thread(target=update_loop, daemon=True)
        self.update_thread.start()

    def stop_live_updates(self):
        """Stop live updates."""
        self._updating = False
        if hasattr(self, 'update_thread'):
            self.update_thread.join(timeout=2.0)
        self.live = None
