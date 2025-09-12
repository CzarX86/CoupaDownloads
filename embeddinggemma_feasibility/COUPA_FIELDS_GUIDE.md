# Coupa Field Extraction - Usage Guide

## 📄 Extração de Campos Específicos do Coupa

Este módulo extrai os 22 campos específicos solicitados dos PDFs e gera um arquivo CSV estruturado.

### 🎯 Campos Extraídos

| #   | Campo                                | Descrição                   | Exemplo                             |
| --- | ------------------------------------ | --------------------------- | ----------------------------------- |
| 1   | **Remarks**                          | Observações gerais          | "Contract renewal required"         |
| 2   | **Supporting Information**           | Informações de apoio        | "Technical specifications included" |
| 3   | **Procurement Negotiation Strategy** | Estratégia de negociação    | "Multi-vendor approach"             |
| 4   | **Opportunity Available**            | Oportunidade disponível     | Yes/No                              |
| 5   | **Inflation %**                      | Percentual de inflação      | 3.5%                                |
| 6   | **Minimum Commitment Value**         | Valor mínimo de compromisso | €50,000                             |
| 7   | **Contractual Commercial Model**     | Modelo comercial contratual | Fixed/Consumption                   |
| 8   | **User Based License**               | Licença baseada em usuário  | Yes/No                              |
| 9   | **Type of Contract - L2**            | Tipo de contrato L2         | Software License                    |
| 10  | **Type of Contract - L1**            | Tipo de contrato L1         | IT Services                         |
| 11  | **SOW Value in EUR**                 | Valor SOW em EUR            | €125,000                            |
| 12  | **FX**                               | Taxa de câmbio              | 1.15                                |
| 13  | **SOW Currency**                     | Moeda SOW                   | EUR                                 |
| 14  | **SOW Value in LC**                  | Valor SOW em moeda local    | $150,000                            |
| 15  | **Managed By**                       | Gerenciado por              | VMO/SL/SAM/Business                 |
| 16  | **Contract End Date**                | Data de fim do contrato     | 31/12/2024                          |
| 17  | **Contract Start Date**              | Data de início do contrato  | 01/01/2024                          |
| 18  | **Contract Type**                    | Tipo de contrato            | SOW/CR/Subs Order form              |
| 19  | **Contract Name**                    | Nome do contrato            | "Microsoft Office License"          |
| 20  | **High Level Scope**                 | Escopo de alto nível        | "Software licensing and support"    |
| 21  | **Platform/Technology**              | Plataforma/Tecnologia       | "Microsoft 365"                     |
| 22  | **PWO#**                             | Número PWO                  | 12345                               |

### 🚀 Quick Start

```bash
cd src/MyScript/embeddinggemma_feasibility
python extract_coupa_fields.py
```

### 📊 Arquivo CSV Gerado

O sistema gera um arquivo CSV com as seguintes colunas:

```csv
Source File,Remarks,Supporting Information,Procurement Negotiation Strategy,Opportunity Available,Inflation %,Minimum Commitment Value,Contractual Commercial Model,User Based License,Type of Contract - L2,Type of Contract - L1,SOW Value in EUR,FX,SOW Currency,SOW Value in LC,Managed By,Contract End Date,Contract Start Date,Contract Type,Contract Name,High Level Scope,Platform/Technology,PWO#,Extraction Confidence,Extraction Method
document1.pdf,"Contract renewal required","Technical specs included","Multi-vendor approach",Yes,3.5%,€50000,Fixed,Yes,Software License,IT Services,€125000,1.15,EUR,$150000,VMO,31/12/2024,01/01/2024,SOW,Microsoft Office License,Software licensing,Microsoft 365,12345,0.85,regex_patterns
```

### 🔍 Métodos de Extração

#### 1. **Padrões Regex**

- Busca por padrões específicos no texto
- Reconhece formatos comuns (datas, valores, etc.)
- Case-insensitive para maior flexibilidade

#### 2. **Análise Semântica** (Opcional)

- Usa EmbeddingGemma para contexto
- Melhora precisão em textos complexos
- Identifica campos mesmo com variações de formato

### 📈 Métricas de Qualidade

#### **Confiança da Extração**

- **0.0-0.3**: Baixa confiança - poucos campos encontrados
- **0.3-0.6**: Confiança média - alguns campos encontrados
- **0.6-1.0**: Alta confiança - maioria dos campos encontrados

#### **Estatísticas Geradas**

- Total de documentos processados
- Campos encontrados por documento
- Taxa de sucesso por campo
- Confiança média da extração

### 🛠️ Configuração Avançada

#### **Personalizar Padrões Regex**

```python
# Exemplo: adicionar novo padrão para um campo
extractor.field_patterns["contract_name"].append(
    r"agreement\s+title\s*:?\s*(.+?)(?:\n|$)"
)
```

