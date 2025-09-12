"""
Módulo de Serviços - Implementa a lógica de negócio
Aplica Service Layer Pattern e Single Responsibility Principle
"""

import os
import time
import threading
import pandas as pd
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import re

from ui_component_interfaces import (
    IInventoryManager, IDownloadService, IExcelReader, IProfileVerifier,
    DownloadInfo, TabInfo
)
from config import config_manager


class InventoryService(IInventoryManager):
    """
    Serviço de inventário - responsável por gerenciar o CSV de controle
    Single Responsibility: apenas operações com CSV
    """
    
    def __init__(self, csv_path: str = None):
        self.csv_path = csv_path or config_manager.system.csv_path
        self.lock = threading.Lock()
        self._initialize_csv()
    
    def _initialize_csv(self):
        """Inicializa o arquivo CSV de controle."""
        # Garantir que o diretório do CSV exista
        csv_dir = os.path.dirname(self.csv_path) or "."
        try:
            os.makedirs(csv_dir, exist_ok=True)
        except Exception as e:
            print(f"⚠️ Não foi possível criar diretório do CSV '{csv_dir}': {e}")
        
        if not os.path.exists(self.csv_path):
            df = pd.DataFrame(columns=[
                'po_number', 'url', 'filename', 'file_type', 'status', 
                'created_at', 'downloaded_at', 'error_message', 'file_size'
            ])
            df.to_csv(self.csv_path, index=False)
            print(f"✅ CSV de controle criado: {self.csv_path}")
    
    def add_download_url(self, download_info: DownloadInfo) -> bool:
        """Adiciona uma URL de download ao inventário."""
        with self.lock:
            try:
                df = pd.read_csv(self.csv_path)
                
                new_row = {
                    'po_number': download_info.po_number,
                    'url': download_info.url,
                    'filename': download_info.filename,
                    'file_type': download_info.file_type,
                    'status': download_info.status,
                    'created_at': download_info.created_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'downloaded_at': download_info.downloaded_at,
                    'error_message': download_info.error_message,
                    'file_size': download_info.file_size
                }
                
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_csv(self.csv_path, index=False)
                
                print(f"📝 URL adicionada ao inventário: {download_info.filename}")
                return True
                
            except Exception as e:
                print(f"❌ Erro ao adicionar URL ao inventário: {e}")
                return False
    
    def get_pending_downloads(self) -> List[DownloadInfo]:
        """Retorna lista de downloads pendentes."""
        try:
            df = pd.read_csv(self.csv_path)
            pending_df = df[df['status'] == 'pending']
            
            downloads = []
            for _, row in pending_df.iterrows():
                download_info = DownloadInfo(
                    po_number=row['po_number'],
                    url=row['url'],
                    filename=row['filename'],
                    file_type=row.get('file_type', 'unknown'),
                    status=row['status'],
                    created_at=row.get('created_at', ''),
                    downloaded_at=row.get('downloaded_at', ''),
                    error_message=row.get('error_message', ''),
                    file_size=row.get('file_size', 0)
                )
                downloads.append(download_info)
            
            return downloads
            
        except Exception as e:
            print(f"❌ Erro ao ler downloads pendentes: {e}")
            return []
    
    def update_download_status(self, po_number: str, filename: str, 
                             status: str, error_message: str = "") -> bool:
        """Atualiza o status de um download."""
        with self.lock:
            try:
                df = pd.read_csv(self.csv_path)
                
                mask = (df['po_number'] == po_number) & (df['filename'] == filename)
                if mask.any():
                    df.loc[mask, 'status'] = status
                    if error_message:
                        df.loc[mask, 'error_message'] = error_message
                    if status == 'completed':
                        df.loc[mask, 'downloaded_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        df['downloaded_at'] = df['downloaded_at'].astype(str)
                    
                    df.to_csv(self.csv_path, index=False)
                    return True
                return False
                
            except Exception as e:
                print(f"❌ Erro ao atualizar status: {e}")
                return False


class DownloadService(IDownloadService):
    """
    Serviço de download - responsável apenas por downloads HTTP
    Single Responsibility: apenas operações de download
    """
    
    def __init__(self, download_dir: str = None, max_workers: int = None):
        self.download_dir = download_dir or config_manager.download.download_dir
        self.max_workers = max_workers or config_manager.download.max_workers
        self.timeout = config_manager.download.timeout
        self.chunk_size = config_manager.download.chunk_size
        
        # Criar diretório se não existir
        os.makedirs(self.download_dir, exist_ok=True)
        
        # Configurar sessão HTTP
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59'
        })
    
    def download_file(self, download_info: DownloadInfo) -> Dict[str, Any]:
        """Baixa um arquivo individual."""
        thread_name = threading.current_thread().name
        
        try:
            print(f"📥 [{thread_name}] Iniciando download: {download_info.filename}")
            
            # Fazer requisição HTTP
            response = self.session.get(
                download_info.url, 
                stream=True, 
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Determinar nome do arquivo final
            filename = self._extract_filename(response, download_info)
            
            # Caminho completo do arquivo
            file_path = os.path.join(self.download_dir, f"{download_info.po_number}_{filename}")
            
            # Baixar arquivo
            total_size = 0
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)
            
            print(f"✅ [{thread_name}] Download concluído: {filename} ({total_size} bytes)")
            return {
                'success': True,
                'filename': filename,
                'file_path': file_path,
                'file_size': total_size,
                'po_number': download_info.po_number
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ [{thread_name}] Erro no download de {download_info.filename}: {error_msg}")
            
            return {
                'success': False,
                'filename': download_info.filename,
                'error': error_msg,
                'po_number': download_info.po_number
            }
    
    def _extract_filename(self, response, download_info: DownloadInfo) -> str:
        """Extrai o nome do arquivo da resposta HTTP."""
        filename = download_info.filename
        
        # Tentar extrair do header Content-Disposition
        content_disposition = response.headers.get('content-disposition', '')
        if 'filename=' in content_disposition:
            filename_match = re.search(r'filename[*]?=([^;]+)', content_disposition)
            if filename_match:
                filename = filename_match.group(1).strip('"')
        
        # Adicionar extensão se não tiver
        if not any(filename.lower().endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.msg']):
            if download_info.file_type == 'pdf':
                filename += '.pdf'
            elif download_info.file_type == 'document':
                filename += '.docx'
            elif download_info.file_type == 'spreadsheet':
                filename += '.xlsx'
            elif download_info.file_type == 'email':
                filename += '.msg'
        
        return filename
    
    def process_downloads_batch(self, downloads: List[DownloadInfo]) -> List[Dict[str, Any]]:
        """Processa um lote de downloads em paralelo."""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submeter downloads
            future_to_download = {
                executor.submit(self.download_file, download_info): download_info
                for download_info in downloads
            }
            
            # Coletar resultados
            for future in as_completed(future_to_download):
                download_info = future_to_download[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"❌ Exceção no download: {e}")
                    results.append({
                        'success': False,
                        'filename': download_info.filename,
                        'error': str(e),
                        'po_number': download_info.po_number
                    })
        
        return results


class ExcelReaderService(IExcelReader):
    """
    Serviço de leitura de Excel - responsável apenas por operações com Excel
    Single Responsibility: apenas leitura de arquivos Excel
    """
    
    def __init__(self, excel_path: str = None):
        self.excel_path = excel_path or config_manager.system.excel_path
        self.base_url = config_manager.system.base_url
    
    def read_po_numbers(self, max_lines: Optional[int] = None) -> List[str]:
        """Lê números de PO de planilha (CSV ou Excel)."""
        try:
            # Verificar se arquivo existe
            if not os.path.exists(self.excel_path):
                print(f"❌ Arquivo não encontrado: {self.excel_path}")
                return []

            _, ext = os.path.splitext(self.excel_path.lower())
            if ext == ".csv":
                # Robust CSV read with BOM + delimiter auto
                try:
                    df = pd.read_csv(self.excel_path, sep=None, engine='python', encoding='utf-8-sig')
                except Exception:
                    df = pd.read_csv(self.excel_path, sep=None, engine='python')
            else:
                # Ler arquivo Excel na aba padrão
                df = pd.read_excel(self.excel_path, sheet_name='PO_Data', engine='openpyxl')
            
            # Extrair números de PO da coluna 'PO_NUMBER'
            po_numbers = df['PO_NUMBER'].dropna().astype(str).tolist()
            
            # Aplicar limite de linhas se especificado
            if max_lines and max_lines > 0:
                po_numbers = po_numbers[:max_lines]
                print(f"📊 Processando apenas as primeiras {max_lines} linhas do Excel")
            
            print(f"📊 Encontrados {len(po_numbers)} números de PO na planilha")
            return po_numbers
            
        except Exception as e:
            print(f"❌ Erro ao ler planilha: {e}")
            return []
    
    def build_coupa_urls(self, po_numbers: List[str]) -> List[str]:
        """Constrói URLs do Coupa a partir dos números de PO."""
        coupa_urls = []
        
        for po_number in po_numbers:
            # Limpar número de PO (remover prefixos como PO, PM, etc.)
            clean_po = po_number.replace("PO", "").replace("PM", "").strip()
            coupa_url = f"{self.base_url}/order_headers/{clean_po}"
            coupa_urls.append(coupa_url)
        
        return coupa_urls


class ProfileVerificationService(IProfileVerifier):
    """
    Serviço de verificação de perfil - responsável apenas por verificar perfil
    Single Responsibility: apenas verificação de perfil Edge
    """
    
    def __init__(self):
        self.config = config_manager.edge_profile
    
    def verify_profile_login_status(self, driver) -> bool:
        """
        🛡️ FUNÇÃO CRÍTICA - NÃO ALTERAR SEM AUTORIZAÇÃO EXPLÍCITA DO USUÁRIO 🛡️
        
        Esta função verifica se o perfil do Edge foi carregado corretamente
        e se o usuário está logado no Coupa. É ESSENCIAL para o funcionamento.
        
        ⚠️  ATENÇÃO: Qualquer alteração nesta função pode quebrar a detecção de perfil
        ⚠️  Se você precisa modificar algo aqui, CONSULTE O USUÁRIO PRIMEIRO
        """
        try:
            # Tentar acessar uma página que requer login para verificar se o perfil está funcionando
            driver.get(self.config.login_check_url)
            time.sleep(self.config.login_check_timeout)  # Aguardar carregamento
            
            # Verificar se há elementos de login (indicando que não estamos logados)
            login_elements = []
            for selector in self.config.login_selectors:
                login_elements.extend(driver.find_elements("css selector", selector))
            
            if login_elements:
                print("⚠️ Perfil carregado mas usuário não está logado no Coupa")
                print("   Será necessário fazer login manualmente se necessário")
                return False
            else:
                print("✅ Perfil carregado e usuário está logado no Coupa!")
                return True
                
        except Exception as e:
            print(f"⚠️ Não foi possível verificar status do login: {e}")
            print("   Continuando com o processamento...")
            return False
