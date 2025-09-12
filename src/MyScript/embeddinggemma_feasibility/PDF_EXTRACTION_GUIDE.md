# PDF Information Extraction - Usage Guide

## 📄 Extração de Informações de PDFs com EmbeddingGemma

Este módulo permite extrair informações estruturadas de documentos PDF usando EmbeddingGemma para análise semântica e categorização.

### 🚀 Quick Start

```bash
cd src/MyScript/embeddinggemma_feasibility
python extract_pdf_info.py
```

### 📁 Estrutura de Arquivos

```
src/MyScript/embeddinggemma_feasibility/
├── pdf_information_extractor.py    # Extrator principal
├── extract_pdf_info.py             # Script simplificado
├── requirements.txt                # Dependências (inclui PDF)
└── reports/                        # Resultados salvos aqui
```

### 🔧 Funcionalidades

#### 1. **Extração de Texto**

- **pdfplumber**: Melhor para PDFs com texto
- **PyPDF2**: Fallback para PDFs simples
- **OCR (Tesseract)**: Para PDFs escaneados

#### 2. **Análise Semântica**

- **EmbeddingGemma**: Geração de embeddings
- **Categorização**: Classificação automática
- **Extração de entidades**: Datas, valores, números

#### 3. **Informações Extraídas**

- **Frases-chave**: Termos importantes
- **Entidades**: Datas, valores monetários, números de PO
- **Categorias**: Purchase Order, Invoice, Contract, etc.
- **Resumo**: Resumo automático do conteúdo
- **Score de relevância**: Importância do documento

### 📊 Tipos de Documentos Suportados

| Tipo               | Palavras-chave                | Exemplos                |
| ------------------ | ----------------------------- | ----------------------- |
| **Purchase Order** | PO, Purchase Order, Compra    | Pedidos de compra       |
| **Invoice**        | Invoice, Fatura, Bill         | Faturas e recibos       |
| **Contract**       | Contract, Contrato, Agreement | Contratos e acordos     |
| **Technical Spec** | Specification, Technical      | Especificações técnicas |
| **Report**         | Report, Relatório, Analysis   | Relatórios e análises   |

### 🎯 Exemplo de Uso

```python
from pdf_information_extractor import PDFInformationExtractor

# Criar extrator
extractor = PDFInformationExtractor("/path/to/pdfs")

# Processar todos os PDFs
result = extractor.process_all_pdfs()

# Salvar resultados
output_file = extractor.save_results(result)
print(f"Resultados salvos em: {output_file}")
```

### 📈 Resultados Gerados

#### 1. **Arquivo JSON** (`pdf_extraction_YYYYMMDD_HHMMSS.json`)

```json
{
  "success": true,
  "documents_processed": 5,
  "total_processing_time": 12.34,
  "extracted_info": [
    {
      "document": {
        "filename": "PO_12345.pdf",
        "file_size": 245760,
        "page_count": 3,
        "text_content": "Purchase Order #12345..."
      },
      "key_phrases": ["PO Number", "Vendor", "Amount"],
      "entities": {
        "dates": ["2024-01-15", "2024-02-01"],
        "amounts": ["$1,250.00", "R$ 5,000.00"],
        "numbers": ["PO #12345", "Contract #789"]
      },
      "summary": "Purchase Order for office supplies...",
      "categories": ["Purchase Order"],
      "relevance_score": 0.85,
      "embedding": [0.1, 0.2, 0.3, ...]
    }
  ],
  "statistics": {
    "total_documents": 5,
    "total_pages": 15,
    "average_relevance_score": 0.78,
    "category_distribution": {
      "Purchase Order": 3,
      "Invoice": 2
    }
  }
}
```

#### 2. **Relatório Markdown** (`pdf_extraction_YYYYMMDD_HHMMSS_report.md`)

```markdown
# Relatório de Extração de Informações de PDFs

## Resumo Geral

- **Documentos processados**: 5
- **Tempo total**: 12.34 segundos
- **Taxa de sucesso**: 100.0%

## Estatísticas

- **Total de páginas**: 15
- **Comprimento médio do texto**: 2,450 caracteres
- **Score médio de relevância**: 0.78

### Distribuição por Categoria

- **Purchase Order**: 3 documentos
- **Invoice**: 2 documentos

## Documentos Processados

### 1. PO_12345.pdf

- **Categorias**: Purchase Order
- **Score de relevância**: 0.85
- **Páginas**: 3
- **Frases-chave**: PO Number, Vendor, Amount
- **Resumo**: Purchase Order for office supplies...
```

