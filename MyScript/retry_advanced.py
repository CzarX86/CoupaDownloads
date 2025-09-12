"""
Sistema de Retry Robusto com Tenacity
Implementa retry automático com backoff exponencial e jitter para operações críticas
"""

import time
import random
from typing import Any, Callable, Optional, Type, Union, List
from functools import wraps
import tenacity
from tenacity import (
    retry, stop_after_attempt, stop_after_delay, 
    wait_exponential, wait_fixed, wait_random,
    retry_if_exception_type, retry_if_result,
    before_sleep_log, after_log
)
from selenium.common.exceptions import (
    TimeoutException, WebDriverException, 
    InvalidSessionIdException, NoSuchWindowException,
    ElementClickInterceptedException, StaleElementReferenceException
)
import requests
from requests.exceptions import (
    ConnectionError, Timeout, RequestException,
    HTTPError, TooManyRedirects
)

# Importação condicional
try:
    from config_advanced import get_config
except ImportError:
    pass

try:
    from logging_advanced import get_logger
except ImportError:
    pass


class RetryConfig:
    """Configuração de retry para diferentes tipos de operações."""
    
    # Configurações padrão
    DEFAULT_ATTEMPTS = 3
    DEFAULT_DELAY = 1.0
    DEFAULT_MAX_DELAY = 60.0
    DEFAULT_MULTIPLIER = 2.0
    DEFAULT_JITTER = True
    
    # Configurações específicas por tipo de operação
    CONFIGS = {
        "download": {
            "attempts": 5,
            "delay": 2.0,
            "max_delay": 30.0,
            "multiplier": 1.5,
            "exceptions": (ConnectionError, Timeout, RequestException, HTTPError)
        },
        "browser_action": {
            "attempts": 3,
            "delay": 1.0,
            "max_delay": 10.0,
            "multiplier": 2.0,
            "exceptions": (
                ElementClickInterceptedException, 
                StaleElementReferenceException,
                TimeoutException
            )
        },
        "page_load": {
            "attempts": 3,
            "delay": 2.0,
            "max_delay": 15.0,
            "multiplier": 1.5,
            "exceptions": (TimeoutException, WebDriverException)
        },
        "element_find": {
            "attempts": 5,
            "delay": 0.5,
            "max_delay": 5.0,
            "multiplier": 1.2,
            "exceptions": (TimeoutException, StaleElementReferenceException)
        },
        "csv_operation": {
            "attempts": 3,
            "delay": 1.0,
            "max_delay": 5.0,
            "multiplier": 1.5,
            "exceptions": (IOError, PermissionError, FileNotFoundError)
        }
    }


class RetryManager:
    """Gerenciador de retry com configurações específicas."""
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_logger("retry")
        self.retry_configs = RetryConfig.CONFIGS
    
    def get_retry_decorator(self, operation_type: str, **kwargs):
        """Retorna decorator de retry configurado para tipo de operação."""
        
        if operation_type not in self.retry_configs:
            operation_type = "default"
            config = {
                "attempts": RetryConfig.DEFAULT_ATTEMPTS,
                "delay": RetryConfig.DEFAULT_DELAY,
                "max_delay": RetryConfig.DEFAULT_MAX_DELAY,
                "multiplier": RetryConfig.DEFAULT_MULTIPLIER,
                "exceptions": Exception
            }
        else:
            config = self.retry_configs[operation_type].copy()
        
        # Sobrescrever com kwargs se fornecidos
        config.update(kwargs)
        
        return retry(
            stop=stop_after_attempt(config["attempts"]),
            wait=wait_exponential(
                multiplier=config["multiplier"],
                min=config["delay"],
                max=config["max_delay"]
            ) if config.get("jitter", True) else wait_fixed(config["delay"]),
            retry=retry_if_exception_type(config["exceptions"]),
            before_sleep=before_sleep_log(self.logger, "WARNING"),
            after=after_log(self.logger, "INFO"),
            reraise=True
        )
    
    def retry_with_custom_logic(self, func: Callable, *args, **kwargs):
        """Executa função com retry e lógica customizada."""
        
        operation_name = func.__name__
        max_attempts = kwargs.get('max_attempts', 3)
        delay = kwargs.get('delay', 1.0)
        
        for attempt in range(max_attempts):
            try:
                self.logger.info(f"Tentativa {attempt + 1}/{max_attempts} para {operation_name}")
                result = func(*args, **kwargs)
                
                if attempt > 0:
                    self.logger.info(f"{operation_name} bem-sucedida na tentativa {attempt + 1}")
                
                return result
                
            except Exception as e:
                self.logger.warning(f"Tentativa {attempt + 1} falhou: {str(e)}")
                
                if attempt == max_attempts - 1:
                    self.logger.error(f"{operation_name} falhou após {max_attempts} tentativas")
                    raise
                
                # Calcular delay com jitter
                sleep_time = delay * (2 ** attempt) + random.uniform(0, 1)
                self.logger.info(f"Aguardando {sleep_time:.2f}s antes da próxima tentativa")
                time.sleep(sleep_time)


