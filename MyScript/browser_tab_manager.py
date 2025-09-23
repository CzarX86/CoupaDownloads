"""
Módulo de Gerenciamento de Abas - Implementa estratégias de gerenciamento
Aplica Strategy Pattern e Open/Closed Principle
"""

import os
import time
import threading
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from ui_component_interfaces import ITabManager, TabInfo, DownloadInfo
from download_services import InventoryService, ProfileVerificationService
from config import config_manager
try:
    # Prefer advanced config selectors when available
    from config_advanced import get_config as get_adv_config
except Exception:
    get_adv_config = None


class BaseTabManager(ITabManager):
    """
    Gerenciador base de abas - implementa funcionalidades comuns
    Open/Closed Principle: aberto para extensão, fechado para modificação
    """
    
    def __init__(self, driver: webdriver.Edge, window_ids: List[str]):
        self.driver = driver
        self.window_ids = window_ids
        self.lock = threading.Lock()
        self.active_tabs: Dict[int, TabInfo] = {}
        
        # Serviços injetados (Dependency Injection)
        self.inventory_service = InventoryService()
        self.profile_verifier = ProfileVerificationService()
        
        # Configurações de seletores de anexos
        # Fallback padrão
        self.attachment_selector = (
            "span[aria-label*='file attachment'], "
            "span[role='button'][aria-label*='file attachment'], "
            "span[title*='.pdf'], span[title*='.docx'], span[title*='.msg']"
        )
        self.attachment_selector = "".join(self.attachment_selector)
        # Tentar usar seletores mais robustos do config avançado
        try:
            if get_adv_config is not None:
                self.attachment_selector = get_adv_config().get_attachment_selectors()
        except Exception:
            pass
        self.allowed_extensions = [".pdf", ".msg", ".docx", ".xlsx", ".txt", ".jpg", ".png", ".zip", ".rar", ".csv", ".xml"]
    
    def create_tab_for_url(self, url_index: int, url: str, 
                          window_id: str, window_name: str) -> Optional[TabInfo]:
        """Cria uma aba para uma URL específica."""
        try:
            with self.lock:
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

            # Early error detection before full readyState wait (optional)
            try:
                from src.core.config import Config as _Cfg
                if getattr(_Cfg, 'EARLY_ERROR_CHECK_BEFORE_READY', True):
                    t0 = time.time()
                    found = False
                    timeout_s = float(getattr(_Cfg, 'ERROR_PAGE_CHECK_TIMEOUT', 4))
                    markers = [m.lower() for m in getattr(_Cfg, 'ERROR_PAGE_MARKERS', []) or []]
                    while time.time() - t0 < timeout_s:
                        page = (self.driver.page_source or '').lower()
                        if any(m in page for m in markers):
                            found = True
                            break
                        time.sleep(0.1)
                    if found:
                        print(f"🚫 [" + threading.current_thread().name + f"] Error page detected early for URL {url_index+1}")
                        return None
            except Exception:
                # Fail silent on early detection path; proceed to normal wait
                pass

            # Aguardar carregamento (normal load wait)
            wait = WebDriverWait(self.driver, 10)
            wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
            
            # Registrar aba ativa
            with self.lock:
                tab_info = TabInfo(
                    tab_id=new_tab_id,
                    url=url,
                    url_index=url_index,
                    window_name=window_name,
                    window_id=window_id,
                    created_at=time.time()
                )
                
                self.active_tabs[url_index] = tab_info
            
            print(f"✅ [{threading.current_thread().name}] URL {url_index+1} carregada com sucesso")
            return tab_info
                
        except Exception as e:
            print(f"❌ [{threading.current_thread().name}] Erro ao criar aba para URL {url_index+1}: {e}")
            return None
    
    def inventory_attachments_for_tab(self, tab_id: str, po_number: str) -> int:
        """Faz inventário dos anexos de uma aba e salva URLs no CSV."""
        thread_name = threading.current_thread().name
        
        try:
            with self.lock:
                self.driver.switch_to.window(tab_id)
                
                # Aguardar elementos carregarem
                wait = WebDriverWait(self.driver, 15)  # Usar timeout maior como no sistema principal
                wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
                
                # Buscar anexos usando o mesmo seletor do sistema principal
                try:
                    wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, self.attachment_selector))
                    attachments = self.driver.find_elements(By.CSS_SELECTOR, self.attachment_selector)
                except Exception as e:
                    print(f"⚠️ [{thread_name}] Timeout aguardando anexos: {e}")
                    attachments = []
            
            if attachments:
                print(f"🔍 [{thread_name}] Inventariando {len(attachments)} anexos para PO {po_number}")
                
                # Coletar informações dos anexos usando a mesma lógica do sistema principal
                for i, attachment in enumerate(attachments):
                    try:
                        # Extrair nome do arquivo usando a mesma estratégia do sistema principal
                        filename = self._extract_filename_from_element(attachment)
                        
                        if not filename:
                            print(f"⚠️ [{thread_name}] Não foi possível determinar nome do arquivo para anexo {i+1}")
                            continue
                        
                        # Para o inventário, não precisamos da URL real, apenas coletar informações
                        # O sistema principal faz o download via click, não via URL direta
                        download_url = f"https://unilever.coupahost.com/attachment/{po_number}/{filename}"
                        
                        # Determinar tipo de arquivo
                        file_type = self._determine_file_type(filename)
                        
                        print(f"🔍 [{thread_name}] Anexo {i+1}: {filename}")
                        
                        # Criar DownloadInfo e adicionar ao inventário
                        download_info = DownloadInfo(
                            po_number=po_number,
                            url=download_url,
                            filename=filename,
                            file_type=file_type,
                            created_at=time.strftime('%Y-%m-%d %H:%M:%S')
                        )
                        
                        success = self.inventory_service.add_download_url(download_info)
                        if success:
                            print(f"✅ [{thread_name}] Anexo coletado: {filename}")
                        else:
                            print(f"❌ [{thread_name}] Falha ao salvar: {filename}")
                            
                    except Exception as e:
                        print(f"❌ [{thread_name}] Erro ao processar anexo {i+1}: {e}")
                
                return len(attachments)
            else:
                print(f"📄 [{thread_name}] Nenhum anexo encontrado para PO {po_number}")
                return 0
                
        except Exception as e:
            print(f"❌ [{thread_name}] Erro ao fazer inventário: {e}")
            return 0
    
    def _extract_filename_from_element(self, attachment) -> Optional[str]:
        """
        Extrai nome do arquivo de um elemento usando a mesma estratégia do sistema principal.
        """
        # Strategy 1: Check text content for a filename with a valid extension
        text_content = attachment.text.strip()
        if text_content and any(
            ext in text_content.lower() for ext in self.allowed_extensions
        ):
            return text_content

        # Strategy 2: Check 'aria-label' for descriptive text
        aria_label = attachment.get_attribute("aria-label")
        if aria_label and "file attachment" in aria_label:
            filename = aria_label.split("file attachment")[0].strip()
            if filename:  # Ensure it's not empty
                return filename

        # Strategy 3: Check 'title' attribute
        title = attachment.get_attribute("title")
        if title:
            # Check if title itself could be a filename
            if any(ext in title.lower() for ext in self.allowed_extensions):
                return title

        # Strategy 4: Check 'href' for a downloadable link
        href = attachment.get_attribute("href")
        if href and href.strip() not in ("#", ""):
            # Check if the href contains something that looks like a file
            basename = os.path.basename(href)
            if "." in basename:  # A simple check for an extension
                return basename

        return None

    def _determine_file_type(self, filename: str) -> str:
        """Determina o tipo de arquivo baseado na extensão."""
        filename_lower = filename.lower()
        if filename_lower.endswith('.pdf'):
            return "pdf"
        elif filename_lower.endswith(('.doc', '.docx')):
            return "document"
        elif filename_lower.endswith(('.xls', '.xlsx')):
            return "spreadsheet"
        elif filename_lower.endswith('.msg'):
            return "email"
        else:
            return "unknown"
    
    def _is_error_page(self, tab_id: str) -> bool:
        """
        Verifica se a página atual é uma página de erro.
        Baseado na lógica do sistema principal: src/core/downloader.py linha 177
        """
        try:
            with self.lock:
                self.driver.switch_to.window(tab_id)
                
            # Verificar se contém a mensagem de erro do Coupa
            page_source = (self.driver.page_source or '').lower()
            try:
                from src.core.config import Config as _Cfg
                markers = [m.lower() for m in getattr(_Cfg, 'ERROR_PAGE_MARKERS', []) or []]
                error_detected = any(m in page_source for m in markers)
            except Exception:
                error_detected = "oops! we couldn't find what you wanted" in page_source
            
            if error_detected:
                print(f"🚫 Página de erro detectada para aba {tab_id}")
            
            return error_detected
            
        except Exception as e:
            print(f"⚠️ Erro ao verificar página de erro: {e}")
            return False
    
    def close_tab_and_create_new(self, url_index: int, new_url: str, 
                               new_url_index: int) -> Optional[TabInfo]:
        """Fecha uma aba e cria uma nova (implementação base)."""
        try:
            with self.lock:
                if url_index in self.active_tabs:
                    tab_info = self.active_tabs[url_index]
                    window_id = tab_info.window_id
                    window_name = tab_info.window_name
                    
                    # Fechar aba atual
                    if tab_info.tab_id in self.driver.window_handles:
                        self.driver.switch_to.window(tab_info.tab_id)
                        self.driver.close()
                        print(f"🔒 [{threading.current_thread().name}] Aba {url_index+1} fechada")
                    
                    # Remover das abas ativas
                    del self.active_tabs[url_index]
                    
                    # Criar nova aba na mesma janela se URL fornecida
                    if new_url and new_url_index >= 0:
                        new_tab_info = self.create_tab_for_url(new_url_index, new_url, window_id, window_name)
                        return new_tab_info
            
            return None
            
        except Exception as e:
            print(f"❌ [{threading.current_thread().name}] Erro ao fechar/criar aba: {e}")
            return None
    
    def get_active_tab_count(self) -> int:
        """Retorna o número de abas ativas."""
        with self.lock:
            return len(self.active_tabs)
    
    def get_active_tabs_info(self) -> Dict[int, TabInfo]:
        """Retorna informações sobre abas ativas."""
        with self.lock:
            return dict(self.active_tabs)


