"""
Função avançada para gerenciar múltiplas janelas no Edge WebDriver com paralelismo e downloads
Cria N janelas configuráveis, processa URLs do Coupa em paralelo e baixa arquivos automaticamente
"""

import os
import sys
import random
import time
import threading
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, InvalidSessionIdException, NoSuchWindowException, ElementClickInterceptedException
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.layout import Layout
from rich.text import Text
from rich import box

# 🛡️ IMPORTAR CONFIGURAÇÃO CRÍTICA DO PERFIL 🛡️
try:
    from profile_config import EDGE_PROFILE_CONFIG, PROFILE_STATUS_MESSAGES
    print("✅ Configuração crítica do perfil carregada com sucesso")
except ImportError as e:
    print(f"⚠️ Aviso: Não foi possível carregar configuração do perfil: {e}")
    print("   Usando configurações padrão...")
    # Configurações de fallback
    EDGE_PROFILE_CONFIG = {
        "macos_profile_path": "~/Library/Application Support/Microsoft Edge",
        "windows_profile_path": "%LOCALAPPDATA%/Microsoft/Edge/User Data",
        "profile_directory": "Default",
        "login_check_url": "https://unilever.coupahost.com",
        "login_check_timeout": 3,
        "login_selectors": [
            "input[type='password']",
            "input[name*='password']", 
            "button[type='submit']"
        ]
    }
    PROFILE_STATUS_MESSAGES = {
        "not_logged_in": "⚠️ Perfil carregado mas usuário não está logado no Coupa\n   Será necessário fazer login manualmente se necessário",
        "logged_in": "✅ Perfil carregado e usuário está logado no Coupa!",
        "check_failed": "⚠️ Não foi possível verificar status do login: {error}\n   Continuando com o processamento..."
    }


class TerminalUI:
    """Interface de terminal dinâmica com tabelas atualizáveis."""
    
    def __init__(self):
        self.console = Console()
        self.layout = Layout()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        )
        self.stats = {
            'total_urls': 0,           # Total de URLs/POs a processar
            'processed_pos': 0,       # POs que foram carregadas e processadas (com downloads)
            'pages_not_found': 0,     # POs com páginas não encontradas
            'total_downloadable_docs': 0,  # Total de documentos baixáveis encontrados
            'successful_downloads': 0, # Documentos baixados com sucesso
            'failed_downloads': 0,    # Documentos que falharam no download
            'active_tabs': 0,         # Abas ativas no momento
            'active_windows': 0       # Janelas ativas
        }
        self.tab_data = {}  # {tab_id: {status, po_number, window, downloads}}
        
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
        
    def create_header(self):
        """Cria o cabeçalho da interface."""
        header_text = Text("🚀 CoupaDownloads - Processamento Paralelo Avançado", style="bold blue")
        return Panel(header_text, box=box.DOUBLE)
    
    def create_stats_table(self):
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
    
    def create_tabs_table(self):
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
    
    def create_progress_table(self):
        """Cria tabela de progresso."""
        table = Table(title="⚡ Progresso Paralelo", box=box.ROUNDED)
        table.add_column("Worker", style="cyan")
        table.add_column("Status", style="yellow")
        table.add_column("PO Atual", style="green")
        table.add_column("Tempo", style="blue")
        
        # Simular dados de workers (será atualizado em tempo real)
        for i in range(4):  # 4 workers
            table.add_row(
                f"Worker-{i+1}",
                "🔄 Processando",
                "N/A",
                "0s"
            )
        
        return table
    
    def create_footer(self):
        """Cria o rodapé da interface."""
        footer_text = Text("Pressione Ctrl+C para interromper", style="dim")
        return Panel(footer_text, box=box.SIMPLE)
    
    def update_stats(self, **kwargs):
        """Atualiza estatísticas."""
        self.stats.update(kwargs)
    
    def update_tab_data(self, tab_id, **kwargs):
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


