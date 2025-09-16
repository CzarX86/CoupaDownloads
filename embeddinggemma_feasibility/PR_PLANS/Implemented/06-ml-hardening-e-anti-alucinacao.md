# PR 06 — Hardening de ML/OCR/Parsing e anti‑alucinação (embeddinggemma_feasibility)

## Objetivo
Elevar a qualidade e a confiabilidade do pipeline com bibliotecas auxiliares e validações determinísticas, reduzindo erros e prevenindo “alucinações” quando técnicas ML são usadas.

## Escopo
- Dependências opcionais a adicionar (documentadas como opt‑in):
  - `rapidfuzz>=3.0.0` — fuzzy matching rápido para normalizar nomes/campos.
  - `dateparser>=1.2.0` — parsing de datas multi‑idioma e formatos irregulares.
  - `python-magic>=0.4.27` — detecção de tipo de arquivo (PDF vs imagem) para roteamento OCR.
  - `camelot-py[cv]>=0.11.0` (opcional) — extração de tabelas de PDFs; requer Ghostscript.
  - (já presente) `pydantic` — reforçar validações dos modelos de saída.
- Validações por campo no extrator avançado:
  - Datas: normalização via `dateparser` + regex de formatos aceitos.
  - Valores: coerência entre SOW EUR, FX e SOW LC.
  - Fornecedor: aproximação via `rapidfuzz` com lista conhecida (quando disponível).
- Logging estruturado (explicar por que um valor foi aceito/rejeitado) e modo “strict” que falha quando validações essenciais não passam.
- CLI: flags para ligar/desligar validações extras.

## Arquivos afetados
- Alterado: `embeddinggemma_feasibility/advanced_coupa_field_extractor.py` (helpers de validação e chamadas)
- Alterado: `embeddinggemma_feasibility/requirements.txt` (acrescentar libs opcionais)
- Alterado: `embeddinggemma_feasibility/interactive_cli.py` (flags para validações extras)
- Alterado: docs (listar dependências opcionais e requisitos, ex.: Ghostscript para Camelot)
