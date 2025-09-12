"""
Função para gerenciar múltiplas abas no Edge WebDriver
Cria 2 abas, exibe seus IDs e permite ao usuário escolher qual fechar
"""

import os
import sys
import random
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, InvalidSessionIdException, NoSuchWindowException


def is_session_valid(driver):
    """
    Verifica se a sessão do WebDriver ainda é válida.
    
    Args:
        driver: Instância do WebDriver
        
    Returns:
        bool: True se a sessão é válida, False caso contrário
    """
    try:
        # Tenta obter o título da página atual
        driver.title
        return True
    except (InvalidSessionIdException, WebDriverException):
        return False


def is_browser_completely_closed(driver):
    """
    Verifica se o navegador foi completamente fechado (todas as abas fechadas).
    
    Args:
        driver: Instância do WebDriver
        
    Returns:
        bool: True se o navegador foi completamente fechado, False caso contrário
    """
    try:
        # Se não conseguimos obter window_handles, o navegador foi fechado
        handles = driver.window_handles
        print(f"🔍 Debug: window_handles encontradas: {len(handles)}")
        return len(handles) == 0
    except (InvalidSessionIdException, WebDriverException) as e:
        # Se há exceção ao tentar obter window_handles, o navegador foi fechado
        print(f"🔍 Debug: Exceção ao obter window_handles: {e}")
        return True


def safe_close_tab(driver, tab_id, tab_name):
    """
    Fecha uma aba de forma segura, verificando se o navegador foi fechado.
    
    Args:
        driver: Instância do WebDriver
        tab_id: ID da aba a ser fechada
        tab_name: Nome da aba para debug
        
    Returns:
        bool: True se a aba foi fechada com sucesso, False se o navegador foi fechado
    """
    try:
        if tab_id not in driver.window_handles:
            print(f"❌ {tab_name} já foi fechada!")
            return True
            
        print(f"🔍 Debug: Fechando {tab_name} (ID: {tab_id})")
        print(f"🔍 Debug: Janelas antes de fechar: {driver.window_handles}")
        
        # Verificar se esta é a última janela
        if len(driver.window_handles) == 1:
            print(f"⚠️  {tab_name} é a última janela! Fechá-la encerrará o navegador completamente.")
            confirm = input("Deseja continuar? (s/n): ").strip().lower()
            if confirm not in ['s', 'sim', 'y', 'yes']:
                print("❌ Operação cancelada.")
                return True
        
        driver.switch_to.window(tab_id)
        driver.close()
        print(f"✅ {tab_name} fechada com sucesso!")
        
        # Pequeno delay para permitir que o sistema processe o fechamento
        time.sleep(0.5)
        
        # Verificar se o navegador foi completamente fechado
        if is_browser_completely_closed(driver):
            print("🌐 Navegador foi completamente fechado!")
            return False
            
        return True
        
    except (InvalidSessionIdException, WebDriverException) as e:
        print(f"🌐 Navegador foi completamente fechado! Erro: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro ao fechar {tab_name}: {e}")
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


