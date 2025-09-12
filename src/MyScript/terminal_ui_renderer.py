"""
Módulo de Interface de Usuário - Implementa UI com Rich
Aplica Observer Pattern e Single Responsibility Principle
"""

from typing import Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich import box

from ui_component_interfaces import IUI


class TerminalUI(IUI):
    """
    Interface de terminal dinâmica com tabelas atualizáveis
    Single Responsibility: apenas renderização da UI
    """
    
    def __init__(self):
        self.console = Console()
        self.layout = Layout()
        self.stats = {
            'total_urls': 0,
            'processed_pos': 0,
            'pages_not_found': 0,
            'total_downloadable_docs': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'active_tabs': 0,
            'active_windows': 0
        }
        self.tab_data: Dict[str, Dict[str, Any]] = {}
        
    def setup_layout(self):
        """Configura o layout da interface."""
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )
        
        self.layout["main"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )
        
    def create_header(self) -> Panel:
        """Cria o cabeçalho da interface."""
        header_text = Text("🚀 CoupaDownloads - Sistema de Inventário + Microserviço", style="bold blue")
        return Panel(header_text, box=box.DOUBLE)
    
    def create_stats_table(self) -> Table:
        """Cria tabela de estatísticas."""
        table = Table(title="📊 Estatísticas Gerais", box=box.ROUNDED, show_header=True)
        table.add_column("Métrica", style="cyan", min_width=20)
        table.add_column("Valor", style="green", min_width=8)
        table.add_column("Status", style="yellow", min_width=10)
        
        # Calcular percentuais
        processed_rate = (self.stats['processed_pos'] / max(self.stats['total_urls'], 1)) * 100
        download_success_rate = (self.stats['successful_downloads'] / max(self.stats['total_downloadable_docs'], 1)) * 100 if self.stats['total_downloadable_docs'] > 0 else 0
        
        table.add_row("Total POs", str(self.stats['total_urls']), "📋")
        table.add_row("POs Processadas", str(self.stats['processed_pos']), f"{processed_rate:.1f}%")
        table.add_row("Páginas Não Encontradas", str(self.stats['pages_not_found']), "❌")
        table.add_row("Docs Baixáveis", str(self.stats['total_downloadable_docs']), "📄")
        table.add_row("Downloads Sucesso", str(self.stats['successful_downloads']), f"{download_success_rate:.1f}%")
        table.add_row("Downloads Falha", str(self.stats['failed_downloads']), "❌")
        table.add_row("Abas Ativas", str(self.stats['active_tabs']), "🪟")
        table.add_row("Janelas Ativas", str(self.stats['active_windows']), "🖥️")
        
        return table
    
    def create_tabs_table(self) -> Table:
        """Cria tabela de abas ativas."""
        table = Table(title="🪟 Abas Ativas", box=box.ROUNDED, show_header=True)
        table.add_column("PO", style="cyan", min_width=12)
        table.add_column("Janela", style="blue", min_width=8)
        table.add_column("Status", style="yellow", min_width=8)
        table.add_column("Downloads", style="green", min_width=12)
        table.add_column("Thread", style="magenta", min_width=15)
        
        if not self.tab_data:
            table.add_row("Nenhuma", "aba", "ativa", "no momento", "")
        else:
            for tab_id, data in self.tab_data.items():
                status_icon = "🔄" if data['status'] == 'processing' else "✅" if data['status'] == 'completed' else "❌"
                table.add_row(
                    data['po_number'],
                    data['window'],
                    status_icon,
                    f"{data['successful_downloads']}/{data['total_downloads']}",
                    data['thread_name']
                )
        
        return table
    
    def create_footer(self) -> Panel:
        """Cria o rodapé da interface."""
        footer_text = Text("Pressione Ctrl+C para interromper", style="dim")
        return Panel(footer_text, box=box.SIMPLE)
    
    def update_stats(self, **kwargs):
        """Atualiza estatísticas."""
        self.stats.update(kwargs)
    
    def update_tab_data(self, tab_id: str, **kwargs):
        """Atualiza dados de uma aba."""
        if tab_id not in self.tab_data:
            self.tab_data[tab_id] = {
                'status': 'processing',
                'po_number': 'N/A',
                'window': 'N/A',
                'downloads': 0,
                'successful_downloads': 0,
                'total_downloads': 0,
                'thread_name': 'N/A'
            }
        self.tab_data[tab_id].update(kwargs)
    
    def render_interface(self):
        """Renderiza a interface completa."""
        self.setup_layout()
        
        self.layout["header"].update(self.create_header())
        self.layout["left"].update(self.create_tabs_table())
        self.layout["right"].update(self.create_stats_table())
        self.layout["footer"].update(self.create_footer())
        
        return self.layout