# Instância global do gerenciador de retry
retry_manager = RetryManager()


# Decorators específicos para diferentes operações
def retry_download(max_attempts: int = 5, delay: float = 2.0):
    """Decorator para operações de download."""
    return retry_manager.get_retry_decorator("download", attempts=max_attempts, delay=delay)


def retry_browser_action(max_attempts: int = 3, delay: float = 1.0):
    """Decorator para ações de browser."""
    return retry_manager.get_retry_decorator("browser_action", attempts=max_attempts, delay=delay)


def retry_page_load(max_attempts: int = 3, delay: float = 2.0):
    """Decorator para carregamento de páginas."""
    return retry_manager.get_retry_decorator("page_load", attempts=max_attempts, delay=delay)


def retry_element_find(max_attempts: int = 5, delay: float = 0.5):
    """Decorator para busca de elementos."""
    return retry_manager.get_retry_decorator("element_find", attempts=max_attempts, delay=delay)


def retry_csv_operation(max_attempts: int = 3, delay: float = 1.0):
    """Decorator para operações de CSV."""
    return retry_manager.get_retry_decorator("csv_operation", attempts=max_attempts, delay=delay)


def retry_with_custom_config(**config):
    """Decorator com configuração customizada."""
    return retry_manager.get_retry_decorator("default", **config)


class RobustDownloader:
    """Downloader com retry automático."""
    
    def __init__(self):
        self.logger = get_logger("robust_downloader")
    
    @retry_download(max_attempts=5, delay=2.0)
    def download_file(self, url: str, filename: str, download_dir: str) -> bool:
        """Baixa arquivo com retry automático."""
        try:
            import requests
            
            self.logger.info("Iniciando download", url=url, filename=filename)
            
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            file_path = os.path.join(download_dir, filename)
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            self.logger.info("Download concluído", filename=filename)
            return True
            
        except Exception as e:
            self.logger.error("Erro no download", error=str(e), url=url)
            raise
    
    @retry_browser_action(max_attempts=3, delay=1.0)
    def click_element(self, driver, element):
        """Clica em elemento com retry automático."""
        try:
            self.logger.info("Tentando clicar em elemento")
            
            # Scroll para o elemento se necessário
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)
            
            # Tentar clique normal
            element.click()
            
            self.logger.info("Clique realizado com sucesso")
            return True
            
        except ElementClickInterceptedException:
            self.logger.warning("Clique interceptado, tentando JavaScript")
            driver.execute_script("arguments[0].click();", element)
            return True
            
        except Exception as e:
            self.logger.error("Erro ao clicar", error=str(e))
            raise
    
    @retry_page_load(max_attempts=3, delay=2.0)
    def load_page(self, driver, url: str) -> bool:
        """Carrega página com retry automático."""
        try:
            self.logger.info("Carregando página", url=url)
            
            driver.get(url)
            
            # Aguardar carregamento completo
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            wait = WebDriverWait(driver, 15)
            wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
            
            self.logger.info("Página carregada com sucesso", url=url)
            return True
            
        except Exception as e:
            self.logger.error("Erro ao carregar página", error=str(e), url=url)
            raise


