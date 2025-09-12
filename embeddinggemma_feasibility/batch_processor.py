#!/usr/bin/env python3
"""
Processador em Lote - Sistema Completamente Customizado
Processa todos os PDFs da pasta P2 e consolida resultados em CSV.
"""

import os
import csv
import json
from pathlib import Path
from datetime import datetime
import logging
from typing import List, Dict, Any

# Importar o extrator customizado
from fully_customized_extractor import FullyCustomizedCoupaExtractor

class BatchContractProcessor:
    """Processador em lote para contratos."""
    
    def __init__(self, pdf_directory: str, csv_file: str, output_dir: str):
        self.pdf_directory = Path(pdf_directory)
        self.csv_file = csv_file
        self.output_dir = Path(output_dir)
        self.logger = logging.getLogger(__name__)
        
        # Criar diretório de saída
        self.output_dir.mkdir(exist_ok=True)
        
        # Inicializar extrator
        self.extractor = FullyCustomizedCoupaExtractor(str(self.pdf_directory), csv_file)
        
        # Lista de resultados
        self.results = []
        self.errors = []
    
    def find_pdf_files(self) -> List[Path]:
        """Encontrar todos os arquivos PDF."""
        pdf_files = []
        
        if self.pdf_directory.exists():
            for pdf_file in self.pdf_directory.rglob("*.pdf"):
                pdf_files.append(pdf_file)
        
        self.logger.info(f"✅ Encontrados {len(pdf_files)} arquivos PDF")
        return pdf_files
    
    def process_single_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """Processar um único PDF."""
        try:
            self.logger.info(f"📄 Processando: {pdf_path.name}")
            
            # Extrair campos
            result = self.extractor.extract_coupa_fields_from_file(str(pdf_path))
            
            # Converter para dicionário
            result_dict = {
                'source_file': result.source_file,
                'extraction_method': result.extraction_method,
                'extraction_confidence': result.extraction_confidence,
                'nlp_libraries_used': ', '.join(result.nlp_libraries_used),
                'processing_timestamp': datetime.now().isoformat(),
                'file_path': str(pdf_path),
                'file_size_mb': round(pdf_path.stat().st_size / (1024 * 1024), 2)
            }
            
            # Adicionar campos extraídos
            for field, value in result.__dict__.items():
                if field not in ['source_file', 'extraction_method', 'extraction_confidence', 'nlp_libraries_used']:
                    result_dict[field] = value
            
            return result_dict
            
        except Exception as e:
            error_info = {
                'source_file': pdf_path.name,
                'error': str(e),
                'processing_timestamp': datetime.now().isoformat(),
                'file_path': str(pdf_path)
            }
            self.errors.append(error_info)
            self.logger.error(f"❌ Erro ao processar {pdf_path.name}: {e}")
            return None
    
    def process_all_pdfs(self):
        """Processar todos os PDFs."""
        pdf_files = self.find_pdf_files()
        
        if not pdf_files:
            self.logger.warning("⚠️ Nenhum arquivo PDF encontrado")
            return
        
        self.logger.info(f"🚀 Iniciando processamento de {len(pdf_files)} arquivos...")
        
        for i, pdf_file in enumerate(pdf_files, 1):
            self.logger.info(f"📊 Progresso: {i}/{len(pdf_files)}")
            
            result = self.process_single_pdf(pdf_file)
            if result:
                self.results.append(result)
        
        self.logger.info(f"✅ Processamento concluído: {len(self.results)} sucessos, {len(self.errors)} erros")
    
    def save_results_to_csv(self):
        """Salvar resultados em CSV."""
        if not self.results:
            self.logger.warning("⚠️ Nenhum resultado para salvar")
            return
        
        # Definir campos do CSV
        fieldnames = [
            'source_file', 'extraction_method', 'extraction_confidence', 'nlp_libraries_used',
            'processing_timestamp', 'file_path', 'file_size_mb',
            'remarks', 'supporting_information', 'procurement_negotiation_strategy',
            'opportunity_available', 'inflation_percent', 'minimum_commitment_value',
            'contractual_commercial_model', 'user_based_license', 'type_of_contract_l2',
            'type_of_contract_l1', 'sow_value_eur', 'fx', 'sow_currency', 'sow_value_lc',
            'managed_by', 'contract_end_date', 'contract_start_date', 'contract_type',
            'contract_name', 'high_level_scope', 'platform_technology', 'pwo_number'
        ]
        
        # Arquivo CSV principal
        csv_file = self.output_dir / f"contract_extraction_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in self.results:
                # Garantir que todos os campos existam
                row = {field: result.get(field, '') for field in fieldnames}
                writer.writerow(row)
        
        self.logger.info(f"💾 Resultados salvos em: {csv_file}")
        
        # Arquivo CSV de erros
        if self.errors:
            error_file = self.output_dir / f"contract_extraction_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            with open(error_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['source_file', 'error', 'processing_timestamp', 'file_path'])
                writer.writeheader()
                writer.writerows(self.errors)
            
            self.logger.info(f"💾 Erros salvos em: {error_file}")
    
    def save_summary_report(self):
        """Salvar relatório de resumo."""
        summary = {
            'processing_date': datetime.now().isoformat(),
            'total_files_processed': len(self.results) + len(self.errors),
            'successful_extractions': len(self.results),
            'failed_extractions': len(self.errors),
            'success_rate': len(self.results) / (len(self.results) + len(self.errors)) * 100 if (len(self.results) + len(self.errors)) > 0 else 0,
            'average_confidence': sum(r['extraction_confidence'] for r in self.results) / len(self.results) if self.results else 0,
            'fields_extracted': {},
            'libraries_used': set()
        }
        
        # Analisar campos extraídos
        for result in self.results:
            for field, value in result.items():
                if field not in ['source_file', 'extraction_method', 'extraction_confidence', 'nlp_libraries_used', 'processing_timestamp', 'file_path', 'file_size_mb']:
                    if value and str(value).strip():
                        summary['fields_extracted'][field] = summary['fields_extracted'].get(field, 0) + 1
            
            # Analisar bibliotecas usadas
            libraries = result.get('nlp_libraries_used', '').split(', ')
            summary['libraries_used'].update(libraries)
        
        summary['libraries_used'] = list(summary['libraries_used'])
        
        # Salvar relatório
        report_file = self.output_dir / f"extraction_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"📊 Relatório de resumo salvo em: {report_file}")
        
        # Imprimir resumo
        print(f"\n📊 RESUMO DO PROCESSAMENTO:")
        print(f"   - Arquivos processados: {summary['total_files_processed']}")
        print(f"   - Extrações bem-sucedidas: {summary['successful_extractions']}")
        print(f"   - Extrações com erro: {summary['failed_extractions']}")
        print(f"   - Taxa de sucesso: {summary['success_rate']:.1f}%")
        print(f"   - Confiança média: {summary['average_confidence']:.2f}")
        print(f"   - Bibliotecas utilizadas: {', '.join(summary['libraries_used'])}")
        
        print(f"\n📋 CAMPOS MAIS EXTRAÍDOS:")
        sorted_fields = sorted(summary['fields_extracted'].items(), key=lambda x: x[1], reverse=True)
        for field, count in sorted_fields[:10]:
            print(f"   - {field}: {count} arquivos")

def main():
    """Função principal."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configurações
    pdf_directory = '/Users/juliocezar/Dev/work/CoupaDownloads/src/data/P2'
    csv_file = '/Users/juliocezar/Dev/work/CoupaDownloads/src/MyScript/embeddinggemma_feasibility/data/20250910_Template_for_data_capture_P2_Contract_Tracker.csv'
    output_dir = '/Users/juliocezar/Dev/work/CoupaDownloads/src/MyScript/embeddinggemma_feasibility/reports'
    
    print("🚀 PROCESSADOR EM LOTE - SISTEMA COMPLETAMENTE CUSTOMIZADO")
    print("=" * 70)
    
    # Criar processador
    processor = BatchContractProcessor(pdf_directory, csv_file, output_dir)
    
    # Processar todos os PDFs
    processor.process_all_pdfs()
    
    # Salvar resultados
    processor.save_results_to_csv()
    processor.save_summary_report()
    
    print(f"\n🎉 PROCESSAMENTO CONCLUÍDO!")
    print(f"   - Resultados salvos em: {output_dir}")

if __name__ == "__main__":
    main()

