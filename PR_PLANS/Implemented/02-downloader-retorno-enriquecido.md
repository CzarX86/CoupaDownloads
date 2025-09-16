# PR 2 — Enriquecer retorno do Downloader (estrutura completa)

Objetivo
- Fazer `download_attachments_for_po` retornar dados suficientes para popular o CSV e derivar STATUS de forma unificada.

Escopo
- Arquivo: `src/core/downloader.py`

Arquivos afetados
- `src/core/downloader.py`

Pseudodiff (referencial)
```
*** Update File: src/core/downloader.py
@@
+from dataclasses import dataclass
+
+@dataclass
+class DownloadResult:
+    success: bool
+    message: str
+    attachments_found: int
+    attachments_downloaded: int
+    attachment_names: list[str]
+    supplier_name: str
+    coupa_url: str
@@ class Downloader:
- def download_attachments_for_po(self, po_number: str) -> Tuple[bool, str]:
+ def download_attachments_for_po(self, po_number: str) -> DownloadResult:
     order_number = ...
     url = f"{Config.BASE_URL}/order_headers/{order_number}"
     self.driver.get(url)
+    supplier_name = self.get_supplier_name()
     attachments = self._find_attachments()
     total = len(attachments)
     downloaded = 0
     names = []
     for el in attachments:
         name = self._extract_filename_from_element(el)
         if name:
             names.append(name)
             if self._download_attachment(el, name):
                 downloaded += 1
- if total == 0: msg = "No attachments found."; return True, msg
- else: msg = f"Initiated download for {downloaded}/{total} attachments."; return (downloaded>0), msg
+ if total == 0:
+     msg = "No attachments found."
+     return DownloadResult(True, msg, 0, 0, [], supplier_name, url)
+ msg = f"Initiated download for {downloaded}/{total} attachments."
+ return DownloadResult(downloaded == total and total > 0, msg, total, downloaded, names, supplier_name, url)
@@
+ def get_supplier_name(self) -> str:
+    for sel in Config.SUPPLIER_NAME_CSS_SELECTORS:
+        els = self.driver.find_elements(By.CSS_SELECTOR, sel)
+        if els:
+            txt = (els[0].text or "").strip()
+            if txt:
+                return txt
+    try:
+        el = self.driver.find_element(By.XPATH, Config.SUPPLIER_NAME_XPATH)
+        txt = (el.text or "").strip()
+        if txt:
+            return txt
+    except Exception:
+        pass
+    return "Unknown"
```

Critérios de aceitação
- Em sucesso com anexos, `message` contém “X/Y”.
- Em sucesso sem anexos, `message` é “No attachments found.”

Teste manual
- 1 PO com anexos e 1 sem anexos; observar logs/retorno e consistência de `X/Y`.

Mensagem de commit sugerida
- `feat(downloader): return rich result (counts, names, supplier, url) and standardized messages`

Branch sugerido
- `feat/downloader-rich-result`