class ParallelTabManager:
    """Gerencia abas de forma paralela e segura com downloads."""
    
    def __init__(self, driver, window_ids):
        self.driver = driver
        self.window_ids = window_ids
        self.lock = threading.Lock()
        self.active_tabs = {}  # url_index -> tab_info
        self.completed_urls = []
        self.failed_urls = []
        self.download_results = []
        
        # Configurações de download
        self.download_dir = os.path.expanduser("~/Downloads/CoupaDownloads")
        self.attachment_selector = (
            "div[class*='commentAttachments'] a[href*='attachment_file'], "
            "div[class*='attachment'] a[href*='attachment_file'], "
            "div[class*='attachment'] a[href*='download'], "
            "div[class*='attachment'] a[href*='attachment'], "
            "span[aria-label*='file attachment'], "
            "span[role='button'][aria-label*='file attachment'], "
            "span[title*='.pdf'], span[title*='.docx'], span[title*='.msg']"
        )
    
    def create_tab_for_url(self, url_index, url, window_id, window_name):
        """Cria uma aba para uma URL específica."""
        try:
            # Usar lock apenas para operações críticas do WebDriver
            with self.lock:
                # Mudar para a janela especificada
                self.driver.switch_to.window(window_id)
                
                # Criar nova aba
                self.driver.execute_script("window.open('');")
                
                # Mudar para a nova aba criada
                self.driver.switch_to.window(self.driver.window_handles[-1])
                new_tab_id = self.driver.current_window_handle
            
            # Carregar URL fora do lock para permitir paralelismo
            print(f"📄 [{threading.current_thread().name}] Criando aba para URL {url_index+1} em {window_name}")
            print(f"   Aba ID: {new_tab_id}")
            print(f"   URL: {url}")
            
            self.driver.get(url)
            
            # Aguardar carregamento
            wait = WebDriverWait(self.driver, 10)
            wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
            
            # Registrar aba ativa (com lock apenas para esta operação)
            with self.lock:
                tab_info = {
                    'tab_id': new_tab_id,
                    'url': url,
                    'url_index': url_index,
                    'window_name': window_name,
                    'created_at': time.time()
                }
                
                self.active_tabs[url_index] = tab_info
            
            print(f"✅ [{threading.current_thread().name}] URL {url_index+1} carregada com sucesso")
            print(f"   Aba ID: {new_tab_id}")
            
            return tab_info
                
        except Exception as e:
            print(f"❌ [{threading.current_thread().name}] Erro ao criar aba para URL {url_index+1}: {e}")
            return None
    
    def find_attachments(self, tab_handle, po_number):
        """Encontra anexos na página de forma thread-safe."""
        try:
            with self.lock:
                self.driver.switch_to.window(tab_handle)
                
                # Aguardar elementos carregarem
                wait = WebDriverWait(self.driver, 10)
                wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
                
                # Buscar anexos
                attachments = self.driver.find_elements(By.CSS_SELECTOR, self.attachment_selector)
                
                print(f"🔍 [{threading.current_thread().name}] Encontrados {len(attachments)} anexos para PO {po_number}")
                
                return attachments
                
        except Exception as e:
            print(f"❌ [{threading.current_thread().name}] Erro ao buscar anexos: {e}")
            return []
    
    def download_attachment(self, attachment, filename, po_number):
        """Inicia download de um anexo e retorna imediatamente (não aguarda conclusão)."""
        try:
            # Estratégia 1: Click direto (mais rápido)
            try:
                attachment.click()
                time.sleep(0.1)  # Delay mínimo apenas para iniciar o download
            except ElementClickInterceptedException:
                # Estratégia 2: Scroll e click
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", 
                    attachment
                )
                time.sleep(0.1)  # Delay mínimo
                attachment.click()
                time.sleep(0.1)  # Delay mínimo
            except:
                # Estratégia 3: JavaScript click
                self.driver.execute_script("arguments[0].click();", attachment)
                time.sleep(0.1)  # Delay mínimo
            
            # Retornar imediatamente - download será monitorado em background
            print(f"📥 [{threading.current_thread().name}] Download iniciado para: {filename}")
            return {
                'success': True,
                'filename': filename,  # Nome esperado do arquivo
                'po_number': po_number,
                'original_filename': filename,
                'status': 'initiated'  # Status: iniciado
            }
                
        except Exception as e:
            print(f"❌ [{threading.current_thread().name}] Erro ao iniciar download: {e}")
            return {
                'success': False,
                'filename': None,
                'po_number': po_number,
                'original_filename': filename,
                'error': str(e)
            }
    
    def monitor_downloads_for_tab(self, tab_id, po_number, expected_downloads):
        """Monitora downloads de uma aba em background e fecha quando todos terminam."""
        thread_name = threading.current_thread().name
        print(f"🔍 [{thread_name}] Iniciando monitoramento de {len(expected_downloads)} downloads para PO {po_number}")
        
        try:
            # Aguardar até 60 segundos para todos os downloads terminarem
            for attempt in range(120):  # 60 segundos com checks a cada 0.5s
                try:
                    # Verificar se a aba ainda existe
                    with self.lock:
                        if tab_id not in self.driver.window_handles:
                            print(f"⚠️ [{thread_name}] Aba {po_number} foi fechada durante monitoramento")
                            return
                    
                    # Verificar downloads concluídos
                    completed_downloads = self._check_completed_downloads(expected_downloads)
                    
                    if len(completed_downloads) == len(expected_downloads):
                        print(f"✅ [{thread_name}] Todos os {len(expected_downloads)} downloads concluídos para PO {po_number}")
                        
                        # Fechar aba após todos os downloads terminarem
                        with self.lock:
                            if tab_id in self.driver.window_handles:
                                self.driver.switch_to.window(tab_id)
                                self.driver.close()
                                print(f"🔒 [{thread_name}] Aba {po_number} fechada após downloads concluídos")
                        return
                    
                    # Log de progresso a cada 10 segundos
                    if attempt % 20 == 0 and attempt > 0:
                        print(f"⏳ [{thread_name}] PO {po_number}: {len(completed_downloads)}/{len(expected_downloads)} downloads concluídos")
                    
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"⚠️ [{thread_name}] Erro no monitoramento: {e}")
                    time.sleep(0.5)
            
            # Timeout - fechar aba mesmo assim
            print(f"⏰ [{thread_name}] Timeout no monitoramento para PO {po_number}, fechando aba")
            with self.lock:
                if tab_id in self.driver.window_handles:
                    self.driver.switch_to.window(tab_id)
                    self.driver.close()
                    print(f"🔒 [{thread_name}] Aba {po_number} fechada por timeout")
                    
        except Exception as e:
            print(f"❌ [{thread_name}] Erro crítico no monitoramento: {e}")
    
    def _check_completed_downloads(self, expected_downloads):
        """Verifica quais downloads foram concluídos."""
        try:
            current_files = set(os.listdir(self.download_dir))
            completed = []
            
            for download_info in expected_downloads:
                filename = download_info['filename']
                # Verificar se arquivo foi baixado
                for file in current_files:
                    if (filename.lower() in file.lower() or 
                        file.lower().endswith(('.pdf', '.docx', '.msg', '.xlsx'))):
                        completed.append(download_info)
                        break
            
            return completed
            
        except Exception as e:
            print(f"❌ Erro ao verificar downloads: {e}")
            return []
    
    def process_url_with_downloads(self, url_index, url, tab_manager, max_workers):
        """Processa uma URL completa com downloads."""
        thread_name = threading.current_thread().name
        result = {
            'url_index': url_index,
            'url': url,
            'success': False,
            'downloads': [],
            'error': None,
            'thread_name': thread_name
        }
        
        try:
            # Determinar qual janela usar (distribuir entre janelas)
            window_index = url_index % len(tab_manager.window_ids)
            window_id = tab_manager.window_ids[window_index]
            window_name = f"Janela {window_index + 1}"
            
            # Criar aba para a URL
            tab_info = tab_manager.create_tab_for_url(url_index, url, window_id, window_name)
            
            if tab_info:
                # Extrair número PO da URL
                po_number = url.split('/')[-1]
                
                # Aguardar um pouco para garantir que a página carregou completamente
                time.sleep(0.5)  # Reduzido de 2s para 0.5s
                
                # Buscar anexos
                attachments = tab_manager.find_attachments(tab_info['tab_id'], po_number)
                
                if attachments:
                    print(f"📎 [{thread_name}] Processando {len(attachments)} anexos para PO {po_number}")
                    
                    # Download sequencial dos anexos (mais estável)
                    for i, attachment in enumerate(attachments):
                        filename = f"{po_number}_attachment_{i+1}"
                        
                        try:
                            download_result = tab_manager.download_attachment(attachment, filename, po_number)
                            result['downloads'].append(download_result)
                            
                            if download_result['success']:
                                print(f"✅ [{thread_name}] Download sucesso: {download_result['filename']}")
                            else:
                                print(f"❌ [{thread_name}] Download falhou: {download_result['error']}")
                                
                        except Exception as e:
                            print(f"❌ [{thread_name}] Erro no download: {e}")
                            result['downloads'].append({
                                'success': False,
                                'filename': None,
                                'po_number': po_number,
                                'error': str(e)
                            })
                else:
                    print(f"📄 [{thread_name}] Nenhum anexo encontrado para PO {po_number}")
                
                result['success'] = True
                
                # Aguardar um pouco antes de fechar a aba
                time.sleep(0.2)  # Reduzido de 1s para 0.2s
                
                # Fechar aba após processamento
                tab_manager.close_tab_safely(url_index)
                
            else:
                result['error'] = "Falha ao criar aba"
                
        except Exception as e:
            result['error'] = str(e)
            print(f"❌ [{thread_name}] Erro ao processar URL {url_index+1}: {e}")
        
        return result
    
    def close_tab_safely(self, url_index):
        """Fecha uma aba de forma segura."""
        try:
            with self.lock:
                if url_index in self.active_tabs:
                    tab_info = self.active_tabs[url_index]
                    tab_id = tab_info['tab_id']
                    
                    # Verificar se a aba ainda existe
                    if tab_id in self.driver.window_handles:
                        self.driver.switch_to.window(tab_id)
                        self.driver.close()
                        print(f"🔒 [{threading.current_thread().name}] Aba {url_index+1} fechada: {tab_id}")
                    
                    # Remover da lista de abas ativas
                    del self.active_tabs[url_index]
                    
        except Exception as e:
            print(f"⚠️ [{threading.current_thread().name}] Erro ao fechar aba {url_index+1}: {e}")
    
    def get_active_tab_count(self):
        """Retorna o número de abas ativas."""
        with self.lock:
            return len(self.active_tabs)
    
    def get_active_tabs_info(self):
        """Retorna informações sobre abas ativas."""
        with self.lock:
            return dict(self.active_tabs)
    
    def process_downloads_for_tab(self, tab_id, po_number):
        """Processa downloads para uma aba específica de forma assíncrona."""
        thread_name = threading.current_thread().name
        result = {
            'success': False,
            'downloads': [],
            'error': None,
            'thread_name': thread_name
        }
        
        try:
            # Usar lock apenas para operações críticas do WebDriver
            with self.lock:
                # Mudar para a aba específica
                self.driver.switch_to.window(tab_id)
                
                # Aguardar página carregar completamente
                wait = WebDriverWait(self.driver, 10)
                wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
                
                # Buscar anexos
                attachments = self.driver.find_elements(By.CSS_SELECTOR, self.attachment_selector)
            
            # Processar anexos FORA do lock para permitir paralelismo real
            if attachments:
                print(f"📎 [{thread_name}] Encontrados {len(attachments)} anexos para PO {po_number}")
                
                # Iniciar todos os downloads rapidamente
                expected_downloads = []
                for i, attachment in enumerate(attachments):
                    filename = f"{po_number}_attachment_{i+1}"
                    
                    try:
                        # Usar lock apenas para operações do WebDriver
                        with self.lock:
                            self.driver.switch_to.window(tab_id)
                            download_result = self.download_attachment(attachment, filename, po_number)
                        
                        result['downloads'].append(download_result)
                        
                        if download_result['success']:
                            expected_downloads.append(download_result)
                            print(f"📥 [{thread_name}] Download iniciado: {filename}")
                        else:
                            print(f"❌ [{thread_name}] Falha ao iniciar download: {download_result['error']}")
                            
                    except Exception as e:
                        print(f"❌ [{thread_name}] Erro no download: {e}")
                        result['downloads'].append({
                            'success': False,
                            'filename': None,
                            'po_number': po_number,
                            'error': str(e)
                        })
                
                # Iniciar monitoramento em background (não bloqueia)
                if expected_downloads:
                    import threading
                    monitor_thread = threading.Thread(
                        target=self.monitor_downloads_for_tab,
                        args=(tab_id, po_number, expected_downloads),
                        daemon=True
                    )
                    monitor_thread.start()
                    print(f"🔍 [{thread_name}] Monitoramento iniciado para {len(expected_downloads)} downloads")
                
            else:
                print(f"📄 [{thread_name}] Nenhum anexo encontrado para PO {po_number}")
                # Fechar aba imediatamente se não há downloads
                with self.lock:
                    if tab_id in self.driver.window_handles:
                        self.driver.switch_to.window(tab_id)
                        self.driver.close()
                        print(f"🔒 [{thread_name}] Aba {po_number} fechada (sem downloads)")
            
            result['success'] = True
            
        except Exception as e:
            result['error'] = str(e)
            print(f"❌ [{thread_name}] Erro ao processar downloads para PO {po_number}: {e}")
        
        return result


