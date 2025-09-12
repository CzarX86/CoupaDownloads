"""
Coupa Field Extractor - Quick Start
Script simplificado para extração de campos específicos do Coupa
"""

import os
import sys
from pathlib import Path

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coupa_field_extractor import CoupaPDFFieldExtractor


def main():
    """Função principal simplificada para extração de campos do Coupa."""
    print("📄 Extrator de Campos Específicos do Coupa")
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
    print("🔧 Inicializando extrator de campos específicos...")
    extractor = CoupaPDFFieldExtractor(pdf_directory)
    
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
    print("\n🚀 Iniciando extração de campos específicos...")
    extractions = extractor.process_all_pdfs()
    
    if extractions:
        print(f"\n✅ Processamento concluído com sucesso!")
        print(f"📊 Documentos processados: {len(extractions)}")
        
        # Calcular estatísticas
        avg_confidence = sum(e.extraction_confidence for e in extractions) / len(extractions)
        print(f"📈 Confiança média da extração: {avg_confidence:.2f}")
        
        # Salvar CSV
        csv_file = extractor.save_to_csv(extractions)
        print(f"💾 CSV salvo em: {csv_file}")
        
        # Gerar relatório
        report = extractor.generate_extraction_report(extractions)
        report_file = csv_file.replace('.csv', '_report.md')
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"📋 Relatório salvo em: {report_file}")
        
        # Mostrar campos mais encontrados
        field_counts = {}
        for field_name in extractor.field_patterns.keys():
            count = sum(1 for e in extractions if getattr(e, field_name, "").strip())
            field_counts[field_name] = count
        
        print(f"\n🔍 Campos mais encontrados:")
        sorted_fields = sorted(field_counts.items(), key=lambda x: x[1], reverse=True)
        for field_name, count in sorted_fields[:10]:
            if count > 0:
                field_display = field_name.replace('_', ' ').title()
                print(f"  - {field_display}: {count} documentos")
        
        # Mostrar exemplos de campos extraídos
        print(f"\n📋 Exemplos de campos extraídos:")
        for i, extraction in enumerate(extractions[:3], 1):  # Mostrar apenas os primeiros 3
            print(f"\n{i}. {extraction.source_file}")
            
            # Mostrar alguns campos encontrados
            fields_shown = 0
            for field_name in extractor.field_patterns.keys():
                field_value = getattr(extraction, field_name, "")
                if field_value and field_value.strip() and fields_shown < 3:
                    field_display = field_name.replace('_', ' ').title()
                    print(f"   {field_display}: {field_value}")
                    fields_shown += 1
            
            if fields_shown == 0:
                print("   Nenhum campo específico encontrado")
        
        print(f"\n📊 Resumo dos campos extraídos:")
        print(f"   Total de campos disponíveis: {len(extractor.field_patterns)}")
        print(f"   Documentos com pelo menos 1 campo: {sum(1 for e in extractions if e.extraction_confidence > 0)}")
        print(f"   Documentos com alta confiança (>0.5): {sum(1 for e in extractions if e.extraction_confidence > 0.5)}")
        
    else:
        print(f"\n❌ Nenhum documento processado com sucesso")
        print("💡 Verifique se os PDFs contêm texto legível")


if __name__ == "__main__":
    main()