class RobustCSVManager:
    """Gerenciador de CSV com retry automático."""
    
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.logger = get_logger("robust_csv")
    
    @retry_csv_operation(max_attempts=3, delay=1.0)
    def read_csv(self):
        """Lê CSV com retry automático."""
        try:
            import pandas as pd
            
            self.logger.info("Lendo CSV", path=self.csv_path)
            df = pd.read_csv(self.csv_path)
            
            self.logger.info("CSV lido com sucesso", rows=len(df))
            return df
            
        except Exception as e:
            self.logger.error("Erro ao ler CSV", error=str(e), path=self.csv_path)
            raise
    
    @retry_csv_operation(max_attempts=3, delay=1.0)
    def write_csv(self, df):
        """Escreve CSV com retry automático."""
        try:
            self.logger.info("Escrevendo CSV", path=self.csv_path, rows=len(df))
            
            df.to_csv(self.csv_path, index=False)
            
            self.logger.info("CSV escrito com sucesso", path=self.csv_path)
            return True
            
        except Exception as e:
            self.logger.error("Erro ao escrever CSV", error=str(e), path=self.csv_path)
            raise
    
    @retry_csv_operation(max_attempts=3, delay=1.0)
    def append_to_csv(self, new_data):
        """Adiciona dados ao CSV com retry automático."""
        try:
            import pandas as pd
            
            self.logger.info("Adicionando dados ao CSV", path=self.csv_path)
            
            # Ler CSV existente
            if os.path.exists(self.csv_path):
                df = pd.read_csv(self.csv_path)
            else:
                df = pd.DataFrame()
            
            # Adicionar novos dados
            new_df = pd.DataFrame([new_data])
            df = pd.concat([df, new_df], ignore_index=True)
            
            # Escrever CSV atualizado
            df.to_csv(self.csv_path, index=False)
            
            self.logger.info("Dados adicionados ao CSV", path=self.csv_path)
            return True
            
        except Exception as e:
            self.logger.error("Erro ao adicionar dados ao CSV", error=str(e), path=self.csv_path)
            raise


class RobustElementFinder:
    """Buscador de elementos com retry automático."""
    
    def __init__(self, driver):
        self.driver = driver
        self.logger = get_logger("robust_element_finder")
    
    @retry_element_find(max_attempts=5, delay=0.5)
    def find_elements(self, by, value, timeout: int = 10):
        """Busca elementos com retry automático."""
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            self.logger.info("Buscando elementos", by=by, value=value)
            
            wait = WebDriverWait(self.driver, timeout)
            elements = wait.until(EC.presence_of_all_elements_located((by, value)))
            
            self.logger.info("Elementos encontrados", count=len(elements))
            return elements
            
        except Exception as e:
            self.logger.error("Erro ao buscar elementos", error=str(e), by=by, value=value)
            raise
    
    @retry_element_find(max_attempts=5, delay=0.5)
    def find_element(self, by, value, timeout: int = 10):
        """Busca elemento único com retry automático."""
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            self.logger.info("Buscando elemento", by=by, value=value)
            
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(EC.presence_of_element_located((by, value)))
            
            self.logger.info("Elemento encontrado")
            return element
            
        except Exception as e:
            self.logger.error("Erro ao buscar elemento", error=str(e), by=by, value=value)
            raise


# Funções utilitárias com retry
@retry_with_custom_config(attempts=3, delay=1.0)
def robust_file_operation(operation: Callable, *args, **kwargs):
    """Executa operação de arquivo com retry."""
    logger = get_logger("file_operation")
    
    try:
        logger.info("Executando operação de arquivo")
        result = operation(*args, **kwargs)
        logger.info("Operação de arquivo concluída")
        return result
        
    except Exception as e:
        logger.error("Erro em operação de arquivo", error=str(e))
        raise


@retry_with_custom_config(attempts=5, delay=2.0)
def robust_network_request(request_func: Callable, *args, **kwargs):
    """Executa requisição de rede com retry."""
    logger = get_logger("network_request")
    
    try:
        logger.info("Executando requisição de rede")
        result = request_func(*args, **kwargs)
        logger.info("Requisição de rede concluída")
        return result
        
    except Exception as e:
        logger.error("Erro em requisição de rede", error=str(e))
        raise


if __name__ == "__main__":
    # Teste do sistema de retry
    print("🔧 Testando sistema de retry...")
    
    logger = get_logger("retry_test")
    
    # Teste de função com retry
    @retry_download(max_attempts=3, delay=1.0)
    def test_function():
        logger.info("Executando função de teste")
        # Simular falha ocasional
        if random.random() < 0.7:  # 70% de chance de falhar
            raise ConnectionError("Simulação de erro de conexão")
        return "Sucesso!"
    
    try:
        result = test_function()
        print(f"✅ Função executada com sucesso: {result}")
    except Exception as e:
        print(f"❌ Função falhou após todas as tentativas: {e}")
    
    print("✅ Sistema de retry testado!")

