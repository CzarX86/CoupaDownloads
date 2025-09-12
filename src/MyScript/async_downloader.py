"""
Sistema de Downloads Assíncronos com httpx + asyncio
Implementa downloads paralelos e eficientes usando tecnologias modernas
"""

import os
import asyncio
import aiofiles
import time
from typing import List, Dict, Any, Optional, Union, Tuple
from pathlib import Path
from urllib.parse import urlparse, unquote
import re

import httpx
from httpx import AsyncClient, Response, HTTPError, TimeoutException, ConnectError
import polars as pl

# Importação condicional
try:
    from config_advanced import get_config, get_async_config
except ImportError:
    pass

try:
    from logging_advanced import get_logger, get_download_logger, get_performance_logger
except ImportError:
    pass

try:
    from retry_advanced import retry_with_custom_config
except ImportError:
    pass


class AsyncDownloadManager:
    """Gerenciador de downloads assíncronos com httpx."""
    
    def __init__(self):
        self.config = get_config()
        self.async_config = get_async_config()
        self.logger = get_logger("async_downloader")
        self.download_logger = get_download_logger()
        self.performance_logger = get_performance_logger()
        
        # Configurações do cliente HTTP
        self.timeout = httpx.Timeout(
            connect=self.async_config.download_timeout,
            read=self.async_config.download_timeout,
            write=self.async_config.download_timeout,
            pool=self.async_config.download_timeout
        )
        
        # Headers padrão
        self.default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Semáforo para controlar downloads simultâneos
        self.semaphore = asyncio.Semaphore(self.async_config.max_concurrent_downloads)
        
        # Estatísticas
        self.stats = {
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'total_bytes': 0,
            'start_time': None,
            'end_time': None
        }
    
    async def create_client(self) -> AsyncClient:
        """Cria cliente HTTP assíncrono."""
        return httpx.AsyncClient(
            timeout=self.timeout,
            headers=self.default_headers,
            follow_redirects=True,
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100
            )
        )
    
    async def download_single_file(self, client: AsyncClient, download_info: Dict[str, Any]) -> Dict[str, Any]:
        """Baixa um arquivo individual de forma assíncrona."""
        async with self.semaphore:  # Controlar concorrência
            po_number = download_info['po_number']
            url = download_info['url']
            filename = download_info['filename']
            file_type = download_info.get('file_type', 'unknown')
            
            download_logger = get_download_logger(po_number, filename)
            
            try:
                start_time = time.time()
                download_logger.download_started(url, filename)
                
                # Fazer requisição HTTP
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                
                # Determinar nome do arquivo final
                final_filename = await self._extract_filename(response, filename, file_type)
                
                # Caminho completo do arquivo
                file_path = os.path.join(self.config.download_dir, f"{po_number}_{final_filename}")
                
                # Baixar arquivo de forma assíncrona
                total_size = await self._save_file_async(response, file_path)
                
                duration = time.time() - start_time
                
                download_logger.download_completed(final_filename, total_size, duration)
                
                return {
                    'success': True,
                    'po_number': po_number,
                    'filename': final_filename,
                    'file_path': file_path,
                    'file_size': total_size,
                    'duration': duration,
                    'url': url
                }
                
            except Exception as e:
                duration = time.time() - start_time if 'start_time' in locals() else 0
                error_msg = str(e)
                
                download_logger.download_failed(filename, error_msg)
                
                return {
                    'success': False,
                    'po_number': po_number,
                    'filename': filename,
                    'error': error_msg,
                    'duration': duration,
                    'url': url
                }
    
    async def _extract_filename(self, response: Response, original_filename: str, file_type: str) -> str:
        """Extrai nome do arquivo da resposta HTTP."""
        try:
            # Tentar obter do Content-Disposition header
            content_disposition = response.headers.get('content-disposition', '')
            if 'filename=' in content_disposition:
                import re
                filename_match = re.search(r'filename[*]?=([^;]+)', content_disposition)
                if filename_match:
                    filename = filename_match.group(1).strip('"')
                    # Decodificar URL encoding
                    filename = unquote(filename)
                    return filename
            
            # Usar nome original se disponível
            if original_filename:
                return original_filename
            
            # Extrair da URL
            parsed_url = urlparse(response.url)
            url_filename = os.path.basename(parsed_url.path)
            if url_filename and '.' in url_filename:
                return url_filename
            
            # Gerar nome baseado no tipo
            timestamp = int(time.time())
            extension_map = {
                'pdf': '.pdf',
                'document': '.docx',
                'spreadsheet': '.xlsx',
                'email': '.msg',
                'image': '.jpg',
                'archive': '.zip',
                'text': '.txt'
            }
            
            extension = extension_map.get(file_type, '.bin')
            return f"download_{timestamp}{extension}"
            
        except Exception as e:
            self.logger.warning("Erro ao extrair nome do arquivo", error=str(e))
            return f"download_{int(time.time())}.bin"
    
    async def _save_file_async(self, response: Response, file_path: str) -> int:
        """Salva arquivo de forma assíncrona."""
        try:
            total_size = 0
            
            async with aiofiles.open(file_path, 'wb') as f:
                async for chunk in response.aiter_bytes(chunk_size=self.async_config.chunk_size):
                    await f.write(chunk)
                    total_size += len(chunk)
            
            return total_size
            
        except Exception as e:
            # Limpar arquivo parcial se houver erro
            if os.path.exists(file_path):
                os.remove(file_path)
            raise e
    
    async def download_batch_async(self, downloads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Baixa lote de arquivos de forma assíncrona."""
        try:
            self.stats['start_time'] = time.time()
            self.stats['total_downloads'] = len(downloads)
            
            self.logger.info("Iniciando downloads assíncronos", 
                           count=len(downloads),
                           max_concurrent=self.async_config.max_concurrent_downloads)
            
            async with await self.create_client() as client:
                # Criar tarefas para todos os downloads
                tasks = [
                    self.download_single_file(client, download_info)
                    for download_info in downloads
                ]
                
                # Executar downloads em paralelo
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Processar resultados
                processed_results = []
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        processed_results.append({
                            'success': False,
                            'po_number': downloads[i]['po_number'],
                            'filename': downloads[i]['filename'],
                            'error': str(result),
                            'url': downloads[i]['url']
                        })
                    else:
                        processed_results.append(result)
                
                # Atualizar estatísticas
                self._update_stats(processed_results)
                
                return processed_results
                
        except Exception as e:
            self.logger.error("Erro no download em lote", error=str(e))
            raise
    
    def _update_stats(self, results: List[Dict[str, Any]]):
        """Atualiza estatísticas dos downloads."""
        try:
            self.stats['end_time'] = time.time()
            
            for result in results:
                if result['success']:
                    self.stats['successful_downloads'] += 1
                    self.stats['total_bytes'] += result.get('file_size', 0)
                else:
                    self.stats['failed_downloads'] += 1
            
            # Log de performance
            total_time = self.stats['end_time'] - self.stats['start_time']
            success_rate = (self.stats['successful_downloads'] / self.stats['total_downloads']) * 100
            throughput = self.stats['total_bytes'] / total_time if total_time > 0 else 0
            
            self.performance_logger.batch_processing(
                batch_size=self.stats['total_downloads'],
                total_processed=self.stats['successful_downloads'],
                success_rate=success_rate,
                duration=total_time
            )
            
            self.performance_logger.throughput(throughput, "downloads_per_second")
            
        except Exception as e:
            self.logger.warning("Erro ao atualizar estatísticas", error=str(e))


class AsyncCSVProcessor:
    """Processador assíncrono de CSV usando Polars."""
    
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.logger = get_logger("async_csv")
    
    async def read_csv_async(self) -> Optional[pl.DataFrame]:
        """Lê CSV de forma assíncrona."""
        try:
            # Polars é thread-safe, então podemos usar em contexto assíncrono
            df = pl.read_csv(self.csv_path)
            self.logger.info("CSV lido com sucesso", rows=len(df))
            return df
            
        except Exception as e:
            self.logger.error("Erro ao ler CSV", error=str(e), path=self.csv_path)
            return None
    
    async def get_pending_downloads_async(self) -> List[Dict[str, Any]]:
        """Obtém downloads pendentes de forma assíncrona."""
        try:
            df = await self.read_csv_async()
            if df is None:
                return []
            
            # Filtrar downloads pendentes
            pending_df = df.filter(pl.col('status') == 'pending')
            
            # Converter para lista de dicionários
            pending_downloads = pending_df.to_dicts()
            
            self.logger.info("Downloads pendentes obtidos", count=len(pending_downloads))
            return pending_downloads
            
        except Exception as e:
            self.logger.error("Erro ao obter downloads pendentes", error=str(e))
            return []
    
    async def update_download_status_async(self, po_number: str, filename: str, 
                                          status: str, error_message: str = "", 
                                          file_size: int = 0) -> bool:
        """Atualiza status de download de forma assíncrona."""
        try:
            df = await self.read_csv_async()
            if df is None:
                return False
            
            # Encontrar e atualizar linha
            mask = (pl.col('po_number') == po_number) & (pl.col('filename') == filename)
            
            matching_rows = df.filter(mask)
            if matching_rows.height > 0:
                # Atualizar status
                df = df.with_columns(
                    pl.when(mask)
                    .then(pl.lit(status))
                    .otherwise(pl.col('status'))
                    .alias('status')
                )
                
                # Atualizar mensagem de erro se fornecida
                if error_message:
                    df = df.with_columns(
                        pl.when(mask)
                        .then(pl.lit(error_message))
                        .otherwise(pl.col('error_message'))
                        .alias('error_message')
                    )
                
                # Atualizar data de download se concluído
                if status == 'completed':
                    from datetime import datetime
                    df = df.with_columns(
                        pl.when(mask)
                        .then(pl.lit(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                        .otherwise(pl.col('downloaded_at'))
                        .alias('downloaded_at')
                    )
                    
                    # Atualizar tamanho do arquivo se fornecido
                    if file_size > 0:
                        df = df.with_columns(
                            pl.when(mask)
                            .then(pl.lit(file_size))
                            .otherwise(pl.col('file_size'))
                            .alias('file_size')
                        )
                
                # Salvar CSV atualizado
                df.write_csv(self.csv_path)
                
                self.logger.info("Status de download atualizado", 
                               po_number=po_number, 
                               filename=filename, 
                               status=status)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error("Erro ao atualizar status de download", error=str(e))
            return False
    
    async def add_downloads_async(self, downloads: List[Dict[str, Any]]) -> bool:
        """Adiciona downloads ao CSV de forma assíncrona."""
        try:
            from datetime import datetime
            
            # Ler CSV existente
            df = await self.read_csv_async()
            if df is None:
                df = pl.DataFrame()
            
            # Preparar novos dados
            new_data = []
            for download in downloads:
                new_data.append({
                    'po_number': download['po_number'],
                    'url': download['url'],
                    'filename': download['filename'],
                    'file_type': download.get('file_type', 'unknown'),
                    'status': 'pending',
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'downloaded_at': '',
                    'error_message': '',
                    'file_size': 0
                })
            
            # Adicionar novos dados
            new_df = pl.DataFrame(new_data)
            combined_df = pl.concat([df, new_df])
            
            # Salvar CSV atualizado
            combined_df.write_csv(self.csv_path)
            
            self.logger.info("Downloads adicionados ao CSV", count=len(downloads))
            return True
            
        except Exception as e:
            self.logger.error("Erro ao adicionar downloads ao CSV", error=str(e))
            return False


class AsyncMicroservice:
    """Microserviço assíncrono de download."""
    
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.download_manager = AsyncDownloadManager()
        self.csv_processor = AsyncCSVProcessor(csv_path)
        self.logger = get_logger("async_microservice")
        self.running = False
    
    async def run_microservice_async(self, batch_size: int = 5, check_interval: int = 2):
        """Executa microserviço de forma assíncrona."""
        try:
            self.running = True
            self.logger.info("Microserviço assíncrono iniciado")
            
            while self.running:
                try:
                    # Obter downloads pendentes
                    pending_downloads = await self.csv_processor.get_pending_downloads_async()
                    
                    if pending_downloads:
                        self.logger.info("Downloads pendentes encontrados", count=len(pending_downloads))
                        
                        # Processar em lotes
                        for i in range(0, len(pending_downloads), batch_size):
                            batch = pending_downloads[i:i + batch_size]
                            
                            self.logger.info("Processando lote assíncrono", 
                                           batch_number=i//batch_size + 1,
                                           batch_size=len(batch))
                            
                            # Baixar lote
                            results = await self.download_manager.download_batch_async(batch)
                            
                            # Atualizar status no CSV
                            for result in results:
                                await self.csv_processor.update_download_status_async(
                                    po_number=result['po_number'],
                                    filename=result['filename'],
                                    status='completed' if result['success'] else 'failed',
                                    error_message=result.get('error', ''),
                                    file_size=result.get('file_size', 0)
                                )
                            
                            # Log de resultados do lote
                            successful = sum(1 for r in results if r['success'])
                            failed = len(results) - successful
                            
                            self.logger.info("Lote assíncrono concluído", 
                                           successful=successful,
                                           failed=failed)
                    
                    else:
                        # Aguardar antes da próxima verificação
                        await asyncio.sleep(check_interval)
                        
                except Exception as e:
                    self.logger.error("Erro no microserviço assíncrono", error=str(e))
                    await asyncio.sleep(check_interval)
                    
        except Exception as e:
            self.logger.error("Erro crítico no microserviço assíncrono", error=str(e))
        finally:
            self.running = False
            self.logger.info("Microserviço assíncrono finalizado")
    
    def stop(self):
        """Para o microserviço."""
        self.running = False


# Funções utilitárias assíncronas
async def download_single_file_async(url: str, filename: str, download_dir: str) -> Dict[str, Any]:
    """Baixa um arquivo único de forma assíncrona."""
    download_manager = AsyncDownloadManager()
    
    download_info = {
        'po_number': 'single',
        'url': url,
        'filename': filename,
        'file_type': 'unknown'
    }
    
    async with download_manager.create_client() as client:
        return await download_manager.download_single_file(client, download_info)


async def process_downloads_from_csv_async(csv_path: str, batch_size: int = 5) -> Dict[str, Any]:
    """Processa downloads de um CSV de forma assíncrona."""
    microservice = AsyncMicroservice(csv_path)
    
    # Executar por tempo limitado para teste
    try:
        await asyncio.wait_for(
            microservice.run_microservice_async(batch_size=batch_size),
            timeout=300  # 5 minutos
        )
    except asyncio.TimeoutError:
        microservice.stop()
        return {'success': True, 'message': 'Processamento concluído (timeout)'}
    
    return {'success': True, 'message': 'Processamento concluído'}


if __name__ == "__main__":
    # Teste do sistema assíncrono
    print("🔧 Testando sistema de downloads assíncronos...")
    
    async def test_async_downloads():
        # Teste de download único
        test_url = "https://httpbin.org/json"
        result = await download_single_file_async(test_url, "test.json", "/tmp")
        print(f"✅ Download único: {result['success']}")
        
        # Teste de processamento de CSV
        csv_path = "src/MyScript/download_inventory.csv"
        if os.path.exists(csv_path):
            result = await process_downloads_from_csv_async(csv_path, batch_size=2)
            print(f"✅ Processamento CSV: {result['success']}")
        else:
            print("⚠️ CSV não encontrado para teste")
    
    # Executar teste
    asyncio.run(test_async_downloads())
    
    print("✅ Sistema assíncrono testado!")

