#!/usr/bin/env python3
"""
Sistema de Inventário de Downloads - Versão Corrigida
Usa o sistema refatorado com gestão de abas melhorada
"""

import os
import sys
import time
import threading
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
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

# Importar sistema refatorado
from config import config_manager
from download_services import InventoryService, ExcelReaderService
from browser_tab_manager import FIFOTabManager
from ui_component_interfaces import DownloadInfo

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


def setup_edge_driver(headless=False):
    """Configura o driver do Edge com perfil."""
    try:
        print("🔧 Configurando driver Edge...")
        
        # Configurar opções do Edge
        options = Options()
        
        if headless:
            options.add_argument("--headless")
            print("   Modo headless ativado")
        
        # Configurações do perfil Edge
        profile_path = os.path.expanduser(EDGE_PROFILE_CONFIG["macos_profile_path"])
        options.add_argument(f"--user-data-dir={profile_path}")
        options.add_argument(f"--profile-directory={EDGE_PROFILE_CONFIG['profile_directory']}")
        
        # Configurações de download
        download_dir = os.path.expanduser("~/Downloads/CoupaDownloads")
        os.makedirs(download_dir, exist_ok=True)
        options.add_argument(f"--download-directory={download_dir}")
        
        # Outras configurações
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        
        # Configurações de download
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
        }
        options.add_experimental_option("prefs", prefs)
        
        # Criar driver
        driver = webdriver.Edge(options=options)
        driver.implicitly_wait(10)
        
        print("✅ Driver Edge configurado com sucesso")
        return driver
        
    except Exception as e:
        print(f"❌ Erro ao configurar driver Edge: {e}")
        return None


def verify_edge_profile_login_status(driver):
    """
    🛡️ FUNÇÃO CRÍTICA - NÃO ALTERAR SEM AUTORIZAÇÃO EXPLÍCITA DO USUÁRIO 🛡️
    
    Esta função verifica se o perfil do Edge foi carregado corretamente
    e se o usuário está logado no Coupa. É ESSENCIAL para o funcionamento.
    
    ⚠️  ATENÇÃO: Qualquer alteração nesta função pode quebrar a detecção de perfil
    ⚠️  Se você precisa modificar algo aqui, CONSULTE O USUÁRIO PRIMEIRO
    """
    try:
        print("🔍 Verificando status do perfil Edge...")
        
        # Tentar acessar uma página que requer login para verificar se o perfil está funcionando
        driver.get(EDGE_PROFILE_CONFIG["login_check_url"])
        time.sleep(EDGE_PROFILE_CONFIG["login_check_timeout"])  # Aguardar carregamento
        
        # Verificar se há elementos de login (indicando que não estamos logados)
        login_elements = []
        for selector in EDGE_PROFILE_CONFIG["login_selectors"]:
            login_elements.extend(driver.find_elements("css selector", selector))
        
        if login_elements:
            print(PROFILE_STATUS_MESSAGES["not_logged_in"])
            return False
        else:
            print(PROFILE_STATUS_MESSAGES["logged_in"])
            return True
            
    except Exception as e:
        print(PROFILE_STATUS_MESSAGES["check_failed"].format(error=e))
        return False


def interactive_configuration():
    """Configuração interativa do sistema."""
    console = Console()
    
    console.print(Panel.fit(
        "[bold blue]CONFIGURAÇÃO INTERATIVA - SISTEMA DE INVENTÁRIO[/bold blue]",
        border_style="blue"
    ))
    
    try:
        # Modo headless
        console.print("\n[bold]🔍 MODO HEADLESS:[/bold]")
        console.print("1 - Sim (sem interface gráfica)")
        console.print("2 - Não (com interface gráfica)")
        headless_choice = input("Escolha (1-2): ").strip()
        headless = headless_choice == "1"
        
        # Número de janelas
        console.print("\n[bold]🪟 NÚMERO DE JANELAS:[/bold]")
        console.print("1 - 1 janela")
        console.print("2 - 2 janelas")
        console.print("3 - 3 janelas")
        console.print("4 - 4 janelas")
        windows_choice = input("Escolha (1-4): ").strip()
        num_windows = int(windows_choice)
        
        # Abas por janela
        console.print("\n[bold]📄 ABAS POR JANELA:[/bold]")
        console.print("1 - 1 aba")
        console.print("2 - 2 abas")
        console.print("3 - 3 abas")
        console.print("4 - 4 abas")
        tabs_choice = input("Escolha (1-4): ").strip()
        max_tabs_per_window = int(tabs_choice)
        
        # Workers
        console.print("\n[bold]⚡ WORKERS PARALELOS:[/bold]")
        console.print("1 - 2 workers")
        console.print("2 - 4 workers")
        console.print("3 - 6 workers")
        console.print("4 - 8 workers")
        workers_choice = input("Escolha (1-4): ").strip()
        max_workers = int(workers_choice) * 2
        
        # Timeout
        console.print("\n[bold]⏱️ TIMEOUT (segundos):[/bold]")
        console.print("1 - 10 segundos")
        console.print("2 - 15 segundos")
        console.print("3 - 20 segundos")
        timeout_choice = input("Escolha (1-3): ").strip()
        timeout = int(timeout_choice) * 5 + 5
        
        config = {
            'headless': headless,
            'num_windows': num_windows,
            'max_tabs_per_window': max_tabs_per_window,
            'max_workers': max_workers,
            'timeout': timeout
        }
        
        console.print(f"\n[bold green]✅ Configuração salva:[/bold green]")
        console.print(f"   Modo headless: {'Sim' if headless else 'Não'}")
        console.print(f"   Janelas: {num_windows}")
        console.print(f"   Abas por janela: {max_tabs_per_window}")
        console.print(f"   Workers: {max_workers}")
        console.print(f"   Timeout: {timeout}s")
        
        return config
        
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Configuração cancelada pelo usuário[/yellow]")
        return None
    except Exception as e:
        console.print(f"\n[red]❌ Erro na configuração: {e}[/red]")
        return None


