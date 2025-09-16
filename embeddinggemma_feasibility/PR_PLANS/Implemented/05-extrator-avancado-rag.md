# PR 05 — Extrator avançado com RAG assistido (embeddinggemma_feasibility)

## Objetivo
Melhorar precisão e robustez do `advanced_coupa_field_extractor.py` adicionando um modo opcional de RAG assistido: recuperar trechos candidatos por campo crítico e aplicar regras/NER sobre esses trechos.

## Escopo
- Novo módulo auxiliar `rag_assisted_extraction.py` com:
  - Build/load de índice (por páginas/trechos) temporário por PDF (HNSW, local).
  - Queries por campo (p.ex., datas de contrato, SOW values, PWO) mapeadas para prompts/keywords.
  - API simples: `retrieve_candidates(pdf_path, field_key, top_k=6)` retornando trechos + metadados.
- `advanced_coupa_field_extractor.py` passa a aceitar `use_rag: bool` para ligar esse fluxo.
- `interactive_cli.py`: flag "Usar RAG" ao rodar o extrator avançado.
- Padrão continua `use_rag=False` (não regressão).

## Arquivos afetados
- Adicionado: `embeddinggemma_feasibility/rag_assisted_extraction.py`
- Alterado: `embeddinggemma_feasibility/advanced_coupa_field_extractor.py` (gate `use_rag` + integração)
- Alterado: `embeddinggemma_feasibility/interactive_cli.py` (perguntar `use_rag`)

## Critérios de aceitação
- `use_rag=False`: resultados idênticos ao extrator atual (compatibilidade garantida).
- `use_rag=True`: redução de ruído e melhoria de precisão em campos críticos em PDFs longos; logs mostram quantos trechos foram avaliados.
- CSV/relatório finais inalterados em estrutura.
