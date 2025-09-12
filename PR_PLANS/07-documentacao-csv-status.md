# PR 7 — Documentação (STATUS unificado + Formato do CSV)

Objetivo
- Atualizar documentação com unificação de STATUS e colunas gravadas no CSV.

Escopo
- Arquivos: `THREAD_IMPLEMENTATION_REPORT.md` (+ opcional `README.md`)

Pseudodiff (referencial)
```
*** Update File: THREAD_IMPLEMENTATION_REPORT.md
@@ CSV behavior
- STATUS differed by mode
+ STATUS is unified across modes: COMPLETED, FAILED, NO_ATTACHMENTS, PARTIAL
+ CSV columns filled: SUPPLIER, ATTACHMENTS_FOUND, ATTACHMENTS_DOWNLOADED, AttachmentName, COUPA_URL, LAST_PROCESSED, ERROR_MESSAGE, DOWNLOAD_FOLDER
```

Critérios de aceitação
- Report e README refletem o comportamento real do sistema.

Mensagem de commit sugerida
- `docs: update thread report and CSV format section`

Branch sugerido
- `docs/csv-format`

