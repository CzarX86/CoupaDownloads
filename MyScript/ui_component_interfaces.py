"""
Módulo de Interfaces - Define contratos para diferentes componentes
Aplica Interface Segregation Principle
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class DownloadInfo:
    """DTO para informações de download."""
    po_number: str
    url: str
    filename: str
    file_type: str = "unknown"
    status: str = "pending"
    created_at: str = ""
    downloaded_at: str = ""
    error_message: str = ""
    file_size: int = 0


@dataclass
class TabInfo:
    """DTO para informações de aba."""
    tab_id: str
    url: str
    url_index: int
    window_name: str
    window_id: str
    created_at: float


class IInventoryManager(ABC):
    """Interface para gerenciamento de inventário."""
    
    @abstractmethod
    def add_download_url(self, download_info: DownloadInfo) -> bool:
        """Adiciona uma URL de download ao inventário."""
        pass
    
    @abstractmethod
    def get_pending_downloads(self) -> List[DownloadInfo]:
        """Retorna lista de downloads pendentes."""
        pass
    
    @abstractmethod
    def update_download_status(self, po_number: str, filename: str, 
                             status: str, error_message: str = "") -> bool:
        """Atualiza o status de um download."""
        pass


class IDownloadService(ABC):
    """Interface para serviço de download."""
    
    @abstractmethod
    def download_file(self, download_info: DownloadInfo) -> Dict[str, Any]:
        """Baixa um arquivo individual."""
        pass
    
    @abstractmethod
    def process_downloads_batch(self, downloads: List[DownloadInfo]) -> List[Dict[str, Any]]:
        """Processa um lote de downloads em paralelo."""
        pass


class ITabManager(ABC):
    """Interface para gerenciamento de abas."""
    
    @abstractmethod
    def create_tab_for_url(self, url_index: int, url: str, 
                          window_id: str, window_name: str) -> Optional[TabInfo]:
        """Cria uma aba para uma URL específica."""
        pass
    
    @abstractmethod
    def inventory_attachments_for_tab(self, tab_id: str, po_number: str) -> int:
        """Faz inventário dos anexos de uma aba."""
        pass
    
    @abstractmethod
    def close_tab_and_create_new(self, url_index: int, new_url: str, 
                               new_url_index: int) -> Optional[TabInfo]:
        """Fecha uma aba e cria uma nova (FIFO)."""
        pass
    
    @abstractmethod
    def get_available_window(self) -> Optional[str]:
        """Retorna uma janela disponível."""
        pass


class IProfileVerifier(ABC):
    """Interface para verificação de perfil."""
    
    @abstractmethod
    def verify_profile_login_status(self, driver) -> bool:
        """Verifica se o perfil foi carregado corretamente."""
        pass


class IExcelReader(ABC):
    """Interface para leitura de arquivos Excel."""
    
    @abstractmethod
    def read_po_numbers(self, max_lines: Optional[int] = None) -> List[str]:
        """Lê números de PO do arquivo Excel."""
        pass
    
    @abstractmethod
    def build_coupa_urls(self, po_numbers: List[str]) -> List[str]:
        """Constrói URLs do Coupa a partir dos números de PO."""
        pass


class IUI(ABC):
    """Interface para interface de usuário."""
    
    @abstractmethod
    def render_interface(self):
        """Renderiza a interface completa."""
        pass
    
    @abstractmethod
    def update_stats(self, **kwargs):
        """Atualiza estatísticas."""
        pass
    
    @abstractmethod
    def update_tab_data(self, tab_id: str, **kwargs):
        """Atualiza dados de uma aba."""
        pass

