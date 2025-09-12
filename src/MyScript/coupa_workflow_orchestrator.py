"""
Sistema Integrado Avançado - Combina todas as melhorias
Integra todas as bibliotecas implementadas em um sistema coeso e robusto
"""

import os #essa lib serve para criar diretórios e arquivos
import asyncio # função: rodar o sistema de forma assíncrona
import time # função: medir o tempo de execução do sistema
from typing import List, Dict, Any, Optional, Union, Tuple #função: tipar as variáveis
from pathlib import Path # função: manipular caminhos de arquivos
from datetime import datetime # função: manipular datas e horas

# Importações condicionais para funcionar tanto como módulo quanto como script
try:
    from config_advanced import get_config, get_playwright_config, get_async_config, get_logging_config
    from logging_advanced import get_logger, get_inventory_logger, get_download_logger, get_performance_logger
    from retry_advanced import retry_with_custom_config, RobustCSVManager, RobustElementFinder
    from polars_processor import PolarsDataProcessor, PolarsExcelProcessor
    from async_downloader import AsyncDownloadManager, AsyncCSVProcessor, AsyncMicroservice
    from playwright_system import PlaywrightInventorySystem
    # NOVO: Importação do progress tracker avançado
    from execution_progress_tracker import IntelligentProgressTracker
    from selenium_beautifulsoup_processor import HybridProcessor
except ImportError:
    from config_advanced import get_config, get_playwright_config, get_async_config, get_logging_config
    from logging_advanced import get_logger, get_inventory_logger, get_download_logger, get_performance_logger
    from retry_advanced import retry_with_custom_config, RobustCSVManager, RobustElementFinder
    from polars_processor import PolarsDataProcessor, PolarsExcelProcessor
    from async_downloader import AsyncDownloadManager, AsyncCSVProcessor, AsyncMicroservice
    from playwright_system import PlaywrightInventorySystem
    from selenium_beautifulsoup_processor import HybridProcessor


