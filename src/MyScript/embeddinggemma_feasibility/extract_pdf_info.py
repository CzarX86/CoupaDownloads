"""
PDF Information Extraction - Quick Start Guide
Guia rápido para extração de informações de PDFs usando EmbeddingGemma
"""

import os
import sys
from pathlib import Path

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_information_extractor import PDFInformationExtractor


def main():
    """Função principal simplificada para extração de PDFs."""
    print("📄 Extrator de Informações de PDFs - CoupaDownloads")
    print("=" * 60)
    
    # Diretório dos PDFs
    pdf_directory = "/Users/juliocezar/Dev/work/CoupaDownloads/src/data/P2"
    
    print(f"📁 Diretório dos PDFs: {pdf_directory}")
    
    # Verificar se o diretório existe
    if not os.path.exists(pdf_directory):
        print(f"❌ Diretório não encontrado: {pdf_directory}")
        print("💡 Certifique-se de que a pasta P2 existe e contém arquivos PDF")
        return
    
    # Criar extrator
    print("🔧 Inicializando extrator...")
    extractor = PDFInformationExtractor(pdf_directory)
    
    # Verificar se há PDFs
    pdf_files = extractor.find_pdf_files()
    if not pdf_files:
        print("⚠️ Nenhum arquivo PDF encontrado na pasta P2")
        print("💡 Adicione alguns arquivos PDF na pasta para testar")
        return
    
    print(f"📄 Encontrados {len(pdf_files)} arquivos PDF:")
    for pdf_file in pdf_files:
        print(f"  - {pdf_file.name}")
    
    # Processar PDFs
    print("\n🚀 Iniciando processamento...")
    result = extractor.process_all_pdfs()
    
    if result.success:
        print(f"\n✅ Processamento concluído com sucesso!")
        print(f"📊 Documentos processados: {result.documents_processed}")
        print(f"⏱️ Tempo total: {result.total_processing_time:.2f} segundos")
        
        # Mostrar estatísticas
        if result.statistics:
            stats = result.statistics
            print(f"\n📈 Estatísticas:")
            print(f"  - Total de páginas: {stats.get('total_pages', 0)}")
            print(f"  - Comprimento médio: {stats.get('average_text_length', 0):.0f} caracteres")
            print(f"  - Score médio de relevância: {stats.get('average_relevance_score', 0):.2f}")
            
            # Mostrar categorias
            if stats.get('category_distribution'):
                print(f"  - Categorias encontradas:")
                for category, count in stats['category_distribution'].items():
                    print(f"    * {category}: {count} documentos")
        
        # Salvar resultados
        output_file = extractor.save_results(result)
        print(f"\n💾 Resultados salvos em: {output_file}")
        
        # Gerar relatório
        report = extractor.generate_report(result)
        report_file = output_file.replace('.json', '_report.md')
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"📋 Relatório salvo em: {report_file}")
        
        # Mostrar exemplos de informações extraídas
        print(f"\n🔍 Exemplos de informações extraídas:")
        for i, info in enumerate(result.extracted_info[:3], 1):  # Mostrar apenas os primeiros 3
            print(f"\n{i}. {info.document.filename}")
            print(f"   Categorias: {', '.join(info.categories)}")
            print(f"   Frases-chave: {', '.join(info.key_phrases[:5])}")
            print(f"   Resumo: {info.summary[:100]}...")
        
    else:
        print(f"\n❌ Processamento falhou")
        print(f"Erros encontrados: {len(result.errors)}")
        for error in result.errors:
            print(f"  - {error}")


if __name__ == "__main__":
    main()
