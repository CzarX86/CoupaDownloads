"""
Sistema de Processamento de Dados com Polars
Substitui pandas por Polars para performance superior e uso de memória otimizado
"""

import os
import time
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from datetime import datetime

import polars as pl
from polars import DataFrame, LazyFrame

# Importação condicional
try:
    from config_advanced import get_config
except ImportError:
    pass

try:
    from logging_advanced import get_logger, get_performance_logger
except ImportError:
    pass

try:
    from retry_advanced import retry_csv_operation
except ImportError:
    pass


class PolarsDataProcessor:
    """Processador de dados usando Polars para alta performance."""
    
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.config = get_config()
        self.logger = get_logger("polars_processor")
        self.performance_logger = get_performance_logger()
        
        # Schema padrão para CSV de inventário
        self.inventory_schema = {
            'po_number': pl.Utf8,
            'url': pl.Utf8,
            'filename': pl.Utf8,
            'file_type': pl.Utf8,
            'status': pl.Utf8,
            'created_at': pl.Utf8,
            'downloaded_at': pl.Utf8,
            'error_message': pl.Utf8,
            'file_size': pl.Int64,
            'window_id': pl.Utf8,
            'tab_id': pl.Utf8
        }
    
    @retry_csv_operation(max_attempts=3, delay=1.0)
    def read_csv(self) -> Optional[DataFrame]:
        """Lê CSV usando Polars com schema definido."""
        try:
            start_time = time.time()
            
            if not os.path.exists(self.csv_path):
                self.logger.warning("CSV não encontrado, criando novo", path=self.csv_path)
                return self._create_empty_dataframe()
            
            # Ler CSV com Polars
            df = pl.read_csv(
                self.csv_path,
                dtypes=self.inventory_schema,
                ignore_errors=True,
                try_parse_dates=False
            )
            
            duration = time.time() - start_time
            self.performance_logger.timing("csv_read", duration, rows=len(df))
            
            self.logger.info("CSV lido com Polars", 
                           path=self.csv_path, 
                           rows=len(df),
                           duration=duration)
            
            return df
            
        except Exception as e:
            self.logger.error("Erro ao ler CSV com Polars", error=str(e), path=self.csv_path)
            return None
    
    def _create_empty_dataframe(self) -> DataFrame:
        """Cria DataFrame vazio com schema correto."""
        try:
            empty_data = {col: [] for col in self.inventory_schema.keys()}
            df = pl.DataFrame(empty_data, schema=self.inventory_schema)
            
            # Salvar CSV vazio
            df.write_csv(self.csv_path)
            
            self.logger.info("DataFrame vazio criado", path=self.csv_path)
            return df
            
        except Exception as e:
            self.logger.error("Erro ao criar DataFrame vazio", error=str(e))
            raise
    
    @retry_csv_operation(max_attempts=3, delay=1.0)
    def write_csv(self, df: DataFrame) -> bool:
        """Escreve DataFrame para CSV usando Polars."""
        try:
            start_time = time.time()
            
            # Garantir que todas as colunas do schema existam
            df = self._ensure_schema(df)
            
            # Escrever CSV
            df.write_csv(self.csv_path)
            
            duration = time.time() - start_time
            self.performance_logger.timing("csv_write", duration, rows=len(df))
            
            self.logger.info("CSV escrito com Polars", 
                           path=self.csv_path, 
                           rows=len(df),
                           duration=duration)
            
            return True
            
        except Exception as e:
            self.logger.error("Erro ao escrever CSV com Polars", error=str(e), path=self.csv_path)
            return False
    
    def _ensure_schema(self, df: DataFrame) -> DataFrame:
        """Garante que DataFrame tenha todas as colunas do schema."""
        try:
            # Adicionar colunas faltantes
            for col, dtype in self.inventory_schema.items():
                if col not in df.columns:
                    if dtype == pl.Utf8:
                        df = df.with_columns(pl.lit("").alias(col))
                    elif dtype == pl.Int64:
                        df = df.with_columns(pl.lit(0).alias(col))
            
            # Reordenar colunas conforme schema
            df = df.select(list(self.inventory_schema.keys()))
            
            return df
            
        except Exception as e:
            self.logger.warning("Erro ao garantir schema", error=str(e))
            return df
    
    def add_download_record(self, record: Dict[str, Any]) -> bool:
        """Adiciona um registro de download ao CSV."""
        try:
            start_time = time.time()
            
            # Ler DataFrame existente
            df = self.read_csv()
            if df is None:
                return False
            
            # Preparar novo registro
            new_record = {
                'po_number': record.get('po_number', ''),
                'url': record.get('url', ''),
                'filename': record.get('filename', ''),
                'file_type': record.get('file_type', 'unknown'),
                'status': record.get('status', 'pending'),
                'created_at': record.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                'downloaded_at': record.get('downloaded_at', ''),
                'error_message': record.get('error_message', ''),
                'file_size': record.get('file_size', 0),
                'window_id': record.get('window_id', ''),
                'tab_id': record.get('tab_id', '')
            }
            
            # Criar DataFrame com novo registro
            new_df = pl.DataFrame([new_record], schema=self.inventory_schema)
            
            # Concatenar DataFrames
            combined_df = pl.concat([df, new_df])
            
            # Escrever CSV atualizado
            success = self.write_csv(combined_df)
            
            duration = time.time() - start_time
            self.performance_logger.timing("add_record", duration)
            
            return success
            
        except Exception as e:
            self.logger.error("Erro ao adicionar registro", error=str(e))
            return False
    
    def add_multiple_records(self, records: List[Dict[str, Any]]) -> bool:
        """Adiciona múltiplos registros de uma vez (mais eficiente)."""
        try:
            start_time = time.time()
            
            # Ler DataFrame existente
            df = self.read_csv()
            if df is None:
                return False
            
            # Preparar novos registros
            new_records = []
            for record in records:
                new_records.append({
                    'po_number': record.get('po_number', ''),
                    'url': record.get('url', ''),
                    'filename': record.get('filename', ''),
                    'file_type': record.get('file_type', 'unknown'),
                    'status': record.get('status', 'pending'),
                    'created_at': record.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                    'downloaded_at': record.get('downloaded_at', ''),
                    'error_message': record.get('error_message', ''),
                    'file_size': record.get('file_size', 0),
                    'window_id': record.get('window_id', ''),
                    'tab_id': record.get('tab_id', '')
                })
            
            # Criar DataFrame com novos registros
            new_df = pl.DataFrame(new_records, schema=self.inventory_schema)
            
            # Concatenar DataFrames
            combined_df = pl.concat([df, new_df])
            
            # Escrever CSV atualizado
            success = self.write_csv(combined_df)
            
            duration = time.time() - start_time
            self.performance_logger.timing("add_multiple_records", duration, count=len(records))
            
            return success
            
        except Exception as e:
            self.logger.error("Erro ao adicionar múltiplos registros", error=str(e))
            return False
    
    def get_pending_downloads(self) -> List[Dict[str, Any]]:
        """Obtém downloads pendentes usando Polars."""
        try:
            df = self.read_csv()
            if df is None:
                return []
            
            # Filtrar downloads pendentes usando Polars
            pending_df = df.filter(pl.col('status') == 'pending')
            
            # Converter para lista de dicionários
            pending_downloads = pending_df.to_dicts()
            
            self.logger.info("Downloads pendentes obtidos", count=len(pending_downloads))
            return pending_downloads
            
        except Exception as e:
            self.logger.error("Erro ao obter downloads pendentes", error=str(e))
            return []
    
    def update_download_status(self, po_number: str, filename: str, 
                             status: str, error_message: str = "", 
                             file_size: int = 0) -> bool:
        """Atualiza status de download usando Polars."""
        try:
            start_time = time.time()
            
            df = self.read_csv()
            if df is None:
                return False
            
            # Criar máscara para encontrar registro
            mask = (pl.col('po_number') == po_number) & (pl.col('filename') == filename)
            
            # Verificar se registro existe
            if not mask.any():
                self.logger.warning("Registro não encontrado", po_number=po_number, filename=filename)
                return False
            
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
            
            # Escrever CSV atualizado
            success = self.write_csv(df)
            
            duration = time.time() - start_time
            self.performance_logger.timing("update_status", duration)
            
            return success
            
        except Exception as e:
            self.logger.error("Erro ao atualizar status", error=str(e))
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas dos downloads usando Polars."""
        try:
            df = self.read_csv()
            if df is None or len(df) == 0:
                return {
                    'total_downloads': 0,
                    'pending_downloads': 0,
                    'completed_downloads': 0,
                    'failed_downloads': 0,
                    'total_size': 0,
                    'unique_pos': 0
                }
            
            # Calcular estatísticas usando Polars
            stats = df.group_by('status').agg([
                pl.count().alias('count'),
                pl.col('file_size').sum().alias('total_size')
            ])
            
            # Converter para dicionário
            stats_dict = {}
            for row in stats.to_dicts():
                status = row['status']
                count = row['count']
                size = row['total_size']
                
                stats_dict[f'{status}_downloads'] = count
                if status == 'completed':
                    stats_dict['total_size'] = size
            
            # Adicionar estatísticas gerais
            stats_dict['total_downloads'] = len(df)
            stats_dict['unique_pos'] = df.select('po_number').n_unique()
            
            # Preencher valores faltantes
            for status in ['pending', 'completed', 'failed', 'downloading']:
                key = f'{status}_downloads'
                if key not in stats_dict:
                    stats_dict[key] = 0
            
            if 'total_size' not in stats_dict:
                stats_dict['total_size'] = 0
            
            self.logger.info("Estatísticas calculadas", **stats_dict)
            return stats_dict
            
        except Exception as e:
            self.logger.error("Erro ao calcular estatísticas", error=str(e))
            return {}
    
    def get_downloads_by_po(self, po_number: str) -> List[Dict[str, Any]]:
        """Obtém todos os downloads de uma PO específica."""
        try:
            df = self.read_csv()
            if df is None:
                return []
            
            # Filtrar por PO usando Polars
            po_df = df.filter(pl.col('po_number') == po_number)
            
            # Converter para lista de dicionários
            downloads = po_df.to_dicts()
            
            self.logger.info("Downloads por PO obtidos", po_number=po_number, count=len(downloads))
            return downloads
            
        except Exception as e:
            self.logger.error("Erro ao obter downloads por PO", error=str(e))
            return []
    
    def get_downloads_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Obtém downloads por status específico."""
        try:
            df = self.read_csv()
            if df is None:
                return []
            
            # Filtrar por status usando Polars
            status_df = df.filter(pl.col('status') == status)
            
            # Converter para lista de dicionários
            downloads = status_df.to_dicts()
            
            self.logger.info("Downloads por status obtidos", status=status, count=len(downloads))
            return downloads
            
        except Exception as e:
            self.logger.error("Erro ao obter downloads por status", error=str(e))
            return []
    
    def cleanup_old_records(self, days_old: int = 30) -> int:
        """Remove registros antigos para manter CSV limpo."""
        try:
            df = self.read_csv()
            if df is None:
                return 0
            
            # Calcular data limite
            cutoff_date = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
            cutoff_str = datetime.fromtimestamp(cutoff_date).strftime('%Y-%m-%d %H:%M:%S')
            
            # Filtrar registros recentes
            recent_df = df.filter(pl.col('created_at') >= cutoff_str)
            
            # Contar registros removidos
            removed_count = len(df) - len(recent_df)
            
            if removed_count > 0:
                # Escrever CSV limpo
                self.write_csv(recent_df)
                self.logger.info("Registros antigos removidos", count=removed_count, days_old=days_old)
            
            return removed_count
            
        except Exception as e:
            self.logger.error("Erro ao limpar registros antigos", error=str(e))
            return 0