class AdvancedCoupaSystem:
    """Sistema avançado que integra todas as melhorias."""
    
    def __init__(self, ui_config=None):
        self.config = get_config()
        self.playwright_config = get_playwright_config()
        self.async_config = get_async_config()
        self.logging_config = get_logging_config()
        
        # Loggers especializados (inicializar primeiro)
        self.logger = get_logger("advanced_system")
        self.inventory_logger = get_inventory_logger()
        self.download_logger = get_download_logger()
        self.performance_logger = get_performance_logger()
        
        # CORREÇÃO: Usar configurações da UI se fornecidas
        if ui_config:
            # Pydantic v2: usar model_copy com update para atualizar configurações
            self.config = self.config.model_copy(update=ui_config)
            self.logger.info("Configurações da UI aplicadas ao sistema avançado")
        
        # Processadores de dados
        self.csv_processor = PolarsDataProcessor(self.config.csv_path)
        self.excel_processor = PolarsExcelProcessor(self.config.excel_path)
        
        # Sistemas de automação
        self.playwright_system: Optional[PlaywrightInventorySystem] = None
        self.hybrid_processor: Optional[HybridProcessor] = None
        
        # Sistema de downloads
        self.async_downloader = AsyncDownloadManager()
        self.async_microservice: Optional[AsyncMicroservice] = None
        
        # NOVO: Progress tracker avançado
        self.progress_tracker = IntelligentProgressTracker("coupa_system")
        
        # Estatísticas
        self.stats = {
            'inventory_start_time': None,
            'inventory_end_time': None,
            'download_start_time': None,
            'download_end_time': None,
            'total_pos_processed': 0,
            'total_attachments_found': 0,
            'total_downloads_completed': 0,
            'total_errors': 0
        }
    
    async def initialize_system(self) -> bool:
        """Inicializa todos os componentes do sistema."""
        try:
            self.logger.info("Inicializando sistema avançado")
            
            # Validar configurações
            if not self._validate_configurations():
                return False
            
            # Criar diretórios necessários
            self._create_directories()
            
            # Inicializar sistema de inventário (Playwright)
            if self.config.profile_mode != "none":
                self.playwright_system = PlaywrightInventorySystem()
                if not await self.playwright_system.initialize():
                    self.logger.warning("Falha ao inicializar Playwright, usando modo híbrido")
                    self.playwright_system = None
                else:
                    # CORREÇÃO: Validar se perfil foi carregado corretamente
                    profile_validation = await self._validate_edge_profile()
                    if not profile_validation:
                        self.logger.warning("Perfil Edge pode não ter sido carregado corretamente")
                    else:
                        self.logger.info("Perfil Edge validado com sucesso")
                    
                    # TODO: Implementar validação real de múltiplas janelas
                    await self._validate_multi_window_support()
            
            # Inicializar sistema de downloads assíncronos
            self.async_microservice = AsyncMicroservice(self.config.csv_path)
            
            self.logger.info("Sistema avançado inicializado com sucesso")
            return True
            
        except Exception as e:
            self.logger.error("Erro ao inicializar sistema avançado", error=str(e))
            return False
    
    async def _validate_edge_profile(self) -> bool:
        """Valida se o perfil Edge foi carregado corretamente."""
        try:
            if not self.playwright_system or not self.playwright_system.playwright_manager:
                return False
            
            # Usar o método de validação do PlaywrightManager
            return await self.playwright_system.playwright_manager._validate_profile_loaded()
            
        except Exception as e:
            self.logger.error("Erro na validação de perfil Edge", error=str(e))
            return False
    
    async def _validate_multi_window_support(self) -> None:
        """Valida se o sistema suporta múltiplas janelas."""
        try:
            if self.config.num_windows > 1:
                self.logger.info("Configurado para múltiplas janelas", 
                               num_windows=self.config.num_windows,
                               max_tabs_per_window=self.config.max_tabs_per_window)
                
                # Implementação: criar múltiplas páginas (abas) em paralelo
                # e validar que conseguem inicializar e executar JS básico.
                if not self.playwright_system or not self.playwright_system.playwright_manager:
                    self.logger.warning("Playwright não inicializado para validação de múltiplas janelas")
                    return

                total_tabs = max(1, int(self.config.num_windows) * int(self.config.max_tabs_per_window))
                pm = self.playwright_system.playwright_manager

                # Criar páginas
                pages = await pm.create_multiple_pages(total_tabs)
                created = len(pages)
                if created == 0:
                    self.logger.warning("Falha ao criar páginas para validação de múltiplas janelas")
                    return

                # Validar navegação leve e execução de JS
                async def _probe(page):
                    try:
                        await page.goto("about:blank")
                        val = await page.evaluate("() => 42")
                        return val == 42
                    except Exception:
                        return False

                results = await asyncio.gather(*[_probe(p) for p in pages], return_exceptions=False)
                success_count = sum(1 for ok in results if ok)

                # Fechar somente as páginas criadas para o teste
                for p in pages:
                    try:
                        await pm.close_page(p)
                    except Exception:
                        pass

                if success_count == total_tabs:
                    self.logger.info("Validação de múltiplas janelas bem-sucedida",
                                     requested_tabs=total_tabs,
                                     created_tabs=created,
                                     validated_tabs=success_count)
                else:
                    self.logger.warning("Validação parcial de múltiplas janelas",
                                        requested_tabs=total_tabs,
                                        created_tabs=created,
                                        validated_tabs=success_count)
            else:
                self.logger.info("Configurado para janela única")
                
        except Exception as e:
            self.logger.error("Erro na validação de múltiplas janelas", error=str(e))
    
    def _validate_configurations(self) -> bool:
        """Valida todas as configurações."""
        try:
            # Validar arquivo de POs (CSV/Excel)
            if not os.path.exists(self.config.excel_path):
                self.logger.error("Arquivo de POs não encontrado", path=self.config.excel_path)
                return False
            
            # Validar diretório de download
            if not os.path.exists(self.config.download_dir):
                self.logger.warning("Diretório de download não existe, será criado", 
                                 path=self.config.download_dir)
            
            # Validar configurações de performance
            if self.config.max_workers < 1 or self.config.max_workers > 20:
                self.logger.error("Número de workers inválido", workers=self.config.max_workers)
                return False
            
            self.logger.info("Configurações validadas com sucesso")
            return True
            
        except Exception as e:
            self.logger.error("Erro na validação de configurações", error=str(e))
            return False
    
    def _create_directories(self):
        """Cria diretórios necessários."""
        try:
            directories = [
                self.config.download_dir,
                os.path.dirname(self.config.csv_path)
            ]
            
            for directory in directories:
                os.makedirs(directory, exist_ok=True)
                self.logger.debug("Diretório criado/verificado", path=directory)
                
        except Exception as e:
            self.logger.warning("Erro ao criar diretórios", error=str(e))
    
    async def run_inventory_phase(self, stop_event=None) -> bool:
        """Executa fase de inventário com progress tracking avançado."""
        try:
            self.stats['inventory_start_time'] = time.time()
            self.logger.info("Iniciando fase de inventário")
            
            # Informar caminho e tipo da planilha (CSV/Excel) que será processada
            _, ext = os.path.splitext(self.config.excel_path.lower())
            kind = "CSV" if ext == ".csv" else "Excel"
            self.logger.info("Processando planilha de POs", path=self.config.excel_path, kind=kind)

            # Ler números de PO da planilha (CSV/Excel)
            po_numbers = self.excel_processor.get_po_numbers(self.config.max_lines)
            if not po_numbers:
                self.logger.error("Nenhum número de PO encontrado na planilha")
                return False
            
            # NOVO: Configurar progress tracker
            self.progress_tracker.start_operation(len(po_numbers))
            self.logger.info("Progress tracker configurado", total_items=len(po_numbers))
            
            # Verificar stop_event antes de processar
            if stop_event and stop_event.is_set():
                self.logger.info("Sistema parado antes do processamento de URLs")
                return False
            
            # Construir URLs
            urls = []
            for po_number in po_numbers:
                clean_po = po_number.replace("PO", "").replace("PM", "").strip()
                url = f"{self.config.base_url}/order_headers/{clean_po}"
                urls.append((url, po_number))
            
            self.logger.info("URLs construídas", count=len(urls))
            
            # Verificar stop_event antes de processar URLs
            if stop_event and stop_event.is_set():
                self.logger.info("Sistema parado antes do processamento de URLs")
                return False
            
            # Processar URLs usando sistema Playwright (sem fallback híbrido)
            if not self.playwright_system:
                raise SystemError("Sistema Playwright não inicializado")
            
            results = await self._process_urls_playwright(urls, stop_event)
            
            # Se não houve resultados, tentar fallback de login manual
            if not results:
                self.logger.warning("Nenhum resultado do Playwright - tentando fallback de login manual")
                if await self.playwright_system.fallback_to_manual_login():
                    self.logger.info("Fallback de login manual bem-sucedido - reprocessando URLs")
                    results = await self._process_urls_playwright(urls, stop_event)
                
                if not results:
                    raise SystemError("Falha no sistema Playwright e fallback de login manual")
            
            # Processar resultados e salvar no CSV
            await self._process_inventory_results(results)
            
            # NOVO: Atualizar progress tracker com métricas inteligentes
            for result in results:
                if result.get('success'):
                    item_time = time.time() - self.stats['inventory_start_time']
                    self.progress_tracker.update_progress(1, item_duration=item_time)
            
            self.stats['inventory_end_time'] = time.time()
            self.stats['total_pos_processed'] = len(results)
            
            # NOVO: Obter estimativas inteligentes
            remaining_time = self.progress_tracker.get_remaining_time_estimate()
            throughput = self.progress_tracker.get_current_throughput()
            
            # Log de performance
            duration = self.stats['inventory_end_time'] - self.stats['inventory_start_time']
            self.performance_logger.timing("inventory_phase", duration, 
                                         pos_processed=len(results),
                                         attachments_found=self.stats['total_attachments_found'],
                                         estimated_remaining_time=remaining_time,
                                         current_throughput=throughput)
            
            self.logger.info("Fase de inventário concluída", 
                           duration=duration,
                           pos_processed=len(results),
                           attachments_found=self.stats['total_attachments_found'],
                           estimated_remaining_time=remaining_time,
                           current_throughput=throughput)
            
            return True
            
        except Exception as e:
            self.logger.error("Erro na fase de inventário", error=str(e))
            return False
    
    async def _process_urls_playwright(self, urls: List[Tuple[str, str]], stop_event=None) -> List[Dict[str, Any]]:
        """Processa URLs usando Playwright."""
        try:
            # Criar workers
            if not await self.playwright_system.create_workers(self.config.max_workers):
                return []
            
            # Processar URLs em lotes
            batch_size = self.config.max_workers * 2
            all_results = []
            
            for i in range(0, len(urls), batch_size):
                batch = urls[i:i + batch_size]
                batch_results = await self.playwright_system.process_urls_batch(batch)
                all_results.extend(batch_results)
                
                # NOVO: Salvar resultados de cada lote no CSV imediatamente
                if batch_results:
                    self.logger.info(f"🔍 DEBUG: Salvando lote de {len(batch_results)} resultados no CSV")
                    await self._process_inventory_results(batch_results)
                    self.logger.info(f"🔍 DEBUG: Lote salvo no CSV com sucesso")
                
                # Log de progresso
                progress = (i + len(batch)) / len(urls) * 100
                self.logger.info("Progresso do inventário", 
                               progress=f"{progress:.1f}%",
                               processed=i + len(batch),
                               total=len(urls))
            
            return all_results
            
        except Exception as e:
            self.logger.error("Erro ao processar URLs com Playwright", error=str(e))
            return []
    
    async def _process_urls_hybrid(self, urls: List[Tuple[str, str]], stop_event=None) -> List[Dict[str, Any]]:
        """Processa URLs usando sistema híbrido (fallback com inventory_system)."""
        try:
            self.logger.info("Usando sistema híbrido com inventory_system")
            
            # Importar o sistema de inventário existente
            from coupa_inventory_collector import manage_inventory_system
            
            # CORREÇÃO: Usar configurações da UI ao invés das configurações padrão
            # O sistema avançado deve receber as configurações da UI
            config = {
                'excel_path': self.config.excel_path,
                'csv_path': self.config.csv_path,
                'download_dir': self.config.download_dir,
                'num_windows': self.config.num_windows,  # Deve vir da UI
                'max_tabs_per_window': self.config.max_tabs_per_window,  # Deve vir da UI
                'max_workers': self.config.max_workers,  # Deve vir da UI
                'headless': self.config.headless,
                'profile_mode': self.config.profile_mode,
                'max_lines': self.config.max_lines
            }
            
            # Log das configurações para debug
            self.logger.info("Configurações do sistema híbrido", 
                           num_windows=config['num_windows'],
                           max_tabs_per_window=config['max_tabs_per_window'],
                           max_workers=config['max_workers'])
            
            # Verificar stop_event antes de executar
            if stop_event and stop_event.is_set():
                self.logger.info("Sistema parado antes da execução híbrida")
                return []
            
            # Executar sistema de inventário com stop_event
            manage_inventory_system(config, stop_event=stop_event)
            
            # Ler resultados do CSV
            import pandas as pd
            try:
                df = pd.read_csv(self.config.csv_path)
                results = []
                
                for _, row in df.iterrows():
                    if row['status'] == 'pending':
                        result = {
                            'success': True,
                            'po_number': row['po_number'],
                            'url': row['url'],
                            'attachments': [{
                                'filename': row['filename'],
                                'url': row['url'],
                                'file_type': row['file_type']
                            }]
                        }
                        results.append(result)
                
                self.logger.info(f"Sistema híbrido processou {len(results)} resultados")
                return results
                
            except Exception as e:
                self.logger.error(f"Erro ao ler CSV: {e}")
                return []
            
        except Exception as e:
            self.logger.error("Erro ao processar URLs com sistema híbrido", error=str(e))
            return []
    
    async def _process_inventory_results(self, results: List[Dict[str, Any]]):
        """Processa resultados do inventário e salva no CSV."""
        try:
            self.logger.info(f"🔍 DEBUG: Iniciando processamento de {len(results)} resultados")
            all_attachments = []
            
            for i, result in enumerate(results):
                self.logger.debug(f"🔍 DEBUG: Processando resultado {i+1}/{len(results)}: {result.get('po_number', 'Unknown')}")
                
                if result['success']:
                    attachments = result.get('attachments', [])
                    all_attachments.extend(attachments)
                    
                    # Log de attachments encontrados
                    po_number = result['po_number']
                    count = len(attachments)
                    self.inventory_logger.attachments_found(po_number, count)
                    
                    # Fallback: registrar PO mesmo sem anexos
                    if count == 0:
                        placeholder = {
                            'po_number': po_number,
                            'url': result.get('url', ''),
                            'filename': 'NO_ATTACHMENTS',
                            'file_type': 'unknown',
                            'status': 'no_attachments',
                            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'downloaded_at': '',
                            'error_message': '',
                            'file_size': 0,
                            'window_id': '',
                            'tab_id': ''
                        }
                        all_attachments.append(placeholder)
                        self.logger.debug(f"🔍 DEBUG: PO sem anexos registrada: {po_number}")
                    
                    # Log individual de cada attachment
                    for attachment in attachments:
                        self.inventory_logger.attachment_inventoried(
                            po_number, 
                            attachment['filename'], 
                            attachment['file_type']
                        )
                else:
                    self.stats['total_errors'] += 1
                    self.logger.warning("PO não processada", 
                                      po_number=result.get('po_number'),
                                      error=result.get('error'))
            
            self.logger.info(f"🔍 DEBUG: Total de attachments coletados: {len(all_attachments)}")
            
            # Salvar resultados no CSV (inclui placeholders quando não há anexos)
            if all_attachments:
                self.logger.info(f"🔍 DEBUG: Tentando salvar {len(all_attachments)} attachments no CSV")
                success = self.csv_processor.add_multiple_records(all_attachments)
                if success:
                    self.stats['total_attachments_found'] = len(all_attachments)
                    self.inventory_logger.csv_updated(self.config.csv_path, len(all_attachments))
                    self.logger.info(f"🔍 DEBUG: CSV salvo com sucesso! {len(all_attachments)} registros adicionados")
                else:
                    self.logger.error("🔍 DEBUG: Falha ao salvar attachments no CSV")
            else:
                self.logger.warning(f"🔍 DEBUG: Nenhum attachment para salvar no CSV")
            
        except Exception as e:
            self.logger.error("Erro ao processar resultados do inventário", error=str(e))
    
    async def run_download_phase(self, stop_event=None) -> bool:
        """Executa fase de downloads com progress tracking avançado."""
        try:
            self.stats['download_start_time'] = time.time()
            self.logger.info("Iniciando fase de downloads")
            
            # Obter downloads pendentes
            pending_downloads = self.csv_processor.get_pending_downloads()
            if not pending_downloads:
                self.logger.info("Nenhum download pendente encontrado")
                return True
            
            # NOVO: Configurar progress tracker para downloads
            self.progress_tracker.start_operation(len(pending_downloads))
            self.logger.info("Progress tracker configurado para downloads", total_items=len(pending_downloads))
            
            self.logger.info("Downloads pendentes encontrados", count=len(pending_downloads))
            
            # Processar downloads em lotes
            batch_size = self.config.batch_size
            total_processed = 0
            
            for i in range(0, len(pending_downloads), batch_size):
                batch = pending_downloads[i:i + batch_size]
                
                # Converter para formato do downloader assíncrono
                download_batch = []
                for download in batch:
                    download_batch.append({
                        'po_number': download['po_number'],
                        'url': download['url'],
                        'filename': download['filename'],
                        'file_type': download['file_type']
                    })
                
                # Baixar lote
                results = await self.async_downloader.download_batch_async(download_batch)
                
                # Atualizar status no CSV
                for result in results:
                    success = self.csv_processor.update_download_status(
                        po_number=result['po_number'],
                        filename=result['filename'],
                        status='completed' if result['success'] else 'failed',
                        error_message=result.get('error', ''),
                        file_size=result.get('file_size', 0)
                    )
                    
                    if result['success']:
                        self.stats['total_downloads_completed'] += 1
                        self.download_logger.download_completed(
                            result['filename'], 
                            result.get('file_size', 0), 
                            result.get('duration', 0)
                        )
                    else:
                        self.download_logger.download_failed(
                            result['filename'], 
                            result.get('error', 'Unknown error')
                        )
                
                total_processed += len(results)
                
                # NOVO: Atualizar progress tracker
                self.progress_tracker.update_progress(total_processed, total_processed, 0)
                
                # NOVO: Obter métricas inteligentes
                remaining_time = self.progress_tracker.get_remaining_time_estimate()
                throughput = self.progress_tracker.get_current_throughput()
                
                # Log de progresso com métricas avançadas
                progress = total_processed / len(pending_downloads) * 100
                self.logger.info("Progresso dos downloads", 
                               progress=f"{progress:.1f}%",
                               processed=total_processed,
                               total=len(pending_downloads),
                               estimated_remaining_time=remaining_time,
                               current_throughput=throughput)
            
            self.stats['download_end_time'] = time.time()
            
            # Log de performance
            duration = self.stats['download_end_time'] - self.stats['download_start_time']
            self.performance_logger.timing("download_phase", duration,
                                         downloads_completed=self.stats['total_downloads_completed'])
            
            self.logger.info("Fase de downloads concluída", 
                           duration=duration,
                           downloads_completed=self.stats['total_downloads_completed'])
            
            return True
            
        except Exception as e:
            self.logger.error("Erro na fase de downloads", error=str(e))
            return False
    
    async def run_complete_workflow(self, stop_event=None, execution_mode="both") -> bool:
        """Executa workflow completo."""
        try:
            self.logger.info("Iniciando workflow completo")
            
            # Verificar se deve parar antes de começar
            if stop_event and stop_event.is_set():
                self.logger.info("Sistema parado antes da execução")
                return False
            
            # Inicializar sistema
            if not await self.initialize_system():
                return False
            
            # Verificar stop_event após inicialização
            if stop_event and stop_event.is_set():
                self.logger.info("Sistema parado após inicialização")
                return False
            
            # Fase 1: Inventário (se necessário)
            if execution_mode in ["inventory_only", "both"]:
                if not await self.run_inventory_phase(stop_event):
                    self.logger.error("Falha na fase de inventário")
                    return False
                
                # Verificar stop_event após inventário
                if stop_event and stop_event.is_set():
                    self.logger.info("Sistema parado após fase de inventário")
                    return False
            
            # Fase 2: Downloads (se necessário)
            if execution_mode in ["download_only", "both"]:
                if not await self.run_download_phase(stop_event):
                    self.logger.error("Falha na fase de downloads")
                    return False
            
            # Relatório final
            await self._generate_final_report()
            
            self.logger.info("Workflow completo concluído com sucesso")
            return True
            
        except Exception as e:
            self.logger.error("Erro no workflow completo", error=str(e))
            return False
        finally:
            # Limpar recursos
            await self._cleanup()
    
    async def _generate_final_report(self):
        """Gera relatório final do processamento."""
        try:
            # Obter estatísticas finais
            final_stats = self.csv_processor.get_statistics()
            
            # Calcular tempos totais
            inventory_duration = 0
            download_duration = 0
            
            if self.stats['inventory_start_time'] and self.stats['inventory_end_time']:
                inventory_duration = self.stats['inventory_end_time'] - self.stats['inventory_start_time']
            
            if self.stats['download_start_time'] and self.stats['download_end_time']:
                download_duration = self.stats['download_end_time'] - self.stats['download_start_time']
            
            # Relatório
            report = {
                'inventory': {
                    'duration': inventory_duration,
                    'pos_processed': self.stats['total_pos_processed'],
                    'attachments_found': self.stats['total_attachments_found'],
                    'errors': self.stats['total_errors']
                },
                'downloads': {
                    'duration': download_duration,
                    'completed': self.stats['total_downloads_completed'],
                    'total_size': final_stats.get('total_size', 0)
                },
                'overall': {
                    'total_duration': inventory_duration + download_duration,
                    'success_rate': (self.stats['total_downloads_completed'] / max(self.stats['total_attachments_found'], 1)) * 100
                }
            }
            
            self.logger.info("Relatório final gerado", **report)
            
            # Log de performance final
            self.performance_logger.batch_processing(
                batch_size=self.stats['total_pos_processed'],
                total_processed=self.stats['total_downloads_completed'],
                success_rate=report['overall']['success_rate'],
                duration=report['overall']['total_duration']
            )
            
        except Exception as e:
            self.logger.error("Erro ao gerar relatório final", error=str(e))
    
    async def _cleanup(self):
        """Limpa recursos do sistema."""
        try:
            # Limpar sistema Playwright
            if self.playwright_system:
                await self.playwright_system.cleanup()
            
            self.logger.info("Recursos do sistema limpos")
            
        except Exception as e:
            self.logger.error("Erro ao limpar recursos", error=str(e))
    
    def get_system_status(self) -> Dict[str, Any]:
        """Retorna status atual do sistema."""
        try:
            csv_stats = self.csv_processor.get_statistics()
            
            return {
                'config': {
                    'max_workers': self.config.max_workers,
                    'batch_size': self.config.batch_size,
                    'headless': self.config.headless,
                    'profile_mode': self.config.profile_mode
                },
                'csv_stats': csv_stats,
                'system_stats': self.stats,
                'components': {
                    'playwright_available': self.playwright_system is not None,
                    'async_downloader_available': self.async_downloader is not None,
                    'csv_processor_available': self.csv_processor is not None
                }
            }
            
        except Exception as e:
            self.logger.error("Erro ao obter status do sistema", error=str(e))
            return {}