class FIFOTabManager(BaseTabManager):
    """
    Gerenciador FIFO de abas - implementa controle FIFO por janela
    Strategy Pattern: estratégia específica para controle FIFO
    """
    
    def __init__(self, driver: webdriver.Edge, window_ids: List[str], max_tabs_per_window: int = 3):
        super().__init__(driver, window_ids)
        self.max_tabs_per_window = max_tabs_per_window
        
        # Controle FIFO por janela
        self.window_tab_queues = {window_id: [] for window_id in window_ids}
    
    def get_available_window(self) -> Optional[str]:
        """Retorna uma janela disponível (com menos abas que o máximo)."""
        with self.lock:
            for window_id in self.window_ids:
                if len(self.window_tab_queues[window_id]) < self.max_tabs_per_window:
                    return window_id
            return None
    
    def create_tab_for_url(self, url_index: int, url: str, 
                          window_id: str, window_name: str) -> Optional[TabInfo]:
        """Cria uma aba para uma URL específica com controle FIFO."""
        try:
            with self.lock:
                # Verificar se janela ainda tem espaço
                if len(self.window_tab_queues[window_id]) >= self.max_tabs_per_window:
                    print(f"⚠️ Janela {window_name} está cheia ({self.max_tabs_per_window} abas)")
                    return None
            
            # Usar implementação base
            tab_info = super().create_tab_for_url(url_index, url, window_id, window_name)
            
            if tab_info:
                # Adicionar à fila FIFO da janela
                with self.lock:
                    self.window_tab_queues[window_id].append(url_index)
            
            return tab_info
                
        except Exception as e:
            print(f"❌ [{threading.current_thread().name}] Erro ao criar aba para URL {url_index+1}: {e}")
            return None
    
    def close_tab_and_create_new(self, url_index: int, new_url: str, 
                               new_url_index: int) -> Optional[TabInfo]:
        """Fecha uma aba e cria uma nova com controle FIFO."""
        try:
            with self.lock:
                if url_index in self.active_tabs:
                    tab_info = self.active_tabs[url_index]
                    window_id = tab_info.window_id
                    window_name = tab_info.window_name
                    
                    # Fechar aba atual
                    if tab_info.tab_id in self.driver.window_handles:
                        self.driver.switch_to.window(tab_info.tab_id)
                        self.driver.close()
                        print(f"🔒 [{threading.current_thread().name}] Aba {url_index+1} fechada")
                    
                    # Remover da fila FIFO da janela
                    if url_index in self.window_tab_queues[window_id]:
                        self.window_tab_queues[window_id].remove(url_index)
                    
                    # Remover das abas ativas
                    del self.active_tabs[url_index]
                    
                    # Criar nova aba na mesma janela se URL fornecida
                    if new_url and new_url_index >= 0:
                        new_tab_info = self.create_tab_for_url(new_url_index, new_url, window_id, window_name)
                        return new_tab_info
            
            return None
            
        except Exception as e:
            print(f"❌ [{threading.current_thread().name}] Erro ao fechar/criar aba: {e}")
            return None
    
    def get_window_tab_counts(self) -> Dict[str, int]:
        """Retorna contagem de abas por janela."""
        with self.lock:
            return {window_id: len(tabs) for window_id, tabs in self.window_tab_queues.items()}
    
    def _ensure_window_focus(self, window_id: str, window_name: str):
        """Garante que a janela está focada antes de processar."""
        try:
            # Focar na janela específica
            self.driver.switch_to.window(window_id)
            print(f"🎯 [{threading.current_thread().name}] Focando em {window_name} (ID: {window_id})")
            
            # Pequeno delay para garantir que o foco foi aplicado
            time.sleep(0.1)
            
        except Exception as e:
            print(f"⚠️ [{threading.current_thread().name}] Erro ao focar janela {window_name}: {e}")
            # Tentar recuperar foco na janela principal
            try:
                self.driver.switch_to.window(self.window_ids[0])
            except:
                pass
    
    def _is_window_active(self, window_id: str) -> bool:
        """Verifica se a janela está ativa e responsiva."""
        try:
            # Tentar focar na janela
            self.driver.switch_to.window(window_id)
            
            # Verificar se conseguimos obter o título da página
            title = self.driver.title
            return title is not None
            
        except Exception as e:
            print(f"⚠️ [{threading.current_thread().name}] Janela {window_id} não está ativa: {e}")
            return False
    
    def process_url_with_inventory(self, url_index: int, url: str, max_workers: int) -> Dict[str, Any]:
        """Processa uma URL fazendo inventário dos anexos com controle FIFO e gestão de foco."""
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
            # Determinar qual janela usar (priorizar janelas com espaço disponível)
            available_window_id = self.get_available_window()
            if available_window_id is not None:
                window_id = available_window_id
                window_index = self.window_ids.index(window_id)
                window_name = f"Janela {window_index + 1}"
            else:
                # Fallback para distribuição round-robin
                window_index = url_index % len(self.window_ids)
                window_id = self.window_ids[window_index]
                window_name = f"Janela {window_index + 1}"
            
            # Garantir que a janela está focada antes de criar aba
            self._ensure_window_focus(window_id, window_name)
            
            # Verificar se a janela ainda está ativa
            if not self._is_window_active(window_id):
                result['error'] = f"Janela {window_name} não está ativa"
                print(f"❌ [{thread_name}] Janela {window_name} não está ativa - pulando URL")
                return result
            
            # Criar aba para a URL
            tab_info = self.create_tab_for_url(url_index, url, window_id, window_name)
            
            if tab_info:
                # Extrair número PO da URL
                po_number = url.split('/')[-1]
                
                # Aguardar carregamento
                time.sleep(0.3)
                
                # Verificar se a página carregou corretamente (detecção de erro)
                if self._is_error_page(tab_info.tab_id):
                    result['error'] = "PO não encontrado ou página de erro detectada"
                    result['success'] = False
                    print(f"❌ [{thread_name}] PO {po_number} não acessível - página de erro")
                    
                    # Fechar aba após erro
                    time.sleep(0.2)
                    self.close_tab_and_create_new(url_index, "", -1)
                    return result
                
                # Fazer inventário dos anexos
                attachments_count = self.inventory_attachments_for_tab(tab_info.tab_id, po_number)
                
                result['attachments_found'] = attachments_count
                result['success'] = True
                
                # Fechar aba após inventário
                time.sleep(0.1)
                self.close_tab_and_create_new(url_index, "", -1)  # Apenas fechar
                
            else:
                result['error'] = "Falha ao criar aba"
                
        except Exception as e:
            result['error'] = str(e)
            print(f"❌ [{thread_name}] Erro ao processar URL {url_index+1}: {e}")
        
        return result


