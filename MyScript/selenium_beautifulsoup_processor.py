"""
Sistema Híbrido Selenium + BeautifulSoup
Combina navegação dinâmica do Selenium com parsing rápido do BeautifulSoup
"""

import os
import re
import time
from typing import List, Dict, Any, Optional, Union, Tuple
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# Importação condicional
try:
    from config_advanced import get_config
except ImportError:
    pass

try:
    from logging_advanced import get_logger, get_inventory_logger
except ImportError:
    pass

try:
    from retry_advanced import retry_browser_action, retry_page_load, retry_element_find
except ImportError:
    pass


class HybridPageAnalyzer:
    """Analisador híbrido que combina Selenium e BeautifulSoup."""
    
    def __init__(self, driver: webdriver.Edge):
        self.driver = driver
        self.config = get_config()
        self.logger = get_logger("hybrid_analyzer")
        self.inventory_logger = get_inventory_logger()
        
        # Configurações de parsing
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
        
        self.error_patterns = {
            'coupa_not_found': [
                r'Oops! We couldn\'t find what you wanted',
                r'Page not found',
                r'404.*error',
                r'Not Found'
            ],
            'authentication': [
                r'Please log in',
                r'Authentication required',
                r'Session expired',
                r'Login required'
            ],
            'server_error': [
                r'500.*error',
                r'Internal server error',
                r'Service unavailable',
                r'Server error'
            ],
            'access_denied': [
                r'Access denied',
                r'Permission required',
                r'Unauthorized',
                r'Forbidden'
            ]
        }
    
    @retry_page_load(max_attempts=3, delay=2.0)
    def load_page_with_selenium(self, url: str) -> bool:
        """Carrega página usando Selenium."""
        try:
            self.logger.info("Carregando página com Selenium", url=url)
            
            self.driver.get(url)
            
            # Aguardar carregamento completo
            wait = WebDriverWait(self.driver, self.config.timeout)
            wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
            
            # Aguardar elementos dinâmicos carregarem
            time.sleep(1)
            
            self.logger.info("Página carregada com Selenium", url=url)
            return True
            
        except Exception as e:
            self.logger.error("Erro ao carregar página com Selenium", error=str(e), url=url)
            raise
    
    def get_page_html(self) -> str:
        """Obtém HTML completo da página atual."""
        try:
            html = self.driver.page_source
            self.logger.debug("HTML obtido", length=len(html))
            return html
        except Exception as e:
            self.logger.error("Erro ao obter HTML", error=str(e))
            raise
    
    def analyze_page_structure(self, html: str) -> Dict[str, Any]:
        """Analisa estrutura da página usando BeautifulSoup."""
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            analysis = {
                'page_type': self._detect_page_type(soup),
                'has_attachments': self._detect_attachments(soup),
                'error_analysis': self._analyze_errors(soup),
                'navigation_elements': self._extract_navigation(soup),
                'forms': self._extract_forms(soup),
                'scripts': self._extract_scripts(soup),
                'performance_hints': self._analyze_performance_hints(soup)
            }
            
            self.logger.info("Análise de página concluída", 
                           page_type=analysis['page_type'],
                           has_attachments=analysis['has_attachments'])
            
            return analysis
            
        except Exception as e:
            self.logger.error("Erro na análise de página", error=str(e))
            return {'error': str(e)}
    
    def _detect_page_type(self, soup: BeautifulSoup) -> str:
        """Detecta o tipo de página do Coupa."""
        try:
            # Detectar página de PO
            if soup.select('.po-header, .purchase-order-header, [class*="po-header"]'):
                return 'po_detail'
            
            # Detectar página de lista
            if soup.select('.po-list, .search-results, [class*="po-list"]'):
                return 'po_list'
            
            # Detectar página de login
            if soup.select('input[type="password"], .login-form, [class*="login"]'):
                return 'login'
            
            # Detectar página de erro
            if soup.select('.error-page, .not-found, [class*="error"]'):
                return 'error'
            
            # Detectar página de attachment
            if soup.select('.attachment, [class*="attachment"]'):
                return 'attachment'
            
            return 'unknown'
            
        except Exception as e:
            self.logger.warning("Erro ao detectar tipo de página", error=str(e))
            return 'unknown'
    
    def _detect_attachments(self, soup: BeautifulSoup) -> bool:
        """Detecta se a página tem attachments."""
        try:
            for selector in self.attachment_selectors:
                elements = soup.select(selector)
                if elements:
                    self.logger.debug("Attachments detectados", selector=selector, count=len(elements))
                    return True
            
            return False
            
        except Exception as e:
            self.logger.warning("Erro ao detectar attachments", error=str(e))
            return False
    
    def _analyze_errors(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analisa erros na página."""
        try:
            page_text = soup.get_text().lower()
            detected_errors = []
            
            for error_type, patterns in self.error_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, page_text, re.IGNORECASE):
                        detected_errors.append({
                            'type': error_type,
                            'pattern': pattern,
                            'severity': self._get_error_severity(error_type)
                        })
            
            return {
                'is_error': len(detected_errors) > 0,
                'errors': detected_errors,
                'page_title': soup.title.string if soup.title else 'No title',
                'main_content': soup.find('main') or soup.find('body')
            }
            
        except Exception as e:
            self.logger.warning("Erro na análise de erros", error=str(e))
            return {'is_error': False, 'errors': []}
    
    def _get_error_severity(self, error_type: str) -> str:
        """Retorna severidade do erro."""
        severity_map = {
            'coupa_not_found': 'high',
            'authentication': 'medium',
            'server_error': 'high',
            'access_denied': 'medium'
        }
        return severity_map.get(error_type, 'low')
    
    def _extract_navigation(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extrai elementos de navegação."""
        try:
            nav_elements = []
            
            # Buscar elementos de navegação comuns
            nav_selectors = [
                'nav a', '.navigation a', '.menu a', 
                '.breadcrumb a', '.pagination a'
            ]
            
            for selector in nav_selectors:
                elements = soup.select(selector)
                for element in elements:
                    nav_elements.append({
                        'text': element.get_text().strip(),
                        'href': element.get('href', ''),
                        'class': element.get('class', [])
                    })
            
            return nav_elements
            
        except Exception as e:
            self.logger.warning("Erro ao extrair navegação", error=str(e))
            return []
    
    def _extract_forms(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extrai formulários da página."""
        try:
            forms = []
            
            for form in soup.find_all('form'):
                form_data = {
                    'action': form.get('action', ''),
                    'method': form.get('method', 'get'),
                    'inputs': []
                }
                
                for input_elem in form.find_all(['input', 'select', 'textarea']):
                    form_data['inputs'].append({
                        'type': input_elem.get('type', 'text'),
                        'name': input_elem.get('name', ''),
                        'id': input_elem.get('id', ''),
                        'required': input_elem.has_attr('required')
                    })
                
                forms.append(form_data)
            
            return forms
            
        except Exception as e:
            self.logger.warning("Erro ao extrair formulários", error=str(e))
            return []
    
    def _extract_scripts(self, soup: BeautifulSoup) -> List[str]:
        """Extrai scripts da página."""
        try:
            scripts = []
            
            for script in soup.find_all('script'):
                src = script.get('src')
                if src:
                    scripts.append(src)
                elif script.string:
                    # Script inline (apenas primeiros 100 caracteres)
                    scripts.append(f"inline: {script.string[:100]}...")
            
            return scripts
            
        except Exception as e:
            self.logger.warning("Erro ao extrair scripts", error=str(e))
            return []
    
    def _analyze_performance_hints(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analisa dicas de performance da página."""
        try:
            hints = {
                'total_images': len(soup.find_all('img')),
                'total_scripts': len(soup.find_all('script')),
                'total_stylesheets': len(soup.find_all('link', rel='stylesheet')),
                'has_lazy_loading': bool(soup.find_all(attrs={'loading': 'lazy'})),
                'has_defer_scripts': bool(soup.find_all('script', defer=True)),
                'has_async_scripts': bool(soup.find_all('script', attrs={'async': True}))
            }
            
            return hints
            
        except Exception as e:
            self.logger.warning("Erro na análise de performance", error=str(e))
            return {}


class HybridAttachmentExtractor:
    """Extrator de attachments usando estratégia híbrida."""
    
    def __init__(self, driver: webdriver.Edge):
        self.driver = driver
        self.logger = get_logger("hybrid_extractor")
        self.inventory_logger = get_inventory_logger()
        
        # Extensões permitidas
        self.allowed_extensions = [
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', 
            '.msg', '.txt', '.jpg', '.jpeg', '.png', 
            '.zip', '.rar', '.csv', '.xml'
        ]
    
    def extract_attachments_intelligent(self, html: str, po_number: str) -> List[Dict[str, Any]]:
        """Extração inteligente de attachments com BeautifulSoup."""
        try:
            soup = BeautifulSoup(html, 'lxml')
            attachments = []
            
            # Usar múltiplos seletores para diferentes layouts do Coupa
            attachment_selectors = [
                'a[href*="/attachment/"]',
                'a[href*="download"]',
                '.attachment-link',
                '.file-download',
                '[data-attachment]',
                'a[title*="attachment"]',
                'span[aria-label*="file attachment"]',
                'span[role="button"][aria-label*="file attachment"]'
            ]
            
            for selector in attachment_selectors:
                elements = soup.select(selector)
                
                for element in elements:
                    attachment_info = self._extract_attachment_details(element, po_number)
                    if attachment_info:
                        attachments.append(attachment_info)
            
            # Remover duplicatas baseado na URL
            unique_attachments = []
            seen_urls = set()
            
            for att in attachments:
                if att['url'] not in seen_urls:
                    unique_attachments.append(att)
                    seen_urls.add(att['url'])
            
            self.logger.info("Attachments extraídos", 
                           po_number=po_number, 
                           count=len(unique_attachments))
            
            return unique_attachments
            
        except Exception as e:
            self.logger.error("Erro na extração de attachments", error=str(e), po_number=po_number)
            return []
    
    def _extract_attachment_details(self, element, po_number: str) -> Optional[Dict[str, Any]]:
        """Extrai detalhes completos de um elemento de attachment."""
        try:
            # URL do download
            url = (element.get('href') or 
                   element.get('data-href') or 
                   element.get('data-url'))
            
            if not url:
                return None
            
            # Tornar URL absoluta se necessário
            if url.startswith('/'):
                url = f"https://unilever.coupahost.com{url}"
            
            # Nome do arquivo (múltiplas estratégias)
            filename = (
                element.get('title') or 
                element.get('aria-label') or 
                element.get('data-filename') or
                self._extract_filename_from_text(element.get_text()) or
                self._extract_filename_from_url(url)
            )
            
            if not filename:
                filename = f"{po_number}_attachment_{int(time.time())}"
            
            # Tipo de arquivo
            file_type = self._determine_file_type_from_element(element, filename)
            
            # Metadados adicionais
            metadata = {
                'size': element.get('data-size'),
                'upload_date': element.get('data-upload-date'),
                'uploader': element.get('data-uploader'),
                'description': element.get('data-description')
            }
            
            return {
                'po_number': po_number,
                'url': url,
                'filename': filename,
                'file_type': file_type,
                'metadata': metadata,
                'element_context': self._get_element_context(element)
            }
            
        except Exception as e:
            self.logger.warning("Erro ao extrair detalhes do attachment", error=str(e))
            return None
    
    def _extract_filename_from_text(self, text: str) -> Optional[str]:
        """Extrai nome de arquivo do texto do elemento."""
        if not text:
            return None
        
        text = text.strip()
        
        # Verificar se o texto contém uma extensão válida
        for ext in self.allowed_extensions:
            if ext in text.lower():
                # Tentar extrair nome do arquivo
                parts = text.split()
                for part in parts:
                    if ext in part.lower():
                        return part.strip()
        
        return None
    
    def _extract_filename_from_url(self, url: str) -> Optional[str]:
        """Extrai nome de arquivo da URL."""
        try:
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            
            if filename and any(filename.lower().endswith(ext) for ext in self.allowed_extensions):
                return filename
            
            return None
            
        except Exception:
            return None
    
    def _determine_file_type_from_element(self, element, filename: str) -> str:
        """Determina tipo de arquivo baseado no elemento e nome."""
        try:
            # Verificar extensão do arquivo
            if filename.lower().endswith('.pdf'):
                return 'pdf'
            elif filename.lower().endswith(('.doc', '.docx')):
                return 'document'
            elif filename.lower().endswith(('.xls', '.xlsx')):
                return 'spreadsheet'
            elif filename.lower().endswith('.msg'):
                return 'email'
            elif filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                return 'image'
            elif filename.lower().endswith(('.zip', '.rar')):
                return 'archive'
            elif filename.lower().endswith(('.txt', '.csv', '.xml')):
                return 'text'
            
            # Verificar classes CSS do elemento
            classes = element.get('class', [])
            class_str = ' '.join(classes).lower()
            
            if 'pdf' in class_str:
                return 'pdf'
            elif 'document' in class_str or 'doc' in class_str:
                return 'document'
            elif 'spreadsheet' in class_str or 'excel' in class_str:
                return 'spreadsheet'
            elif 'email' in class_str or 'msg' in class_str:
                return 'email'
            
            return 'unknown'
            
        except Exception:
            return 'unknown'
    
    def _get_element_context(self, element) -> Dict[str, Any]:
        """Obtém contexto do elemento."""
        try:
            return {
                'tag': element.name,
                'classes': element.get('class', []),
                'id': element.get('id', ''),
                'parent_tag': element.parent.name if element.parent else None,
                'siblings_count': len(element.find_siblings()) if hasattr(element, 'find_siblings') else 0
            }
        except Exception:
            return {}


class HybridProcessor:
    """Processador híbrido principal que coordena Selenium + BeautifulSoup."""
    
    def __init__(self, driver: webdriver.Edge):
        self.driver = driver
        self.analyzer = HybridPageAnalyzer(driver)
        self.extractor = HybridAttachmentExtractor(driver)
        self.logger = get_logger("hybrid_processor")
        self.inventory_logger = get_inventory_logger()
    
    def process_url_hybrid(self, url: str, po_number: str) -> Dict[str, Any]:
        """Processa URL usando estratégia híbrida."""
        try:
            start_time = time.time()
            
            # 1. SELENIUM: Navegar e aguardar carregamento
            self.analyzer.load_page_with_selenium(url)
            
            # 2. SELENIUM: Obter HTML completo
            html_content = self.analyzer.get_page_html()
            
            # 3. BEAUTIFULSOUP: Processar HTML estático (mais rápido)
            page_analysis = self.analyzer.analyze_page_structure(html_content)
            
            # 4. Verificar se é página de erro
            if page_analysis.get('error_analysis', {}).get('is_error', False):
                return {
                    'success': False,
                    'po_number': po_number,
                    'url': url,
                    'error': 'Página de erro detectada',
                    'error_details': page_analysis['error_analysis']
                }
            
            # 5. SELENIUM: Interações dinâmicas (se necessário)
            if page_analysis['page_type'] == 'po_detail':
                # Aguardar elementos dinâmicos carregarem
                time.sleep(2)
                # Atualizar HTML após carregamento dinâmico
                html_content = self.analyzer.get_page_html()
                page_analysis = self.analyzer.analyze_page_structure(html_content)
            
            # 6. BEAUTIFULSOUP: Extrair attachments
            attachments = self.extractor.extract_attachments_intelligent(html_content, po_number)
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'po_number': po_number,
                'url': url,
                'attachments': attachments,
                'page_analysis': page_analysis,
                'processing_time': processing_time,
                'attachments_count': len(attachments)
            }
            
        except Exception as e:
            self.logger.error("Erro no processamento híbrido", error=str(e), po_number=po_number)
            return {
                'success': False,
                'po_number': po_number,
                'url': url,
                'error': str(e)
            }


if __name__ == "__main__":
    # Teste do sistema híbrido
    print("🔧 Testando sistema híbrido Selenium + BeautifulSoup...")
    
    # Este teste requer um driver Selenium ativo
    # Em um ambiente real, seria inicializado aqui
    
    print("✅ Sistema híbrido implementado!")
    print("📋 Funcionalidades:")
    print("   • Navegação dinâmica com Selenium")
    print("   • Parsing rápido com BeautifulSoup")
    print("   • Detecção inteligente de erros")
    print("   • Extração robusta de attachments")
    print("   • Análise estrutural de páginas")