### 🔍 Informações Extraídas

#### **Entidades Detectadas**

- **Datas**: `2024-01-15`, `15/01/2024`, `January 15, 2024`
- **Valores**: `$1,250.00`, `R$ 5,000.00`, `€2,500.00`
- **Números**: `PO #12345`, `Contract #789`, `Invoice #456`
- **Empresas**: Nomes de fornecedores e contratantes

#### **Categorização Automática**

- **Purchase Order**: Documentos de pedidos de compra
- **Invoice**: Faturas e recibos
- **Contract**: Contratos e acordos
- **Technical Specification**: Especificações técnicas
- **Report**: Relatórios e análises

#### **Análise Semântica**

- **Embeddings**: Vetores semânticos para cada documento
- **Similaridade**: Comparação entre documentos
- **Relevância**: Score de importância do conteúdo

### ⚙️ Configuração

#### **Dependências Necessárias**

```bash
# PDF Processing
pip install PyPDF2 pdfplumber

# OCR (opcional)
pip install pytesseract Pillow PyMuPDF

# ML Libraries
pip install sentence-transformers torch numpy scikit-learn
```

#### **Configuração do Tesseract (OCR)**

```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

### 🛠️ Troubleshooting

#### **Problemas Comuns**

1. **"Bibliotecas de PDF não disponíveis"**

   ```bash
   pip install PyPDF2 pdfplumber
   ```

2. **"Erro ao extrair texto"**

   - Verifique se o PDF não está corrompido
   - Tente com PDFs diferentes
   - Para PDFs escaneados, instale OCR

3. **"Modelo EmbeddingGemma não carregado"**

   ```bash
   pip install sentence-transformers torch
   ```

4. **"OCR não funciona"**
   - Instale Tesseract no sistema
   - Verifique se pytesseract está instalado

### 📊 Métricas de Performance

#### **Benchmarks Típicos**

- **PDFs com texto**: 2-5 segundos por documento
- **PDFs escaneados**: 10-30 segundos por documento
- **Memória**: 150-300MB (com EmbeddingGemma)
- **Precisão**: 85-95% para documentos bem estruturados

#### **Fatores que Afetam Performance**

- **Tamanho do PDF**: Mais páginas = mais tempo
- **Qualidade do texto**: PDFs escaneados são mais lentos
- **Complexidade**: Documentos com tabelas são mais difíceis
- **Hardware**: CPU e RAM disponíveis

### 🎯 Casos de Uso

#### **1. Análise de Contratos**

- Extrair datas importantes
- Identificar partes envolvidas
- Categorizar tipos de contrato

#### **2. Processamento de Faturas**

- Extrair valores e datas de vencimento
- Identificar fornecedores
- Categorizar por tipo de despesa

#### **3. Gestão de POs**

- Detectar duplicatas
- Extrair informações de entrega
- Categorizar por tipo de produto

#### **4. Relatórios Financeiros**

- Extrair métricas importantes
- Identificar tendências
- Categorizar por período

### 🔄 Integração com MyScript

O extrator pode ser facilmente integrado ao sistema MyScript existente:

```python
# Exemplo de integração
from pdf_information_extractor import PDFInformationExtractor

def process_coupa_documents():
    extractor = PDFInformationExtractor()
    result = extractor.process_all_pdfs()

    # Integrar com sistema existente
    for info in result.extracted_info:
        # Salvar no CSV do MyScript
        save_to_myscript_csv(info)

        # Processar com workflow existente
        process_with_existing_workflow(info)
```

### 📝 Próximos Passos

1. **Adicione PDFs** na pasta `src/data/P2`
2. **Execute o extrator**: `python extract_pdf_info.py`
3. **Analise os resultados** nos arquivos gerados
4. **Integre com MyScript** conforme necessário

---

**Nota**: Este módulo é completamente isolado e não afeta o sistema MyScript principal.