class PolarsExcelProcessor:
    """Processador de planilhas (Excel ou CSV) usando Polars.

    Mantém a API existente e detecta o formato pelo sufixo do arquivo.
    """
    
    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self.logger = get_logger("polars_excel")
    
    def read_excel(self, sheet_name: str = 'PO_Data') -> Optional[DataFrame]:
        """Lê planilha via Polars.

        - .csv => usa pl.read_csv
        - .xlsx/.xls => usa pl.read_excel na aba indicada
        """
        try:
            start_time = time.time()
            
            if not os.path.exists(self.excel_path):
                self.logger.error("Arquivo Excel não encontrado", path=self.excel_path)
                return None
            
            # Detectar formato
            _, ext = os.path.splitext(self.excel_path.lower())
            if ext == ".csv":
                # Robust CSV read for Polars: handle BOM and semicolon/comma separator
                import io
                encodings = ["utf-8-sig", "utf-8", "latin1"]
                text = None
                used_enc = None
                for enc in encodings:
                    try:
                        with open(self.excel_path, "r", encoding=enc, errors="strict") as f:
                            text = f.read()
                            used_enc = enc
                            break
                    except Exception:
                        continue
                if text is None:
                    # Fallback with replacement
                    with open(self.excel_path, "r", encoding="utf-8", errors="replace") as f:
                        text = f.read()
                        used_enc = "utf-8"
                header_line = text.splitlines()[0] if text else ""
                sep = ";" if header_line.count(";") > header_line.count(",") else ","
                df = pl.read_csv(io.StringIO(text), separator=sep)
                self.logger.debug("CSV detectado para Polars", separator=sep, encoding=used_enc)
            else:
                # Ler Excel com Polars
                df = pl.read_excel(self.excel_path, sheet_name=sheet_name)

            duration = time.time() - start_time
            self.logger.info("Planilha lida com Polars", 
                            path=self.excel_path, 
                            kind=("CSV" if ext == ".csv" else "Excel"),
                            rows=len(df),
                            duration=duration)
            
            return df
            
        except Exception as e:
            self.logger.error("Erro ao ler planilha com Polars", error=str(e), path=self.excel_path)
            return None
    
    def get_po_numbers(self, max_lines: Optional[int] = None) -> List[str]:
        """Obtém números de PO do Excel usando Polars."""
        try:
            df = self.read_excel()
            if df is None:
                return []
            
            # Filtrar e limpar números de PO
            po_numbers = (
                df.select('PO_NUMBER')
                .drop_nulls()
                .with_columns(
                    pl.col('PO_NUMBER').cast(pl.Utf8)
                )
                .to_series()
                .to_list()
            )
            
            # Aplicar limite se especificado
            if max_lines and max_lines > 0:
                po_numbers = po_numbers[:max_lines]
                self.logger.info("POs limitados", max_lines=max_lines, actual_count=len(po_numbers))
            
            self.logger.info("Números de PO obtidos", count=len(po_numbers))
            return po_numbers
            
        except Exception as e:
            self.logger.error("Erro ao obter números de PO", error=str(e))
            return []


