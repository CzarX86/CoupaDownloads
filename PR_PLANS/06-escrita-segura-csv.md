# PR 6 — Revisão/garantia de escrita segura no CSV

Objetivo
- Confirmar coerções de tipo, criação de colunas faltantes e parâmetros de escrita (delimitador preservado, utf-8-sig, lineterminator, quoting).

Escopo
- Arquivo: `src/core/excel_processor.py`

Arquivos afetados
- `src/core/excel_processor.py`

Pseudodiff (referencial)
```
*** Update File: src/core/excel_processor.py
@@ def update_po_status(...):
+ for col in ['STATUS','SUPPLIER','AttachmentName','LAST_PROCESSED','ERROR_MESSAGE','DOWNLOAD_FOLDER','COUPA_URL']:
+   if col not in df.columns: df[col] = ""
+   df[col] = df[col].astype('string').fillna("")
+ for col in ['ATTACHMENTS_FOUND','ATTACHMENTS_DOWNLOADED']:
+   if col not in df.columns: df[col] = 0
+   df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

- df.to_csv(excel_file_path, index=False)
+ df.to_csv(
+   excel_file_path,
+   index=False,
+   sep=detected_sep,
+   encoding='utf-8-sig',
+   lineterminator='\n',
+   quoting=csv.QUOTE_MINIMAL,
+ )
```

Critérios de aceitação
- Sem FutureWarnings de dtype; arquivo abre corretamente no Excel mantendo o delimitador.

Teste manual
- Rodar com CSV “;” (pt-BR); abrir no Excel e validar colunas/hierarquia.

Mensagem de commit sugerida
- `chore(csv): ensure robust coercion and safe write settings (no warnings)`

Branch sugerido
- `chore/csv-safe-write`