class MicroserviceUI(IUI):
    """
    Interface específica para o microserviço de download
    Single Responsibility: apenas UI do microserviço
    """
    
    def __init__(self):
        self.console = Console()
        self.layout = Layout()
        self.stats = {
            'total_pending': 0,
            'total_downloading': 0,
            'total_completed': 0,
            'total_failed': 0,
            'total_size_downloaded': 0,
            'start_time': None
        }
        self.downloads_data: Dict[str, Dict[str, Any]] = {}
    
    def setup_layout(self):
        """Configura o layout da interface do microserviço."""
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )
        
        self.layout["main"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1)
        )
    
    def create_header(self) -> Panel:
        """Cria o cabeçalho da interface."""
        header_text = Text("🔧 Microserviço de Download - Monitoramento CSV", style="bold blue")
        return Panel(header_text, box=box.DOUBLE)
    
    def create_stats_table(self) -> Table:
        """Cria tabela de estatísticas do microserviço."""
        table = Table(title="📊 Estatísticas do Microserviço", box=box.ROUNDED, show_header=True)
        table.add_column("Métrica", style="cyan", min_width=20)
        table.add_column("Valor", style="green", min_width=15)
        table.add_column("Status", style="yellow", min_width=10)
        
        # Calcular percentuais
        total_files = self.stats['total_pending'] + self.stats['total_downloading'] + self.stats['total_completed'] + self.stats['total_failed']
        completion_rate = (self.stats['total_completed'] / max(total_files, 1)) * 100
        
        # Formatar tamanho
        size_mb = self.stats['total_size_downloaded'] / (1024 * 1024)
        
        table.add_row("Arquivos Pendentes", str(self.stats['total_pending']), "⏳")
        table.add_row("Arquivos Baixando", str(self.stats['total_downloading']), "🔄")
        table.add_row("Arquivos Concluídos", str(self.stats['total_completed']), f"{completion_rate:.1f}%")
        table.add_row("Arquivos Falharam", str(self.stats['total_failed']), "❌")
        table.add_row("Tamanho Baixado", f"{size_mb:.1f} MB", "📦")
        
        if self.stats['start_time']:
            from datetime import datetime
            runtime = datetime.now() - self.stats['start_time']
            table.add_row("Tempo Execução", str(runtime).split('.')[0], "⏱️")
        
        return table
    
    def create_downloads_table(self) -> Table:
        """Cria tabela de downloads em andamento."""
        table = Table(title="🔄 Downloads em Andamento", box=box.ROUNDED, show_header=True)
        table.add_column("PO", style="cyan", min_width=12)
        table.add_column("Arquivo", style="blue", min_width=20)
        table.add_column("Status", style="yellow", min_width=10)
        table.add_column("Tipo", style="green", min_width=10)
        
        if not self.downloads_data:
            table.add_row("Nenhum", "download", "em andamento", "no momento")
        else:
            for po_number, data in list(self.downloads_data.items())[:10]:  # Mostrar apenas os primeiros 10
                status_icon = "🔄" if data['status'] == 'downloading' else "⏳"
                table.add_row(
                    po_number,
                    data['filename'][:20] + "..." if len(data['filename']) > 20 else data['filename'],
                    status_icon,
                    data.get('file_type', 'unknown')
                )
        
        return table
    
    def create_footer(self) -> Panel:
        """Cria o rodapé da interface."""
        footer_text = Text("Pressione Ctrl+C para parar o microserviço", style="dim")
        return Panel(footer_text, box=box.SIMPLE)
    
    def update_stats(self, **kwargs):
        """Atualiza estatísticas do microserviço."""
        self.stats.update(kwargs)
    
    def update_tab_data(self, tab_id: str, **kwargs):
        """Atualiza dados de downloads (compatibilidade com interface)."""
        # Para o microserviço, usamos po_number como chave
        po_number = kwargs.get('po_number', tab_id)
        if po_number not in self.downloads_data:
            self.downloads_data[po_number] = {
                'filename': 'N/A',
                'status': 'pending',
                'file_type': 'unknown'
            }
        self.downloads_data[po_number].update(kwargs)
    
    def render_interface(self):
        """Renderiza a interface completa do microserviço."""
        self.setup_layout()
        
        self.layout["header"].update(self.create_header())
        self.layout["left"].update(self.create_downloads_table())
        self.layout["right"].update(self.create_stats_table())
        self.layout["footer"].update(self.create_footer())
        
        return self.layout

