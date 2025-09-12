"""
Sistema de Logging Estruturado com structlog
Fornece logging robusto, contextual e performático para todo o sistema
"""

import os
import sys
import logging
import logging.handlers
from typing import Any, Dict, Optional, Union
from pathlib import Path
import structlog
from structlog.stdlib import LoggerFactory
from structlog.processors import JSONRenderer, KeyValueRenderer
from structlog.contextvars import merge_contextvars
from rich.console import Console
from rich.logging import RichHandler

# Importação condicional para funcionar tanto como módulo quanto como script
try:
    from config_advanced import get_logging_config
except ImportError:
    from config_advanced import get_logging_config


class StructuredLogger:
    """Sistema de logging estruturado com structlog."""
    
    def __init__(self, name: str = "coupa_downloads"):
        self.name = name
        self.config = get_logging_config()
        self.console = Console()
        
        # Configurar structlog
        self._setup_structlog()
        
        # Obter logger
        self.logger = structlog.get_logger(name)
    
    def _setup_structlog(self):
        """Configura o structlog com processadores e renderizadores."""
        
        # Verificar se já foi configurado
        if hasattr(structlog, '_configured') and structlog._configured:
            return
        
        # Processadores comuns
        processors = [
            merge_contextvars,  # Mesclar variáveis de contexto
            structlog.stdlib.add_log_level,  # Adicionar nível de log
            structlog.stdlib.add_logger_name,  # Adicionar nome do logger
            structlog.stdlib.PositionalArgumentsFormatter(),  # Formatar argumentos posicionais
            structlog.processors.TimeStamper(fmt="iso"),  # Timestamp ISO
            structlog.processors.StackInfoRenderer(),  # Informações de stack
            structlog.processors.format_exc_info,  # Formatar exceções
        ]
        
        # Renderizador baseado na configuração
        if self.config.format == "json":
            processors.append(JSONRenderer())
        elif self.config.format == "text":
            processors.append(KeyValueRenderer())
        else:  # console
            processors.append(structlog.dev.ConsoleRenderer(colors=True))
        
        # Configurar structlog
        structlog.configure(
            processors=processors,
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        
        # Marcar como configurado
        structlog._configured = True
        
        # Configurar logging padrão do Python
        self._setup_stdlib_logging()
    
    def _setup_stdlib_logging(self):
        """Configura o logging padrão do Python."""
        
        # Configurar nível de log
        level = getattr(logging, self.config.level.upper(), logging.INFO)
        
        # Configurar handler baseado no formato
        if self.config.format == "console":
            handler = RichHandler(
                console=self.console,
                show_time=True,
                show_path=True,
                markup=True
            )
        elif self.config.file_path:
            # Handler para arquivo com rotação
            handler = logging.handlers.RotatingFileHandler(
                filename=self.config.file_path,
                maxBytes=self.config.max_file_size,
                backupCount=self.config.backup_count,
                encoding='utf-8'
            )
        else:
            # Handler padrão para console
            handler = logging.StreamHandler(sys.stdout)
        
        # Configurar formato
        if self.config.format == "json":
            formatter = logging.Formatter('%(message)s')
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        handler.setFormatter(formatter)
        
        # Configurar logger raiz
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        root_logger.addHandler(handler)
        
        # Configurar loggers específicos
        self._configure_specific_loggers()
    
    def _configure_specific_loggers(self):
        """Configura loggers específicos para diferentes componentes."""
        
        # Logger para Selenium (reduzir verbosidade)
        selenium_logger = logging.getLogger("selenium")
        selenium_logger.setLevel(logging.WARNING)
        
        # Logger para urllib3 (reduzir verbosidade)
        urllib3_logger = logging.getLogger("urllib3")
        urllib3_logger.setLevel(logging.WARNING)
        
        # Logger para httpx (se usado)
        httpx_logger = logging.getLogger("httpx")
        httpx_logger.setLevel(logging.INFO)
    
    def get_logger(self, name: Optional[str] = None) -> structlog.BoundLogger:
        """Retorna um logger estruturado."""
        if name:
            return structlog.get_logger(name)
        return self.logger
    
    def bind_context(self, **kwargs) -> structlog.BoundLogger:
        """Vincula contexto ao logger."""
        return self.logger.bind(**kwargs)


class ContextualLogger:
    """Logger contextual para diferentes componentes do sistema."""
    
    def __init__(self, component: str, logger: Optional[StructuredLogger] = None):
        self.component = component
        self.logger = logger or StructuredLogger()
        self._logger = self.logger.get_logger(component)
    
    def info(self, message: str, **kwargs):
        """Log de informação."""
        self._logger.info(message, component=self.component, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log de aviso."""
        self._logger.warning(message, component=self.component, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log de erro."""
        self._logger.error(message, component=self.component, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log de debug."""
        self._logger.debug(message, component=self.component, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log crítico."""
        self._logger.critical(message, component=self.component, **kwargs)
    
    def bind(self, **kwargs) -> 'ContextualLogger':
        """Vincula contexto adicional."""
        bound_logger = self._logger.bind(**kwargs)
        new_logger = ContextualLogger(self.component, self.logger)
        new_logger._logger = bound_logger
        return new_logger


class DownloadLogger(ContextualLogger):
    """Logger especializado para downloads."""
    
    def __init__(self, po_number: str = None, filename: str = None):
        super().__init__("download")
        if po_number:
            self._logger = self._logger.bind(po_number=po_number)
        if filename:
            self._logger = self._logger.bind(filename=filename)
    
    def download_started(self, url: str, filename: str):
        """Log quando download inicia."""
        self.info("Download iniciado", url=url, filename=filename)
    
    def download_completed(self, filename: str, file_size: int, duration: float):
        """Log quando download completa."""
        self.info("Download concluído", 
                 filename=filename, 
                 file_size=file_size, 
                 duration=duration)
    
    def download_failed(self, filename: str, error: str, retry_count: int = 0):
        """Log quando download falha."""
        self.error("Download falhou", 
                  filename=filename, 
                  error=error, 
                  retry_count=retry_count)
    
    def download_retry(self, filename: str, attempt: int, max_attempts: int):
        """Log quando download é retentado."""
        self.warning("Tentando novamente", 
                    filename=filename, 
                    attempt=attempt, 
                    max_attempts=max_attempts)


class InventoryLogger(ContextualLogger):
    """Logger especializado para inventário."""
    
    def __init__(self):
        super().__init__("inventory")
    
    def po_processing_started(self, po_number: str, url: str):
        """Log quando processamento de PO inicia."""
        self.info("Processando PO", po_number=po_number, url=url)
    
    def attachments_found(self, po_number: str, count: int):
        """Log quando anexos são encontrados."""
        self.info("Anexos encontrados", po_number=po_number, count=count)
    
    def attachment_inventoried(self, po_number: str, filename: str, file_type: str):
        """Log quando anexo é inventariado."""
        self.info("Anexo inventariado", 
                 po_number=po_number, 
                 filename=filename, 
                 file_type=file_type)
    
    def error_page_detected(self, po_number: str, url: str):
        """Log quando página de erro é detectada."""
        self.warning("Página de erro detectada", po_number=po_number, url=url)
    
    def csv_updated(self, filename: str, total_entries: int):
        """Log quando CSV é atualizado."""
        self.info("CSV atualizado", filename=filename, total_entries=total_entries)


class BrowserLogger(ContextualLogger):
    """Logger especializado para operações de browser."""
    
    def __init__(self):
        super().__init__("browser")
    
    def window_created(self, window_id: str, window_name: str):
        """Log quando janela é criada."""
        self.info("Janela criada", window_id=window_id, window_name=window_name)
    
    def tab_created(self, tab_id: str, url: str, window_name: str):
        """Log quando aba é criada."""
        self.info("Aba criada", tab_id=tab_id, url=url, window_name=window_name)
    
    def tab_closed(self, tab_id: str, window_name: str):
        """Log quando aba é fechada."""
        self.info("Aba fechada", tab_id=tab_id, window_name=window_name)
    
    def profile_loaded(self, profile_path: str, success: bool):
        """Log quando perfil é carregado."""
        if success:
            self.info("Perfil carregado", profile_path=profile_path)
        else:
            self.warning("Falha ao carregar perfil", profile_path=profile_path)
    
    def login_verified(self, success: bool):
        """Log quando login é verificado."""
        if success:
            self.info("Login verificado com sucesso")
        else:
            self.warning("Usuário não está logado")


class PerformanceLogger(ContextualLogger):
    """Logger especializado para métricas de performance."""
    
    def __init__(self):
        super().__init__("performance")
    
    def timing(self, operation: str, duration: float, **kwargs):
        """Log de timing de operações."""
        self.info("Operação concluída", 
                 operation=operation, 
                 duration=duration, 
                 **kwargs)
    
    def batch_processing(self, batch_size: int, total_processed: int, 
                        success_rate: float, duration: float):
        """Log de processamento em lote."""
        self.info("Lote processado", 
                 batch_size=batch_size,
                 total_processed=total_processed,
                 success_rate=success_rate,
                 duration=duration)
    
    def memory_usage(self, memory_mb: float, component: str):
        """Log de uso de memória."""
        self.info("Uso de memória", memory_mb=memory_mb, component=component)
    
    def throughput(self, items_per_second: float, operation: str):
        """Log de throughput."""
        self.info("Throughput", 
                 items_per_second=items_per_second, 
                 operation=operation)


# Instâncias globais dos loggers especializados
download_logger = DownloadLogger()
inventory_logger = InventoryLogger()
browser_logger = BrowserLogger()
performance_logger = PerformanceLogger()

# Logger principal
main_logger = StructuredLogger()


def get_logger(name: str = "coupa_downloads") -> structlog.BoundLogger:
    """Retorna um logger estruturado."""
    return main_logger.get_logger(name)


def get_download_logger(po_number: str = None, filename: str = None) -> DownloadLogger:
    """Retorna logger especializado para downloads."""
    return DownloadLogger(po_number, filename)


def get_inventory_logger() -> InventoryLogger:
    """Retorna logger especializado para inventário."""
    return inventory_logger


def get_browser_logger() -> BrowserLogger:
    """Retorna logger especializado para browser."""
    return browser_logger


def get_performance_logger() -> PerformanceLogger:
    """Retorna logger especializado para performance."""
    return performance_logger


def log_function_call(func_name: str, **kwargs):
    """Decorator para logar chamadas de função."""
    def decorator(func):
        def wrapper(*args, **func_kwargs):
            logger = get_logger("function_calls")
            logger.info("Função chamada", 
                       function=func_name, 
                       args_count=len(args),
                       kwargs_count=len(func_kwargs),
                       **kwargs)
            
            try:
                result = func(*args, **func_kwargs)
                logger.info("Função concluída", function=func_name, success=True)
                return result
            except Exception as e:
                logger.error("Função falhou", 
                            function=func_name, 
                            error=str(e), 
                            success=False)
                raise
        
        return wrapper
    return decorator


if __name__ == "__main__":
    # Teste do sistema de logging
    print("🔧 Testando sistema de logging...")
    
    # Testar logger principal
    logger = get_logger()
    logger.info("Sistema de logging inicializado")
    
    # Testar loggers especializados
    download_logger.download_started("https://example.com/file.pdf", "file.pdf")
    inventory_logger.attachments_found("PO123", 5)
    browser_logger.window_created("window_1", "Janela 1")
    performance_logger.timing("download_batch", 2.5)
    
    print("✅ Sistema de logging testado com sucesso!")