def verify_edge_profile_login_status(driver):
    """
    🛡️ FUNÇÃO CRÍTICA - NÃO ALTERAR SEM AUTORIZAÇÃO EXPLÍCITA DO USUÁRIO 🛡️
    
    Esta função verifica se o perfil do Edge foi carregado corretamente
    e se o usuário está logado no Coupa. É ESSENCIAL para o funcionamento.
    
    ⚠️  ATENÇÃO: Qualquer alteração nesta função pode quebrar a detecção de perfil
    ⚠️  Se você precisa modificar algo aqui, CONSULTE O USUÁRIO PRIMEIRO
    
    Args:
        driver: Instância do WebDriver do Edge
        
    Returns:
        bool: True se perfil carregado e usuário logado, False caso contrário
    """
    try:
        # Tentar acessar uma página que requer login para verificar se o perfil está funcionando
        driver.get(EDGE_PROFILE_CONFIG["login_check_url"])
        time.sleep(EDGE_PROFILE_CONFIG["login_check_timeout"])  # Aguardar carregamento
        
        # Verificar se há elementos de login (indicando que não estamos logados)
        login_elements = []
        for selector in EDGE_PROFILE_CONFIG["login_selectors"]:
            login_elements.extend(driver.find_elements(By.CSS_SELECTOR, selector))
        
        if login_elements:
            print(PROFILE_STATUS_MESSAGES["not_logged_in"])
            return False
        else:
            print(PROFILE_STATUS_MESSAGES["logged_in"])
            return True
            
    except Exception as e:
        print(PROFILE_STATUS_MESSAGES["check_failed"].format(error=e))
        return False


