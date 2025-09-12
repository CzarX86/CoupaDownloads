#!/usr/bin/env python3
"""
Script de teste para processar um único PDF com o extrator avançado.
"""

import os
import sys
from pathlib import Path
from advanced_coupa_field_extractor import AdvancedCoupaPDFFieldExtractor

def test_single_pdf(pdf_path: str):
    """Testar extração em um único PDF."""
    print(f"🧪 Testando extração com: {os.path.basename(pdf_path)}")
    print("=" * 60)
    
    # Inicializar extrator
    pdf_dir = os.path.dirname(pdf_path)
    extractor = AdvancedCoupaPDFFieldExtractor(pdf_dir)
    
    # Extrair campos
    result = extractor.extract_coupa_fields_from_file(pdf_path)
    
    # Mostrar resultados
    print(f"📄 Arquivo: {result.source_file}")
    print(f"📊 Confiança: {result.extraction_confidence:.2f}")
    print(f"🔧 Método: {result.extraction_method}")
    print(f"📚 Bibliotecas: {', '.join(result.nlp_libraries_used)}")
    print()
    
    # Mostrar campos extraídos
    fields_with_values = []
    for field, value in result.__dict__.items():
        if field not in ['source_file', 'extraction_method', 'extraction_confidence', 'nlp_libraries_used'] and value:
            fields_with_values.append((field, str(value)))
    
    if fields_with_values:
        print(f"✅ {len(fields_with_values)} campos extraídos:")
        for field, value in fields_with_values:
            print(f"  - {field}: {value[:80]}{'...' if len(value) > 80 else ''}")
    else:
        print("❌ Nenhum campo extraído com sucesso")
    
    return result

def main():
    """Função principal."""
    if len(sys.argv) != 2:
        print("Uso: python test_single_pdf.py <caminho_do_pdf>")
        print("Exemplo: python test_single_pdf.py /path/to/document.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"❌ Arquivo não encontrado: {pdf_path}")
        sys.exit(1)
    
    if not pdf_path.lower().endswith('.pdf'):
        print(f"❌ Arquivo não é um PDF: {pdf_path}")
        sys.exit(1)
    
    try:
        result = test_single_pdf(pdf_path)
        print("\n🎉 Teste concluído com sucesso!")
    except Exception as e:
        print(f"❌ Erro durante o teste: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

