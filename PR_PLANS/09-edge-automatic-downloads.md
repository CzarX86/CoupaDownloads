# PR 9 — Edge: permitir múltiplos downloads automáticos (automatic_downloads)

Objetivo
- Reduzir prompts internos e falhas silenciosas quando vários arquivos são disparados rapidamente, habilitando múltiplos downloads automáticos no Edge (Chromium) via preferências do navegador.

Escopo
- Projeto principal `src/`:
  - `src/core/browser.py`: adicionar a preferência `"profile.default_content_setting_values.automatic_downloads": 1` ao dicionário de prefs do Edge em:
    - `_create_browser_options(...)`
    - `_create_browser_options_without_profile(...)`

Arquivos afetados
- `src/core/browser.py`

Pseudodiff (referencial)
```
*** Update File: src/core/browser.py
@@ def _create_browser_options(...):
-        browser_prefs = {
-            "download.default_directory": download_dir,
-            "download.prompt_for_download": False,
-            "download.directory_upgrade": True,
-            "safebrowsing.enabled": False,
-            "plugins.always_open_pdf_externally": True,
-        }
+        browser_prefs = {
+            "download.default_directory": download_dir,
+            "download.prompt_for_download": False,
+            "download.directory_upgrade": True,
+            "safebrowsing.enabled": False,
+            "plugins.always_open_pdf_externally": True,
+            # Permitir múltiplos downloads automáticos
+            "profile.default_content_setting_values.automatic_downloads": 1,
+        }
@@ def _create_browser_options_without_profile(...):
-        browser_prefs = {
-            "download.default_directory": download_dir,
-            "download.prompt_for_download": False,
-            "download.directory_upgrade": True,
-            "safebrowsing.enabled": False,
-            "plugins.always_open_pdf_externally": True,
-        }
+        browser_prefs = {
+            "download.default_directory": download_dir,
+            "download.prompt_for_download": False,
+            "download.directory_upgrade": True,
+            "safebrowsing.enabled": False,
+            "plugins.always_open_pdf_externally": True,
+            # Permitir múltiplos downloads automáticos
+            "profile.default_content_setting_values.automatic_downloads": 1,
+        }
```

Critérios de aceitação
- Vários downloads sequenciais disparam sem prompts bloqueadores no Edge.
- Nenhuma regressão nas preferências existentes (download.default_directory etc.).

Testes manuais sugeridos
- Executar um PO com múltiplos anexos (≥3) e observar que todos iniciam sem prompt.
- Validar que os arquivos chegam na pasta do PO conforme definido por CDP (`Page.setDownloadBehavior`).

Riscos / observações
- Algumas políticas corporativas podem sobrepor preferências do navegador; nesse caso, a efetividade pode variar.
- Mantida compatibilidade com as opções já usadas (detach=false, etc.).

Mensagem de commit sugerida
- `feat(edge): allow multiple automatic downloads via browser prefs`

Branch sugerido
- `feat/edge-automatic-downloads`

Dependências
- Nenhuma obrigatória; pode ser aplicado isoladamente após as PRs anteriores.

