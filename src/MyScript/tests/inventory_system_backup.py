"""
BACKUP - Sistema de Inventário de Downloads - Versão Original
Este arquivo mantém a versão original antes da correção de distribuição de janelas

Data: $(date)
Problema: get_available_window() sempre retorna primeira janela disponível
Solução: Usar distribuição determinística com módulo (%)

PROBLEMA IDENTIFICADO:
- Linha 347: window_id = self.get_available_window()
- Linha 175-181: get_available_window() busca sequencialmente
- Resultado: Todas as threads vão para a primeira janela disponível
- Race condition com processamento paralelo

CORREÇÃO APLICADA:
- Trocar get_available_window() por distribuição determinística
- window_index = url_index % len(self.window_ids)
- Garante distribuição uniforme mesmo com processamento paralelo
"""

import os
import sys
import time
import threading
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, InvalidSessionIdException, NoSuchWindowException
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.layout import Layout
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


class DownloadInventoryManager:
    """Gerencia o inventário de downloads - coleta URLs sem baixar."""
    
    def __init__(self, csv_path="download_inventory.csv"):
        self.csv_path = csv_path
        self.lock = threading.Lock()
        self.attachment_selector = (
            "div[class*='commentAttachments'] a[href*='attachment_file'], "
            "div[class*='attachment'] a[href*='attachment_file'], "
            "div[class*='attachment'] a[href*='download'], "
            "div[class*='attachment'] a[href*='attachment'], "
            "span[aria-label*='file attachment'], "
            "span[role='button'][aria-label*='file attachment'], "
            "span[title*='.pdf'], span[title*='.docx'], span[title*='.msg']"
        )
        
        # Inicializar CSV se não existir
        self._initialize_csv()
    
    def _initialize_csv(self):
        """Inicializa o arquivo CSV de controle."""
        if not os.path.exists(self.csv_path):
            df = pd.DataFrame(columns=[
                'po_number', 'url', 'filename', 'file_type', 'status', 
                'created_at', 'downloaded_at', 'error_message', 'window_id', 'tab_id'
            ])
            df.to_csv(self.csv_path, index=False)
            print(f"✅ CSV de controle criado: {self.csv_path}")
    
    def add_download_url(self, po_number, url, filename, file_type="unknown", window_id="", tab_id=""):
        """Adiciona uma URL de download ao inventário."""
        with self.lock:
            try:
                # Ler CSV existente
                df = pd.read_csv(self.csv_path)
                
                # Adicionar nova linha
                new_row = {
                    'po_number': po_number,
                    'url': url,
                    'filename': filename,
                    'file_type': file_type,
                    'status': 'pending',
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'downloaded_at': '',
                    'error_message': '',
                    'window_id': window_id,
                    'tab_id': tab_id
                }
                
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(self.csv_path, index=False)
                
                print(f"📝 URL adicionada ao inventário: {filename}")
                return True
                
            except Exception as e:
                print(f"❌ Erro ao adicionar URL ao inventário: {e}")
                return False
    
    def get_pending_downloads(self):
        """Retorna lista de downloads pendentes."""
        try:
            df = pd.read_csv(self.csv_path)
            return df[df['status'] == 'pending'].to_dict('records')
        except Exception as e:
            print(f"❌ Erro ao ler downloads pendentes: {e}")
            return []
    
    def update_download_status(self, po_number, filename, status, error_message=""):
        """Atualiza o status de um download."""
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
                    
                    df.to_csv(self.csv_path, index=False)
                    return True
                return False
                
            except Exception as e:
                print(f"❌ Erro ao atualizar status: {e}")
                return False