# Instâncias globais para compatibilidade
def get_polars_processor(csv_path: str) -> PolarsDataProcessor:
    """Retorna instância do processador Polars."""
    return PolarsDataProcessor(csv_path)


def get_polars_excel_processor(excel_path: str) -> PolarsExcelProcessor:
    """Retorna instância do processador Excel Polars."""
    return PolarsExcelProcessor(excel_path)


if __name__ == "__main__":
    # Teste do sistema Polars
    print("🔧 Testando sistema Polars...")
    
    # Teste de processamento de dados
    csv_path = "src/MyScript/test_polars.csv"
    processor = PolarsDataProcessor(csv_path)
    
    # Teste de adição de registros
    test_record = {
        'po_number': 'PO123456',
        'url': 'https://example.com/file.pdf',
        'filename': 'test_file.pdf',
        'file_type': 'pdf',
        'status': 'pending'
    }
    
    success = processor.add_download_record(test_record)
    print(f"✅ Registro adicionado: {success}")
    
    # Teste de estatísticas
    stats = processor.get_statistics()
    print(f"✅ Estatísticas: {stats}")
    
    # Teste de Excel
    excel_path = "src/MyScript/input.xlsx"
    if os.path.exists(excel_path):
        excel_processor = PolarsExcelProcessor(excel_path)
        po_numbers = excel_processor.get_po_numbers(max_lines=5)
        print(f"✅ POs obtidos: {len(po_numbers)}")
    
    print("✅ Sistema Polars testado!")