def load_urls_in_windows(driver, tab1_id, tab2_id, coupa_urls):
    """
    Carrega URLs do Coupa em novas abas dentro das janelas, revezando entre elas.
    
    Args:
        driver: Instância do WebDriver
        tab1_id: ID da primeira janela
        tab2_id: ID da segunda janela
        coupa_urls: Lista de URLs para carregar
    """
    wait = WebDriverWait(driver, 10)
    
    print(f"\n🚀 Iniciando carregamento de {len(coupa_urls)} URLs do Coupa em novas abas...")
    
    # Dicionário para armazenar IDs das abas criadas
    created_tabs = {
        'window1_tabs': [],  # Abas da janela 1
        'window2_tabs': []   # Abas da janela 2
    }
    
    for i, url in enumerate(coupa_urls):
        # Determinar qual janela usar (revezar)
        if i % 2 == 0:
            # Par: usar janela 1
            current_window_id = tab1_id
            window_name = "Janela 1"
            tab_list_key = 'window1_tabs'
        else:
            # Ímpar: usar janela 2
            current_window_id = tab2_id
            window_name = "Janela 2"
            tab_list_key = 'window2_tabs'
        
        try:
            # Mudar para a janela atual
            driver.switch_to.window(current_window_id)
            
            # Criar nova aba dentro da janela atual
            driver.execute_script("window.open('');")
            
            # Mudar para a nova aba criada (última aba da lista)
            driver.switch_to.window(driver.window_handles[-1])
            new_tab_id = driver.current_window_handle
            
            # Carregar URL na nova aba
            print(f"📄 Criando nova aba em {window_name} para URL {i+1}/{len(coupa_urls)}")
            print(f"   Nova aba ID: {new_tab_id}")
            print(f"   URL: {url}")
            
            driver.get(url)
            
            # Aguardar carregamento completo
            wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
            
            # Registrar ID da aba criada
            created_tabs[tab_list_key].append({
                'tab_id': new_tab_id,
                'url': url,
                'url_number': i+1
            })
            
            print(f"✅ URL {i+1} carregada com sucesso em nova aba de {window_name}")
            print(f"   Aba ID: {new_tab_id}")
            
            # Pequeno delay entre carregamentos
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Erro ao carregar URL {i+1} em {window_name}: {e}")
            continue
    
    # Exibir resumo das abas criadas
    print(f"\n🎉 Carregamento concluído! {len(coupa_urls)} URLs processadas.")
    print("\n📋 RESUMO DAS ABAS CRIADAS:")
    print("=" * 50)
    
    print(f"\n🪟 JANELA 1 ({len(created_tabs['window1_tabs'])} abas):")
    for tab_info in created_tabs['window1_tabs']:
        print(f"   Aba {tab_info['url_number']} - ID: {tab_info['tab_id']}")
        print(f"   URL: {tab_info['url']}")
    
    print(f"\n🪟 JANELA 2 ({len(created_tabs['window2_tabs'])} abas):")
    for tab_info in created_tabs['window2_tabs']:
        print(f"   Aba {tab_info['url_number']} - ID: {tab_info['tab_id']}")
        print(f"   URL: {tab_info['url']}")
    
    print("=" * 50)
    
    return created_tabs


def interactive_configuration():
    """
    Menu interativo de configuração do Edge WebDriver.
    
    Returns:
        dict: Configurações escolhidas pelo usuário
    """
    print(" CONFIGURAÇÃO INTERATIVA DO EDGE WEBDRIVER")
    print("=" * 50)
    
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
    
    # 4. Número de linhas para processar
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
    
    # 5. Resumo da configuração
    print("\n📋 RESUMO DA CONFIGURAÇÃO:")
    print("=" * 30)
    print(f"Headless: {'Sim' if config['headless'] else 'Não'}")
    print(f"Perfil: {config['profile_mode']}")
    print(f"Stacktrace: {'Oculto' if config['hide_stacktrace'] else 'Completo'}")
    max_lines_text = 'Todas' if config['max_lines'] is None else f'{config["max_lines"]} linhas'
    print(f"Linhas Excel: {max_lines_text}")
    
    confirm = input("\n✅ Confirmar configuração? (s/n): ").strip().lower()
    if confirm not in ['s', 'sim', 'y', 'yes']:
        print("❌ Configuração cancelada.")
        return None
    
    return config


