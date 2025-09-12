# PR 3 — Propagar campos do Downloader para gravação no CSV

Objetivo
- Usar o retorno enriquecido para preencher colunas do CSV e derivar STATUS de forma unificada (sequencial e worker).

Escopo
- Arquivo: `src/main.py`

Arquivos afetados
- `src/main.py`

Pseudodiff (referencial)
```
*** Update File: src/main.py
@@ def process_single_po(...):
- result = downloader.download_attachments_for_po(po_number)
- success = result.success
- message = result.message
- status_code = _derive_status_label(success, message)
- final_folder = _rename_folder_with_status(folder_path, status_code)
- formatted_names = self.folder_hierarchy.format_attachment_names(result.attachment_names)
- self.excel_processor.update_po_status(
-   po_number=display_po,
-   status=status_code,
-   supplier=result.supplier_name,
-   attachments_found=result.attachments_found,
-   attachments_downloaded=result.attachments_downloaded,
-   error_message=message,
-   download_folder=final_folder,
-   coupa_url=result.coupa_url,
-   attachment_names=formatted_names,
- )
```
- Worker → incluir os mesmos campos no `result` do worker e, no pai, repassar para `update_po_status(...)` com formatação de nomes via `FolderHierarchyManager.format_attachment_names`.

Critérios de aceitação
- CSV passa a ter SUPPLIER, ATTACHMENTS_FOUND, ATTACHMENTS_DOWNLOADED, AttachmentName, COUPA_URL populados quando disponíveis.

Teste manual
- Sequencial e worker (1 processo) com 1–2 POs; verificar preenchimento no CSV e sufixo da pasta.

Mensagem de commit sugerida
- `feat(main): propagate downloader result to CSV (supplier, counts, names, url)`

Branch sugerido
- `feat/propagate-to-csv`