# Função principal para execução
async def run_advanced_coupa_system(stop_event=None, execution_mode="both", ui_config=None) -> bool:
    """Executa o sistema avançado completo."""
    # CORREÇÃO: Passar configurações da UI para o sistema avançado
    system = AdvancedCoupaSystem(ui_config=ui_config)
    
    try:
        success = await system.run_complete_workflow(stop_event, execution_mode)
        
        if success:
            print("✅ Sistema avançado executado com sucesso!")
            
            # Mostrar status final
            status = system.get_system_status()
            print(f"📊 Estatísticas finais:")
            print(f"   • POs processadas: {status['system_stats']['total_pos_processed']}")
            print(f"   • Attachments encontrados: {status['system_stats']['total_attachments_found']}")
            print(f"   • Downloads concluídos: {status['system_stats']['total_downloads_completed']}")
            print(f"   • Taxa de sucesso: {status['csv_stats'].get('success_rate', 0):.1f}%")
        else:
            print("❌ Sistema avançado falhou")
        
        return success
        
    except Exception as e:
        print(f"❌ Erro crítico no sistema avançado: {e}")
        return False


if __name__ == "__main__":
    # Executar sistema avançado
    print("🚀 Iniciando Sistema Avançado CoupaDownloads...")
    
    success = asyncio.run(run_advanced_coupa_system())
    
    if success:
        print("🎉 Sistema avançado concluído com sucesso!")
    else:
        print("💥 Sistema avançado falhou!")