def manage_inventory_system(config):
    """Gerencia o sistema de inventário usando o sistema refatorado."""
    console = Console()
    
    try:
        # Configurar driver
        driver = setup_edge_driver(config['headless'])
        if not driver:
            console.print("[red]❌ Falha ao configurar driver Edge[/red]")
            return
        
        # Verificar perfil
        if not verify_edge_profile_login_status(driver):
            console.print("[yellow]⚠️ Continuando mesmo com perfil não verificado...[/yellow]")
        
        # Criar janelas
        window_ids = [driver.current_window_handle]
        for i in range(config['num_windows'] - 1):
            driver.execute_script("window.open('');")
            window_ids.append(driver.window_handles[-1])
        
        console.print(f"[green]✅ {len(window_ids)} janelas criadas[/green]")
        
        # Criar gerenciador de abas usando sistema refatorado
        tab_manager = FIFOTabManager(driver, window_ids, config['max_tabs_per_window'])
        
        # Ler URLs do Excel
        excel_service = ExcelReaderService()
        po_numbers = excel_service.read_po_numbers()
        
        if po_numbers:
            coupa_urls = excel_service.build_coupa_urls(po_numbers)
            console.print(f"[blue]📊 {len(coupa_urls)} URLs para processar[/blue]")
            
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
                            console.print(f"[green]✅ [{result['thread_name']}] PO {po_number}: {result['attachments_found']} anexos inventariados[/green]")
                        else:
                            console.print(f"[red]❌ [{result['thread_name']}] Erro em URL {i+1}: {result['error']}[/red]")
                        
                        # Mostrar progresso
                        progress = (processed_urls / len(coupa_urls)) * 100
                        console.print(f"[blue]📊 Progresso: {processed_urls}/{len(coupa_urls)} ({progress:.1f}%)[/blue]")
                        
                    except Exception as e:
                        console.print(f"[red]❌ Exceção para URL {i+1}: {e}[/red]")
            
            # Resumo final
            console.print(f"\n[bold green]🎉 Sistema de inventário concluído![/bold green]")
            console.print(f"[blue]📊 URLs processadas: {processed_urls}/{len(coupa_urls)}[/blue]")
            console.print(f"[blue]📎 Total de anexos inventariados: {total_attachments}[/blue]")
            console.print(f"[blue]📄 Arquivo CSV criado: download_inventory.csv[/blue]")
            console.print(f"\n[yellow]💡 Próximo passo: Execute o microserviço de download para baixar os arquivos![/yellow]")
            
        else:
            console.print("[yellow]⚠️ Nenhuma URL encontrada no Excel.[/yellow]")
        
    except Exception as e:
        console.print(f"[red]❌ Erro no sistema de inventário: {e}[/red]")
        
    finally:
        if driver:
            try:
                driver.quit()
                console.print("[green]🔒 WebDriver fechado com sucesso![/green]")
            except Exception as e:
                console.print(f"[yellow]⚠️ Erro ao fechar WebDriver: {e}[/yellow]")


if __name__ == "__main__":
    console = Console()
    console.print("[bold blue]🚀 Iniciando Sistema de Inventário de Downloads...[/bold blue]")
    
    # Configuração interativa
    config = interactive_configuration()
    if config is None:
        console.print("[yellow]👋 Programa finalizado![/yellow]")
        sys.exit(0)
    
    # Executar sistema de inventário
    manage_inventory_system(config)
    console.print("[yellow]👋 Programa finalizado![/yellow]")