def read_po_numbers_from_excel(max_lines=None):
    """
    Lê os números de PO do arquivo Excel e constrói URLs do Coupa.
    
    Args:
        max_lines (int, optional): Número máximo de linhas para processar
    
    Returns:
        list: Lista de URLs do Coupa para carregar
    """
    try:
        # Caminho para o arquivo Excel
        excel_path = os.path.join(os.path.dirname(__file__), "input.xlsx")
        
        # Verificar se arquivo existe
        if not os.path.exists(excel_path):
            print(f"❌ Arquivo não encontrado: {excel_path}")
            return []
        
        # Ler arquivo Excel
        df = pd.read_excel(excel_path, sheet_name='PO_Data', engine='openpyxl')
        
        # Extrair números de PO da coluna 'PO_NUMBER'
        po_numbers = df['PO_NUMBER'].dropna().astype(str).tolist()
        
        # Aplicar limite de linhas se especificado
        if max_lines and max_lines > 0:
            po_numbers = po_numbers[:max_lines]
            print(f"📊 Processando apenas as primeiras {max_lines} linhas do Excel")
        
        # Construir URLs do Coupa
        base_url = "https://unilever.coupahost.com"
        coupa_urls = []
        
        for po_number in po_numbers:
            # Limpar número de PO (remover prefixos como PO, PM, etc.)
            clean_po = po_number.replace("PO", "").replace("PM", "").strip()
            coupa_url = f"{base_url}/order_headers/{clean_po}"
            coupa_urls.append(coupa_url)
        
        print(f"📊 Encontrados {len(coupa_urls)} números de PO no Excel")
        return coupa_urls
        
    except Exception as e:
        print(f"❌ Erro ao ler arquivo Excel: {e}")
        return []