#### **Ajustar Sensibilidade**

```python
# Tornar busca mais restritiva
pattern = r"contract\s+name\s*:?\s*(.+?)(?:\n|$)"  # Mais específico

# Tornar busca mais flexível
pattern = r".*contract.*name.*:?\s*(.+?)(?:\n|$)"  # Mais flexível
```

### 📋 Relatório Gerado

O sistema gera um relatório Markdown com:

#### **Resumo Geral**

- Documentos processados
- Campos extraídos
- Confiança média

#### **Estatísticas por Campo**

- Taxa de sucesso por campo
- Documentos com cada campo encontrado

#### **Detalhes por Documento**

- Campos encontrados em cada PDF
- Confiança da extração
- Método utilizado

### 🔧 Troubleshooting

#### **Problemas Comuns**

1. **"Nenhum campo encontrado"**

   - Verifique se o PDF contém texto legível
   - Teste com PDFs diferentes
   - Ajuste os padrões regex se necessário

2. **"Confiança baixa"**

   - PDFs podem ter formato não padrão
   - Considere usar OCR para PDFs escaneados
   - Revise os padrões regex

3. **"Campos incorretos"**
   - Ajuste os padrões regex
   - Use análise semântica com EmbeddingGemma
   - Revise manualmente os resultados

### 📊 Exemplo de Saída

```
📄 Extrator de Campos Específicos do Coupa
============================================================
📁 Diretório dos PDFs: /Users/juliocezar/Dev/work/CoupaDownloads/src/data/P2
🔧 Inicializando extrator de campos específicos...
📄 Encontrados 5 arquivos PDF:
  - contract_001.pdf
  - contract_002.pdf
  - contract_003.pdf
  - contract_004.pdf
  - contract_005.pdf

🚀 Iniciando extração de campos específicos...
📄 Processando 1/5: contract_001.pdf
✅ Processado: contract_001.pdf (confiança: 0.85)
📄 Processando 2/5: contract_002.pdf
✅ Processado: contract_002.pdf (confiança: 0.72)
...

✅ Processamento concluído com sucesso!
📊 Documentos processados: 5
📈 Confiança média da extração: 0.78
💾 CSV salvo em: reports/coupa_fields_extraction_20241201_143022.csv
📋 Relatório salvo em: reports/coupa_fields_extraction_20241201_143022_report.md

🔍 Campos mais encontrados:
  - Contract Name: 5 documentos
  - Contract Type: 4 documentos
  - Contract Start Date: 4 documentos
  - Contract End Date: 4 documentos
  - SOW Value in EUR: 3 documentos
  - Managed By: 3 documentos
  - Platform/Technology: 2 documentos
  - PWO#: 2 documentos
  - High Level Scope: 2 documentos
  - Remarks: 1 documento

📋 Exemplos de campos extraídos:

1. contract_001.pdf
   Contract Name: Microsoft Office License Agreement
   Contract Type: SOW
   Contract Start Date: 01/01/2024

2. contract_002.pdf
   Contract Name: AWS Cloud Services Contract
   Contract Type: CR
   SOW Value in EUR: €125,000

3. contract_003.pdf
   Contract Name: SAP Software License
   Contract Type: Subs Order form
   Managed By: VMO

📊 Resumo dos campos extraídos:
   Total de campos disponíveis: 22
   Documentos com pelo menos 1 campo: 5
   Documentos com alta confiança (>0.5): 4
```

### 🎯 Casos de Uso

#### **1. Análise de Contratos**

- Extrair informações padronizadas
- Comparar termos entre contratos
- Identificar campos obrigatórios

#### **2. Relatórios Executivos**

- Consolidar dados de múltiplos contratos
- Análise de valores e datas
- Identificar tendências

#### **3. Compliance**

- Verificar campos obrigatórios
- Identificar contratos incompletos
- Auditoria de dados

### 🔄 Integração com MyScript

```python
# Exemplo de integração
from coupa_field_extractor import CoupaPDFFieldExtractor

def process_coupa_contracts():
    extractor = CoupaPDFFieldExtractor()
    extractions = extractor.process_all_pdfs()

    # Salvar CSV
    csv_file = extractor.save_to_csv(extractions)

    # Integrar com sistema existente
    for extraction in extractions:
        # Processar cada contrato
        process_contract_data(extraction)

        # Atualizar base de dados
        update_contract_database(extraction)
```

### 📝 Próximos Passos

1. **Adicione PDFs** na pasta `src/data/P2`
2. **Execute**: `python extract_coupa_fields.py`
3. **Analise o CSV** gerado
4. **Revise o relatório** para entender a qualidade da extração
5. **Ajuste padrões** se necessário para melhorar precisão

---

**Nota**: Este módulo é otimizado especificamente para os 22 campos solicitados e gera um CSV estruturado pronto para uso.
