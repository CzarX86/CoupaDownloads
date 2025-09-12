"""
Advanced Coupa Field Extractor - Quick Start
Script simplificado para extração avançada com múltiplas bibliotecas NLP
"""

import os
import sys
from pathlib import aePath

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from advanced_coupa_field_extractor import AdvancedCoupaPDFFieldExtractor


def main():
    """Função principal simplificada para extração avançada."""
    print("📄 Extrator Avançado de Campos do Coupa com NLP")
    print("=" * 60)
    
    # Diretório dos PDFs
    pdf_directory = "/Users/juliocezar/Dev/work/CoupaDownloads/src/data/P2"
    
    print(f"📁 Diretório dos PDFs: {pdf_directory}")
    
    # Verificar se o diretório existe
    if not os.path.exists(pdf_directory):
        print(f"❌ Diretório não encontrado: {pdf_directory}")
        print("💡 Certifique-se de que a pasta P2 existe e contém arquivos PDF")
        return
    
    # Criar extrator avançado
    print("🔧 Inicializando extrator avançado com múltiplas bibliotecas NLP...")
    extractor = AdvancedCoupaPDFFieldExtractor(pdf_directory)
    
    # Verificar bibliotecas disponíveis
    print(f"📚 Bibliotecas NLP disponíveis: {', '.join(extractor.available_libraries)}")
    
    if not extractor.available_libraries:
        print("⚠️ Nenhuma biblioteca NLP disponível!")
        print("💡 Instale pelo menos uma das seguintes:")
        print("   - spaCy: pip install spacy && python -m spacy download pt_core_news_sm")
        print("   - Transformers: pip install transformers")
        print("   - Sentence Transformers: pip install sentence-transformers")
        print("   - LangChain: pip install langchain")
        print("   - Ollama: pip install ollama")
        return
    
    # Verificar se há PDFs
    pdf_files = extractor.find_pdf_files()
    if not pdf_files:
        print("⚠️ Nenhum arquivo PDF encontrado na pasta P2")
        print("💡 Adicione alguns arquivos PDF na pasta para testar")
        return
    
    print(f"📄 Encontrados {len(pdf_files)} arquivos PDF")
    
    # Processar PDFs
    print("\n🚀 Iniciando extração avançada com múltiplas técnicas NLP...")
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
        for field_name in extractor.target_fields:
            count = sum(1 for e in extractions if getattr(e, field_name, "").strip())
            field_counts[field_name] = count
        
        print(f"\n🔍 Campos mais encontrados:")
        sorted_fields = sorted(field_counts.items(), key=lambda x: x[1], reverse=True)
        for field_name, count in sorted_fields[:10]:
            if count > 0:
                field_display = field_name.replace('_', ' ').title()
                print(f"  - {field_display}: {count} documentos")
        
        # Mostrar estatísticas por biblioteca NLP
        library_stats = {}
        for extraction in extractions:
            for lib in extraction.nlp_libraries_used or []:
                if lib not in library_stats:
                    library_stats[lib] = 0
                library_stats[lib] += 1
        
        print(f"\n📚 Uso das bibliotecas NLP:")
        for lib, count in library_stats.items():
            print(f"  - {lib}: {count} documentos")
        
        # Mostrar exemplos de campos extraídos
        print(f"\n📋 Exemplos de campos extraídos:")
        for i, extraction in enumerate(extractions[:3], 1):  # Mostrar apenas os primeiros 3
            print(f"\n{i}. {extraction.source_file}")
            print(f"   Confiança: {extraction.extraction_confidence:.2f}")
            print(f"   Bibliotecas: {', '.join(extraction.nlp_libraries_used or [])}")
            
            # Mostrar alguns campos encontrados
            fields_shown = 0
            for field_name in extractor.target_fields:
                field_value = getattr(extraction, field_name, "")
                if field_value and field_value.strip() and fields_shown < 3:
                    field_display = field_name.replace('_', ' ').title()
                    print(f"   {field_display}: {field_value}")
                    fields_shown += 1
            
            if fields_shown == 0:
                print("   Nenhum campo específico encontrado")
        
        print(f"\n📊 Resumo da extração avançada:")
        print(f"   Total de campos disponíveis: {len(extractor.target_fields)}")
        print(f"   Documentos com pelo menos 1 campo: {sum(1 for e in extractions if e.extraction_confidence > 0)}")
        print(f"   Documentos com alta confiança (>0.5): {sum(1 for e in extractions if e.extraction_confidence > 0.5)}")
        print(f"   Bibliotecas NLP utilizadas: {len(extractor.available_libraries)}")
        
    else:
        print(f"\n❌ Nenhum documento processado com sucesso")
        print("💡 Verifique se os PDFs contêm texto legível e se as bibliotecas NLP estão funcionando")


if __name__ == "__main__":
    main()