def interactive_configuration():
    """
    Menu interativo de configuração do Edge WebDriver avançado.
    
    Returns:
        dict: Configurações escolhidas pelo usuário
    """
    print(" CONFIGURAÇÃO INTERATIVA DO EDGE WEBDRIVER (AVANÇADO)")
    print("=" * 60)
    
    config = {}
    
    # 1. Modo Headless
    print("\n🔍 MODO HEADLESS:")
    print("1 - Sim (sem interface gráfica)")
    print("2 - Não (com interface gráfica)")
    choice = input("Escolha (1-2): ").strip()
    config['headless'] = choice == "1"
    
    # 2. Perfil do Edge
    print("\n👤 PERFIL DO EDGE:")
    print("1 - Perfil temporário (limpo)")
    print("2 - Perfil mínimo (apenas cookies/logins)")
    print("3 - Perfil completo (extensões, histórico, etc.)")
    choice = input("Escolha (1-3): ").strip()
    
    if choice == "1":
        config['profile_mode'] = "none"
    elif choice == "2":
        config['profile_mode'] = "minimal"
    else:
        config['profile_mode'] = "full"
    
    # 3. Stacktrace
    print("\n🔇 STACKTRACE:")
    print("1 - Mostrar stacktraces completos")
    print("2 - Ocultar stacktraces (apenas mensagens)")
    choice = input("Escolha (1-2): ").strip()
    config['hide_stacktrace'] = choice == "2"
    
    # 4. Número de janelas
    print("\n🪟 NÚMERO DE JANELAS:")
    print("1 - 2 janelas (conservador)")
    print("2 - 4 janelas (equilibrado)")
    print("3 - 6 janelas (agressivo)")
    print("4 - Personalizado")
    choice = input("Escolha (1-4): ").strip()
    
    if choice == "1":
        config['num_windows'] = 2
    elif choice == "2":
        config['num_windows'] = 4
    elif choice == "3":
        config['num_windows'] = 6
    else:
        while True:
            try:
                num_windows = int(input("Número de janelas (1-8): ").strip())
                if 1 <= num_windows <= 8:
                    config['num_windows'] = num_windows
                    break
                else:
                    print("❌ Digite um número entre 1 e 8")
            except ValueError:
                print("❌ Digite um número válido")
    
    # 5. Número de linhas para processar
    print("\n📊 PROCESSAMENTO DO EXCEL:")
    print("1 - Processar arquivo completo")
    print("2 - Processar apenas algumas linhas (para teste)")
    choice = input("Escolha (1-2): ").strip()
    
    if choice == "2":
        while True:
            try:
                max_lines = int(input("Quantas linhas deseja processar? (ex: 5): ").strip())
                if max_lines > 0:
                    config['max_lines'] = max_lines
                    break
                else:
                    print("❌ Digite um número maior que 0")
            except ValueError:
                print("❌ Digite um número válido")
    else:
        config['max_lines'] = None
    
    # 6. Número de workers paralelos
    print("\n⚡ PARALELISMO:")
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
    
    # 7. Resumo da configuração
    print("\n📋 RESUMO DA CONFIGURAÇÃO:")
    print("=" * 30)
    print(f"Headless: {'Sim' if config['headless'] else 'Não'}")
    print(f"Perfil: {config['profile_mode']}")
    print(f"Stacktrace: {'Oculto' if config['hide_stacktrace'] else 'Completo'}")
    print(f"Janelas: {config['num_windows']}")
    max_lines_text = 'Todas' if config['max_lines'] is None else f'{config["max_lines"]} linhas'
    print(f"Linhas Excel: {max_lines_text}")
    print(f"Workers Paralelos: {config['max_workers']}")
    
    confirm = input("\n✅ Confirmar configuração? (s/n): ").strip().lower()
    if confirm not in ['s', 'sim', 'y', 'yes']:
        print("❌ Configuração cancelada.")
        return None
    
    return config


def create_windows(driver, num_windows, config):
    """
    Cria múltiplas janelas posicionadas na tela.
    
    Args:
        driver: Instância do WebDriver
        num_windows: Número de janelas para criar
        config: Configurações do usuário
    
    Returns:
        list: Lista de IDs das janelas criadas
    """
    wait = WebDriverWait(driver, 10)
    window_ids = []
    
    # Obter dimensões da tela
    screen_width = driver.execute_script("return screen.width")
    screen_height = driver.execute_script("return screen.height")
    
    # Calcular tamanho das janelas baseado no número
    if num_windows <= 2:
        window_width = screen_width // 2
        window_height = screen_height // 2
        cols = 2
    elif num_windows <= 4:
        window_width = screen_width // 2
        window_height = screen_height // 2
        cols = 2
    else:
        window_width = screen_width // 3
        window_height = screen_height // 2
        cols = 3
    
    print(f"🪟 Criando {num_windows} janelas...")
    print(f"   Tamanho: {window_width}x{window_height}")
    print(f"   Layout: {cols} colunas")
    
    for i in range(num_windows):
        # Criar nova janela
        driver.switch_to.new_window('window')
        driver.get("about:blank")
        
        # Aguardar carregamento completo
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        
        # Calcular posição da janela
        row = i // cols
        col = i % cols
        
        x = col * window_width
        y = row * window_height
        
        # Posicionar janela
        driver.set_window_position(x, y)
        driver.set_window_size(window_width, window_height)
        
        window_id = driver.current_window_handle
        window_ids.append(window_id)
        
        print(f"✅ Janela {i+1} criada - ID: {window_id}")
        
        print(f"   Posição: ({x}, {y})")
        print(f"   Tamanho: {window_width}x{window_height}")
    
    return window_ids