def manage_edge_tabs(config):
    """
    Cria 2 janelas no Edge WebDriver com configurações personalizadas.
    
    Args:
        config (dict): Configurações escolhidas pelo usuário
    """
    driver = None
    
    try:
        # Configurar o Edge WebDriver EXATAMENTE como no projeto principal
        options = webdriver.EdgeOptions()
        
        # Set profile options FIRST (como no projeto principal)
        if config['profile_mode'] != "none":
            # Usar o mesmo caminho do projeto principal
            if os.name == 'nt':  # Windows
                profile_dir = os.path.expanduser("%LOCALAPPDATA%/Microsoft/Edge/User Data")
            else:  # macOS/Linux
                profile_dir = os.path.expanduser("~/Library/Application Support/Microsoft Edge")
            
            options.add_argument(f"--user-data-dir={profile_dir}")
            options.add_argument(f"--profile-directory=Default")
        
        # Ensure browser remains open after script ends (for session persistency)
        options.add_experimental_option("detach", True)
        
        # Other options after profile setup
        if config['profile_mode'] == "minimal":
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            print("🍪 Perfil mínimo carregado - apenas cookies e logins")
        elif config['profile_mode'] == "full":
            # options.add_argument("--disable-extensions")  # Commented out to allow profile extensions
            print("👤 Perfil completo carregado")
        
        options.add_argument("--start-maximized")
        
        # Browser preferences (como no projeto principal)
        browser_prefs = {
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
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
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option("useAutomationExtension", False)
                
                if config['hide_stacktrace']:
                    options.add_argument("--log-level=3")
                    options.add_argument("--silent")
                    options.add_argument("--disable-logging")
                
                if config['headless']:
                    options.add_argument("--headless=new")
                
                driver = webdriver.Edge(options=options)
                print("✅ Using Edge WebDriver without profile")
            else:
                raise
        
        # Carregar uma página na janela inicial para garantir que o perfil seja aplicado
        driver.get("about:blank")  # Página em branco para carregar o perfil

        # Aguardar carregamento completo da janela inicial
        wait = WebDriverWait(driver, 10)
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
        print("✅ Janela inicial com perfil carregada completamente")

        # Obter dimensões da tela
        screen_width = driver.execute_script("return screen.width")
        screen_height = driver.execute_script("return screen.height")
        window_width = screen_width // 2  # 50% da largura
        window_height = screen_height // 2  # 50% da altura

        # Posicionar janela inicial (canto inferior esquerdo)
        driver.set_window_position(0, screen_height - window_height)
        driver.set_window_size(window_width, window_height)
        print("📍 Janela inicial posicionada (canto inferior esquerdo)")

        # Delay de 2 segundos antes de criar as 2 janelas
        print("⏳ Aguardando 2 segundos antes de criar as janelas...")
        time.sleep(2)

        # Criar primeira janela (página em branco) - canto superior esquerdo
        driver.switch_to.new_window('window')
        driver.get("about:blank")

        # Aguardar carregamento completo
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

        # Posicionar janela 1
        driver.set_window_position(0, 0)
        driver.set_window_size(window_width, window_height)

        tab1_id = driver.current_window_handle
        print(f"✅ Janela 1 criada - ID: {tab1_id}")
        print(f"   URL: {driver.current_url}")
        print("📍 Janela 1 posicionada (canto superior esquerdo)")

        # Criar segunda janela (página em branco) - canto superior direito
        driver.switch_to.new_window('window')
        driver.get("about:blank")

        # Aguardar carregamento completo
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

        # Posicionar janela 2
        driver.set_window_position(screen_width - window_width, 0)
        driver.set_window_size(window_width, window_height)

        tab2_id = driver.current_window_handle
        print(f"✅ Janela 2 criada - ID: {tab2_id}")
        print(f"   URL: {driver.current_url}")
        print("📍 Janela 2 posicionada (canto superior direito)")

        # Delay de 2 segundos antes de fechar a janela inicial
        print("⏳ Aguardando 2 segundos antes de fechar janela inicial...")
        time.sleep(2)

        # Fechar janela inicial
        driver.switch_to.window(driver.window_handles[0])
        driver.close()
        print("✅ Janela inicial fechada")
        
        # NOVA FUNCIONALIDADE: Ler Excel e carregar URLs do Coupa
        coupa_urls = read_po_numbers_from_excel(config.get('max_lines'))
        
        created_tabs = None
        if coupa_urls:
            # Carregar URLs nas janelas em novas abas
            created_tabs = load_urls_in_windows(driver, tab1_id, tab2_id, coupa_urls)
        else:
            print("⚠️ Nenhuma URL encontrada no Excel. Continuando com janelas vazias.")
        
        # Exibir informações das janelas
        print("\n" + "="*50)
        print("📋 RESUMO DAS JANELAS CRIADAS:")
        print("="*50)
        print(f"Janela 1 - ID: {tab1_id} (Página em Branco - Superior Esquerdo)")
        print(f"Janela 2 - ID: {tab2_id} (Página em Branco - Superior Direito)")
        
        if created_tabs:
            total_tabs = len(created_tabs['window1_tabs']) + len(created_tabs['window2_tabs'])
            print(f"Total de abas criadas: {total_tabs}")
            print(f"  - Janela 1: {len(created_tabs['window1_tabs'])} abas")
            print(f"  - Janela 2: {len(created_tabs['window2_tabs'])} abas")
        
        print("="*50)
        
        # Loop para escolha do usuário
        while True:
            # Verificar quais abas ainda estão abertas
            available_tabs = []
            if tab1_id in driver.window_handles:
                available_tabs.append("1")
            if tab2_id in driver.window_handles:
                available_tabs.append("2")
            
            print("\n🎯 ESCOLHA UMA OPÇÃO:")
            if "1" in available_tabs:
                print("1 - Fechar Aba 1")
            if "2" in available_tabs:
                print("2 - Fechar Aba 2")
            print("0 - Fechar navegador completamente")
            
            # Se não há mais abas para fechar, sair do loop
            if not available_tabs:
                print("⚠️  Todas as abas foram fechadas!")
                break
            
            try:
                # Criar string de opções disponíveis
                valid_options = available_tabs + ["0"]
                options_text = ", ".join(valid_options)
                choice = input(f"\nDigite sua escolha ({options_text}): ").strip()
                
                if choice == "1":
                    if tab1_id in driver.window_handles:
                        driver.switch_to.window(tab1_id)
                        driver.close()
                        print("✅ Aba 1 fechada com sucesso!")
                        
                        # Verificar se ainda há abas abertas
                        if len(driver.window_handles) == 1:
                            print("📝 Restou apenas 1 aba aberta.")
                            remaining_tab = driver.window_handles[0]
                            driver.switch_to.window(remaining_tab)
                            print(f"   Aba restante - ID: {remaining_tab}")
                            print(f"   URL: {driver.current_url}")
                        elif len(driver.window_handles) == 0:
                            print("⚠️  Todas as abas foram fechadas!")
                            break
                        else:
                            print(f"📝 Restam {len(driver.window_handles)} abas abertas.")
                            # Continuar o loop para permitir mais escolhas
                            continue
                    else:
                        print("❌ Aba 1 já foi fechada!")
                        
                elif choice == "2":
                    if tab2_id in driver.window_handles:
                        driver.switch_to.window(tab2_id)
                        driver.close()
                        print("✅ Aba 2 fechada com sucesso!")
                        
                        # Verificar se ainda há abas abertas
                        if len(driver.window_handles) == 1:
                            print("📝 Restou apenas 1 aba aberta.")
                            remaining_tab = driver.window_handles[0]
                            driver.switch_to.window(remaining_tab)
                            print(f"   Aba restante - ID: {remaining_tab}")
                            print(f"   URL: {driver.current_url}")
                        elif len(driver.window_handles) == 0:
                            print("⚠️  Todas as abas foram fechadas!")
                            break
                        else:
                            print(f"📝 Restam {len(driver.window_handles)} abas abertas.")
                            # Continuar o loop para permitir mais escolhas
                            continue
                    else:
                        print("❌ Aba 2 já foi fechada!")
                        
                elif choice == "0":
                    print("🔄 Fechando navegador completamente...")
                    break
                    
                else:
                    print(f"❌ Opção inválida! Digite apenas uma das opções disponíveis: {options_text}")
                    
            except KeyboardInterrupt:
                print("\n⚠️  Operação cancelada pelo usuário.")
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
                print(f"⚠️  Erro ao fechar WebDriver: {e}")


if __name__ == "__main__":
    print("🚀 Iniciando gerenciador de janelas do Edge...")
    
    # Configuração interativa
    config = interactive_configuration()
    if config is None:
        print("👋 Programa finalizado!")
        sys.exit(0)
    
    # Executar com configurações
    manage_edge_tabs(config)
    print("👋 Programa finalizado!")
