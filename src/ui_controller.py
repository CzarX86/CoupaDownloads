"""
Módulo UIController.

Controla a interface do usuário usando Rich, incluindo tabelas de progresso,
layouts e atualizações em tempo real durante o processamento.
"""

from typing import Optional, List, Dict, Any
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

        # Update worker states - preserve existing states and update with new metrics
        current_worker_states = {ws['worker_id']: ws for ws in self.worker_states}

        for worker_id, worker_metric_list in worker_metrics.items():
            # Get the most recent metric for this worker
            latest_metric = worker_metric_list[-1] if worker_metric_list else {}

            # Get existing state if available, otherwise create new
            existing_state = current_worker_states.get(worker_id, {})

            # Update the worker state with the latest metric
            worker_state = {
                'worker_id': worker_id,
                'current_po': latest_metric.get('po_id', existing_state.get('current_po', 'Unknown')),
                'status': latest_metric.get('status', existing_state.get('status', 'Unknown')),
                'attachments_found': latest_metric.get('attachments_found', existing_state.get('attachments_found', 0)),
                'attachments_downloaded': latest_metric.get('attachments_downloaded', existing_state.get('attachments_downloaded', 0)),
                'duration': latest_metric.get('duration', existing_state.get('duration', 0.0)),
            }
            # Update the current worker states dict
            current_worker_states[worker_id] = worker_state

        # Update the instance variable
        self.worker_states = list(current_worker_states.values())

        # Update global stats based on aggregated metrics
        agg_metrics = communication_manager.get_aggregated_metrics()
        self.global_stats['total'] = agg_metrics.get('total_processed', 0)
        self.global_stats['completed'] = agg_metrics.get('total_successful', 0)
        self.global_stats['failed'] = agg_metrics.get('total_failed', 0)

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