def manage_edge_tabs_advanced(config):
    """
    Cria múltiplas janelas no Edge WebDriver e processa URLs em paralelo com downloads.
    
    Args:
        config (dict): Configurações escolhidas pelo usuário
    """
    driver = None
    tab_manager = None
    
    try:
        # Configurar o Edge WebDriver EXATAMENTE como no projeto principal
        options = webdriver.EdgeOptions()
        
        # Set profile options FIRST (exatamente como no debug que funciona)
        if config['profile_mode'] != "none":
            # Usar exatamente a mesma lógica que funciona no debug
            if os.name != 'nt':  # macOS/Linux
                profile_path = os.path.expanduser("~/Library/Application Support/Microsoft Edge")
            else:  # Windows
                profile_path = os.path.expanduser("%LOCALAPPDATA%/Microsoft/Edge/User Data")
            
            # Verificar se o diretório do perfil existe
            if os.path.exists(profile_path):
                options.add_argument(f"--user-data-dir={profile_path}")
                options.add_argument(f"--profile-directory=Default")
                print(f"✅ Perfil Edge carregado: {profile_path}")
            else:
                print(f"⚠️ Diretório do perfil não encontrado: {profile_path}")
                print("   Usando sessão temporária sem perfil")
        
        # Ensure browser remains open after script ends (for session persistency)
        options.add_experimental_option("detach", True)
        
        # Other options after profile setup
        if config['profile_mode'] == "minimal":
            # Comentado para permitir extensões do perfil (como no projeto principal)
            # options.add_argument("--disable-extensions")
            # options.add_argument("--disable-plugins")
            print("🍪 Perfil mínimo carregado - apenas cookies e logins")
        elif config['profile_mode'] == "full":
            print("👤 Perfil completo carregado")
        
        options.add_argument("--start-maximized")
        
        # Browser preferences (exatamente como no projeto principal)
        browser_prefs = {
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
            "plugins.always_open_pdf_externally": True,  # Keep this as per project
        }
        options.add_experimental_option("prefs", browser_prefs)
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # Suppress verbose browser output
        if config['hide_stacktrace']:
            options.add_argument("--log-level=3")  # Only fatal errors
            options.add_argument("--silent")
            options.add_argument("--disable-logging")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--no-sandbox")
            print("🔇 Stacktrace ocultado")
        
        if config['headless']:
            options.add_argument("--headless=new")  # Usar headless=new como no projeto principal
            print("🔍 Modo headless ativado")
        
        # Inicializar o driver com tratamento de erro como no projeto principal
        try:
            driver = webdriver.Edge(options=options)
            print("✅ Edge WebDriver inicializado com perfil")
        except Exception as e:
            if "user data directory is already in use" in str(e):
                print("⚠️ Profile directory is already in use. Falling back to default browser session.")
                # Retry without profile options
                options = webdriver.EdgeOptions()
                options.add_experimental_option("detach", True)
                options.add_argument("--start-maximized")
                
                # Browser preferences (exatamente como no projeto principal)
                browser_prefs = {
                    "download.prompt_for_download": False,
                    "download.directory_upgrade": True,
                    "safebrowsing.enabled": False,
                    "plugins.always_open_pdf_externally": True,  # Keep this as per project
                }
                options.add_experimental_option("prefs", browser_prefs)
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option("useAutomationExtension", False)
                
                if config['hide_stacktrace']:
                    options.add_argument("--log-level=3")
                    options.add_argument("--silent")
                    options.add_argument("--disable-logging")
                    options.add_argument("--disable-dev-shm-usage")
                    options.add_argument("--no-sandbox")
                
                if config['headless']:
                    options.add_argument("--headless=new")
                
                driver = webdriver.Edge(options=options)
                print("✅ Using Edge WebDriver without profile")
            else:
                print(f"❌ Erro ao inicializar WebDriver: {e}")
                raise
        
        # Carregar uma página na janela inicial para garantir que o perfil seja aplicado
        driver.get("about:blank")  # Página em branco para carregar o perfil

        # Aguardar carregamento completo da janela inicial
        wait = WebDriverWait(driver, 10)
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        print("✅ Janela inicial com perfil carregada completamente")
        
        # ============================================================================
        # 🛡️ CHAMADA DA FUNÇÃO CRÍTICA - NÃO ALTERAR SEM AUTORIZAÇÃO EXPLÍCITA 🛡️
        # ============================================================================
        # Esta função é ESSENCIAL para verificar se o perfil foi carregado corretamente
        # ⚠️  ATENÇÃO: Não altere esta chamada sem consultar o usuário primeiro
        # ============================================================================
        verify_edge_profile_login_status(driver)
        # ============================================================================
        # 🛡️ FIM DA CHAMADA CRÍTICA 🛡️
        # ============================================================================

        # Delay de 2 segundos antes de criar as janelas
        print("⏳ Aguardando 2 segundos antes de criar as janelas...")
        time.sleep(2)

        # Criar múltiplas janelas
        window_ids = create_windows(driver, config['num_windows'], config)

        # Delay de 2 segundos antes de fechar a janela inicial
        print("⏳ Aguardando 2 segundos antes de fechar janela inicial...")
        time.sleep(2)

        # Fechar janela inicial
        driver.switch_to.window(driver.window_handles[0])
        driver.close()
        print("✅ Janela inicial fechada")
        
        # NOVA FUNCIONALIDADE: Ler Excel e processar URLs em paralelo com downloads
        coupa_urls = read_po_numbers_from_excel(config.get('max_lines'))
        
        if coupa_urls:
            # Inicializar gerenciador de abas paralelo
            tab_manager = ParallelTabManager(driver, window_ids)
            
            print(f"\n🚀 Iniciando processamento paralelo de {len(coupa_urls)} URLs...")
            print(f"⚡ Usando {config['max_workers']} workers paralelos")
            print(f"🪟 Distribuindo entre {config['num_windows']} janelas")
            
            # Inicializar interface de terminal dinâmica
            ui = TerminalUI()
            ui.update_stats(
                total_urls=len(coupa_urls),
                active_windows=len(window_ids)
            )
            
            # VERDADEIRO PARALELISMO: Criar múltiplas abas simultaneamente
            print(f"\n🚀 Criando {len(coupa_urls)} abas simultaneamente...")
            
            # Criar função para criar uma aba específica (SEM LOCK para paralelismo real)
            def create_single_tab(url_data):
                url_index, url = url_data
                window_index = url_index % len(window_ids)
                window_id = window_ids[window_index]
                window_name = f"Janela {window_index + 1}"
                
                try:
                    # Usar lock apenas para operações críticas do WebDriver
                    with tab_manager.lock:
                        # Mudar para a janela especificada
                        tab_manager.driver.switch_to.window(window_id)
                        
                        # Criar nova aba
                        tab_manager.driver.execute_script("window.open('');")
                        
                        # Mudar para a nova aba criada
                        tab_manager.driver.switch_to.window(tab_manager.driver.window_handles[-1])
                        new_tab_id = tab_manager.driver.current_window_handle
                    
                    # Carregar URL fora do lock para permitir paralelismo
                    print(f"📄 [{threading.current_thread().name}] Criando aba para URL {url_index+1} em {window_name}")
                    print(f"   Aba ID: {new_tab_id}")
                    print(f"   URL: {url}")
                    
                    tab_manager.driver.get(url)
                    
                    # Aguardar carregamento
                    wait = WebDriverWait(tab_manager.driver, 10)
                    wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
                    
                    # Registrar aba ativa (com lock apenas para esta operação)
                    with tab_manager.lock:
                        tab_info = {
                            'tab_id': new_tab_id,
                            'url': url,
                            'url_index': url_index,
                            'window_name': window_name,
                            'created_at': time.time()
                        }
                        
                        tab_manager.active_tabs[url_index] = tab_info
                    
                    po_number = tab_info['url'].split('/')[-1]
                    
                    # Atualizar UI com nova aba
                    ui.update_tab_data(tab_info['tab_id'], 
                                     po_number=po_number,
                                     window=window_name,
                                     status='processing',
                                     successful_downloads=0,
                                     total_downloads=0,
                                     thread_name=threading.current_thread().name)
                    
                    print(f"✅ [{threading.current_thread().name}] Aba {url_index+1} criada em {window_name}")
                    return tab_info
                    
                except Exception as e:
                    print(f"❌ [{threading.current_thread().name}] Erro ao criar aba {url_index+1}: {e}")
                    return None
            
            # Criar todas as abas em paralelo usando ThreadPoolExecutor
            created_tabs = []
            with ThreadPoolExecutor(max_workers=min(len(coupa_urls), config['max_workers'])) as tab_executor:
                # Submeter todas as tarefas de criação de abas
                url_data_list = [(i, url) for i, url in enumerate(coupa_urls)]
                future_to_url = {
                    tab_executor.submit(create_single_tab, url_data): url_data 
                    for url_data in url_data_list
                }
                
                # Coletar resultados conforme completam
                for future in as_completed(future_to_url):
                    url_data = future_to_url[future]
                    try:
                        tab_info = future.result()
                        if tab_info:
                            created_tabs.append(tab_info)
                    except Exception as e:
                        print(f"❌ Erro ao criar aba {url_data[0]+1}: {e}")
            
            ui.update_stats(active_tabs=len(created_tabs))
            print(f"📊 Total de abas criadas: {len(created_tabs)}")
            
            # Aguardar todas as páginas carregarem (otimizado)
            print("⏳ Aguardando carregamento de todas as páginas...")
            time.sleep(2)  # Reduzido de 5s para 2s
            
            # Processar downloads em paralelo com interface dinâmica
            print(f"📥 Iniciando downloads paralelos com {config['max_workers']} workers...")
            
            # Inicializar estatísticas
            processed_pos = 0
            pages_not_found = 0
            total_downloadable_docs = 0
            successful_downloads = 0
            failed_downloads = 0
            
            with Live(ui.render_interface(), refresh_per_second=1, console=ui.console) as live:
                with ThreadPoolExecutor(max_workers=config['max_workers']) as executor:
                    # Submeter todas as tarefas de download
                    future_to_tab = {
                        executor.submit(
                            tab_manager.process_downloads_for_tab, 
                            tab_info['tab_id'], 
                            tab_info['url'].split('/')[-1]
                        ): tab_info 
                        for tab_info in created_tabs
                    }
                    
                    # Processar tarefas completadas
                    for future in as_completed(future_to_tab):
                        tab_info = future_to_tab[future]
                        try:
                            result = future.result()
                            
                            po_number = tab_info['url'].split('/')[-1]
                            
                            if result['success']:
                                processed_pos += 1
                                downloads = result['downloads']
                                
                                # Contar documentos baixáveis e downloads
                                total_downloadable_docs += len(downloads)
                                successful_downloads += sum(1 for d in downloads if d['success'])
                                failed_downloads += sum(1 for d in downloads if not d['success'])
                                
                                # Atualizar UI com sucesso
                                ui.update_tab_data(tab_info['tab_id'],
                                                 status='completed',
                                                 successful_downloads=sum(1 for d in downloads if d['success']),
                                                 total_downloads=len(downloads),
                                                 thread_name=result['thread_name'])
                                
                                print(f"✅ [{result['thread_name']}] PO {po_number} processada com sucesso")
                                print(f"   📎 Downloads: {len(downloads)} anexos")
                            else:
                                # Verificar se é página não encontrada ou outro erro
                                if "não encontrada" in str(result['error']).lower() or "not found" in str(result['error']).lower():
                                    pages_not_found += 1
                                else:
                                    processed_pos += 1  # PO foi processada mas falhou
                                
                                # Atualizar UI com falha
                                ui.update_tab_data(tab_info['tab_id'],
                                                 status='failed',
                                                 thread_name=result['thread_name'])
                                
                                print(f"❌ [{result['thread_name']}] PO {po_number} falhou: {result['error']}")
                            
                            # Atualizar estatísticas gerais
                            ui.update_stats(
                                processed_pos=processed_pos,
                                pages_not_found=pages_not_found,
                                total_downloadable_docs=total_downloadable_docs,
                                successful_downloads=successful_downloads,
                                failed_downloads=failed_downloads,
                                active_tabs=len(created_tabs) - (processed_pos + pages_not_found)
                            )
                            
                            # Atualizar interface
                            live.update(ui.render_interface())
                            
                        except Exception as e:
                            pages_not_found += 1  # Exceção geralmente indica página não encontrada
                            
                            # Atualizar UI com erro
                            ui.update_tab_data(tab_info['tab_id'],
                                             status='failed',
                                             thread_name='Error')
                            
                            ui.update_stats(
                                pages_not_found=pages_not_found,
                                active_tabs=len(created_tabs) - (processed_pos + pages_not_found)
                            )
                            
                            print(f"❌ Exceção para PO {tab_info['url'].split('/')[-1]}: {e}")
                            live.update(ui.render_interface())
            
            # Resumo final
            print(f"\n🎉 Processamento paralelo concluído!")
            print(f"📊 Total POs: {len(coupa_urls)}")
            print(f"✅ POs Processadas: {processed_pos}")
            print(f"❌ Páginas Não Encontradas: {pages_not_found}")
            print(f"📈 Taxa de Processamento: {(processed_pos/len(coupa_urls)*100):.1f}%")
            print(f"📄 Total Docs Baixáveis: {total_downloadable_docs}")
            print(f"📥 Downloads Bem-sucedidos: {successful_downloads}")
            print(f"❌ Downloads Falharam: {failed_downloads}")
            print(f"📈 Taxa de Download: {(successful_downloads/total_downloadable_docs*100):.1f}%" if total_downloadable_docs > 0 else "📈 Taxa de Download: 0%")
            
        else:
            print("⚠️ Nenhuma URL encontrada no Excel. Continuando com janelas vazias.")
        
        # Exibir informações das janelas
        print("\n" + "="*50)
        print("📋 RESUMO DAS JANELAS CRIADAS:")
        print("="*50)
        for i, window_id in enumerate(window_ids):
            print(f"Janela {i+1} - ID: {window_id}")
        print("="*50)
        
        # Loop para escolha do usuário
        while True:
            print("\n🎯 ESCOLHA UMA OPÇÃO:")
            print("0 - Fechar navegador completamente")
            
            try:
                choice = input("\nDigite sua escolha (0): ").strip()
                
                if choice == "0":
                    print("🔄 Fechando navegador completamente...")
                    break
                else:
                    print("❌ Opção inválida! Digite apenas 0")
                    
            except KeyboardInterrupt:
                print("\n⚠️ Operação cancelada pelo usuário.")
                break
            except Exception as e:
                print(f"❌ Erro na entrada: {e}")
                
    except Exception as e:
        print(f"❌ Erro ao inicializar o WebDriver: {e}")
        
    finally:
        # Fechar o driver se ainda estiver aberto
        if driver:
            try:
                driver.quit()
                print("🔒 WebDriver fechado com sucesso!")
            except Exception as e:
                print(f"⚠️ Erro ao fechar WebDriver: {e}")


if __name__ == "__main__":
    print("🚀 Iniciando gerenciador avançado de janelas do Edge...")
    
    # Configuração interativa
    config = interactive_configuration()
    if config is None:
        print("👋 Programa finalizado!")
        sys.exit(0)
    
    # Executar com configurações
    manage_edge_tabs_advanced(config)
    print("👋 Programa finalizado!")