class ParallelTabManager(BaseTabManager):
    """
    Gerenciador paralelo de abas - implementa processamento paralelo
    Strategy Pattern: estratégia específica para processamento paralelo
    """
    
    def __init__(self, driver: webdriver.Edge, window_ids: List[str]):
        super().__init__(driver, window_ids)
        self.completed_urls = []
        self.failed_urls = []
    
    def process_url_with_inventory(self, url_index: int, url: str, max_workers: int) -> Dict[str, Any]:
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
            # Determinar qual janela usar (distribuir entre janelas)
            window_index = url_index % len(self.window_ids)
            window_id = self.window_ids[window_index]
            window_name = f"Janela {window_index + 1}"
            
            # Criar aba para a URL
            tab_info = self.create_tab_for_url(url_index, url, window_id, window_name)
            
            if tab_info:
                # Extrair número PO da URL
                po_number = url.split('/')[-1]
                
                # Aguardar carregamento
                time.sleep(0.5)
                
                # Verificar se a página carregou corretamente (detecção de erro)
                if self._is_error_page(tab_info.tab_id):
                    result['error'] = "PO não encontrado ou página de erro detectada"
                    result['success'] = False
                    print(f"❌ [{thread_name}] PO {po_number} não acessível - página de erro")
                    
                    # Fechar aba após erro
                    time.sleep(0.2)
                    self.close_tab_and_create_new(url_index, "", -1)
                    return result
                
                # Fazer inventário dos anexos
                attachments_count = self.inventory_attachments_for_tab(tab_info.tab_id, po_number)
                
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
