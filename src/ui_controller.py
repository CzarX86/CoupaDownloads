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
        table.add_column("Progress", style="cyan")
        table.add_column("Tempo Transcorrido", style="yellow")
        table.add_column("ETA Restante", style="green")
        table.add_column("Eficiência", style="magenta")
        for worker in self.worker_states:
            table.add_row(
                worker["worker_id"],
                worker["progress"],
                worker["elapsed"],
                worker["eta"],
                worker["efficiency"]
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