"""
Sistema Integrado Refatorado - Entry Point Principal
Combina sistema de inventário + microserviço de download usando arquitetura modular
"""

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from rich.console import Console
from rich.panel import Panel

# Importar sistema refatorado
from config import config_manager
from services import InventoryService, ExcelReaderService, ProfileVerificationService
from tab_managers import FIFOTabManager
from interfaces import DownloadInfo, TabInfo
from ui import TerminalUI
from download_microservice import DownloadMicroservice

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


class IntegratedSystem:
    """Sistema integrado que combina inventário + microserviço."""
    
    def __init__(self):
        self.console = Console()
        self.driver = None
        self.tab_manager = None
        self.microservice = None
        
    def setup_edge_driver(self, headless=False):
        """Configura o driver do Edge com perfil."""
        try:
            self.console.print("🔧 Configurando driver Edge...")
            
            # Configurar opções do Edge
            options = Options()
            
            if headless:
                options.add_argument("--headless=new")
                self.console.print("   Modo headless ativado")
            
            # Configurações do perfil Edge
            if os.name != 'nt':  # macOS/Linux
                profile_path = os.path.expanduser(EDGE_PROFILE_CONFIG["macos_profile_path"])
            else:  # Windows
                profile_path = os.path.expanduser(EDGE_PROFILE_CONFIG["windows_profile_path"])
            
            if os.path.exists(profile_path):
                options.add_argument(f"--user-data-dir={profile_path}")
                options.add_argument(f"--profile-directory={EDGE_PROFILE_CONFIG['profile_directory']}")
                self.console.print(f"✅ Perfil Edge carregado: {profile_path}")
            else:
                self.console.print(f"⚠️ Diretório do perfil não encontrado: {profile_path}")
            
            # Outras configurações
            options.add_experimental_option("detach", True)
            options.add_argument("--start-maximized")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            
            # Configurações de download
            download_dir = os.path.expanduser("~/Downloads/CoupaDownloads")
            os.makedirs(download_dir, exist_ok=True)
            
            browser_prefs = {
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False,
            }
            options.add_experimental_option("prefs", browser_prefs)
            
            # Criar driver
            self.driver = webdriver.Edge(options=options)
            self.driver.implicitly_wait(10)
            
            self.console.print("✅ Driver Edge configurado com sucesso")
            return True
            
        except Exception as e:
            self.console.print(f"❌ Erro ao configurar driver Edge: {e}")
            return False
    
    def verify_profile(self):
        """Verifica se o perfil foi carregado corretamente."""
        try:
            profile_service = ProfileVerificationService()
            return profile_service.verify_profile_login_status(self.driver)
        except Exception as e:
            self.console.print(f"⚠️ Erro na verificação do perfil: {e}")
            return False
    
    def create_windows(self, num_windows):
        """Cria múltiplas janelas posicionadas na tela."""
        wait = WebDriverWait(self.driver, 10)
        window_ids = []
        
        # Obter dimensões da tela
        screen_width = self.driver.execute_script("return screen.width")
        screen_height = self.driver.execute_script("return screen.height")
        
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
        
        self.console.print(f"🪟 Criando {num_windows} janelas...")
        self.console.print(f"   Tamanho: {window_width}x{window_height}")
        self.console.print(f"   Layout: {cols} colunas")
        
        for i in range(num_windows):
            # Criar nova janela
            self.driver.switch_to.new_window('window')
            self.driver.get("about:blank")
            
            # Aguardar carregamento completo
            wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
            
            # Calcular posição da janela
            row = i // cols
            col = i % cols
            
            x = col * window_width
            y = row * window_height
            
            # Posicionar janela
            self.driver.set_window_position(x, y)
            self.driver.set_window_size(window_width, window_height)
            
            window_id = self.driver.current_window_handle
            window_ids.append(window_id)
            
            self.console.print(f"✅ Janela {i+1} criada - ID: {window_id}")
            self.console.print(f"   Posição: ({x}, {y})")
            self.console.print(f"   Tamanho: {window_width}x{window_height}")
        
        return window_ids
    
    def run_inventory_system(self, config):
        """Executa o sistema de inventário usando componentes refatorados."""
        try:
            # Configurar driver
            if not self.setup_edge_driver(config['headless']):
                return False
            
            # Verificar perfil
            if not self.verify_profile():
                self.console.print("[yellow]⚠️ Continuando mesmo com perfil não verificado...[/yellow]")
            
            # Criar janelas
            window_ids = self.create_windows(config['num_windows'])
            
            # Fechar janela inicial
            self.driver.switch_to.window(self.driver.window_handles[0])
            self.driver.close()
            self.console.print("✅ Janela inicial fechada")
            
            # Criar gerenciador de abas usando sistema refatorado
            self.tab_manager = FIFOTabManager(self.driver, window_ids, config['max_tabs_per_window'])
            
            # Ler URLs do Excel usando serviço refatorado
            excel_service = ExcelReaderService()
            po_numbers = excel_service.read_po_numbers(config.get('max_lines'))
            
            if po_numbers:
                coupa_urls = excel_service.build_coupa_urls(po_numbers)
                self.console.print(f"[blue]📊 {len(coupa_urls)} URLs para processar[/blue]")
                
                # Processar URLs em paralelo
                processed_urls = 0
                total_attachments = 0
                
                with ThreadPoolExecutor(max_workers=config['max_workers']) as executor:
                    # Submeter todas as tarefas
                    future_to_url = {
                        executor.submit(self.tab_manager.process_url_with_inventory, i, url, config['max_workers']): (i, url)
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
                                self.console.print(f"[green]✅ [{result['thread_name']}] PO {po_number}: {result['attachments_found']} anexos inventariados[/green]")
                            else:
                                self.console.print(f"[red]❌ [{result['thread_name']}] Erro em URL {i+1}: {result['error']}[/red]")
                            
                            # Mostrar progresso
                            progress = (processed_urls / len(coupa_urls)) * 100
                            self.console.print(f"[blue]📊 Progresso: {processed_urls}/{len(coupa_urls)} ({progress:.1f}%)[/blue]")
                            
                        except Exception as e:
                            self.console.print(f"[red]❌ Exceção para URL {i+1}: {e}[/red]")
                
                # Resumo final
                self.console.print(f"\n[bold green]🎉 Sistema de inventário concluído![/bold green]")
                self.console.print(f"[blue]📊 URLs processadas: {processed_urls}/{len(coupa_urls)}[/blue]")
                self.console.print(f"[blue]📎 Total de anexos inventariados: {total_attachments}[/blue]")
                self.console.print(f"[blue]📄 Arquivo CSV criado: download_inventory.csv[/blue]")
                
                return True
                
            else:
                self.console.print("[yellow]⚠️ Nenhuma URL encontrada no Excel.[/yellow]")
                return False
            
        except Exception as e:
            self.console.print(f"[red]❌ Erro no sistema de inventário: {e}[/red]")
            return False
    
    def run_microservice(self, config):
        """Executa o microserviço de download."""
        try:
            self.console.print("🔧 Iniciando microserviço de download...")
            
            # Verificar se arquivo CSV existe
            csv_path = config.get('csv_path', 'src/MyScript/download_inventory.csv')  # CORREÇÃO: Caminho correto
            if not os.path.exists(csv_path):
                self.console.print(f"[red]❌ Arquivo CSV não encontrado: {csv_path}[/red]")
                self.console.print("[yellow]💡 Execute primeiro o sistema de inventário para criar o CSV![/yellow]")
                return False
            
            # Inicializar microserviço
            self.microservice = DownloadMicroservice(
                csv_path=csv_path,
                download_dir=config.get('download_dir', os.path.expanduser("~/Downloads/CoupaDownloads")),
                max_workers=config.get('max_workers', 4)
            )
            
            # Executar microserviço
            self.microservice.run_microservice(
                batch_size=config.get('batch_size', 5),
                check_interval=config.get('check_interval', 2)
            )
            
            return True
            
        except KeyboardInterrupt:
            self.console.print("\n[yellow]⚠️ Microserviço interrompido pelo usuário[/yellow]")
            return True
        except Exception as e:
            self.console.print(f"[red]❌ Erro no microserviço: {e}[/red]")
            return False
    
    def interactive_configuration(self):
        """Menu interativo de configuração."""
        self.console.print(Panel.fit(
            "[bold blue]CONFIGURAÇÃO INTERATIVA - SISTEMA INTEGRADO[/bold blue]",
            border_style="blue"
        ))
        
        try:
            # Modo de execução
            self.console.print("\n[bold]🚀 MODO DE EXECUÇÃO:[/bold]")
            self.console.print("1 - Apenas Sistema de Inventário")
            self.console.print("2 - Apenas Microserviço de Download")
            self.console.print("3 - Executar Ambos (Recomendado)")
            choice = input("Escolha (1-3): ").strip()
            
            config = {'execution_mode': choice}
            
            if choice in ["1", "3"]:
                # Configurações do inventário
                self.console.print("\n[bold]📊 CONFIGURAÇÕES DO INVENTÁRIO:[/bold]")
                
                # Modo headless
                self.console.print("\n🔍 MODO HEADLESS:")
                self.console.print("1 - Sim (sem interface gráfica)")
                self.console.print("2 - Não (com interface gráfica)")
                headless_choice = input("Escolha (1-2): ").strip()
                config['headless'] = headless_choice == "1"
                
                # Número de janelas
                self.console.print("\n🪟 NÚMERO DE JANELAS:")
                self.console.print("1 - 2 janelas")
                self.console.print("2 - 4 janelas")
                self.console.print("3 - 6 janelas")
                self.console.print("4 - 8 janelas")
                windows_choice = input("Escolha (1-4): ").strip()
                config['num_windows'] = int(windows_choice) * 2
                
                # Abas por janela
                self.console.print("\n📄 ABAS POR JANELA:")
                self.console.print("1 - 2 abas")
                self.console.print("2 - 3 abas")
                self.console.print("3 - 5 abas")
                self.console.print("4 - 10 abas")
                tabs_choice = input("Escolha (1-4): ").strip()
                config['max_tabs_per_window'] = int(tabs_choice) * 2 + (1 if tabs_choice == "1" else 0)
                
                # Workers
                self.console.print("\n⚡ WORKERS PARALELOS:")
                self.console.print("1 - 2 workers")
                self.console.print("2 - 4 workers")
                self.console.print("3 - 6 workers")
                self.console.print("4 - 8 workers")
                workers_choice = input("Escolha (1-4): ").strip()
                config['max_workers'] = int(workers_choice) * 2
                
                # Linhas para processar
                self.console.print("\n📊 PROCESSAMENTO DO EXCEL:")
                self.console.print("1 - Processar arquivo completo")
                self.console.print("2 - Processar apenas algumas linhas (para teste)")
                lines_choice = input("Escolha (1-2): ").strip()
                
                if lines_choice == "2":
                    while True:
                        try:
                            max_lines = int(input("Quantas linhas deseja processar? (ex: 5): ").strip())
                            if max_lines > 0:
                                config['max_lines'] = max_lines
                                break
                            else:
                                self.console.print("❌ Digite um número maior que 0")
                        except ValueError:
                            self.console.print("❌ Digite um número válido")
                else:
                    config['max_lines'] = None
            
            if choice in ["2", "3"]:
                # Configurações do microserviço
                self.console.print("\n[bold]🔧 CONFIGURAÇÕES DO MICROSERVIÇO:[/bold]")
                
                # Arquivo CSV
                csv_path = input("Caminho do arquivo CSV (Enter para 'src/MyScript/download_inventory.csv'): ").strip()
                config['csv_path'] = csv_path if csv_path else "src/MyScript/download_inventory.csv"
                
                # Diretório de download
                download_dir = input("Diretório de download (Enter para '~/Downloads/CoupaDownloads'): ").strip()
                config['download_dir'] = download_dir if download_dir else os.path.expanduser("~/Downloads/CoupaDownloads")
                
                # Workers
                self.console.print("\n⚡ WORKERS PARALELOS:")
                self.console.print("1 - 2 workers")
                self.console.print("2 - 4 workers")
                self.console.print("3 - 6 workers")
                self.console.print("4 - 8 workers")
                workers_choice = input("Escolha (1-4): ").strip()
                config['microservice_workers'] = int(workers_choice) * 2
                
                # Tamanho do lote
                self.console.print("\n📦 TAMANHO DO LOTE:")
                self.console.print("1 - 3 arquivos por lote")
                self.console.print("2 - 5 arquivos por lote")
                self.console.print("3 - 10 arquivos por lote")
                self.console.print("4 - 20 arquivos por lote")
                batch_choice = input("Escolha (1-4): ").strip()
                config['batch_size'] = int(batch_choice) * 2 + (1 if batch_choice == "1" else 0)
                
                # Intervalo de verificação
                self.console.print("\n⏱️ INTERVALO DE VERIFICAÇÃO:")
                self.console.print("1 - 1 segundo")
                self.console.print("2 - 2 segundos")
                self.console.print("3 - 5 segundos")
                self.console.print("4 - 10 segundos")
                interval_choice = input("Escolha (1-4): ").strip()
                config['check_interval'] = int(interval_choice) * 2 - (1 if interval_choice == "1" else 0)
            
            # Resumo da configuração
            self.console.print(f"\n[bold green]✅ Configuração salva:[/bold green]")
            self.console.print(f"   Modo de execução: {choice}")
            if choice in ["1", "3"]:
                self.console.print(f"   Headless: {'Sim' if config['headless'] else 'Não'}")
                self.console.print(f"   Janelas: {config['num_windows']}")
                self.console.print(f"   Abas por janela: {config['max_tabs_per_window']}")
                self.console.print(f"   Workers: {config['max_workers']}")
            if choice in ["2", "3"]:
                self.console.print(f"   CSV: {config['csv_path']}")
                self.console.print(f"   Diretório: {config['download_dir']}")
                self.console.print(f"   Workers Microserviço: {config['microservice_workers']}")
                self.console.print(f"   Lote: {config['batch_size']}")
                self.console.print(f"   Intervalo: {config['check_interval']}s")
            
            return config
            
        except KeyboardInterrupt:
            self.console.print("\n[yellow]👋 Configuração cancelada pelo usuário[/yellow]")
            return None
        except Exception as e:
            self.console.print(f"\n[red]❌ Erro na configuração: {e}[/red]")
            return None
    
    def run(self, config=None):
        """Executa o sistema integrado."""
        try:
            # Usar configuração fornecida ou obter configuração interativa
            if config is None:
                config = self.interactive_configuration()
                if config is None:
                    return
            else:
                # Configuração padrão para execução via GUI
                if 'execution_mode' not in config:
                    config['execution_mode'] = "1"  # Apenas inventário por padrão
            
            execution_mode = config['execution_mode']
            
            if execution_mode in ["1", "3"]:
                # Executar sistema de inventário
                self.console.print("\n[bold blue]🚀 Iniciando Sistema de Inventário...[/bold blue]")
                success = self.run_inventory_system(config)
                
                if not success:
                    self.console.print("[red]❌ Sistema de inventário falhou![/red]")
                    return
                
                if execution_mode == "1":
                    self.console.print("[green]✅ Sistema de inventário concluído![/green]")
                    return
            
            if execution_mode in ["2", "3"]:
                # Executar microserviço
                self.console.print("\n[bold blue]🔧 Iniciando Microserviço de Download...[/bold blue]")
                self.run_microservice(config)
            
            self.console.print("[green]✅ Sistema integrado concluído![/green]")
            
        except KeyboardInterrupt:
            self.console.print("\n[yellow]⚠️ Sistema interrompido pelo usuário[/yellow]")
        except Exception as e:
            self.console.print(f"[red]❌ Erro no sistema integrado: {e}[/red]")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Limpa recursos do sistema."""
        if self.driver:
            try:
                self.driver.quit()
                self.console.print("[green]🔒 WebDriver fechado com sucesso![/green]")
            except Exception as e:
                self.console.print(f"[yellow]⚠️ Erro ao fechar WebDriver: {e}[/yellow]")
        
        if self.microservice:
            try:
                self.microservice.stop()
                self.console.print("[green]🔒 Microserviço finalizado![/green]")
            except Exception as e:
                self.console.print(f"[yellow]⚠️ Erro ao finalizar microserviço: {e}[/yellow]")


def main():
    """Função principal do sistema integrado."""
    console = Console()
    console.print("[bold blue]🚀 Iniciando Sistema Integrado Refatorado...[/bold blue]")
    
    try:
        system = IntegratedSystem()
        system.run()
    except Exception as e:
        console.print(f"[red]❌ Erro crítico: {e}[/red]")
    finally:
        console.print("[yellow]👋 Sistema finalizado![/yellow]")


if __name__ == "__main__":
    main()
