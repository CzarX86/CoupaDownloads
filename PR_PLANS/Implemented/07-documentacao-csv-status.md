# PR 7 — Documentação (STATUS unificado + formato CSV/Excel)

Objetivo
- Atualizar documentação para refletir o STATUS unificado, colunas preenchidas e o entrypoint atual (`src/Core_main.py`).

Escopo
- Atualizar `THREAD_IMPLEMENTATION_REPORT.md` (seções de CSV, orquestração e fluxo) e `README.md` (como executar, arquivo de entrada, colunas/gravação).

Arquivos afetados
- `THREAD_IMPLEMENTATION_REPORT.md`
- `README.md`

Pseudodiff (referencial)
```
*** Update File: THREAD_IMPLEMENTATION_REPORT.md
@@ Overview of Key Themes
- Post‑download folder renaming with standardized status suffixes.
+ Post‑download folder renaming with standardized status suffixes (COMPLETED/FAILED/NO_ATTACHMENTS/PARTIAL).
@@ Core: Excel/CSV Processing
- Status updates in CSV are safe:
+ Status updates in CSV are safe and unified:
   - Case/whitespace‑insensitive lookup for PO_NUMBER.
   - Dtype normalization (string/int) e escrita com BOM/delimitador preservado.
+  - Campos gravados: SUPPLIER, ATTACHMENTS_FOUND, ATTACHMENTS_DOWNLOADED, AttachmentName, LAST_PROCESSED, ERROR_MESSAGE, DOWNLOAD_FOLDER, COUPA_URL.
@@ Main Application Orchestration
- File: `src/main.py`
+ File: `src/Core_main.py`
@@ Derivation and status
+ STATUS derivation unified via `_derive_status_label(success, message)`:
+ - COMPLETED quando todos baixados; PARTIAL quando X/Y; NO_ATTACHMENTS quando 0 ou mensagem; FAILED em erros.
+ Folder rename aplica sufixos: `_COMPLETED`, `_FAILED`, `_NO_ATTACHMENTS`, `_PARTIAL`.

*** Update File: README.md
@@ Quick Start / Run the Application
- python src\main.py
+ python -m src.Core_main
@@ Input file format
+ CSV/Excel columns suportados: PO_NUMBER, STATUS, SUPPLIER, ATTACHMENTS_FOUND, ATTACHMENTS_DOWNLOADED, AttachmentName, LAST_PROCESSED, ERROR_MESSAGE, DOWNLOAD_FOLDER, COUPA_URL. O sistema preenche/atualiza quando disponíveis.
```

Critérios de aceitação
- Documento “Thread” e README ficam consistentes com o código atual (entrypoint `src/Core_main.py`, STATUS unificado e colunas preenchidas).

Teste manual
- Leitura rápida dos arquivos renderizados, checando seções alteradas e exemplos de execução.

Mensagem de commit sugerida
- `docs: PR 07 — CSV/Excel format and unified status (Core_main entrypoint)`

Branch sugerido
- `docs/07-csv-format-and-status`

Checklist
- [x] Objetivo e Escopo claros e limitados
- [x] Arquivos afetados listados
- [x] Pseudodiff pequeno e representativo
- [x] Critérios de aceitação e testes manuais
- [x] Mensagem de commit e branch

