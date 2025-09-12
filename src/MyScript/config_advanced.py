"""
Configuração Avançada com Pydantic - Sistema Robusto e Validado
Substitui o sistema de configuração anterior por um mais robusto e type-safe
"""

import os
from typing import List, Optional, Union
from pathlib import Path
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class CoupaConfig(BaseSettings):
    """Configuração principal do sistema CoupaDownloads com validação automática."""
    
    # URLs e caminhos
    base_url: str = Field(default="https://unilever.coupahost.com", description="URL base do Coupa")
    excel_path: str = Field(default="src/MyScript/data/input.csv", description="Caminho do arquivo de POs (CSV ou Excel)")
    csv_path: str = Field(default="src/MyScript/download_inventory.csv", description="Caminho do CSV de inventário")
    download_dir: str = Field(default="~/Downloads/CoupaDownloads", description="Diretório de downloads")
    
    # Configurações de browser
    headless: bool = Field(default=False, description="Executar em modo headless")
    profile_mode: str = Field(default="minimal", description="Modo do perfil Edge")
    num_windows: int = Field(default=2, ge=1, le=8, description="Número de janelas")
    max_tabs_per_window: int = Field(default=3, ge=1, le=10, description="Máximo de abas por janela")
    
    # Configurações de performance
    max_workers: int = Field(default=4, ge=1, le=10, description="Workers paralelos")
    timeout: int = Field(default=15, ge=5, le=60, description="Timeout em segundos")
    batch_size: int = Field(default=5, ge=1, le=20, description="Tamanho do lote")
    check_interval: int = Field(default=2, ge=1, le=30, description="Intervalo de verificação")
    
    # Configurações de retry
    retry_attempts: int = Field(default=3, ge=1, le=10, description="Tentativas de retry")
    retry_delay: float = Field(default=1.0, ge=0.1, le=10.0, description="Delay entre tentativas")
    
    # Configurações de arquivo
    allowed_extensions: List[str] = Field(
        default=[".pdf", ".msg", ".docx", ".xlsx", ".txt", ".jpg", ".png", ".zip", ".rar", ".csv", ".xml"],
        description="Extensões de arquivo permitidas"
    )
    
    # Configurações de perfil Edge
    edge_profile_path: Optional[str] = Field(default=None, description="Caminho do perfil Edge")
    login_check_url: str = Field(default="https://unilever.coupahost.com", description="URL para verificar login")
    login_check_timeout: int = Field(default=3, ge=1, le=10, description="Timeout para verificação de login")
    
    # Configurações de logging
    log_level: str = Field(default="INFO", description="Nível de log")
    log_format: str = Field(default="json", description="Formato do log")
    log_file: Optional[str] = Field(default=None, description="Arquivo de log")
    
    # Configurações de processamento
    max_lines: Optional[int] = Field(default=None, ge=1, description="Máximo de linhas para processar")
    random_sample: Optional[int] = Field(default=None, ge=1, description="Amostra aleatória")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        validate_assignment = True
        
    @validator('profile_mode')
    def validate_profile_mode(cls, v):
        if v not in ['none', 'minimal', 'full']:
            raise ValueError('profile_mode deve ser: none, minimal ou full')
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        if v.upper() not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            raise ValueError('log_level deve ser: DEBUG, INFO, WARNING, ERROR ou CRITICAL')
        return v.upper()
    
    @validator('log_format')
    def validate_log_format(cls, v):
        if v not in ['json', 'text', 'console']:
            raise ValueError('log_format deve ser: json, text ou console')
        return v
    
    @validator('download_dir')
    def expand_download_dir(cls, v):
        return os.path.expanduser(v)
    
    @validator('excel_path')
    def validate_excel_path(cls, v):
        # Tentar diferentes caminhos possíveis (suporta .csv e .xlsx)
        possible_paths = [
            v,
            os.path.join(os.getcwd(), v),
            os.path.join(os.path.dirname(__file__), v),
            os.path.join(os.path.dirname(__file__), os.path.basename(v))
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return os.path.abspath(path)
        return os.path.abspath(v)
    
    def get_edge_profile_path(self) -> str:
        """Retorna o caminho do perfil Edge baseado no OS."""
        if self.edge_profile_path:
            return os.path.expanduser(self.edge_profile_path)
        
        if os.name == 'nt':  # Windows
            return os.path.expanduser("%LOCALAPPDATA%/Microsoft/Edge/User Data")
        else:  # macOS/Linux
            return os.path.expanduser("~/Library/Application Support/Microsoft Edge")
    
    def get_login_selectors(self) -> List[str]:
        """Retorna os seletores para verificação de login."""
        return [
            "input[type='password']",
            "input[name*='password']",
            "button[type='submit']"
        ]
    
    def get_attachment_selectors(self) -> str:
        """Retorna os seletores CSS para attachments."""
        return (
            "div[class*='commentAttachments'] a[href*='attachment_file'], "
            "div[class*='attachment'] a[href*='attachment_file'], "
            "div[class*='attachment'] a[href*='download'], "
            "div[class*='attachment'] a[href*='attachment'], "
            "span[aria-label*='file attachment'], "
            "span[role='button'][aria-label*='file attachment'], "
            "span[title*='.pdf'], span[title*='.docx'], span[title*='.msg']"
        )
    
    def get_browser_prefs(self) -> dict:
        """Retorna as preferências do browser."""
        return {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
        }
    
    def get_retry_config(self) -> dict:
        """Retorna configuração para retry."""
        return {
            "attempts": self.retry_attempts,
            "delay": self.retry_delay,
            "backoff": "exponential",
            "jitter": True
        }


class PlaywrightConfig(BaseSettings):
    """Configuração específica para Playwright."""
    
    browser_type: str = Field(default="msedge", description="Tipo de browser")
    headless: bool = Field(default=False, description="Modo headless")
    slow_mo: int = Field(default=0, ge=0, le=5000, description="Delay entre ações")
    timeout: int = Field(default=30000, ge=1000, le=120000, description="Timeout em ms")
    viewport_width: int = Field(default=1920, ge=800, le=3840, description="Largura da viewport")
    viewport_height: int = Field(default=1080, ge=600, le=2160, description="Altura da viewport")
    
    class Config:
        env_prefix = "PLAYWRIGHT_"
        case_sensitive = False


class AsyncConfig(BaseSettings):
    """Configuração para processamento assíncrono."""
    
    max_concurrent_downloads: int = Field(default=5, ge=1, le=20, description="Downloads simultâneos")
    download_timeout: int = Field(default=30, ge=5, le=300, description="Timeout de download")
    chunk_size: int = Field(default=8192, ge=1024, le=65536, description="Tamanho do chunk")
    max_retries: int = Field(default=3, ge=1, le=10, description="Máximo de tentativas")
    
    class Config:
        env_prefix = "ASYNC_"
        case_sensitive = False


class LoggingConfig(BaseSettings):
    """Configuração de logging estruturado."""
    
    level: str = Field(default="INFO", description="Nível de log")
    format: str = Field(default="json", description="Formato do log")
    file_path: Optional[str] = Field(default=None, description="Arquivo de log")
    max_file_size: int = Field(default=10485760, ge=1024, description="Tamanho máximo do arquivo")
    backup_count: int = Field(default=5, ge=1, le=20, description="Número de backups")
    
    class Config:
        env_prefix = "LOG_"
        case_sensitive = False


class ConfigManager:
    """Gerenciador centralizado de configurações."""
    
    def __init__(self):
        self.coupa = CoupaConfig()
        self.playwright = PlaywrightConfig()
        self.async_config = AsyncConfig()
        self.logging = LoggingConfig()
        
        # Criar diretórios necessários
        self._create_directories()
    
    def _create_directories(self):
        """Cria diretórios necessários."""
        directories = [
            os.path.dirname(self.coupa.csv_path),
            self.coupa.download_dir
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def validate_config(self) -> bool:
        """Valida todas as configurações."""
        try:
            # Validar configurações principais
            self.coupa.model_validate(self.coupa.dict())
            self.playwright.model_validate(self.playwright.dict())
            self.async_config.model_validate(self.async_config.dict())
            self.logging.model_validate(self.logging.dict())
            
            return True
        except Exception as e:
            print(f"❌ Erro na validação de configuração: {e}")
            return False
    
    def get_summary(self) -> dict:
        """Retorna resumo das configurações."""
        return {
            "coupa": {
                "base_url": self.coupa.base_url,
                "num_windows": self.coupa.num_windows,
                "max_tabs_per_window": self.coupa.max_tabs_per_window,
                "max_workers": self.coupa.max_workers,
                "headless": self.coupa.headless,
                "profile_mode": self.coupa.profile_mode
            },
            "playwright": {
                "browser_type": self.playwright.browser_type,
                "headless": self.playwright.headless,
                "timeout": self.playwright.timeout
            },
            "async": {
                "max_concurrent_downloads": self.async_config.max_concurrent_downloads,
                "download_timeout": self.async_config.download_timeout,
                "max_retries": self.async_config.max_retries
            },
            "logging": {
                "level": self.logging.level,
                "format": self.logging.format,
                "file_path": self.logging.file_path
            }
        }


# Instância global do gerenciador de configurações
config_manager = ConfigManager()


def get_config() -> CoupaConfig:
    """Retorna a configuração principal."""
    return config_manager.coupa


def get_playwright_config() -> PlaywrightConfig:
    """Retorna a configuração do Playwright."""
    return config_manager.playwright


def get_async_config() -> AsyncConfig:
    """Retorna a configuração assíncrona."""
    return config_manager.async_config


def get_logging_config() -> LoggingConfig:
    """Retorna a configuração de logging."""
    return config_manager.logging


def validate_all_configs() -> bool:
    """Valida todas as configurações."""
    return config_manager.validate_config()


def get_config_summary() -> dict:
    """Retorna resumo de todas as configurações."""
    return config_manager.get_summary()


if __name__ == "__main__":
    # Teste das configurações
    print("🔧 Testando configurações...")
    
    if validate_all_configs():
        print("✅ Todas as configurações são válidas!")
        
        summary = get_config_summary()
        print("\n📋 Resumo das configurações:")
        for section, config in summary.items():
            print(f"\n{section.upper()}:")
            for key, value in config.items():
                print(f"  {key}: {value}")
    else:
        print("❌ Erro na validação das configurações!")
