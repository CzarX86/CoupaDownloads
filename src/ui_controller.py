"""
Módulo UIController.

Controla a interface do usuário usando Rich, incluindo tabelas de progresso,
layouts e atualizações em tempo real durante o processamento.
"""

from typing import Optional, List, Dict, Any
import time
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.layout import Layout
from rich.live import Live
from rich.console import Console, Group


class UIController:
    def __init__(self):
        """Initialize UI controller with Rich components."""
        self.console = Console()
        self.live: Optional[Live] = None
        self._run_start_time: Optional[float] = None

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

    def _build_progress_table(self) -> Table:
        table = Table(title="Worker Progress")
        table.add_column("Worker ID", style="blue", no_wrap=True)
        table.add_column("Current PO", style="cyan")
        table.add_column("Status", style="yellow")
        table.add_column("Attachments Found", style="green")
        table.add_column("Attachments Downloaded", style="magenta")
        table.add_column("Duration (s)", style="red")

        for worker in self.worker_states:
            table.add_row(
                str(worker.get("worker_id", "N/A")),
                worker.get("current_po", "Idle"),
                worker.get("status", "Idle"),
                str(worker.get("attachments_found", 0)),
                str(worker.get("attachments_downloaded", 0)),
                f"{worker.get('duration', 0.0):.2f}"
            )
        return table

    def _update_header(self) -> Columns:
        """Update the header with KPI cards."""
        time_card = Panel(
            f"⏱️ Tempo Global\n{self.global_stats['elapsed']}\nETA: {self.global_stats['eta_global']}",
            title="Tempo", border_style="blue"
        )
        total_card = Panel(
            f"📊 Total POs\n{self.global_stats['total']}\nAtivos: {self.global_stats['active']}",
            title="Total", border_style="cyan"
        )
        efficiency_card = Panel(
            f"⚡ Eficiência Global\n{self.global_stats['global_efficiency']}",
            title="Performance", border_style="yellow"
        )
        completed_card = Panel(
            f"✅ Concluídos\n{self.global_stats['completed']}",
            title="Sucesso", border_style="green"
        )
        failed_card = Panel(
            f"❌ Falhas\n{self.global_stats['failed']}",
            title="Erros", border_style="red"
        )

        # All cards in a single row
        return Columns([time_card, total_card, efficiency_card, completed_card, failed_card])

    def get_initial_renderable(self) -> Group:
        """Get the initial renderable for Live display."""
        return Group(self._update_header(), "", self._build_progress_table())

    def update_display(self) -> None:
        """Update the live display if active."""
        if self.live:
            self.live.update(Group(self._update_header(), "", self._build_progress_table()))

    def update_with_metrics(self, communication_manager) -> None:
        """
        Update display with metrics from communication manager.

        Args:
            communication_manager: CommunicationManager instance to get metrics from
        """
        if not communication_manager:
            self.update_display()
            return

        # Get metrics from communication manager
        metrics = communication_manager.get_metrics()

        # Update worker states based on metrics
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

        # Update worker states - preserve existing states and update with new metrics
        current_worker_states = {ws['worker_id']: ws for ws in self.worker_states if 'worker_id' in ws}

        for worker_id, worker_metric_list in worker_metrics.items():
            # Get the most recent metric for this worker
            latest_metric = worker_metric_list[-1] if worker_metric_list else {}

            # Get existing state if available, otherwise create new
            worker_key = _normalize_worker_id(worker_id)
            existing_state = current_worker_states.get(worker_key, {})

            started_at = existing_state.get('started_at')
            if latest_metric.get('status') in {'STARTED', 'PROCESSING'} and not started_at:
                started_at = latest_metric.get('timestamp', time.time())

            # Update the worker state with the latest metric
            worker_state = {
                'worker_id': worker_key,
                'current_po': latest_metric.get('po_id', existing_state.get('current_po', 'Unknown')),
                'status': latest_metric.get('status', existing_state.get('status', 'Unknown')),
                'attachments_found': latest_metric.get('attachments_found', existing_state.get('attachments_found', 0)),
                'attachments_downloaded': latest_metric.get('attachments_downloaded', existing_state.get('attachments_downloaded', 0)),
                'duration': latest_metric.get('duration', existing_state.get('duration', 0.0)),
                'started_at': started_at,
            }
            # Update the current worker states dict
            current_worker_states[worker_key] = worker_state

        # Update the instance variable
        self.worker_states = list(current_worker_states.values())

        # Update live durations for active workers even without new metrics
        now = time.time()
        for worker_state in self.worker_states:
            status = worker_state.get('status')
            started_at = worker_state.get('started_at')
            if status in {'STARTED', 'PROCESSING'} and started_at:
                worker_state['duration'] = max(0.0, now - started_at)

        # Update global stats based on aggregated metrics
        agg_metrics = communication_manager.get_aggregated_metrics()
        if not self.global_stats.get('total'):
            self.global_stats['total'] = agg_metrics.get('total_processed', 0)
        self.global_stats['completed'] = agg_metrics.get('total_successful', 0)
        self.global_stats['failed'] = agg_metrics.get('total_failed', 0)
        total = self.global_stats.get('total', 0)
        self.global_stats['active'] = max(0, total - self.global_stats['completed'] - self.global_stats['failed'])

        # Update efficiency and ETA from elapsed time
        if self._run_start_time:
            elapsed_seconds = max(0.0, time.time() - self._run_start_time)
            if elapsed_seconds > 0 and self.global_stats['completed'] > 0:
                global_efficiency = (self.global_stats['completed'] / elapsed_seconds) * 60
                self.global_stats['global_efficiency'] = f"{global_efficiency:.1f} POs/min"

                remaining = max(0, total - self.global_stats['completed'] - self.global_stats['failed'])
                if remaining > 0:
                    avg_time_per_po = elapsed_seconds / max(1, self.global_stats['completed'])
                    eta_seconds = avg_time_per_po * remaining
                    eta_minutes, eta_seconds = divmod(int(eta_seconds), 60)
                    self.global_stats['eta_global'] = f"{eta_minutes}m {eta_seconds}s"
                else:
                    self.global_stats['eta_global'] = "0m 0s"
            elif elapsed_seconds > 0:
                self.global_stats['global_efficiency'] = "⏳"

        # Update display
        self.update_display()

    def start_live_updates(self, communication_manager, update_interval: float = 1.0):
        """
        Start live updates from communication manager.

        Args:
            communication_manager: CommunicationManager instance to get metrics from
            update_interval: Interval in seconds between updates
        """
        import threading
        import time

        if self._run_start_time is None:
            self._run_start_time = time.time()

        def update_loop():
            while getattr(self, '_updating', False):
                try:
                    self.update_with_metrics(communication_manager)
                    time.sleep(update_interval)
                except Exception as e:
                    print(f"Error updating UI: {e}")
                    time.sleep(update_interval)

        self._updating = True
        self.update_thread = threading.Thread(target=update_loop, daemon=True)
        self.update_thread.start()

    def stop_live_updates(self):
        """Stop live updates."""
        self._updating = False
        if hasattr(self, 'update_thread'):
            self.update_thread.join(timeout=1.0)  # Wait up to 1 second for thread to finish
