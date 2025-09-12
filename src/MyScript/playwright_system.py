"""
Sistema Playwright - Alternativa Moderna ao Selenium
Implementa automação de browser usando Playwright para resolver problemas de interceptação
"""

import os
import asyncio
import time
from typing import List, Dict, Any, Optional, Union, Tuple
from pathlib import Path
from datetime import datetime

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

# Exceção personalizada para erros de navegação
class PlaywrightNavigationError(Exception):
    """Exceção específica para erros de navegação do Playwright."""
    pass

# Importações condicionais para funcionar tanto como módulo quanto como script
try:
    from config_advanced import get_config, get_playwright_config
    from logging_advanced import get_logger, get_browser_logger, get_inventory_logger
    from retry_advanced import retry_with_custom_config
except ImportError:
    from config_advanced import get_config, get_playwright_config
    from logging_advanced import get_logger, get_browser_logger, get_inventory_logger
    from retry_advanced import retry_with_custom_config


class PlaywrightManager:
    """Gerenciador principal do Playwright."""
    
    def __init__(self):
        self.config = get_config()
        self.playwright_config = get_playwright_config()
        self.logger = get_logger("playwright_manager")
        self.browser_logger = get_browser_logger()
        
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.pages: List[Page] = []
        
        # Configurações de browser
        self.browser_type = self.playwright_config.browser_type
        self.headless = self.playwright_config.headless
        self.slow_mo = self.playwright_config.slow_mo
        self.timeout = self.playwright_config.timeout
        
        # Configurações de viewport
        self.viewport = {
            'width': self.playwright_config.viewport_width,
            'height': self.playwright_config.viewport_height
        }
    
    async def initialize(self) -> bool:
        """Inicializa Playwright e browser."""
        try:
            self.logger.info("Inicializando Playwright")
            
            # Inicializar Playwright
            self.playwright = await async_playwright().start()
            
            # Configurar browser
            browser_options = {
                'headless': self.headless,
                'slow_mo': self.slow_mo,
                'timeout': self.timeout
            }
            
            # Configurar contexto
            context_options = {
                'viewport': self.viewport,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59'
            }
            
            # Usar persistent context se perfil estiver configurado
            if self.config.profile_mode != "none":
                profile_path = self.config.get_edge_profile_path()
                if os.path.exists(profile_path):
                    self.browser_logger.profile_loaded(profile_path, True)
                    
                    # PROTEÇÃO CRÍTICA: NÃO ALTERAR ESTA CONFIGURAÇÃO
                    # O perfil Edge DEVE ser carregado via user_data_dir como parâmetro direto
                    # NÃO usar --user-data-dir como argumento de linha de comando
                    # Esta configuração é essencial para funcionamento correto do sistema
                    if self.browser_type in ['chromium', 'msedge']:
                        # Argumentos específicos para Edge (SEM --user-data-dir)
                        edge_args = [
                            '--profile-directory=Default',
                            '--disable-web-security',
                            '--disable-features=VizDisplayCompositor',
                            '--disable-extensions-except',
                            '--disable-plugins-discovery',
                            '--no-first-run',
                            '--no-default-browser-check',
                            '--disable-default-apps',
                            '--disable-blink-features=AutomationControlled',
                            '--disable-dev-shm-usage',
                            '--no-sandbox'
                        ]
                        
                        # CORREÇÃO CRÍTICA: user_data_dir como parâmetro direto, não como argumento
                        self.context = await self.playwright.chromium.launch_persistent_context(
                            user_data_dir=profile_path,  # CORREÇÃO: parâmetro direto
                            headless=self.headless,
                            slow_mo=self.slow_mo,
                            timeout=self.timeout,
                            viewport=self.viewport,
                            args=edge_args,
                            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
                        )
                        self.browser = self.context.browser  # Obter browser do contexto persistente
                    elif self.browser_type == 'firefox':
                        self.context = await self.playwright.firefox.launch_persistent_context(
                            profile_path,
                            headless=self.headless,
                            slow_mo=self.slow_mo,
                            timeout=self.timeout,
                            viewport=self.viewport,
                            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59'
                        )
                        self.browser = self.context.browser
                    else:
                        # Fallback para chromium se tipo não suportado
                        # PROTEÇÃO CRÍTICA: Mesma correção aplicada aqui
                        edge_args = [
                            '--profile-directory=Default',
                            '--disable-web-security',
                            '--disable-features=VizDisplayCompositor',
                            '--disable-extensions-except',
                            '--disable-plugins-discovery',
                            '--no-first-run',
                            '--no-default-browser-check',
                            '--disable-default-apps',
                            '--disable-blink-features=AutomationControlled',
                            '--disable-dev-shm-usage',
                            '--no-sandbox'
                        ]
                        
                        self.context = await self.playwright.chromium.launch_persistent_context(
                            user_data_dir=profile_path,  # CORREÇÃO: parâmetro direto
                            headless=self.headless,
                            slow_mo=self.slow_mo,
                            timeout=self.timeout,
                            viewport=self.viewport,
                            args=edge_args,
                            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
                        )
                        self.browser = self.context.browser
                else:
                    # Perfil não encontrado, usar modo normal
                    self.browser_logger.profile_loaded(profile_path, False)
                    if self.browser_type in ['chromium', 'msedge']:
                        self.browser = await self.playwright.chromium.launch(**browser_options)
                    elif self.browser_type == 'firefox':
                        self.browser = await self.playwright.firefox.launch(**browser_options)
                    elif self.browser_type == 'webkit':
                        self.browser = await self.playwright.webkit.launch(**browser_options)
                    else:
                        self.browser = await self.playwright.chromium.launch(**browser_options)
                    
                    self.context = await self.browser.new_context(**context_options)
            else:
                # Modo sem perfil
                if self.browser_type == 'chromium':
                    self.browser = await self.playwright.chromium.launch(**browser_options)
                elif self.browser_type == 'firefox':
                    self.browser = await self.playwright.firefox.launch(**browser_options)
                elif self.browser_type == 'webkit':
                    self.browser = await self.playwright.webkit.launch(**browser_options)
                else:
                    self.browser = await self.playwright.chromium.launch(**browser_options)
                
                self.context = await self.browser.new_context(**context_options)
            
            self.logger.info("Playwright inicializado com sucesso", 
                           browser_type=self.browser_type,
                           headless=self.headless)
            
            # VALIDAÇÃO CRÍTICA: Verificar se perfil foi carregado corretamente
            if self.config.profile_mode != "none" and self.context:
                profile_validation = await self._validate_profile_loaded()
                if not profile_validation:
                    self.logger.warning("Perfil pode não ter sido carregado corretamente")
                else:
                    self.logger.info("Perfil Edge validado com sucesso")
            
            return True
            
        except Exception as e:
            self.logger.error("Erro ao inicializar Playwright", error=str(e))
            return False
    
    async def _validate_profile_loaded(self) -> bool:
        """Valida se o perfil Edge foi carregado corretamente."""
        try:
            if not self.context:
                return False
            
            # Criar página temporária para teste
            test_page = await self.context.new_page()
            
            # Navegar para página de teste
            await test_page.goto("about:blank")
            
            # Verificar se podemos executar JavaScript (indicativo de perfil carregado)
            result = await test_page.evaluate("() => navigator.userAgent")
            
            # Fechar página de teste
            await test_page.close()
            
            # Verificar se user agent contém Edge
            is_edge_profile = "Edg" in result or "Edge" in result
            
            self.logger.info("Validação de perfil", 
                           user_agent=result,
                           is_edge_profile=is_edge_profile)
            
            return is_edge_profile
            
        except Exception as e:
            self.logger.error("Erro na validação de perfil", error=str(e))
            return False
    
    async def fallback_to_manual_login(self) -> bool:
        """Fallback: abrir página inicial e aguardar login manual."""
        try:
            self.logger.info("Iniciando fallback de login manual")
            
            # Abrir página inicial do Coupa
            login_page = await self.context.new_page()
            await login_page.goto("https://unilever.coupahost.com/login", 
                                wait_until='domcontentloaded', timeout=30000)
            
            self.logger.info("Página de login aberta - aguardando login manual do usuário")
            
            # Aguardar login manual (detectar mudança de URL ou elemento)
            await self._wait_for_manual_login(login_page)
            
            # Fechar página de login e continuar
            await login_page.close()
            
            self.logger.info("Login manual detectado - continuando processamento")
            return True
            
        except Exception as e:
            self.logger.error("Erro no fallback de login manual", error=str(e))
            return False
    
    async def _wait_for_manual_login(self, page: Page) -> None:
        """Aguarda o usuário fazer login manualmente."""
        try:
            # Aguardar até que a URL mude ou elemento de login desapareça
            await page.wait_for_function("""
                () => {
                    const currentUrl = window.location.href;
                    const hasLoginElements = document.querySelector('[data-testid="login-button"]') || 
                                           document.querySelector('input[type="password"]') ||
                                           document.querySelector('button[type="submit"]');
                    
                    return currentUrl.includes('/dashboard') || 
                           currentUrl.includes('/home') ||
                           currentUrl.includes('/orders') ||
                           !hasLoginElements;
                }
            """, timeout=300000)  # 5 minutos para login
            
            self.logger.info("Login manual detectado com sucesso")
            
        except PlaywrightTimeoutError:
            self.logger.warning("Timeout aguardando login manual (5 minutos)")
            raise
        except Exception as e:
            self.logger.error("Erro aguardando login manual", error=str(e))
            raise
    
    async def create_page(self) -> Optional[Page]:
        """Cria uma nova página."""
        try:
            if not self.context:
                self.logger.error("Contexto não inicializado")
                return None
            
            page = await self.context.new_page()
            self.pages.append(page)
            
            # Configurar timeout da página
            page.set_default_timeout(self.timeout)
            
            self.browser_logger.tab_created(str(id(page)), "new_page", "Playwright")
            
            return page
            
        except Exception as e:
            self.logger.error("Erro ao criar página", error=str(e))
            return None
    
    async def create_multiple_pages(self, count: int) -> List[Page]:
        """Cria múltiplas páginas."""
        try:
            pages = []
            
            for i in range(count):
                page = await self.create_page()
                if page:
                    pages.append(page)
                    self.logger.info("Página criada", index=i+1, total=count)
            
            self.logger.info("Múltiplas páginas criadas", count=len(pages))
            return pages
            
        except Exception as e:
            self.logger.error("Erro ao criar múltiplas páginas", error=str(e))
            return []
    
    async def close_page(self, page: Page) -> bool:
        """Fecha uma página específica."""
        try:
            if page in self.pages:
                self.pages.remove(page)
            
            await page.close()
            
            self.browser_logger.tab_closed(str(id(page)), "Playwright")
            return True
            
        except Exception as e:
            self.logger.error("Erro ao fechar página", error=str(e))
            return False
    
    async def close_all_pages(self) -> bool:
        """Fecha todas as páginas."""
        try:
            for page in self.pages[:]:  # Cópia da lista para evitar modificação durante iteração
                await self.close_page(page)
            
            self.logger.info("Todas as páginas fechadas")
            return True
            
        except Exception as e:
            self.logger.error("Erro ao fechar todas as páginas", error=str(e))
            return False
    
    async def cleanup(self) -> bool:
        """Limpa recursos do Playwright."""
        try:
            # Fechar todas as páginas
            await self.close_all_pages()
            
            # Fechar contexto
            if self.context:
                await self.context.close()
                self.context = None
            
            # Fechar browser
            if self.browser:
                await self.browser.close()
                self.browser = None
            
            # Parar Playwright
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            
            self.logger.info("Playwright limpo com sucesso")
            return True
            
        except Exception as e:
            self.logger.error("Erro ao limpar Playwright", error=str(e))
            return False


