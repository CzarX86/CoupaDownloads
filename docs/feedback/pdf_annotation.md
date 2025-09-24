# Fluxo de Anotação em PDF

> ⚠️ **Este fluxo está descontinuado.** O módulo de treinamento agora grava as
> correções diretamente no banco de dados, exibindo os PDFs no componente
> `PdfViewer` do SPA. Mantenha este arquivo apenas como referência histórica e
> utilize o script `scripts/migrate_review_csv.py` para importar planilhas
> antigas antes de seguir pelo wizard web.

## Alternativa suportada

1. Execute `poetry run python scripts/migrate_review_csv.py --training-run <nome> '<glob>'`
   para carregar os dados legados.
2. Abra o SPA (`./start_spa.sh` ou `start_spa.bat`) e selecione o documento na
   tabela. O PDF será renderizado na própria aplicação e os campos podem ser
   atualizados pelo painel de anotações.
3. Os dados revisados são persistidos em `annotations.latest_payload`. Use os
   endpoints `/api/pdf-training/documents/{id}/entities` ou
   `/api/pdf-training/training-runs/{id}/dataset` para integrar com outras
   ferramentas.

Para instruções completas sobre o novo fluxo, consulte
`docs/HITL_FEEDBACK_WORKFLOW.md`.
