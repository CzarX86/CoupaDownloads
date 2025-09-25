# Fluxo de Anotação em PDF

> ⚠️ **Este fluxo está descontinuado.** O módulo de treinamento agora grava as
> correções diretamente no banco de dados, exibindo os PDFs no componente
> `PdfViewer` do SPA. Mantenha este arquivo apenas como referência histórica;
> novas importações devem acontecer exclusivamente via upload de PDFs na
> interface ou pela API `/api/pdf-training/documents`.

## Alternativa suportada

1. Abra o SPA (`./start_spa.sh` ou `start_spa.bat`) e selecione o documento na
   tabela. O PDF será renderizado na própria aplicação e os campos podem ser
   atualizados pelo painel de anotações.
2. Os dados revisados são persistidos em `annotations.latest_payload`. Use os
   endpoints `/api/pdf-training/documents/{id}/entities` ou
   `/api/pdf-training/training-runs/{id}/dataset` para integrar com outras
   ferramentas.

Para instruções completas sobre o novo fluxo, consulte
`docs/HITL_FEEDBACK_WORKFLOW.md`.