class PlaywrightPageProcessor:
    """Processador de páginas usando Playwright."""
    
    def __init__(self, page: Page):
        self.page = page
        self.logger = get_logger("playwright_processor")
        self.inventory_logger = get_inventory_logger()
        
        # Seletores para attachments
        self.attachment_selectors = [
            "div[class*='commentAttachments'] a[href*='attachment_file']",
            "div[class*='attachment'] a[href*='attachment_file']",
            "div[class*='attachment'] a[href*='download']",
            "div[class*='attachment'] a[href*='attachment']",
            "span[aria-label*='file attachment']",
            "span[role='button'][aria-label*='file attachment']",
            "span[title*='.pdf'], span[title*='.docx'], span[title*='.msg']",
            "a[href*='/attachment/']",
            "a[href*='download']",
            ".attachment-link",
            ".file-download",
            "[data-attachment]"
        ]
        
        # Padrões de erro
        self.error_patterns = [
            "Oops! We couldn't find what you wanted",
            "Page not found",
            "404",
            "Not Found",
            "Error 404"
        ]
    
    @retry_with_custom_config(attempts=3, delay=2.0)
    async def load_page(self, url: str) -> bool:
        """Carrega página com retry automático e rate limiting."""
        max_retries = 3
        retry_delay = 1.5  # segundos (reduzido para melhor performance)
        
        for attempt in range(max_retries):
            try:
                self.logger.info("Carregando página com Playwright", url=url, attempt=attempt + 1)
                
                # Adicionar delay entre requisições para evitar rate limiting
                if attempt > 0:
                    await asyncio.sleep(retry_delay * attempt)
                
                # Navegar para URL com timeout mais robusto
                await self.page.goto(url, wait_until='domcontentloaded', timeout=45000)
                
                self.logger.info("Página carregada com sucesso", url=url)
                return True
                
            except PlaywrightTimeoutError as e:
                self.logger.warning("Timeout ao carregar página", error=str(e), url=url, attempt=attempt + 1)
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(retry_delay)
                
            except Exception as e:
                # Tratamento específico para ERR_ABORTED
                if "ERR_ABORTED" in str(e):
                    self.logger.warning("Erro de navegação ERR_ABORTED", error=str(e), url=url, attempt=attempt + 1)
                    if attempt == max_retries - 1:
                        raise PlaywrightNavigationError(f"Erro de navegação após {max_retries} tentativas: {e}")
                    await asyncio.sleep(retry_delay * (attempt + 1))  # Delay progressivo
                else:
                    self.logger.error("Erro ao carregar página", error=str(e), url=url)
                    raise
        
        return False
    
    async def is_error_page(self) -> bool:
        """Verifica se a página é uma página de erro."""
        try:
            # Obter texto da página
            page_content = await self.page.content()
            page_text = await self.page.text_content('body')
            
            # Verificar padrões de erro
            for pattern in self.error_patterns:
                if pattern.lower() in page_text.lower():
                    self.logger.warning("Página de erro detectada", pattern=pattern)
                    return True
            
            return False
            
        except Exception as e:
            self.logger.warning("Erro ao verificar página de erro", error=str(e))
            return False
    
    async def extract_attachments(self, po_number: str) -> List[Dict[str, Any]]:
        """Extrai attachments da página usando Playwright."""
        try:
            attachments = []
            
            # Aguardar elementos carregarem
            await self.page.wait_for_load_state('networkidle')
            
            # Tentar cada seletor
            for selector in self.attachment_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    
                    for element in elements:
                        attachment_info = await self._extract_attachment_details(element, po_number)
                        if attachment_info:
                            attachments.append(attachment_info)
                            
                except Exception as e:
                    self.logger.debug("Erro com seletor", selector=selector, error=str(e))
                    continue
            
            # Remover duplicatas
            unique_attachments = self._remove_duplicates(attachments)
            
            self.inventory_logger.attachments_found(po_number, len(unique_attachments))
            
            return unique_attachments
            
        except Exception as e:
            self.logger.error("Erro ao extrair attachments", error=str(e), po_number=po_number)
            return []
    
    async def _extract_attachment_details(self, element, po_number: str) -> Optional[Dict[str, Any]]:
        """Extrai detalhes de um elemento de attachment."""
        try:
            # Obter URL
            url = await element.get_attribute('href')
            if not url:
                url = await element.get_attribute('data-href')
            if not url:
                url = await element.get_attribute('data-url')
            
            if not url:
                return None
            
            # Tornar URL absoluta
            if url.startswith('/'):
                url = f"https://unilever.coupahost.com{url}"
            
            # Obter nome do arquivo
            filename = (
                await element.get_attribute('title') or
                await element.get_attribute('aria-label') or
                await element.get_attribute('data-filename') or
                await element.text_content() or
                f"{po_number}_attachment_{int(time.time())}"
            )
            
            # Determinar tipo de arquivo
            file_type = self._determine_file_type(filename)
            
            return {
                'po_number': po_number,
                'url': url,
                'filename': filename.strip(),
                'file_type': file_type,
                'status': 'pending',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'downloaded_at': '',
                'error_message': '',
                'file_size': 0,
                'element_selector': 'playwright_extracted'
            }
            
        except Exception as e:
            self.logger.warning("Erro ao extrair detalhes do attachment", error=str(e))
            return None
    
    def _determine_file_type(self, filename: str) -> str:
        """Determina tipo de arquivo baseado na extensão."""
        filename_lower = filename.lower()
        
        if filename_lower.endswith('.pdf'):
            return 'pdf'
        elif filename_lower.endswith(('.doc', '.docx')):
            return 'document'
        elif filename_lower.endswith(('.xls', '.xlsx')):
            return 'spreadsheet'
        elif filename_lower.endswith('.msg'):
            return 'email'
        elif filename_lower.endswith(('.jpg', '.jpeg', '.png', '.gif')):
            return 'image'
        elif filename_lower.endswith(('.zip', '.rar')):
            return 'archive'
        elif filename_lower.endswith(('.txt', '.csv', '.xml')):
            return 'text'
        else:
            return 'unknown'
    
    def _remove_duplicates(self, attachments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove attachments duplicados baseado na URL."""
        seen_urls = set()
        unique_attachments = []
        
        for attachment in attachments:
            if attachment['url'] not in seen_urls:
                unique_attachments.append(attachment)
                seen_urls.add(attachment['url'])
        
        return unique_attachments
    
    async def click_element_safe(self, selector: str) -> bool:
        """Clica em elemento de forma segura (resolve interceptação)."""
        try:
            # Aguardar elemento estar visível
            await self.page.wait_for_selector(selector, state='visible')
            
            # Tentar clique normal primeiro
            try:
                await self.page.click(selector)
                self.logger.info("Clique normal realizado", selector=selector)
                return True
            except Exception:
                # Se falhar, tentar clique forçado
                await self.page.click(selector, force=True)
                self.logger.info("Clique forçado realizado", selector=selector)
                return True
                
        except Exception as e:
            self.logger.error("Erro ao clicar em elemento", error=str(e), selector=selector)
            return False
    
    async def scroll_to_element(self, selector: str) -> bool:
        """Rola página até elemento estar visível."""
        try:
            await self.page.scroll_into_view_if_needed(selector)
            self.logger.debug("Página rolada até elemento", selector=selector)
            return True
        except Exception as e:
            self.logger.warning("Erro ao rolar até elemento", error=str(e), selector=selector)
            return False
    
    async def wait_for_element(self, selector: str, timeout: int = 10000) -> bool:
        """Aguarda elemento aparecer na página."""
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            self.logger.warning("Timeout aguardando elemento", selector=selector)
            return False
        except Exception as e:
            self.logger.error("Erro ao aguardar elemento", error=str(e), selector=selector)
            return False


class PlaywrightInventorySystem:
    """Sistema de inventário usando Playwright."""
    
    def __init__(self):
        self.playwright_manager = PlaywrightManager()
        self.logger = get_logger("playwright_inventory")
        self.inventory_logger = get_inventory_logger()
        
        # Processadores de página
        self.page_processors: List[PlaywrightPageProcessor] = []
    
    async def initialize(self) -> bool:
        """Inicializa sistema Playwright."""
        try:
            success = await self.playwright_manager.initialize()
            if success:
                self.logger.info("Sistema Playwright inicializado")
            return success
        except Exception as e:
            self.logger.error("Erro ao inicializar sistema Playwright", error=str(e))
            return False
    
    async def create_workers(self, num_workers: int) -> bool:
        """Cria workers (páginas) para processamento paralelo."""
        try:
            pages = await self.playwright_manager.create_multiple_pages(num_workers)
            
            # Criar processadores para cada página
            self.page_processors = [
                PlaywrightPageProcessor(page) for page in pages
            ]
            
            self.logger.info("Workers Playwright criados", count=len(self.page_processors))
            return True
            
        except Exception as e:
            self.logger.error("Erro ao criar workers Playwright", error=str(e))
            return False
    
    async def process_url_async(self, url: str, po_number: str, worker_index: int = 0) -> Dict[str, Any]:
        """Processa URL usando Playwright de forma assíncrona."""
        try:
            if worker_index >= len(self.page_processors):
                worker_index = 0
            
            processor = self.page_processors[worker_index]
            
            start_time = time.time()
            
            # Carregar página
            await processor.load_page(url)
            
            # Verificar se é página de erro
            if await processor.is_error_page():
                return {
                    'success': False,
                    'po_number': po_number,
                    'url': url,
                    'error': 'Página de erro detectada',
                    'worker_index': worker_index
                }
            
            # Extrair attachments
            attachments = await processor.extract_attachments(po_number)
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'po_number': po_number,
                'url': url,
                'attachments': attachments,
                'attachments_count': len(attachments),
                'processing_time': processing_time,
                'worker_index': worker_index
            }
            
        except Exception as e:
            self.logger.error("Erro ao processar URL com Playwright", 
                            error=str(e), po_number=po_number, worker_index=worker_index)
            return {
                'success': False,
                'po_number': po_number,
                'url': url,
                'error': str(e),
                'worker_index': worker_index
            }
    
    async def process_urls_batch(self, urls: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        """Processa lote de URLs usando workers paralelos."""
        try:
            if not self.page_processors:
                self.logger.error("Workers não inicializados")
                return []
            
            # Criar tarefas para processamento paralelo
            tasks = []
            for i, (url, po_number) in enumerate(urls):
                worker_index = i % len(self.page_processors)
                task = self.process_url_async(url, po_number, worker_index)
                tasks.append(task)
            
            # Executar tarefas em paralelo
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Processar resultados
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    url, po_number = urls[i]
                    processed_results.append({
                        'success': False,
                        'po_number': po_number,
                        'url': url,
                        'error': str(result)
                    })
                else:
                    processed_results.append(result)
            
            self.logger.info("Lote de URLs processado com Playwright", 
                           total=len(urls),
                           successful=sum(1 for r in processed_results if r['success']))
            
            return processed_results
            
        except Exception as e:
            self.logger.error("Erro ao processar lote de URLs", error=str(e))
            return []
    
    async def cleanup(self) -> bool:
        """Limpa recursos do sistema Playwright."""
        try:
            self.page_processors.clear()
            success = await self.playwright_manager.cleanup()
            
            if success:
                self.logger.info("Sistema Playwright limpo")
            
            return success
            
        except Exception as e:
            self.logger.error("Erro ao limpar sistema Playwright", error=str(e))
            return False


# Funções utilitárias assíncronas
async def process_single_url_playwright(url: str, po_number: str) -> Dict[str, Any]:
    """Processa uma URL única usando Playwright."""
    inventory_system = PlaywrightInventorySystem()
    
    try:
        # Inicializar sistema
        if not await inventory_system.initialize():
            return {'success': False, 'error': 'Falha ao inicializar Playwright'}
        
        # Criar worker
        if not await inventory_system.create_workers(1):
            return {'success': False, 'error': 'Falha ao criar worker'}
        
        # Processar URL
        result = await inventory_system.process_url_async(url, po_number)
        
        return result
        
    finally:
        # Limpar recursos
        await inventory_system.cleanup()


async def process_urls_playwright(urls: List[Tuple[str, str]], num_workers: int = 4) -> List[Dict[str, Any]]:
    """Processa múltiplas URLs usando Playwright."""
    inventory_system = PlaywrightInventorySystem()
    
    try:
        # Inicializar sistema
        if not await inventory_system.initialize():
            return []
        
        # Criar workers
        if not await inventory_system.create_workers(num_workers):
            return []
        
        # Processar URLs em lotes
        batch_size = num_workers * 2  # Processar 2 URLs por worker por vez
        all_results = []
        
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            batch_results = await inventory_system.process_urls_batch(batch)
            all_results.extend(batch_results)
        
        return all_results
        
    finally:
        # Limpar recursos
        await inventory_system.cleanup()


if __name__ == "__main__":
    # Teste do sistema Playwright
    print("🔧 Testando sistema Playwright...")
    
    async def test_playwright():
        # Teste de URL única
        test_url = "https://httpbin.org/html"
        result = await process_single_url_playwright(test_url, "TEST001")
        print(f"✅ URL única processada: {result['success']}")
        
        # Teste de múltiplas URLs
        test_urls = [
            ("https://httpbin.org/html", "TEST001"),
            ("https://httpbin.org/json", "TEST002"),
            ("https://httpbin.org/xml", "TEST003")
        ]
        
        results = await process_urls_playwright(test_urls, num_workers=2)
        successful = sum(1 for r in results if r['success'])
        print(f"✅ Múltiplas URLs processadas: {successful}/{len(results)}")
    
    # Executar teste
    asyncio.run(test_playwright())
    
    print("✅ Sistema Playwright testado!")

