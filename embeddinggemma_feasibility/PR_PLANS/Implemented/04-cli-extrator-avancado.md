# PR 04 — CLI: extrator avançado + CSV alinhado (embeddinggemma_feasibility)

## Objetivo
Adicionar opção no menu interativo (`interactive_cli.py`) para executar o extrator avançado com parâmetros básicos (pasta de PDFs, saída), e alinhar a escrita de CSV do extrator às regras de IO do repo (UTF‑8 BOM, `lineterminator="\n"`, `csv.QUOTE_MINIMAL`) sem mudar colunas.

## Escopo
- CLI: nova opção "Executar Extrator Avançado" com prompts simples (diretório dos PDFs, pasta de saída de relatórios, ativar/desativar OCR conforme libs disponíveis).
- Extrator avançado: ajustar escrita do CSV para seguir SOP do repo; manter cabeçalhos e ordem de colunas.
- Atualizar doc de uso com a nova opção.

## Arquivos afetados
- Alterado: `embeddinggemma_feasibility/interactive_cli.py` (nova opção de menu)
- Alterado: `embeddinggemma_feasibility/advanced_coupa_field_extractor.py` (parâmetros de escrita do CSV)
- Alterado: `embeddinggemma_feasibility/docs/RAG_MINIMAL.md` (nota de como executar pelo menu)

## Pseudodiff (representativo)
```
~ embeddinggemma_feasibility/interactive_cli.py
+   print("4) Executar Extrator Avançado")
+   elif choice == "4":
+       # perguntar pdf_dir e dir de saída; chamar process_all_pdfs e save_to_csv

~ embeddinggemma_feasibility/advanced_coupa_field_extractor.py
- with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
+ with open(output_path, 'w', newline='\n', encoding='utf-8-sig') as csvfile:
+     writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)

~ embeddinggemma_feasibility/docs/RAG_MINIMAL.md
+ ## Run advanced extractor from the interactive menu
```

## Critérios de aceitação
- CLI mostra a opção do extrator avançado e executa ponta‑a‑ponta gerando CSV e relatório.
- CSV gerado abre corretamente no Excel sem problemas de acentuação e com quebras de linha corretas.
- Nenhuma alteração de semântica das colunas.

## Testes manuais
1) `poetry run python -m embeddinggemma_feasibility.interactive_cli` → opção 4 disponível.
2) Informar `embeddinggemma_feasibility/data/sample_documents` (ou pasta real de PDFs) → CSV em `embeddinggemma_feasibility/reports/`.
3) Abrir CSV no Excel e validar conteúdo.

## Mensagem + branch sugeridos
- Branch (plan): `plan/04-cli-extrator-avancado`
- Commit (plan): `docs(pr-plan): PR 04 — CLI: extrator avançado + CSV alinhado`
- Branch (impl): `feat/04-cli-extrator-avancado`
- Commit (impl): `feat(rag-cli): PR 04 — menu: extrator avançado + CSV alinhado`
