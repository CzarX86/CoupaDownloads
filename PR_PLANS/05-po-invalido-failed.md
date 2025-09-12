# PR 5 — STATUS de PO inválido padronizado (FAILED + mensagem)

Objetivo
- Quando PO for inválido, gravar `STATUS='FAILED'` (maiúsculo), `ERROR_MESSAGE='Invalid PO format'` e `COUPA_URL` calculada.

Escopo
- Arquivo: `src/core/excel_processor.py`

Arquivos afetados
- `src/core/excel_processor.py`

Pseudodiff (referencial)
```
*** Update File: src/core/excel_processor.py
@@ def process_po_numbers(...):
- ExcelProcessor.update_po_status(po_number, 'FAILED', error_message='Invalid PO format', coupa_url=invalid_url)
+ ExcelProcessor.update_po_status(
+   po_number=po_number,
+   status='FAILED',
+   error_message='Invalid PO format',
+   coupa_url=invalid_url,
+ )
```

Critérios de aceitação
- CSV reflete FAILED em maiúsculo com mensagem consistente para POs inválidos.

Teste manual
- Incluir um PO malformado; rodar e validar a linha no CSV.

Mensagem de commit sugerida
- `fix(csv): set FAILED and message for invalid PO format`

Branch sugerido
- `fix/invalid-po-failed`