class FIFOTabManager:
    """Gerencia abas com controle FIFO por janela."""
    
    def __init__(self, driver, window_ids, max_tabs_per_window=3):
        self.driver = driver
        self.window_ids = window_ids
        self.max_tabs_per_window = max_tabs_per_window
        self.lock = threading.Lock()
        
        # Controle FIFO por janela
        self.window_tab_queues = {window_id: [] for window_id in window_ids}
        self.active_tabs = {}  # url_index -> tab_info
        self.inventory_manager = DownloadInventoryManager()
        
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
    
    def get_available_window(self):
        """Retorna uma janela disponível (com menos abas que o máximo)."""
        with self.lock:
            for window_id in self.window_ids:
                if len(self.window_tab_queues[window_id]) < self.max_tabs_per_window:
                    return window_id
            return None
    
    def create_tab_for_url(self, url_index, url, window_id, window_name):
        """Cria uma aba para uma URL específica."""
        try:
            with self.lock:
                # Verificar se janela ainda tem espaço
                if len(self.window_tab_queues[window_id]) >= self.max_tabs_per_window:
                    print(f"⚠️ Janela {window_name} está cheia ({self.max_tabs_per_window} abas)")
                    return None
                
                # Mudar para a janela especificada
                self.driver.switch_to.window(window_id)
                
                # Criar nova aba
                self.driver.execute_script("window.open('');")
                
                # Mudar para a nova aba criada
                self.driver.switch_to.window(self.driver.window_handles[-1])
                new_tab_id = self.driver.current_window_handle
            
            # Carregar URL fora do lock
            print(f"📄 [{threading.current_thread().name}] Criando aba para URL {url_index+1} em {window_name}")
            print(f"   Aba ID: {new_tab_id}")
            print(f"   URL: {url}")
            
            self.driver.get(url)
            
            # Aguardar carregamento
            wait = WebDriverWait(self.driver, 10)
            wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
            
            # Registrar aba ativa
            with self.lock:
                tab_info = {
                    'tab_id': new_tab_id,
                    'url': url,
                    'url_index': url_index,
                    'window_name': window_name,
                    'window_id': window_id,
                    'created_at': time.time()
                }
                
                self.active_tabs[url_index] = tab_info
                self.window_tab_queues[window_id].append(url_index)
            
            print(f"✅ [{threading.current_thread().name}] URL {url_index+1} carregada com sucesso")
            return tab_info
                
        except Exception as e:
            print(f"❌ [{threading.current_thread().name}] Erro ao criar aba para URL {url_index+1}: {e}")
            return None
    
    def inventory_attachments_for_tab(self, tab_id, po_number):
        """Faz inventário dos anexos de uma aba e salva URLs no CSV."""
        thread_name = threading.current_thread().name
        
        try:
            with self.lock:
                self.driver.switch_to.window(tab_id)
                
                # Aguardar elementos carregarem
                wait = WebDriverWait(self.driver, 10)
                wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
                
                # Buscar anexos
                attachments = self.driver.find_elements(By.CSS_SELECTOR, self.attachment_selector)
            
            if attachments:
                print(f"🔍 [{thread_name}] Inventariando {len(attachments)} anexos para PO {po_number}")
                
                # Coletar informações dos anexos
                for i, attachment in enumerate(attachments):
                    try:
                        # Obter URL do anexo
                        download_url = attachment.get_attribute('href')
                        if not download_url:
                            # Tentar obter de outros atributos
                            download_url = attachment.get_attribute('data-href') or attachment.get_attribute('data-url')
                        
                        # Obter nome do arquivo
                        filename = attachment.get_attribute('title') or attachment.get_attribute('aria-label') or f"{po_number}_attachment_{i+1}"
                        
                        # Determinar tipo de arquivo
                        file_type = "unknown"
                        if filename.lower().endswith('.pdf'):
                            file_type = "pdf"
                        elif filename.lower().endswith(('.doc', '.docx')):
                            file_type = "document"
                        elif filename.lower().endswith(('.xls', '.xlsx')):
                            file_type = "spreadsheet"
                        elif filename.lower().endswith('.msg'):
                            file_type = "email"
                        
                        # Adicionar ao inventário
                        if download_url:
                            self.inventory_manager.add_download_url(
                                po_number=po_number,
                                url=download_url,
                                filename=filename,
                                file_type=file_type,
                                window_id=tab_id,
                                tab_id=tab_id
                            )
                            print(f"📝 [{thread_name}] URL coletada: {filename}")
                        else:
                            print(f"⚠️ [{thread_name}] URL não encontrada para: {filename}")
                            
                    except Exception as e:
                        print(f"❌ [{thread_name}] Erro ao processar anexo {i+1}: {e}")
                
                return len(attachments)
            else:
                print(f"📄 [{thread_name}] Nenhum anexo encontrado para PO {po_number}")
                return 0
                
        except Exception as e:
            print(f"❌ [{thread_name}] Erro ao fazer inventário: {e}")
            return 0
    
    def close_tab_and_create_new(self, url_index, new_url, new_url_index):
        """Fecha uma aba e cria uma nova (FIFO)."""
        try:
            with self.lock:
                if url_index in self.active_tabs:
                    tab_info = self.active_tabs[url_index]
                    window_id = tab_info['window_id']
                    window_name = tab_info['window_name']
                    
                    # Fechar aba atual
                    if tab_info['tab_id'] in self.driver.window_handles:
                        self.driver.switch_to.window(tab_info['tab_id'])
                        self.driver.close()
                        print(f"🔒 [{threading.current_thread().name}] Aba {url_index+1} fechada")
                    
                    # Remover da fila da janela
                    if url_index in self.window_tab_queues[window_id]:
                        self.window_tab_queues[window_id].remove(url_index)
                    
                    # Remover das abas ativas
                    del self.active_tabs[url_index]
                    
                    # Criar nova aba na mesma janela
                    new_tab_info = self.create_tab_for_url(new_url_index, new_url, window_id, window_name)
                    return new_tab_info
            
            return None
            
        except Exception as e:
            print(f"❌ [{threading.current_thread().name}] Erro ao fechar/criar aba: {e}")
            return None
    
    def process_url_with_inventory(self, url_index, url, max_workers):
        """Processa uma URL fazendo inventário dos anexos."""
        thread_name = threading.current_thread().name
        result = {
            'url_index': url_index,
            'url': url,
            'success': False,
            'attachments_found': 0,
            'error': None,
            'thread_name': thread_name
        }
        
        try:
            # PROBLEMA: Obter janela disponível (sempre primeira janela)
            window_id = self.get_available_window()
            if not window_id:
                result['error'] = "Nenhuma janela disponível"
                return result
            
            window_name = f"Janela {self.window_ids.index(window_id) + 1}"
            
            # Criar aba para a URL
            tab_info = self.create_tab_for_url(url_index, url, window_id, window_name)
            
            if tab_info:
                # Extrair número PO da URL
                po_number = url.split('/')[-1]
                
                # Aguardar carregamento
                time.sleep(0.5)
                
                # Fazer inventário dos anexos
                attachments_count = self.inventory_attachments_for_tab(tab_info['tab_id'], po_number)
                
                result['attachments_found'] = attachments_count
                result['success'] = True
                
                # Fechar aba após inventário
                time.sleep(0.2)
                self.close_tab_and_create_new(url_index, "", -1)  # Apenas fechar
                
            else:
                result['error'] = "Falha ao criar aba"
                
        except Exception as e:
            result['error'] = str(e)
            print(f"❌ [{thread_name}] Erro ao processar URL {url_index+1}: {e}")
        
        return result
    
    def get_active_tab_count(self):
        """Retorna o número de abas ativas."""
        with self.lock:
            return len(self.active_tabs)
    
    def get_window_tab_counts(self):
        """Retorna contagem de abas por janela."""
        with self.lock:
            return {window_id: len(tabs) for window_id, tabs in self.window_tab_queues.items()}


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
    Menu interativo de configuração do sistema de inventário.
    
    Returns:
        dict: Configurações escolhidas pelo usuário
    """
    print(" CONFIGURAÇÃO INTERATIVA - SISTEMA DE INVENTÁRIO")
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
    
    # 3. Número de janelas
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
    
    # 4. Máximo de abas por janela
    print("\n📑 MÁXIMO DE ABAS POR JANELA:")
    print("1 - 2 abas (conservador)")
    print("2 - 3 abas (equilibrado)")
    print("3 - 5 abas (agressivo)")
    print("4 - Personalizado")
    choice = input("Escolha (1-4): ").strip()
    
    if choice == "1":
        config['max_tabs_per_window'] = 2
    elif choice == "2":
        config['max_tabs_per_window'] = 3
    elif choice == "3":
        config['max_tabs_per_window'] = 5
    else:
        while True:
            try:
                max_tabs = int(input("Máximo de abas por janela (1-10): ").strip())
                if 1 <= max_tabs <= 10:
                    config['max_tabs_per_window'] = max_tabs
                    break
                else:
                    print("❌ Digite um número entre 1 e 10")
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
    print(f"Janelas: {config['num_windows']}")
    print(f"Máx Abas/Janelas: {config['max_tabs_per_window']}")
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


def manage_inventory_system(config):
    """
    Sistema principal de inventário - coleta URLs sem baixar.
    
    Args:
        config (dict): Configurações escolhidas pelo usuário
    """
    driver = None
    tab_manager = None
    
    try:
        # Configurar o Edge WebDriver
        options = webdriver.EdgeOptions()
        
        # Set profile options FIRST
        if config['profile_mode'] != "none":
            if os.name != 'nt':  # macOS/Linux
                profile_path = os.path.expanduser("~/Library/Application Support/Microsoft Edge")
            else:  # Windows
                profile_path = os.path.expanduser("%LOCALAPPDATA%/Microsoft/Edge/User Data")
            
            if os.path.exists(profile_path):
                options.add_argument(f"--user-data-dir={profile_path}")
                options.add_argument(f"--profile-directory=Default")
                print(f"✅ Perfil Edge carregado: {profile_path}")
            else:
                print(f"⚠️ Diretório do perfil não encontrado: {profile_path}")
        
        options.add_experimental_option("detach", True)
        options.add_argument("--start-maximized")
        
        # Browser preferences
        browser_prefs = {
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
        }
        options.add_experimental_option("prefs", browser_prefs)
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        if config.get('hide_stacktrace', False):
            options.add_argument("--log-level=3")
            options.add_argument("--silent")
            options.add_argument("--disable-logging")
        
        if config['headless']:
            options.add_argument("--headless=new")
            print("🔍 Modo headless ativado")
        
        # Inicializar o driver
        try:
            driver = webdriver.Edge(options=options)
            print("✅ Edge WebDriver inicializado com perfil")
        except Exception as e:
            if "user data directory is already in use" in str(e):
                print("⚠️ Profile directory is already in use. Falling back to default browser session.")
                options = webdriver.EdgeOptions()
                options.add_experimental_option("detach", True)
                options.add_argument("--start-maximized")
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option("useAutomationExtension", False)
                
                if config['headless']:
                    options.add_argument("--headless=new")
                
                driver = webdriver.Edge(options=options)
                print("✅ Using Edge WebDriver without profile")
            else:
                raise
        
        # Carregar página inicial
        driver.get("about:blank")
        wait = WebDriverWait(driver, 10)
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        print("✅ Janela inicial carregada")
        
        # ============================================================================
        # 🛡️ CHAMADA DA FUNÇÃO CRÍTICA - NÃO ALTERAR SEM AUTORIZAÇÃO EXPLÍCITA 🛡️
        # ============================================================================
        verify_edge_profile_login_status(driver)
        # ============================================================================
        # 🛡️ FIM DA CHAMADA CRÍTICA 🛡️
        # ============================================================================
        
        # Criar múltiplas janelas
        window_ids = create_windows(driver, config['num_windows'], config)
        
        # Fechar janela inicial
        driver.switch_to.window(driver.window_handles[0])
        driver.close()
        print("✅ Janela inicial fechada")
        
        # Ler Excel e processar URLs
        coupa_urls = read_po_numbers_from_excel(config.get('max_lines'))
        
        if coupa_urls:
            # Inicializar gerenciador FIFO
            tab_manager = FIFOTabManager(driver, window_ids, config['max_tabs_per_window'])
            
            print(f"\n🚀 Iniciando sistema de inventário...")
            print(f"📊 Processando {len(coupa_urls)} URLs")
            print(f"🪟 {config['num_windows']} janelas com máximo {config['max_tabs_per_window']} abas cada")
            print(f"⚡ {config['max_workers']} workers paralelos")
            
            # Processar URLs em paralelo
            processed_urls = 0
            total_attachments = 0
            
            with ThreadPoolExecutor(max_workers=config['max_workers']) as executor:
                # Submeter todas as tarefas
                future_to_url = {
                    executor.submit(tab_manager.process_url_with_inventory, i, url, config['max_workers']): (i, url)
                    for i, url in enumerate(coupa_urls)
                }
                
                # Processar resultados
                for future in as_completed(future_to_url):
                    i, url = future_to_url[future]
                    try:
                        result = future.result()
                        
                        if result['success']:
                            processed_urls += 1
                            total_attachments += result['attachments_found']
                            po_number = url.split('/')[-1]
                            print(f"✅ [{result['thread_name']}] PO {po_number}: {result['attachments_found']} anexos inventariados")
                        else:
                            print(f"❌ [{result['thread_name']}] Erro em URL {i+1}: {result['error']}")
                        
                        # Mostrar progresso
                        progress = (processed_urls / len(coupa_urls)) * 100
                        print(f"📊 Progresso: {processed_urls}/{len(coupa_urls)} ({progress:.1f}%)")
                        
                    except Exception as e:
                        print(f"❌ Exceção para URL {i+1}: {e}")
            
            # Resumo final
            print(f"\n🎉 Sistema de inventário concluído!")
            print(f"📊 URLs processadas: {processed_urls}/{len(coupa_urls)}")
            print(f"📎 Total de anexos inventariados: {total_attachments}")
            print(f"📄 Arquivo CSV criado: download_inventory.csv")
            print(f"\n💡 Próximo passo: Execute o microserviço de download para baixar os arquivos!")
            
        else:
            print("⚠️ Nenhuma URL encontrada no Excel.")
        
    except Exception as e:
        print(f"❌ Erro no sistema de inventário: {e}")
        
    finally:
        if driver:
            try:
                driver.quit()
                print("🔒 WebDriver fechado com sucesso!")
            except Exception as e:
                print(f"⚠️ Erro ao fechar WebDriver: {e}")


if __name__ == "__main__":
    print("🚀 Iniciando Sistema de Inventário de Downloads...")
    
    # Configuração interativa
    config = interactive_configuration()
    if config is None:
        print("👋 Programa finalizado!")
        sys.exit(0)
    
    # Executar sistema de inventário
    manage_inventory_system(config)
    print("👋 Programa finalizado!")


