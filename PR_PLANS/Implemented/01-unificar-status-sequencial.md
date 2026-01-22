# PR 1 — Unificar STATUS no modo sequencial

Objetivo
- Substituir “Success/Error” por derivação única via `_derive_status_label(success, message)` no fluxo sequencial.

Escopo
- Arquivo: `src/main.py`
- Função: `process_single_po`

Arquivos afetados
- `src/main.py`

Pseudodiff (referencial)
```
*** Update File: src/main.py
@@ def process_single_po(...):
- final_status = "Success" if success else "Error"
+ final_status = _derive_status_label(success, message)  # COMPLETED/FAILED/NO_ATTACHMENTS/PARTIAL

- final_folder = self._rename_folder_with_status(folder_path, final_status)
+ final_folder = _rename_folder_with_status(folder_path, final_status)

- self.excel_processor.update_po_status(display_po, final_status, error_message=message, download_folder=final_folder)
+ self.excel_processor.update_po_status(display_po, final_status, error_message=message, download_folder=final_folder)
```

Critérios de aceitação
- CSV sempre grava STATUS em {COMPLETED, FAILED, NO_ATTACHMENTS, PARTIAL} no modo sequencial.
- Sufixo da pasta segue o STATUS padronizado.

Teste manual
- Rodar em modo sequencial (USE_PROCESS_POOL=false) com 1 PO sem anexos e 1 com anexos; validar STATUS e sufixo.

Mensagem de commit sugerida
- `feat: unify STATUS in sequential mode using derive_status_label`

Branch sugerido
- `feat/unify-status-seq`

