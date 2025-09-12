"""
Microserviço de Download - Monitora CSV e executa downloads em background
Este módulo implementa o microserviço que monitora o CSV de inventário
e executa downloads de forma assíncrona e paralela
"""

import os
import sys
import time
import threading
import requests
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.layout import Layout
from rich import box


class DownloadMicroservice:
    """Microserviço que monitora CSV e executa downloads em background."""
    
    def __init__(self, csv_path="download_inventory.csv", download_dir=None, max_workers=4):
        self.csv_path = csv_path
        self.download_dir = download_dir or os.path.expanduser("~/Downloads/CoupaDownloads")
        self.max_workers = max_workers
        self.lock = threading.Lock()
        self.running = False
        self.stats = {
            'total_pending': 0,
            'total_downloading': 0,
            'total_completed': 0,
            'total_failed': 0,
            'total_size_downloaded': 0,
            'start_time': None
        }
        
        # Criar diretório de download se não existir
        os.makedirs(self.download_dir, exist_ok=True)
        
        # Configurar sessão HTTP
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59'
        })
    
    def get_pending_downloads(self):
        """Retorna lista de downloads pendentes do CSV."""
        try:
            if not os.path.exists(self.csv_path):
                return []
            
            df = pd.read_csv(self.csv_path)
            pending = df[df['status'] == 'pending'].to_dict('records')
            return pending
        except Exception as e:
            print(f"❌ Erro ao ler downloads pendentes: {e}")
            return []
    
    def update_download_status(self, po_number, filename, status, error_message="", file_size=0):
        """Atualiza o status de um download no CSV."""
        with self.lock:
            try:
                df = pd.read_csv(self.csv_path)
                
                # Encontrar e atualizar linha
                mask = (df['po_number'] == po_number) & (df['filename'] == filename)
                if mask.any():
                    df.loc[mask, 'status'] = status
                    if error_message:
                        df.loc[mask, 'error_message'] = error_message
                    if status == 'completed':
                        df.loc[mask, 'downloaded_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        # Garantir que a coluna seja string
                        df['downloaded_at'] = df['downloaded_at'].astype(str)
                        if file_size > 0:
                            df.loc[mask, 'file_size'] = file_size
                    
                    df.to_csv(self.csv_path, index=False)
                    return True
                return False
                
            except Exception as e:
                print(f"❌ Erro ao atualizar status: {e}")
                return False
    
    def download_file(self, download_info):
        """Baixa um arquivo individual."""
        po_number = download_info['po_number']
        url = download_info['url']
        filename = download_info['filename']
        file_type = download_info.get('file_type', 'unknown')
        
        thread_name = threading.current_thread().name
        
        try:
            print(f"📥 [{thread_name}] Iniciando download: {filename}")
            
            # Atualizar status para downloading
            self.update_download_status(po_number, filename, 'downloading')
            
            # Fazer requisição HTTP
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Determinar nome do arquivo final
            content_disposition = response.headers.get('content-disposition', '')
            if 'filename=' in content_disposition:
                # Extrair nome do arquivo do header
                import re
                filename_match = re.search(r'filename[*]?=([^;]+)', content_disposition)
                if filename_match:
                    filename = filename_match.group(1).strip('"')
            
            # Adicionar extensão se não tiver
            if not any(filename.lower().endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.msg']):
                if file_type == 'pdf':
                    filename += '.pdf'
                elif file_type == 'document':
                    filename += '.docx'
                elif file_type == 'spreadsheet':
                    filename += '.xlsx'
                elif file_type == 'email':
                    filename += '.msg'
            
            # Caminho completo do arquivo
            file_path = os.path.join(self.download_dir, f"{po_number}_{filename}")
            
            # Baixar arquivo
            total_size = 0
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)
            
            # Atualizar status para completed
            self.update_download_status(po_number, filename, 'completed', file_size=total_size)
            
            print(f"✅ [{thread_name}] Download concluído: {filename} ({total_size} bytes)")
            return {
                'success': True,
                'filename': filename,
                'file_path': file_path,
                'file_size': total_size,
                'po_number': po_number
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ [{thread_name}] Erro no download de {filename}: {error_msg}")
            
            # Atualizar status para failed
            self.update_download_status(po_number, filename, 'failed', error_msg)
            
            return {
                'success': False,
                'filename': filename,
                'error': error_msg,
                'po_number': po_number
            }
    
    def process_downloads_batch(self, downloads_batch):
        """Processa um lote de downloads em paralelo."""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submeter downloads
            future_to_download = {
                executor.submit(self.download_file, download_info): download_info
                for download_info in downloads_batch
            }
            
            # Coletar resultados
            for future in as_completed(future_to_download):
                download_info = future_to_download[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"❌ Exceção no download: {e}")
                    results.append({
                        'success': False,
                        'filename': download_info['filename'],
                        'error': str(e),
                        'po_number': download_info['po_number']
                    })
        
        return results
    
    def update_stats(self):
        """Atualiza estatísticas do microserviço."""
        try:
            if not os.path.exists(self.csv_path):
                return
            
            df = pd.read_csv(self.csv_path)
            
            self.stats['total_pending'] = len(df[df['status'] == 'pending'])
            self.stats['total_downloading'] = len(df[df['status'] == 'downloading'])
            self.stats['total_completed'] = len(df[df['status'] == 'completed'])
            self.stats['total_failed'] = len(df[df['status'] == 'failed'])
            
            # Calcular tamanho total baixado
            completed_df = df[df['status'] == 'completed']
            if 'file_size' in completed_df.columns:
                self.stats['total_size_downloaded'] = completed_df['file_size'].sum()
            else:
                self.stats['total_size_downloaded'] = 0
                
        except Exception as e:
            print(f"❌ Erro ao atualizar estatísticas: {e}")
    
    def create_stats_table(self):
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
            runtime = datetime.now() - self.stats['start_time']
            table.add_row("Tempo Execução", str(runtime).split('.')[0], "⏱️")
        
        return table
    
    def create_downloads_table(self):
        """Cria tabela de downloads em andamento."""
        table = Table(title="🔄 Downloads em Andamento", box=box.ROUNDED, show_header=True)
        table.add_column("PO", style="cyan", min_width=12)
        table.add_column("Arquivo", style="blue", min_width=20)
        table.add_column("Status", style="yellow", min_width=10)
        table.add_column("Tipo", style="green", min_width=10)
        
        try:
            if os.path.exists(self.csv_path):
                df = pd.read_csv(self.csv_path)
                downloading_df = df[df['status'].isin(['downloading', 'pending'])]
                
                if downloading_df.empty:
                    table.add_row("Nenhum", "download", "em andamento", "no momento")
                else:
                    for _, row in downloading_df.head(10).iterrows():  # Mostrar apenas os primeiros 10
                        status_icon = "🔄" if row['status'] == 'downloading' else "⏳"
                        table.add_row(
                            row['po_number'],
                            row['filename'][:20] + "..." if len(row['filename']) > 20 else row['filename'],
                            status_icon,
                            row.get('file_type', 'unknown')
                        )
        except Exception as e:
            table.add_row("Erro", "ao carregar", "dados", str(e))
        
        return table
    
    def create_header(self):
        """Cria cabeçalho da interface."""
        header_text = Text("🔧 Microserviço de Download - Monitoramento CSV", style="bold blue")
        return Panel(header_text, box=box.DOUBLE)
    
    def create_footer(self):
        """Cria rodapé da interface."""
        footer_text = Text("Pressione Ctrl+C para parar o microserviço", style="dim")
        return Panel(footer_text, box=box.SIMPLE)
    
    def render_interface(self):
        """Renderiza a interface completa do microserviço."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )
        
        layout["main"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1)
        )
        
        layout["header"].update(self.create_header())
        layout["left"].update(self.create_downloads_table())
        layout["right"].update(self.create_stats_table())
        layout["footer"].update(self.create_footer())
        
        return layout
    
    def run_microservice(self, batch_size=5, check_interval=2):
        """
        Executa o microserviço de download.
        
        Args:
            batch_size: Número de downloads por lote
            check_interval: Intervalo entre verificações do CSV (segundos)
        """
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        console = Console()
        
        print("🚀 Iniciando microserviço de download...")
        print(f"📁 Diretório de download: {self.download_dir}")
        print(f"⚡ Workers paralelos: {self.max_workers}")
        print(f"📦 Tamanho do lote: {batch_size}")
        print(f"⏱️ Intervalo de verificação: {check_interval}s")
        
        try:
            with Live(self.render_interface(), refresh_per_second=1, console=console) as live:
                while self.running:
                    try:
                        # Atualizar estatísticas
                        self.update_stats()
                        
                        # Obter downloads pendentes
                        pending_downloads = self.get_pending_downloads()
                        
                        if pending_downloads:
                            print(f"📋 Encontrados {len(pending_downloads)} downloads pendentes")
                            
                            # Processar em lotes
                            for i in range(0, len(pending_downloads), batch_size):
                                batch = pending_downloads[i:i + batch_size]
                                print(f"🔄 Processando lote {i//batch_size + 1}: {len(batch)} arquivos")
                                
                                # Processar lote
                                results = self.process_downloads_batch(batch)
                                
                                # Mostrar resultados do lote
                                successful = sum(1 for r in results if r['success'])
                                failed = len(results) - successful
                                print(f"✅ Lote concluído: {successful} sucessos, {failed} falhas")
                                
                                # Atualizar interface
                                self.update_stats()
                                live.update(self.render_interface())
                                
                                # Pequena pausa entre lotes
                                time.sleep(0.5)
                        else:
                            # Nenhum download pendente
                            live.update(self.render_interface())
                            time.sleep(check_interval)
                            
                    except KeyboardInterrupt:
                        print("\n⚠️ Interrupção solicitada pelo usuário")
                        break
                    except Exception as e:
                        print(f"❌ Erro no microserviço: {e}")
                        time.sleep(check_interval)
                        
        except Exception as e:
            print(f"❌ Erro crítico no microserviço: {e}")
        finally:
            self.running = False
            print("🔒 Microserviço finalizado")
    
    def stop(self):
        """Para o microserviço."""
        self.running = False


def interactive_configuration():
    """
    Menu interativo de configuração do microserviço.
    
    Returns:
        dict: Configurações escolhidas pelo usuário
    """
    print(" CONFIGURAÇÃO INTERATIVA - MICROSERVIÇO DE DOWNLOAD")
    print("=" * 60)
    
    config = {}
    
    # 1. Arquivo CSV
    print("\n📄 ARQUIVO CSV:")
    csv_path = input("Caminho do arquivo CSV (Enter para 'download_inventory.csv'): ").strip()
    config['csv_path'] = csv_path if csv_path else "download_inventory.csv"
    
    # 2. Diretório de download
    print("\n📁 DIRETÓRIO DE DOWNLOAD:")
    download_dir = input("Diretório de download (Enter para '~/Downloads/CoupaDownloads'): ").strip()
    config['download_dir'] = download_dir if download_dir else os.path.expanduser("~/Downloads/CoupaDownloads")
    
    # 3. Número de workers
    print("\n⚡ WORKERS PARALELOS:")
    print("1 - 2 workers (conservador)")
    print("2 - 4 workers (equilibrado)")
    print("3 - 6 workers (agressivo)")
    print("4 - Personalizado")
    choice = input("Escolha (1-4): ").strip()
    
    if choice == "1":
        config['max_workers'] = 2
    elif choice == "2":
        config['max_workers'] = 4
    elif choice == "3":
        config['max_workers'] = 6
    else:
        while True:
            try:
                max_workers = int(input("Número de workers paralelos (1-10): ").strip())
                if 1 <= max_workers <= 10:
                    config['max_workers'] = max_workers
                    break
                else:
                    print("❌ Digite um número entre 1 e 10")
            except ValueError:
                print("❌ Digite um número válido")
    
    # 4. Tamanho do lote
    print("\n📦 TAMANHO DO LOTE:")
    print("1 - 3 arquivos por lote (conservador)")
    print("2 - 5 arquivos por lote (equilibrado)")
    print("3 - 10 arquivos por lote (agressivo)")
    print("4 - Personalizado")
    choice = input("Escolha (1-4): ").strip()
    
    if choice == "1":
        config['batch_size'] = 3
    elif choice == "2":
        config['batch_size'] = 5
    elif choice == "3":
        config['batch_size'] = 10
    else:
        while True:
            try:
                batch_size = int(input("Tamanho do lote (1-20): ").strip())
                if 1 <= batch_size <= 20:
                    config['batch_size'] = batch_size
                    break
                else:
                    print("❌ Digite um número entre 1 e 20")
            except ValueError:
                print("❌ Digite um número válido")
    
    # 5. Intervalo de verificação
    print("\n⏱️ INTERVALO DE VERIFICAÇÃO:")
    print("1 - 1 segundo (rápido)")
    print("2 - 2 segundos (equilibrado)")
    print("3 - 5 segundos (conservador)")
    print("4 - Personalizado")
    choice = input("Escolha (1-4): ").strip()
    
    if choice == "1":
        config['check_interval'] = 1
    elif choice == "2":
        config['check_interval'] = 2
    elif choice == "3":
        config['check_interval'] = 5
    else:
        while True:
            try:
                check_interval = int(input("Intervalo em segundos (1-30): ").strip())
                if 1 <= check_interval <= 30:
                    config['check_interval'] = check_interval
                    break
                else:
                    print("❌ Digite um número entre 1 e 30")
            except ValueError:
                print("❌ Digite um número válido")
    
    # 6. Resumo da configuração
    print("\n📋 RESUMO DA CONFIGURAÇÃO:")
    print("=" * 30)
    print(f"Arquivo CSV: {config['csv_path']}")
    print(f"Diretório Download: {config['download_dir']}")
    print(f"Workers Paralelos: {config['max_workers']}")
    print(f"Tamanho do Lote: {config['batch_size']}")
    print(f"Intervalo Verificação: {config['check_interval']}s")
    
    confirm = input("\n✅ Confirmar configuração? (s/n): ").strip().lower()
    if confirm not in ['s', 'sim', 'y', 'yes']:
        print("❌ Configuração cancelada.")
        return None
    
    return config


def main():
    """Função principal do microserviço."""
    print("🔧 Iniciando Microserviço de Download...")
    
    # Configuração interativa
    config = interactive_configuration()
    if config is None:
        print("👋 Programa finalizado!")
        return
    
    # Verificar se arquivo CSV existe
    if not os.path.exists(config['csv_path']):
        print(f"❌ Arquivo CSV não encontrado: {config['csv_path']}")
        print("💡 Execute primeiro o sistema de inventário para criar o CSV!")
        return
    
    # Criar diretório de download se não existir
    os.makedirs(config['download_dir'], exist_ok=True)
    
    # Inicializar e executar microserviço
    microservice = DownloadMicroservice(
        csv_path=config['csv_path'],
        download_dir=config['download_dir'],
        max_workers=config['max_workers']
    )
    
    try:
        microservice.run_microservice(
            batch_size=config['batch_size'],
            check_interval=config['check_interval']
        )
    except KeyboardInterrupt:
        print("\n⚠️ Microserviço interrompido pelo usuário")
    except Exception as e:
        print(f"❌ Erro no microserviço: {e}")
    finally:
        microservice.stop()
        print("👋 Microserviço finalizado!")


if __name__ == "__main__":
    main()
