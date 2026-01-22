# PR 3 — Propagar campos do Downloader para gravação no CSV

Objetivo
- Usar o retorno enriquecido do Downloader para preencher colunas do CSV/Excel e derivar STATUS de forma unificada tanto no fluxo sequencial quanto no de workers.

Escopo
- Adaptar ao estado atual do projeto (runner em `src/Core_main.py`).
- Enriquecer o retorno de `Downloader.download_attachments_for_po` (dict com campos), sem alterar arquitetura.

Arquivos afetados
- `src/Core_main.py`
- `src/core/downloader.py`

Pseudodiff (referencial)
```
*** Update File: src/core/downloader.py
@@ class Downloader
-    def download_attachments_for_po(self, po_number: str) -> Tuple[bool, str]:
+    def download_attachments_for_po(self, po_number: str) -> dict:
         # ...
         url = f"{Config.BASE_URL}/order_headers/{order_number}"
         self.driver.get(url)
         # ... localizar anexos, tentar downloads, contar, coletar nomes
+        supplier = self._extract_supplier_name()  # novo helper resiliente
         if not attachments:
             msg = "No attachments found."
             return {
                 'success': True,
                 'message': msg,
+                'supplier_name': supplier or '',
                 'attachments_found': 0,
                 'attachments_downloaded': 0,
                 'coupa_url': url,
                 'attachment_names': [],
             }
         # ... após o loop
         if downloaded_count > 0:
             msg = f"Initiated download for {downloaded_count}/{total_attachments} attachments."
             return {
                 'success': True,
                 'message': msg,
+                'supplier_name': supplier or '',
                 'attachments_found': total_attachments,
                 'attachments_downloaded': downloaded_count,
                 'coupa_url': url,
                 'attachment_names': names_list,
             }
         else:
             msg = f"Failed to download any of the {total_attachments} attachments."
             return {
                 'success': False,
                 'message': msg,
+                'supplier_name': supplier or '',
                 'attachments_found': total_attachments,
                 'attachments_downloaded': 0,
                 'coupa_url': url,
                 'attachment_names': names_list,
             }

*** Update File: src/Core_main.py
@@ def process_single_po(...):
-                success, message = downloader.download_attachments_for_po(po_number)
+                result = downloader.download_attachments_for_po(po_number)
+                success = result['success']
+                message = result['message']
                 # ... wait, derive status and rename
                 status_code = _derive_status_label(success, message)
                 final_folder = _rename_folder_with_status(folder_path, status_code)
-                self.excel_processor.update_po_status(
-                    display_po,
-                    status_code,
-                    error_message=message,
-                    download_folder=final_folder
-                )
+                formatted_names = self.folder_hierarchy.format_attachment_names(result['attachment_names'])
+                self.excel_processor.update_po_status(
+                    display_po,
+                    status_code,
+                    supplier=result['supplier_name'],
+                    attachments_found=result['attachments_found'],
+                    attachments_downloaded=result['attachments_downloaded'],
+                    error_message=message,
+                    download_folder=final_folder,
+                    coupa_url=result['coupa_url'],
+                    attachment_names=formatted_names,
+                )

@@ def process_po_worker(args):
-        success, message = downloader.download_attachments_for_po(po_number)
+        result = downloader.download_attachments_for_po(po_number)
+        success = result['success']
+        message = result['message']
         status_code = _derive_status_label(success, message)
         final_folder = _rename_folder_with_status(folder_path, status_code)
         return {
             'po_number_display': display_po,
             'status_code': status_code,
             'message': message,
             'final_folder': final_folder,
+            'supplier_name': result['supplier_name'],
+            'attachments_found': result['attachments_found'],
+            'attachments_downloaded': result['attachments_downloaded'],
+            'coupa_url': result['coupa_url'],
+            'attachment_names': result['attachment_names'],
         }

@@ in parent loop of process pool
-                    self.excel_processor.update_po_status(
-                        display_po,
-                        status_code,
-                        error_message=message,
-                        download_folder=final_folder,
-                    )
+                    formatted_names = self.folder_hierarchy.format_attachment_names(result['attachment_names'])
+                    self.excel_processor.update_po_status(
+                        display_po,
+                        status_code,
+                        supplier=result['supplier_name'],
+                        attachments_found=result['attachments_found'],
+                        attachments_downloaded=result['attachments_downloaded'],
+                        error_message=message,
+                        download_folder=final_folder,
+                        coupa_url=result['coupa_url'],
+                        attachment_names=formatted_names,
+                    )
```

Critérios de aceitação
- CSV/Excel passam a ter SUPPLIER, ATTACHMENTS_FOUND, ATTACHMENTS_DOWNLOADED, AttachmentName, COUPA_URL populados quando disponíveis (sequencial e workers).
- STATUS continua derivado via `_derive_status_label` e sufixo de pasta aplicado de forma consistente.
- Sem alteração de arquitetura (mesmos entrypoints e fluxo principal).

Teste manual
- Rodar sequencial (USE_PROCESS_POOL=false) com 1–2 POs; verificar preenchimento no CSV/Excel e sufixo da pasta.
- Rodar com workers (USE_PROCESS_POOL=true, PROC_WORKERS=1..2) com 1–2 POs; verificar os mesmos campos.

Mensagem de commit sugerida
- `feat(core): PR 03 — propagate downloader result to CSV (supplier, counts, names, url)`

Branch sugerido
- `feat/03-propagate-to-csv`

Checklist
- [x] Objetivo e Escopo claros e limitados
- [x] Arquivos afetados listados
- [x] Pseudodiff pequeno e representativo
- [x] Critérios de aceitação e testes manuais
- [x] Mensagem de commit e branch

