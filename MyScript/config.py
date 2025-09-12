"""
Módulo de Configuração - Centraliza todas as configurações do sistema
Aplica Single Responsibility Principle
"""

import os
from dataclasses import dataclass
from typing import List


@dataclass
class SystemConfig:
    """Configurações do sistema principal."""
    excel_path: str = "src/MyScript/data/input.csv"
    csv_path: str = "src/MyScript/download_inventory.csv"  # Caminho absoluto para MyScript
    base_url: str = "https://unilever.coupahost.com"


@dataclass  
class DownloadConfig:
    """Configurações de download."""
    download_dir: str = "~/Downloads/CoupaDownloads"
    max_workers: int = 1
    timeout: int = 30
    chunk_size: int = 8192


@dataclass
class EdgeProfileConfig:
    """Configurações do perfil Edge."""
    login_check_url: str = "https://unilever.coupahost.com"
    login_check_timeout: int = 3
    login_selectors: List[str] = None
    
    def __post_init__(self):
        if self.login_selectors is None:
            self.login_selectors = [
                "input[type='password']",
                "input[name*='password']",
                "button[type='submit']"
            ]


class ConfigManager:
    """Gerenciador de configurações - aplica Singleton Pattern."""
    
    def __init__(self):
        self.system = SystemConfig()
        self.download = DownloadConfig()
        self.edge_profile = EdgeProfileConfig()


# Instância global do gerenciador de configurações
config_manager = ConfigManager()
